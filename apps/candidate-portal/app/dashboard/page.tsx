'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Application {
  id: string;
  status: string;
  started_at: string | null;
  submitted_at: string | null;
  score: { percentage: number } | null;
}

export default function CandidateDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/candidates`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.length > 0) {
          setUser({ name: data[0].name });
        }
      })
      .catch(() => router.push('/login'));

    // For demo, show hardcoded applications
    setApplications([
      { id: 'demo-1', status: 'applied', started_at: null, submitted_at: null, score: null },
      { id: 'demo-2', status: 'attempted', started_at: new Date().toISOString(), submitted_at: null, score: null },
    ]);
    setLoading(false);
  }, [router]);

  const startAssessment = async (applicationId: string) => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

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
      window.location.href = `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/assessment?token=${data.token}`;
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
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">{user?.name || 'Candidate'}</span>
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
          <h1 className="text-2xl font-bold">Hello {user?.name || 'Alex'},</h1>
          <p className="mt-1 text-white/80">Here are your assigned assessments. Maintain your high-precision streak.</p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            { label: 'Total Assigned', value: '2', icon: '📝' },
            { label: 'Completed', value: '0', icon: '✅' },
            { label: 'Pending', value: '2', icon: '⏳' },
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
          {applications.map((app) => (
            <div key={app.id} className="rounded-2xl bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">MCQ</span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  app.status === 'applied' ? 'bg-amber-50 text-amber-600' :
                  app.status === 'attempted' ? 'bg-blue-50 text-blue-600' :
                  'bg-green-50 text-green-600'
                }`}>
                  {app.status.toUpperCase()}
                </span>
              </div>
              <h3 className="mt-3 font-semibold">Distributed Systems Assessment</h3>
              <div className="mt-2 space-y-1 text-sm text-gray-500">
                <p>📝 10 Questions</p>
                <p>⏱ 30 mins</p>
              </div>
              {app.status === 'applied' && (
                <button
                  onClick={() => startAssessment(app.id)}
                  className="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Start Assessment
                </button>
              )}
              {app.status === 'attempted' && (
                <button
                  onClick={() => startAssessment(app.id)}
                  className="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Continue Assessment
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
