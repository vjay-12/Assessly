'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Login failed');
        return;
      }

      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      router.push('/dashboard');
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-between bg-gradient-to-br from-slate-900 to-indigo-700 p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <span className="text-xl font-bold">Zetheta</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">
            Your journey to <span className="text-indigo-200">excellence</span> starts here.
          </h1>
          <p className="mt-4 text-lg text-white/80">
            Welcome to the Zetheta Evaluation Portal. A high-performance environment designed to showcase your true potential.
          </p>
        </div>
        <div className="flex gap-4">
          {[
            { icon: '🔒', title: 'Encrypted', desc: 'End-to-end secure session' },
            { icon: '⚡', title: 'Live Feedback', desc: 'Real-time performance sync' },
            { icon: '✓', title: 'Verified', desc: 'Industry standard results' },
          ].map((item) => (
            <div key={item.title} className="rounded-xl bg-white/10 p-4 backdrop-blur-sm">
              <div className="text-2xl">{item.icon}</div>
              <div className="mt-2 font-semibold">{item.title}</div>
              <div className="text-sm text-white/70">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex w-full items-center justify-center p-8 lg:w-1/2">
        <div className="w-full max-w-md">
          <h2 className="text-2xl font-bold">Candidate Login</h2>
          <p className="mt-1 text-gray-500">Access your personalized assessment suite.</p>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Professional Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                required
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                required
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" className="rounded border-gray-300" />
                Keep me authenticated
              </label>
              <a href="#" className="text-sm font-medium text-indigo-600 hover:underline">Forgot access?</a>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Start Assessment'}
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-gray-500">
            Secured by <span className="font-semibold text-gray-700">Zetheta</span>
          </p>
        </div>
      </div>
    </div>
  );
}
