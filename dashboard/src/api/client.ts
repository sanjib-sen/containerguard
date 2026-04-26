const BASE = '/api/v1';

export interface Agent {
  id: string;
  container_id: string;
  hostname: string;
  image: string;
  ip: string | null;
  status: string;
  registered_at: string;
  last_heartbeat: string;
}

export interface ResourceSnapshot {
  id: string;
  agent_id: string;
  cpu_pct: number;
  mem_mb: number;
  mem_limit_mb: number;
  net_bytes_sent: number;
  net_bytes_recv: number;
  disk_read_bytes: number;
  disk_write_bytes: number;
  timestamp: string;
}

export interface NetworkEvent {
  id: string;
  agent_id: string;
  direction: string;
  src_ip: string;
  dst_ip: string | null;
  port: number;
  protocol: string;
  bytes: number;
  timestamp: string;
}

export interface FilesystemEvent {
  id: string;
  agent_id: string;
  event_type: string;
  path: string;
  pid: number;
  process_name: string;
  timestamp: string;
}

export interface ProcessSnapshot {
  id: string;
  agent_id: string;
  pid: number;
  command: string;
  user: string;
  started_at: string;
  timestamp: string;
}

export interface PortSnapshot {
  id: string;
  agent_id: string;
  port: number;
  protocol: string;
  pid: number;
  process_name: string;
  timestamp: string;
}

// ── Alerts ─────────────────────────────────────────────────────────

export interface AlertRule {
  id: string;
  name: string;
  description: string | null;
  metric: string;
  operator: string;
  threshold: number;
  severity: string;
  cooldown_sec: number;
  enabled: boolean;
}

export interface AlertRuleInput {
  name: string;
  description?: string | null;
  metric: string;
  operator: string;
  threshold: number;
  severity: string;
  cooldown_sec: number;
  enabled: boolean;
}

export interface Alert {
  id: string;
  agent_id: string;
  rule_id: string | null;
  rule_name: string;
  severity: string;
  message: string;
  status: string;
  alert_metadata: Record<string, unknown> | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

// ── Compliance ─────────────────────────────────────────────────────

export interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  rule_json: Record<string, unknown>;
  severity: string;
  enabled: boolean;
}

export interface ComplianceRuleInput {
  name: string;
  description: string;
  rule_json: Record<string, unknown>;
  severity: string;
  enabled: boolean;
}

export interface ComplianceResult {
  id: string;
  agent_id: string;
  rule_id: string;
  status: string;
  details: Record<string, unknown> | null;
  evaluated_at: string;
}

// ── Scans ──────────────────────────────────────────────────────────

export interface ScanResult {
  id: string;
  image_name: string;
  image_tag: string | null;
  status: string;
  vulnerabilities_json: Record<string, unknown> | unknown[] | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  scanned_at: string;
  agent_id: string | null;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function jsonRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Agents
  getAgents: () => get<Agent[]>('/agents/'),
  getAgent: (id: string) => get<Agent>(`/agents/${id}`),

  // Global telemetry
  getLatestResources: () => get<ResourceSnapshot[]>('/telemetry/latest-resources'),
  getResources: (hours = 24, limit = 500) =>
    get<ResourceSnapshot[]>(`/telemetry/resources?hours=${hours}&limit=${limit}`),
  getNetwork: (hours = 24, limit = 500) =>
    get<NetworkEvent[]>(`/telemetry/network?hours=${hours}&limit=${limit}`),
  getFilesystem: (hours = 24, limit = 500) =>
    get<FilesystemEvent[]>(`/telemetry/filesystem?hours=${hours}&limit=${limit}`),

  // Per-agent telemetry
  getAgentResources: (agentId: string, hours = 1, limit = 200) =>
    get<ResourceSnapshot[]>(`/telemetry/${agentId}/resources?hours=${hours}&limit=${limit}`),
  getAgentNetwork: (agentId: string, hours = 24, limit = 500) =>
    get<NetworkEvent[]>(`/telemetry/${agentId}/network?hours=${hours}&limit=${limit}`),
  getAgentFilesystem: (agentId: string, hours = 24, limit = 500) =>
    get<FilesystemEvent[]>(`/telemetry/${agentId}/filesystem?hours=${hours}&limit=${limit}`),
  getAgentProcesses: (agentId: string, hours = 1, limit = 200) =>
    get<ProcessSnapshot[]>(`/telemetry/${agentId}/processes?hours=${hours}&limit=${limit}`),
  getAgentPorts: (agentId: string, hours = 1, limit = 200) =>
    get<PortSnapshot[]>(`/telemetry/${agentId}/ports?hours=${hours}&limit=${limit}`),

  // Alerts
  getAlerts: (params: { agent_id?: string; status?: string; severity?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.agent_id) q.set('agent_id', params.agent_id);
    if (params.status) q.set('status', params.status);
    if (params.severity) q.set('severity', params.severity);
    if (params.limit) q.set('limit', String(params.limit));
    return get<Alert[]>(`/alerts/?${q}`);
  },
  setAlertStatus: (alertId: string, status: string) =>
    jsonRequest<Alert>('PATCH', `/alerts/${alertId}`, { status }),

  // Alert Rules
  getAlertRules: () => get<AlertRule[]>('/alerts/rules/'),
  createAlertRule: (rule: AlertRuleInput) => jsonRequest<AlertRule>('POST', '/alerts/rules/', rule),
  updateAlertRule: (id: string, rule: Partial<AlertRuleInput>) =>
    jsonRequest<AlertRule>('PATCH', `/alerts/rules/${id}`, rule),
  deleteAlertRule: (id: string) => jsonRequest<void>('DELETE', `/alerts/rules/${id}`),

  // Compliance
  getComplianceRules: () => get<ComplianceRule[]>('/compliance/rules/'),
  createComplianceRule: (rule: ComplianceRuleInput) =>
    jsonRequest<ComplianceRule>('POST', '/compliance/rules/', rule),
  deleteComplianceRule: (id: string) => jsonRequest<void>('DELETE', `/compliance/rules/${id}`),
  getComplianceResults: (params: { agent_id?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.agent_id) q.set('agent_id', params.agent_id);
    if (params.limit) q.set('limit', String(params.limit));
    return get<ComplianceResult[]>(`/compliance/results/?${q}`);
  },
  getComplianceStatus: () => get<ComplianceResult[]>('/compliance/status/'),

  // Scans
  getScans: (limit = 100) => get<ScanResult[]>(`/scans/?limit=${limit}`),
  getScan: (id: string) => get<ScanResult>(`/scans/${id}`),
  createScan: (image: string, agentId?: string) =>
    jsonRequest<ScanResult>('POST', '/scans/', { image, agent_id: agentId }),
};
