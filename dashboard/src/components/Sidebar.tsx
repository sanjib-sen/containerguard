import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Overview', icon: '□' },
  { to: '/agents', label: 'Agents', icon: '▣' },
  { to: '/network', label: 'Network', icon: '⇄' },
  { to: '/logs', label: 'Logs', icon: '☰' },
];

export function Sidebar() {
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
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-800 text-[10px] text-gray-600">
        v1.0.0
      </div>
    </aside>
  );
}
