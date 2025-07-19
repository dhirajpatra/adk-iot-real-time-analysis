# simple_oauth_server.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Dummy client and user config
CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')
AUTH_CODE = os.getenv('AUTH_CODE', 'dummy_auth_code')  # Replace with actual auth code logic
ACCESS_TOKEN_SECRET = os.getenv('SECRET_KEY')

@router.get("/oauth/authorize")
async def authorize(response_type: str, client_id: str, redirect_uri: str, state: Optional[str] = None):
    if client_id != CLIENT_ID:
        return JSONResponse({"error": "invalid_client"}, status_code=400)

    redirect_url = f"{redirect_uri}?code={AUTH_CODE}"
    if state:
        redirect_url += f"&state={state}"
    return RedirectResponse(redirect_url)

@router.post("/oauth/token")
async def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...)
):
    if (
        grant_type != "authorization_code"
        or code != AUTH_CODE
        or client_id != CLIENT_ID
        or client_secret != CLIENT_SECRET
        or redirect_uri != REDIRECT_URI
    ):
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    access_token = jwt.encode(
        {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
        ACCESS_TOKEN_SECRET,
        algorithm="HS256"
    )
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }

@router.get("/oauth/userinfo")
async def userinfo(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    token = auth.split(" ")[1]
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        return {"sub": payload["sub"], "name": "Test User", "email": "test@example.com"}
    except Exception:
        return JSONResponse({"error": "invalid_token"}, status_code=401)
