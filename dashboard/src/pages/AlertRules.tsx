import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { AlertRule, AlertRuleInput } from '../api/client';

const METRICS = [
  { value: 'cpu_pct', label: 'CPU %' },
  { value: 'mem_mb', label: 'Memory (MB)' },
  { value: 'mem_pct', label: 'Memory %' },
  { value: 'net_bytes_sent', label: 'Network sent (bytes)' },
  { value: 'net_bytes_recv', label: 'Network received (bytes)' },
  { value: 'disk_read_bytes', label: 'Disk read (bytes)' },
  { value: 'disk_write_bytes', label: 'Disk write (bytes)' },
];

const OPERATORS = [
  { value: 'gt', label: '>' },
  { value: 'ge', label: '>=' },
  { value: 'lt', label: '<' },
  { value: 'le', label: '<=' },
  { value: 'eq', label: '=' },
  { value: 'ne', label: '!=' },
];

const SEVERITIES = ['low', 'medium', 'high', 'critical'];

const EMPTY: AlertRuleInput = {
  name: '',
  description: '',
  metric: 'cpu_pct',
  operator: 'gt',
  threshold: 80,
  severity: 'high',
  cooldown_sec: 300,
  enabled: true,
};

export function AlertRules() {
  const navigate = useNavigate();
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState<AlertRuleInput>(EMPTY);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    api.getAlertRules().then(setRules).catch(console.error);
  };

  useEffect(() => {
    refresh();
  }, []);

  const submit = async () => {
    setError(null);
    try {
      await api.createAlertRule(draft);
      setDraft(EMPTY);
      setShowForm(false);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const toggle = async (rule: AlertRule) => {
    await api.updateAlertRule(rule.id, { enabled: !rule.enabled });
    refresh();
  };

  const remove = async (id: string) => {
    if (!confirm('Delete this rule?')) return;
    await api.deleteAlertRule(id);
    refresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => navigate('/alerts')} className="text-sm text-blue-600 hover:underline mb-1">&larr; Back to alerts</button>
          <h2 className="text-2xl font-bold text-gray-900">Alert Rules</h2>
          <p className="text-sm text-gray-500 mt-0.5">Threshold-based rules evaluated on every telemetry batch</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-700"
        >
          {showForm ? 'Cancel' : '+ New Rule'}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-800">Create Alert Rule</h3>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Name">
              <input
                type="text"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                className="border rounded px-2 py-1.5 text-sm w-full"
                placeholder="High CPU"
              />
            </Field>
            <Field label="Severity">
              <select
                value={draft.severity}
                onChange={(e) => setDraft({ ...draft, severity: e.target.value })}
                className="border rounded px-2 py-1.5 text-sm w-full"
              >
                {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Description" className="col-span-2">
              <input
                type="text"
                value={draft.description ?? ''}
                onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                className="border rounded px-2 py-1.5 text-sm w-full"
              />
            </Field>
            <Field label="Metric">
              <select
                value={draft.metric}
                onChange={(e) => setDraft({ ...draft, metric: e.target.value })}
                className="border rounded px-2 py-1.5 text-sm w-full"
              >
                {METRICS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Operator">
                <select
                  value={draft.operator}
                  onChange={(e) => setDraft({ ...draft, operator: e.target.value })}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                >
                  {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </Field>
              <Field label="Threshold">
                <input
                  type="number"
                  step="0.1"
                  value={draft.threshold}
                  onChange={(e) => setDraft({ ...draft, threshold: parseFloat(e.target.value) || 0 })}
                  className="border rounded px-2 py-1.5 text-sm w-full"
                />
              </Field>
            </div>
            <Field label="Cooldown (seconds)">
              <input
                type="number"
                value={draft.cooldown_sec}
                onChange={(e) => setDraft({ ...draft, cooldown_sec: parseInt(e.target.value) || 0 })}
                className="border rounded px-2 py-1.5 text-sm w-full"
              />
            </Field>
            <Field label="Enabled">
              <label className="flex items-center gap-2 mt-1.5">
                <input
                  type="checkbox"
                  checked={draft.enabled}
                  onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
                />
                <span className="text-sm text-gray-700">Active</span>
              </label>
            </Field>
          </div>
          {error && <div className="text-sm text-red-600">{error}</div>}
          <div className="flex gap-2">
            <button onClick={submit} className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700">
              Create
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Condition</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Cooldown</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map((rule) => {
              const opLabel = OPERATORS.find((o) => o.value === rule.operator)?.label || rule.operator;
              return (
                <tr key={rule.id}>
                  <td className="px-4 py-2 font-medium text-gray-800">
                    {rule.name}
                    {rule.description && <p className="text-xs text-gray-500 font-normal mt-0.5">{rule.description}</p>}
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">{rule.metric} {opLabel} {rule.threshold}</td>
                  <td className="px-4 py-2"><span className="text-xs uppercase font-bold">{rule.severity}</span></td>
                  <td className="px-4 py-2 text-gray-600">{rule.cooldown_sec}s</td>
                  <td className="px-4 py-2">
                    <button onClick={() => toggle(rule)} className={`text-xs px-2 py-0.5 rounded ${rule.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {rule.enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </td>
                  <td className="px-4 py-2">
                    <button onClick={() => remove(rule.id)} className="text-xs text-red-600 hover:underline">Delete</button>
                  </td>
                </tr>
              );
            })}
            {rules.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No rules. Create one above to start receiving alerts.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Field({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  );
}
