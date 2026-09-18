#!/usr/bin/env python3
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
import json


async def verify_defense_modal():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})

        url = f'file://{Path(__file__).resolve().parent}/docs/index.html'
        print(f"📂 Loading game from: {url}")
        await page.goto(url)
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_timeout(2000)

        game_exists = await page.evaluate('''() => {
            return typeof window.game !== 'undefined';
        }''')
        print(f"  Game object exists: {game_exists}")

        if not game_exists:
            print("❌ Game object not found. Waiting longer...")
            await page.wait_for_timeout(3000)

        print("🎯 Setting up defense modal state...")
        result = await page.evaluate('''() => {
            // Access the existing game object
            if (!window.game || typeof window.game.updateDefenseUI !== 'function') {
                console.error('Game object not initialized', typeof window.game);
                return { success: false, error: 'Game not initialized' };
            }

            // Set up defense state
            window.game.defenseState = {
                turn: 1,
                maxTurns: 3,
                phases: ['Phase 1', 'Phase 2', 'Phase 3'],
                thesis_quality: 50,
                presentation_skill: 50,
                committee_support: 50,
                committee: [
                    { name: 'Dr. Smith', mood: 'neutral' },
                    { name: 'Dr. Johnson', mood: 'positive' },
                    { name: 'Dr. Williams', mood: 'skeptical' }
                ],
                skepticism: 1.0,
                portfolioLabel: 'Test Defense'
            };

            // Initialize state if needed
            if (!window.game.state) {
                window.game.state = {
                    morale: 70,
                    papers: 3,
                    credits: 60,
                    strategicAlignment: 50,
                    peerNetwork: 50
                };
            }

            // Update UI using game method
            window.game.updateDefenseUI();

            // Show modal - add active class to modal-overlay
            const modal = document.getElementById('defense-modal');
            if (modal) {
                modal.classList.add('active');
                return { success: true, modalId: modal.id, hasActive: modal.classList.contains('active') };
            } else {
                return { success: false, error: 'Modal not found' };
            }
        }''')

        print(f"  Defense state setup result: {result}")

        await page.wait_for_timeout(1000)

        print("\n🔍 Checking element visibility...")

        elements_to_check = [
            '#defense-modal',
            '#defense-meter-thesis',
            '#defense-meter-presentation',
            '#defense-meter-committee',
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

        print("\n📊 Defense Meter Details:")
        for selector in ['#defense-meter-thesis', '#defense-meter-presentation', '#defense-meter-committee', '#defense-weighted-total']:
            element = await page.query_selector(selector)
            if element:
                text = await element.text_content()
                print(f"  {selector}: {text[:100] if text else 'N/A'}")

        print("\n🎓 Defense Modal Content:")
        modal_content = await page.evaluate('''() => {
            const modal = document.getElementById('defense-modal');
            if (!modal) return 'Modal not found';

            const committee = [];
            const committeeEls = modal.querySelectorAll('.committee-member');
            committeeEls.forEach(el => {
                const name = el.querySelector('.committee-name')?.textContent;
                const mood = el.querySelector('.committee-mood')?.textContent;
                committee.push({ name, mood });
            });

            const phase = modal.querySelector('.defense-phase')?.textContent;
            const turn = modal.querySelector('.defense-turn')?.textContent;

            const thesisQuality = modal.querySelector('.stat-value.thesis-quality')?.textContent;
            const presentationSkill = modal.querySelector('.stat-value.presentation-skill')?.textContent;
            const committeeSupport = modal.querySelector('.stat-value.committee-support')?.textContent;
            const weightedTotal = modal.querySelector('.weighted-total')?.textContent;

            return {
                phase,
                turn,
                thesisQuality,
                presentationSkill,
                committeeSupport,
                weightedTotal,
                committee
            };
        }''')

        print(json.dumps(modal_content, indent=2))

        screenshot_path = f'{Path(__file__).resolve().parent}/defense_modal_verification.png'
        print(f"\n📸 Taking screenshot: {screenshot_path}")
        await page.screenshot(path=screenshot_path, full_page=False)
        print("✅ Screenshot saved!")

        await browser.close()

        return {
            'elements': results,
            'modal_content': modal_content,
            'screenshot_path': screenshot_path,
            'all_visible': all(r.get('visible') for r in results.values())
        }


async def main():
    print("="*70)
    print("DEFENSE GAUNTLET UI VERIFICATION")
    print("="*70)

    results = await verify_defense_modal()

    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    if results['all_visible']:
        print("✅ All required defense meter elements are VISIBLE")
    else:
        print("❌ Some elements are missing or hidden")

    print(f"\n📸 Screenshot saved to: {results['screenshot_path']}")

    print("\n" + "="*70)


if __name__ == '__main__':
    asyncio.run(main())
