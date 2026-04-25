'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '../../components/DashboardShell';

interface AuditLog {
  id: number;
  event_type: string;
  severity: string;
  details: string | null;
  ip_address: string | null;
  user_agent: string | null;
  session_id: string | null;
  created_at: string;
}

function AuditContent() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Placeholder: backend audit endpoint not yet implemented
    // fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/audit`, ...)
    setTimeout(() => {
      setLogs([
        { id: 1, event_type: 'LOGIN', severity: 'Informational', details: 'User logged in successfully', ip_address: '192.168.1.1', user_agent: 'Mozilla/5.0', session_id: 'sess_001', created_at: new Date().toISOString() },
        { id: 2, event_type: 'ASSESSMENT_STARTED', severity: 'Informational', details: 'Assessment session started', ip_address: '192.168.1.2', user_agent: 'Mozilla/5.0', session_id: 'sess_002', created_at: new Date(Date.now() - 3600000).toISOString() },
        { id: 3, event_type: 'TOKEN_ISSUED', severity: 'Medium', details: 'Cross-app token minted', ip_address: '192.168.1.1', user_agent: 'Mozilla/5.0', session_id: 'sess_001', created_at: new Date(Date.now() - 7200000).toISOString() },
      ]);
      setLoading(false);
    }, 500);
  }, []);

  const severityColor = (s: string) => {
    const map: Record<string, string> = {
      Informational: 'bg-blue-50 text-blue-700',
      Medium: 'bg-amber-50 text-amber-700',
      High: 'bg-orange-50 text-orange-700',
      Critical: 'bg-red-50 text-red-700',
    };
    return map[s] || 'bg-gray-100 text-gray-600';
  };

  const filtered = logs.filter((l) =>
    filter ? l.event_type.toLowerCase().includes(filter.toLowerCase()) || (l.details || '').toLowerCase().includes(filter.toLowerCase()) : true
  );

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit Trail</h1>
          <p className="text-sm text-gray-500">Security and compliance event log</p>
        </div>
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter events..."
          className="w-64 rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      <div className="rounded-2xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-6 py-4">Time</th>
              <th className="px-6 py-4">Event</th>
              <th className="px-6 py-4">Severity</th>
              <th className="px-6 py-4">Details</th>
              <th className="px-6 py-4">IP Address</th>
              <th className="px-6 py-4">Session</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                  <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                  No audit logs found.
                </td>
              </tr>
            )}
            {filtered.map((log) => (
              <tr key={log.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-6 py-4 text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                <td className="px-6 py-4 font-medium">{log.event_type}</td>
                <td className="px-6 py-4">
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${severityColor(log.severity)}`}>
                    {log.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-600">{log.details || '—'}</td>
                <td className="px-6 py-4 font-mono text-xs text-gray-500">{log.ip_address || '—'}</td>
                <td className="px-6 py-4 font-mono text-xs text-gray-500">{log.session_id || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
