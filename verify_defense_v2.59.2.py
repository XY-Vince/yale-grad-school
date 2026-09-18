#!/usr/bin/env python3
from pathlib import Path
"""
Verification script for V2.59.2 Defense Gauntlet
Tests the 3-Track defense system with committee mood tracking
"""
import asyncio
from playwright.async_api import async_playwright


async def verify_defense_modal():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})

        url = f'file://{Path(__file__).resolve().parent}/docs/index.html'
        print(f"📂 Loading game from: {url}")
        await page.goto(url)
        await page.wait_for_load_state('domcontentloaded')

        # Wait for game to initialize
        print("⏳ Waiting for game object to initialize...")
        await page.wait_for_timeout(4000)

        # Set up a game state ready for defense
        print("🎮 Setting up defense-ready state...")
        setup_result = await page.evaluate('''() => {
            // Check what's available
            const hasGame = typeof game !== 'undefined';
            const hasWindowGame = typeof window.game !== 'undefined';

            if (!hasGame) {
                return { success: false, error: 'game not in global scope', hasGame, hasWindowGame };
            }

            // Check if initState exists
            const hasInitState = typeof game.initState === 'function';
            const hasInitDOM = typeof game.initDOM === 'function';

            if (!hasInitState) {
                return { success: false, error: 'game.initState not found', hasInitState, hasInitDOM, hasGame };
            }

            // Initialize game state if not already done
            if (!game.state || !game.state.morale) {
                try {
                    game.state = game.initState();
                    if (hasInitDOM) {
                        game.initDOM();
                    }
                } catch (e) {
                    return { success: false, error: 'Failed to init state: ' + e.toString(), stack: e.stack };
                }
            }

            // Set up state that meets defense requirements:
            // - 3+ papers
            // - 100% thesis progress
            // - Quals passed
            const s = game.state;

            // Set papers (via item counts)
            if (!window.game.state.items) {
                window.game.state.items = {};
            }
            window.game.state.items['paper'] = 3;

            // Set thesis progress
            s.thesisProgress = 100;

            // Set credits (need 60 for PhD)
            s.credits = 60;

            // Set qual status
            s.qualStatus = 'passed';

            // Set other relevant stats
            s.morale = 70;
            s.funding = 12;
            s.totalMonths = 60; // 5 years
            s.strategicAlignment = 50;
            s.peerNetwork = 50;
            s.figureQuality = 80;

            // Expose game to window for later calls
            if (typeof window.game === 'undefined') {
                window.game = gameObj;
            }

            return {
                success: true,
                papers: gameObj.state.items['paper'],
                thesisProgress: s.thesisProgress,
                credits: s.credits,
                qualStatus: s.qualStatus,
                gameExposed: typeof window.game !== 'undefined'
            };
        }''')

        print(f"  Setup result: {setup_result}")

        # Trigger the defense modal
        print("\n🎯 Triggering defense modal via thesisDefend()...")
        defense_result = await page.evaluate('''() => {
            try {
                game.thesisDefend();
                return { success: true, modalShown: document.getElementById('defense-modal').classList.contains('active') };
            } catch (e) {
                return { success: false, error: e.toString() };
            }
        }''')

        print(f"  Defense triggered: {defense_result}")

        await page.wait_for_timeout(1000)

        # Check defense modal visibility
        print("\n🔍 Checking defense modal visibility...")
        modal_visible = await page.evaluate('''() => {
            const modal = document.getElementById('defense-modal');
            return {
                exists: modal !== null,
                hasActive: modal.classList.contains('active'),
                displayStyle: window.getComputedStyle(modal).display
            };
        }''')
        print(f"  Modal: exists={modal_visible['exists']}, active={modal_visible['hasActive']}, display={modal_visible['displayStyle']}")

        # Check 3-track meter elements
        print("\n📊 Checking 3-Track Defense Meters...")
        elements_to_check = [
            '#defense-meter-thesis',
            '#defense-meter-presentation',
            '#defense-meter-committee',
            '#defense-thesis-value',
            '#defense-presentation-value',
            '#defense-committee-value',
            '#defense-weighted-total'
        ]

        results = {}
        for selector in elements_to_check:
            element = await page.query_selector(selector)
            if element:
                is_visible = await element.is_visible()
                results[selector] = {
                    'exists': True,
                    'visible': is_visible
                }
                status = '✅' if is_visible else '⚠️'
                print(f"  {status} {selector}: {'VISIBLE' if is_visible else 'HIDDEN'}")
            else:
                results[selector] = {
                    'exists': False,
                    'visible': False
                }
                print(f"  ❌ {selector}: NOT FOUND")

        # Check committee members
        print("\n👨‍🏫 Checking Committee Members...")
        committee_members = await page.evaluate('''() => {
            const members = [];
            const memberEls = document.querySelectorAll('.committee-member');
            memberEls.forEach(el => {
                const id = el.id;
                const moodEl = el.querySelector('.member-mood');
                const mood = moodEl ? moodEl.textContent : 'N/A';
                members.push({ id, mood });
            });
            return members;
        }''')
        for member in committee_members:
            print(f"  ✓ {member['id']}: {member['mood']}")

        # Get defense meter values
        print("\n📈 Getting Defense Meter Values...")
        meter_values = await page.evaluate('''() => {
            return {
                thesis_width: document.getElementById('defense-meter-thesis')?.style.width,
                thesis_value: document.getElementById('defense-thesis-value')?.textContent,
                presentation_width: document.getElementById('defense-meter-presentation')?.style.width,
                presentation_value: document.getElementById('defense-presentation-value')?.textContent,
                committee_width: document.getElementById('defense-meter-committee')?.style.width,
                committee_value: document.getElementById('defense-committee-value')?.textContent,
                weighted_total: document.getElementById('defense-weighted-total')?.textContent
            };
        }''')
        print(f"  Thesis: {meter_values['thesis_value']}% ({meter_values['thesis_width']})")
        print(f"  Presentation: {meter_values['presentation_value']}% ({meter_values['presentation_width']})")
        print(f"  Committee: {meter_values['committee_value']}% ({meter_values['committee_width']})")
        print(f"  Weighted Total: {meter_values['weighted_total']}% (need 65%)")

        # Take screenshot
        screenshot_path = f'{Path(__file__).resolve().parent}/defense_modal_v2.59.2.png'
        print(f"\n📸 Taking screenshot: {screenshot_path}")
        await page.screenshot(path=screenshot_path, full_page=False)
        print("✅ Screenshot saved!")

        await browser.close()

        # Verify all required elements are visible
        all_visible = all(r.get('visible', False) for r in results.values())

        return {
            'modal_visible': modal_visible['hasActive'],
            'elements': results,
            'committee_members': committee_members,
            'meter_values': meter_values,
            'screenshot_path': screenshot_path,
            'all_visible': all_visible
        }


async def main():
    print("="*70)
    print("DEFENSE GAUNTLET V2.59.2 VERIFICATION")
    print("3-Track Defense System + Committee Mood Tracking")
    print("="*70)

    results = await verify_defense_modal()

    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    if results['modal_visible']:
        print("✅ Defense modal is ACTIVE")
    else:
        print("❌ Defense modal is NOT ACTIVE")

    if results['all_visible']:
        print("✅ All required defense meter elements are VISIBLE")
    else:
        print("❌ Some elements are missing or hidden")

    print(f"\n👨‍🏫 Committee Members Found: {len(results['committee_members'])}")
    print(f"📸 Screenshot saved to: {results['screenshot_path']}")

    print("\n" + "="*70)


if __name__ == '__main__':
    asyncio.run(main())
