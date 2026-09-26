# (Yale) Grad School Workspace Hub — Agent Guide

This is the canonical project briefing for coding agents operating within the
**(Yale) Grad School Workspace Hub** (`yale-grad-school`).

---

## 1. Workspace Structure & Subproject Authority

The workspace operates as a two-tier hub:

- **Hub Level (`yale-grad-school`)**: Centralized workspace for Yale doctoral affairs, research tools, and simulations. Governed by this root `AGENTS.md`.
- **Game Subproject (`GradQuest @ Yale`)**: Browser-only PhD life simulator located in `docs/`.
  - Authoritative source of truth: `docs/index.html`.
  - Game baseline: `GAME_VERSION = '2.59.2'`.
  - Storage key: `localStorage['gradquest_save']`.
  - Auxiliary data: `data/` houses historical/experimental rulesets and playtest logs, not active runtime game logic.
- **Autonomous Research Skills**: Located in `.agents/skills/`. Each skill is governed by its local `SKILL.md` contract.

---

## 2. Confidentiality & Public/Private Boundaries (FERPA)

Because this repository may be publicly accessible or published via GitHub Pages:

- **FERPA Compliance**: Never commit student-identifiable educational records, grading sheets, course evaluations, or student communications.
- **Academic Privacy**: Never commit private advisor/committee correspondence, degree progress audits containing private PII, unreleased research manuscripts, or credentials (API keys, PAT tokens).
- **Physical Separation**: Confidential documents must reside in dedicated private repositories or institutional drives outside this workspace. Never rely solely on `.gitignore` for sensitive materials.

---

## 3. GradQuest Canonical State Invariants

Use these exact names when touching gameplay or save migration logic:

- Journal papers: `state.items.paper`.
- Conference papers: `state.confPaperCount`.
- Funding: `state.fundingMonths`.
- Teaching load status: `teaching_load`.
- Stress: numeric `state.stress`, capped by `GAME_CONSTANTS.MAX_STRESS = 100`.
- Save version: `GAME_VERSION`.
- Runtime statuses are a `Set`; saved statuses are arrays and must be rehydrated on load.
- LocalStorage key: `gradquest_save` (retained without rename to avoid introducing key migration paths).

Legacy names such as `state.papers`, `state.funding`, `teachingLoad`, and
stress values above 100 must be handled only through `migrateSave()`.

---

## 4. Architectural Rules for GradQuest

- Keep the game static and client-side in `docs/index.html`. Avoid adding build tooling.
- Treat `docs/index.html` as the source of truth for shipped gameplay.
- Keep changes scoped. Do not refactor unrelated systems while fixing one issue.
- Use `updateState(changes, owner)` for player/game state mutations.
- Preserve save compatibility with `gradquest_save`.
- `GRADUATION_CONTRACT` is the authoritative defense eligibility contract.
  `evaluateDefenseCriteria()` may add labels, skepticism, and UI breakdowns,
  but must not create separate eligibility paths.
- The active endgame is the 3-turn Defense Gauntlet. Legacy `attemptDefense()`
  must not be routed into.
- Keep EventResolver modal discipline intact: major events are queued through
  `showMessage()` / `EventResolver`; silent log messages must remain silent.

---

## 5. Gameplay Design Rules

- Every punishment must unlock a recovery path. This is the Slog Check.
- Recovery actions are mechanical safety valves, not decorative flavor.
- Do not hide decisive failure causes. Important changes in funding, morale,
  stress, defense eligibility, review outcomes, and conference cooldowns must
  be visible in UI text or the event log.
- Critical Path Mode is currently enabled. When testing non-critical actions,
  disable it temporarily in the test and restore it afterward.

---

## 6. Verification Rules

Before calling a code change done, run the checks relevant to the files touched:

- Browser tests syntax: `node --check tests/browser_tests.js`.
- Browser integration: `python3 run_tests.py`.
- Unit test suite: `python3 -m pytest tests/`.
- Python syntax for changed scripts:
  `python3 -m compileall -q <changed-python-files>`.
- Patch hygiene: `git diff --check`.
- Stale references: search for old paths, old version literals, and retired
  files when touching related code.
- Generated cache files (`__pycache__/`, `*.pyc`) must not be committed.

When Playwright fails only because the sandbox cannot launch Chromium, rerun the
same command with the required approval rather than weakening the test.

---

## 7. Engineering Rigor & Terminology Rules

For investigation, profiling, and benchmarking tasks (such as `.agents/skills/verify-public-person-profile/`):
- Refer to `.agents/rules/04-engineering-rigor-and-wording.md` for full term mappings.
- File permission restrictions (`chmod 0o000` under same UID) are "file permission access blocking", never "physical isolation".
- Avoid hyperbole ("彻底根治", "彻底解决", "100% 解决"). Use empirical phrasing: "tests pass", "not reproduced in current regression suite".
- Once implementation is completed, update plans to "实施记录" in past tense.
- Cite exact code fields (`mention_key`, `raw_payload_sha256`); do not use phantom fields (`url_sha256`).
- Qualify statistical bounds to the synthetic benchmark and binomial assumptions; do not extrapolate to open-web guarantees.
