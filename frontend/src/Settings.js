import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Settings.css';

const Settings = () => {
  const [settings, setSettings] = useState({
    risk_reward_ratio: '',
    risk_percent: '',
    cooldown_minutes: '',
    confirm_delta_slope: '',
    confirm_gamma_change: '',
    confirm_iv_trend: '',
    confirm_conditions_met: '',
    atr_neutral_max: '',
    atr_trendy_min: '',
    atr_trendy_max: ''
  });
  const [message, setMessage] = useState('');
  const location = useLocation();

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch('http://localhost:8000/settings');
        const data = await response.json();
        setSettings(data);
      } catch (error) {
        console.error("Error fetching settings:", error);
      }
    };
    fetchSettings();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async (key) => {
    try {
      const response = await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: settings[key] }),
      });
      if (response.ok) {
        setMessage(`Setting '${key}' saved successfully!`);
        setTimeout(() => setMessage(''), 3000); // Clear message after 3 seconds
      } else {
        throw new Error('Failed to save setting');
      }
    } catch (error) {
      console.error("Error saving setting:", error);
      setMessage(`Error saving setting '${key}'.`);
      setTimeout(() => setMessage(''), 3000);
    }
  };

  return (
    <div className="settings-page">
      <header className="settings-header">
        <h1>Strategy Settings</h1>
        <nav className="dashboard-nav">
          <Link to={`/dashboard${location.search}`}>Dashboard</Link>
          <Link to={`/signals${location.search}`}>Signals</Link>
          <Link to={`/logs${location.search}`}>Logs</Link>
          <Link to={`/settings${location.search}`}>Settings</Link>
          <Link to={`/option-chain${location.search}`}>Option Chain</Link>
        </nav>
      </header>

      {message && <div className="save-message">{message}</div>}

      <div className="settings-form">
        <div className="form-group">
          <label htmlFor="risk_reward_ratio">Risk-to-Reward Ratio</label>
          <input type="number" id="risk_reward_ratio" name="risk_reward_ratio" value={settings.risk_reward_ratio} onChange={handleInputChange} />
          <button onClick={() => handleSave('risk_reward_ratio')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="risk_percent">Risk Per Trade (%)</label>
          <input type="number" id="risk_percent" name="risk_percent" value={settings.risk_percent} onChange={handleInputChange} />
          <button onClick={() => handleSave('risk_percent')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="cooldown_minutes">Cooldown After Trade (minutes)</label>
          <input type="number" id="cooldown_minutes" name="cooldown_minutes" value={settings.cooldown_minutes} onChange={handleInputChange} />
          <button onClick={() => handleSave('cooldown_minutes')}>Save</button>
        </div>
        <div className="form-group-divider">Greek Confirmation Thresholds</div>
        <div className="form-group">
          <label htmlFor="confirm_delta_slope">Delta Slope</label>
          <input type="number" step="0.01" id="confirm_delta_slope" name="confirm_delta_slope" value={settings.confirm_delta_slope} onChange={handleInputChange} />
          <button onClick={() => handleSave('confirm_delta_slope')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="confirm_gamma_change">Gamma Change (%)</label>
          <input type="number" step="0.1" id="confirm_gamma_change" name="confirm_gamma_change" value={settings.confirm_gamma_change} onChange={handleInputChange} />
          <button onClick={() => handleSave('confirm_gamma_change')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="confirm_iv_trend">IV Trend</label>
          <input type="number" step="0.1" id="confirm_iv_trend" name="confirm_iv_trend" value={settings.confirm_iv_trend} onChange={handleInputChange} />
          <button onClick={() => handleSave('confirm_iv_trend')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="confirm_conditions_met">Conditions to Meet</label>
          <input type="number" step="1" id="confirm_conditions_met" name="confirm_conditions_met" value={settings.confirm_conditions_met} onChange={handleInputChange} />
          <button onClick={() => handleSave('confirm_conditions_met')}>Save</button>
        </div>
        <div className="form-group-divider">Market Type Thresholds (ATR)</div>
        <div className="form-group">
          <label htmlFor="atr_neutral_max">Neutral Max ATR</label>
          <input type="number" step="1" id="atr_neutral_max" name="atr_neutral_max" value={settings.atr_neutral_max} onChange={handleInputChange} />
          <button onClick={() => handleSave('atr_neutral_max')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="atr_trendy_min">Trendy Min ATR</label>
          <input type="number" step="1" id="atr_trendy_min" name="atr_trendy_min" value={settings.atr_trendy_min} onChange={handleInputChange} />
          <button onClick={() => handleSave('atr_trendy_min')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="atr_trendy_max">Trendy Max ATR</label>
          <input type="number" step="1" id="atr_trendy_max" name="atr_trendy_max" value={settings.atr_trendy_max} onChange={handleInputChange} />
          <button onClick={() => handleSave('atr_trendy_max')}>Save</button>
        </div>
      </div>
    </div>
  );
};

export default Settings;