import { useEffect, useRef, useState } from 'react';

export interface TelemetryMessage {
  type: 'telemetry';
  agent_id: string;
  container_id: string;
  hostname: string;
  timestamp: string;
  resources: {
    cpu_percent: number;
    memory_mb: number;
    memory_limit_mb: number;
    net_bytes_sent: number;
    net_bytes_recv: number;
    disk_read_bytes: number;
    disk_write_bytes: number;
  } | null;
  network_connections: number;
  filesystem_events: number;
  processes: number;
  ports: number;
}

export interface AlertMessage {
  type: 'alert';
  id: string;
  agent_id: string;
  hostname: string;
  container_id: string;
  rule_id: string | null;
  rule_name: string;
  severity: string;
  message: string;
  status: string;
  alert_metadata: Record<string, unknown> | null;
  created_at: string;
}

export type WSMessage = TelemetryMessage | AlertMessage | { type: string; [k: string]: unknown };

export function useWebSocket<T = WSMessage>(path: string) {
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}${path}`;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {
          // ignore malformed messages
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [path]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return { lastMessage, connected };
}
