const BASE = '/api/v1/logs';

export interface LogStream {
  stream: Record<string, string>;
  values: [string, string][]; // [nanosecond timestamp, log line]
}

export interface LokiQueryResult {
  status: string;
  data: {
    resultType: string;
    result: LogStream[];
  };
}

export interface LogEntry {
  timestamp: Date;
  line: string;
  labels: Record<string, string>;
}

function parseResult(data: LokiQueryResult): LogEntry[] {
  const entries: LogEntry[] = [];
  for (const stream of data.data.result) {
    for (const [nsTimestamp, line] of stream.values) {
      entries.push({
        timestamp: new Date(Number(nsTimestamp) / 1_000_000),
        line,
        labels: stream.stream,
      });
    }
  }
  // Sort newest first
  entries.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  return entries;
}

export async function queryLogs(query: string, limit = 200): Promise<LogEntry[]> {
  const params = new URLSearchParams({
    query,
    limit: String(limit),
    direction: 'backward',
  });
  const res = await fetch(`${BASE}/query?${params}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data: LokiQueryResult = await res.json();
  return parseResult(data);
}

export async function getServices(): Promise<string[]> {
  const res = await fetch(`${BASE}/labels/service/values`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.data || [];
}

export async function getContainers(): Promise<string[]> {
  const res = await fetch(`${BASE}/labels/container/values`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.data || [];
}
