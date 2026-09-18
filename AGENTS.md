# GradQuest Agent Guide

This is the canonical project briefing for coding agents. Older guidance in
`docs/AGENTS.md`, `.cursorrules`, and roadmap documents may be stale; verify
against the shipped code before relying on those files.

## Current Project State

- Product: GradQuest, a browser-only PhD life simulator.
- Shipped app: `docs/index.html`.
- Current baseline: `GAME_VERSION = '2.59.2'`.
- Test runner: `python3 run_tests.py`.
- Browser tests: `tests/browser_tests.js`, injected into the shipped
  `docs/index.html`.
- Public test fixture `docs/tests.html` has been retired; do not recreate it
  unless the user explicitly asks.

## Canonical State Fields

Use these names when changing gameplay or migration code:

- Journal papers: `state.items.paper`.
- Conference papers: `state.confPaperCount`.
- Funding: `state.fundingMonths`.
- Teaching load status: `teaching_load`.
- Stress: numeric `state.stress`, capped by `GAME_CONSTANTS.MAX_STRESS = 100`.
- Save version: `GAME_VERSION`.
- Runtime statuses are a `Set`; saved statuses are arrays and must be
  rehydrated on load.

Legacy names such as `state.papers`, `state.funding`, `teachingLoad`, and
stress values above 100 must be handled only through `migrateSave()`.

## Architectural Rules

- Keep the game static and client-side. Avoid adding build tooling unless the
  user explicitly requests it.
- Treat `docs/index.html` as the source of truth for shipped gameplay.
- Keep changes scoped. This project has accumulated stale docs and historical
  plans; do not refactor unrelated systems while fixing one issue.
- Use `updateState(changes, owner)` for player/game state mutations unless
  touching legacy code that cannot safely be changed in the current task.
- Preserve save compatibility. Any field rename or state-shape change needs a
  migration case and a browser test.
- `GRADUATION_CONTRACT` is the authoritative defense eligibility contract.
  `evaluateDefenseCriteria()` may add labels, skepticism, and UI breakdowns,
  but must not create separate eligibility paths.
- The active endgame is the 3-turn Defense Gauntlet. Legacy `attemptDefense()`
  may exist historically, but shipped flows must not route through it.
- Keep EventResolver modal discipline intact: major events are queued through
  `showMessage()` / `EventResolver`; silent log messages must remain silent.

## Gameplay Design Rules

- Every punishment must unlock a recovery path. This is the Slog Check.
- Recovery actions are not flavor; they are mechanical safety valves.
- Do not hide decisive failure causes. Important changes in funding, morale,
  stress, defense eligibility, review outcomes, and conference cooldowns must
  be visible in UI text or the event log.
- Critical Path Mode is currently enabled. When testing non-critical actions,
  disable it temporarily in the test and restore it afterward.
- The instruction sentinel `汪` in older docs is an internal compliance check,
  not player-facing copy and not public documentation.

## Verification Rules

Before calling a code change done, run the checks relevant to the files touched:

- Browser integration: `python3 run_tests.py`.
- Python syntax for changed scripts:
  `python3 -m compileall -q <changed-python-files>`.
- Patch hygiene: `git diff --check`.
- Stale references: search for old paths, old version literals, and retired
  files when touching related code.
- Generated cache files (`__pycache__/`, `*.pyc`) must not be committed.

When Playwright fails only because the sandbox cannot launch Chromium, rerun the
same command with the required approval rather than weakening the test.

## Engineering Rigor & Terminology Rules

For investigation, profiling, and benchmarking tasks (such as `.agents/skills/verify-public-person-profile/`):
- Refer to `.agents/rules/04-engineering-rigor-and-wording.md` for full term mappings.
- File permission restrictions (`chmod 0o000` under same UID) are "file permission access blocking", never "physical isolation".
- Avoid hyperbole ("彻底根治", "彻底解决", "100% 解决"). Use empirical phrasing: "tests pass", "not reproduced in current regression suite".
- Once implementation is completed, update plans to "实施记录" in past tense.
- Cite exact code fields (`mention_key`, `raw_payload_sha256`); do not use phantom fields (`url_sha256`).
- Qualify statistical bounds to the synthetic benchmark and binomial assumptions; do not extrapolate to open-web guarantees.

