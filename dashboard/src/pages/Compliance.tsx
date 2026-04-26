import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { ComplianceRule, ComplianceResult, Agent, ComplianceRuleInput } from '../api/client';

const RULE_PRESETS: { label: string; name: string; description: string; rule_json: Record<string, unknown>; severity: string }[] = [
  {
    label: 'No Root Processes',
    name: 'no-root-processes',
    description: 'Disallow processes running as root (except PID 1)',
    rule_json: { type: 'no_root_processes', allow_pids: [1] },
    severity: 'high',
  },
  {
    label: 'Authorized Ports Only',
    name: 'authorized-ports-only',
    description: 'Only expected ports may listen',
    rule_json: { type: 'no_unauthorized_ports', allowed_ports: [80, 443, 8080, 8000] },
    severity: 'medium',
  },
  {
    label: 'No Sensitive Path Access',
    name: 'no-sensitive-path-access',
    description: 'Block reads/writes on sensitive system paths',
    rule_json: { type: 'no_sensitive_paths', paths: ['/etc/shadow', '/etc/passwd', '/root', '/etc/sudoers'] },
    severity: 'critical',
  },
  {
    label: 'Internal Network Allowlist',
    name: 'internal-network-only',
    description: 'Outbound connections must stay in private CIDRs',
    rule_json: { type: 'network_allowlist', allowed_cidrs: ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'] },
    severity: 'high',
  },
  {
    label: 'Block Known Bad IPs',
    name: 'block-known-bad-ips',
    description: 'Demo blocklist',
    rule_json: { type: 'network_blocklist', blocked_ips: ['1.1.1.1', '8.8.8.8'] },
    severity: 'high',
  },
];

const STATUS_COLORS: Record<string, string> = {
  pass: 'bg-green-100 text-green-700',
  fail: 'bg-red-100 text-red-700',
  error: 'bg-orange-100 text-orange-700',
  skip: 'bg-gray-100 text-gray-500',
};

export function Compliance() {
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [results, setResults] = useState<ComplianceResult[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ComplianceRuleInput>({
    name: '',
    description: '',
    severity: 'medium',
    rule_json: { type: 'no_root_processes', allow_pids: [1] },
    enabled: true,
  });
  const [draftJson, setDraftJson] = useState(JSON.stringify(draft.rule_json, null, 2));

  const refresh = () => {
    api.getComplianceRules().then(setRules).catch(console.error);
    api.getComplianceStatus().then(setResults).catch(console.error);
  };

  useEffect(() => {
    refresh();
    api.getAgents().then(setAgents).catch(console.error);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => api.getComplianceStatus().then(setResults).catch(console.error), 10000);
    return () => clearInterval(interval);
  }, []);

  const ruleMap = useMemo(() => {
    const m = new Map<string, ComplianceRule>();
    rules.forEach((r) => m.set(r.id, r));
    return m;
  }, [rules]);

  const hostnameMap = useMemo(() => {
    const m = new Map<string, string>();
    agents.forEach((a) => m.set(a.id, a.hostname));
    return m;
  }, [agents]);

  const usePreset = (i: number) => {
    const p = RULE_PRESETS[i];
    setDraft({
      name: p.name,
      description: p.description,
      rule_json: p.rule_json,
      severity: p.severity,
      enabled: true,
    });
    setDraftJson(JSON.stringify(p.rule_json, null, 2));
  };

  const submit = async () => {
    setError(null);
    let parsedJson: Record<string, unknown>;
    try {
      parsedJson = JSON.parse(draftJson);
    } catch {
      setError('rule_json must be valid JSON');
      return;
    }
    try {
      await api.createComplianceRule({ ...draft, rule_json: parsedJson });
      setShowForm(false);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const remove = async (id: string) => {
    if (!confirm('Delete this rule?')) return;
    await api.deleteComplianceRule(id);
    refresh();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Compliance</h2>
          <p className="text-sm text-gray-500 mt-0.5">Policy rules evaluated against telemetry — violations create alerts</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="px-3 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-700">
          {showForm ? 'Cancel' : '+ New Rule'}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-4 space-y-3">
          <h3 className="font-semibold text-gray-800">Create Compliance Rule</h3>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Quick presets</label>
            <div className="flex flex-wrap gap-2">
              {RULE_PRESETS.map((p, i) => (
                <button key={p.name} onClick={() => usePreset(i)} className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded">
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input type="text" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} className="border rounded px-2 py-1.5 text-sm w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
              <select value={draft.severity} onChange={(e) => setDraft({ ...draft, severity: e.target.value })} className="border rounded px-2 py-1.5 text-sm w-full">
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
              <input type="text" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} className="border rounded px-2 py-1.5 text-sm w-full" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-600 mb-1">Rule JSON</label>
              <textarea value={draftJson} onChange={(e) => setDraftJson(e.target.value)} rows={8} className="border rounded px-2 py-1.5 text-xs font-mono w-full" />
            </div>
          </div>
          {error && <div className="text-sm text-red-600">{error}</div>}
          <button onClick={submit} className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700">Create</button>
        </div>
      )}

      {/* Rules list */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Active Rules ({rules.length})</h3>
        <div className="bg-white border rounded-lg overflow-hidden">
          {rules.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">No compliance rules. Create one to start evaluating.</div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td className="px-4 py-2 font-medium text-gray-800">
                      {rule.name}
                      <p className="text-xs text-gray-500 font-normal mt-0.5">{rule.description}</p>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{String(rule.rule_json.type ?? '')}</td>
                    <td className="px-4 py-2"><span className="text-xs uppercase font-bold">{rule.severity}</span></td>
                    <td className="px-4 py-2"><button onClick={() => remove(rule.id)} className="text-xs text-red-600 hover:underline">Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* Latest results */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Latest Status (per agent / per rule)</h3>
        <div className="bg-white border rounded-lg overflow-hidden">
          {results.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">No evaluation results yet</div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {results.map((r) => {
                const rule = ruleMap.get(r.rule_id);
                const hostname = hostnameMap.get(r.agent_id) || r.agent_id.slice(0, 8);
                const expanded = expandedId === r.id;
                const cls = STATUS_COLORS[r.status] || 'bg-gray-100 text-gray-700';
                return (
                  <li key={r.id}>
                    <div className="px-4 py-2.5 cursor-pointer flex items-center gap-3" onClick={() => setExpandedId(expanded ? null : r.id)}>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${cls}`}>{r.status}</span>
                      <span className="font-mono text-xs text-gray-700 w-32 truncate">{hostname}</span>
                      <span className="text-sm text-gray-800 flex-1">{rule?.name || r.rule_id.slice(0, 8)}</span>
                      <span className="text-xs text-gray-500">{(r.details as { summary?: string } | null)?.summary || ''}</span>
                      <span className="text-xs text-gray-400">{new Date(r.evaluated_at).toLocaleTimeString()}</span>
                    </div>
                    {expanded && r.details && (
                      <pre className="ml-12 mr-4 mb-3 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
                        {JSON.stringify(r.details, null, 2)}
                      </pre>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
