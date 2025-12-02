import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import './Signals.css';

const Signals = () => {
  const [status, setStatus] = useState(null);
  const [signals, setSignals] = useState(null);
  const location = useLocation();

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const userName = searchParams.get('user');

    if (!userName) {
      console.error("User not found in URL for Signals page.");
      return;
    }

    const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
    const fetchData = async () => {
      try {
        const [statusRes, signalsRes] = await Promise.all([
          fetch(`${apiBaseUrl}/status`),
          fetch(`${apiBaseUrl}/signals?user_name=${userName}`),
        ]);
        const statusData = await statusRes.json();
        const signalsData = await signalsRes.json();
        // Extract status for the current user
        if (statusData[userName]) {
          setStatus(statusData[userName]);
        }
        setSignals(signalsData);
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [location.search]);

  const renderChecklist = (title, rules) => (
    <div className="checklist-container">
      <h3>{title}</h3>
      <ul>
        {Object.entries(rules).map(([rule, result]) => (
          <li key={rule} className={result ? 'passed' : 'failed'}>
            {result ? '✔' : '✖'} {rule}
          </li>
        ))}
      </ul>
    </div>
  );

  if (!status || !signals) {
    return <div>Loading signals...</div>;
  }

  // --- Recreate logic from backend to show checklist status ---
  const swing_highs = signals.swing_points?.filter(p => p.type === 'high').sort((a, b) => b.price - a.price) || [];
  const swing_lows = signals.swing_points?.filter(p => p.type === 'low').sort((a, b) => b.price - a.price) || [];

  const biasBullishRules = {
    'Is Higher High': swing_highs.length >= 3 && swing_highs[0].price > swing_highs[1].price && swing_highs[1].price > swing_highs[2].price,
    'Is Higher Low': swing_lows.length >= 3 && swing_lows[0].price > swing_lows[1].price && swing_lows[1].price > swing_lows[2].price,
    'Price > 20 EMA': signals.latest_price > signals.ema_20,
    'Delta Slope Rising (>= 0.01)': signals.delta_slope >= 0.01,
    'Gamma Change Rising (>= 5%)': signals.gamma_change_percent >= 5.0,
    'IV Trend Stable/Rising (>= 0)': signals.iv_trend >= 0.0,
  };

  const biasBearishRules = {
    'Is Lower High': swing_highs.length >= 3 && swing_highs[0].price < swing_highs[1].price && swing_highs[1].price < swing_highs[2].price,
    'Is Lower Low': swing_lows.length >= 3 && swing_lows[0].price < swing_lows[1].price && swing_lows[1].price < swing_lows[2].price,
    'Price < 20 EMA': signals.latest_price < signals.ema_20,
    'Delta Slope Falling (<= -0.01)': signals.delta_slope <= -0.01,
    'Gamma Change Falling (<= -5%)': signals.gamma_change_percent <= -5.0,
    'IV Trend Stable/Falling (<= 0)': signals.iv_trend <= 0.0,
  };

  const marketTrendyRules = {
    'ATR (10-18)': signals.atr_14 >= 10 && signals.atr_14 <= 18,
    'Body Ratio (>= 60%)': signals.latest_candle_body_ratio >= 0.6,
    'Delta Stability (< 0.015)': signals.delta_stability < 0.015,
    'Gamma Change (>= 3%)': signals.gamma_change_percent >= 3.0,
    'IV Trend (>= 0)': signals.iv_trend >= 0.0,
  };

  const marketVolatileRules = {
    'ATR (> 18)': signals.atr_14 > 18,
    'Body Ratio (30-60%)': signals.latest_candle_body_ratio >= 0.3 && signals.latest_candle_body_ratio < 0.6,
    'Delta Stability (> 0.040)': signals.delta_stability > 0.040,
    'Gamma Change (> 10%)': signals.gamma_change_percent > 10.0,
    'IV Trend (> 2.0)': signals.iv_trend > 2.0,
  };

  const entryContinuationRules = {
    'Market Type is "Trendy"': status.market_type === 'Trendy',
    '(Bullish) Price > Last Swing Low': status.bias === 'Bullish' && signals.latest_price > signals.last_swing_low,
    '(Bearish) Price < Last Swing High': status.bias === 'Bearish' && signals.latest_price < signals.last_swing_high,
    '--- Greek Confirmation ---': '---',
    'Delta Slope Confirms': '...',
    'Gamma Change Confirms': '...',
    'IV Trend Confirms': '...',
    'Theta Change OK': '...',
  };

  const entryBreakoutRules = {
    'Market Type is "Volatile"': status.market_type === 'Volatile',
    '(Bullish) Price > Breakout Threshold': status.bias === 'Bullish' && signals.last_swing_high && signals.latest_price > (signals.last_swing_high * 1.0015),
    '(Bearish) Price < Breakout Threshold': status.bias === 'Bearish' && signals.last_swing_low && signals.latest_price < (signals.last_swing_low * 0.9985),
    'Breakout Candle Body >= 60%': signals.latest_candle_body_ratio >= 0.6,
    '--- Greek Confirmation ---': '---',
    'Delta Slope Confirms': '...',
    'Gamma Change Confirms': '...',
    'IV Trend Confirms': '...',
  };

  const entryReversalRules = {
    'Market Type is "Volatile"': status.market_type === 'Volatile',
    '(Bullish) Price Near Last Swing Low': status.bias === 'Bullish' && signals.last_swing_low && Math.abs(signals.latest_price - signals.last_swing_low) / signals.last_swing_low < 0.001,
    '(Bearish) Price Near Last Swing High': status.bias === 'Bearish' && signals.last_swing_high && Math.abs(signals.latest_price - signals.last_swing_high) / signals.last_swing_high < 0.001,
    'Reversal Candle Body < 30%': signals.latest_candle_body_ratio < 0.3,
    '--- Greek Confirmation ---': '---',
    'Delta Slope Flipped': '...',
    'Gamma Change Dropped': '...',
    'IV Trend Dropped': '...',
  };

  return (
    <div className="signals-page">
      <div className="status-summary">
        <h2>Current Status: <span className="status-value">{status.bias} / {status.market_type}</span></h2>
      </div>

      <div className="checklists-grid">
        {renderChecklist('Bias: Bullish Conditions', biasBullishRules)}
        {renderChecklist('Bias: Bearish Conditions', biasBearishRules)}
        {renderChecklist('Market Type: Trendy Conditions', marketTrendyRules)}
        {renderChecklist('Market Type: Volatile Conditions', marketVolatileRules)}
        {renderChecklist('Entry: Continuation Setup', entryContinuationRules)}
        {renderChecklist('Entry: Breakout Setup', entryBreakoutRules)}
        {renderChecklist('Entry: Reversal Setup', entryReversalRules)}
      </div>
    </div>
  );
};

export default Signals;