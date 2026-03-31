import { LogViewer } from '../components/LogViewer';

export function Logs() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Logs</h2>
        <p className="text-sm text-gray-500 mt-0.5">Live container logs from all services via Loki</p>
      </div>
      <LogViewer />
    </div>
  );
}
