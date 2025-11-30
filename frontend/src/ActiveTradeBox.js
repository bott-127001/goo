import React from 'react';

const ActiveTradeBox = ({ signal }) => {
  const renderSignalDetails = () => {
    if (!signal) {
      return <p className="status-value">No active signal.</p>;
    }

    if (signal.status === 'ENTRY_APPROVED') {
      return (
        <>
          <p>Type: <span className="status-value">{signal.type}</span></p>
          <p>Status: <span className="status-value">{signal.status}</span></p>
          <p>Entry: <span className="status-value">{signal.signal_premium?.toFixed(2)}</span> | SL: <span className="status-value">{signal.stop_loss}</span> | TGT: <span className="status-value">{signal.target}</span></p>
        </>
      );
    }

    return (
      <>
        <p>Type: <span className="status-value">{signal.type}</span></p>
        <p>Status: <span className="status-value">{signal.status}</span></p>
      </>
    );
  };

  return (
    <div className="widget">
      <h2>Active Signal / Trade</h2>
      {renderSignalDetails()}
    </div>
  );
};

export default ActiveTradeBox;