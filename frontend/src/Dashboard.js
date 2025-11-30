import React, { useState, useEffect, useRef } from 'react';
import './Dashboard.css';
import { Link } from 'react-router-dom';
import SystemStatus from './SystemStatus';
import LiveMarketOverview from './LiveMarketOverview';
import GreeksMonitor from './GreeksMonitor';
import ActiveTradeBox from './ActiveTradeBox';

const Dashboard = () => {
  // Placeholder state for all data
  const [status, setStatus] = useState({ bias: 'Neutral', market_type: 'Undetermined' });
  const [market, setMarket] = useState({ nifty_price: 'Fetching...' });
  const [greeks, setGreeks] = useState({ delta: '--', gamma: '--', theta: '--', iv: '--' });
  const [signal, setSignal] = useState(null);
  const previousSignalRef = useRef();

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsURL = `${wsProtocol}//${wsHost}/ws`;

    const ws = new WebSocket(wsURL);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus({ bias: data.bias, market_type: data.market_type });
      setMarket({ nifty_price: data.nifty_price });
      setGreeks({ delta: data.delta, gamma: data.gamma, theta: data.theta, iv: data.iv });

      // Logic to show the final result of a closed trade for a few seconds
      if (!data.candidate_setup && previousSignalRef.current?.status === 'ENTRY_APPROVED') {
        // A trade was just closed. Fetch the final result.
        fetch('/tradelogs')
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
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    // Cleanup function to close the WebSocket connection when the component unmounts
    return () => {
      ws.close();
    };
  }, []); // The empty dependency array ensures this effect runs only once on mount

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Trading Dashboard</h1>
        <nav className="dashboard-nav">
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/signals">Signals</Link>
            <Link to="/logs">Logs</Link>
            <Link to="/settings">Settings</Link>
            <Link to="/option-chain">Option Chain</Link>
        </nav>
      </header>
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