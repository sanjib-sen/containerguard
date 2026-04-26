import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { Alert, Agent } from '../api/client';

const SEV_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-red-100 text-red-700',
  acknowledged: 'bg-yellow-100 text-yellow-700',
  resolved: 'bg-green-100 text-green-700',
};

export function Alerts() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchAlerts = () => {
    api.getAlerts({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
      limit: 500,
    }).then(setAlerts).catch(console.error);
  };

  useEffect(() => {
    api.getAgents().then(setAgents).catch(console.error);
  }, []);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, severityFilter]);

  const hostnameMap = useMemo(() => {
    const m = new Map<string, string>();
    agents.forEach((a) => m.set(a.id, a.hostname));
    return m;
  }, [agents]);

  const counts = useMemo(() => {
    const c = { all: alerts.length, open: 0, acknowledged: 0, resolved: 0 };
    alerts.forEach((a) => {
      if (a.status in c) (c as Record<string, number>)[a.status]++;
    });
    return c;
  }, [alerts]);

  const updateStatus = async (id: string, newStatus: string) => {
    await api.setAlertStatus(id, newStatus);
    fetchAlerts();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Alerts</h2>
          <p className="text-sm text-gray-500 mt-0.5">Threshold breaches, anomalies, and compliance violations</p>
        </div>
        <button
          onClick={() => navigate('/alerts/rules')}
          className="px-3 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-700"
        >
          Manage Rules
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1">
          <FilterChip label={`All (${counts.all})`} active={!statusFilter} onClick={() => setStatusFilter('')} />
          <FilterChip label={`Open (${counts.open})`} active={statusFilter === 'open'} onClick={() => setStatusFilter('open')} />
          <FilterChip label={`Ack'd (${counts.acknowledged})`} active={statusFilter === 'acknowledged'} onClick={() => setStatusFilter('acknowledged')} />
          <FilterChip label={`Resolved (${counts.resolved})`} active={statusFilter === 'resolved'} onClick={() => setStatusFilter('resolved')} />
        </div>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="border rounded px-2 py-1.5 text-sm bg-white"
        >
          <option value="">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <button onClick={fetchAlerts} className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200">
          Refresh
        </button>
      </div>

      {/* Alert list */}
      <div className="bg-white border rounded-lg overflow-hidden">
        {alerts.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No alerts</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {alerts.map((alert) => {
              const hostname = hostnameMap.get(alert.agent_id) || alert.agent_id.slice(0, 12);
              const sevCls = SEV_COLORS[alert.severity] || 'bg-gray-100 text-gray-700 border-gray-200';
              const statusCls = STATUS_COLORS[alert.status] || 'bg-gray-100 text-gray-700';
              const expanded = expandedId === alert.id;
              return (
                <li key={alert.id} className="hover:bg-gray-50">
                  <div
                    className="px-4 py-3 cursor-pointer flex items-start gap-3"
                    onClick={() => setExpandedId(expanded ? null : alert.id)}
                  >
                    <span className={`mt-0.5 px-2 py-0.5 rounded border text-[11px] font-bold uppercase tracking-wide shrink-0 ${sevCls}`}>
                      {alert.severity}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-900">{alert.rule_name}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${statusCls}`}>{alert.status}</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/agents/${alert.agent_id}`); }}
                          className="text-xs text-blue-600 hover:underline font-mono"
                        >
                          {hostname}
                        </button>
                        <span className="text-xs text-gray-400 ml-auto">{new Date(alert.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 break-words">{alert.message}</p>
                    </div>
                  </div>

                  {expanded && (
                    <div className="px-4 pb-3 ml-12 space-y-2">
                      {alert.alert_metadata && (
                        <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                          {JSON.stringify(alert.alert_metadata, null, 2)}
                        </pre>
                      )}
                      <div className="flex gap-2">
                        {alert.status === 'open' && (
                          <button
                            onClick={() => updateStatus(alert.id, 'acknowledged')}
                            className="px-3 py-1 bg-yellow-500 text-white text-xs rounded hover:bg-yellow-600"
                          >
                            Acknowledge
                          </button>
                        )}
                        {alert.status !== 'resolved' && (
                          <button
                            onClick={() => updateStatus(alert.id, 'resolved')}
                            className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                          >
                            Resolve
                          </button>
                        )}
                        {alert.status !== 'open' && (
                          <button
                            onClick={() => updateStatus(alert.id, 'open')}
                            className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300"
                          >
                            Re-open
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function FilterChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
        active ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      {label}
    </button>
  );
}
