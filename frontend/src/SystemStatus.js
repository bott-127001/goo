import React from 'react';

const SystemStatus = ({ bias, marketType, signal }) => {
  return (
    <div className="widget">
      <h2>System Status</h2>
      <p>Bias: <span className="status-value">{bias}</span></p>
      <p>Market Type: <span className="status-value">{marketType}</span></p>
      <p>
        Signal: 
        <span className="status-value">
          {signal && <span className="signal-indicator"></span>}
          {signal ? signal.status : 'No Active Signal'}
        </span>
      </p>
    </div>
  );
};

export default SystemStatus;