from collections import deque

# A simple in-memory dictionary to hold the application state.
# For a single-user app, this is sufficient to store the access token.

# Define the maximum size of our rolling buffers (e.g., last 5 minutes of data at 10s intervals)
BUFFER_SIZE = 30 

app_state = {
    "access_token": None,
    "scheduler": None, # To hold the background scheduler instance
    
    # Rolling buffers for live data
    "price_buffer": deque(maxlen=BUFFER_SIZE),
    "premium_buffer": deque(maxlen=BUFFER_SIZE), # Add this line
    "delta_buffer": deque(maxlen=BUFFER_SIZE),
    "gamma_buffer": deque(maxlen=BUFFER_SIZE),
    "theta_buffer": deque(maxlen=BUFFER_SIZE),
    "iv_buffer": deque(maxlen=BUFFER_SIZE),

    # Buffer for 5-minute candles [timestamp, open, high, low, close]
    "candles_5min_buffer": deque(maxlen=100), # Store last 100 5-min candles

    # System Status
    "bias": "Neutral",
    "market_type": "Undetermined",

    # Candidate Setup
    "candidate_setup": None, # e.g., {"type": "Breakout_Bullish", "price": 22500, "status": "Pending"}

    # Cooldown period after a trade is closed
    "cooldown_until": None,
}