# Contributing to GradQuest @ Yale

Thank you for your interest in contributing to **GradQuest @ Yale**! 🎓

---

## 🏛️ Architecture Overview

GradQuest @ Yale is a **pure client-side static game** contained primarily within:
- `docs/index.html`: The authoritative single-file engine, rendering, state management, and event system.
- `tests/browser_tests.js`: Headless browser test suite verifying gameplay balance and regression invariants.
- `data/`: Historical/experimental rulesets and auxiliary playtest references.

There is **no server or Python runtime backend** for the game. Any state change must respect the core engineering standards:
- Always use `this.updateState(changes, owner)` for state mutations.
- Maintain canonical state fields (`state.items.paper`, `state.confPaperCount`, `state.fundingMonths`, `teaching_load`, max stress 100).
- Preserve save compatibility using `localStorage['gradquest_save']`.

---

## 🛠️ Development & Testing

```bash
# 1. Syntax check test suites
node --check tests/browser_tests.js

# 2. Run Playwright browser integration tests
python3 run_tests.py

# 3. Check git hygiene before committing
git diff --check
```

---

## 📝 Commit Convention

We follow [Conventional Commits](https://conventionalcommits.org/):

```
feat(game): add new advisor event
fix(defense): resolve skepticism multiplier edge case
docs(readme): update gameplay instructions
test(storage): add save continuity regression assertion
```
