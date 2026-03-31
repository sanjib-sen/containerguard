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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
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
};
