import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import SystemStatus from './SystemStatus';
import LiveMarketOverview from './LiveMarketOverview'; // Assuming this is a component, not a page
import GreeksMonitor from './GreeksMonitor';
import ActiveTradeBox from './ActiveTradeBox';

const Dashboard = () => {
  // Placeholder state for all data
  const [status, setStatus] = useState({ bias: 'Neutral', market_type: 'Undetermined' });
  const [market, setMarket] = useState({ nifty_price: 'Fetching...' });
  const [greeks, setGreeks] = useState({ delta: '--', gamma: '--', theta: '--', iv: '--' });
  const [signal, setSignal] = useState(null);
  const [error, setError] = useState(null);
  const previousSignalRef = useRef();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const userName = searchParams.get('user');

    if (!userName) {
      setError("User name not found in URL. Cannot connect to WebSocket.");
      return;
    }

    const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
    const wsBaseUrl = apiBaseUrl.replace(/^http/, 'ws');

    const wsURL = `${wsBaseUrl}/ws/${userName}`; // This constructs ws:// or wss:// automatically

    const ws = new WebSocket(wsURL);

    ws.onopen = () => {
      console.log(`WebSocket connected for user: ${userName} at ${wsURL}`);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus({ bias: data.bias, market_type: data.market_type });
        setMarket({ nifty_price: data.nifty_price });
        setGreeks({ delta: data.delta, gamma: data.gamma, theta: data.theta, iv: data.iv });
  
        // Logic to show the final result of a closed trade for a few seconds
        if (!data.candidate_setup && previousSignalRef.current?.status === 'ENTRY_APPROVED') {
          // A trade was just closed. Fetch the final result.
          fetch(`${apiBaseUrl}/tradelogs`)
            .then(res => res.json())
            .then(logs => {
              const lastLog = logs.find(log => log.id === previousSignalRef.current.log_id);
              if (lastLog) {
                setSignal({ type: 'CLOSED', status: lastLog.result });
                // Clear the "CLOSED" message after 10 seconds
                setTimeout(() => setSignal(null), 10000);
              }
            });
        } else {
          setSignal(data.candidate_setup);
        }
        previousSignalRef.current = data.candidate_setup;
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.onerror = (event) => {
      console.error("WebSocket Error:", event);
      setError("Failed to connect to the live data stream. Is the backend server running?");
    };

    return () => {
      ws.close();
    };
  }, [location.search]);

  return (
    <div className="dashboard">
      {error && <p className="error-message">{error}</p>}
      <div className="dashboard-grid">
        <div className="widget-container">
          <SystemStatus 
            bias={status.bias} 
            marketType={status.market_type} 
            signal={signal}
          />
        </div>
        <div className="widget-container">
          <LiveMarketOverview 
            niftyPrice={market.nifty_price} 
          />
        </div>
        <div className="widget-container full-width">
          <GreeksMonitor 
            delta={greeks.delta}
            gamma={greeks.gamma}
            theta={greeks.theta}
            iv={greeks.iv}
          />
        </div>
        <div className="widget-container full-width">
          <ActiveTradeBox signal={signal} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;