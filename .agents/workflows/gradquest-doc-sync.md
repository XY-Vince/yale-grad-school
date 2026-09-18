# GradQuest Doc Sync

Description: Reconcile public and internal docs with the shipped game.

## Steps

1. Treat `docs/index.html`, `AGENTS.md`, and `tests/browser_tests.js` as the
   starting truth.
2. Check version references against `GAME_VERSION`.
3. Update public docs only with shipped, playable mechanics.
4. Mark aspirational or planned systems explicitly as planned.
5. Remove or rewrite stale references to:
   - `docs/tests.html`
   - `state.papers`
   - `state.funding`
   - `teachingLoad`
   - stress caps above 100
   - one-shot defense as the shipped endgame
6. Preserve the instruction sentinel only in internal agent docs.
7. Run `git diff --check` and report files changed.

