import React, { useState, useEffect } from 'react';
import './Settings.css';

const Settings = () => {
  const [settings, setSettings] = useState({
    risk_reward_ratio: '',
    risk_percent: '',
    cooldown_minutes: '', // Kept this one
    eod_exit_minutes: '', // Kept this one
    // --- New Strategy Settings ---
    market_type_window_size: '3', // Default to 3 (15-min)
    bos_buffer_points: '',
    retest_min_percent: '',
    retest_max_percent: '',
    entry_delta_slope_thresh: '',
    entry_gamma_change_thresh: '',
    entry_iv_trend_thresh: '',
    entry_theta_max_spike: '',
    exit_iv_crush_thresh: '',
  });
  const [message, setMessage] = useState('');

  const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/settings`);
        const data = await response.json();
        setSettings(data);
      } catch (error) {
        console.error("Error fetching settings:", error);
      }
    };
    fetchSettings();
  }, [apiBaseUrl]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async (key) => {
    try {
      const response = await fetch(`${apiBaseUrl}/settings`, {
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
        <div className="form-group">
          <label htmlFor="eod_exit_minutes">Exit Before EOD (minutes)</label>
          <input type="number" id="eod_exit_minutes" name="eod_exit_minutes" value={settings.eod_exit_minutes} onChange={handleInputChange} />
          <button onClick={() => handleSave('eod_exit_minutes')}>Save</button>
        </div>

        <div className="form-group-divider">Market Type Settings</div>
        <div className="form-group">
          <label>Market Type Window Size</label>
          <div className="radio-group">
            <input type="radio" id="market_type_15min" name="market_type_window_size" value="3" checked={settings.market_type_window_size === '3'} onChange={handleInputChange} />
            <label htmlFor="market_type_15min">15-min (3 candles)</label>
            <input type="radio" id="market_type_30min" name="market_type_window_size" value="6" checked={settings.market_type_window_size === '6'} onChange={handleInputChange} />
            <label htmlFor="market_type_30min">30-min (6 candles)</label>
          </div>
          <button onClick={() => handleSave('market_type_window_size')}>Save</button>
        </div>

        <div className="form-group-divider">Price Action (BOS/Retest) Settings</div>
        <div className="form-group">
          <label htmlFor="bos_buffer_points">BOS Buffer Points</label>
          <input type="number" step="1" id="bos_buffer_points" name="bos_buffer_points" value={settings.bos_buffer_points} onChange={handleInputChange} />
          <button onClick={() => handleSave('bos_buffer_points')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="retest_min_percent">Retest Min %</label>
          <input type="number" step="1" id="retest_min_percent" name="retest_min_percent" value={settings.retest_min_percent} onChange={handleInputChange} />
          <button onClick={() => handleSave('retest_min_percent')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="retest_max_percent">Retest Max %</label>
          <input type="number" step="1" id="retest_max_percent" name="retest_max_percent" value={settings.retest_max_percent} onChange={handleInputChange} />
          <button onClick={() => handleSave('retest_max_percent')}>Save</button>
        </div>

        <div className="form-group-divider">Entry Greek Confirmation Thresholds</div>
        <div className="form-group">
          <label htmlFor="entry_delta_slope_thresh">Delta Slope (min)</label>
          <input type="number" step="0.01" id="entry_delta_slope_thresh" name="entry_delta_slope_thresh" value={settings.entry_delta_slope_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('entry_delta_slope_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="entry_gamma_change_thresh">Gamma Change % (min)</label>
          <input type="number" step="0.1" id="entry_gamma_change_thresh" name="entry_gamma_change_thresh" value={settings.entry_gamma_change_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('entry_gamma_change_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="entry_iv_trend_thresh">IV Trend (min)</label>
          <input type="number" step="0.1" id="entry_iv_trend_thresh" name="entry_iv_trend_thresh" value={settings.entry_iv_trend_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('entry_iv_trend_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="entry_theta_max_spike">Theta Max Spike (abs)</label>
          <input type="number" step="0.1" id="entry_theta_max_spike" name="entry_theta_max_spike" value={settings.entry_theta_max_spike} onChange={handleInputChange} />
          <button onClick={() => handleSave('entry_theta_max_spike')}>Save</button>
        </div>
        <div className="form-group-divider">Emergency Exit Thresholds</div>
        <div className="form-group">
          <label htmlFor="exit_iv_crush_thresh">Emergency IV Crush (min)</label>
          <input type="number" step="0.1" id="exit_iv_crush_thresh" name="exit_iv_crush_thresh" value={settings.exit_iv_crush_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('exit_iv_crush_thresh')}>Save</button>
        </div>
      </div>
    </div>
  );
};


export default Settings;