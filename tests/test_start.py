#!/usr/bin/env python3
"""
Test script to verify GradQuest start screen functionality using Playwright.

Steps:
1. Load docs/index.html
2. Click .spec-card (e.g. experimentalist)
3. Verify #start-game-btn is enabled
4. Click #start-game-btn
5. Verify #game-screen is visible (display: block)

Output: "SUCCESS" or "FAILURE" with details.
"""

import sys
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


import os
from pathlib import Path

CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

def test_start_screen():
    """Run the start screen functionality test."""

    base_dir = Path(__file__).resolve().parent.parent
    url = f"file://{base_dir}/docs/index.html"
    console_logs = []
    page_errors = []

    try:
        with sync_playwright() as p:
            launch_args = {"headless": True}
            if CHROME.exists():
                launch_args["executable_path"] = str(CHROME)
            browser = p.chromium.launch(**launch_args)
            page = browser.new_page()

            page.on("console", lambda msg: console_logs.append((msg.type, msg.text)))
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            print(f"Loading {url}...")
            page.goto(url, wait_until="networkidle")
            page.wait_for_selector("#start-screen", timeout=10000)
            page.wait_for_timeout(2000)

            if page_errors:
                print("\nJavaScript errors detected:")
                for err in page_errors:
                    print(f"  ERROR: {err}")
                print("\nFAILURE: Cannot run tests due to JavaScript errors in the page.")
                browser.close()
                assert False, "Cannot run tests due to JavaScript errors in the page."

            game_defined = page.evaluate("""() => typeof game !== 'undefined'""")
            if not game_defined:
                print("\nFAILURE: Game object not initialized. Check JavaScript console for errors.")
                if console_logs:
                    print("\nConsole logs:")
                    for level, msg in console_logs[-10:]:
                        print(f"  [{level}] {msg}")
                browser.close()
                assert False, "Game object not initialized."

            print("Clicking on specialization card (experimentalist)...")
            spec_card = page.locator("#spec-experimentalist")
            spec_card.wait_for(state="visible", timeout=5000)
            spec_card.scroll_into_view_if_needed()
            spec_card.click()
            page.wait_for_timeout(1000)

            selection_text = page.evaluate("""() => {
                const el = document.getElementById('spec-selected');
                return el ? el.textContent.trim() : 'element not found';
            }""")
            print(f"Selection text: '{selection_text}'")

            print("Verifying start game button is enabled...")
            start_btn = page.locator("#start-game-btn")

            if not start_btn.is_visible():
                print("FAILURE: Start game button not visible")
                browser.close()
                assert False, "Start game button not visible"

            page.wait_for_timeout(500)
            has_disabled_attr = start_btn.evaluate("el => el.hasAttribute('disabled')")
            opacity = start_btn.evaluate("el => window.getComputedStyle(el).opacity")

            if has_disabled_attr or opacity == "0.5":
                print(f"FAILURE: Start game button is still disabled (has_disabled_attr={has_disabled_attr}, opacity={opacity})")
                browser.close()
                assert False, f"Start game button is still disabled (has_disabled_attr={has_disabled_attr}, opacity={opacity})"

            print("Start game button is enabled!")

            print("Clicking start game button...")
            start_btn.click()
            page.wait_for_timeout(500)

            print("Verifying game screen is visible...")
            game_screen = page.locator("#game-screen")

            if not game_screen.is_visible():
                print("FAILURE: Game screen is not visible")
                browser.close()
                assert False, "Game screen is not visible"

            display_style = game_screen.evaluate("el => window.getComputedStyle(el).display")

            assert display_style == "block", f"Game screen display style is '{display_style}', expected 'block'"

            start_screen = page.locator("#start-screen")
            start_display = start_screen.evaluate("el => window.getComputedStyle(el).display")

            if start_display != "none":
                print(f"WARNING: Start screen is still visible (display: {start_display})")

            browser.close()

    except PlaywrightTimeoutError as e:
        assert False, f"Timeout waiting for element - {e}"
    except Exception as e:
        assert False, f"Unexpected error - {type(e).__name__}: {e}"

if __name__ == "__main__":
    test_start_screen()
