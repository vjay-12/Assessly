'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

interface Question {
  id: string;
  question_text: string;
  code_snippet?: string;
  options: string[];
  difficulty: number;
}

interface SessionData {
  session_token: string;
  candidate_id: string;
  application_id: string;
}

interface AssessmentInfo {
  title: string;
  duration_minutes: number;
  total_questions: number;
}

function AssessmentContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get('token');

  const [session, setSession] = useState<SessionData | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [flagged, setFlagged] = useState<Set<string>>(new Set());
  const [timeLeft, setTimeLeft] = useState(30 * 60);
  const [assessmentInfo, setAssessmentInfo] = useState<AssessmentInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setError('Missing assessment token');
      setLoading(false);
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/auth/redeem-cross-app`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.detail) {
          setError(data.detail);
          setLoading(false);
          return;
        }
        setSession(data);
        const headers = { Authorization: `Bearer ${data.session_token}` };
        return Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/questions`, { headers }).then((r) => r.json()),
          fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessment-info`, { headers }).then((r) => r.json()),
        ]);
      })
      .then(([questionsData, infoData]) => {
        setQuestions(questionsData || []);
        if (infoData?.duration_minutes) {
          setAssessmentInfo(infoData);
          const durationSeconds = infoData.duration_minutes * 60;
          localStorage.setItem('assessment_duration', String(durationSeconds));

          // Calculate remaining time based on when assessment was first loaded
          const appId = session?.application_id;
          const startKey = appId ? `assessment_start_time_${appId}` : null;
          const storedStart = startKey ? localStorage.getItem(startKey) : null;

          if (storedStart) {
            const elapsed = Math.floor((Date.now() - Number(storedStart)) / 1000);
            const remaining = Math.max(0, durationSeconds - elapsed);
            if (remaining <= 0) {
              setError('Assessment time has expired. Please contact support.');
              setLoading(false);
              return;
            }
            setTimeLeft(remaining);
          } else {
            setTimeLeft(durationSeconds);
            if (startKey) {
              localStorage.setItem(startKey, String(Date.now()));
            }
          }
        }
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load assessment');
        setLoading(false);
      });
  }, [token]);

  useEffect(() => {
    if (timeLeft <= 0) return;
    const interval = setInterval(() => setTimeLeft((t) => t - 1), 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  const selectOption = (optionIndex: number) => {
    const q = questions[currentIndex];
    setAnswers((prev) => ({ ...prev, [q.id]: optionIndex }));
  };

  const toggleFlag = () => {
    const q = questions[currentIndex];
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(q.id)) next.delete(q.id);
      else next.add(q.id);
      return next;
    });
  };

  const goToReview = () => {
    if (!session) return;
    // Persist state for review page
    localStorage.setItem('assessment_session', JSON.stringify(session));
    localStorage.setItem('assessment_answers', JSON.stringify(answers));
    localStorage.setItem('assessment_flagged', JSON.stringify([...flagged]));
    localStorage.setItem('assessment_questions', JSON.stringify(questions));
    localStorage.setItem('assessment_time_left', String(timeLeft));
    localStorage.setItem('assessment_title', assessmentInfo?.title || 'Assessment');
    router.push('/assessment/review');
  };

  if (loading) return <div className="flex h-screen items-center justify-center">Loading assessment...</div>;
  if (error) return <div className="flex h-screen items-center justify-center text-red-600">{error}</div>;

  const currentQuestion = questions[currentIndex];
  const answeredCount = Object.keys(answers).length;

  return (
    <div className="flex h-screen bg-slate-50">
      <div className="w-64 border-r bg-white p-6">
        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Questions</div>
        <div className="mt-4 grid grid-cols-4 gap-2">
          {questions.map((q, idx) => (
            <button
              key={q.id}
              onClick={() => setCurrentIndex(idx)}
              className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold ${
                idx === currentIndex
                  ? 'bg-indigo-600 text-white'
                  : answers[q.id] !== undefined
                  ? 'bg-green-100 text-green-700'
                  : flagged.has(q.id)
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {idx + 1}
            </button>
          ))}
        </div>
        <div className="mt-6 space-y-2 text-sm">
          <div className="flex items-center gap-2"><div className="h-3 w-3 rounded bg-green-100" /> Answered</div>
          <div className="flex items-center gap-2"><div className="h-3 w-3 rounded bg-indigo-600" /> Current</div>
          <div className="flex items-center gap-2"><div className="h-3 w-3 rounded bg-amber-100" /> Flagged</div>
          <div className="flex items-center gap-2"><div className="h-3 w-3 rounded bg-gray-100" /> Unanswered</div>
        </div>
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between border-b bg-white px-8 py-4">
          <div className="text-sm text-gray-500">
            Assessly Assessment Engine <span className="mx-2">|</span> <span className="font-semibold text-gray-800">{assessmentInfo?.title || 'Assessment'}</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2 text-sm font-mono font-semibold">
              ⏱ {formatTime(timeLeft)}
            </div>
            <div className="text-sm text-gray-500">
              Question {currentIndex + 1} of {questions.length}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-8">
          <div className="mx-auto max-w-3xl">
            <div className="mb-2 inline-block rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">
              QUESTION {currentIndex + 1}
            </div>
            <h2 className="text-xl font-semibold leading-relaxed">{currentQuestion?.question_text}</h2>
            {currentQuestion?.code_snippet && (
              <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-900 p-4 text-sm text-slate-100">
                <code>{currentQuestion.code_snippet}</code>
              </pre>
            )}

            <div className="mt-6 space-y-3">
              {currentQuestion?.options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => selectOption(idx)}
                  className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left transition ${
                    answers[currentQuestion.id] === idx
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 bg-white hover:border-indigo-300'
                  }`}
                >
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                    answers[currentQuestion.id] === idx
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {String.fromCharCode(65 + idx)}
                  </div>
                  <span className="mt-0.5 text-sm">{opt}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between border-t bg-white px-8 py-4">
          <button
            onClick={toggleFlag}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
              flagged.has(currentQuestion?.id) ? 'bg-amber-100 text-amber-700' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            🚩 {flagged.has(currentQuestion?.id) ? 'Flagged' : 'Flag for Review'}
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
              disabled={currentIndex === 0}
              className="rounded-lg border border-gray-200 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              ← Previous
            </button>
            {currentIndex < questions.length - 1 ? (
              <button
                onClick={() => setCurrentIndex((i) => i + 1)}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Save & Next →
              </button>
            ) : (
              <button
                onClick={goToReview}
                className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Review & Submit
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AssessmentPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center">Loading...</div>}>
      <AssessmentContent />
    </Suspense>
  );
}
