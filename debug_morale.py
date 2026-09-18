from pathlib import Path
"""
Debug script to track morale changes turn by turn using Playwright.
Uses direct DOM access instead of game object.
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_morale():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()

        print("=" * 100)
        print("Loading game from docs/index.html")
        print("=" * 100)
        await page.goto(f'file://{Path(__file__).resolve().parent}/docs/index.html')

        # Wait for page to load
        await asyncio.sleep(2)

        # Start game - select specialization and click start
        print("\nStarting game...")
        try:
            await page.click("#spec-computational")
            await asyncio.sleep(0.5)
            await page.click("#start-game-btn")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Note: {e}")

        # Wait for game screen to be visible
        try:
            await page.wait_for_selector("#game-screen", timeout=5000)
            await asyncio.sleep(1)
        except:
            pass

        # Function to get game state from DOM
        async def get_game_state():
            return await page.evaluate("""() => {
                const moraleBar = document.getElementById('morale-bar');
                const moraleStatus = document.getElementById('morale-status');
                const stressState = document.getElementById('stress-state');
                const advisorStatus = document.getElementById('advisor-status');
                const totalMonthsEl = document.getElementById('total-months');
                const messageLog = document.getElementById('message-log');
                const buffsEl = document.getElementById('active-buffs');
                const statusesEl = document.getElementById('statuses');

                // Extract morale and stress from game state
                let morale = 50;
                let stress = 0;
                if (window.game && window.game.state) {
                    morale = window.game.state.morale || 50;
                    stress = window.game.state.stress || 0;
                }

                // Parse advisor
                let advisor = 50;
                if (advisorStatus) {
                    const text = advisorStatus.textContent;
                    if (text.includes('Happy')) advisor = 60;
                    else if (text.includes('Unhappy')) advisor = 20;
                    else if (text.includes('Furious')) advisor = 10;
                }

                // Total months
                let totalMonths = 1;
                if (totalMonthsEl) {
                    totalMonths = parseInt(totalMonthsEl.textContent) || 1;
                }

                // Get active buffs
                let buffs = '—';
                if (buffsEl && buffsEl.textContent.trim()) {
                    buffs = buffsEl.textContent.trim();
                }

                // Get statuses (badge list)
                let statuses = [];
                if (statusesEl) {
                    const badges = statusesEl.querySelectorAll('.status-badge, .item-badge');
                    badges.forEach(b => statuses.push(b.textContent.trim()));
                }

                return {
                    morale: morale,
                    stress: stress,
                    advisor: advisor,
                    totalMonths: totalMonths,
                    lastEvent: messageLog ? messageLog.textContent.trim() : '',
                    buffs: buffs,
                    statuses: statuses
                };
            }""")

        # Function to check if button exists and is enabled
        async def can_click_action(action_id):
            result = await page.evaluate(f"""() => {{
                const btn = document.querySelector(`button[onclick*="{action_id}"]`);
                if (!btn) return false;
                return !btn.classList.contains('disabled');
            }}""")
            return result

        # Print header
        print(f"\n{'Turn':<6} | {'Morale':<8} | {'Stress':<8} | {'Change':<10} | {'Action':<20} | {'Statuses':<30} | {'Event'}")
        print("-" * 130)

        prev_morale = 50

        # Run for up to 20 turns
        for turn in range(1, 21):
            try:
                # Get state before action
                state = await get_game_state()
                morale = state['morale']
                stress = state['stress']
                event = state['lastEvent']

                # Determine action
                action_id = 'advance'
                action_name = 'Next Month'

                if morale < 30:
                    if await can_click_action('break'):
                        action_id = 'break'
                        action_name = 'Take a Break'
                elif await can_click_action('read'):
                    action_id = 'read'
                    action_name = 'Read Papers'
                elif await can_click_action('work_idea'):
                    action_id = 'work_idea'
                    action_name = 'Work on Idea'

                # Click the action button
                try:
                    await page.evaluate(f"""() => {{
                        const btn = document.querySelector(`button[onclick*="{action_id}"]`);
                        if (btn) btn.click();
                    }}""")
                except:
                    # Try advance button with exact onclick
                    await page.evaluate("""() => {
                        const btns = document.querySelectorAll('button');
                        for (const btn of btns) {
                            if (btn.textContent.includes('Next Month')) {
                                btn.click();
                                break;
                            }
                        }
                    }""")

                # Wait for update
                await asyncio.sleep(1.5)

                # Check for modal and dismiss
                try:
                    modal_visible = await page.evaluate("""() => {
                        const modal = document.getElementById('event-modal');
                        return modal && modal.style.display !== 'none';
                    }""")
                    if modal_visible:
                        await page.evaluate("""() => {
                            const btn = document.querySelector('.event-modal-btn');
                            if (btn) btn.click();
                        }""")
                        await asyncio.sleep(0.5)
                except:
                    pass

                # Get new state
                new_state = await get_game_state()
                new_morale = new_state['morale']
                new_event = new_state['lastEvent']

                # Calculate change
                change = new_morale - morale

                # Format event for display
                if len(new_event) > 60:
                    new_event = new_event[:60] + "..."

                # Format statuses
                status_str = ', '.join(new_state['statuses'])
                if not status_str:
                    status_str = '—'

                # Print turn info
                print(f"{turn:<6} | {new_morale:<8} | {stress:<8} | {change:+<10} | {action_name:<20} | {status_str:<30} | {new_event[:50]}")

                # Check game over
                if new_morale <= 0:
                    print("\nGame Over: Morale reached 0!")
                    break

                prev_morale = new_morale

            except Exception as e:
                print(f"\nError on turn {turn}: {e}")
                import traceback
                traceback.print_exc()
                break

        print("=" * 100)
        print("Debug session complete")

        # Keep window open
        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_morale())
