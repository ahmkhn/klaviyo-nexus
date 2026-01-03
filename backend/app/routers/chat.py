from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import OAuthInstallation
from app.agent import run_chat_turn

router = APIRouter(prefix="/api", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: list = [] # Simplification: Frontend sends history

@router.post("/chat")
async def chat_endpoint(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    # 1. Get Session ID from Cookie
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # 2. Get OAuth Token from DB
    install = db.query(OAuthInstallation).filter(OAuthInstallation.session_id == session_id).first()
    if not install or not install.access_token:
        raise HTTPException(status_code=401, detail="Klaviyo login required")

    # 3. Run the Agent
    # Note: We pass the access_token so the agent can use it securely
    try:
        response_data = await run_chat_turn(
            user_message=payload.message, 
            chat_history=payload.history, 
            oauth_token=install.access_token
        )
        return response_data
    except Exception as e:
        print(f"Agent Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))