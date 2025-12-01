
import os
import requests
import datetime
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from .state import get_user_state

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

user_credentials = {} # Keyed by user name ('samarth', 'prajwal')

# Safely add users to the credentials dictionary if their details exist
if samarth_client_id and samarth_client_secret:
    user_credentials["samarth"] = {"client_id": samarth_client_id, "secret": samarth_client_secret}

if prajwal_client_id and prajwal_client_secret:
    user_credentials["prajwal"] = {"client_id": prajwal_client_id, "secret": prajwal_client_secret}

if not redirect_uri or not user_credentials:
    # We need at least one user and a redirect URI to function
    print("WARNING: Required environment variables are missing. Please configure UPSTOX_REDIRECT_URI and at least one user's CLIENT_ID and CLIENT_SECRET in backend/.env")

@router.get("/upstox/callback")
async def upstox_callback(code: str, state: str, request: Request):
    """
    Handles the callback from Upstox after user authentication.
    Exchanges the authorization code for an access token.
    """
    token_url = "https://api-v2.upstox.com/login/authorization/token"
    headers = {
        "accept": "application/json"
    }

    # The 'state' parameter identifies the user.
    user_name = state
    if user_name not in user_credentials:
        raise HTTPException(status_code=400, detail=f"Invalid user identifier in state: {user_name}")

    creds = user_credentials[user_name]
    data = {
        "client_id": creds["client_id"],
        "client_secret": creds["secret"],
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code": code,
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        
        # Check for a non-successful status code from Upstox
        if response.status_code != 200:
            error_details = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            print(f"Error from Upstox API: {response.status_code} - {error_details}")
            raise HTTPException(status_code=400, detail=f"Failed to obtain access token from Upstox: {error_details}")

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Access token not found in response from Upstox.")
        
        # Get or create the state for this user and store their token
        user_state = get_user_state(user_name)
        user_state["access_token"] = access_token
        print(f"Successfully authenticated as {user_name} and access token stored.")

        # Start the background jobs specifically for this user
        from .main import start_user_scheduler
        start_user_scheduler(user_name)

        # Redirect to the frontend with the access token and user identifier
        frontend_url = f"http://localhost:3000/dashboard?access_token={access_token}&user={user_name}"
        return RedirectResponse(url=frontend_url)
    except requests.exceptions.RequestException as e: # Catch network-level errors
        print(f"Error exchanging token for {user_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Network error while communicating with Upstox: {e}")