from collections import deque
import numpy as np
import pandas as pd

# --- New Smoothed Greek Calculation Functions ---

def calculate_smoothed_slope(buffer: deque, window_seconds: int) -> float:
    """
    Generic function to calculate the slope of a value in a buffer over a time window.
    Assumes data is captured every 10 seconds.
    """
    num_updates = window_seconds // 10
    if len(buffer) < num_updates:
        return 0.0

    recent_values = list(buffer)[-num_updates:]
    if any(v is None for v in recent_values):
        return 0.0

    latest_val = recent_values[-1]
    earliest_val = recent_values[0]

    slope = (latest_val - earliest_val) / num_updates
    return slope

def calculate_smoothed_percent_change(buffer: deque, window_seconds: int) -> float:
    """
    Generic function to calculate the percentage change of a value in a buffer over a time window.
    Assumes data is captured every 10 seconds.
    """
    num_updates = window_seconds // 10
    if len(buffer) < num_updates:
        return 0.0

    recent_values = list(buffer)[-num_updates:]
    if any(v is None for v in recent_values):
        return 0.0

    latest_val = recent_values[-1]
    earliest_val = recent_values[0]

    if earliest_val == 0:
        return 0.0

    change_percent = ((latest_val - earliest_val) / earliest_val) * 100
    return change_percent


def calculate_delta_slope(delta_buffer: deque, num_updates: int = 5) -> float:
    """
    Calculates the slope of delta over the last few updates.
    Formula: DeltaSlope = (D_latest - D_earliest) / number_of_updates
    """
    # Ensure we have enough data points and no None values in the slice
    if len(delta_buffer) < num_updates:
        return 0.0

    recent_deltas = list(delta_buffer)[-num_updates:]
    if any(d is None for d in recent_deltas):
        return 0.0

    # D5 is the latest, D1 is the earliest in the window
    d5 = recent_deltas[-1]
    d1 = recent_deltas[0]

    slope = (d5 - d1) / num_updates
    return slope

def calculate_gamma_change_percent(gamma_buffer: deque, num_updates: int = 5) -> float:
    """
    Calculates the percentage change in gamma over the last few updates.
    Formula: GammaChange = ((Gamma_latest - Gamma_previous) / Gamma_previous) * 100
    """
    if len(gamma_buffer) < num_updates:
        return 0.0

    recent_gammas = list(gamma_buffer)[-num_updates:]
    if any(g is None for g in recent_gammas):
        return 0.0

    gamma_latest = recent_gammas[-1]
    gamma_previous = recent_gammas[0]

    if gamma_previous == 0: # Avoid division by zero
        return 0.0

    change_percent = ((gamma_latest - gamma_previous) / gamma_previous) * 100
    return change_percent

def calculate_iv_trend(iv_buffer: deque, num_updates: int = 3) -> float:
    """
    Calculates the trend of IV over the last few updates.
    Formula: IVTrend = IV_latest - IV_earliest
    """
    if len(iv_buffer) < num_updates:
        return 0.0

    recent_ivs = list(iv_buffer)[-num_updates:]
    if any(iv is None for iv in recent_ivs):
        return 0.0

    iv_latest = recent_ivs[-1]
    iv_earliest = recent_ivs[0]

    trend = iv_latest - iv_earliest
    return trend

def calculate_delta_stability(delta_buffer: deque, num_updates: int = 5) -> float:
    """
    Measures the stability (volatility) of delta using standard deviation.
    """
    if len(delta_buffer) < num_updates:
        return 0.0

    recent_deltas = list(delta_buffer)[-num_updates:]
    if any(d is None for d in recent_deltas):
        return 0.0

    stability = np.std(recent_deltas)
    return stability

def calculate_theta_change_percent(theta_buffer: deque, num_updates: int = 5) -> float:
    """
    Calculates the percentage change in theta.
    """
    if len(theta_buffer) < num_updates:
        return 0.0
    
    recent_thetas = list(theta_buffer)[-num_updates:]
    if any(t is None for t in recent_thetas):
        return 0.0

    theta_now = recent_thetas[-1]
    theta_prev = recent_thetas[0]

    if theta_prev == 0:
        return 0.0

    change_percent = ((theta_now - theta_prev) / theta_prev) * 100
    return change_percent

def calculate_ema(candles_5min: deque, period: int = 20) -> float:
    """
    Calculates the 20-period Exponential Moving Average from 5-min candles.
    """
    if len(candles_5min) < period:
        return 0.0

    # Create a pandas DataFrame from the candle data
    df = pd.DataFrame(list(candles_5min), columns=['timestamp', 'open', 'high', 'low', 'close'])
    
    # Calculate EMA on the 'close' price series
    ema = df['close'].ewm(span=period, adjust=False).mean()
    
    # Return the latest EMA value
    return ema.iloc[-1]

def calculate_atr(candles_5min: deque, period: int = 14) -> float:
    """
    Calculates the 14-period Average True Range from 5-min candles.
    """
    if len(candles_5min) < period:
        return 0.0

    df = pd.DataFrame(list(candles_5min), columns=['timestamp', 'open', 'high', 'low', 'close'])
    
    # Calculate True Range (TR)
    high_low = df['high'] - df['low']
    high_prev_close = abs(df['high'] - df['close'].shift(1))
    low_prev_close = abs(df['low'] - df['close'].shift(1))
    
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    
    # Calculate ATR as the simple moving average of TR for the specified period
    atr = tr.rolling(window=period).mean()

    # Return the latest ATR value
    if not atr.empty and not pd.isna(atr.iloc[-1]):
        return atr.iloc[-1]
    return 0.0

def find_swing_points(candles_5min: deque) -> list:
    """
    Identifies swing highs and lows from a list of candles.
    Swing High: high[n] > high[n-1] AND high[n] > high[n+1]
    Swing Low:  low[n] < low[n-1] AND low[n] < low[n+1]
    """
    if len(candles_5min) < 3:
        return []

    df = pd.DataFrame(list(candles_5min), columns=['timestamp', 'open', 'high', 'low', 'close'])
    swing_points = []

    # Iterate from the second to the second-to-last candle
    for i in range(1, len(df) - 1):
        # Check for Swing High
        if df['high'].iloc[i] > df['high'].iloc[i-1] and df['high'].iloc[i] > df['high'].iloc[i+1]:
            swing_points.append({
                "type": "high", "price": df['high'].iloc[i], "timestamp": df['timestamp'].iloc[i]
            })
        # Check for Swing Low
        if df['low'].iloc[i] < df['low'].iloc[i-1] and df['low'].iloc[i] < df['low'].iloc[i+1]:
            swing_points.append({
                "type": "low", "price": df['low'].iloc[i], "timestamp": df['timestamp'].iloc[i]
            })
            
    return swing_points

def calculate_body_ratio(candles_5min: deque) -> float:
    """
    Calculates the body-to-range ratio for the most recent candle.
    """
    if not candles_5min:
        return 0.0
    
    latest_candle = candles_5min[-1]
    _timestamp, candle_open, candle_high, candle_low, candle_close = latest_candle
    
    body = abs(candle_close - candle_open)
    rng = candle_high - candle_low
    
    return body / rng if rng > 0 else 0.0

def calculate_average_body_ratio(candles_5min: deque, window_size: int) -> float:
    """
    Calculates the average body-to-range ratio over the last N candles.
    """
    if len(candles_5min) < window_size:
        return 0.0
    
    recent_candles = list(candles_5min)[-window_size:]
    ratios = []
    for candle in recent_candles:
        _timestamp, candle_open, candle_high, candle_low, candle_close = candle
        body = abs(candle_close - candle_open)
        rng = candle_high - candle_low
        ratio = body / rng if rng > 0 else 0.0
        ratios.append(ratio)
    
    return sum(ratios) / len(ratios) if ratios else 0.0

# --- New Price Action (BOS/Retest) Functions ---
# These are placeholders. The actual implementation will be more complex and stateful.

def check_bullish_bos(candles_5min_buffer: list, settings: dict) -> dict | None:
    """
    Checks for a Bullish Break of Structure.
    Placeholder: In a real scenario, this would need more robust logic.
    """
    # This is a simplified placeholder.
    # A real implementation would need to manage the state of the last BOS.
    return None

def check_bearish_bos(candles_5min_buffer: list, settings: dict) -> dict | None:
    """
    Checks for a Bearish Break of Structure.
    Placeholder.
    """
    return None

def check_bullish_retest(candles_5min_buffer: list, last_bos_info: dict, settings: dict) -> dict | None:
    """
    Checks for a valid Bullish Retest after a BOS.
    Placeholder.
    """
    return None

def check_bearish_retest(candles_5min_buffer: list, last_bos_info: dict, settings: dict) -> dict | None:
    """
    Checks for a valid Bearish Retest after a BOS.
    Placeholder.
    """
    return None