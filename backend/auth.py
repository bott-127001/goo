
import os
import requests
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from .state import app_state

# Build a path to the .env file relative to this file's location
# This ensures the backend can find its .env file reliably.
env_path = Path(__file__).resolve().parent / '.env'
if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}. Please create it.")
load_dotenv(dotenv_path=env_path) # Load the .env file

router = APIRouter(
    # No prefix here, as the callback URL from Upstox doesn't have it.
    # We will add the prefix in main.py when including the router.
    tags=["authentication"]
)

# --- Load credentials from .env file ---
samarth_client_id = os.getenv("SAMARTH_UPSTOX_CLIENT_ID")
samarth_client_secret = os.getenv("SAMARTH_UPSTOX_CLIENT_SECRET")
prajwal_client_id = os.getenv("PRAJWAL_UPSTOX_CLIENT_ID")
prajwal_client_secret = os.getenv("PRAJWAL_UPSTOX_CLIENT_SECRET")
redirect_uri = os.getenv("UPSTOX_REDIRECT_URI")

user_credentials = {}

# Safely add users to the credentials dictionary if their details exist
if samarth_client_id and samarth_client_secret:
    user_credentials[samarth_client_id] = {"secret": samarth_client_secret, "name": "samarth"}

if prajwal_client_id and prajwal_client_secret:
    user_credentials[prajwal_client_id] = {"secret": prajwal_client_secret, "name": "prajwal"}

if not redirect_uri or not user_credentials:
    # We need at least one user and a redirect URI to function
    print("WARNING: Required environment variables are missing. Please configure UPSTOX_REDIRECT_URI and at least one user's CLIENT_ID and CLIENT_SECRET in backend/.env")

@router.get("/upstox/callback")
async def upstox_callback(code: str, request: Request):
    """
    Handles the callback from Upstox after user authentication.
    Exchanges the authorization code for an access token.
    """
    token_url = "https://api-v2.upstox.com/login/authorization/token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Try to get a token for each configured user until one succeeds
    for client_id, creds in user_credentials.items():
        data = {
            "client_id": client_id,
            "client_secret": creds["secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code": code,
        }
        try:
            response = requests.post(token_url, headers=headers, data=data)
            if response.status_code == 200 and "access_token" in response.json():
                token_data = response.json()
                access_token = token_data.get("access_token")
                app_state["access_token"] = access_token
                print(f"Successfully authenticated as {creds.get('name')} and access token stored.")
                
                # Resume the scheduler if it's paused
                scheduler = app_state.get("scheduler")
                if scheduler and scheduler.state == 2: # 2 is the state for 'paused'
                    scheduler.resume()
                    print("Scheduler has been resumed.")

                # Redirect to the frontend with the access token and user identifier
                frontend_url = f"http://localhost:3000/dashboard?access_token={access_token}&user={creds.get('name')}"
                return RedirectResponse(url=frontend_url)
        except requests.exceptions.RequestException:
            continue # Ignore exceptions and try the next user
    
    # If the loop finishes without a successful token exchange
    raise HTTPException(
        status_code=400, 
        detail="Failed to obtain access token for any user. The authorization code may be invalid or expired."
    )