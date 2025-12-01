import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './TradeLogs.css';

const TradeLogs = () => {
  const [logs, setLogs] = useState([]);
  const location = useLocation();

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/tradelogs');
        const data = await response.json();
        setLogs(data);
      } catch (error) {
        console.error("Error fetching trade logs:", error);
      }
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="logs-page">
      <header className="logs-header">
        <h1>Trade Logs</h1>
        <nav className="dashboard-nav">
          <Link to={`/dashboard${location.search}`}>Dashboard</Link>
          <Link to={`/signals${location.search}`}>Signals</Link>
          <Link to={`/logs${location.search}`}>Logs</Link>
          <Link to={`/settings${location.search}`}>Settings</Link>
          <Link to={`/option-chain${location.search}`}>Option Chain</Link>
        </nav>
      </header>

      <div className="logs-table-container">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Signal Type</th>
              <th>Status</th>
              <th>Strike</th>
              <th>Entry Price</th>
              <th>Result / Levels</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
                <td>{log.signal_type}</td>
                <td>{log.status}</td>
                <td>{log.strike_price}</td>
                <td>{log.entry_price}</td>
                <td>{log.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TradeLogs;