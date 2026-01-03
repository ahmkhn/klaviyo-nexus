from fastapi import FastAPI

app = FastAPI(title="Klaviyo Nexus Backend")

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Klaviyo Nexus"}

@app.get("/health")
def health_check():
    return {"status": "super healthy"}