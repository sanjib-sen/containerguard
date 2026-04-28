import { useMemo, useState } from 'react';

const defaultGrafanaUrl =
  'http://localhost:3001/d/containerguard-main/containerguard?orgId=1&from=now-1h&to=now&timezone=browser&var-hostname=$__all&var-log_service=$__all&refresh=10s&kiosk';

const grafanaUrl = import.meta.env.VITE_GRAFANA_DASHBOARD_URL || defaultGrafanaUrl;

const ranges = [
  { label: '15m', from: 'now-15m' },
  { label: '1h', from: 'now-1h' },
  { label: '6h', from: 'now-6h' },
  { label: '24h', from: 'now-24h' },
];

function buildGrafanaUrl(from: string) {
  const url = new URL(grafanaUrl);

  url.searchParams.set('from', from);
  url.searchParams.set('to', 'now');
  url.searchParams.set('timezone', 'browser');
  url.searchParams.set('var-hostname', url.searchParams.get('var-hostname') || '$__all');
  url.searchParams.set('var-log_service', url.searchParams.get('var-log_service') || '$__all');

  if (!url.searchParams.has('refresh')) {
    url.searchParams.set('refresh', '10s');
  }

  if (!url.searchParams.has('kiosk')) {
    url.searchParams.set('kiosk', '');
  }

  return url.toString();
}

export function Metrics() {
  const [range, setRange] = useState(ranges[1]);
  const src = useMemo(() => buildGrafanaUrl(range.from), [range]);

  return (
    <div className="h-[calc(100vh-3rem)] min-h-[720px] flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Metrics</h2>
          <p className="text-sm text-gray-500">ContainerGuard / Grafana</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex rounded border border-gray-300 bg-white p-0.5">
            {ranges.map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() => setRange(option)}
                className={`px-3 py-1.5 text-sm rounded ${
                  range.label === option.label
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <a
            href={src}
            target="_blank"
            rel="noreferrer"
            className="px-3 py-2 rounded bg-white border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
          >
            Open Grafana
          </a>
        </div>
      </div>

      <div className="flex-1 overflow-hidden rounded border border-gray-200 bg-white shadow-sm">
        <iframe
          key={src}
          title="ContainerGuard Grafana metrics"
          src={src}
          className="h-full w-full border-0"
          loading="lazy"
        />
      </div>
    </div>
  );
}
