import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Agent } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';

export function AgentList() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    api.getAgents().then(setAgents).catch(console.error);
    const interval = setInterval(() => {
      api.getAgents().then(setAgents).catch(console.error);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(() => {
    let list = agents;
    if (statusFilter !== 'all') {
      list = list.filter((a) => a.status === statusFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((a) =>
        a.hostname.toLowerCase().includes(q) ||
        a.image.toLowerCase().includes(q) ||
        a.container_id.toLowerCase().includes(q) ||
        (a.ip && a.ip.includes(q))
      );
    }
    return list;
  }, [agents, search, statusFilter]);

  const statusCounts = useMemo(() => {
    const c: Record<string, number> = { all: agents.length, online: 0, unreachable: 0, offline: 0 };
    agents.forEach((a) => { c[a.status] = (c[a.status] || 0) + 1; });
    return c;
  }, [agents]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Agents</h2>
        <p className="text-sm text-gray-500 mt-0.5">Click any agent to see detailed telemetry</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search hostname, image, IP..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded-lg px-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-1">
          {(['all', 'online', 'unreachable', 'offline'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                statusFilter === s
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)} ({statusCounts[s] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Hostname</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Image</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Registered</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((agent) => (
                <tr
                  key={agent.id}
                  className="hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/agents/${agent.id}`)}
                >
                  <td className="px-4 py-2 font-mono text-gray-800 font-medium">{agent.hostname}</td>
                  <td className="px-4 py-2 text-gray-600 max-w-[200px] truncate">{agent.image}</td>
                  <td className="px-4 py-2 font-mono text-gray-500">{agent.ip || '—'}</td>
                  <td className="px-4 py-2"><StatusBadge status={agent.status} /></td>
                  <td className="px-4 py-2 text-gray-500">{new Date(agent.registered_at).toLocaleString()}</td>
                  <td className="px-4 py-2 text-gray-500">{new Date(agent.last_heartbeat).toLocaleString()}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  {agents.length === 0 ? 'No agents registered' : 'No agents match your filters'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
        {filtered.length > 0 && (
          <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-500">
            Showing {filtered.length} of {agents.length} agents
          </div>
        )}
      </div>
    </div>
  );
}
