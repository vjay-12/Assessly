'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CandidateDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    // Decode JWT to get user info (simplified)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUser({ name: 'Candidate', email: '' });
    } catch {
      router.push('/login');
    }
    setLoading(false);
  }, [router]);

  const startAssessment = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    setStarting(true);

    // For demo, use the seeded application ID
    // In production, this would come from the candidate's applications list
    const applicationId = '11111111-1111-1111-1111-111111111111';

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
        // Redirect to assessment engine with cross-app token
        const assessmentUrl = `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/assessment?token=${encodeURIComponent(data.token)}`;
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

  if (loading) return <div className="flex h-screen items-center justify-center">Loading...</div>;

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
          <button
            onClick={() => { localStorage.clear(); router.push('/login'); }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Logout
          </button>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl p-6">
        <div className="rounded-2xl bg-gradient-to-r from-slate-800 to-indigo-700 p-8 text-white">
          <h1 className="text-2xl font-bold">Hello {user?.name || 'Candidate'},</h1>
          <p className="mt-1 text-white/80">Welcome to your assessment dashboard. You have an active assessment ready.</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Total Assigned', value: '1', icon: '📝' },
            { label: 'Completed', value: '0', icon: '✅' },
            { label: 'Pending', value: '1', icon: '⏳' },
            { label: 'Average Score', value: '—', icon: '📊' },
          ].map((stat) => (
            <div key={stat.label} className="rounded-2xl bg-white p-6 shadow-sm">
              <div className="text-2xl">{stat.icon}</div>
              <div className="mt-2 text-2xl font-bold">{stat.value}</div>
              <div className="text-sm text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>

        <h2 className="mt-10 text-xl font-bold">Active Assessments</h2>
        <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">MCQ</span>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-600">PENDING</span>
            </div>
            <h3 className="mt-3 font-semibold">Distributed Systems Assessment</h3>
            <div className="mt-2 space-y-1 text-sm text-gray-500">
              <p>📝 10 Questions</p>
              <p>⏱ 30 mins</p>
            </div>
            <button
              onClick={startAssessment}
              disabled={starting}
              className="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {starting ? 'Starting...' : 'Start Assessment'}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
