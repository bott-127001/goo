import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './OptionChain.css';

const OptionChain = () => {
  const [chainData, setChainData] = useState([]);
  const [status, setStatus] = useState({});
  const location = useLocation();

  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const userName = searchParams.get('user');

    if (!userName) {
      console.error("User not found in URL for Option Chain.");
      return;
    }

    const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
    const fetchData = async () => {
      try {
        const [chainRes, statusRes] = await Promise.all([
          fetch(`${apiBaseUrl}/option-chain/${userName}`),
          fetch(`${apiBaseUrl}/status`),
        ]);
        const chainData = await chainRes.json();
        const statusData = await statusRes.json();
        setChainData(chainData);
        // Extract the status for the current user
        if (statusData[userName]) {
          setStatus(statusData[userName]);
        }
      } catch (error) {
        console.error("Error fetching option chain data:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [location.search]);

  const getRowClass = (strike) => {
    if (!status.candidate_setup) return '';
    if (strike === status.candidate_setup.strike_price) {
      return 'highlight-monitored';
    }
    if (strike === status.candidate_setup.atm_strike) {
      return 'highlight-atm';
    }
    return '';
  };

  if (chainData.length === 0) {
    return <div>Loading Option Chain...</div>;
  }

  return (
    <div className="option-chain-page">
      <div className="option-chain-table-container">
        <table>
          <thead>
            <tr className="header-row">
              {/* Call Side */}
              <th className="call-side">OI</th>
              <th className="call-side">Volume</th>
              <th className="call-side">IV</th>
              <th className="call-side">Gamma</th>
              <th className="call-side">Theta</th>
              <th className="call-side">Vega</th>
              <th className="call-side">Delta</th>
              <th className="call-side">LTP</th>
              {/* Strike */}
              <th className="strike-header">Strike Price</th>
              {/* Put Side */}
              <th className="put-side">LTP</th>
              <th className="put-side">Delta</th>
              <th className="put-side">Vega</th>
              <th className="put-side">Theta</th>
              <th className="put-side">Gamma</th>
              <th className="put-side">IV</th>
              <th className="put-side">Volume</th>
              <th className="put-side">OI</th>
            </tr>
          </thead>
          <tbody>
            {chainData.map((item) => (
              <tr key={item.strike_price} className={getRowClass(item.strike_price)}>
                {/* Call Side Data */}
                <td>{item.call_options?.market_data?.open_interest || '-'}</td>
                <td>{item.call_options?.market_data?.volume || '-'}</td>
                <td>{item.call_options?.option_greeks?.iv?.toFixed(2) || '-'}</td>
                <td>{item.call_options?.option_greeks?.gamma?.toFixed(4) || '-'}</td>
                <td>{item.call_options?.option_greeks?.theta?.toFixed(2) || '-'}</td>
                <td>{item.call_options?.option_greeks?.vega?.toFixed(2) || '-'}</td>
                <td>{item.call_options?.option_greeks?.delta?.toFixed(2) || '-'}</td>
                <td>{item.call_options?.market_data?.ltp?.toFixed(2) || '-'}</td>
                {/* Strike Price */}
                <td className="strike-price">{item.strike_price}</td>
                {/* Put Side Data */}
                <td>{item.put_options?.market_data?.ltp?.toFixed(2) || '-'}</td>
                <td>{item.put_options?.option_greeks?.delta?.toFixed(2) || '-'}</td>
                <td>{item.put_options?.option_greeks?.vega?.toFixed(2) || '-'}</td>
                <td>{item.put_options?.option_greeks?.theta?.toFixed(2) || '-'}</td>
                <td>{item.put_options?.option_greeks?.gamma?.toFixed(4) || '-'}</td>
                <td>{item.put_options?.option_greeks?.iv?.toFixed(2) || '-'}</td>
                <td>{item.put_options?.market_data?.volume || '-'}</td>
                <td>{item.put_options?.market_data?.open_interest || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OptionChain;