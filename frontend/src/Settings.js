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
    atr_trendy_max: '',
    cont_delta_thresh: '',
    cont_gamma_thresh: '',
    cont_iv_thresh: '',
    cont_theta_thresh: '',
    cont_conditions_met: '',
    rev_delta_flip_thresh: '',
    rev_gamma_drop_thresh: '',
    rev_iv_drop_thresh: '',
    rev_conditions_met: '',
    exit_delta_flip_thresh: '',
    exit_gamma_drop_thresh: '',
    exit_iv_crush_thresh: '',
    eod_exit_minutes: ''
  });
  const [message, setMessage] = useState('');
  const location = useLocation();

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
        <div className="form-group-divider">Greek Exit Thresholds</div>
        <div className="form-group">
          <label htmlFor="exit_delta_flip_thresh">Exit on Delta Flip</label>
          <input type="number" step="0.01" id="exit_delta_flip_thresh" name="exit_delta_flip_thresh" value={settings.exit_delta_flip_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('exit_delta_flip_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="exit_gamma_drop_thresh">Exit on Gamma Drop (%)</label>
          <input type="number" step="0.1" id="exit_gamma_drop_thresh" name="exit_gamma_drop_thresh" value={settings.exit_gamma_drop_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('exit_gamma_drop_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="exit_iv_crush_thresh">Exit on IV Crush</label>
          <input type="number" step="0.1" id="exit_iv_crush_thresh" name="exit_iv_crush_thresh" value={settings.exit_iv_crush_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('exit_iv_crush_thresh')}>Save</button>
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
        <div className="form-group-divider">Continuation Entry Thresholds</div>
        <div className="form-group">
          <label htmlFor="cont_delta_thresh">Continuation Delta Slope</label>
          <input type="number" step="0.01" id="cont_delta_thresh" name="cont_delta_thresh" value={settings.cont_delta_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('cont_delta_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="cont_gamma_thresh">Continuation Gamma Change (%)</label>
          <input type="number" step="0.1" id="cont_gamma_thresh" name="cont_gamma_thresh" value={settings.cont_gamma_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('cont_gamma_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="cont_iv_thresh">Continuation IV Trend</label>
          <input type="number" step="0.1" id="cont_iv_thresh" name="cont_iv_thresh" value={settings.cont_iv_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('cont_iv_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="cont_theta_thresh">Continuation Theta Change (%)</label>
          <input type="number" step="0.1" id="cont_theta_thresh" name="cont_theta_thresh" value={settings.cont_theta_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('cont_theta_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="cont_conditions_met">Continuation Conditions to Meet</label>
          <input type="number" step="1" id="cont_conditions_met" name="cont_conditions_met" value={settings.cont_conditions_met} onChange={handleInputChange} />
          <button onClick={() => handleSave('cont_conditions_met')}>Save</button>
        </div>
        <div className="form-group-divider">Reversal Entry Thresholds</div>
        <div className="form-group">
          <label htmlFor="rev_delta_flip_thresh">Reversal Delta Flip</label>
          <input type="number" step="0.01" id="rev_delta_flip_thresh" name="rev_delta_flip_thresh" value={settings.rev_delta_flip_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('rev_delta_flip_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="rev_gamma_drop_thresh">Reversal Gamma Drop (%)</label>
          <input type="number" step="0.1" id="rev_gamma_drop_thresh" name="rev_gamma_drop_thresh" value={settings.rev_gamma_drop_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('rev_gamma_drop_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="rev_iv_drop_thresh">Reversal IV Drop</label>
          <input type="number" step="0.1" id="rev_iv_drop_thresh" name="rev_iv_drop_thresh" value={settings.rev_iv_drop_thresh} onChange={handleInputChange} />
          <button onClick={() => handleSave('rev_iv_drop_thresh')}>Save</button>
        </div>
        <div className="form-group">
          <label htmlFor="rev_conditions_met">Reversal Conditions to Meet</label>
          <input type="number" step="1" id="rev_conditions_met" name="rev_conditions_met" value={settings.rev_conditions_met} onChange={handleInputChange} />
          <button onClick={() => handleSave('rev_conditions_met')}>Save</button>
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