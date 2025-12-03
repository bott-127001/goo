from collections import deque
import copy

BUFFER_SIZE = 30 

def get_default_user_state():
    """Returns a new, default state structure for a single user."""
    return {
        "access_token": None,
        "scheduler": None,
        "price_buffer": deque(maxlen=BUFFER_SIZE),
        "premium_buffer": deque(maxlen=BUFFER_SIZE),
        "delta_buffer": deque(maxlen=BUFFER_SIZE),
        "gamma_buffer": deque(maxlen=BUFFER_SIZE),
        "theta_buffer": deque(maxlen=BUFFER_SIZE),
        "iv_buffer": deque(maxlen=BUFFER_SIZE),
        "candles_5min_buffer": deque(maxlen=100),
        "bias": "Neutral",
        "market_type": "Undetermined",
        "candidate_setup": None,
        "cooldown_until": None,
        # --- New state fields for refined strategy ---
        "login_timestamp": None,          # To track when the session started
        "baseline_set": False,            # Flag to check if baseline is captured
        "baseline_timestamp": None,       # The exact time baseline was captured
        "baseline_values": {},            # Dict to hold Price, Delta, Gamma, IV at baseline
        "market_type_window_size": 3,     # Default to 3 (15-min window)
        "option_chain_data": [],          # To store the full option chain for the UI
        # --- New state for BOS/Retest Engine ---
        "price_action_state": {
            "status": "LOOKING_FOR_BOS",        # Current mode: LOOKING_FOR_BOS or LOOKING_FOR_RETEST
            "last_bos_type": None,             # 'BULLISH' or 'BEARISH'
            "breakout_high": None,             # The high of the move that caused the BOS
            "breakout_low": None,              # The low of the move that caused the BOS
            "breakout_candle_timestamp": None, # To avoid re-triggering on the same candle
        },
    }

# The global state now holds a dictionary of user-specific states.
app_state = {
    "users": {
        # "samarth": get_default_user_state(),
        # "prajwal": get_default_user_state(),
    }
}

def get_user_state(user_name: str):
    """
    Retrieves the state for a specific user, creating it if it doesn't exist.
    """
    if user_name not in app_state["users"]:
        # Use a deep copy to ensure deques are new instances for each user
        app_state["users"][user_name] = get_default_user_state()
    return app_state["users"][user_name]