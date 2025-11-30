import React from 'react';

const LiveMarketOverview = ({ niftyPrice }) => {
  return (
    <div className="widget">
      <h2>Live Market</h2>
      <p>NIFTY 50: <span className="status-value">{niftyPrice}</span></p>
    </div>
  );
};

export default LiveMarketOverview;