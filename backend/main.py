from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import requests
import asyncio
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

# --- Mount Static Files for Frontend ---
# This must be after all other routes
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="static")

def fetch_and_store_data():
    """
    Fetches option chain data, extracts relevant info, and stores it in buffers.
    """
    access_token = app_state.get("access_token")
    if not access_token:
        print("Data fetch skipped: User not authenticated.")
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
    app_state["option_chain_data"] = data

    # --- Extract and store data ---
    underlying_price = data[0].get('underlying_spot_price')
    app_state["price_buffer"].append(underlying_price)

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

        # Populate the Greek buffers
        app_state["delta_buffer"].append(call_greeks.get('delta'))
        app_state["gamma_buffer"].append(call_greeks.get('gamma'))
        app_state["theta_buffer"].append(call_greeks.get('theta'))
        app_state["iv_buffer"].append(call_greeks.get('iv'))

        print(f"Fetched Price: {underlying_price:.2f} | "
              f"Monitoring Strike: {target_strike_data['strike_price']} | "
              f"Delta: {call_greeks.get('delta')}")
    else:
        print("Could not find 2nd OTM strike.")

def run_greek_confirmation():
    """
    Runs every 10 seconds to check for Greek confirmation on a pending candidate.
    """
    now = datetime.datetime.now()
    if app_state.get("cooldown_until") and now < app_state.get("cooldown_until"):
        # We are in a cooldown period, do nothing with active signals.
        return

    candidate = app_state.get("candidate_setup")
    if not candidate:
        return

    # --- State 1: Monitor for Entry Confirmation ---
    if candidate.get("status") == "Pending_Greek_Confirmation":
        # Calculate latest Greek features from buffers
        delta_slope = calculations.calculate_delta_slope(app_state["delta_buffer"])
        gamma_change_percent = calculations.calculate_gamma_change_percent(app_state["gamma_buffer"])
        iv_trend = calculations.calculate_iv_trend(app_state["iv_buffer"])

        settings = database.get_settings()
        # Run the confirmation logic
        confirmed_candidate = logic.confirm_with_greeks(candidate, delta_slope, gamma_change_percent, iv_trend, settings)

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
            app_state["candidate_setup"] = confirmed_candidate
        return

    # --- State 2: Monitor Active Trade for Exit ---
    if candidate.get("status") == "ENTRY_APPROVED":
        latest_premium = app_state["premium_buffer"][-1] if app_state["premium_buffer"] else 0
        exit_reason = logic.check_exit_conditions(candidate, latest_premium)

        if exit_reason:
            print(f"!!! EXIT CONDITION MET: {exit_reason} !!!")
            # Update the log with the exit reason
            db_updates = {"status": "CLOSED", "result": exit_reason}
            database.update_log_entry(candidate.get("log_id"), db_updates)

            # Clear the active signal and enter cooldown
            app_state["candidate_setup"] = None
            settings = database.get_settings()
            cooldown_minutes = int(settings.get('cooldown_minutes', 15))
            app_state["cooldown_until"] = now + datetime.timedelta(minutes=cooldown_minutes)
            print(f"Trade closed. Entering cooldown until {app_state['cooldown_until']}")


def process_5min_candle():
    """
    Forms a 5-minute candle from the price_buffer and stores it.
    """
    price_buffer = app_state["price_buffer"]
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
    app_state["candles_5min_buffer"].append(new_candle)
    print(f"New 5-min Candle created: {new_candle}")

def run_logic_controller():
    """
    Runs every 5 minutes to determine Bias and Market Type.
    """
    if app_state.get("cooldown_until") and datetime.datetime.now() < app_state.get("cooldown_until"):
        print("Logic controller skipped due to cooldown.")
        # Reset bias/market type during cooldown to avoid new signals
        app_state["bias"], app_state["market_type"] = "Neutral", "Undetermined"
        return
    # 1. Get all calculated features
    signals = get_signals()
    latest_price = app_state["price_buffer"][-1] if app_state["price_buffer"] else 0
    latest_premium = app_state["premium_buffer"][-1] if app_state["premium_buffer"] else 0

    # 2. Determine Bias
    bias = logic.determine_bias(
        swing_points=signals["swing_points"],
        latest_price=latest_price,
        ema_20=signals["ema_20"],
        delta_slope=signals["delta_slope"],
        gamma_change=signals["gamma_change_percent"],
        iv_trend=signals["iv_trend"]
    )
    app_state["bias"] = bias

    # 3. Determine Market Type
    settings = database.get_settings()
    market_type = logic.determine_market_type(
        atr=signals["atr_14"],
        body_ratio=signals["latest_candle_body_ratio"],
        delta_stability=signals["delta_stability"],
        gamma_change=signals["gamma_change_percent"],
        iv_trend=signals["iv_trend"],
        settings=settings
    )
    app_state["market_type"] = market_type

    # 4. Detect Entry Setup
    candidate = logic.detect_entry_setup(
        market_type=market_type,
        bias=bias,
        swing_points=signals["swing_points"],
        latest_price=latest_price,
        body_ratio=signals["latest_candle_body_ratio"],
        signal_premium=latest_premium
    )
    app_state["candidate_setup"] = candidate
    if candidate and candidate.get("status") == "Pending_Greek_Confirmation":
        # Log the initial detection of a candidate signal
        log_id = database.log_signal(candidate)
        if log_id:
            candidate["log_id"] = log_id
            app_state["candidate_setup"] = candidate
    print(f"Logic Controller Update: Bias={bias}, MarketType={market_type}, Candidate={candidate}")

@app.get("/")
def read_root():
    return {"message": "Greeks-Based Trading Tool Backend is running."}

@app.get("/profile")
def get_user_profile():
    """
    Fetches the user's profile from Upstox to test the access token.
    """
    access_token = app_state.get("access_token")
    if not access_token:
        return {"error": "User not authenticated. Please login first via /auth/login"}

    url = "https://api-v2.upstox.com/user/profile"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

@app.on_event("startup")
def startup_event():
    """
    Initializes and starts the background scheduler on application startup.
    """
    database.init_db() # Initialize the database
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_data, 'interval', seconds=10, id='data_fetch_job')
    scheduler.add_job(run_greek_confirmation, 'interval', seconds=10, start_date=datetime.datetime.now() + datetime.timedelta(seconds=10), id='greek_confirm_job')
    scheduler.add_job(process_5min_candle, 'cron', minute='*/5', second='5', id='candle_job') # Creates candle
    scheduler.add_job(run_logic_controller, 'cron', minute='*/5', second='10', id='logic_job') # Runs logic after candle
    scheduler.start(paused=True)
    app_state["scheduler"] = scheduler
    print("Background scheduler initialized in a paused state.")

@app.get("/latest-data")
def get_latest_data():
    """
    An endpoint to inspect the current content of our data buffers.
    """
    return {
        "prices": list(app_state["price_buffer"]),
        "deltas": list(app_state["delta_buffer"]),
        "gammas": list(app_state["gamma_buffer"]),
        "thetas": list(app_state["theta_buffer"]),
        "ivs": list(app_state["iv_buffer"]),
        "candles_5min": list(app_state["candles_5min_buffer"]),
    }

@app.get("/signals")
def get_signals():
    """
    An endpoint to calculate and display the current signals from the data.
    """
    # --- TEMPORARY DEBUGGING ---
    print(f"DEBUG: /signals called. Current delta_buffer: {list(app_state['delta_buffer'])}")

    delta_slope = calculations.calculate_delta_slope(app_state["delta_buffer"])
    gamma_change_percent = calculations.calculate_gamma_change_percent(app_state["gamma_buffer"])
    iv_trend = calculations.calculate_iv_trend(app_state["iv_buffer"])
    delta_stability = calculations.calculate_delta_stability(app_state["delta_buffer"])
    theta_change_percent = calculations.calculate_theta_change_percent(app_state["theta_buffer"])
    
    ema_20 = calculations.calculate_ema(app_state["candles_5min_buffer"])
    atr_14 = calculations.calculate_atr(app_state["candles_5min_buffer"])
    
    swing_points = calculations.find_swing_points(app_state["candles_5min_buffer"])
    body_ratio = calculations.calculate_body_ratio(app_state["candles_5min_buffer"])

    return {
        "delta_slope": delta_slope,
        "gamma_change_percent": gamma_change_percent,
        "iv_trend": iv_trend,
        "delta_stability": delta_stability,
        "theta_change_percent": theta_change_percent,
        "ema_20": ema_20,
        "atr_14": atr_14,
        "swing_points": swing_points,
        "latest_candle_body_ratio": body_ratio,
    }

@app.get("/status")
def get_system_status():
    """
    Returns the current system status (Bias and Market Type).
    """
    return {
        "bias": app_state.get("bias"),
        "market_type": app_state.get("market_type"),
        "candidate_setup": app_state.get("candidate_setup"),
    }

@app.get("/tradelogs")
def get_trade_logs():
    """
    Returns all historical trade logs from the database.
    """
    return database.get_all_logs()

@app.get("/option-chain")
def get_option_chain():
    """
    Returns the latest full option chain data.
    """
    # Return a copy to avoid potential mutation issues
    return list(app_state.get("option_chain_data", []))

@app.get("/settings")
def read_settings():
    """
    Returns the current strategy settings from the database.
    """
    return database.get_settings()

class SettingsUpdate(BaseModel):
    key: str
    value: str

@app.post("/settings")
def write_settings(settings_update: SettingsUpdate):
    database.update_setting(settings_update.key, settings_update.value)
    return {"status": "success", "key": settings_update.key, "value": settings_update.value}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to stream live data and system status to the frontend.
    """
    await websocket.accept()
    try:
        while True:
            # Gather the latest data from the application state
            nifty_price = app_state["price_buffer"][-1] if app_state["price_buffer"] else "Fetching..."
            delta = app_state["delta_buffer"][-1] if app_state["delta_buffer"] else "--"
            gamma = app_state["gamma_buffer"][-1] if app_state["gamma_buffer"] else "--"
            theta = app_state["theta_buffer"][-1] if app_state["theta_buffer"] else "--"
            iv = app_state["iv_buffer"][-1] if app_state["iv_buffer"] else "--"

            payload = {
                "nifty_price": f"{nifty_price:.2f}" if isinstance(nifty_price, float) else nifty_price,
                "delta": f"{delta:.4f}" if isinstance(delta, float) else delta,
                "gamma": f"{gamma:.4f}" if isinstance(gamma, float) else gamma,
                "theta": f"{theta:.4f}" if isinstance(theta, float) else theta,
                "iv": f"{iv:.4f}" if isinstance(iv, float) else iv,
                "bias": app_state.get("bias", "Neutral"),
                "market_type": app_state.get("market_type", "Undetermined"),
                "candidate_setup": app_state.get("candidate_setup"),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2)  # Send updates every 2 seconds
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        print("Client disconnected from WebSocket.")