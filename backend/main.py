from fastapi import FastAPI, WebSocket, APIRouter
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import asyncio, functools
import datetime
from . import auth
from .state import app_state
from . import calculations
from . import database
from . import logic
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()

origins = [
    "http://localhost:3000",  # The origin of our React frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")

api_router = APIRouter(prefix="/api")


@api_router.get("/profile")
def fetch_and_store_data(user_name: str):
    """
    Fetches option chain data, extracts relevant info, and stores it in buffers.
    """
    # --- ADD THIS CHECK ---
    # Only run during market hours (e.g., Mon-Fri, 9:15 AM to 3:30 PM IST)
    # Note: Render servers are in UTC. IST is UTC+5:30.
    # 9:15 AM IST = 3:45 AM UTC. 3:30 PM IST = 10:00 AM UTC.
    now_utc = datetime.datetime.utcnow()
    if not (0 <= now_utc.weekday() <= 4 and datetime.time(3, 45) <= now_utc.time() <= datetime.time(10, 0)):
        # Silently skip if market is closed
        return
    # --- END OF CHECK ---
    user_state = app_state["users"].get(user_name)
    access_token = user_state.get("access_token") if user_state else None
    if not access_token:
        print(f"Data fetch for {user_name} skipped: User not authenticated or state not found.")
        return

    # For now, we use a fixed expiry. This will be made dynamic later.
    # TODO: Make expiry_date dynamic
    # NIFTY weekly expiry is on Tuesday.
    today = datetime.date.today()
    days_until_tuesday = (1 - today.weekday() + 7) % 7 # 1 = Tuesday
    expiry_date = today + datetime.timedelta(days=days_until_tuesday)
    
    url = 'https://api-v2.upstox.com/option/chain'
    params = {
        'instrument_key': 'NSE_INDEX|Nifty 50',
        'expiry_date': expiry_date.strftime('%Y-%m-%d')
    }
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching option chain: {response.text}")
        return

    data = response.json().get('data', [])
    if not data:
        print("No option chain data received.")
        return

    # Store the full option chain for the UI
    user_state["option_chain_data"] = data

    # --- Extract and store data ---
    underlying_price = data[0].get('underlying_spot_price')
    user_state["price_buffer"].append(underlying_price)

    # Find the ATM strike
    atm_strike = min(data, key=lambda x: abs(x['strike_price'] - underlying_price))

    # Find the index of the ATM strike in the sorted list
    try:
        atm_index = sorted(data, key=lambda x: x['strike_price']).index(atm_strike)
    except ValueError:
        print("Could not find ATM strike in the data list.")
        return

    # Select the 2nd OTM call option as per the strategy
    target_strike_index = atm_index + 2
    sorted_strikes = sorted(data, key=lambda x: x['strike_price'])

    if target_strike_index < len(sorted_strikes):
        target_strike_data = sorted_strikes[target_strike_index]
        call_greeks = target_strike_data.get('call_options', {}).get('option_greeks', {})
        call_market_data = target_strike_data.get('call_options', {}).get('market_data', {})
        latest_premium = call_market_data.get('ltp')

        # Populate the Greek buffers
        user_state["delta_buffer"].append(call_greeks.get('delta'))
        user_state["gamma_buffer"].append(call_greeks.get('gamma'))
        user_state["theta_buffer"].append(call_greeks.get('theta'))
        user_state["iv_buffer"].append(call_greeks.get('iv'))
        # Populate the premium buffer
        user_state["premium_buffer"].append(latest_premium)

        print(f"[{user_name}] Fetched Price: {underlying_price:.2f} | "
              f"Monitoring Strike: {target_strike_data['strike_price']} | "
              f"Delta: {call_greeks.get('delta')}")

        # --- Delayed Baseline Capture Logic ---
        if not user_state.get("baseline_set") and user_state.get("login_timestamp"):
            # Check if 15 minutes have passed since login
            if datetime.datetime.now() - user_state["login_timestamp"] >= datetime.timedelta(minutes=15):
                user_state["baseline_values"] = {
                    "price": underlying_price,
                    "delta": call_greeks.get('delta'),
                    "gamma": call_greeks.get('gamma'),
                    "iv": call_greeks.get('iv')
                }
                user_state["baseline_timestamp"] = datetime.datetime.now()
                user_state["baseline_set"] = True
                print(f"!!! [{user_name}] BASELINE CAPTURED at {user_state['baseline_timestamp']} !!!")
                print(f"Baseline values: {user_state['baseline_values']}")
    else:
        print(f"[{user_name}] Could not find 2nd OTM strike.")

def run_greek_confirmation(user_name: str):
    """
    Runs every 10 seconds to check for Greek confirmation on a pending candidate.
    """
    # --- ADD THIS CHECK ---
    # Only run during market hours
    now_utc = datetime.datetime.utcnow()
    if not (0 <= now_utc.weekday() <= 4 and datetime.time(3, 45) <= now_utc.time() <= datetime.time(10, 0)):
        # If a candidate exists outside hours, clear it to be safe.
        if app_state["users"].get(user_name, {}).get("candidate_setup"):
            app_state["users"][user_name]["candidate_setup"] = None
        return
    # --- END OF CHECK ---
    user_state = app_state["users"].get(user_name)
    if not user_state: return
    now = datetime.datetime.now()
    if user_state.get("cooldown_until") and now < user_state.get("cooldown_until"):
        # We are in a cooldown period, do nothing with active signals.
        return

    candidate = user_state.get("candidate_setup")
    if not candidate:
        return

    # --- State 1: Monitor for Entry Confirmation ---
    if candidate.get("status") == "Pending_Greek_Confirmation":
        # Calculate smoothed Greek values over a 30-second window for entry confirmation
        smoothed_greeks = {
            "delta_slope": calculations.calculate_smoothed_slope(user_state["delta_buffer"], 30),
            "gamma_change": calculations.calculate_smoothed_percent_change(user_state["gamma_buffer"], 30),
            "iv_trend": calculations.calculate_smoothed_slope(user_state["iv_buffer"], 30),
            "theta_change": calculations.calculate_smoothed_percent_change(user_state["theta_buffer"], 30)
        }

        settings = database.get_settings()
        # Run the confirmation logic
        confirmed_candidate = logic.confirm_with_greeks(
            candidate=candidate, 
            smoothed_greeks=smoothed_greeks, 
            settings=settings
        )

        # If the signal is approved, calculate SL/Target and update the log
        if confirmed_candidate and confirmed_candidate.get("status") == "ENTRY_APPROVED":
            risk_percent = float(settings.get('risk_percent', 1.0))
            rr_ratio = float(settings.get('risk_reward_ratio', 2.0))

            entry_price = confirmed_candidate.get("signal_premium")
            stop_loss_points = entry_price * (risk_percent / 100)
            
            sl_price = entry_price - stop_loss_points
            target_price = entry_price + (stop_loss_points * rr_ratio)

            confirmed_candidate['stop_loss'] = round(sl_price, 2)
            confirmed_candidate['target'] = round(target_price, 2)

            # Update the database log with the final details
            db_updates = {"status": "ENTRY_APPROVED", "entry_price": entry_price, "result": f"SL: {sl_price:.2f}, TGT: {target_price:.2f}"}
            database.update_log_entry(confirmed_candidate.get("log_id"), db_updates)
            user_state["candidate_setup"] = confirmed_candidate
        return

    # --- State 2: Monitor Active Trade for Exit ---
    if candidate.get("status") == "ENTRY_APPROVED":
        latest_premium = user_state["premium_buffer"][-1] if user_state["premium_buffer"] else 0

        # Calculate smoothed Greek values over a 60-second window for exit monitoring
        smoothed_greeks_for_exit = {
            "delta_slope": calculations.calculate_smoothed_slope(user_state["delta_buffer"], 60),
            "gamma_change": calculations.calculate_smoothed_percent_change(user_state["gamma_buffer"], 60),
            "iv_trend": calculations.calculate_smoothed_slope(user_state["iv_buffer"], 60),
        }

        settings = database.get_settings()
        exit_reason = logic.check_exit_conditions(candidate, latest_premium, smoothed_greeks_for_exit, settings)

        if exit_reason:
            print(f"!!! [{user_name}] EXIT CONDITION MET: {exit_reason} !!!")
            # Update the log with the exit reason
            db_updates = {"status": "CLOSED", "result": exit_reason}
            database.update_log_entry(candidate.get("log_id"), db_updates)

            # Clear the active signal and enter cooldown
            user_state["candidate_setup"] = None
            settings = database.get_settings()
            # Temporarily store the exit reason for the WebSocket to broadcast
            user_state["last_exit_reason"] = exit_reason

            cooldown_minutes = int(settings.get('cooldown_minutes', 15))
            user_state["cooldown_until"] = now + datetime.timedelta(minutes=cooldown_minutes)
            print(f"[{user_name}] Trade closed. Entering cooldown until {user_state['cooldown_until']}")


def process_5min_candle(user_name: str):
    """
    Forms a 5-minute candle from the price_buffer and stores it.
    """
    # --- ADD THIS CHECK ---
    # Only run during market hours
    now_utc = datetime.datetime.utcnow()
    if not (0 <= now_utc.weekday() <= 4 and datetime.time(3, 45) <= now_utc.time() <= datetime.time(10, 0)):
        return
    # --- END OF CHECK ---
    user_state = app_state["users"].get(user_name)
    if not user_state: return

    price_buffer = user_state["price_buffer"]
    if len(price_buffer) < 30:
        print("Not enough data for 5-min candle, skipping.")
        return

    # Take the last 30 data points for the 5-min candle
    prices = list(price_buffer)[-30:]
    
    candle_open = prices[0]
    candle_high = max(prices)
    candle_low = min(prices)
    candle_close = prices[-1]
    
    # Align timestamp to the start of the 5-minute interval
    now = datetime.datetime.now()
    timestamp = now.replace(minute=now.minute - (now.minute % 5), second=0, microsecond=0)
    
    new_candle = [timestamp.isoformat(), candle_open, candle_high, candle_low, candle_close]
    user_state["candles_5min_buffer"].append(new_candle)
    print(f"[{user_name}] New 5-min Candle created: {new_candle}")

def run_logic_controller(user_name: str):
    """
    Runs every 5 minutes to determine Bias and Market Type.
    """
    # --- ADD THIS CHECK ---
    # Only run during market hours
    now_utc = datetime.datetime.utcnow()
    if not (0 <= now_utc.weekday() <= 4 and datetime.time(3, 45) <= now_utc.time() <= datetime.time(10, 0)):
        return
    # --- END OF CHECK ---
    user_state = app_state["users"].get(user_name)
    if not user_state: return
    
    # Ensure baseline is set before running logic
    if not user_state.get("baseline_set"):
        return

    if user_state.get("cooldown_until") and datetime.datetime.now() < user_state.get("cooldown_until"):
        print(f"[{user_name}] Logic controller skipped due to cooldown.")
        # Reset bias/market type during cooldown to avoid new signals
        user_state["bias"], user_state["market_type"] = "Neutral", "Undetermined"
        return
    # 1. Get all calculated features
    latest_price = user_state["price_buffer"][-1] if user_state["price_buffer"] else 0
    latest_delta = user_state["delta_buffer"][-1] if user_state["delta_buffer"] else None
    latest_gamma = user_state["gamma_buffer"][-1] if user_state["gamma_buffer"] else None
    latest_iv = user_state["iv_buffer"][-1] if user_state["iv_buffer"] else None
    latest_premium = user_state["premium_buffer"][-1] if user_state["premium_buffer"] else 0

    # 2. Determine Bias
    bias = logic.determine_bias(
        current_price=latest_price,
        current_delta=latest_delta,
        current_gamma=latest_gamma,
        current_iv=latest_iv,
        baseline_values=user_state["baseline_values"]
    )
    user_state["bias"] = bias

    # 3. Determine Market Type
    settings = database.get_settings()
    # Update market_type_window_size from settings if it has changed
    user_state["market_type_window_size"] = int(settings.get("market_type_window_size", 3))

    market_type = logic.determine_market_type(
        candles_5min_buffer=user_state["candles_5min_buffer"],
        market_type_window_size=user_state["market_type_window_size"],
        settings=settings
    )
    user_state["market_type"] = market_type

    # 4. Detect Entry Setup
    # This function now returns an action dictionary
    result = logic.detect_entry_setup(
        bias=bias,
        market_type=market_type,
        candles_5min_buffer=user_state["candles_5min_buffer"],
        latest_price=latest_price,
        signal_premium=latest_premium,
        price_action_state=user_state["price_action_state"],
        settings=settings
    )

    if result:
        action = result.get("action")
        if action == "trade_setup":
            candidate = result.get("setup")
            user_state["candidate_setup"] = candidate
            if candidate and candidate.get("status") == "Pending_Greek_Confirmation":
                log_id = database.log_signal(candidate)
                if log_id:
                    candidate["log_id"] = log_id
                    user_state["candidate_setup"] = candidate
        elif action == "update_state":
            user_state["price_action_state"].update(result.get("new_state", {}))
            print(f"[{user_name}] Price action state updated: {user_state['price_action_state']}")
        elif action == "reset_state":
            user_state["price_action_state"]["status"] = "LOOKING_FOR_BOS"
            user_state["price_action_state"]["last_bos_type"] = None
            print(f"[{user_name}] Price action state reset to LOOKING_FOR_BOS.")

    print(f"[{user_name}] Logic Controller Update: Bias={bias}, MarketType={market_type}, PA_Status={user_state['price_action_state']['status']}")

def get_user_profile():
    """
    Fetches the user's profile from Upstox to test the access token.
    """
    # This is a generic endpoint, let's just use the first available token for a quick test
    first_user = next(iter(app_state["users"].values()), None)
    access_token = first_user.get("access_token") if first_user else None
    if not access_token:
        return {"error": "User not authenticated. Please login first via /auth/login"}

    url = "https://api-v2.upstox.com/user/profile"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

def start_user_scheduler(user_name: str):
    """
    Starts a set of background jobs for a specific user.
    """
    user_state = app_state["users"].get(user_name)
    if not user_state or user_state.get("scheduler"):
        print(f"Scheduler for {user_name} already running or user state not found.")
        return

    # Set the login timestamp when the scheduler starts
    user_state["login_timestamp"] = datetime.datetime.now()

    scheduler = BackgroundScheduler()
    # Use functools.partial to pass the user_name to the job functions
    scheduler.add_job(functools.partial(fetch_and_store_data, user_name), 'interval', seconds=10, id=f'data_fetch_{user_name}')
    scheduler.add_job(functools.partial(run_greek_confirmation, user_name), 'interval', seconds=10, start_date=datetime.datetime.now() + datetime.timedelta(seconds=10), id=f'greek_confirm_{user_name}')
    scheduler.add_job(functools.partial(process_5min_candle, user_name), 'cron', minute='*/5', second='5', id=f'candle_{user_name}')
    scheduler.add_job(functools.partial(run_logic_controller, user_name), 'cron', minute='*/5', second='10', id=f'logic_{user_name}')
    scheduler.start()
    user_state["scheduler"] = scheduler
    print(f"Background scheduler started for user: {user_name} at {user_state['login_timestamp']}")

@app.on_event("startup")
def startup_event():
    """
    Initializes and starts the background scheduler on application startup.
    """
    database.init_db() # Initialize the database
    # We no longer start a global scheduler on startup.
    print("Database initialized. Schedulers will start upon user login.")

@api_router.get("/latest-data")
def get_latest_data():
    """
    An endpoint to inspect the current content of our data buffers.
    """
    return {
        "users": {
            user: {
                "prices": list(state["price_buffer"]),
                "deltas": list(state["delta_buffer"]),
                "gammas": list(state["gamma_buffer"]),
            } for user, state in app_state["users"].items()
        }
    }

@api_router.get("/signals")
def get_signals(user_name: str = None):
    """
    An endpoint to calculate and display the current signals from the data.
    """
    # If no user is specified, try to get the first one.
    if not user_name:
        user_name = next(iter(app_state["users"]), None)
    
    user_state = app_state["users"].get(user_name)
    if not user_state:
        return {"error": f"No data for user: {user_name}"}

    # --- New structured signals object ---
    signals_data = {}
    settings = database.get_settings()

    # --- 1. Bias Details ---
    if user_state.get("baseline_set"):
        baseline_values = user_state["baseline_values"]
        current_price = user_state["price_buffer"][-1] if user_state["price_buffer"] else None
        current_delta = user_state["delta_buffer"][-1] if user_state["delta_buffer"] else None
        
        price_from_baseline = current_price - baseline_values.get("price", current_price) if current_price else 0
        delta_from_baseline = current_delta - baseline_values.get("delta", current_delta) if current_delta else 0

        signals_data["bias_details"] = {
            "price_from_baseline": f"{price_from_baseline:.2f}",
            "delta_from_baseline": f"{delta_from_baseline:.4f}",
            "bullish_conditions": {
                "Price > Baseline": price_from_baseline > 0,
                "Delta > Baseline": delta_from_baseline > 0,
            },
            "bearish_conditions": {
                "Price < Baseline": price_from_baseline < 0,
                "Delta < Baseline": delta_from_baseline < 0,
            }
        }

    # --- 2. Market Type Details ---
    window_size = int(user_state.get("market_type_window_size", 3))
    atr = calculations.calculate_atr(user_state["candles_5min_buffer"], period=window_size)
    body_ratio_avg = calculations.calculate_average_body_ratio(user_state["candles_5min_buffer"], window_size=window_size)
    signals_data["market_type_details"] = {
        "atr": f"{atr:.2f}",
        "body_ratio_avg": f"{body_ratio_avg:.2f}",
        "trendy_conditions": {
            f"ATR ({window_size}-p) > 15": atr > 15,
            f"Avg Body Ratio ({window_size}-p) > 0.5": body_ratio_avg > 0.5,
        },
        "volatile_conditions": {
            f"ATR ({window_size}-p) > 25": atr > 25,
            f"Avg Body Ratio ({window_size}-p) < 0.4": body_ratio_avg < 0.4,
        }
    }

    # --- 3. Price Action Details (Placeholder) ---
    signals_data["price_action_details"] = {
        "status": "Monitoring...",
        "details": "Waiting for BOS or Retest signal."
    }

    # --- 4. Greek Confirmation Details ---
    signals_data["greek_confirmation_details"] = {
        "smoothed_delta_slope": f"{calculations.calculate_smoothed_slope(user_state['delta_buffer'], 30):.4f}",
        "smoothed_gamma_change": f"{calculations.calculate_smoothed_percent_change(user_state['gamma_buffer'], 30):.2f}%",
        "smoothed_iv_trend": f"{calculations.calculate_smoothed_slope(user_state['iv_buffer'], 30):.4f}",
        "smoothed_theta_change": f"{calculations.calculate_smoothed_percent_change(user_state['theta_buffer'], 30):.2f}%",
    }

    return signals_data

@api_router.get("/status")
def get_system_status():
    """
    Returns the current system status (Bias and Market Type).
    """
    # Return status for all active users
    return {user: {
        "bias": state.get("bias"),
        "market_type": state.get("market_type"),
        "candidate_setup": state.get("candidate_setup"),
    } for user, state in app_state["users"].items()}

@api_router.get("/tradelogs")
def get_trade_logs():
    """
    Returns all historical trade logs from the database.
    """
    return database.get_all_logs()

@api_router.get("/option-chain/{user_name}")
def get_option_chain(user_name: str):
    """
    Returns the latest full option chain data.
    """
    user_state = app_state["users"].get(user_name)
    if not user_state:
        return []
    # Return a copy to avoid potential mutation issues
    return list(user_state.get("option_chain_data", []))

@api_router.get("/settings")
def read_settings():
    """
    Returns the current strategy settings from the database.
    """
    return database.get_settings()

class SettingsUpdate(BaseModel):
    key: str
    value: str

@api_router.post("/settings")
def write_settings(settings_update: SettingsUpdate):
    database.update_setting(settings_update.key, settings_update.value)
    return {"status": "success", "key": settings_update.key, "value": settings_update.value}

class LogoutRequest(BaseModel):
    user_name: str

@api_router.post("/logout")
def logout_user(request: LogoutRequest):
    """
    Stops the background scheduler for a user and clears their session state.
    """
    user_name = request.user_name
    user_state = app_state["users"].get(user_name)

    if not user_state:
        return {"status": "ok", "message": "User already logged out."}

    scheduler = user_state.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print(f"Scheduler for user '{user_name}' has been shut down.")

    del app_state["users"][user_name]
    return {"status": "ok", "message": f"User {user_name} logged out successfully."}

@api_router.websocket("/ws/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_name: str):
    """
    WebSocket endpoint to stream live data and system status to the frontend.
    """
    await websocket.accept()
    print(f"WebSocket connection established for user: {user_name}")
    try:
        while True:
            user_state = app_state["users"].get(user_name)
            if not user_state:
                # If user logs out or state is cleared, send an empty payload and wait
                await websocket.send_json({})
                await asyncio.sleep(2)
                continue

            nifty_price = user_state["price_buffer"][-1] if user_state["price_buffer"] else "Fetching..."
            delta = user_state["delta_buffer"][-1] if user_state["delta_buffer"] else "--"
            gamma = user_state["gamma_buffer"][-1] if user_state["gamma_buffer"] else "--"
            theta = user_state["theta_buffer"][-1] if user_state["theta_buffer"] else "--"
            iv = user_state["iv_buffer"][-1] if user_state["iv_buffer"] else "--"

            payload = {
                "nifty_price": f"{nifty_price:.2f}" if isinstance(nifty_price, float) else nifty_price,
                "delta": f"{delta:.4f}" if isinstance(delta, float) else delta,
                "gamma": f"{gamma:.4f}" if isinstance(gamma, float) else gamma,
                "theta": f"{theta:.4f}" if isinstance(theta, float) else theta,
                "iv": f"{iv:.4f}" if isinstance(iv, float) else iv,
                "bias": user_state.get("bias", "Neutral"),
                "market_type": user_state.get("market_type", "Undetermined"),
                "candidate_setup": user_state.get("candidate_setup"),
                "last_exit_reason": user_state.get("last_exit_reason"),
            }
            
            # Clear the one-time exit reason after adding it to the payload
            if user_state.get("last_exit_reason"):
                user_state["last_exit_reason"] = None

            await websocket.send_json(payload)
            await asyncio.sleep(2)  # Send updates every 2 seconds
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        print("Client disconnected from WebSocket.")

app.include_router(api_router)

# Serve specific root-level static files directly
@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("frontend/build/manifest.json")

@app.get("/favicon.ico")
async def serve_favicon():
    return FileResponse("frontend/build/favicon.ico")

@app.get("/logo192.png")
async def serve_logo192():
    return FileResponse("frontend/build/logo192.png")

# Mount the static files directory for assets like JS, CSS, images
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """
    Catch-all endpoint to serve the React app's index.html for any non-API, non-static path.
    This allows React Router to handle the routing.
    """
    return FileResponse("frontend/build/index.html")