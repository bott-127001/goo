import React from 'react';
import './Login.css';

const Login = () => {
  const samarthClientId = process.env.REACT_APP_SAMARTH_UPSTOX_CLIENT_ID;
  const prajwalClientId = process.env.REACT_APP_PRAJWAL_UPSTOX_CLIENT_ID;

  const handleLogin = (user) => {
    let redirectUri;
    // In development, we must point directly to the backend server for the callback.
    // The 'proxy' in package.json doesn't work for browser redirects.
    if (process.env.NODE_ENV === 'development') {
      redirectUri = 'http://localhost:8000/auth/upstox/callback';
    } else {
      // In production, the origin is the same for frontend and backend.
      redirectUri = `${window.location.origin}/auth/upstox/callback`;
    }

    let clientId;

    if (user === 'samarth') {
      clientId = samarthClientId;
    } else if (user === 'prajwal') {
      clientId = prajwalClientId;
    }

    if (!clientId || !redirectUri) {
      console.error('Upstox Client ID or Redirect URI is not configured in .env file.');
      return;
    }

    const authUrl = `https://api-v2.upstox.com/login/authorization/dialog?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&state=${user}`;
    window.location.href = authUrl;
  };

  return (
    <div className="login-container">
      <h1>Greeks-Based Trading Tool</h1>
      <p>Authenticate securely using your Upstox account to access your trading dashboard.</p>
      <button onClick={() => handleLogin('samarth')} style={{ marginRight: '10px' }} disabled={!samarthClientId}>
        Login as Samarth
      </button>
      <button onClick={() => handleLogin('prajwal')} disabled={!prajwalClientId}>
        Login as Prajwal
      </button>
    </div>
  );
};

export default Login;