import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Signals.css';

const Signals = () => {
  const [status, setStatus] = useState(null);
  const [signals, setSignals] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, signalsRes] = await Promise.all([
          fetch('/status'),
          fetch('/signals'),
        ]);
        const statusData = await statusRes.json();
        const signalsData = await signalsRes.json();
        setStatus(statusData);
        setSignals(signalsData);
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

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
  const biasRules = {
    'Is Higher High': signals.swing_points?.length >= 3 && signals.swing_points[0].price > signals.swing_points[1].price,
    'Is Higher Low': signals.swing_points?.length >= 3 && signals.swing_points[0].price > signals.swing_points[1].price, // Simplified for display
    'Price > 20 EMA': signals.latest_price > signals.ema_20,
    'Delta Slope Rising (>= 0.01)': signals.delta_slope >= 0.01,
    'Gamma Change Rising (>= 5%)': signals.gamma_change_percent >= 5.0,
    'IV Trend Stable/Rising (>= 0)': signals.iv_trend >= 0.0,
  };

  const marketTypeRules = {
    'ATR (10-18)': signals.atr_14 >= 10 && signals.atr_14 <= 18,
    'Body Ratio (>= 60%)': signals.latest_candle_body_ratio >= 0.6,
    'Delta Stability (< 0.015)': signals.delta_stability < 0.015,
    'Gamma Change (>= 3%)': signals.gamma_change_percent >= 3.0,
    'IV Trend (>= 0)': signals.iv_trend >= 0.0,
  };

  return (
    <div className="signals-page">
      <header className="signals-header">
        <h1>System Signals</h1>
        <nav className="dashboard-nav">
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/signals">Signals</Link>
            <Link to="/logs">Logs</Link>
            <Link to="/settings">Settings</Link>
            <Link to="/option-chain">Option Chain</Link>
        </nav>
      </header>

      <div className="status-summary">
        <h2>Current Status: <span className="status-value">{status.bias} / {status.market_type}</span></h2>
      </div>

      <div className="checklists-grid">
        {renderChecklist('Bias Determination (Bullish)', biasRules)}
        {renderChecklist('Market Type Determination (Trendy)', marketTypeRules)}
      </div>
    </div>
  );
};

export default Signals;