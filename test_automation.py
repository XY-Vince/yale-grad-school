#!/usr/bin/env python3
"""Quick test of GradQuest automation"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1280, 'height': 800})
        
        print("Loading game...")
        await page.goto('file:///Users/guozhenghui/Desktop/WXY/ComBio/GradQuest/docs/index.html')
        
        print("Waiting for start screen...")
        await page.wait_for_selector('#start-screen', timeout=10000)
        print("✓ Start screen found")
        
        title = await page.title()
        print(f"Page title: {title}")
        
        # Check if start button exists
        start_btn = await page.query_selector('#start-game-btn')
        if start_btn:
            disabled = await start_btn.get_attribute('disabled')
            print(f"Start button found, disabled: {disabled}")
        
        # Select specialization
        print("Selecting specialization...")
        await page.click('#spec-experimentalist')
        await page.wait_for_timeout(500)
        
        # Check if button is now enabled
        start_btn = await page.query_selector('#start-game-btn')
        disabled = await start_btn.get_attribute('disabled')
        print(f"After selection - Start button disabled: {disabled}")
        
        # Try to start
        print("Starting game...")
        await page.click('#start-game-btn')
        await page.wait_for_timeout(2000)
        
        # Check game screen
        game_screen = await page.query_selector('#game-screen')
        if game_screen:
            is_visible = await game_screen.is_visible()
            print(f"Game screen visible: {is_visible}")
        
        # Get initial state
        state = await page.evaluate('''() => {
            return {
                date: document.getElementById('date')?.textContent,
                morale: document.getElementById('morale-bar')?.style?.width,
                papers: document.getElementById('papers')?.textContent,
                months: document.getElementById('total-months')?.textContent,
                actions: document.querySelectorAll('#actions .action-btn').length
            };
        }''')
        print(f"Initial state: {state}")
        
        # Try clicking an action
        print("\nTrying to click 'Read Papers'...")
        read_btn = await page.query_selector('button:has-text("Read Papers")')
        if read_btn:
            print("Found Read Papers button")
            await read_btn.click()
            await page.wait_for_timeout(1000)
            
            # Check message log
            msg = await page.text_content('#message-log')
            print(f"Message after action: {msg[:200]}")
        else:
            print("Read Papers button not found")
            # List all buttons
            buttons = await page.query_selector_all('button')
            print(f"\nFound {len(buttons)} buttons:")
            for i, btn in enumerate(buttons[:10]):
                text = await btn.text_content()
                print(f"  {i}: {text[:50]}")
        
        await browser.close()
        print("\n✓ Test complete")

asyncio.run(test())
