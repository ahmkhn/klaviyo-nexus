import base64
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OAuthInstallation, OAuthState  # you create OAuthState

router = APIRouter(prefix="/auth", tags=["auth"])

KLAVIYO_CLIENT_ID = os.getenv("KLAVIYO_CLIENT_ID")
KLAVIYO_CLIENT_SECRET = os.getenv("KLAVIYO_CLIENT_SECRET")
REDIRECT_URI = os.getenv("KLAVIYO_REDIRECT_URI", "http://localhost:8000/auth/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode("utf-8")
    )
    return verifier, challenge


def basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("utf-8")


@router.get("/login")
def login(db: Session = Depends(get_db)):
    print(f"DEBUG: My Client ID is: '{KLAVIYO_CLIENT_ID}'")
    if not KLAVIYO_CLIENT_ID or not KLAVIYO_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Missing Klaviyo OAuth env vars")

    state = str(uuid.uuid4())
    code_verifier, code_challenge = generate_pkce_pair()

    # Store verifier keyed by state for 5 min
    db.add(OAuthState(state=state, code_verifier=code_verifier))
    db.commit()

    scopes = "accounts:read campaigns:read profiles:read lists:read segments:read lists:write profiles:write campaigns:write"
    params = {
        "response_type": "code",
        "client_id": KLAVIYO_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": scopes,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }

    auth_url = "https://www.klaviyo.com/oauth/authorize?" + urlencode(params)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(request: Request, db: Session = Depends(get_db)):
    error = request.query_params.get("error")
    if error:
        desc = request.query_params.get("error_description", "")
        return RedirectResponse(f"{FRONTEND_URL}/?error={error}&desc={desc}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    # Look up verifier
    oauth_state = db.query(OAuthState).filter(OAuthState.state == state).first()
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid/expired state")

    token_url = "https://a.klaviyo.com/oauth/token"
    headers = {
        "Authorization": basic_auth_header(KLAVIYO_CLIENT_ID, KLAVIYO_CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": oauth_state.code_verifier,
        "redirect_uri": REDIRECT_URI,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(token_url, headers=headers, data=data)

    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")

    token_data = resp.json()
    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))

    # Create/update installation (keyed by session cookie OR new session_id)
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())

    inst = (
        db.query(OAuthInstallation)
        .filter(OAuthInstallation.session_id == session_id)
        .first()
    )
    if not inst:
        inst = OAuthInstallation(session_id=session_id)
        db.add(inst)

    inst.access_token = token_data["access_token"]
    inst.refresh_token = token_data.get("refresh_token")
    inst.token_expires_at = expires_at
    inst.scopes = token_data.get("scope")

    # Clean up used state
    db.delete(oauth_state)

    db.commit()

    r = RedirectResponse(url=f"{FRONTEND_URL}/chat")
    r.set_cookie(
        key="session_id", 
        value=session_id, 
        httponly=True, 
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        secure=False # make this an env var for localhost vs production environments, needs to be True on prod
    )
    return r