# google_auth.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
import os
from dotenv import load_dotenv

load_dotenv()

# Setup OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Define router for auth
router = APIRouter()

@router.get('/auth/google/login')
async def login(request: Request):
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"message": "Logged out"})

@router.get('/auth/google/callback')
async def callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        return JSONResponse({'error': str(e)}, status_code=400)
    
    user_info = token.get('userinfo')
    if user_info:
        request.session['user'] = dict(user_info)
        return JSONResponse(user_info)
    raise HTTPException(status_code=400, detail='Could not retrieve user info.')

@router.get('/me')
async def get_user(request: Request):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user
