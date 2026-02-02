## 📝 Description

Brief description of what this PR changes and why.

**Example:** "Adds new 'Conference Networking' action that allows players to build network at conferences. Addresses balance issue where network was too hard to gain in early game."

## 🔄 Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] ⚡ Performance improvement
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🎨 UI/UX improvements
- [ ] 📚 Documentation update
- [ ] 🧪 Test additions or improvements
- [ ] 🔧 Configuration/CI changes
- [ ] ⚠️ Breaking change (fix or feature that would cause existing functionality to not work as expected)

## 🎮 Game Changes (if applicable)

### New/Modified Actions
| Action | Category | Cost | Effect |
|--------|----------|------|--------|
| [Action Name] | [research/admin/mental_health] | [resources] | [outcome] |

### New/Modified Events
- [ ] Event IDs: `EventName1`, `EventName2`
- [ ] Triggers: [e.g., MonthBegin, ActionComplete]
- [ ] Balance impact: [describe any balance changes]

### UI Changes
- [ ] New components added
- [ ] Visual changes (describe)
- [ ] Mobile responsive checked

### Balance Impact
- [ ] Completion time affected: [faster/slower/unchanged]
- [ ] Difficulty curve: [easier/harder/unchanged]
- [ ] Recovery mechanisms: [improved/worsened/unchanged]

## 🧪 Testing

- [ ] Unit tests added/updated (`pytest tests/`)
- [ ] Integration tests pass
- [ ] Manual testing performed
- [ ] Tested in Chrome
- [ ] Tested in Firefox
- [ ] Tested on mobile (if UI changes)
- [ ] Console errors checked (F12)
- [ ] Game loop stable at 60FPS (if applicable)

### Test Scenarios

Describe what you tested:
1. [e.g., Started new game, completed 3 papers, defended thesis]
2. [e.g., Tested recovery action triggers at low morale]
3. [e.g., Verified conference actions appear correctly]

## 📊 Telemetry (if balance changes)

If this PR affects game balance, include telemetry:

```
Test runs: 50
Median completion: XX months (target: 60-75)
Inspiration frequency: X.X per run (target: <4)
Failure rate: X% (target: reasonable challenge)
```

## ✅ Checklist

### Code Quality
- [ ] Code follows project style guidelines (see `docs/rules.md`)
- [ ] Type hints added for all public functions
- [ ] Self-documenting actions include `category`, `cost`, `desc`
- [ ] No `eval()` used - ExpressionParser for safe evaluation
- [ ] PlayerState mutations use named transitions (not inline)
- [ ] Deterministic RNG from `state.rng` with log tokens

### Data & Schema
- [ ] YAML validates against JSON Schema
- [ ] Ruleset version incremented if needed
- [ ] Default initializers added for new state fields
- [ ] Actions have at least 3 variant phrases for variety

### Architecture
- [ ] UI reads from UIState transformer (not raw engine state)
- [ ] GameState changes logically immutable
- [ ] Recovery mechanisms provided for any new penalties
- [ ] "Slog" check passed (no infinite death spirals)

### Documentation
- [ ] `AGENTS.md` updated if new patterns introduced
- [ ] `.cursorrules` updated if coding standards changed
- [ ] Code comments added for complex logic
- [ ] CHANGELOG.md updated

## 🚀 Deployment Notes

- [ ] Database migration needed: [Yes/No]
- [ ] Save game compatibility: [Forward compatible/Breaking]
- [ ] Performance impact: [None/Low/High]
- [ ] Requires server restart: [Yes/No]

## 🔗 Related Issues

- Fixes #XXX (issue number)
- Related to #XXX
- Addresses feature request: [link]

## 📸 Screenshots (if UI changes)

Add before/after screenshots or GIFs showing the changes.

## 🎯 Reviewer Notes

**Specific areas to review:**
- [ ] Balance numbers feel right?
- [ ] Code follows immutability pattern?
- [ ] Recovery mechanisms adequate?
- [ ] Tests cover edge cases?

---

## 🎓 GradQuest Standards Reminder

> "Every punishment must unlock a new form of agency."

- [ ] Every penalty has a recovery action
- [ ] Every mechanic avoids "infinite death spirals"
- [ ] Every action provides player agency
- [ ] No negative event without counterplay

---

*Thank you for contributing to GradQuest! 🎓*
