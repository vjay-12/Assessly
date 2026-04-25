'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '../../components/DashboardShell';

interface Candidate {
  id: string;
  full_name: string;
  email: string;
  is_verified: boolean;
  application_status: string | null;
  score_percentage: number | null;
}

function CandidatesContent() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/candidates?limit=100`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setCandidates(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = candidates.filter(
    (c) =>
      c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.email.toLowerCase().includes(search.toLowerCase())
  );

  const statusBadge = (status: string | null) => {
    if (!status) return <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">—</span>;
    const map: Record<string, string> = {
      applied: 'bg-blue-50 text-blue-700',
      attempted: 'bg-amber-50 text-amber-700',
      submitted: 'bg-purple-50 text-purple-700',
      evaluated: 'bg-green-50 text-green-700',
    };
    return (
      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${map[status] || 'bg-gray-100 text-gray-600'}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Candidates</h1>
          <p className="text-sm text-gray-500">Track candidate progress through the assessment pipeline</p>
        </div>
        <div className="w-72">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email..."
            className="w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          />
        </div>
      </div>

      <div className="rounded-2xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-6 py-4">Candidate</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Progress</th>
              <th className="px-6 py-4">Score</th>
              <th className="px-6 py-4">Verified</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                  <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-gray-400">
                  No candidates found.
                </td>
              </tr>
            )}
            {filtered.map((c) => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-6 py-4">
                  <div className="font-medium">{c.full_name}</div>
                  <div className="text-gray-500">{c.email}</div>
                </td>
                <td className="px-6 py-4">{statusBadge(c.application_status)}</td>
                <td className="px-6 py-4">
                  <div className="h-2 w-32 rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{
                        width:
                          c.application_status === 'evaluated'
                            ? '100%'
                            : c.application_status === 'submitted'
                            ? '75%'
                            : c.application_status === 'attempted'
                            ? '50%'
                            : '25%',
                      }}
                    />
                  </div>
                </td>
                <td className="px-6 py-4">
                  {c.score_percentage !== null ? (
                    <span className="font-semibold">{c.score_percentage.toFixed(1)}%</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {c.is_verified ? (
                    <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">✓ YES</span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-500">NO</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function CandidatesPage() {
  return (
    <DashboardShell>
      <CandidatesContent />
    </DashboardShell>
  );
}
