import datetime
from . import calculations # Assuming calculations.py will be updated with new functions

def determine_bias(current_price: float, current_delta: float, current_gamma: float, current_iv: float, baseline_values: dict) -> str:
    """
    Determines the market bias based on comparing current values to a delayed baseline.
    This provides a stable, "theme of the day" bias.
    Rule: 3 out of 4 conditions must be true for a Bullish/Bearish bias.
    """
    if not baseline_values or not all([v is not None for v in [current_price, current_delta, current_gamma, current_iv]]):
        return "Neutral"

    # --- Calculate differences from the baseline ---
    price_from_baseline = current_price - baseline_values.get("price", current_price)
    delta_from_baseline = current_delta - baseline_values.get("delta", current_delta)
    gamma_from_baseline = current_gamma - baseline_values.get("gamma", current_gamma)
    iv_from_baseline = current_iv - baseline_values.get("iv", current_iv)

    # --- Bullish Bias Check ---
    # For a bullish bias, we expect price, delta, and gamma to rise. IV can be stable or rising.
    bullish_conditions = [
        price_from_baseline > 0,
        delta_from_baseline > 0,
        gamma_from_baseline > 0,
        iv_from_baseline >= -0.5 # Allow for minor IV drops
    ]
    if sum(bullish_conditions) >= 3:
        return "Bullish"

    # --- Bearish Bias Check (Inverse Conditions) ---
    # For a bearish bias, we expect price and delta to fall, but gamma and IV (fear) to rise.
    bearish_conditions = [
        price_from_baseline < 0,
        delta_from_baseline < 0,
        gamma_from_baseline > 0, # Gamma rises with volatility
        iv_from_baseline > 0.5   # IV (fear) rises
    ]
    if sum(bearish_conditions) >= 3:
        return "Bearish"

    # --- Neutral Bias ---
    return "Neutral"

def determine_market_type(candles_5min_buffer: list, market_type_window_size: int, settings: dict) -> str:
    """
    Determines the market type based on a configurable lookback window.
    """
    if len(candles_5min_buffer) < market_type_window_size:
        return "Undetermined"

    # These will call new/updated functions in calculations.py
    atr = calculations.calculate_atr(candles_5min_buffer, period=market_type_window_size)
    body_ratio_avg = calculations.calculate_average_body_ratio(candles_5min_buffer, window_size=market_type_window_size)
    # We'll need to add these calculations later
    # delta_stability = calculations.calculate_delta_stability(delta_buffer, window_size=market_type_window_size)
    # gamma_change = calculations.calculate_gamma_change_percent(gamma_buffer, num_updates=market_type_window_size * 30) # 30 updates per 5min candle
    # iv_trend = calculations.calculate_iv_trend(iv_buffer, num_updates=market_type_window_size * 30)

    # --- Trendy Market Check ---
    # Placeholder logic until all calculations are in place
    trendy_conditions = [
        atr > 15, # Example: ATR is expanding
        body_ratio_avg > 0.5, # Example: Candles have strong bodies
    ]
    if sum(trendy_conditions) >= 2:
        return "Trendy"

    # --- Volatile Market Check ---
    volatile_conditions = [
        atr > 25, # Example: ATR is very high
        body_ratio_avg < 0.4, # Example: Candles are indecisive (long wicks)
    ]
    if sum(volatile_conditions) >= 2:
        return "Volatile"

    return "Neutral" # Default if no other type is met

def detect_entry_setup(bias: str, market_type: str, candles_5min_buffer: list, latest_price: float, signal_premium: float, price_action_state: dict, settings: dict) -> dict | None:
    """
    The new "Four-Layer Entry Engine".
    Manages the price action state and detects trade setups.
    Returns a dictionary for a trade setup, a state update, or None.
    """
    # --- Layer 1: Bias Check ---
    if bias == "Neutral":
        return {"action": "reset_state"} # If bias is neutral, reset any pending price action state

    # --- Layer 2: Market Type Check ---
    if market_type not in ["Trendy", "Volatile"]:
        return None

    # --- Layer 3: Price Setup (BOS/Retest) ---
    if price_action_state.get("status") == "LOOKING_FOR_BOS":
        bos_result = None
        if bias == "Bullish":
            bos_result = calculations.check_bullish_bos(candles_5min_buffer, settings, price_action_state)
        elif bias == "Bearish":
            bos_result = calculations.check_bearish_bos(candles_5min_buffer, settings, price_action_state)

        if bos_result:
            # A Break of Structure was found. Now decide what to do.
            if market_type == "Volatile":
                # In a volatile market, enter immediately on the BOS.
                return {
                    "action": "trade_setup",
                    "setup": {
                        "type": bos_result["type"],
                        "price": latest_price,
                        "status": "Pending_Greek_Confirmation",
                        "signal_premium": signal_premium,
                    }
                }
            elif market_type == "Trendy":
                # In a trendy market, don't trade yet. Update state to look for a retest.
                return {
                    "action": "update_state",
                    "new_state": {
                        "status": "LOOKING_FOR_RETEST",
                        "last_bos_type": "BULLISH" if "BULLISH" in bos_result["type"] else "BEARISH",
                        "breakout_high": bos_result["breakout_high"],
                        "breakout_low": bos_result["breakout_low"],
                        "breakout_candle_timestamp": bos_result["breakout_candle_timestamp"],
                    }
                }

    elif price_action_state.get("status") == "LOOKING_FOR_RETEST":
        retest_result = None
        if price_action_state.get("last_bos_type") == "BULLISH" and bias == "Bullish":
            retest_result = calculations.check_bullish_retest(latest_price, price_action_state, settings)
        elif price_action_state.get("last_bos_type") == "BEARISH" and bias == "Bearish":
            retest_result = calculations.check_bearish_retest(latest_price, price_action_state, settings)

        if retest_result:
            if retest_result.get("type") == "INVALIDATED":
                # The retest failed (e.g., pullback was too deep). Reset the state.
                return {"action": "reset_state"}
            else:
                # A valid retest was found. This is our trade signal.
                return {
                    "action": "trade_setup",
                    "setup": {
                        "type": retest_result["type"], # e.g., "RETEST_BULLISH"
                        "price": latest_price,
                        "status": "Pending_Greek_Confirmation",
                        "signal_premium": signal_premium,
                    }
                }

    return None # No action needed

def confirm_with_greeks(candidate: dict, smoothed_greeks: dict, settings: dict) -> dict | None:
    """
    Confirms a pending setup with live SMOOTHED Greek data.
    """
    if not candidate or candidate.get("status") != "Pending_Greek_Confirmation":
        return None

    # Get thresholds from settings, with defaults
    delta_thresh = float(settings.get('entry_delta_slope_thresh', 0.01))
    gamma_thresh = float(settings.get('entry_gamma_change_thresh', 5.0))
    iv_thresh = float(settings.get('entry_iv_trend_thresh', 0.5))
    theta_thresh = float(settings.get('entry_theta_max_spike', 5.0))

    # Get smoothed values
    delta_slope = smoothed_greeks.get("delta_slope", 0.0)
    gamma_change = smoothed_greeks.get("gamma_change", 0.0)
    iv_trend = smoothed_greeks.get("iv_trend", 0.0)
    theta_change = smoothed_greeks.get("theta_change", 0.0)

    # Check conditions based on trade direction
    is_confirmed = False
    if "BULLISH" in candidate["type"]:
        # For bullish, we want positive delta slope, positive gamma change, and positive IV trend.
        # We also want to ensure theta decay isn't spiking against us.
        if (delta_slope >= delta_thresh and gamma_change >= gamma_thresh and iv_trend >= iv_thresh and abs(theta_change) < theta_thresh):
            is_confirmed = True
    elif "BEARISH" in candidate["type"]:
        # For bearish, we want negative delta slope, but still positive gamma and IV expansion.
        if (delta_slope <= -delta_thresh and gamma_change >= gamma_thresh and iv_trend >= iv_thresh and abs(theta_change) < theta_thresh):
            is_confirmed = True

    if is_confirmed:
        candidate["status"] = "ENTRY_APPROVED"
        print(f"!!! GREEK CONFIRMATION PASSED: {candidate['type']} at {candidate['price']} !!!")
        return candidate

    return None # Not confirmed yet

def check_exit_conditions(active_trade: dict, latest_premium: float, smoothed_greeks: dict, settings: dict) -> str | None:
    """
    Checks if an active trade should be exited based on SL/Target or Greek conditions.
    """
    if not latest_premium:
        return None
    
    # --- Price-Based Exits ---
    if latest_premium <= active_trade.get('stop_loss', 0):
        return f"StopLoss Hit at {latest_premium}"
    if latest_premium >= active_trade.get('target', float('inf')):
        return f"Target Hit at {latest_premium}"
    
    # --- Emergency Greek-Based Exit ---
    # This will use the new smoothed greeks and settings.
    iv_crush_thresh = float(settings.get('exit_iv_crush_thresh', -2.0))
    smoothed_iv_trend = smoothed_greeks.get("iv_trend", 0.0)

    if smoothed_iv_trend < iv_crush_thresh:
        return f"Emergency Exit: IV Crush (Trend: {smoothed_iv_trend:.2f})"

    # --- Time-Based Exit ---
    eod_exit_minutes = int(settings.get('eod_exit_minutes', 60))
    # Market close is 10:00 AM UTC (3:30 PM IST)
    market_close_time_utc = datetime.time(10, 0)
    # Calculate the time when the EOD exit should trigger
    exit_trigger_time = (datetime.datetime.combine(datetime.date.today(), market_close_time_utc) - datetime.timedelta(minutes=eod_exit_minutes)).time()
    
    now_utc_time = datetime.datetime.utcnow().time()
    if now_utc_time >= exit_trigger_time:
        return "Time-based Exit (EOD)"

    return None