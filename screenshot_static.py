import asyncio
import os
from playwright.async_api import async_playwright

os.makedirs('screenshots', exist_ok=True)

CANDIDATE_LOGIN_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Assessly — Candidate Portal</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="flex min-h-screen">
<div class="hidden w-1/2 flex-col justify-between bg-gradient-to-br from-slate-900 to-indigo-700 p-12 text-white lg:flex">
  <div class="flex items-center gap-3">
    <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
      <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
      </svg>
    </div><span class="text-xl font-bold">Assessly</span>
  </div>
  <div>
    <h1 class="text-4xl font-bold leading-tight">Your journey to <span class="text-indigo-200">excellence</span> starts here.</h1>
    <p class="mt-4 text-lg text-white/80">Welcome to the Assessly Evaluation Portal. A high-performance environment designed to showcase your true potential.</p>
  </div>
  <div class="flex gap-4">
    <div class="rounded-xl bg-white/10 p-4 backdrop-blur-sm"><div class="text-2xl">🔒</div><div class="mt-2 font-semibold">Encrypted</div><div class="text-sm text-white/70">End-to-end secure session</div></div>
    <div class="rounded-xl bg-white/10 p-4 backdrop-blur-sm"><div class="text-2xl">⚡</div><div class="mt-2 font-semibold">Live Feedback</div><div class="text-sm text-white/70">Real-time performance sync</div></div>
    <div class="rounded-xl bg-white/10 p-4 backdrop-blur-sm"><div class="text-2xl">✓</div><div class="mt-2 font-semibold">Verified</div><div class="text-sm text-white/70">Industry standard results</div></div>
  </div>
</div>
<div class="flex w-full items-center justify-center p-8 lg:w-1/2">
  <div class="w-full max-w-md">
    <h2 class="text-2xl font-bold">Candidate Login</h2>
    <p class="mt-1 text-gray-500">Access your personalized assessment suite.</p>
    <form class="mt-8 space-y-5">
      <div><label class="text-xs font-semibold uppercase tracking-wide text-gray-500">Professional Email</label>
        <input type="email" value="alex.rivera@example.com" class="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"/></div>
      <div><label class="text-xs font-semibold uppercase tracking-wide text-gray-500">Password</label>
        <input type="password" value="candidate123" class="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"/></div>
      <div class="flex items-center justify-between">
        <label class="flex items-center gap-2 text-sm text-gray-600"><input type="checkbox" class="rounded border-gray-300"/> Keep me authenticated</label>
        <a href="#" class="text-sm font-medium text-indigo-600 hover:underline">Forgot access?</a>
      </div>
      <button type="button" class="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-700">Start Assessment →</button>
    </form>
    <p class="mt-8 text-center text-sm text-gray-500">Secured by <span class="font-semibold text-gray-700">Assessly</span></p>
  </div>
</div>
</body></html>
"""

CANDIDATE_DASHBOARD_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Assessly — Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="min-h-screen bg-slate-50">
<nav class="border-b bg-white px-6 py-4">
  <div class="mx-auto flex max-w-6xl items-center justify-between">
    <div class="flex items-center gap-2">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div><span class="font-bold text-slate-800">Assessly</span>
    </div>
    <div class="flex items-center gap-4">
      <span class="text-sm text-gray-500">alex.rivera@example.com</span>
      <button class="text-sm text-gray-500 hover:text-gray-700">Logout</button>
    </div>
  </div>
</nav>
<main class="mx-auto max-w-6xl p-6">
  <div class="rounded-2xl bg-gradient-to-r from-slate-800 to-indigo-700 p-8 text-white">
    <h1 class="text-2xl font-bold">Hello Alex Rivera,</h1>
    <p class="mt-1 text-white/80">Welcome to your assessment dashboard. You have 1 active assessment ready.</p>
  </div>
  <div class="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
    <div class="rounded-2xl bg-white p-6 shadow-sm"><div class="text-2xl">📝</div><div class="mt-2 text-2xl font-bold">1</div><div class="text-sm text-gray-500">Total Assigned</div></div>
    <div class="rounded-2xl bg-white p-6 shadow-sm"><div class="text-2xl">✅</div><div class="mt-2 text-2xl font-bold">0</div><div class="text-sm text-gray-500">Completed</div></div>
    <div class="rounded-2xl bg-white p-6 shadow-sm"><div class="text-2xl">⏳</div><div class="mt-2 text-2xl font-bold">1</div><div class="text-sm text-gray-500">Pending</div></div>
    <div class="rounded-2xl bg-white p-6 shadow-sm"><div class="text-2xl">📊</div><div class="mt-2 text-2xl font-bold">—</div><div class="text-sm text-gray-500">Average Score</div></div>
  </div>
  <h2 class="mt-10 text-xl font-bold">My Assessments</h2>
  <div class="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
    <div class="rounded-2xl bg-white p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <span class="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">MCQ</span>
        <span class="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">PENDING</span>
      </div>
      <h3 class="mt-3 font-semibold">Full Stack Engineering Assessment</h3>
      <div class="mt-2 space-y-1 text-sm text-gray-500"><p>📝 10 Questions</p><p>⏱ 60 mins</p></div>
      <button class="mt-4 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Start Assessment</button>
    </div>
  </div>
</main>
</body></html>
"""

ASSESSMENT_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Assessly — Assessment</title>
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="flex h-screen bg-slate-50">
<div class="w-64 border-r bg-white p-6">
  <div class="text-xs font-semibold uppercase tracking-wide text-gray-500">Questions</div>
  <div class="mt-4 grid grid-cols-4 gap-2">
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-indigo-600 text-white">1</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-green-100 text-green-700">2</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-amber-100 text-amber-700">3</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">4</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">5</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">6</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">7</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">8</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">9</button>
    <button class="flex h-10 w-10 items-center justify-center rounded-lg text-sm font-semibold bg-gray-100 text-gray-600">10</button>
  </div>
  <div class="mt-6 space-y-2 text-sm">
    <div class="flex items-center gap-2"><div class="h-3 w-3 rounded bg-green-100"></div> Answered</div>
    <div class="flex items-center gap-2"><div class="h-3 w-3 rounded bg-indigo-600"></div> Current</div>
    <div class="flex items-center gap-2"><div class="h-3 w-3 rounded bg-amber-100"></div> Flagged</div>
    <div class="flex items-center gap-2"><div class="h-3 w-3 rounded bg-gray-100"></div> Unanswered</div>
  </div>
</div>
<div class="flex flex-1 flex-col">
  <div class="flex items-center justify-between border-b bg-white px-8 py-4">
    <div class="text-sm text-gray-500">Assessly Assessment Engine <span class="mx-2">|</span> <span class="font-semibold text-gray-800">Full Stack Engineering</span></div>
    <div class="flex items-center gap-6">
      <div class="flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2 text-sm font-mono font-semibold">⏱ 28:45</div>
      <div class="text-sm text-gray-500">Question 1 of 10</div>
    </div>
  </div>
  <div class="flex-1 overflow-auto p-8">
    <div class="mx-auto max-w-3xl">
      <div class="mb-2 inline-block rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-600">QUESTION 1</div>
      <h2 class="text-xl font-semibold leading-relaxed">What is the primary purpose of an API Gateway in a microservices architecture?</h2>
      <div class="mt-6 space-y-3">
        <button class="flex w-full items-start gap-4 rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-indigo-300">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-sm font-bold text-gray-600">A</div>
          <span class="mt-0.5 text-sm">To store business logic</span>
        </button>
        <button class="flex w-full items-start gap-4 rounded-xl border border-indigo-500 bg-indigo-50 p-4 text-left transition">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">B</div>
          <span class="mt-0.5 text-sm">To route requests, enforce authentication, and aggregate responses</span>
        </button>
        <button class="flex w-full items-start gap-4 rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-indigo-300">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-sm font-bold text-gray-600">C</div>
          <span class="mt-0.5 text-sm">To replace the need for a database</span>
        </button>
        <button class="flex w-full items-start gap-4 rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-indigo-300">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-sm font-bold text-gray-600">D</div>
          <span class="mt-0.5 text-sm">To compile frontend assets</span>
        </button>
      </div>
    </div>
  </div>
  <div class="flex items-center justify-between border-t bg-white px-8 py-4">
    <button class="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">🚩 Flag for Review</button>
    <div class="flex items-center gap-3">
      <button class="rounded-lg border border-gray-200 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40" disabled>← Previous</button>
      <button class="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700">Save & Next →</button>
    </div>
  </div>
</div>
</body></html>
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})

        screens = [
            ("01_candidate_login_final", CANDIDATE_LOGIN_HTML),
            ("02_candidate_dashboard_final", CANDIDATE_DASHBOARD_HTML),
            ("03_assessment_engine_final", ASSESSMENT_HTML),
        ]

        for name, html in screens:
            path = f'screenshots/{name}.html'
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            await page.goto('file:///' + os.path.abspath(path).replace('\\', '/'), wait_until='networkidle')
            await page.screenshot(path=f'screenshots/{name}.png', full_page=False)
            print(f"Saved screenshots/{name}.png")

        await browser.close()

asyncio.run(main())
