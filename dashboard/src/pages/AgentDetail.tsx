import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { api } from '../api/client';
import type { Agent, ResourceSnapshot, NetworkEvent, FilesystemEvent, ProcessSnapshot, PortSnapshot } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import { StatusBadge } from '../components/StatusBadge';
import { LogViewer } from '../components/LogViewer';

export function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [resources, setResources] = useState<ResourceSnapshot[]>([]);
  const [networkEvents, setNetworkEvents] = useState<NetworkEvent[]>([]);
  const [fsEvents, setFsEvents] = useState<FilesystemEvent[]>([]);
  const [processes, setProcesses] = useState<ProcessSnapshot[]>([]);
  const [ports, setPorts] = useState<PortSnapshot[]>([]);
  const [tab, setTab] = useState<'overview' | 'network' | 'filesystem' | 'processes' | 'ports' | 'logs'>('overview');
  const { lastMessage } = useWebSocket('/ws/dashboard');

  // Fetch all data for this agent
  useEffect(() => {
    if (!id) return;
    api.getAgent(id).then(setAgent).catch(() => navigate('/agents'));
    api.getAgentResources(id, 1, 200).then(setResources).catch(console.error);
    api.getAgentNetwork(id, 24, 200).then(setNetworkEvents).catch(console.error);
    api.getAgentFilesystem(id, 24, 200).then(setFsEvents).catch(console.error);
    api.getAgentProcesses(id, 1, 200).then(setProcesses).catch(console.error);
    api.getAgentPorts(id, 1, 200).then(setPorts).catch(console.error);
  }, [id, navigate]);

  // Refresh non-resource data periodically
  useEffect(() => {
    if (!id) return;
    const interval = setInterval(() => {
      api.getAgent(id).then(setAgent).catch(console.error);
      api.getAgentNetwork(id, 24, 200).then(setNetworkEvents).catch(console.error);
      api.getAgentFilesystem(id, 24, 200).then(setFsEvents).catch(console.error);
      api.getAgentProcesses(id, 1, 200).then(setProcesses).catch(console.error);
      api.getAgentPorts(id, 1, 200).then(setPorts).catch(console.error);
    }, 15000);
    return () => clearInterval(interval);
  }, [id]);

  // Live update resources from WebSocket
  useEffect(() => {
    if (!lastMessage?.resources || lastMessage.agent_id !== id) return;
    const r = lastMessage.resources;
    setResources((prev) => {
      const point: ResourceSnapshot = {
        id: '',
        agent_id: lastMessage.agent_id,
        cpu_pct: r.cpu_percent,
        mem_mb: r.memory_mb,
        mem_limit_mb: r.memory_limit_mb,
        net_bytes_sent: r.net_bytes_sent,
        net_bytes_recv: r.net_bytes_recv,
        disk_read_bytes: r.disk_read_bytes,
        disk_write_bytes: r.disk_write_bytes,
        timestamp: lastMessage.timestamp,
      };
      return [point, ...prev].slice(0, 200);
    });
  }, [lastMessage, id]);

  if (!agent) return <div className="text-gray-400 py-12 text-center">Loading...</div>;

  const chartPoints = resources.slice().reverse().map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString(),
    cpu: r.cpu_pct,
    mem: Math.round(r.mem_mb),
    netSent: r.net_bytes_sent,
    netRecv: r.net_bytes_recv,
    diskRead: r.disk_read_bytes,
    diskWrite: r.disk_write_bytes,
  }));

  const latest = resources[0];

  // Deduplicate processes by pid (take latest)
  const uniqueProcesses = (() => {
    const seen = new Map<number, ProcessSnapshot>();
    for (const p of processes) {
      if (!seen.has(p.pid)) seen.set(p.pid, p);
    }
    return [...seen.values()];
  })();

  // Deduplicate ports
  const uniquePorts = (() => {
    const seen = new Map<string, PortSnapshot>();
    for (const p of ports) {
      const key = `${p.port}-${p.protocol}`;
      if (!seen.has(key)) seen.set(key, p);
    }
    return [...seen.values()];
  })();

  const tabs = [
    { key: 'overview' as const, label: 'Overview' },
    { key: 'network' as const, label: `Network (${networkEvents.length})` },
    { key: 'filesystem' as const, label: `Filesystem (${fsEvents.length})` },
    { key: 'processes' as const, label: `Processes (${uniqueProcesses.length})` },
    { key: 'ports' as const, label: `Ports (${uniquePorts.length})` },
    { key: 'logs' as const, label: 'Logs' },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => navigate(-1)} className="text-sm text-blue-600 hover:text-blue-800 mb-1">&larr; Back</button>
          <h2 className="text-2xl font-bold text-gray-900 font-mono">{agent.hostname}</h2>
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
            <StatusBadge status={agent.status} />
            <span>{agent.image}</span>
            <span className="font-mono">{agent.ip || 'No IP'}</span>
          </div>
        </div>
        <div className="text-right text-xs text-gray-400 space-y-0.5">
          <p>ID: <span className="font-mono">{agent.id}</span></p>
          <p>Container: <span className="font-mono">{agent.container_id}</span></p>
          <p>Registered: {new Date(agent.registered_at).toLocaleString()}</p>
        </div>
      </div>

      {/* Quick stats */}
      {latest && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <MiniStat label="CPU" value={`${latest.cpu_pct.toFixed(1)}%`} />
          <MiniStat label="Memory" value={`${Math.round(latest.mem_mb)} MB`} />
          <MiniStat label="Mem Limit" value={`${Math.round(latest.mem_limit_mb)} MB`} />
          <MiniStat label="Net Sent" value={formatBytes(latest.net_bytes_sent)} />
          <MiniStat label="Net Recv" value={formatBytes(latest.net_bytes_recv)} />
          <MiniStat label="Disk Read" value={formatBytes(latest.disk_read_bytes)} />
          <MiniStat label="Disk Write" value={formatBytes(latest.disk_write_bytes)} />
        </div>
      )}

      {/* Tabs */}
      <div className="border-b flex gap-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="CPU Usage (%)">
            <LineChart data={chartPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="cpu" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ChartCard>
          <ChartCard title="Memory Usage (MB)">
            <LineChart data={chartPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="mem" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ChartCard>
          <ChartCard title="Network I/O (bytes, cumulative)">
            <AreaChart data={chartPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={shortBytes} />
              <Tooltip formatter={(v) => formatBytes(Number(v))} />
              <Area type="monotone" dataKey="netSent" stroke="#f59e0b" fill="#fef3c7" strokeWidth={1.5} name="Sent" />
              <Area type="monotone" dataKey="netRecv" stroke="#8b5cf6" fill="#ede9fe" strokeWidth={1.5} name="Received" />
            </AreaChart>
          </ChartCard>
          <ChartCard title="Disk I/O (bytes, cumulative)">
            <AreaChart data={chartPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={shortBytes} />
              <Tooltip formatter={(v) => formatBytes(Number(v))} />
              <Area type="monotone" dataKey="diskRead" stroke="#06b6d4" fill="#cffafe" strokeWidth={1.5} name="Read" />
              <Area type="monotone" dataKey="diskWrite" stroke="#ec4899" fill="#fce7f3" strokeWidth={1.5} name="Write" />
            </AreaChart>
          </ChartCard>
        </div>
      )}

      {tab === 'network' && (
        <DataTable
          columns={['Time', 'Direction', 'Source', 'Destination', 'Port', 'Protocol', 'Bytes']}
          rows={networkEvents.map((e) => [
            new Date(e.timestamp).toLocaleTimeString(),
            <DirectionBadge dir={e.direction} key="dir" />,
            <span className="font-mono" key="src">{e.src_ip}</span>,
            <span className="font-mono" key="dst">{e.dst_ip || '—'}</span>,
            String(e.port),
            e.protocol,
            String(e.bytes),
          ])}
          empty="No network events in the last 24h"
        />
      )}

      {tab === 'filesystem' && (
        <DataTable
          columns={['Time', 'Event', 'Path', 'PID', 'Process']}
          rows={fsEvents.map((e) => [
            new Date(e.timestamp).toLocaleTimeString(),
            <EventBadge type={e.event_type} key="type" />,
            <span className="font-mono text-xs break-all" key="path">{e.path}</span>,
            String(e.pid),
            e.process_name,
          ])}
          empty="No filesystem events in the last 24h"
        />
      )}

      {tab === 'processes' && (
        <DataTable
          columns={['PID', 'Command', 'User', 'Started']}
          rows={uniqueProcesses.map((p) => [
            String(p.pid),
            <span className="font-mono text-xs" key="cmd">{p.command}</span>,
            p.user,
            new Date(p.started_at).toLocaleString(),
          ])}
          empty="No process data"
        />
      )}

      {tab === 'ports' && (
        <DataTable
          columns={['Port', 'Protocol', 'PID', 'Process']}
          rows={uniquePorts.map((p) => [
            String(p.port),
            p.protocol.toUpperCase(),
            String(p.pid),
            p.process_name,
          ])}
          empty="No open ports detected"
        />
      )}

      {tab === 'logs' && agent && (
        <LogViewer
          fixedQuery={`{container=~".*${agent.container_id}.*"}`}
          title={`Logs for ${agent.hostname}`}
        />
      )}
    </div>
  );
}

// ── Helpers ──

function formatBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`;
  return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function shortBytes(b: number): string {
  if (b < 1024) return `${b}`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)}K`;
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(0)}M`;
  return `${(b / (1024 * 1024 * 1024)).toFixed(1)}G`;
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border rounded px-3 py-2">
      <p className="text-[10px] text-gray-500 uppercase">{label}</p>
      <p className="text-sm font-bold text-gray-800 font-mono">{value}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactElement }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

function DirectionBadge({ dir }: { dir: string }) {
  const cls = dir === 'inbound' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700';
  return <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${cls}`}>{dir}</span>;
}

function EventBadge({ type }: { type: string }) {
  const cls = type === 'delete' ? 'bg-red-100 text-red-700'
    : type === 'create' ? 'bg-green-100 text-green-700'
    : 'bg-gray-100 text-gray-700';
  return <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${cls}`}>{type}</span>;
}

function DataTable({ columns, rows, empty }: { columns: string[]; rows: React.ReactNode[][]; empty: string }) {
  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              {columns.map((c) => (
                <th key={c} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-1.5 text-gray-700">{cell}</td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">{empty}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
