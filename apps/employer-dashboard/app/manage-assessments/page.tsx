'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface Assessment {
  id: string;
  title: string;
  category: string;
  difficulty: string;
  duration_minutes: number;
  pass_mark: number;
  is_published: boolean;
  total_questions: number;
  created_at: string;
}

interface Candidate {
  id: string;
  full_name: string;
  email: string;
  already_assigned: boolean;
}

function ManageContent() {
  const router = useRouter();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignAssessment, setAssignAssessment] = useState<Assessment | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<string>>(new Set());
  const [dueDate, setDueDate] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [toast, setToast] = useState('');

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : '';

  const handleUnauthorized = (res: Response) => {
    if (res.status === 401) {
      localStorage.clear();
      router.push('/login');
      return true;
    }
    return false;
  };

  const fetchAssessments = () => {
    if (!token) return;
    const params = new URLSearchParams();
    if (filterCategory) params.append('category', filterCategory);
    if (filterDifficulty) params.append('difficulty', filterDifficulty);
    if (filterStatus) params.append('status', filterStatus);
    if (search) params.append('search', search);

    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments-all?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (handleUnauthorized(r)) return;
        return r.json();
      })
      .then((data) => {
        if (data) {
          setAssessments(Array.isArray(data) ? data : []);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    fetchAssessments();
  }, [filterCategory, filterDifficulty, filterStatus]);

  useEffect(() => {
    const timer = setTimeout(fetchAssessments, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const openAssign = async (assessment: Assessment) => {
    setAssignAssessment(assessment);
    setAssignModalOpen(true);
    setSelectedCandidates(new Set());
    setDueDate('');

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/candidates/for-assignment/${assessment.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (handleUnauthorized(res)) return;
    const data = await res.json();
    setCandidates(Array.isArray(data) ? data : []);
  };

  const toggleCandidate = (id: string) => {
    const next = new Set(selectedCandidates);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedCandidates(next);
  };

  const selectAll = () => {
    const available = candidates.filter((c) => !c.already_assigned).map((c) => c.id);
    setSelectedCandidates(new Set(available));
  };

  const deselectAll = () => {
    setSelectedCandidates(new Set());
  };

  const doAssign = async () => {
    if (!assignAssessment || selectedCandidates.size === 0) return;
    setAssigning(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments/${assignAssessment.id}/assign-bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ candidate_ids: Array.from(selectedCandidates), due_at: dueDate || null }),
      });
      if (handleUnauthorized(res)) return;
      const data = await res.json();
      if (res.ok) {
        setToast(`Assigned to ${data.assigned_count} candidate(s)`);
        setAssignModalOpen(false);
        setTimeout(() => setToast(''), 3000);
      } else {
        alert(data.detail || 'Assignment failed');
      }
    } catch {
      alert('Network error');
    } finally {
      setAssigning(false);
    }
  };

  const duplicateAssessment = async (id: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments/${id}/duplicate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (handleUnauthorized(res)) return;
      if (res.ok) {
        setToast('Assessment duplicated');
        fetchAssessments();
        setTimeout(() => setToast(''), 3000);
      } else {
        alert('Duplicate failed');
      }
    } catch {
      alert('Network error');
    }
  };

  const deleteAssessment = async (id: string) => {
    if (!confirm('Delete this assessment?')) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (handleUnauthorized(res)) return;
      if (res.ok) {
        setToast('Assessment deleted');
        fetchAssessments();
        setTimeout(() => setToast(''), 3000);
      } else {
        const data = await res.json();
        alert(data.detail || 'Delete failed');
      }
    } catch {
      alert('Network error');
    }
  };

  return (
    <div className="p-6">
      {toast && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{toast}</div>
      )}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Manage Assessments</h1>
          <p className="text-sm text-gray-500">Create, edit, assign, and organize assessments</p>
        </div>
        <button onClick={() => router.push('/assessment-builder')} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          + New Assessment
        </button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by title..."
          className="w-64 rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
        />
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500">
          <option value="">All Categories</option>
          {['Backend', 'Frontend', 'DSA', 'System Design', 'UI/UX', 'General'].map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filterDifficulty} onChange={(e) => setFilterDifficulty(e.target.value)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500">
          <option value="">All Difficulties</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500">
          <option value="">All Statuses</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-6 py-4">Title</th>
              <th className="px-6 py-4">Category</th>
              <th className="px-6 py-4">Difficulty</th>
              <th className="px-6 py-4">Questions</th>
              <th className="px-6 py-4">Duration</th>
              <th className="px-6 py-4">Pass Mark</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={8} className="px-6 py-12 text-center text-gray-400"><div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" /></td></tr>
            )}
            {!loading && assessments.length === 0 && (
              <tr><td colSpan={8} className="px-6 py-12 text-center text-gray-400">No assessments found.</td></tr>
            )}
            {assessments.map((a) => (
              <tr key={a.id} className="border-b last:border-0 hover:bg-slate-50">
                <td className="px-6 py-4 font-medium">{a.title}</td>
                <td className="px-6 py-4 text-gray-500">{a.category}</td>
                <td className="px-6 py-4">
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${a.difficulty === 'Easy' ? 'bg-green-50 text-green-700' : a.difficulty === 'Hard' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'}`}>
                    {a.difficulty}
                  </span>
                </td>
                <td className="px-6 py-4">{a.total_questions}</td>
                <td className="px-6 py-4">{a.duration_minutes} min</td>
                <td className="px-6 py-4">{a.pass_mark}%</td>
                <td className="px-6 py-4">
                  {a.is_published ? (
                    <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">Published</span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-500">Draft</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-1">
                    <button onClick={() => router.push(`/assessment-builder?id=${a.id}`)} className="rounded-md px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50">Edit</button>
                    <button onClick={() => openAssign(a)} className="rounded-md px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50">Assign</button>
                    <button onClick={() => duplicateAssessment(a.id)} className="rounded-md px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50">Duplicate</button>
                    <button onClick={() => deleteAssessment(a.id)} className="rounded-md px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Assign Modal */}
      {assignModalOpen && assignAssessment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-auto rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="mb-1 text-lg font-bold">Assign Assessment</h2>
            <p className="mb-4 text-sm text-gray-500">{assignAssessment.title}</p>

            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase text-gray-500">Candidates</span>
              <div className="flex gap-2">
                <button onClick={selectAll} className="text-xs text-indigo-600 hover:underline">Select All</button>
                <button onClick={deselectAll} className="text-xs text-gray-500 hover:underline">Clear</button>
              </div>
            </div>

            <div className="mb-4 max-h-64 overflow-auto rounded-lg border border-gray-200">
              {candidates.map((c) => (
                <label key={c.id} className={`flex items-center gap-3 border-b px-4 py-3 text-sm last:border-0 ${c.already_assigned ? 'bg-gray-50 text-gray-400' : 'hover:bg-gray-50'}`}>
                  <input
                    type="checkbox"
                    checked={selectedCandidates.has(c.id)}
                    onChange={() => toggleCandidate(c.id)}
                    disabled={c.already_assigned}
                    className="h-4 w-4"
                  />
                  <div className="flex-1">
                    <div className="font-medium">{c.full_name}</div>
                    <div className="text-xs text-gray-500">{c.email}</div>
                  </div>
                  {c.already_assigned && <span className="rounded-full bg-gray-200 px-2 py-0.5 text-xs text-gray-500">Already Assigned</span>}
                </label>
              ))}
            </div>

            <div className="mb-4">
              <label className="text-xs font-semibold uppercase text-gray-500">Due Date (optional)</label>
              <input type="datetime-local" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500" />
            </div>

            <div className="flex justify-end gap-2">
              <button onClick={() => setAssignModalOpen(false)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
              <button onClick={doAssign} disabled={assigning || selectedCandidates.size === 0} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                {assigning ? 'Assigning...' : `Assign to ${selectedCandidates.size}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ManageAssessmentsPage() {
  return (
    <DashboardShell>
      <ManageContent />
    </DashboardShell>
  );
}
