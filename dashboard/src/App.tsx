import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { NetworkView } from './pages/NetworkView';
import { AgentList } from './pages/AgentList';
import { AgentDetail } from './pages/AgentDetail';
import { Logs } from './pages/Logs';
import { Alerts } from './pages/Alerts';
import { AlertRules } from './pages/AlertRules';
import { Compliance } from './pages/Compliance';
import { Scans } from './pages/Scans';

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-100">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/network" element={<NetworkView />} />
            <Route path="/agents" element={<AgentList />} />
            <Route path="/agents/:id" element={<AgentDetail />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/alerts/rules" element={<AlertRules />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/scans" element={<Scans />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
