'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';

function ResetForm() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Reset failed');
        return;
      }

      setMessage('Password updated! Redirecting to login...');
      setTimeout(() => router.push('/login'), 2000);
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-red-600">Invalid or missing reset token.</p>
        <Link href="/forgot-password" className="mt-4 inline-block text-indigo-600 hover:underline">
          Request a new reset link
        </Link>
      </div>
    );
  }

  return (
    <>
      {error && (
        <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}
      {message && (
        <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-600">{message}</div>
      )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">New Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            required
            minLength={6}
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">Confirm Password</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••••••"
            className="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            required
            minLength={6}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-600 py-3 font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Updating...' : 'Update Password'}
        </button>
      </form>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Set New Password</h2>
          <p className="mt-1 text-gray-500">Enter your new password below</p>
        </div>
        <Suspense fallback={<div className="mt-6 text-center text-gray-500">Loading...</div>}>
          <ResetForm />
        </Suspense>
      </div>
    </div>
  );
}
