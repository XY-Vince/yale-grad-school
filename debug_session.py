#!/usr/bin/env python3
"""Quick debug session to inspect game state"""
import asyncio
from playwright.async_api import async_playwright

async def debug_session():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})

        print("Navigating to game...")
        await page.goto('file:///Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/docs/index.html')
        await page.wait_for_selector('#start-screen', timeout=10000)

        version = await page.text_content('#version-display')
        print(f"Game version: {(version or '').strip()}")

        print("\nClicking experimentalist spec...")
        await page.click('#spec-experimentalist')
        await page.wait_for_timeout(500)
        await page.click('#start-game-btn')
        await page.wait_for_timeout(1000)

        print("\nStarting game session...")
        print("="*60)

        for turn in range(15):
            end_screen = await page.query_selector('#end-screen')
            if end_screen and await end_screen.is_visible():
                title = await page.text_content('#end-title')
                print(f"\nGAME ENDED: {(title or '').strip()}")
                break

            state = await page.evaluate('''() => {
                const b = document.getElementById('morale-bar');
                const eventModal = document.getElementById('event-modal');
                const messageEl = document.getElementById('message-log');
                return {
                    morale: b ? (parseInt(b.style.width) || 50) : 50,
                    months: parseInt(document.getElementById('total-months')?.textContent || '1'),
                    eventModalVisible: eventModal ? eventModal.style.display !== 'none' : false,
                    message: messageEl ? messageEl.textContent.trim() : '',
                    waitingForAck: window.game ? window.game.waitingForAcknowledge : false
                };
            }''')

            print(f"\nTurn {turn+1}: Month={state['months']}, Morale={state['morale']}")
            print(f"  Event modal: {state['eventModalVisible']}, Waiting: {state['waitingForAck']}")
            print(f"  Message: {state['message'][:80] if state['message'] else 'None'}...")

            if state['eventModalVisible']:
                print("  -> Clicking acknowledge button...")
                await page.click('.event-modal-btn')
                await page.wait_for_timeout(500)
            else:
                action_result = await page.evaluate('''() => {
                    const btns = document.querySelectorAll('#actions .action-btn:not(.disabled)');
                    if (btns.length > 0) {
                        btns[0].click();
                        return btns[0].textContent.trim();
                    }
                    return 'no-action';
                }''')
                print(f"  -> Action: {action_result}")
                await page.wait_for_timeout(1000)

        print("\n" + "="*60)
        print("Final state:")
        final_state = await page.evaluate('''() => {
            return {
                morale: parseInt(document.getElementById('morale-bar').style.width || '50'),
                months: parseInt(document.getElementById('total-months').textContent),
                papers: parseInt(document.getElementById('papers').textContent || '0'),
                endScreenVisible: document.getElementById('end-screen').style.display !== 'none'
            };
        }''')
        print(f"  Morale: {final_state['morale']}")
        print(f"  Months: {final_state['months']}")
        print(f"  Papers: {final_state['papers']}")
        print(f"  End screen visible: {final_state['endScreenVisible']}")

        await page.screenshot(path='debug_screenshot.png', full_page=True)
        print("\nScreenshot saved to debug_screenshot.png")

        print("\nPress Enter to close browser...")
        input()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_session())
