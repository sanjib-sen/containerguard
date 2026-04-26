import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { api } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import type { AlertMessage } from '../hooks/useWebSocket';

const links = [
  { to: '/', label: 'Overview', icon: '□' },
  { to: '/agents', label: 'Agents', icon: '▣' },
  { to: '/network', label: 'Network', icon: '⇄' },
  { to: '/logs', label: 'Logs', icon: '☰' },
  { to: '/alerts', label: 'Alerts', icon: '!', badge: 'alerts' as const },
  { to: '/compliance', label: 'Compliance', icon: '✓' },
  { to: '/scans', label: 'Scans', icon: '⊙' },
];

export function Sidebar() {
  const [openAlerts, setOpenAlerts] = useState(0);
  const { lastMessage } = useWebSocket<AlertMessage>('/ws/alerts');

  // Poll for open alerts count
  useEffect(() => {
    const fetchCount = () => {
      api.getAlerts({ status: 'open', limit: 500 })
        .then((alerts) => setOpenAlerts(alerts.length))
        .catch(() => {});
    };
    fetchCount();
    const interval = setInterval(fetchCount, 15000);
    return () => clearInterval(interval);
  }, []);

  // Increment on new alerts arriving via WS
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'alert') {
      setOpenAlerts((c) => c + 1);
    }
  }, [lastMessage]);

  return (
    <aside className="w-56 bg-gray-900 text-gray-300 flex flex-col min-h-screen shrink-0">
      <div className="px-4 py-5 border-b border-gray-700">
        <h1 className="text-lg font-bold text-white tracking-tight">ContainerGuard</h1>
        <p className="text-[10px] text-gray-500 mt-0.5 uppercase tracking-widest">Security Monitor</p>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-0.5">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded text-sm ${
                isActive
                  ? 'bg-gray-800 text-white font-medium'
                  : 'text-gray-400 hover:bg-gray-800/50 hover:text-gray-200'
              }`
            }
          >
            <span className="text-xs w-4 text-center">{link.icon}</span>
            <span className="flex-1">{link.label}</span>
            {link.badge === 'alerts' && openAlerts > 0 && (
              <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-5 text-center">
                {openAlerts > 99 ? '99+' : openAlerts}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-800 text-[10px] text-gray-600">
        v1.0.0
      </div>
    </aside>
  );
}
