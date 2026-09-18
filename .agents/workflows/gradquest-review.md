# GradQuest Review

Description: Review current changes for regressions, stale claims, and missing tests.

## Steps

1. Inspect `git status --short` and `git diff --stat`.
2. Review diffs in this order:
   - `docs/index.html`
   - `tests/browser_tests.js`
   - `run_tests.py`
   - changed Python helper scripts
   - docs
3. Prioritize findings that can break shipped gameplay, saves, browser tests,
   or agent workflows.
4. Check for stale references to retired paths such as `docs/tests.html`.
5. Run or request approval for:
   - `python3 run_tests.py`
   - `git diff --check`
   - compile checks for changed Python
6. Report findings first, ordered by severity with file and line references.
7. If no blocking issues remain, state that clearly and mention any test gaps.

