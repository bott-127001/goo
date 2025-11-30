import './App.css';
import Login from './Login';
import Dashboard from './Dashboard';
import Signals from './Signals';
import TradeLogs from './TradeLogs';
import Settings from './Settings';
import OptionChain from './OptionChain';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/logs" element={<TradeLogs />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/option-chain" element={<OptionChain />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
