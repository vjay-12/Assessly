'use client';

import { useEffect, useState } from 'react';
import DashboardShell from '../../components/DashboardShell';

interface Score {
  id: string;
  application_id: string;
  candidate_name: string;
  percentage: number;
  correct_count: number;
  total_questions: number;
  evaluated_at: string;
}

function ScoresContent() {
  const [scores, setScores] = useState<Score[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const url = new URL(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/scores`);
    url.searchParams.set('limit', '100');
    if (minScore) url.searchParams.set('min_score', minScore);

    fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setScores(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [minScore]);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scores</h1>
          <p className="text-sm text-gray-500">Review evaluated assessment results</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">Min score:</span>
          <input
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="0"
            className="w-24 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          />
        </div>
      </div>

      <div className="rounded-2xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-6 py-4">Candidate</th>
              <th className="px-6 py-4">Score</th>
              <th className="px-6 py-4">Correct</th>
              <th className="px-6 py-4">Total</th>
              <th className="px-6 py-4">Evaluated</th>
              <th className="px-6 py-4">Result</th>
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
            {!loading && scores.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                  No scores found.
                </td>
              </tr>
            )}
            {scores.map((s) => (
              <tr key={s.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-6 py-4 font-medium">{s.candidate_name}</td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="h-2 w-24 rounded-full bg-gray-100">
                      <div
                        className={`h-full rounded-full ${s.percentage >= 50 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${s.percentage}%` }}
                      />
                    </div>
                    <span className="font-semibold">{s.percentage.toFixed(1)}%</span>
                  </div>
                </td>
                <td className="px-6 py-4">{s.correct_count}</td>
                <td className="px-6 py-4">{s.total_questions}</td>
                <td className="px-6 py-4 text-gray-500">
                  {s.evaluated_at ? new Date(s.evaluated_at).toLocaleString() : '—'}
                </td>
                <td className="px-6 py-4">
                  {s.percentage >= 50 ? (
                    <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">PASS</span>
                  ) : (
                    <span className="rounded-full bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">FAIL</span>
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

export default function ScoresPage() {
  return (
    <DashboardShell>
      <ScoresContent />
    </DashboardShell>
  );
}
