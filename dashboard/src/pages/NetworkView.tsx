import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { NetworkEvent } from '../api/client';

export function NetworkView() {
  const [events, setEvents] = useState<NetworkEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getNetwork(24, 200).then((data) => {
      setEvents(data);
      setLoading(false);
    }).catch(console.error);
  }, []);

  // Refresh every 15s
  useEffect(() => {
    const interval = setInterval(() => {
      api.getNetwork(24, 200).then(setEvents).catch(console.error);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold text-gray-900">Network Activity</h2>
      <div className="bg-white border rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Direction</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source IP</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Dest IP</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Protocol</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bytes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {events.map((e) => (
              <tr key={e.id}>
                <td className="px-4 py-2 text-sm text-gray-500">{new Date(e.timestamp).toLocaleTimeString()}</td>
                <td className="px-4 py-2 text-sm">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    e.direction === 'inbound' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'
                  }`}>
                    {e.direction}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm font-mono text-gray-700">{e.src_ip}</td>
                <td className="px-4 py-2 text-sm font-mono text-gray-700">{e.dst_ip || '—'}</td>
                <td className="px-4 py-2 text-sm text-gray-700">{e.port}</td>
                <td className="px-4 py-2 text-sm text-gray-600">{e.protocol}</td>
                <td className="px-4 py-2 text-sm text-gray-600">{e.bytes}</td>
              </tr>
            ))}
            {!loading && events.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No network events</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
