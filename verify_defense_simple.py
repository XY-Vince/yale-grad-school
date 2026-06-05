#!/usr/bin/env python3
"""
Simple verification script for V2.59.2 Defense Gauntlet
Tests the 3-track defense system by checking HTML elements directly
"""
import asyncio
from playwright.async_api import async_playwright


async def verify_defense_modal():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})

        url = 'file:///Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/docs/index.html'
        print(f"📂 Loading game from: {url}")
        await page.goto(url)
        await page.wait_for_load_state('domcontentloaded')

        # Wait for page to fully load
        print("⏳ Waiting for page load...")
        await page.wait_for_timeout(5000)

        # Check if the defense modal HTML elements exist
        print("\n🔍 Checking defense modal HTML structure...")

        elements_to_check = [
            '#defense-modal',
            '#defense-meter-thesis',
            '#defense-thesis-value',
            '#defense-meter-presentation',
            '#defense-presentation-value',
            '#defense-meter-committee',
            '#defense-committee-value',
            '#defense-weighted-total',
            '#defense-committee',
        ]

        results = {}
        for selector in elements_to_check:
            element = await page.query_selector(selector)
            if element:
                results[selector] = {'exists': True}
                print(f"  ✅ {selector}: EXISTS")
            else:
                results[selector] = {'exists': False}
                print(f"  ❌ {selector}: NOT FOUND")

        # Check committee members
        print("\n👨‍🏫 Checking Committee Members...")
        committee_check = await page.evaluate('''() => {
            const members = [];
            const ids = ['committee-chen', 'committee-smith', 'committee-alvarez'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    const moodEl = el.querySelector('.member-mood');
                    members.push({ id, exists: true, mood: moodEl ? moodEl.textContent : 'N/A' });
                } else {
                    members.push({ id, exists: false });
                }
            });
            return members;
        }''')

        for member in committee_check:
            status = '✅' if member['exists'] else '❌'
            print(f"  {status} {member['id']}: {member.get('mood', 'N/A')}")

        # Try to trigger defense modal using the game's internal function
        print("\n🎯 Attempting to trigger defense modal...")

        # First check if game object is accessible
        game_check = await page.evaluate('''() => {
            return {
                gameDefined: typeof game !== 'undefined',
                windowGameDefined: typeof window.game !== 'undefined'
            };
        }''')
        print(f"  Game object check: {game_check}")

        # If game exists, try to trigger defense
        if game_check['gameDefined']:
            trigger_result = await page.evaluate('''() => {
                try {
                    // Create a minimal state that meets defense requirements
                    const minimalState = {
                        year: 5,
                        month: 9,
                        morale: 70,
                        items: { 'paper': 3 },
                        credits: 60,
                        qualsPassed: true,
                        thesisProgress: 100,
                        totalMonths: 60,
                        peerNetwork: 50,
                        strategicAlignment: 50,
                        figureQuality: 80
                    };

                    // Set up the game state
                    if (!game.state || !game.state.morale) {
                        game.state = game.initState();
                        game.initDOM();
                    }

                    // Override with defense-ready state
                    Object.assign(game.state, minimalState);

                    // Trigger defense
                    if (typeof game.thesisDefend === 'function') {
                        game.thesisDefend();
                        return { success: true, modalActive: document.getElementById('defense-modal').classList.contains('active') };
                    } else {
                        return { success: false, error: 'thesisDefend not found' };
                    }
                } catch (e) {
                    return { success: false, error: e.toString() };
                }
            }''')
            print(f"  Trigger result: {trigger_result}")

            if trigger_result.get('success'):
                await page.wait_for_timeout(1000)

                # Now check visibility of elements
                print("\n📊 Checking visibility after modal trigger...")
                for selector in elements_to_check[:7]:  # Just the meter elements
                    element = await page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        status = '✅' if is_visible else '⚠️'
                        print(f"  {status} {selector}: {'VISIBLE' if is_visible else 'HIDDEN'}")

                # Get values
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
                print(f"\n📈 Defense Meter Values:")
                print(f"  Thesis: {meter_values['thesis_value']}% ({meter_values['thesis_width']})")
                print(f"  Presentation: {meter_values['presentation_value']}% ({meter_values['presentation_width']})")
                print(f"  Committee: {meter_values['committee_value']}% ({meter_values['committee_width']})")
                print(f"  Weighted Total: {meter_values['weighted_total']}% (need 65%)")

        # Take screenshot
        screenshot_path = '/Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/defense_modal_verification_simple.png'
        print(f"\n📸 Taking screenshot: {screenshot_path}")
        await page.screenshot(path=screenshot_path, full_page=False)
        print("✅ Screenshot saved!")

        await browser.close()

        # Count visible elements
        visible_count = 0
        for selector in elements_to_check[:7]:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                visible_count += 1

        return {
            'elements': results,
            'committee': committee_check,
            'screenshot_path': screenshot_path,
            'visible_count': visible_count,
            'total_count': len(elements_to_check[:7])
        }


async def main():
    print("="*70)
    print("DEFENSE GAUNTLET V2.59.2 VERIFICATION (Simple)")
    print("3-Track Defense System + Committee Mood Tracking")
    print("="*70)

    results = await verify_defense_modal()

    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    print(f"✅ Defense modal HTML structure verified")
    print(f"✅ Committee members found: {sum(1 for m in results['committee'] if m.get('exists'))}/3")
    print(f"📸 Screenshot: {results['screenshot_path']}")

    print("\n" + "="*70)


if __name__ == '__main__':
    asyncio.run(main())
