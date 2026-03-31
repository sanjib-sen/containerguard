import { useEffect, useRef, useState } from 'react';

export interface TelemetryMessage {
  type: string;
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

export function useWebSocket(path: string) {
  const [lastMessage, setLastMessage] = useState<TelemetryMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}${path}`;

    function connect() {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, 3000);
      };
      ws.onmessage = (event) => {
        try {
          setLastMessage(JSON.parse(event.data));
        } catch {}
      };
    }

    connect();

    return () => {
      wsRef.current?.close();
    };
  }, [path]);

  // Send a keepalive ping so the server's receive_text() doesn't block forever
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
