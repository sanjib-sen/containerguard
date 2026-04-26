import { useEffect, useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Agent, ResourceSnapshot } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import type { TelemetryMessage } from '../hooks/useWebSocket';
import { StatusBadge } from '../components/StatusBadge';

const STATUS_COLORS: Record<string, string> = {
  online: '#22c55e',
  unreachable: '#eab308',
  offline: '#ef4444',
};

export function Dashboard() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [latestResources, setLatestResources] = useState<ResourceSnapshot[]>([]);
  const { lastMessage, connected } = useWebSocket<TelemetryMessage>('/ws/dashboard');

  // Fetch
  useEffect(() => {
    api.getAgents().then(setAgents).catch(console.error);
    api.getLatestResources().then(setLatestResources).catch(console.error);
  }, []);

  // Refresh periodically
  useEffect(() => {
    const interval = setInterval(() => {
      api.getAgents().then(setAgents).catch(console.error);
      api.getLatestResources().then(setLatestResources).catch(console.error);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Update latest resources on WS message
  useEffect(() => {
    if (!lastMessage?.resources) return;
    setLatestResources((prev) => {
      const next = prev.filter((r) => r.agent_id !== lastMessage.agent_id);
      next.push({
        id: '',
        agent_id: lastMessage.agent_id,
        cpu_pct: lastMessage.resources!.cpu_percent,
        mem_mb: lastMessage.resources!.memory_mb,
        mem_limit_mb: lastMessage.resources!.memory_limit_mb,
        net_bytes_sent: lastMessage.resources!.net_bytes_sent,
        net_bytes_recv: lastMessage.resources!.net_bytes_recv,
        disk_read_bytes: lastMessage.resources!.disk_read_bytes,
        disk_write_bytes: lastMessage.resources!.disk_write_bytes,
        timestamp: lastMessage.timestamp,
      });
      return next;
    });
  }, [lastMessage]);

  // Computed stats
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { online: 0, unreachable: 0, offline: 0 };
    agents.forEach((a) => { counts[a.status] = (counts[a.status] || 0) + 1; });
    return counts;
  }, [agents]);

  const statusPieData = useMemo(
    () => Object.entries(statusCounts).filter(([, v]) => v > 0).map(([name, value]) => ({ name, value })),
    [statusCounts],
  );

  // Build hostname lookup
  const hostnameMap = useMemo(() => {
    const m = new Map<string, string>();
    agents.forEach((a) => m.set(a.id, a.hostname));
    return m;
  }, [agents]);

  // Top CPU / Memory consumers
  const topCpu = useMemo(() =>
    [...latestResources]
      .sort((a, b) => b.cpu_pct - a.cpu_pct)
      .slice(0, 10)
      .map((r) => ({ name: hostnameMap.get(r.agent_id) || r.agent_id.slice(0, 12), value: Math.round(r.cpu_pct * 10) / 10, agent_id: r.agent_id })),
    [latestResources, hostnameMap],
  );

  const topMem = useMemo(() =>
    [...latestResources]
      .sort((a, b) => b.mem_mb - a.mem_mb)
      .slice(0, 10)
      .map((r) => ({ name: hostnameMap.get(r.agent_id) || r.agent_id.slice(0, 12), value: Math.round(r.mem_mb), agent_id: r.agent_id })),
    [latestResources, hostnameMap],
  );

  // Aggregate stats
  const avgCpu = latestResources.length > 0
    ? (latestResources.reduce((s, r) => s + r.cpu_pct, 0) / latestResources.length).toFixed(1)
    : '—';
  const totalMem = latestResources.length > 0
    ? Math.round(latestResources.reduce((s, r) => s + r.mem_mb, 0))
    : '—';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Overview</h2>
          <p className="text-sm text-gray-500 mt-0.5">Aggregate health across all monitored containers</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded font-medium ${connected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {connected ? 'Live' : 'Disconnected'}
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total Agents" value={agents.length} />
        <StatCard label="Online" value={statusCounts.online} color="text-green-600" />
        <StatCard label="Unreachable" value={statusCounts.unreachable} color="text-yellow-600" />
        <StatCard label="Offline" value={statusCounts.offline} color="text-red-600" />
        <StatCard label="Avg CPU" value={`${avgCpu}%`} />
        <StatCard label="Total Memory" value={typeof totalMem === 'number' ? `${totalMem} MB` : totalMem} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Health distribution */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Health Distribution</h3>
          {statusPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={statusPieData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                  {statusPieData.map((entry) => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#9ca3af'} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-gray-400 text-sm">No agents</div>
          )}
        </div>

        {/* Top CPU */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Top CPU Consumers (%)</h3>
          {topCpu.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={topCpu} layout="vertical" margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} cursor="pointer"
                  onClick={(_data, index) => { const item = topCpu[index]; if (item) navigate(`/agents/${item.agent_id}`); }} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-gray-400 text-sm">No data</div>
          )}
        </div>

        {/* Top Memory */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">Top Memory Consumers (MB)</h3>
          {topMem.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={topMem} layout="vertical" margin={{ left: 0, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#10b981" radius={[0, 4, 4, 0]} cursor="pointer"
                  onClick={(_data, index) => { const item = topMem[index]; if (item) navigate(`/agents/${item.agent_id}`); }} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[180px] flex items-center justify-center text-gray-400 text-sm">No data</div>
          )}
        </div>
      </div>

      {/* Agent table — compact, sortable-ready, clickable */}
      <div className="bg-white border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h3 className="text-xs font-semibold text-gray-500 uppercase">All Agents</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Hostname</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Image</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">IP</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">CPU</th>
                <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Memory</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Last Heartbeat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {agents.map((agent) => {
                const res = latestResources.find((r) => r.agent_id === agent.id);
                return (
                  <tr key={agent.id} className="hover:bg-blue-50 cursor-pointer transition-colors" onClick={() => navigate(`/agents/${agent.id}`)}>
                    <td className="px-4 py-2 font-mono text-gray-800 font-medium">{agent.hostname}</td>
                    <td className="px-4 py-2 text-gray-600 max-w-[200px] truncate">{agent.image}</td>
                    <td className="px-4 py-2 font-mono text-gray-500">{agent.ip || '—'}</td>
                    <td className="px-4 py-2"><StatusBadge status={agent.status} /></td>
                    <td className="px-4 py-2 text-right font-mono text-gray-700">{res ? `${res.cpu_pct.toFixed(1)}%` : '—'}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-700">{res ? `${Math.round(res.mem_mb)} MB` : '—'}</td>
                    <td className="px-4 py-2 text-gray-500">{new Date(agent.last_heartbeat).toLocaleString()}</td>
                  </tr>
                );
              })}
              {agents.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No agents registered</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-white border rounded-lg px-4 py-3">
      <p className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold mt-0.5 ${color || 'text-gray-900'}`}>{value}</p>
    </div>
  );
}
