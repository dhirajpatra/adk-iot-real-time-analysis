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

@router.get("/oauth/auth")
async def authorize(request: Request):
    # Access query parameters directly
    query_params = dict(request.query_params)
    print(f"Received authorize request with raw query parameters: {query_params}")

    # Manually extract parameters from query_params
    response_type = query_params.get("response_type")
    client_id = query_params.get("client_id")
    redirect_uri = query_params.get("redirect_uri")
    state = query_params.get("state") # state is optional

    print(f"  Incoming response_type: {response_type}")
    print(f"  Incoming client_id: {client_id}")
    print(f"  Incoming redirect_uri: {redirect_uri}")
    print(f"  Incoming state: {state}")

    # Print values loaded from .env for comparison
    print(f"  Expected CLIENT_ID (from .env): {CLIENT_ID}")
    print(f"  Expected GOOGLE_REDIRECT_URI (from .env) that your server redirects back to: {REDIRECT_URI}")


    # Original validation logic
    if client_id != CLIENT_ID:
        print("Authorization failed: Client ID mismatch.")
        return JSONResponse({"error": "invalid_client"}, status_code=400)

    # Ensure required parameters are present before proceeding with redirect logic
    if not response_type or not client_id or not redirect_uri:
        print("Authorization failed: Missing required query parameters.")
        return JSONResponse({"error": "invalid_request", "description": "Missing required parameters"}, status_code=422)


    redirect_url = f"{redirect_uri}?code={AUTH_CODE}"
    if state:
        redirect_url += f"&state={state}"
    print(f"Redirecting to: {redirect_url}")
    return RedirectResponse(redirect_url)

@router.post("/oauth/token")
async def token(request: Request):
    form_data = {}
    try:
        form_data = await request.form() # Attempt to parse as form data
    except Exception as e:
        print(f"Error parsing form data: {e}")
        return JSONResponse({"error": "invalid_request_format"}, status_code=400)

    print(f"Received token request with raw form data: {form_data}")

    # Manually extract parameters from form_data
    grant_type = form_data.get("grant_type")
    code = form_data.get("code")
    redirect_uri = form_data.get("redirect_uri")
    client_id_from_request = form_data.get("client_id") # Renamed to avoid conflict
    client_secret_from_request = form_data.get("client_secret") # Renamed to avoid conflict

    print(f"  Incoming grant_type: {grant_type}")
    print(f"  Incoming code: {code}")
    print(f"  Incoming redirect_uri: {redirect_uri}")
    print(f"  Incoming client_id: {client_id_from_request}")
    print(f"  Incoming client_secret: {client_secret_from_request}")

    # Print values loaded from .env for comparison
    print(f"  Expected CLIENT_ID (from .env): {CLIENT_ID}")
    print(f"  Expected CLIENT_SECRET (from .env): {CLIENT_SECRET}")
    print(f"  Expected REDIRECT_URI (from .env): {REDIRECT_URI}")
    print(f"  Expected AUTH_CODE (from .env): {AUTH_CODE}")

    # Modified validation logic: Removed checks for client_id_from_request and client_secret_from_request
    # as Google is not sending them in the form data for this integration.
    if (
        grant_type != "authorization_code"
        or code != AUTH_CODE
        or redirect_uri != REDIRECT_URI
    ):
        print("Token validation failed: Mismatch in grant_type, code, or redirect_uri.")
        # Added a more specific error message based on the actual failure points
        if grant_type != "authorization_code":
            print("  Reason: grant_type is not 'authorization_code'")
        if code != AUTH_CODE:
            print("  Reason: code mismatch")
        if redirect_uri != REDIRECT_URI:
            print("  Reason: redirect_uri mismatch")

        return JSONResponse({"error": "invalid_request"}, status_code=400)

    access_token = jwt.encode(
        {"sub": "user123", "exp": datetime.utcnow() + timedelta(hours=1)},
        ACCESS_TOKEN_SECRET,
        algorithm="HS256"
    )
    print(f"Successfully issued access token for user: user123")
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