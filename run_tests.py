#!/usr/bin/env python3
"""
Test runner for GradQuest docs/index.html
Uses Playwright to run the actual browser integration tests instead of python mocks.
"""

import sys
import os
import asyncio
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ModuleNotFoundError:
    print("Error: Playwright is required to run the actual browser integration tests.")
    print("Please install it via: pip install playwright && playwright install")
    sys.exit(1)

async def run_tests():
    async with async_playwright() as p:
        chrome_path = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        launch_args = {"headless": True}
        if chrome_path.exists():
            launch_args["executable_path"] = str(chrome_path)
        browser = await p.chromium.launch(**launch_args)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})

        # Build absolute path to docs/index.html
        base_dir = os.path.dirname(os.path.abspath(__file__))
        test_file = os.path.join(base_dir, 'docs', 'index.html')

        print(f"[TestSuite] Loading {test_file} in headless Chromium...")
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        await page.goto(f'file://{test_file}')

        # Inject the test suite into the shipped game
        test_script = os.path.join(base_dir, 'tests', 'browser_tests.js')
        await page.add_script_tag(path=test_script)

        print("[TestSuite] Waiting for tests to complete...")

        # Trigger the tests manually since DOMContentLoaded has already fired
        await page.evaluate('TestSuite.runAll()')

        # Wait for the summary to show PASSED or FAILED instead of "Running tests..."
        await page.wait_for_function('''() => {
            const summary = document.getElementById('test-summary');
            return summary && (summary.textContent.includes('PASSED') || summary.textContent.includes('FAILED'));
        }''', timeout=15000)

        # Extract summary
        summary_text = await page.evaluate('''() => {
            const summary = document.getElementById('test-summary');
            return summary ? summary.innerText : "Error: Summary not found";
        }''')

        # Extract details
        details_text = await page.evaluate('''() => {
            const details = document.getElementById('test-details');
            return details ? details.innerText : "";
        }''')

        await browser.close()

        print("=" * 60)
        print("GRADQUEST REGRESSION TEST RESULTS (BROWSER INTEGRATION)")
        print("=" * 60)
        print(f"\n{summary_text}\n")
        print("=" * 60)

        if details_text:
            print(details_text)
            print("=" * 60)

        if " 0 FAILED" in summary_text:
            sys.exit(0)
        elif "FAILED" in summary_text:
            sys.exit(1)
        else:
            sys.exit(0)

def main():
    asyncio.run(run_tests())

if __name__ == '__main__':
    main()
