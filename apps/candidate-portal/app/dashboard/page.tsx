'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface TestSession {
  id: string;
  assessment_title: string;
  status: string;
  application_status: string;
  score_percentage: number | null;
  due_at: string | null;
}

export default function CandidateDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<{ full_name: string; email: string; role: string } | null>(null);
  const [sessions, setSessions] = useState<TestSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser({ full_name: payload.sub_name || 'Candidate', email: payload.sub_email || '', role: payload.role || 'candidate' });
    } catch {
      router.push('/login');
      return;
    }

    // For demo, load seeded test sessions via a candidate-specific endpoint
    // Since we don't have a dedicated /api/my-sessions endpoint yet, we use a static demo session
    setSessions([
      {
        id: '11111111-1111-1111-1111-111111111111',
        assessment_title: 'Full Stack Engineering Assessment',
        status: 'Assigned',
        application_status: 'applied',
        score_percentage: null,
        due_at: null,
      },
    ]);
    setLoading(false);
  }, [router]);

  const startAssessment = async (applicationId: string) => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setStarting(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/auth/cross-app-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ application_id: applicationId }),
      });

      const data = await res.json();
      if (res.ok) {
        const assessmentEngineUrl = process.env.NEXT_PUBLIC_ASSESSMENT_ENGINE_URL;
        const assessmentUrl = `${assessmentEngineUrl}/assessment?token=${encodeURIComponent(data.token)}`;
        window.location.href = assessmentUrl;
      } else {
        alert(data.detail || 'Failed to start assessment');
        setStarting(false);
      }
    } catch {
      alert('Network error');
      setStarting(false);
    }
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      applied: 'bg-blue-50 text-blue-700',
      attempted: 'bg-amber-50 text-amber-700',
      submitted: 'bg-purple-50 text-purple-700',
      evaluated: 'bg-green-50 text-green-700',
    };
    return (
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${map[status] || 'bg-gray-100 text-gray-600'}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;

  const completedCount = sessions.filter((s) => s.application_status === 'evaluated').length;
  const pendingCount = sessions.filter((s) => s.application_status !== 'evaluated').length;
  const avgScore = sessions.length > 0
    ? sessions.reduce((acc, s) => acc + (s.score_percentage || 0), 0) / sessions.filter((s) => s.score_percentage !== null).length || 0
    : 0;

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="border-b bg-white px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <span className="font-bold text-slate-800">Zetheta</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button
              onClick={() => { localStorage.clear(); router.push('/login'); }}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl p-6">
        <div className="rounded-2xl bg-gradient-to-r from-slate-800 to-indigo-700 p-8 text-white">
          <h1 className="text-2xl font-bold">Hello {user?.full_name || 'Candidate'},</h1>
          <p className="mt-1 text-white/80">Welcome to your assessment dashboard. You have {pendingCount} active assessment(s) ready.</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Total Assigned', value: String(sessions.length), icon: '📝' },
            { label: 'Completed', value: String(completedCount), icon: '✅' },
            { label: 'Pending', value: String(pendingCount), icon: '⏳' },
            { label: 'Average Score', value: avgScore > 0 ? `${avgScore.toFixed(1)}%` : '—', icon: '📊' },
          ].map((stat) => (
            <div key={stat.label} className="rounded-2xl bg-white p-6 shadow-sm">
              <div className="text-2xl">{stat.icon}</div>
              <div className="mt-2 text-2xl font-bold">{stat.value}</div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>

        <h2 className="mt-10 text-xl font-bold">My Assessments</h2>
        <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <div key={session.id} className="rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">MCQ</span>
                {statusBadge(session.application_status)}
              </div>
              <h3 className="mt-3 font-semibold">{session.assessment_title}</h3>
              <div className="mt-2 space-y-1 text-sm text-gray-500">
                <p>📝 10 Questions</p>
                <p>⏱ 60 mins</p>
                {session.score_percentage !== null && (
                  <p>📊 Score: {session.score_percentage.toFixed(1)}%</p>
                )}
              </div>
              {session.application_status !== 'evaluated' && (
                <button
                  onClick={() => startAssessment(session.id)}
                  disabled={starting}
                  className="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {starting ? 'Starting...' : session.application_status === 'applied' ? 'Start Assessment' : 'Continue Assessment'}
                </button>
              )}
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="rounded-2xl bg-white p-6 shadow-sm text-gray-500">
              No assessments assigned yet.
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
