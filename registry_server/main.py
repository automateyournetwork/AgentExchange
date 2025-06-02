import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from registry_server.routes import router as registry_router
from registry_server.models import AgentRegisterRequest

# === Load environment variables ===
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
TRUSTED_DOMAINS = os.getenv("TRUSTED_AGENT_DOMAINS", "").split(",")
SESSION_SECRET = os.getenv("SESSION_SECRET", "registry_secret")

# === FastAPI app ===
app = FastAPI(title="Agent Registry")

# === Middleware ===
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Bearer Token Middleware ===
@app.middleware("http")
async def verify_bearer_token(request: Request, call_next):
    if request.url.path.startswith("/register"):
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        token = auth_header.split(" ", 1)[1]
        try:
            id_info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
            email = id_info.get("email", "")
            if not any(email.endswith(domain) for domain in TRUSTED_DOMAINS):
                raise HTTPException(status_code=403, detail=f"Unauthorized domain: {email}")
            request.state.user_email = email
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Bearer token verification failed: {e}")
    return await call_next(request)

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "message": "Agent Registry is running"}

# === Routes ===
app.include_router(registry_router)

# === Run server ===
if __name__ == "__main__":
    uvicorn.run("registry_server.main:app", host="0.0.0.0", port=3000, reload=True)
