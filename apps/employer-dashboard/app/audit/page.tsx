'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface AuditLog {
  id: number;
  event_type: string;
  category: string;
  severity: string;
  details: string | null;
  user_email: string | null;
  user_name: string | null;
  assessment_title: string | null;
  ip_address: string | null;
  session_id: string | null;
  created_at: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  Informational: 'bg-blue-50 text-blue-700 border-blue-200',
  Medium: 'bg-amber-50 text-amber-700 border-amber-200',
  High: 'bg-red-50 text-red-700 border-red-200',
  Critical: 'bg-purple-50 text-purple-700 border-purple-200',
};

const SEVERITY_DOT: Record<string, string> = {
  Informational: 'bg-blue-500',
  Medium: 'bg-amber-500',
  High: 'bg-red-500',
  Critical: 'bg-purple-500',
};

const CATEGORIES = [
  'All',
  'Auth',
  'OTP Tokens',
  'Assessment (Candidate)',
  'Evaluation Pipeline',
  'Admin Actions',
  'System',
];

const SEVERITIES = ['All', 'Informational', 'Medium', 'High', 'Critical'];

function AuditContent() {
  const router = useRouter();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterEventType, setFilterEventType] = useState('');
  const [filterCategory, setFilterCategory] = useState('All');
  const [filterSeverity, setFilterSeverity] = useState('All');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [filterUser, setFilterUser] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [toast, setToast] = useState('');
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : '';
  const sseRef = useRef<EventSource | null>(null);

  const handleUnauthorized = (res: Response) => {
    if (res.status === 401) {
      localStorage.clear();
      router.push('/login');
      return true;
    }
    return false;
  };

  const fetchLogs = async () => {
    if (!token) return;
    setLoading(true);
    const params = new URLSearchParams();
    params.append('limit', '500');
    if (filterEventType) params.append('event_type', filterEventType);
    if (filterCategory !== 'All') params.append('category', filterCategory);
    if (filterSeverity !== 'All') params.append('severity', filterSeverity);
    if (filterDateFrom) params.append('date_from', filterDateFrom);
    if (filterDateTo) params.append('date_to', filterDateTo);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/audit/events?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (handleUnauthorized(res)) return;
      if (res.ok) {
        const data = await res.json();
        setLogs(Array.isArray(data) ? data : []);
      }
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  useEffect(() => {
    const timer = setTimeout(fetchLogs, 300);
    return () => clearTimeout(timer);
  }, [filterEventType, filterCategory, filterSeverity, filterDateFrom, filterDateTo]);

  // SSE live stream
  useEffect(() => {
    if (!token) return;
    const es = new EventSource(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/audit/events/stream?token=${token}`);
    sseRef.current = es;
    es.onmessage = (event) => {
      try {
        const newEvent = JSON.parse(event.data);
        const newLog: AuditLog = {
          id: Date.now(),
          event_type: newEvent.event_type,
          category: newEvent.category,
          severity: newEvent.severity,
          details: newEvent.details,
          user_email: newEvent.user_id,
          user_name: null,
          assessment_title: null,
          ip_address: newEvent.ip_address,
          session_id: newEvent.session_id,
          created_at: newEvent.created_at,
        };
        setLogs((prev) => [newLog, ...prev].slice(0, 500));
      } catch {
        // ignore
      }
    };
    es.onerror = () => {
      // silently reconnect or ignore
    };
    return () => {
      es.close();
    };
  }, [token]);

  const filtered = logs.filter((l) => {
    if (filterUser) {
      const u = (l.user_email || '').toLowerCase();
      const n = (l.user_name || '').toLowerCase();
      if (!u.includes(filterUser.toLowerCase()) && !n.includes(filterUser.toLowerCase())) return false;
    }
    return true;
  });

  const exportCSV = () => {
    const headers = ['Timestamp', 'User', 'Event Type', 'Category', 'Severity', 'Details', 'Assessment', 'IP Address', 'Session ID'];
    const rows = filtered.map((l) => [
      new Date(l.created_at).toISOString(),
      l.user_email || l.user_name || '—',
      l.event_type,
      l.category,
      l.severity,
      l.details || '',
      l.assessment_title || '',
      l.ip_address || '',
      l.session_id || '',
    ]);
    const csv = [headers, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-trail-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setToast('CSV exported');
    setTimeout(() => setToast(''), 2000);
  };

  const formatTime = (d: string | null | undefined) => {
    if (!d) return '—';
    return new Date(d).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  };

  return (
    <div className="p-6">
      {toast && <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{toast}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit Trail</h1>
          <p className="text-sm text-gray-500">Security and compliance event log — append only</p>
        </div>
        <button
          onClick={exportCSV}
          className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <input
          type="text"
          value={filterUser}
          onChange={(e) => setFilterUser(e.target.value)}
          placeholder="Search user..."
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <input
          type="text"
          value={filterEventType}
          onChange={(e) => setFilterEventType(e.target.value)}
          placeholder="Event type..."
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={filterDateFrom}
          onChange={(e) => setFilterDateFrom(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <input
          type="date"
          value={filterDateTo}
          onChange={(e) => setFilterDateTo(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        />
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Event Type</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Details</th>
              <th className="px-4 py-3">Assessment</th>
              <th className="px-4 py-3">IP Address</th>
              <th className="px-4 py-3">Session ID</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-400">
                  <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center text-gray-400">
                  No audit logs found.
                </td>
              </tr>
            )}
            {filtered.map((log) => (
              <tr
                key={log.id}
                className="cursor-pointer border-b last:border-0 hover:bg-slate-50"
                onClick={() => setSelectedLog(log)}
              >
                <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">{formatTime(log.created_at)}</td>
                <td className="px-4 py-3">
                  <div className="text-xs font-medium">{log.user_name || '—'}</div>
                  <div className="text-[11px] text-gray-400">{log.user_email || ''}</div>
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                    {log.event_type}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${SEVERITY_COLORS[log.severity] || 'bg-gray-100 text-gray-600'}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[log.severity] || 'bg-gray-400'}`} />
                    {log.severity}
                  </span>
                </td>
                <td className="max-w-[200px] truncate px-4 py-3 text-xs text-gray-600">{log.details || '—'}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{log.assessment_title || '—'}</td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-400">{log.ip_address || '—'}</td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-400">{log.session_id ? log.session_id.slice(0, 12) + '...' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Side Drawer */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={() => setSelectedLog(null)}>
          <div
            className="h-full w-full max-w-md overflow-auto bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-bold">Event Detail</h2>
              <button onClick={() => setSelectedLog(null)} className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Event ID</div>
                <div className="mt-1 font-mono text-sm">{selectedLog.id}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Timestamp</div>
                <div className="mt-1 text-sm">{formatTime(selectedLog.created_at)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Event Type</div>
                <div className="mt-1 text-sm font-medium">{selectedLog.event_type}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Category</div>
                <div className="mt-1 text-sm">{selectedLog.category}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Severity</div>
                <div className="mt-1">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${SEVERITY_COLORS[selectedLog.severity]}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${SEVERITY_DOT[selectedLog.severity]}`} />
                    {selectedLog.severity}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">User</div>
                <div className="mt-1 text-sm">
                  {selectedLog.user_name || '—'} <span className="text-gray-400">({selectedLog.user_email || '—'})</span>
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Assessment</div>
                <div className="mt-1 text-sm">{selectedLog.assessment_title || '—'}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">IP Address</div>
                <div className="mt-1 font-mono text-sm">{selectedLog.ip_address || '—'}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Session ID</div>
                <div className="mt-1 font-mono text-sm break-all">{selectedLog.session_id || '—'}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase text-gray-400">Details</div>
                <div className="mt-1 rounded-lg bg-slate-50 p-3 text-sm text-gray-700">{selectedLog.details || '—'}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AuditPage() {
  return (
    <DashboardShell>
      <AuditContent />
    </DashboardShell>
  );
}
