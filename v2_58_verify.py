#!/usr/bin/env python3
from pathlib import Path
"""Quick V2.58 balance verification - runs 3 fast playtests"""
import asyncio
import json
from playwright.async_api import async_playwright

async def quick_test():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for run in range(1, 4):
            page = await browser.new_page(viewport={'width': 1280, 'height': 800})

            await page.goto(f'file://{Path(__file__).resolve().parent}/docs/index.html')
            await page.wait_for_selector('#start-screen', timeout=10000)

            version = await page.text_content('#version-display') or "Unknown"
            print(f"Run {run}: Game version = {version.strip()}")

            specs = ['experimentalist', 'theoretician', 'computational']
            await page.click(f'#spec-{specs[run % 3]}')
            await page.wait_for_timeout(500)
            await page.click('#start-game-btn')
            await page.wait_for_timeout(1000)

            ending = "Unknown"
            months = 0
            papers = 0
            lowest_morale = 100
            stuck_counter = 0
            prev_month = 1
            no_action_count = 0

            for turn in range(150):
                end_screen = await page.query_selector('#end-screen')
                if end_screen and await end_screen.is_visible():
                    title = await page.text_content('#end-title') or ""
                    ending = title.strip()
                    break

                state = await page.evaluate('''() => {
                    const b = document.getElementById('morale-bar');
                    const gameScreen = document.getElementById('game-screen');
                    return {
                        morale: b ? (parseInt(b.style.width) || 50) : 50,
                        papers: parseInt(document.getElementById('papers')?.textContent || '0'),
                        months: parseInt(document.getElementById('total-months')?.textContent || '1'),
                        gameScreenVisible: gameScreen ? gameScreen.style.display !== 'none' : false,
                        gameScreenExists: !!gameScreen,
                    };
                }''')

                months = state['months']
                papers = state['papers']
                if state['morale'] < lowest_morale:
                    lowest_morale = state['morale']

                if months == prev_month:
                    stuck_counter += 1
                    if stuck_counter > 5:
                        debug_info = await page.evaluate('''() => {
                            const eventModal = document.getElementById('event-modal');
                            const eventModalOverlay = document.querySelector('.event-modal-overlay');
                            const thesisModal = document.getElementById('thesis-modal');
                            const defenseModal = document.getElementById('defense-modal');
                            const actionsDiv = document.getElementById('actions');
                            const actionButtons = actionsDiv ? actionsDiv.querySelectorAll('.action-btn') : [];
                            return {
                                eventModal_visible: eventModal ? eventModal.style.display : 'not found',
                                eventModalOverlay_visible: eventModalOverlay ? eventModalOverlay.style.display : 'not found',
                                thesisModal_visible: thesisModal ? thesisModal.classList.contains('active') : 'not found',
                                defenseModal_visible: defenseModal ? defenseModal.classList.contains('active') : 'not found',
                                actionButtons_count: actionButtons.length,
                                actionButtons: Array.from(actionButtons).slice(0, 3).map(b => b.textContent.trim()),
                            };
                        }''')
                        print(f"  DEBUG (turn {turn}): Stuck at month {months}")
                        print(f"    Modals: {debug_info}")
                        ending = f"Stuck at Month {months}"
                        break
                else:
                    stuck_counter = 0
                    prev_month = months

                action_result = await page.evaluate('''() => {
                    const eventModal = document.getElementById('event-modal');
                    if (eventModal && eventModal.style.display !== 'none') {
                        const btn = eventModal.querySelector('.event-modal-btn');
                        if (btn) { btn.click(); return 'event-modal'; }
                    }

                    const thesisModal = document.getElementById('thesis-modal');
                    if (thesisModal && thesisModal.classList.contains('active')) {
                        const btn = thesisModal.querySelector('.modal-btn.primary');
                        if (btn) { btn.click(); return 'thesis-modal'; }
                    }

                    const defenseModal = document.getElementById('defense-modal');
                    if (defenseModal && defenseModal.classList.contains('active')) {
                        const action = defenseModal.querySelector('.defense-action-btn:not(.disabled)');
                        if (action) { action.click(); return 'defense-action'; }
                        const resultBtn = defenseModal.querySelector('.defense-result .modal-btn');
                        if (resultBtn) { resultBtn.click(); return 'defense-continue'; }
                    }

                    const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                    const msg = document.getElementById('message-log')?.textContent || '';

                    const morale = parseInt(document.getElementById('morale-bar')?.style.width || '50');
                    if (morale < 25) {
                        for (const b of btns) {
                            if (b.textContent.includes('Break') || b.textContent.includes('Time Of')) {
                                b.click();
                                return 'morale-action';
                            }
                        }
                    }

                    if (msg.includes('QUALS') && (msg.includes('2 MONTHS') || msg.includes('NEXT MONTH'))) {
                        for (const b of btns) {
                            if (b.textContent.includes('Study for Quals')) {
                                b.click();
                                return 'quals-action';
                            }
                        }
                    }

                    const priorities = ['Defend Thesis', 'Write Thesis', 'Write Dissertation',
                                      'Draft Paper', 'Make Figures', 'Validate Discovery',
                                      'Develop Findings', 'Work on Idea', 'Read Papers'];
                    for (const p of priorities) {
                        for (const b of btns) {
                            if (b.textContent.includes(p)) {
                                b.click();
                                return 'pipeline-action';
                            }
                        }
                    }

                    if (btns.length > 0) {
                        btns[0].click();
                        return 'fallback';
                    }
                    return 'no-action';
                }''')

                if turn < 10 or (turn % 10 == 0):
                    print(f"  Turn {turn}: {action_result} (month={months}, morale={state['morale']})")

                await page.wait_for_timeout(800)

            if ending == "Unknown":
                ending = "Timeout (150 turns)"

            results.append({
                'run': run,
                'ending': ending,
                'months': months,
                'papers': papers,
                'lowest_morale': lowest_morale
            })

            print(f"  Result: {ending} | {months}mo | {papers} papers | lowest morale: {lowest_morale}")
            await page.close()

        await browser.close()

    print("\n" + "="*60)
    print("V2.58 BALANCE VERIFICATION SUMMARY")
    print("="*60)

    phd_wins = sum(1 for r in results if 'PhD' in r['ending'] or 'Doctorate' in r['ending'])
    dropouts = sum(1 for r in results if 'Drop' in r['ending'] or 'drop' in r['ending'].lower())
    avg_months = sum(r['months'] for r in results) / len(results)
    max_papers = max(r['papers'] for r in results)

    print(f"\nRuns completed: {len(results)}")
    print(f"PhD wins: {phd_wins}/{len(results)} ({phd_wins/len(results)*100:.0f}%)")
    print(f"Dropouts: {dropouts}/{len(results)} ({dropouts/len(results)*100:.0f}%)")
    print(f"Average duration: {avg_months:.1f} months")
    print(f"Max papers published: {max_papers}")

    if phd_wins > 0:
        print("\n✅ SUCCESS: At least one PhD completion!")
        print("   V2.58 balance fixes are working.")
    elif avg_months > 40:
        print("\n⚠️  IMPROVED: Average duration increased significantly")
        print("   Players surviving longer, but not yet winning.")
    else:
        print("\n⚠️  NEEDS MORE WORK: Still dropping out early")
        print("   Consider further balance adjustments.")

    print("\n" + "="*60)

    with open('v2_58_verification.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Results saved to v2_58_verification.json")

if __name__ == "__main__":
    asyncio.run(quick_test())
