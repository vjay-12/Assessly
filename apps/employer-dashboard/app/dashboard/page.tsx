'use client';

import { useEffect, useState } from 'react';

interface FunnelData {
  applied: number;
  attempted: number;
  submitted: number;
  evaluated: number;
}

export default function EmployerDashboard() {
  const [funnel, setFunnel] = useState<FunnelData>({ applied: 0, attempted: 0, submitted: 0, evaluated: 0 });
  const [live, setLive] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Fetch funnel data
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/analytics/funnel`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setFunnel(data));

    // SSE connection
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/events`, {
      withCredentials: false,
    });

    // Manually set headers via query param workaround or use EventSource without auth for demo
    // In production, you'd use a custom SSE client with headers

    eventSource.onopen = () => setLive(true);
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'EVALUATION_COMPLETED') {
        setFunnel((prev) => ({ ...prev, evaluated: prev.evaluated + 1 }));
      }
    };
    eventSource.onerror = () => setLive(false);

    return () => eventSource.close();
  }, []);

  const stats = [
    { label: 'TOTAL CANDIDATES', value: funnel.applied, trend: '+12.5%', trendUp: true },
    { label: 'ASSIGNED', value: funnel.attempted, trend: 'vs last month', trendUp: true },
    { label: 'COMPLETED TODAY', value: funnel.submitted, trend: 'Real-time', trendUp: true, live: true },
    { label: 'AVG SCORE', value: '76%', trend: 'Benchmark 70%', trendUp: true },
    { label: 'PASS RATE', value: '68%', trend: '-2.1%', trendUp: false },
  ];

  const funnelStages = [
    { label: 'APPLIED', value: funnel.applied, icon: '👥' },
    { label: 'INVITED', value: funnel.attempted + funnel.submitted + funnel.evaluated, icon: '📧' },
    { label: 'STARTED', value: funnel.attempted + funnel.submitted + funnel.evaluated, icon: '▶️' },
    { label: 'COMPLETED', value: funnel.submitted + funnel.evaluated, icon: '✅' },
    { label: 'EVALUATED', value: funnel.evaluated, icon: '📊' },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Bar */}
      <header className="border-b bg-white px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <span className="font-bold text-slate-800">Zetheta HR</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex gap-2">
              {['Today', 'This Week', 'This Month'].map((f) => (
                <button key={f} className={`rounded-lg px-4 py-2 text-sm font-medium ${f === 'Today' ? 'bg-indigo-50 text-indigo-600' : 'text-gray-500 hover:bg-gray-50'}`}>
                  {f}
                </button>
              ))}
            </div>
            {live && (
              <div className="flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-600">
                <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" /> LIVE
              </div>
            )}
            <div className="h-8 w-8 rounded-full bg-indigo-100" />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        {/* Stats */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
          {stats.map((s) => (
            <div key={s.label} className="rounded-2xl bg-white p-5 shadow-sm">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{s.label}</div>
              <div className="mt-2 text-2xl font-bold">{s.value}</div>
              <div className={`mt-1 text-xs ${s.trendUp ? 'text-green-600' : 'text-red-500'}`}>
                {s.trendUp ? '↗' : '↘'} {s.trend}
              </div>
            </div>
          ))}
        </div>

        {/* Funnel */}
        <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Candidate Funnel</h2>
              <p className="text-sm text-gray-500">End-to-end conversion workflow tracking</p>
            </div>
            <button className="text-sm font-medium text-indigo-600 hover:underline">View Details →</button>
          </div>

          <div className="mt-8 flex items-center justify-between gap-4">
            {funnelStages.map((stage, idx) => (
              <div key={stage.label} className="flex flex-1 items-center">
                <div className="flex flex-1 flex-col items-center text-center">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">
                    {stage.icon}
                  </div>
                  <div className="mt-3 text-2xl font-bold">{stage.value}</div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{stage.label}</div>
                </div>
                {idx < funnelStages.length - 1 && (
                  <div className="mx-2 text-gray-300">→</div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-8 grid grid-cols-3 gap-4 border-t pt-6">
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Drop-off Rate</div>
              <div className="mt-1 text-lg font-bold">22.4% <span className="text-xs text-red-500">+2%</span></div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Avg. Time to Finish</div>
              <div className="mt-1 text-lg font-bold">48m 12s</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase text-gray-500">Invitation Acceptance</div>
              <div className="mt-1 text-lg font-bold">91%</div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold">Recent Activity</h3>
            <div className="flex items-center gap-2 text-xs font-semibold text-green-600">
              <div className="h-2 w-2 rounded-full bg-green-500" /> REAL-TIME STREAM
            </div>
          </div>
          <div className="mt-4 space-y-4">
            {[
              { name: 'Ravi Kumar', action: 'Completed Backend Assessment', time: '2 mins ago', score: 82 },
              { name: 'Priya Sharma', action: 'Started DSA Assessment', time: '15 mins ago', score: null },
              { name: 'Karthik', action: 'Logged into Admin Panel', time: '1 hour ago', score: null },
            ].map((item, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600">
                    {item.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-medium">{item.name}</div>
                    <div className="text-sm text-gray-500">{item.action}</div>
                  </div>
                </div>
                <div className="text-right">
                  {item.score && (
                    <div className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                      Score: {item.score}/100
                    </div>
                  )}
                  <div className="mt-1 text-xs text-gray-400">{item.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
