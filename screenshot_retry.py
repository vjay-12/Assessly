import asyncio
import os
from playwright.async_api import async_playwright

os.makedirs('screenshots', exist_ok=True)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})

        # Test login API first
        print("Testing auth API...")
        import urllib.request, json
        req = urllib.request.Request(
            'http://localhost:3001/auth/login',
            data=json.dumps({"email": "alex.rivera@example.com", "password": "candidate123"}).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"Login API status: {resp.status}")
                data = json.loads(resp.read())
                print(f"Login response keys: {list(data.keys())}")
                token = data.get('access_token')
        except Exception as e:
            print(f"Login API failed: {e}")
            token = None

        # Screenshot candidate portal with longer wait
        print("Screenshot: Candidate Portal Login...")
        await page.goto('http://localhost:4000/login', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(5000)  # Extra wait for Tailwind compilation
        await page.screenshot(path='screenshots/01_candidate_login_v2.png', full_page=False)
        print("  -> screenshots/01_candidate_login_v2.png")

        # Try automated login
        if token:
            print("Screenshot: Candidate Dashboard (injecting token)...")
            await page.evaluate(f"localStorage.setItem('access_token', '{token}')")
            await page.goto('http://localhost:4000/dashboard', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path='screenshots/02_candidate_dashboard_v2.png', full_page=False)
            print("  -> screenshots/02_candidate_dashboard_v2.png")
        else:
            print("Skipping candidate dashboard - no token")

        # Assessment engine with token
        print("Screenshot: Assessment Engine...")
        if token:
            # Get cross-app token
            req2 = urllib.request.Request(
                'http://localhost:3001/auth/cross-app-token',
                data=json.dumps({"application_id": "11111111-1111-1111-1111-111111111111"}).encode(),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req2, timeout=10) as resp:
                    cross_app = json.loads(resp.read())
                    opaque_token = cross_app.get('token')
                    print(f"Cross-app token obtained: {opaque_token[:20]}...")
            except Exception as e:
                print(f"Cross-app token failed: {e}")
                opaque_token = None

            if opaque_token:
                await page.goto(f'http://localhost:4001/assessment?token={opaque_token}', wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(5000)
                await page.screenshot(path='screenshots/03_assessment_engine_v2.png', full_page=False)
                print("  -> screenshots/03_assessment_engine_v2.png")
            else:
                await page.goto('http://localhost:4001/assessment', wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(5000)
                await page.screenshot(path='screenshots/03_assessment_engine_v2.png', full_page=False)
                print("  -> screenshots/03_assessment_engine_v2.png")
        else:
            await page.goto('http://localhost:4001/assessment', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path='screenshots/03_assessment_engine_v2.png', full_page=False)
            print("  -> screenshots/03_assessment_engine_v2.png")

        await browser.close()
        print("Done")

asyncio.run(main())
