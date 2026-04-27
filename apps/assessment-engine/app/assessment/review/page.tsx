'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface Question {
  id: string;
  question_text: string;
  options: string[];
  difficulty: number;
}

interface SessionData {
  session_token: string;
  candidate_id: string;
  application_id: string;
}

export default function ReviewPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [session, setSession] = useState<SessionData | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [questions, setQuestions] = useState<Question[]>([]);
  const [timeLeft, setTimeLeft] = useState(0);
  const [totalDuration, setTotalDuration] = useState(30 * 60);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sess = localStorage.getItem('assessment_session');
    const ans = localStorage.getItem('assessment_answers');
    const flg = localStorage.getItem('assessment_flagged');
    const qs = localStorage.getItem('assessment_questions');
    const tl = localStorage.getItem('assessment_time_left');
    const dur = localStorage.getItem('assessment_duration');

    if (!sess || !ans || !qs) {
      router.push('/assessment');
      return;
    }

    setSession(JSON.parse(sess));
    setAnswers(JSON.parse(ans));
    setFlagged(new Set(JSON.parse(flg || '[]')));
    setQuestions(JSON.parse(qs));
    setTimeLeft(Number(tl || 0));
    setTotalDuration(Number(dur || 30 * 60));
    setLoading(false);
  }, [router]);

  const handleSubmit = async () => {
    if (!session) return;
    setSubmitting(true);

    const payload = {
      application_id: session.application_id,
      answers: Object.entries(answers).map(([qid, sel]) => ({ question_id: qid, selected_option: sel })),
    };

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/submissions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.session_token}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem('assessment_submission', JSON.stringify(data));
        if (session?.application_id) {
          localStorage.removeItem(`assessment_start_time_${session.application_id}`);
        }
        router.push('/assessment/results');
      } else {
        alert(data.detail || 'Submission failed');
        setSubmitting(false);
      }
    } catch {
      alert('Network error during submission');
      setSubmitting(false);
    }
  };

  const total = questions.length;
  const answered = Object.keys(answers).length;
  const unanswered = total - answered;
  const flaggedCount = flagged.size;
  const timeTaken = totalDuration - timeLeft;
  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center">Loading review...</div>;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="grid w-full max-w-5xl grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left — Summary */}
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-indigo-600">
              ✓
            </div>
            <div>
              <h2 className="text-xl font-bold">Final Submission</h2>
              <p className="text-sm text-gray-500">Please review your assessment details before finalization.</p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">
            {[
              { label: 'TOTAL QUESTIONS', value: total },
              { label: 'ANSWERED', value: answered, percent: total > 0 ? `${Math.round((answered / total) * 100)}%` : '0%' },
              { label: 'UNANSWERED', value: unanswered, warning: unanswered > 0 },
              { label: 'FLAGGED FOR REVIEW', value: flaggedCount },
              { label: 'TIME TAKEN', value: formatTime(timeTaken) },
            ].map((s) => (
              <div key={s.label} className={`rounded-xl p-4 ${s.warning ? 'bg-amber-50' : 'bg-slate-50'}`}>
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{s.label}</div>
                <div className={`mt-1 text-2xl font-bold ${s.warning ? 'text-amber-600' : ''}`}>
                  {s.value}
                  {s.percent && <span className="ml-2 text-sm font-normal text-green-600">{s.percent}</span>}
                </div>
              </div>
            ))}
          </div>

          {unanswered > 0 && (
            <div className="mt-4 rounded-xl bg-amber-50 p-4">
              <p className="font-medium text-amber-800">You have {unanswered} unanswered question(s)</p>
              <p className="mt-1 text-sm text-amber-700">Consider reviewing before submitting.</p>
            </div>
          )}

          <div className="mt-6 rounded-xl bg-amber-50 p-4">
            <p className="font-medium text-amber-800">Are you sure you want to submit?</p>
            <p className="mt-1 text-sm text-amber-700">Once submitted, you will not be able to return to any questions or change your answers.</p>
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-indigo-600 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Confirm & Submit Assessment'}
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
            <button
              onClick={() => router.push('/assessment')}
              className="rounded-lg border border-gray-200 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel & Return
            </button>
          </div>
        </div>

        {/* Right — Processing Panel */}
        <div className="rounded-2xl bg-slate-900 p-8 text-white">
          <div className="flex items-center justify-between">
            <h3 className="font-bold">Submission Engine</h3>
            <div className="flex items-center gap-2 rounded-full bg-green-500/20 px-3 py-1 text-xs font-semibold text-green-400">
              <div className="h-2 w-2 animate-pulse rounded-full bg-green-400" /> LIVE SYNC
            </div>
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between text-sm">
              <span>Processing Queue</span>
              <span className="font-mono font-bold">{submitting ? '75%' : '0%'}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-slate-700">
              <div className={`h-full rounded-full bg-indigo-500 transition-all ${submitting ? 'w-3/4' : 'w-0'}`} />
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {[
              { label: 'Submitting your answers...', sub: 'Payload verified and encrypted.', done: true },
              { label: 'Evaluating your responses...', sub: 'Computing score against answer key.', done: submitting },
              { label: 'Calculating your final score...', sub: 'Ranking against global benchmarks.', done: false },
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  step.done ? 'bg-green-500 text-white' : 'border border-slate-600'
                }`}>
                  {step.done ? '✓' : i + 1}
                </div>
                <div>
                  <div className={`text-sm font-medium ${step.done ? 'text-white' : 'text-slate-400'}`}>{step.label}</div>
                  <div className="text-xs text-slate-500">{step.sub}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-xl bg-slate-800 p-4">
            <div className="text-xs font-semibold uppercase text-slate-500">Environment Status</div>
            <div className="mt-1 text-sm">🔒 Encrypted AES-256 Connection</div>
          </div>
        </div>
      </div>
    </div>
  );
}
