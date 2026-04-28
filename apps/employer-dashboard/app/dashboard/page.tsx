'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface FunnelData {
  applied: number;
  attempted: number;
  submitted: number;
  evaluated: number;
}

interface SummaryData {
  total_candidates: number;
  total_assessments: number;
  avg_score: number;
  pass_rate: number;
  avg_time_taken_seconds: number;
  evaluated_today: number;
  submitted_today: number;
  drop_off_rate: number;
  invitation_acceptance: number;
}

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function DashboardContent() {
  const [funnel, setFunnel] = useState<FunnelData>({ applied: 0, attempted: 0, submitted: 0, evaluated: 0 });
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [live, setLive] = useState(false);
  const [activities, setActivities] = useState<any[]>([]);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const headers = { Authorization: `Bearer ${token}` };

    // Fetch funnel
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/analytics/funnel`, { headers })
      .then((r) => {
        if (r.status === 401) {
          localStorage.clear();
          router.push('/login');
          return null;
        }
        if (!r.ok) return null;
        return r.json();
      })
      .then((data) => {
        if (data && typeof data.applied === 'number') {
          setFunnel(data);
        }
      })
      .catch(() => {
        // network or server error — leave defaults
      });

    // Fetch summary
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/analytics/summary`, { headers })
      .then((r) => {
        if (r.status === 401) {
          localStorage.clear();
          router.push('/login');
          return null;
        }
        if (!r.ok) return null;
        return r.json();
      })
      .then((data) => {
        if (data && typeof data.avg_score === 'number') {
          setSummary(data);
        }
      })
      .catch(() => {
        // network or server error — leave defaults
      });

    // Fetch recent audit events for initial activity feed
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/audit/events?limit=10`, { headers })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (Array.isArray(data)) {
          setActivities(
            data.map((log: any) => ({
              name: log.event_type?.replace(/_/g, ' ') || 'System',
              action: log.details || log.event_type,
              time: log.created_at ? new Date(log.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '',
              score: null,
            }))
          );
        }
      })
      .catch(() => {
        // ignore
      });

    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/events?token=${encodeURIComponent(token)}`
    );

    eventSource.onopen = () => setLive(true);
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'EVALUATION_COMPLETED') {
        setFunnel((prev) => ({ ...prev, evaluated: prev.evaluated + 1 }));
        setActivities((prev) => [
          {
            name: 'Evaluation',
            action: `Completed — Score: ${data.payload.percentage}%`,
            time: 'Just now',
            score: data.payload.percentage,
          },
          ...prev,
        ]);
      }
    };
    eventSource.onerror = () => setLive(false);

    return () => eventSource.close();
  }, [router]);

  const stats = [
    { label: 'TOTAL CANDIDATES', value: summary?.total_candidates ?? 0, sub: `${summary?.total_assessments ?? 0} assessments` },
    { label: 'AVG SCORE', value: summary ? `${summary.avg_score}%` : '—', sub: 'All evaluated sessions' },
    { label: 'PASS RATE', value: summary ? `${summary.pass_rate}%` : '—', sub: 'Above pass mark' },
    { label: 'COMPLETED TODAY', value: summary?.submitted_today ?? 0, sub: 'Submissions today', live: true },
    { label: 'EVALUATED TODAY', value: summary?.evaluated_today ?? 0, sub: 'Evaluations today', live: true },
  ];

  const funnelStages = [
    { label: 'APPLIED', value: funnel.applied, icon: '👥' },
    { label: 'INVITED', value: funnel.attempted, icon: '📧' },
    { label: 'STARTED', value: funnel.attempted, icon: '▶️' },
    { label: 'COMPLETED', value: funnel.submitted, icon: '✅' },
    { label: 'EVALUATED', value: funnel.evaluated, icon: '📊' },
  ];

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-500">Real-time overview of your talent pipeline</p>
        </div>
        {live && (
          <div className="flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-600">
            <div className="h-2 w-2 animate-pulse rounded-full bg-green-500" /> LIVE
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label} className="rounded-2xl bg-white p-5 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{s.label}</div>
            <div className="mt-2 text-2xl font-bold">{s.value}</div>
            <div className="mt-1 text-xs text-gray-400">
              {s.live && <span className="mr-1 text-green-500">●</span>}
              {s.sub}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">Candidate Funnel</h2>
            <p className="text-sm text-gray-500">End-to-end conversion workflow tracking</p>
          </div>
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
            <div className="mt-1 text-lg font-bold">
              {summary ? `${summary.drop_off_rate}%` : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Avg. Time to Finish</div>
            <div className="mt-1 text-lg font-bold">
              {summary ? formatDuration(summary.avg_time_taken_seconds) : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase text-gray-500">Invitation Acceptance</div>
            <div className="mt-1 text-lg font-bold">
              {summary ? `${summary.invitation_acceptance}%` : '—'}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="font-bold">Recent Activity</h3>
          <div className="flex items-center gap-2 text-xs font-semibold text-green-600">
            <div className="h-2 w-2 rounded-full bg-green-500" /> REAL-TIME STREAM
          </div>
        </div>
        <div className="mt-4 space-y-4">
          {activities.length === 0 && (
            <div className="text-sm text-gray-400">No recent activity.</div>
          )}
          {activities.map((item, i) => (
            <div key={i} className="flex items-center justify-between rounded-xl bg-slate-50 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-600">
                  {typeof item.name === 'string' ? item.name.charAt(0) : 'A'}
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
    </div>
  );
}

export default function EmployerDashboard() {
  return (
    <DashboardShell>
      <DashboardContent />
    </DashboardShell>
  );
}
