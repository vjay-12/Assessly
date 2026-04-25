import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})

        # 1. Candidate Portal Login
        try:
            await page.goto('http://localhost:4000/login', wait_until='networkidle', timeout=15000)
            await page.screenshot(path='screenshots/01_candidate_login.png', full_page=True)
            print('Screenshot 01_candidate_login.png saved')
        except Exception as e:
            print(f'Candidate login screenshot failed: {e}')

        # 2. Assessment Engine (no token = error state)
        try:
            await page.goto('http://localhost:4001/assessment', wait_until='networkidle', timeout=15000)
            await page.screenshot(path='screenshots/02_assessment_no_token.png', full_page=True)
            print('Screenshot 02_assessment_no_token.png saved')
        except Exception as e:
            print(f'Assessment screenshot failed: {e}')

        # 3. Employer Dashboard Login
        try:
            await page.goto('http://localhost:4002/login', wait_until='networkidle', timeout=15000)
            await page.screenshot(path='screenshots/03_employer_login.png', full_page=True)
            print('Screenshot 03_employer_login.png saved')
        except Exception as e:
            print(f'Employer login screenshot failed: {e}')

        await browser.close()

import os
os.makedirs('screenshots', exist_ok=True)
asyncio.run(main())
