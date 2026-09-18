# GradQuest Always-On Rules

Activation: Always On

Use this rule for all GradQuest tasks.

## Read This First

Treat `../../AGENTS.md` as the canonical agent briefing for this repository.
Older project documents may be useful history, but they can be stale.

## Source of Truth

- Shipped app: `docs/index.html`.
- Browser tests: `tests/browser_tests.js`.
- Test command: `python3 run_tests.py`.
- Current baseline: `GAME_VERSION = '2.59.2'`.

Do not rely on old claims from `docs/AGENTS.md`, `.cursorrules`, or the V3.0
upgrade plan without checking current code.

## Non-Negotiables

- Keep the app static and browser-only.
- Preserve save compatibility through `migrateSave()`.
- Use canonical state names:
  - `items.paper`
  - `confPaperCount`
  - `fundingMonths`
  - `teaching_load`
  - `stress` capped at `100`
- Keep `GRADUATION_CONTRACT` authoritative for defense eligibility.
- Keep the 3-turn Defense Gauntlet as the active endgame.
- Do not recreate `docs/tests.html`; the test harness now injects
  `tests/browser_tests.js` into the shipped page.
- Never commit generated Python caches.

## Instruction Sentinel

The token `汪` in older agent docs is a deliberate instruction-following
sentinel. Do not turn it into public-facing game copy, README text, or UI text.

