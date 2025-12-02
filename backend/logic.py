def determine_bias(swing_points: list, latest_price: float, ema_20: float, delta_slope: float, gamma_change: float, iv_trend: float) -> str:
    """
    Determines the market bias based on a set of rules.
    Rule: 4 out of 6 conditions must be true for a Bullish/Bearish bias.
    """
    if not all([swing_points, latest_price, ema_20]):
        return "Neutral"

    # --- Price Rules ---
    swing_highs = sorted([p['price'] for p in swing_points if p['type'] == 'high'], reverse=True)
    swing_lows = sorted([p['price'] for p in swing_points if p['type'] == 'low'], reverse=True)

    # 1. Higher Highs (HH)
    is_hh = len(swing_highs) >= 3 and swing_highs[0] > swing_highs[1] > swing_highs[2]
    # 2. Higher Lows (HL)
    is_hl = len(swing_lows) >= 3 and swing_lows[0] > swing_lows[1] > swing_lows[2]
    # 3. Price vs EMA
    price_above_ema = latest_price > ema_20

    # --- Greek Rules ---
    # 4. Delta Slope
    delta_rising = delta_slope >= 0.01
    # 5. Gamma Change
    gamma_rising = gamma_change >= 5.0
    # 6. IV Trend
    iv_stable_or_rising = iv_trend >= 0.0

    # --- Bullish Bias Check ---
    bullish_conditions = [is_hh, is_hl, price_above_ema, delta_rising, gamma_rising, iv_stable_or_rising]
    if sum(bullish_conditions) >= 4:
        return "Bullish"

    # --- Bearish Bias Check (Inverse Conditions) ---
    is_lh = len(swing_highs) >= 3 and swing_highs[0] < swing_highs[1] < swing_highs[2]
    is_ll = len(swing_lows) >= 3 and swing_lows[0] < swing_lows[1] < swing_lows[2]
    price_below_ema = latest_price < ema_20
    delta_falling = delta_slope <= -0.01
    gamma_falling = gamma_change <= -5.0
    iv_stable_or_falling = iv_trend <= 0.0

    bearish_conditions = [is_lh, is_ll, price_below_ema, delta_falling, gamma_falling, iv_stable_or_falling]
    if sum(bearish_conditions) >= 4:
        return "Bearish"

    # --- Neutral Bias ---
    return "Neutral"

import datetime

def determine_market_type(atr: float, body_ratio: float, delta_stability: float, gamma_change: float, iv_trend: float, settings: dict) -> str:
    """
    Determines the market type based on a set of rules.
    Rule: 3+ conditions must be true for a given market type.
    """
    # Get thresholds from settings
    atr_neutral_max = float(settings.get('atr_neutral_max', 10))
    atr_trendy_min = float(settings.get('atr_trendy_min', 10))
    atr_trendy_max = float(settings.get('atr_trendy_max', 18))

    # --- Trendy Market Check ---
    trendy_conditions = [
        atr_trendy_min <= atr <= atr_trendy_max,
        body_ratio >= 0.6,
        delta_stability < 0.015,
        gamma_change >= 3.0,
        iv_trend >= 0.0 # Stable or rising
    ]
    if sum(trendy_conditions) >= 3:
        return "Trendy"

    # --- Volatile Market Check ---
    # Volatile is defined as ATR being above the trendy max
    volatile_conditions = [
        atr > atr_trendy_max,
        0.3 <= body_ratio < 0.6, # Unstable
        delta_stability > 0.040,
        gamma_change > 10.0,
        iv_trend > 2.0
    ]
    if sum(volatile_conditions) >= 3:
        return "Volatile"

    # --- Neutral/Sideways Market Check ---
    # Neutral is defined as ATR being below the neutral max
    neutral_conditions = [
        atr < atr_neutral_max,
        -0.005 < delta_stability < 0.005, # Using stability as proxy for flat delta
        abs(gamma_change) < 2.0,
        iv_trend <= 0.0 # Stable or dropping
    ]
    if sum(neutral_conditions) >= 3:
        return "Neutral"

    return "Undetermined"

def detect_entry_setup(market_type: str, bias: str, swing_points: list, latest_price: float, body_ratio: float, signal_premium: float) -> dict | None:
    """
    Detects a price-based entry setup based on the current market type and bias.
    For now, focuses on the Breakout setup for Volatile markets.
    """
    # Guard clause: Only look for entries if bias and market type are favorable.
    if bias == "Neutral" or market_type not in ["Trendy", "Volatile"] or not signal_premium:
        return None

    last_swing_high = max([p['price'] for p in swing_points if p['type'] == 'high'], default=None)
    last_swing_low = min([p['price'] for p in swing_points if p['type'] == 'low'], default=None)

    # --- Continuation Entry Logic (for Trendy Market) ---
    if market_type == "Trendy":
        # Bullish Continuation: In a bullish trend, we look for a pullback that respects the structure.
        if bias == "Bullish" and last_swing_low:
            # Price Rule: Price has pulled back but has not closed below the last swing low.
            if latest_price > last_swing_low:
                return {
                    "type": "Continuation_Bullish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }
        # Bearish Continuation: In a bearish trend, we look for a pullback that respects the structure.
        if bias == "Bearish" and last_swing_high:
            # Price Rule: Price has pulled back but has not closed above the last swing high.
            if latest_price < last_swing_high:
                return {
                    "type": "Continuation_Bearish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }

    # --- Breakout Entry Logic (for Volatile Market) ---
    if market_type == "Volatile":
        # Bullish Breakout
        if bias == "Bullish" and last_swing_high:
            # Rule: Price breaks swing high by >= 0.15%
            breakout_threshold = last_swing_high * 1.0015
            # Rule: Breakout candle is large (body >= 60% of range)
            is_large_candle = body_ratio >= 0.6

            if latest_price > breakout_threshold and is_large_candle:
                return {
                    "type": "Breakout_Bullish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }

        # Bearish Breakout
        if bias == "Bearish" and last_swing_low:
            # Rule: Price breaks swing low by >= 0.15%
            breakout_threshold = last_swing_low * 0.9985
            # Rule: Breakout candle is large (body >= 60% of range)
            is_large_candle = body_ratio >= 0.6

            if latest_price < breakout_threshold and is_large_candle:
                return {
                    "type": "Breakout_Bearish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }

        # --- Reversal Entry Logic (also for Volatile Market) ---
        # Bullish Reversal: Price rejects a key low and shows reversal signs.
        if bias == "Bullish" and last_swing_low:
            # Price Rule: Price is near the last swing low, suggesting a test of support.
            is_near_low = abs(latest_price - last_swing_low) / last_swing_low < 0.001 # within 0.1%
            # Candle Rule: A small body ratio can indicate a reversal candle (like a pin bar).
            is_reversal_candle = body_ratio < 0.3

            if is_near_low and is_reversal_candle:
                return {
                    "type": "Reversal_Bullish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }

        # Bearish Reversal: Price rejects a key high and shows reversal signs.
        if bias == "Bearish" and last_swing_high:
            is_near_high = abs(latest_price - last_swing_high) / last_swing_high < 0.001 # within 0.1%
            is_reversal_candle = body_ratio < 0.3

            if is_near_high and is_reversal_candle:
                return {
                    "type": "Reversal_Bearish",
                    "price": latest_price,
                    "status": "Pending_Greek_Confirmation",
                    "signal_premium": signal_premium
                }
    return None

def confirm_with_greeks(candidate: dict, delta_slope: float, gamma_change: float, iv_trend: float, theta_change: float, settings: dict) -> dict:
    """
    Confirms a pending setup with live Greek data.
    """
    if not candidate or candidate.get("status") != "Pending_Greek_Confirmation":
        return candidate

    # --- Continuation Confirmation Rules ---
    if "Continuation" in candidate["type"]:
        # Get thresholds from settings
        min_conditions = int(settings.get('cont_conditions_met', 2))
        delta_thresh = float(settings.get('cont_delta_thresh', 0.01))
        gamma_thresh = float(settings.get('cont_gamma_thresh', 3.0))
        iv_thresh = float(settings.get('cont_iv_thresh', 0.0))
        theta_thresh = float(settings.get('cont_theta_thresh', 5.0))

        conditions_met = 0
        if candidate["type"] == "Continuation_Bullish":
            if delta_slope >= delta_thresh: conditions_met += 1
            if gamma_change >= gamma_thresh: conditions_met += 1
            if iv_trend >= iv_thresh: conditions_met += 1
            if theta_change < theta_thresh: conditions_met += 1
        elif candidate["type"] == "Continuation_Bearish":
            if delta_slope <= -delta_thresh: conditions_met += 1
            if gamma_change >= gamma_thresh: conditions_met += 1 # Gamma expansion is good for both
            if iv_trend >= iv_thresh: conditions_met += 1
            if theta_change < theta_thresh: conditions_met += 1

        if conditions_met >= min_conditions:
            candidate["status"] = "ENTRY_APPROVED"
            print(f"!!! ENTRY APPROVED: {candidate['type']} at {candidate['price']} !!!")

    # --- Reversal Confirmation Rules ---
    if "Reversal" in candidate["type"]:
        min_conditions = int(settings.get('rev_conditions_met', 2))
        delta_flip_thresh = float(settings.get('rev_delta_flip_thresh', 0.02))
        gamma_drop_thresh = float(settings.get('rev_gamma_drop_thresh', -5.0))
        iv_drop_thresh = float(settings.get('rev_iv_drop_thresh', -1.0))

        conditions_met = 0
        # For a bullish reversal, we expect bearish momentum to die.
        # So, we look for the delta slope to flip from negative to positive.
        if candidate["type"] == "Reversal_Bullish":
            if delta_slope >= delta_flip_thresh: conditions_met += 1 # Delta has flipped to positive
            if gamma_change <= gamma_drop_thresh: conditions_met += 1 # Gamma momentum drops
            if iv_trend <= iv_drop_thresh: conditions_met += 1 # IV (fear) is dropping
        # For a bearish reversal, we expect bullish momentum to die.
        elif candidate["type"] == "Reversal_Bearish":
            if delta_slope <= -delta_flip_thresh: conditions_met += 1 # Delta has flipped to negative
            if gamma_change <= gamma_drop_thresh: conditions_met += 1 # Gamma momentum drops
            if iv_trend <= iv_drop_thresh: conditions_met += 1 # IV (greed) is dropping

        if conditions_met >= min_conditions:
            candidate["status"] = "ENTRY_APPROVED"
            print(f"!!! ENTRY APPROVED: {candidate['type']} at {candidate['price']} !!!")

    # --- Breakout Confirmation Rules ---
    if "Breakout" in candidate["type"]:
        # Get thresholds from settings
        min_conditions = int(settings.get('confirm_conditions_met', 2))
        delta_thresh = float(settings.get('confirm_delta_slope', 0.02))
        gamma_thresh = float(settings.get('confirm_gamma_change', 8.0))
        iv_thresh = float(settings.get('confirm_iv_trend', 1.0))

        conditions_met = 0
        if candidate["type"] == "Breakout_Bullish":
            if delta_slope >= delta_thresh: conditions_met += 1
            if gamma_change >= gamma_thresh: conditions_met += 1
            if iv_trend >= iv_thresh: conditions_met += 1
        elif candidate["type"] == "Breakout_Bearish":
            if delta_slope <= -delta_thresh: conditions_met += 1
            if gamma_change >= gamma_thresh: conditions_met += 1 # Gamma should still expand
            if iv_trend >= iv_thresh: conditions_met += 1

        if conditions_met >= min_conditions:
            candidate["status"] = "ENTRY_APPROVED"
            print(f"!!! ENTRY APPROVED: {candidate['type']} at {candidate['price']} !!!")
        else:
            # Optional: Add a counter or timeout to cancel the candidate if not confirmed
            # For now, it just remains pending.
            pass

    return candidate

def check_exit_conditions(active_trade: dict, latest_premium: float, delta_slope: float, gamma_change: float, iv_trend: float, settings: dict) -> str | None:
    """
    Checks if an active trade should be exited based on SL/Target or Greek conditions.
    
    Args:
        active_trade (dict): The active trade object with 'stop_loss' and 'target'.
        latest_premium (float): The current market price of the option.
        delta_slope (float): The current slope of delta.
        gamma_change (float): The current percentage change in gamma.
        iv_trend (float): The current trend of implied volatility.
        settings (dict): The application settings.

    Returns:
        str: A string describing the exit reason, or None if no exit condition is met.
    """
    if not latest_premium:
        return None
    
    # --- Price-Based Exits ---
    if latest_premium <= active_trade.get('stop_loss', 0):
        return f"StopLoss Hit at {latest_premium}"
    if latest_premium >= active_trade.get('target', float('inf')):
        return f"Target Hit at {latest_premium}"
    
    # --- Greek-Based Exits ---
    delta_flip_thresh = float(settings.get('exit_delta_flip_thresh', 0.02))
    gamma_drop_thresh = float(settings.get('exit_gamma_drop_thresh', -5.0))
    iv_crush_thresh = float(settings.get('exit_iv_crush_thresh', -1.5))

    trade_type = active_trade.get("type", "")

    # Delta Reversal Check
    if "Bullish" in trade_type and delta_slope < -delta_flip_thresh:
        return "Greek Exit: Delta Reversal"
    if "Bearish" in trade_type and delta_slope > delta_flip_thresh:
        return "Greek Exit: Delta Reversal"

    # Gamma Drop and IV Crush Checks
    if gamma_change < gamma_drop_thresh:
        return "Greek Exit: Gamma Drop"
    if iv_trend < iv_crush_thresh:
        return "Greek Exit: IV Crush"

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