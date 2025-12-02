import React, { useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import './Layout.css';

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const keepAliveIntervalRef = useRef(null);

  // --- Keep-alive ping to prevent Render service from spinning down ---
  useEffect(() => {
    const sendKeepAlive = () => {
      const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
      // We can use a lightweight endpoint like /api/settings which just reads from the DB
      fetch(`${apiBaseUrl}/api/settings`)
        .then(res => console.log(`Keep-alive ping sent at ${new Date().toLocaleTimeString()}`))
        .catch(err => console.error("Keep-alive ping failed:", err));
    };

    // Start pinging every 5 minutes (300,000 milliseconds)
    keepAliveIntervalRef.current = setInterval(sendKeepAlive, 300000);

    // Add an event listener for the Page Visibility API
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log("Tab is visible again. Sending immediate keep-alive ping.");
        sendKeepAlive();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup on component unmount
    return () => {
      if (keepAliveIntervalRef.current) {
        clearInterval(keepAliveIntervalRef.current);
      }
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const handleLogout = async () => {
    const searchParams = new URLSearchParams(location.search);
    const userName = searchParams.get('user');
    if (!userName) return;

    try {
      const apiBaseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
      await fetch(`${apiBaseUrl}/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName }),
      });
      // Redirect to login page after successful logout
      navigate('/');
    } catch (err) {
      console.error("Logout failed:", err);
      // Still redirect even if the API call fails, as the user wants to log out.
      navigate('/');
    }
  };

  return (
    <>
      <header className="app-header">
        <h1>Trading Dashboard</h1>
        <nav className="app-nav">
          <Link to={`/dashboard${location.search}`}>Dashboard</Link>
          <Link to={`/signals${location.search}`}>Signals</Link>
          <Link to={`/logs${location.search}`}>Logs</Link>
          <Link to={`/settings${location.search}`}>Settings</Link>
          <Link to={`/option-chain${location.search}`}>Option Chain</Link>
          <button onClick={handleLogout} className="logout-button">Logout</button>
        </nav>
      </header>
      <Outlet /> {/* This is where the specific page content will be rendered */}
    </>
  );
};

export default Layout;