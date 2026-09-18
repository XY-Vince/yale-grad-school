# GradQuest Verification Rules

Activation: Always On

Use this rule before reporting completion.

## Required Checks

Run these after meaningful code changes:

1. `python3 run_tests.py`
2. `git diff --check`
3. `python3 -m compileall -q <changed-python-files>` when Python changed
4. `git status --short`

If Playwright cannot launch Chromium in a sandbox, request approval and rerun
the same `python3 run_tests.py` command outside the sandbox.

## Review Checklist

- Does the change touch the shipped game (`docs/index.html`) rather than only a
  stale fixture or doc?
- If state shape changed, does `migrateSave()` cover old saves?
- If defense eligibility changed, do tests cover Gold Standard, Hybrid, and
  locked/incomplete cases?
- If conference logic changed, do tests cover manual actions and auto-invite
  cooldowns?
- If a test passes because an action is absent, is that absence explicitly
  asserted?
- Are stale references updated when a file is moved or deleted?
- Are generated files absent from the commit?

## Completion Standard

Do not claim completion if tests are skipped, if browser console errors are
newly introduced, or if `git diff --check` fails. Report any known residual
risk plainly.

