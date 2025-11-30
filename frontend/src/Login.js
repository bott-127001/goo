import React from 'react';

const Login = () => {
  const samarthClientId = process.env.REACT_APP_SAMARTH_UPSTOX_CLIENT_ID;
  const prajwalClientId = process.env.REACT_APP_PRAJWAL_UPSTOX_CLIENT_ID;

  const handleLogin = (user) => {
    const redirectUri = process.env.REACT_APP_UPSTOX_REDIRECT_URI;
    let clientId;

    if (user === 'samarth') {
      clientId = process.env.REACT_APP_SAMARTH_UPSTOX_CLIENT_ID;
    } else if (user === 'prajwal') {
      clientId = process.env.REACT_APP_PRAJWAL_UPSTOX_CLIENT_ID;
    }

    if (!clientId || !redirectUri) {
      console.error('Upstox Client ID or Redirect URI is not configured in .env file.');
      return;
    }

    const authUrl = `https://api.upstox.com/v2/login/authorization/dialog?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code`;
    window.location.href = authUrl;
  };

  return (
    <div className="login-container">
      <h1>Greeks-Based Trading Tool</h1>
      <p>Authenticate securely using your Upstox account to access your trading dashboard.</p>
      <button onClick={() => handleLogin('samarth')} style={{ marginRight: '10px' }}>
        Login as Samarth
      </button>
      <button onClick={() => handleLogin('prajwal')} disabled={!prajwalClientId}>
        Login as Prajwal
      </button>
    </div>
  );
};

export default Login;