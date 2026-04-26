'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface Question {
  id?: string;
  question_text: string;
  code_snippet: string;
  options: string[];
  correct_option: number;
  points: number;
  difficulty: number;
  sort_order: number;
}

const categories = ['Backend', 'Frontend', 'DSA', 'System Design', 'UI/UX', 'General'];
const difficulties = ['Easy', 'Medium', 'Hard'];

function BuilderContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = searchParams.get('id');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Backend');
  const [difficulty, setDifficulty] = useState('Medium');
  const [duration, setDuration] = useState(60);
  const [passMark, setPassMark] = useState(50);
  const [maxAttempts, setMaxAttempts] = useState(1);
  const [isPublished, setIsPublished] = useState(false);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [showQuestionForm, setShowQuestionForm] = useState(false);
  const [editingQIndex, setEditingQIndex] = useState<number | null>(null);
  const [expandedQ, setExpandedQ] = useState<number | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : '';

  // Inline question form state
  const [qText, setQText] = useState('');
  const [qCode, setQCode] = useState('');
  const [qOptions, setQOptions] = useState(['', '', '', '']);
  const [qCorrect, setQCorrect] = useState(0);
  const [qPoints, setQPoints] = useState(1);
  const [qDifficulty, setQDifficulty] = useState(1);

  useEffect(() => {
    if (editId) {
      fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments/${editId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((data) => {
          setTitle(data.title || '');
          setDescription(data.description || '');
          setCategory(data.category || 'Backend');
          setDifficulty(data.difficulty || 'Medium');
          setDuration(data.duration_minutes || 60);
          setPassMark(data.pass_mark || 50);
          setMaxAttempts(data.max_attempts || 1);
          setIsPublished(data.is_published || false);
          setQuestions(data.questions || []);
        })
        .catch(() => setError('Failed to load assessment'));
    }
  }, [editId]);

  const totalPoints = questions.reduce((sum, q) => sum + (q.points || 1), 0);

  const resetQForm = () => {
    setQText('');
    setQCode('');
    setQOptions(['', '', '', '']);
    setQCorrect(0);
    setQPoints(1);
    setQDifficulty(1);
    setEditingQIndex(null);
  };

  const addQuestion = () => {
    if (!qText.trim()) return;
    if (qOptions.some((o) => !o.trim())) return;

    const newQ: Question = {
      question_text: qText,
      code_snippet: qCode,
      options: qOptions,
      correct_option: qCorrect,
      points: qPoints,
      difficulty: qDifficulty,
      sort_order: editingQIndex !== null ? questions[editingQIndex].sort_order : questions.length,
    };

    if (editingQIndex !== null) {
      const updated = [...questions];
      updated[editingQIndex] = { ...newQ, id: questions[editingQIndex].id };
      setQuestions(updated);
    } else {
      setQuestions([...questions, newQ]);
    }
    resetQForm();
    setShowQuestionForm(false);
  };

  const editQuestion = (index: number) => {
    const q = questions[index];
    setQText(q.question_text);
    setQCode(q.code_snippet || '');
    setQOptions([...q.options]);
    setQCorrect(q.correct_option);
    setQPoints(q.points);
    setQDifficulty(q.difficulty);
    setEditingQIndex(index);
    setShowQuestionForm(true);
  };

  const deleteQuestion = (index: number) => {
    if (!confirm('Delete this question?')) return;
    const updated = questions.filter((_, i) => i !== index);
    // Renumber sort_order
    updated.forEach((q, i) => (q.sort_order = i));
    setQuestions(updated);
  };

  const moveQuestion = (index: number, direction: number) => {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= questions.length) return;
    const updated = [...questions];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    updated.forEach((q, i) => (q.sort_order = i));
    setQuestions(updated);
  };

  const saveAssessment = async (publish: boolean) => {
    if (!title.trim()) { setError('Title is required'); return; }
    if (questions.length === 0 && publish) { setError('Add at least one question before publishing'); return; }

    setSaving(true);
    setError('');

    const payload = {
      title,
      description,
      category,
      difficulty,
      duration_minutes: duration,
      pass_mark: passMark,
      max_attempts: maxAttempts,
      is_published: publish,
      questions: questions.map((q, i) => ({ ...q, sort_order: i })),
    };

    try {
      const url = editId
        ? `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments/${editId}`
        : `${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments`;
      const res = await fetch(url, {
        method: editId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Save failed');
        return;
      }
      router.push('/manage-assessments');
    } catch {
      setError('Network error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">{editId ? 'Edit Assessment' : 'Assessment Builder'}</h1>
      <p className="text-sm text-gray-500">{editId ? 'Update assessment details and questions' : 'Create a new assessment with MCQ questions'}</p>

      {error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Assessment Details */}
      <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-bold">Assessment Details</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" placeholder="e.g. Full Stack Engineering" />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Category</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500">
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" placeholder="What this assessment covers..." />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Difficulty</label>
            <div className="mt-1 flex gap-2">
              {difficulties.map((d) => (
                <button key={d} onClick={() => setDifficulty(d)} className={`rounded-lg px-4 py-2 text-sm font-medium transition ${difficulty === d ? 'bg-indigo-600 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                  {d}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Duration (min)</label>
              <input type="number" value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" min={1} />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Pass Mark (%)</label>
              <input type="number" value={passMark} onChange={(e) => setPassMark(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" min={0} max={100} />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Max Attempts</label>
              <input type="number" value={maxAttempts} onChange={(e) => setMaxAttempts(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" min={1} />
            </div>
          </div>
          <div className="md:col-span-2 flex items-center gap-4">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Status</span>
            <button onClick={() => setIsPublished(false)} className={`rounded-lg px-4 py-2 text-sm font-medium transition ${!isPublished ? 'bg-gray-800 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>Draft</button>
            <button onClick={() => setIsPublished(true)} className={`rounded-lg px-4 py-2 text-sm font-medium transition ${isPublished ? 'bg-green-600 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>Published</button>
          </div>
        </div>
      </div>

      {/* Questions Section */}
      <div className="mt-6 rounded-2xl bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Questions</h2>
            <p className="text-sm text-gray-500">{questions.length} Questions · {totalPoints} Points Total</p>
          </div>
          <button onClick={() => { setShowQuestionForm(true); resetQForm(); }} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            + Add Question
          </button>
        </div>

        {showQuestionForm && (
          <div className="mb-6 rounded-xl border border-indigo-100 bg-indigo-50/50 p-5">
            <h3 className="mb-3 font-semibold">{editingQIndex !== null ? 'Edit Question' : 'New Question'}</h3>
            <div className="space-y-3">
              <textarea value={qText} onChange={(e) => setQText(e.target.value)} rows={3} className="w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" placeholder="Question text..." />
              <textarea value={qCode} onChange={(e) => setQCode(e.target.value)} rows={3} className="w-full rounded-lg border border-gray-200 bg-gray-900 px-4 py-2 font-mono text-sm text-green-400 outline-none focus:border-indigo-500" placeholder="Code snippet (optional)..." />
              <div className="grid grid-cols-2 gap-3">
                {qOptions.map((opt, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input type="radio" name="correct" checked={qCorrect === i} onChange={() => setQCorrect(i)} className="h-4 w-4 text-indigo-600" />
                    <input value={opt} onChange={(e) => { const o = [...qOptions]; o[i] = e.target.value; setQOptions(o); }} className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500" placeholder={`Option ${String.fromCharCode(65 + i)}`} />
                  </div>
                ))}
              </div>
              <div className="flex gap-3">
                <div>
                  <label className="text-xs text-gray-500">Points</label>
                  <input type="number" value={qPoints} onChange={(e) => setQPoints(Number(e.target.value))} className="mt-1 w-20 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500" min={1} />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Difficulty (1-5)</label>
                  <input type="number" value={qDifficulty} onChange={(e) => setQDifficulty(Number(e.target.value))} className="mt-1 w-20 rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-indigo-500" min={1} max={5} />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={addQuestion} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                  {editingQIndex !== null ? 'Update Question' : 'Add Question'}
                </button>
                <button onClick={() => { setShowQuestionForm(false); resetQForm(); }} className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Question Cards */}
        <div className="space-y-3">
          {questions.map((q, index) => (
            <div key={index} className="rounded-xl border border-gray-100 bg-white p-4 transition hover:border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-50 text-xs font-bold text-indigo-600">{index + 1}</span>
                  <span className="font-medium">{q.question_text.slice(0, 60)}{q.question_text.length > 60 ? '...' : ''}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">{q.points} pts</span>
                  <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">Lv.{q.difficulty}</span>
                  <button onClick={() => setExpandedQ(expandedQ === index ? null : index)} className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-50">
                    {expandedQ === index ? 'Collapse' : 'Expand'}
                  </button>
                  <button onClick={() => moveQuestion(index, -1)} disabled={index === 0} className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-30">↑</button>
                  <button onClick={() => moveQuestion(index, 1)} disabled={index === questions.length - 1} className="rounded-lg px-2 py-1 text-sm text-gray-500 hover:bg-gray-50 disabled:opacity-30">↓</button>
                  <button onClick={() => editQuestion(index)} className="rounded-lg px-2 py-1 text-sm text-indigo-600 hover:bg-indigo-50">Edit</button>
                  <button onClick={() => deleteQuestion(index)} className="rounded-lg px-2 py-1 text-sm text-red-600 hover:bg-red-50">Delete</button>
                </div>
              </div>

              {expandedQ === index && (
                <div className="mt-3 space-y-2 border-t pt-3">
                  <p className="text-sm">{q.question_text}</p>
                  {q.code_snippet && (
                    <pre className="rounded-lg bg-gray-900 p-3 font-mono text-sm text-green-400">{q.code_snippet}</pre>
                  )}
                  <div className="grid grid-cols-2 gap-2">
                    {q.options.map((opt, i) => (
                      <div key={i} className={`rounded-lg border px-3 py-2 text-sm ${i === q.correct_option ? 'border-green-300 bg-green-50 text-green-700' : 'border-gray-200 bg-gray-50 text-gray-600'}`}>
                        <span className="font-bold">{String.fromCharCode(65 + i)}.</span> {opt}
                        {i === q.correct_option && <span className="ml-2 text-xs font-semibold">(Correct)</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          {questions.length === 0 && (
            <div className="rounded-xl border border-dashed border-gray-200 p-8 text-center text-gray-400">
              No questions yet. Click "+ Add Question" to get started.
            </div>
          )}
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="mt-6 flex items-center justify-between rounded-2xl bg-white p-4 shadow-sm">
        <button onClick={() => router.push('/manage-assessments')} className="rounded-lg border border-gray-200 px-6 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50">
          Cancel
        </button>
        <div className="flex gap-3">
          <button onClick={() => setPreviewOpen(true)} className="rounded-lg border border-gray-200 px-6 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50">
            Preview
          </button>
          <button onClick={() => saveAssessment(false)} disabled={saving} className="rounded-lg border border-gray-200 px-6 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save as Draft'}
          </button>
          <button onClick={() => saveAssessment(true)} disabled={saving} className="rounded-lg bg-indigo-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Publishing...' : 'Publish'}
          </button>
        </div>
      </div>

      {/* Preview Modal */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-2xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">Preview: {title || 'Untitled Assessment'}</h2>
              <button onClick={() => setPreviewOpen(false)} className="rounded-lg px-3 py-1 text-gray-500 hover:bg-gray-50">Close</button>
            </div>
            <div className="space-y-4">
              <p className="text-sm text-gray-500">{description || 'No description'}</p>
              <div className="flex gap-4 text-sm text-gray-500">
                <span>Category: {category}</span>
                <span>Difficulty: {difficulty}</span>
                <span>Duration: {duration} min</span>
                <span>Pass: {passMark}%</span>
              </div>
              {questions.map((q, i) => (
                <div key={i} className="rounded-xl border border-gray-100 bg-slate-50 p-4">
                  <p className="font-medium">{i + 1}. {q.question_text}</p>
                  {q.code_snippet && <pre className="mt-2 rounded bg-gray-900 p-2 font-mono text-xs text-green-400">{q.code_snippet}</pre>}
                  <div className="mt-2 space-y-1">
                    {q.options.map((opt, j) => (
                      <div key={j} className={`rounded px-3 py-2 text-sm ${j === q.correct_option ? 'bg-green-100 text-green-700' : 'bg-white'}`}>
                        {String.fromCharCode(65 + j)}. {opt}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AssessmentBuilderPage() {
  return (
    <DashboardShell>
      <BuilderContent />
    </DashboardShell>
  );
}
