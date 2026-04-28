'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface Score {
  id: string;
  application_id: string;
  candidate_name: string;
  candidate_email: string;
  assessment_title: string;
  percentage: number;
  correct_count: number;
  incorrect_count: number;
  unanswered_count: number;
  total_questions: number;
  total_answered: number;
  time_taken_seconds: number | null;
  pass_mark: number;
  evaluated_at: string;
}

function ScoresContent() {
  const router = useRouter();
  const [scores, setScores] = useState<Score[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState('');
  const [search, setSearch] = useState('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : '';

  const handleUnauthorized = (res: Response) => {
    if (res.status === 401) {
      localStorage.clear();
      router.push('/login');
      return true;
    }
    return false;
  };

  const fetchScores = () => {
    if (!token) return;
    setLoading(true);
    const url = new URL(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/scores`);
    url.searchParams.set('limit', '100');
    if (minScore) url.searchParams.set('min_score', minScore);

    fetch(url.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (handleUnauthorized(r)) return;
        return r.json();
      })
      .then((data) => {
        if (data) {
          setScores(Array.isArray(data) ? data : []);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchScores();
  }, []);

  useEffect(() => {
    const timer = setTimeout(fetchScores, 300);
    return () => clearTimeout(timer);
  }, [minScore]);

  const filtered = scores.filter((s) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.candidate_name.toLowerCase().includes(q) ||
      s.candidate_email.toLowerCase().includes(q) ||
      s.assessment_title.toLowerCase().includes(q)
    );
  });

  const formatTime = (seconds: number | null) => {
    if (!seconds || seconds <= 0) return '—';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
  };

  const toLocalTime = (iso: string | null | undefined) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  };

  const passed = (s: Score) => s.percentage >= s.pass_mark;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scores</h1>
          <p className="text-sm text-gray-500">Review evaluated assessment results</p>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search candidate or assessment..."
            className="w-64 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <span className="text-sm text-gray-500">Min score:</span>
          <input
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            placeholder="0"
            className="w-20 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="w-full min-w-[1100px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-4 py-3">Candidate</th>
              <th className="px-4 py-3">Assessment</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Correct</th>
              <th className="px-4 py-3">Incorrect</th>
              <th className="px-4 py-3">Unanswered</th>
              <th className="px-4 py-3">Time Taken</th>
              <th className="px-4 py-3">Evaluated</th>
              <th className="px-4 py-3">Result</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} className="px-4 py-12 text-center text-gray-400">
                  <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-12 text-center text-gray-400">
                  No scores found.
                </td>
              </tr>
            )}
            {filtered.map((s) => (
              <tr key={s.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="font-medium">{s.candidate_name}</div>
                  <div className="text-xs text-gray-400">{s.candidate_email}</div>
                </td>
                <td className="px-4 py-3 text-xs text-gray-600">{s.assessment_title}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-20 rounded-full bg-gray-100">
                      <div
                        className={`h-full rounded-full ${passed(s) ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(s.percentage, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold">
                      {s.percentage != null ? `${s.percentage.toFixed(1)}%` : '—'}
                    </span>
                    <span className="text-[10px] text-gray-400">({s.pass_mark}% to pass)</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs font-medium text-green-600">{s.correct_count}</td>
                <td className="px-4 py-3 text-xs font-medium text-red-600">{s.incorrect_count}</td>
                <td className="px-4 py-3 text-xs font-medium text-gray-500">{s.unanswered_count}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{formatTime(s.time_taken_seconds)}</td>
                <td className="px-4 py-3 text-xs text-gray-500">
                  {toLocalTime(s.evaluated_at)}
                </td>
                <td className="px-4 py-3">
                  {passed(s) ? (
                    <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-700">PASS</span>
                  ) : (
                    <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700">FAIL</span>
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
