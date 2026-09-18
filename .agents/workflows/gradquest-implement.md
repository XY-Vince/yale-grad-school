# GradQuest Implement

Description: Safely implement a gameplay, UI, migration, or test-harness change.

## Steps

1. Inspect `git status --short` and identify unrelated user changes.
2. Read the relevant code in `docs/index.html`, plus `tests/browser_tests.js`
   when behavior needs coverage.
3. Check `AGENTS.md` for canonical field names and architecture rules.
4. Make the smallest scoped change that satisfies the request.
5. If persistent state changes, update `migrateSave()` and add/adjust a browser
   test.
6. If gameplay availability changes, verify Critical Path Mode interactions.
7. Run:
   - `python3 run_tests.py`
   - `git diff --check`
   - `python3 -m compileall -q <changed-python-files>` if Python changed
8. Summarize changed files, verification results, and residual risk.

