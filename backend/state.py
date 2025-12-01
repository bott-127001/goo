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