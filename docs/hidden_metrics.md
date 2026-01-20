# GradQuest Hidden Metrics (V2.54 Update)

## Now Visible in UI ✅

| Metric | UI Display | Thresholds |
|--------|------------|------------|
| **Stress** | 😌 Normal / ⚠️ High / 🔥 Critical | 0-49 / 50-79 / 80+ |
| **Funding** | ✅ Stable / ⚠️ Tight / 🚨 Critical | >12mo / 7-12mo / ≤6mo |
| **Network** | Raw number (0-100) | Always visible |
| **Quals Prep** | X/3 (until passed) | Shows when quals approaching |
| **Alignment** | Raw number (after quals) | Replaces quals prep |

---

## Still Hidden Metrics

### Core Stats (Medium Priority to Surface)

| Metric | Range | Effect |
|--------|-------|--------|
| `advisorScore` | 0-100, default 50 | Defense skepticism, interventions |
| `strategicAlignment` | 0-100, default 0 | Talk success, reviews, defense |

### Advisor Hidden State

| Metric | Effect |
|--------|--------|
| `advisor.tension` | Builds from aggressive actions |
| `advisor.riskTolerance` | 30-70, personality trait |
| `advisorInterventions` | Count of vacation suggestions |

### Dissertation State

| Metric | Effect |
|--------|--------|
| `dissertation.draft_quality` | Affects review RNG |
| `dissertation.revision_load` | Slows progress >75% |
| `dissertation.committee_friction` | Defense failure chance |

### Defense Hidden State

| Metric | Affects |
|--------|---------|
| `defenseState.thesis_quality` | From figures, papers |
| `defenseState.presentation_skill` | From teaching, network |
| `defenseState.committee_support` | From alignment, advisor |

### Social/Collaboration

| Metric | Effect |
|--------|--------|
| `socialDebt` | +10 per collab, decays -10/6mo |
| `collaborationOffered` | Flag from networking |

### Timing/Cooldowns

| Metric | Purpose |
|--------|---------|
| `lastVacationMonth` | Vacation cooldown |
| `lastScoopMonth` | 6-month scoop cooldown |
| `lastConferenceMonth` | Conference cooldown |
| `conferencesThisYear` | 2/year limit |

### Buffs/Effects (Hidden Timers)

| Metric | Effect |
|--------|--------|
| `freshPerspectiveUntil` | +research success |
| `renewedPerspectiveUntil` | +10% develop findings |
| `equipmentStabilizedUntil` | Equipment protected |
| `peerReviewShieldActive` | Paper protected |

---

## Recommended Next Steps

### Already Done ✅
- Stress state indicator
- Funding state indicator

### Next Priority
1. **Quals prep** → clearer progress narrative (not just warnings)
2. **Advisor relationship** → long-term vs short-term signals
3. **Network spend** → tag which actions consume vs scale with network
