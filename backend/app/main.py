from fastapi import FastAPI
from app.database import Base, engine
from app.routers import auth 
from app import models

app = FastAPI(title="Klaviyo Nexus Backend")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Klaviyo Nexus"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}