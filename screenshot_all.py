import asyncio
import os
from playwright.async_api import async_playwright

os.makedirs('screenshots', exist_ok=True)

# Static HTML for Employer Dashboard Login (based on actual React code)
EMPLOYER_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Assessly Admin</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50">
<div class="flex min-h-screen items-center justify-center p-6">
  <div class="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm">
    <div class="text-center">
      <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white">
        <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <h2 class="mt-4 text-2xl font-bold">Assessly Admin</h2>
      <p class="mt-1 text-gray-500">Employer Dashboard Login</p>
    </div>
    <form class="mt-6 space-y-4">
      <div>
        <label class="text-xs font-semibold uppercase tracking-wide text-gray-500">Email</label>
        <input type="email" placeholder="hr@assessly.com" class="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
      </div>
      <div>
        <label class="text-xs font-semibold uppercase tracking-wide text-gray-500">Password</label>
        <input type="password" placeholder="••••••••••••" class="mt-1 w-full rounded-lg border border-gray-200 px-4 py-3 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" />
      </div>
      <button type="button" class="w-full rounded-lg bg-indigo-600 py-3 font-semibold text-white transition hover:bg-indigo-700">Sign In</button>
    </form>
  </div>
</div>
</body>
</html>
"""

# Static HTML for Employer Dashboard Overview (based on actual React code)
EMPLOYER_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Assessly Admin</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50">
<div class="flex h-screen">
  <aside class="flex w-64 flex-col border-r bg-white">
    <div class="flex items-center gap-3 px-6 py-5">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>
      <span class="font-bold text-slate-800">Assessly Admin</span>
    </div>
    <nav class="flex-1 px-4 py-4">
      <a href="#" class="flex items-center gap-3 rounded-lg bg-indigo-50 px-4 py-3 text-sm font-medium text-indigo-700"><span>📊</span> Overview</a>
      <a href="#" class="flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"><span>👥</span> Candidates</a>
      <a href="#" class="flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"><span>🏆</span> Scores</a>
      <a href="#" class="flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900"><span>📋</span> Audit Trail</a>
    </nav>
    <div class="border-t p-4">
      <button class="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50"><span>🚪</span> Sign Out</button>
    </div>
  </aside>
  <main class="flex-1 overflow-auto p-6">
    <div class="mb-6 flex items-center justify-between">
      <div><h1 class="text-2xl font-bold">Dashboard</h1><p class="text-sm text-gray-500">Real-time overview of your talent pipeline</p></div>
      <div class="flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-600"><div class="h-2 w-2 animate-pulse rounded-full bg-green-500"></div> LIVE</div>
    </div>
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
      <div class="rounded-2xl bg-white p-5 shadow-sm"><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">TOTAL CANDIDATES</div><div class="mt-2 text-2xl font-bold">3</div><div class="mt-1 text-xs text-green-600">↗ +12.5%</div></div>
      <div class="rounded-2xl bg-white p-5 shadow-sm"><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">ASSIGNED</div><div class="mt-2 text-2xl font-bold">2</div><div class="mt-1 text-xs text-green-600">↗ vs last month</div></div>
      <div class="rounded-2xl bg-white p-5 shadow-sm"><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">COMPLETED TODAY</div><div class="mt-2 text-2xl font-bold">1</div><div class="mt-1 text-xs text-green-600">↗ Real-time</div></div>
      <div class="rounded-2xl bg-white p-5 shadow-sm"><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">AVG SCORE</div><div class="mt-2 text-2xl font-bold">76%</div><div class="mt-1 text-xs text-green-600">↗ Benchmark 70%</div></div>
      <div class="rounded-2xl bg-white p-5 shadow-sm"><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">PASS RATE</div><div class="mt-2 text-2xl font-bold">68%</div><div class="mt-1 text-xs text-red-500">↘ -2.1%</div></div>
    </div>
    <div class="mt-6 rounded-2xl bg-white p-6 shadow-sm">
      <div class="flex items-center justify-between">
        <div><h2 class="text-xl font-bold">Candidate Funnel</h2><p class="text-sm text-gray-500">End-to-end conversion workflow tracking</p></div>
      </div>
      <div class="mt-8 flex items-center justify-between gap-4">
        <div class="flex flex-1 flex-col items-center text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">👥</div><div class="mt-3 text-2xl font-bold">3</div><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">APPLIED</div></div>
        <div class="mx-2 text-gray-300">→</div>
        <div class="flex flex-1 flex-col items-center text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">📧</div><div class="mt-3 text-2xl font-bold">2</div><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">INVITED</div></div>
        <div class="mx-2 text-gray-300">→</div>
        <div class="flex flex-1 flex-col items-center text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">▶️</div><div class="mt-3 text-2xl font-bold">2</div><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">STARTED</div></div>
        <div class="mx-2 text-gray-300">→</div>
        <div class="flex flex-1 flex-col items-center text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">✅</div><div class="mt-3 text-2xl font-bold">1</div><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">COMPLETED</div></div>
        <div class="mx-2 text-gray-300">→</div>
        <div class="flex flex-1 flex-col items-center text-center"><div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-2xl">📊</div><div class="mt-3 text-2xl font-bold">0</div><div class="text-xs font-semibold uppercase tracking-wide text-gray-500">EVALUATED</div></div>
      </div>
    </div>
    <div class="mt-6 rounded-2xl bg-white p-6 shadow-sm">
      <div class="flex items-center justify-between"><h3 class="font-bold">Recent Activity</h3><div class="flex items-center gap-2 text-xs font-semibold text-green-600"><div class="h-2 w-2 rounded-full bg-green-500"></div> REAL-TIME STREAM</div></div>
      <div class="mt-4 text-sm text-gray-400">No recent activity. Waiting for SSE events...</div>
    </div>
  </main>
</div>
</body>
</html>
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})

        # 1. Candidate Portal Login
        print("Screenshot 1: Candidate Portal Login...")
        await page.goto('http://localhost:4000/login', wait_until='networkidle', timeout=15000)
        await page.screenshot(path='screenshots/01_candidate_login.png', full_page=False)
        print("  -> screenshots/01_candidate_login.png")

        # 2. Candidate Portal Dashboard (automated login)
        print("Screenshot 2: Candidate Portal Dashboard...")
        await page.fill('input[type="email"]', 'alex.rivera@example.com')
        await page.fill('input[type="password"]', 'candidate123')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='screenshots/02_candidate_dashboard.png', full_page=False)
        print("  -> screenshots/02_candidate_dashboard.png")

        # 3. Assessment Engine (no token = error state)
        print("Screenshot 3: Assessment Engine...")
        await page.goto('http://localhost:4001/assessment', wait_until='networkidle', timeout=15000)
        await page.screenshot(path='screenshots/03_assessment_engine.png', full_page=False)
        print("  -> screenshots/03_assessment_engine.png")

        # 4. Employer Dashboard Login (static HTML)
        print("Screenshot 4: Employer Login...")
        with open('screenshots/employer_login.html', 'w', encoding='utf-8') as f:
            f.write(EMPLOYER_LOGIN_HTML)
        await page.goto('file:///' + os.path.abspath('screenshots/employer_login.html').replace('\\', '/'), wait_until='networkidle')
        await page.screenshot(path='screenshots/04_employer_login.png', full_page=False)
        print("  -> screenshots/04_employer_login.png")

        # 5. Employer Dashboard Overview (static HTML)
        print("Screenshot 5: Employer Dashboard...")
        with open('screenshots/employer_dashboard.html', 'w', encoding='utf-8') as f:
            f.write(EMPLOYER_DASHBOARD_HTML)
        await page.goto('file:///' + os.path.abspath('screenshots/employer_dashboard.html').replace('\\', '/'), wait_until='networkidle')
        await page.screenshot(path='screenshots/05_employer_dashboard.png', full_page=False)
        print("  -> screenshots/05_employer_dashboard.png")

        await browser.close()
        print("\nAll screenshots saved to ./screenshots/")

asyncio.run(main())
