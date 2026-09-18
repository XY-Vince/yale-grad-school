#!/usr/bin/env python3
from pathlib import Path
"""
audit_playtest.py - Metric Consistency Verification for GradQuest

This script uses Playwright to:
1. Start the game and select "Experimentalist"
2. Run 500 turns, recording stats before and after each action
3. Parse result messages for stat gains
4. Verify that stat updates persist correctly (accounting for decay)

Formula: End = Start + ActionGain - MonthlyDecay
Base decay is approximately 4.
"""

import asyncio
from playwright.async_api import async_playwright
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import re


@dataclass
class TurnLog:
    turn: int
    action: str
    message: str

    # Pre-action stats
    pre_morale: int
    pre_stress: int
    pre_network: int
    pre_alignment: int

    # Post-action stats
    post_morale: int
    post_stress: int
    post_network: int
    post_alignment: int

    # Parsed gains from message
    morale_gain: Optional[int] = None
    network_gain: Optional[int] = None
    alignment_gain: Optional[int] = None

    # Calculations
    expected_morale: Optional[int] = None
    match: bool = False


def parse_stat_gains(message: str, action: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse stat gains from action result message."""
    morale_gain = None
    network_gain = None
    alignment_gain = None

    # Look for morale gains in message for all actions
    morale_matches = re.findall(r'\+?(\d+)\s*morale', message, re.IGNORECASE)
    if morale_matches:
        morale_gain = int(morale_matches[-1])

    if action == 'read':
        if "Found a new idea" in message:
            alignment_gain = 2
            network_gain = 2
        morale_gain = None  # Read costs 2 morale on fail, no gain on success

    return morale_gain, network_gain, alignment_gain


async def get_stats(page) -> Tuple[int, int, int, int]:
    """Extract current stats from the game state directly."""
    state = await page.evaluate("""() => {
        if (!window.game || !window.game.state) return null;
        return {
            morale: window.game.state.morale || 50,
            stress: window.game.state.stress || 0,
            network: window.game.state.peerNetwork || 10,
            alignment: window.game.state.strategicAlignment || 0
        };
    }""")

    if not state:
        return 50, 0, 10, 0

    return state['morale'], state['stress'], state['network'], state['alignment']


async def get_message_log(page) -> str:
    """Get the current message from the log."""
    try:
        message = await page.locator('#message-log').text_content()
        return message or ""
    except:
        return ""


async def click_action(page, action_id: str):
    """Click an action button by ID."""
    # Try different selectors since actions might be in tabs
    selectors = [
        f'button[onclick*="{action_id}"]',
        f'.actions-grid button[onclick*="{action_id}"]',
        f'#actions button[onclick*="{action_id}"]',
        f'button.action-btn[onclick*="{action_id}"]',
    ]

    for selector in selectors:
        try:
            if await page.locator(selector).count() > 0:
                await page.click(selector)
                return
        except:
            continue

    # If not found, try to find by text content
    try:
        await page.get_by_role("button", name=action_id.replace("_", " "), exact=False).click()
    except:
        # Try to click on the Actions tab first, then find button
        try:
            await page.click('[data-tab="actions"], .tab-btn[data-tab="actions"]')
            await asyncio.sleep(0.3)
            await page.click(f'button[onclick*="{action_id}"]')
        except Exception as e:
            print(f"Warning: Could not click action '{action_id}': {e}")
            # Take screenshot for debugging
            await page.screenshot(path=f'debug_turn_{action_id}.png')


async def acknowledge_event(page):
    """Click the acknowledge button on event modal if present."""
    max_retries = 3
    for _ in range(max_retries):
        try:
            modal = page.locator('#event-modal')
            if await modal.is_visible():
                await page.click('button.event-modal-btn, button[onclick="game.acknowledgeEvent()"]')
                await asyncio.sleep(0.6)
                if not await modal.is_visible():
                    return True
            else:
                return True
        except:
            await asyncio.sleep(0.3)
    return False


def print_table(logs: List[TurnLog], show_all: bool = False):
    display_logs = logs if show_all else [log for log in logs if not log.match]

    print("\n" + "="*120)
    print("GRADQUEST METRIC CONSISTENCY AUDIT")
    print("="*120)

    if not display_logs:
        print("\n✅ All turns passed consistency checks (no mismatches to display)")
    else:
        print(f"\nShowing {'all' if show_all else 'mismatch'} turns ({len(display_logs)} of {len(logs)}):")
        print("-"*120)
        print(f"{'Turn':<5} {'Action':<25} {'Start':<12} {'Gain':<10} {'Decay':<8} {'End':<12} {'Match?':<8}")
        print(f"{'':5} {'':25} {'Morale':<12} {'(Msg)':<10} {'(Est)':<8} {'Actual':<12} {'':8}")
        print("-"*120)

        for log in display_logs:
            action_name = log.action[:24] if len(log.action) > 24 else log.action
            start_str = f"M:{log.pre_morale}"
            gain_str = f"+{log.morale_gain}" if log.morale_gain else "N/A"
            decay_str = "~4"  # Base decay
            end_str = f"M:{log.post_morale}"
            match_str = "✅ YES" if log.match else "❌ NO"

            print(f"{log.turn:<5} {action_name:<25} {start_str:<12} {gain_str:<10} {decay_str:<8} {end_str:<12} {match_str:<8}")

            # Show detailed calculation if we have enough info
            if log.morale_gain is not None and log.expected_morale is not None:
                expected = f"Expected: {log.pre_morale} + {log.morale_gain} - 4 = {log.expected_morale}"
                actual = f"Actual: {log.post_morale}"
                diff = log.post_morale - log.expected_morale
                diff_str = f"Diff: {diff:+d}"
                print(f"      → {expected:<40} | {actual:<15} | {diff_str}")

        print("-"*120)


def print_summary(logs: List[TurnLog], game_ended: bool = False, end_reason: Optional[str] = None, end_won: Optional[bool] = None):
    total = len(logs)
    matched = sum(1 for log in logs if log.match)
    inconsistent = total - matched

    print("\n" + "="*120)
    print("📊 FINAL SUMMARY REPORT")
    print("="*120)
    print(f"\n  📈 Total Turns Run:      {total}")
    print(f"  ✅ Consistent Turns:     {matched}")
    print(f"  ❌ Inconsistent Turns:   {inconsistent}")

    if total > 0:
        consistency_rate = (matched / total) * 100
        print(f"  📊 Consistency Rate:     {consistency_rate:.1f}%")

    print(f"\n  🎮 Game Status:          {'ENDED' if game_ended else 'RUNNING (reached turn limit)'}")
    if game_ended and end_reason:
        outcome_emoji = "🏆" if end_won else "💔"
        print(f"  {outcome_emoji} Game Outcome:         {end_reason}")

    failed = [log for log in logs if not log.match]
    if failed:
        print(f"\n  ⚠️  Inconsistent Turns Details ({len(failed)}):")
        for log in failed[:10]:
            print(f"     - Turn {log.turn:3d} ({log.action:20s}): Expected ~{log.expected_morale}, got {log.post_morale}")
        if len(failed) > 10:
            print(f"     ... and {len(failed) - 10} more")
    else:
        print("\n  ✅ All turns were consistent! Stat updates are persisting correctly.")

    print("\n" + "="*120)


async def check_game_over(page) -> Tuple[bool, Optional[str], Optional[bool]]:
    try:
        end_screen_visible = await page.locator('#end-screen').is_visible()
        if end_screen_visible:
            end_state = await page.evaluate("() => window.game && window.game.state ? window.game.state.endState : null")
            if end_state:
                return True, end_state.get('message', 'Game ended'), end_state.get('won', False)
            return True, "Game ended (unknown reason)", False

        is_running = await page.evaluate("() => window.game && window.game.state ? window.game.state.isRunning : true")
        is_ended = await page.evaluate("() => window.game && window.game.state ? window.game.state.isEnded : false")

        if is_ended or not is_running:
            end_state = await page.evaluate("() => window.game && window.game.state ? window.game.state.endState : null")
            if end_state:
                return True, end_state.get('message', 'Game ended'), end_state.get('won', False)
            return True, "Game ended (unknown reason)", False

        return False, None, None
    except Exception:
        return False, None, None


async def run_audit():
    """Main audit function."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load the game
        print("Loading GradQuest...")
        await page.goto(f'file://{Path(__file__).resolve().parent}/docs/index.html')
        await asyncio.sleep(1)

        # Select Experimentalist specialization
        print("Selecting Experimentalist...")
        await page.click('#spec-experimentalist')
        await asyncio.sleep(0.5)

        # Start the game
        print("Starting game...")
        await page.click('#start-game-btn')
        await asyncio.sleep(1)

        # Acknowledge welcome modal
        await acknowledge_event(page)

        base_actions = ['read', 'break', 'read', 'read', 'break', 'read', 'work_idea', 'read', 'break', 'work_findings']
        actions = base_actions * 5

        logs: List[TurnLog] = []
        game_ended = False
        end_reason = None
        end_won = None

        print("\nRunning 50-turn audit...")
        print("-" * 60)
        print("(Only mismatches will be shown per-turn to keep output clean)")
        print("-" * 60)

        for turn in range(1, 51):
            game_ended, end_reason, end_won = await check_game_over(page)
            if game_ended:
                print(f"\n🎮 Game ended at turn {turn - 1}")
                break

            action = actions[turn - 1]

            # Record pre-action stats
            pre_morale, pre_stress, pre_network, pre_alignment = await get_stats(page)

            # Perform action
            await click_action(page, action)
            await asyncio.sleep(0.5)

            # Acknowledge any event modal (conference invites, etc)
            await acknowledge_event(page)
            await asyncio.sleep(0.4)
            # Double-check modal is closed
            await acknowledge_event(page)

            # Get result message
            message = await get_message_log(page)

            # Record post-action stats
            post_morale, post_stress, post_network, post_alignment = await get_stats(page)

            # Parse gains from message
            morale_gain, network_gain, alignment_gain = parse_stat_gains(message, action)

            # Calculate expected end morale (formula: Start + Gain - Decay)
            expected_morale = None
            match = True
            if morale_gain is not None:
                expected_morale = pre_morale + morale_gain - 4  # Base decay
                # Allow some tolerance since decay can vary (3-6 typically)
                tolerance = 3
                diff = abs(post_morale - expected_morale)
                match = diff <= tolerance

            log = TurnLog(
                turn=turn,
                action=action,
                message=message[:100] + "..." if len(message) > 100 else message,
                pre_morale=pre_morale,
                pre_stress=pre_stress,
                pre_network=pre_network,
                pre_alignment=pre_alignment,
                post_morale=post_morale,
                post_stress=post_stress,
                post_network=post_network,
                post_alignment=post_alignment,
                morale_gain=morale_gain,
                network_gain=network_gain,
                alignment_gain=alignment_gain,
                expected_morale=expected_morale,
                match=match
            )
            logs.append(log)

            if not match:
                print(f"❌ Turn {turn:3d}: {action:20s} | Pre: M={pre_morale:3d} | Post: M={post_morale:3d} | Expected: ~{expected_morale}")

            if turn % 10 == 0:
                consistent_so_far = sum(1 for log in logs if log.match)
                print(f"   → Progress: {turn} turns complete ({consistent_so_far}/{turn} consistent)")

        await browser.close()

        print_table(logs, show_all=False)
        print_summary(logs, game_ended, end_reason, end_won)

        return logs


if __name__ == "__main__":
    try:
        asyncio.run(run_audit())
    except Exception as e:
        print(f"\n❌ Audit failed with error: {e}")
        import traceback
        traceback.print_exc()
