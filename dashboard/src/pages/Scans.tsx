import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ScanResult } from '../api/client';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

const SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'];
const SEV_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-200 text-red-900',
  HIGH: 'bg-orange-200 text-orange-900',
  MEDIUM: 'bg-yellow-200 text-yellow-900',
  LOW: 'bg-blue-100 text-blue-700',
  UNKNOWN: 'bg-gray-100 text-gray-600',
};

interface TrivyVuln {
  VulnerabilityID?: string;
  PkgName?: string;
  InstalledVersion?: string;
  FixedVersion?: string;
  Severity?: string;
  Title?: string;
  Description?: string;
  PrimaryURL?: string;
}

interface TrivyResult {
  Target?: string;
  Vulnerabilities?: TrivyVuln[];
}

interface TrivyReport {
  Results?: TrivyResult[];
}

function summarize(scan: ScanResult): Record<string, number> {
  const counts: Record<string, number> = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 };
  if (!scan.vulnerabilities_json || typeof scan.vulnerabilities_json !== 'object' || Array.isArray(scan.vulnerabilities_json)) {
    return counts;
  }
  const report = scan.vulnerabilities_json as TrivyReport;
  if (!report.Results) return counts;
  for (const r of report.Results) {
    for (const v of r.Vulnerabilities || []) {
      const sev = (v.Severity || 'UNKNOWN').toUpperCase();
      counts[sev] = (counts[sev] || 0) + 1;
    }
  }
  return counts;
}

function flattenVulns(scan: ScanResult): TrivyVuln[] {
  const all: TrivyVuln[] = [];
  if (!scan.vulnerabilities_json || typeof scan.vulnerabilities_json !== 'object' || Array.isArray(scan.vulnerabilities_json)) {
    return all;
  }
  const report = scan.vulnerabilities_json as TrivyReport;
  for (const r of report.Results || []) {
    for (const v of r.Vulnerabilities || []) {
      all.push(v);
    }
  }
  // Sort by severity rank
  all.sort((a, b) => SEV_ORDER.indexOf((a.Severity || 'UNKNOWN').toUpperCase()) - SEV_ORDER.indexOf((b.Severity || 'UNKNOWN').toUpperCase()));
  return all;
}

export function Scans() {
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [image, setImage] = useState('alpine:3.14');
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const refresh = () => {
    api.getScans(50).then(setScans).catch(console.error);
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, []);

  const startScan = async () => {
    if (!image.trim()) return;
    setError(null);
    setScanning(true);
    try {
      await api.createScan(image.trim());
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Vulnerability Scans</h2>
        <p className="text-sm text-gray-500 mt-0.5">Scan container images with Trivy</p>
      </div>

      {/* Trigger */}
      <div className="bg-white border rounded-lg p-4 space-y-2">
        <label className="block text-xs font-medium text-gray-600">Image to scan</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={image}
            onChange={(e) => setImage(e.target.value)}
            placeholder="e.g. alpine:3.14, redis:7, python:3.12-slim"
            className="border rounded px-3 py-1.5 text-sm flex-1 font-mono"
          />
          <button
            onClick={startScan}
            disabled={scanning}
            className="px-4 py-1.5 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
          >
            {scanning ? 'Starting...' : 'Scan'}
          </button>
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <div className="flex flex-wrap gap-1.5 pt-2">
          <span className="text-[11px] text-gray-500">Quick:</span>
          {['alpine:3.14', 'redis:7', 'python:3.12-slim', 'node:18', 'nginx:1.21'].map((img) => (
            <button key={img} onClick={() => setImage(img)} className="text-[11px] px-2 py-0.5 bg-gray-100 hover:bg-gray-200 rounded font-mono">
              {img}
            </button>
          ))}
        </div>
      </div>

      {/* Scans list */}
      <div className="bg-white border rounded-lg overflow-hidden">
        {scans.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No scans yet</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {scans.map((scan) => {
              const counts = summarize(scan);
              const totalVulns = Object.values(counts).reduce((s, n) => s + n, 0);
              const expanded = expandedId === scan.id;
              const cls = STATUS_COLORS[scan.status] || 'bg-gray-100 text-gray-700';
              const elapsed = scan.completed_at && scan.started_at
                ? Math.round((new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime()) / 1000)
                : null;
              return (
                <li key={scan.id}>
                  <div className="px-4 py-3 cursor-pointer flex items-center gap-3" onClick={() => setExpandedId(expanded ? null : scan.id)}>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${cls}`}>{scan.status}</span>
                    <span className="font-mono text-sm text-gray-800 w-64 truncate">
                      {scan.image_name}{scan.image_tag ? `:${scan.image_tag}` : ''}
                    </span>
                    <div className="flex gap-1.5">
                      {SEV_ORDER.map((sev) => counts[sev] > 0 && (
                        <span key={sev} className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${SEV_BADGE[sev]}`}>
                          {sev[0]}: {counts[sev]}
                        </span>
                      ))}
                      {totalVulns === 0 && scan.status === 'completed' && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-green-100 text-green-700">CLEAN</span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500 ml-auto">
                      {elapsed !== null ? `${elapsed}s · ` : ''}
                      {new Date(scan.scanned_at).toLocaleString()}
                    </span>
                  </div>

                  {expanded && (
                    <div className="px-4 pb-4 ml-3 space-y-2">
                      {scan.error_message && (
                        <pre className="text-xs bg-red-50 text-red-800 p-3 rounded">{scan.error_message}</pre>
                      )}
                      {scan.status === 'completed' && (
                        <VulnTable vulns={flattenVulns(scan)} />
                      )}
                      {scan.status === 'pending' && (
                        <p className="text-sm text-gray-500 italic">Scan in progress...</p>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

function VulnTable({ vulns }: { vulns: TrivyVuln[] }) {
  if (vulns.length === 0) {
    return <p className="text-sm text-green-700 italic">No vulnerabilities found.</p>;
  }
  return (
    <div className="border rounded overflow-hidden">
      <div className="overflow-y-auto max-h-96">
        <table className="min-w-full divide-y divide-gray-200 text-xs">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">Severity</th>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">CVE</th>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">Package</th>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">Installed</th>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">Fixed In</th>
              <th className="px-3 py-1.5 text-left font-medium text-gray-500 uppercase">Title</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {vulns.map((v, i) => {
              const sev = (v.Severity || 'UNKNOWN').toUpperCase();
              return (
                <tr key={`${v.VulnerabilityID}-${i}`} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${SEV_BADGE[sev]}`}>{sev}</span></td>
                  <td className="px-3 py-1.5 font-mono">
                    {v.PrimaryURL ? <a href={v.PrimaryURL} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{v.VulnerabilityID}</a> : v.VulnerabilityID}
                  </td>
                  <td className="px-3 py-1.5 font-mono text-gray-700">{v.PkgName}</td>
                  <td className="px-3 py-1.5 font-mono text-gray-700">{v.InstalledVersion}</td>
                  <td className="px-3 py-1.5 font-mono text-green-700">{v.FixedVersion || '—'}</td>
                  <td className="px-3 py-1.5 text-gray-600 max-w-md truncate">{v.Title}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
