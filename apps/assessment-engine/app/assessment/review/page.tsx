'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function ReviewPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  const stats = [
    { label: 'TOTAL QUESTIONS', value: 10 },
    { label: 'ANSWERED', value: 8, percent: '80%' },
    { label: 'UNANSWERED', value: 2, warning: true },
    { label: 'FLAGGED FOR REVIEW', value: 1 },
    { label: 'TIME TAKEN', value: '28m 15s' },
  ];

  const handleSubmit = () => {
    setSubmitting(true);
    setTimeout(() => {
      router.push('/assessment/results');
    }, 1500);
  };

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
            {stats.map((s) => (
              <div key={s.label} className={`rounded-xl p-4 ${s.warning ? 'bg-amber-50' : 'bg-slate-50'}`}>
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{s.label}</div>
                <div className={`mt-1 text-2xl font-bold ${s.warning ? 'text-amber-600' : ''}`}>
                  {s.value}
                  {s.percent && <span className="ml-2 text-sm font-normal text-green-600">{s.percent}</span>}
                </div>
              </div>
            ))}
          </div>

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
