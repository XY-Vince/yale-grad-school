from pathlib import Path
"""
Focused debug to track what happens with exhaustion and morale recovery.
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_exhaustion():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        page = await browser.new_page()

        print("Loading game...")
        await page.goto(f'file://{Path(__file__).resolve().parent}/docs/index.html')
        await asyncio.sleep(2)

        # Start game
        await page.click("#spec-computational")
        await asyncio.sleep(0.5)
        await page.click("#start-game-btn")
        await asyncio.sleep(1)

        # Wait for game screen
        await page.wait_for_selector("#game-screen", timeout=5000)
        await asyncio.sleep(1)

        # Get morale from game state directly
        async def get_morale():
            return await page.evaluate("""() => {
                const status = document.getElementById('morale-status');
                const statuses = document.getElementById('statuses');
                let morale = window.game && window.game.state ? window.game.state.morale : 50;

                let statusList = [];
                if (statuses) {
                    statuses.querySelectorAll('.status-badge, .item-badge').forEach(b => {
                        statusList.push(b.textContent.trim());
                    });
                }
                return {
                    morale: morale,
                    status: status ? status.textContent : '',
                    statuses: statusList
                };
            }""")

        print(f"\n{'Turn':<6} | {'Morale':<8} | {'Status':<30}")
        print("-" * 50)

        # Run until morale is low, then take break
        for turn in range(1, 25):
            state = await get_morale()
            morale = state['morale']

            if turn == 1:
                print(f"{turn:<6} | {morale:<8} | {state['status']:<30} | Initial state")

            # Action: read papers until morale is low, then break
            if morale < 25:
                print(f"{turn:<6} | {morale:<8} | {state['status']:<30} | Taking a Break...")
                # Click break button
                await page.evaluate("""() => {
                    const btn = document.querySelector("button[onclick*='break']");
                    if (btn) btn.click();
                }""")
            else:
                print(f"{turn:<6} | {morale:<8} | {state['status']:<30} | Reading Papers...")
                # Click read button
                await page.evaluate("""() => {
                    const btn = document.querySelector("button[onclick*='read']");
                    if (btn) btn.click();
                }""")

            # Wait for update
            await asyncio.sleep(1.5)

            # Dismiss modal if present
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

                    # Check state after modal
                    state = await get_morale()
                    print(f"{turn:<6} | {state['morale']:<8} | {state['status']:<30} | After event!")

            except Exception as e:
                print(f"Error: {e}")
                break

            # Check game over
            new_state = await get_morale()
            if new_state['morale'] <= 0:
                print(f"\nGame Over at turn {turn}!")
                break

        print("\nFinal State Check:")
        final = await get_morale()
        print(f"Morale: {final['morale']}")
        print(f"Status: {final['status']}")
        print(f"Statuses: {final['statuses']}")

        await asyncio.sleep(3)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_exhaustion())
