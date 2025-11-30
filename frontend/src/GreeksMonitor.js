import React from 'react';

const GreeksMonitor = ({ delta, gamma, theta, iv }) => {
  return (
    <div className="widget">
      <h2>Greeks Monitor (2nd OTM Call)</h2>
      <div className="greeks-grid">
        <p>Delta: <span className="status-value">{delta}</span></p>
        <p>Gamma: <span className="status-value">{gamma}</span></p>
        <p>Theta: <span className="status-value">{theta}</span></p>
        <p>IV: <span className="status-value">{iv}</span></p>
      </div>
    </div>
  );
};

export default GreeksMonitor;