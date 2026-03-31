import { useState, useEffect, useRef } from 'react';
import { queryLogs, getContainers, getServices } from '../api/logs';
import type { LogEntry } from '../api/logs';

interface Props {
  /** Pre-set LogQL query. If provided, hides the query builder. */
  fixedQuery?: string;
  /** Title shown above the viewer */
  title?: string;
}

const LEVEL_OPTIONS = [
  { value: '', label: 'All levels' },
  { value: 'error', label: 'Error' },
  { value: 'warn', label: 'Warning' },
  { value: 'info', label: 'Info' },
  { value: 'debug', label: 'Debug' },
];

export function LogViewer({ fixedQuery, title }: Props) {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [services, setServices] = useState<string[]>([]);
  const [containers, setContainers] = useState<string[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const [selectedContainer, setSelectedContainer] = useState<string>('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [searchText, setSearchText] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load filter options
  useEffect(() => {
    if (!fixedQuery) {
      getServices().then(setServices).catch(console.error);
      getContainers().then(setContainers).catch(console.error);
    }
  }, [fixedQuery]);

  const buildQuery = () => {
    if (fixedQuery) return fixedQuery;

    // Build label selector
    const labels: string[] = [];
    if (selectedService) {
      labels.push(`service="${selectedService}"`);
    }
    if (selectedContainer) {
      labels.push(`container="${selectedContainer}"`);
    }
    if (labels.length === 0) {
      labels.push('service=~".+"');
    }

    let q = `{${labels.join(', ')}}`;

    // Pipeline filters
    if (levelFilter) {
      q += ` |~ \`(?i)(${levelFilter})\``;
    }
    if (searchText) {
      q += ` |= \`${searchText}\``;
    }
    return q;
  };

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await queryLogs(buildQuery(), 300);
      setEntries(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch + auto-refresh
  useEffect(() => {
    fetchLogs();
    if (!autoRefresh) return;
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fixedQuery, selectedService, selectedContainer, levelFilter, searchText, autoRefresh]);

  const levelColor = (line: string): string => {
    const lower = line.toLowerCase();
    if (lower.includes('error') || lower.includes('traceback') || lower.includes('exception')) return 'text-red-400';
    if (lower.includes('warning') || lower.includes('warn')) return 'text-yellow-400';
    if (lower.includes('info')) return 'text-blue-300';
    if (lower.includes('debug')) return 'text-gray-500';
    return 'text-gray-300';
  };

  const serviceBadgeColor = (service: string): string => {
    if (service === 'agent') return 'text-emerald-400';
    if (service === 'server') return 'text-blue-400';
    if (service.includes('heartbeat')) return 'text-orange-400';
    if (service === 'db') return 'text-purple-400';
    if (service.includes('promtail') || service.includes('loki')) return 'text-yellow-400';
    return 'text-cyan-400';
  };

  return (
    <div className="space-y-3">
      {title && <h3 className="text-xs font-semibold text-gray-500 uppercase">{title}</h3>}

      {/* Controls */}
      {!fixedQuery && (
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedService}
            onChange={(e) => { setSelectedService(e.target.value); setSelectedContainer(''); }}
            className="border rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All services</option>
            {services.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select
            value={selectedContainer}
            onChange={(e) => { setSelectedContainer(e.target.value); setSelectedService(''); }}
            className="border rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All containers</option>
            {containers.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {LEVEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Search text..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <label className="flex items-center gap-1.5 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Live
          </label>
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="px-3 py-1.5 bg-gray-900 text-white text-xs rounded hover:bg-gray-700 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      )}

      {fixedQuery && (
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Live (5s)
          </label>
          <input
            type="text"
            placeholder="Search text..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="border rounded px-2 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-[10px] text-gray-400 font-mono">{fixedQuery}</span>
        </div>
      )}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>
      )}

      {/* Log output */}
      <div className="bg-gray-950 rounded-lg border border-gray-800 overflow-hidden">
        <div ref={scrollRef} className="overflow-y-auto max-h-[600px] p-3 font-mono text-xs leading-5">
          {entries.length === 0 && !loading && (
            <div className="text-gray-600 text-center py-8">No logs found</div>
          )}
          {entries.map((entry, i) => (
            <div key={i} className="flex gap-2 hover:bg-gray-900/50 px-1 -mx-1 rounded">
              <span className="text-gray-600 shrink-0 select-none w-20">
                {entry.timestamp.toLocaleTimeString()}.{String(entry.timestamp.getMilliseconds()).padStart(3, '0')}
              </span>
              {entry.labels.service && (
                <span className={`shrink-0 w-20 truncate ${serviceBadgeColor(entry.labels.service)}`} title={entry.labels.service}>
                  {entry.labels.service}
                </span>
              )}
              <span className={`break-all whitespace-pre-wrap ${levelColor(entry.line)}`}>
                {entry.line}
              </span>
            </div>
          ))}
        </div>
        <div className="border-t border-gray-800 px-3 py-1.5 text-[10px] text-gray-600 flex justify-between">
          <span>{entries.length} log entries</span>
          <span>{autoRefresh ? (loading ? 'Fetching...' : 'Live') : 'Paused'}</span>
        </div>
      </div>
    </div>
  );
}
