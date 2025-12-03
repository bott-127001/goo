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

  const renderChecklist = (title, conditions) => {
    if (!conditions) return null;
    return (
    <div className="checklist-container">
      <h3>{title}</h3>
      <ul>
        {Object.entries(conditions).map(([rule, result]) => (
          <li key={rule} className={result === true ? 'passed' : (result === false ? 'failed' : '')}>
            {result ? '✔' : '✖'} {rule}
          </li>
        ))}
      </ul>
    </div>
  )};

  if (!status || !signals) {
    return <div>Loading signals...</div>;
  }

  return (
    <div className="signals-page">
      <div className="status-summary">
        <h2>Current Status: <span className="status-value">{status.bias} / {status.market_type}</span></h2>
      </div>

      <div className="checklists-grid">
        {/* Layer 1: Bias */}
        <div className="checklist-container">
          <h3>Layer 1: Day-Open Bias ({status.bias})</h3>
          {signals.bias_details ? (
            <ul>
              <li>Price from Baseline: {signals.bias_details.price_from_baseline}</li>
              <li>Delta from Baseline: {signals.bias_details.delta_from_baseline}</li>
              {renderChecklist('Bullish Conditions', signals.bias_details.bullish_conditions)}
              {renderChecklist('Bearish Conditions', signals.bias_details.bearish_conditions)}
            </ul>
          ) : <li>Baseline not set yet.</li>}
        </div>

        {/* Layer 2: Market Type */}
        <div className="checklist-container">
          <h3>Layer 2: Market Type ({status.market_type})</h3>
          {signals.market_type_details ? (
            <ul>
              <li>ATR: {signals.market_type_details.atr}</li>
              <li>Avg. Body Ratio: {signals.market_type_details.body_ratio_avg}</li>
              {renderChecklist('Trendy Conditions', signals.market_type_details.trendy_conditions)}
              {renderChecklist('Volatile Conditions', signals.market_type_details.volatile_conditions)}
            </ul>
          ) : <li>Calculating...</li>}
        </div>

        {/* Layer 3: Price Action */}
        <div className="checklist-container">
          <h3>Layer 3: Price Action Setup</h3>
          {signals.price_action_details ? (
            <ul>
              <li>Status: {signals.price_action_details.status}</li>
              <li>Details: {signals.price_action_details.details}</li>
            </ul>
          ) : <li>Monitoring...</li>}
        </div>

        {/* Layer 4: Greek Confirmation */}
        <div className="checklist-container">
          <h3>Layer 4: Live Greek Confirmation</h3>
          {signals.greek_confirmation_details ? (
            <ul>
              <li>Smoothed Delta Slope (30s): {signals.greek_confirmation_details.smoothed_delta_slope}</li>
              <li>Smoothed Gamma Change (30s): {signals.greek_confirmation_details.smoothed_gamma_change}</li>
              <li>Smoothed IV Trend (30s): {signals.greek_confirmation_details.smoothed_iv_trend}</li>
              <li>Smoothed Theta Change (30s): {signals.greek_confirmation_details.smoothed_theta_change}</li>
            </ul>
          ) : <li>Calculating...</li>}
        </div>
      </div>
    </div>
  );
};

export default Signals;