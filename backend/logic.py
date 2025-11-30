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
    if bias == "Neutral" or market_type != "Volatile" or not signal_premium:
        return None

    last_swing_high = max([p['price'] for p in swing_points if p['type'] == 'high'], default=None)
    last_swing_low = min([p['price'] for p in swing_points if p['type'] == 'low'], default=None)

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

    return None

def confirm_with_greeks(candidate: dict, delta_slope: float, gamma_change: float, iv_trend: float, settings: dict) -> dict:
    """
    Confirms a pending setup with live Greek data.
    """
    if not candidate or candidate.get("status") != "Pending_Greek_Confirmation":
        return candidate

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

def check_exit_conditions(active_trade: dict, latest_premium: float) -> str | None:
    """
    Checks if an active trade should be exited based on SL or Target.
    
    Args:
        active_trade (dict): The active trade object with 'stop_loss' and 'target'.
        latest_premium (float): The current market price of the option.

    Returns:
        str: A string describing the exit reason, or None if no exit condition is met.
    """
    if not latest_premium:
        return None
        
    if latest_premium <= active_trade.get('stop_loss', 0):
        return f"StopLoss Hit at {latest_premium}"
    if latest_premium >= active_trade.get('target', float('inf')):
        return f"Target Hit at {latest_premium}"
    
    return None