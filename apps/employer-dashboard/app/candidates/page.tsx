'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DashboardShell from '../../components/DashboardShell';

interface Candidate {
  id: string;
  full_name: string;
  email: string;
  is_verified: boolean;
  application_status: string | null;
  score_percentage: number | null;
  assigned_assessments?: string[];
}

interface Assessment {
  id: string;
  title: string;
}

function CandidatesContent() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showAssign, setShowAssign] = useState(false);
  const [createForm, setCreateForm] = useState({ email: '', password: '', full_name: '', role: 'candidate' });
  const [assignForm, setAssignForm] = useState({ candidate_id: '', assessment_id: '' });
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [toast, setToast] = useState('');

  const router = useRouter();
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : '';

  const handleUnauthorized = (res: Response) => {
    if (res.status === 401) {
      localStorage.clear();
      router.push('/login');
      return true;
    }
    return false;
  };

  const fetchCandidates = () => {
    if (!token) return;
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/candidates?limit=100`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (handleUnauthorized(r)) return;
        return r.json();
      })
      .then((data) => {
        if (data) setCandidates(Array.isArray(data) ? data : []);
      })
      .catch(() => {});
  };

  const fetchAssessments = () => {
    if (!token) return;
    fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assessments`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (handleUnauthorized(r)) return;
        return r.json();
      })
      .then((data) => {
        if (data) setAssessments(Array.isArray(data) ? data : []);
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchCandidates();
    fetchAssessments();
    setLoading(false);
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(createForm),
      });
      console.log('Create user response status:', res.status);
      if (handleUnauthorized(res)) return;
      const data = await res.json();
      console.log('Create user response body:', data);
      if (!res.ok) {
        setFormError(data.detail || 'Failed to create user');
        return;
      }
      setFormSuccess(`User ${data.email} created successfully`);
      setCreateForm({ email: '', password: '', full_name: '', role: 'candidate' });
      fetchCandidates();
      setTimeout(() => setShowCreate(false), 1500);
    } catch (err) {
      console.error('Create user error:', err);
      setFormError('Network error');
    }
  };

  const handleDeleteUser = async (id: string) => {
    if (!confirm('Are you sure you want to delete this candidate?')) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/users/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (handleUnauthorized(res)) return;
      if (res.ok) {
        setToast('Candidate deleted successfully');
        fetchCandidates();
        setTimeout(() => setToast(''), 3000);
      } else {
        const data = await res.json();
        alert(data.detail || 'Delete failed');
      }
    } catch {
      alert('Network error');
    }
  };

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_GATEWAY_URL}/api/assignments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(assignForm),
      });
      if (handleUnauthorized(res)) return;
      const data = await res.json();
      if (!res.ok) {
        setFormError(data.detail || 'Failed to assign assessment');
        return;
      }
      setFormSuccess('Assessment assigned successfully');
      setAssignForm({ candidate_id: '', assessment_id: '' });
      fetchCandidates();
      setTimeout(() => setShowAssign(false), 1500);
    } catch {
      setFormError('Network error');
    }
  };

  const filtered = candidates.filter(
    (c) =>
      c.full_name.toLowerCase().includes(search.toLowerCase()) ||
      c.email.toLowerCase().includes(search.toLowerCase())
  );

  const statusBadge = (status: string | null) => {
    if (!status) return <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">—</span>;
    const map: Record<string, string> = {
      applied: 'bg-blue-50 text-blue-700',
      attempted: 'bg-amber-50 text-amber-700',
      submitted: 'bg-purple-50 text-purple-700',
      evaluated: 'bg-green-50 text-green-700',
    };
    return (
      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${map[status] || 'bg-gray-100 text-gray-600'}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="p-6">
      {toast && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{toast}</div>
      )}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Candidates</h1>
          <p className="text-sm text-gray-500">Track candidate progress through the assessment pipeline</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowAssign(true); setFormError(''); setFormSuccess(''); }}
            className="rounded-lg border border-indigo-200 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Assign Assessment
          </button>
          <button
            onClick={() => { setShowCreate(true); setFormError(''); setFormSuccess(''); }}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            + Create User
          </button>
          <div className="w-64">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or email..."
              className="w-full rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>
        </div>
      </div>

      {showCreate && (
        <div className="mb-6 rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-bold">Create New User</h3>
          {formError && <div className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">{formError}</div>}
          {formSuccess && <div className="mb-3 rounded-lg bg-green-50 p-3 text-sm text-green-600">{formSuccess}</div>}
          <form onSubmit={handleCreateUser} className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <input
              type="text"
              placeholder="Full Name"
              value={createForm.full_name}
              onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={createForm.email}
              onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={createForm.password}
              onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              required
              minLength={6}
            />
            <div className="flex gap-2">
              <select
                value={createForm.role}
                onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              >
                <option value="candidate">Candidate</option>
                <option value="admin">Admin</option>
              </select>
              <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                Create
              </button>
              <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {showAssign && (
        <div className="mb-6 rounded-2xl bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-bold">Assign Assessment</h3>
          {formError && <div className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-600">{formError}</div>}
          {formSuccess && <div className="mb-3 rounded-lg bg-green-50 p-3 text-sm text-green-600">{formSuccess}</div>}
          <form onSubmit={handleAssign} className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <select
              value={assignForm.candidate_id}
              onChange={(e) => setAssignForm({ ...assignForm, candidate_id: e.target.value })}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              required
            >
              <option value="">Select Candidate</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>{c.full_name} ({c.email})</option>
              ))}
            </select>
            <select
              value={assignForm.assessment_id}
              onChange={(e) => setAssignForm({ ...assignForm, assessment_id: e.target.value })}
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm outline-none focus:border-indigo-500"
              required
            >
              <option value="">Select Assessment</option>
              {assessments.map((a) => (
                <option key={a.id} value={a.id}>{a.title}</option>
              ))}
            </select>
            <div className="flex gap-2">
              <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                Assign
              </button>
              <button type="button" onClick={() => setShowAssign(false)} className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="rounded-2xl bg-white shadow-sm overflow-x-auto">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-gray-500">
              <th className="px-6 py-4">Candidate</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Progress</th>
              <th className="px-6 py-4">Assigned Assessments</th>
              <th className="px-6 py-4">Score</th>
              <th className="px-6 py-4">Verified</th>
              <th className="px-6 py-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                </td>
              </tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  No candidates found.
                </td>
              </tr>
            )}
            {filtered.map((c) => (
              <tr key={c.id} className="border-b last:border-0 transition-colors hover:bg-indigo-50">
                <td className="px-6 py-4">
                  <div className="font-medium">{c.full_name}</div>
                  <div className="text-gray-500">{c.email}</div>
                </td>
                <td className="px-6 py-4">{statusBadge(c.application_status)}</td>
                <td className="px-6 py-4">
                  <div className="h-2 w-32 rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{
                        width:
                          c.application_status === 'evaluated'
                            ? '100%'
                            : c.application_status === 'submitted'
                            ? '75%'
                            : c.application_status === 'attempted'
                            ? '50%'
                            : '25%',
                      }}
                    />
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="group relative inline-block cursor-default">
                    {c.assigned_assessments && c.assigned_assessments.length > 0 ? (
                      <>
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                            <path fillRule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 00-2 2v6a2 2 0 002 2h2a1 1 0 100-2H6V7h5a1 1 0 011-1h2a1 1 0 011 1v5h1V9a3 3 0 00-3-3H4z" clipRule="evenodd" />
                          </svg>
                          {c.assigned_assessments.length} Assessment{c.assigned_assessments.length !== 1 ? 's' : ''}
                        </span>
                        <div className="pointer-events-none absolute left-1/2 top-full z-50 mt-2 w-max max-w-xs -translate-x-1/2 rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                          <div className="font-semibold mb-1">Assigned Assessments:</div>
                          <ul className="list-disc pl-4">
                            {c.assigned_assessments.map((title, i) => (
                              <li key={i}>{title}</li>
                            ))}
                          </ul>
                        </div>
                      </>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {c.score_percentage !== null ? (
                    <span className="font-semibold">{c.score_percentage != null ? `${c.score_percentage.toFixed(1)}%` : '—'}</span>
                  ) : (
                    <span className="text-gray-400">—</span>
                  )}
                </td>
                <td className="px-6 py-4">
                  {c.is_verified ? (
                    <span className="rounded-full bg-green-50 px-2 py-1 text-xs font-semibold text-green-700">YES</span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-500">NO</span>
                  )}
                </td>
                <td className="px-6 py-4 text-center">
                  <button
                    onClick={() => handleDeleteUser(c.id)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600"
                    title="Delete candidate"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function CandidatesPage() {
  return (
    <DashboardShell>
      <CandidatesContent />
    </DashboardShell>
  );
}
