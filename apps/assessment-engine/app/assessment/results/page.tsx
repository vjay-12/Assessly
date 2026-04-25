'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function ResultsPage() {
  const router = useRouter();
  const [submission, setSubmission] = useState<any>(null);

  useEffect(() => {
    const sub = localStorage.getItem('assessment_submission');
    if (sub) {
      setSubmission(JSON.parse(sub));
    }
  }, []);

  const score = submission?.score;
  const percentage = score?.percentage || 84;
  const correct = score?.correct_count || 8;
  const total = score?.total_questions || 10;
  const incorrect = total - correct - (total - correct - (score?.unanswered || 0));
  const unanswered = total - correct - incorrect;
  const passed = percentage >= 50;

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-2xl">
        <div className="rounded-2xl bg-white p-8 shadow-sm">
          <div className="flex flex-col items-center">
            <div className="relative flex h-40 w-40 items-center justify-center">
              <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#e2e8f0" strokeWidth="8" />
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke={passed ? '#4f46e5' : '#ef4444'}
                  strokeWidth="8"
                  strokeDasharray={`${percentage * 2.83} 283`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute text-center">
                <div className="text-4xl font-bold">{percentage}</div>
                <div className="text-sm text-gray-500">out of 100</div>
              </div>
            </div>
            <div className={`mt-4 rounded-full px-4 py-1 text-sm font-semibold ${passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {passed ? 'PASS' : 'FAIL'}
            </div>
            <h1 className="mt-4 text-2xl font-bold">Assessment Complete</h1>
            <p className="mt-2 text-gray-500">
              {passed
                ? 'Excellent work! Your strong performance demonstrates a solid foundation.'
                : 'Keep learning! Review the topics and try again when ready.'}
            </p>
          </div>

          <div className="mt-8 grid grid-cols-2 gap-4">
            <div className="rounded-xl bg-slate-50 p-4 text-center">
              <div className="text-sm text-gray-500">Submitted On</div>
              <div className="mt-1 font-semibold">{new Date().toLocaleString()}</div>
            </div>
            <div className="rounded-xl bg-slate-50 p-4 text-center">
              <div className="text-sm text-gray-500">Time Taken</div>
              <div className="mt-1 font-semibold">—</div>
            </div>
          </div>

          <div className="mt-8">
            <h3 className="font-semibold">Breakdown</h3>
            <div className="mt-3 space-y-2">
              {[
                { label: 'Correct', count: correct, color: 'bg-green-500' },
                { label: 'Incorrect', count: incorrect, color: 'bg-red-500' },
                { label: 'Unanswered', count: unanswered, color: 'bg-gray-300' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <div className="flex items-center gap-3">
                    <div className={`h-3 w-3 rounded-full ${item.color}`} />
                    <span className="text-sm">{item.label}</span>
                  </div>
                  <span className="font-semibold">{item.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-8 flex gap-4">
            <button
              onClick={() => {
                localStorage.removeItem('assessment_session');
                localStorage.removeItem('assessment_answers');
                localStorage.removeItem('assessment_flagged');
                localStorage.removeItem('assessment_questions');
                localStorage.removeItem('assessment_time_left');
                localStorage.removeItem('assessment_submission');
                window.location.href = process.env.NEXT_PUBLIC_CANDIDATE_PORTAL_URL || '/';
              }}
              className="flex-1 rounded-lg bg-indigo-600 py-3 font-semibold text-white hover:bg-indigo-700"
            >
              Back to Dashboard
            </button>
            <button className="flex-1 rounded-lg border border-gray-200 py-3 font-semibold text-gray-700 hover:bg-gray-50">
              Download Transcript
            </button>
          </div>
        </div>

        <div className="mt-4 rounded-xl bg-slate-800 p-4 text-center text-sm text-white/80">
          🔒 Evaluation Integrity Protected — correct answers are suppressed for candidates.
        </div>
      </div>
    </div>
  );
}
