from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

# actual users/installs
class OAuthInstallation(Base):
    __tablename__ = "oauth_installations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable = False)
    
    # OAuth Tokens
    access_token = Column(Text, nullable = False)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    scopes = Column(Text)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# PKCE storage
class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    
    state = Column(String, unique=True, index=True) 
    
    code_verifier = Column(String, nullable=False) 
    
    created_at = Column(DateTime, default=datetime.utcnow)