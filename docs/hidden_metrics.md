# GradQuest Hidden Metrics

## Core Hidden Stats

| Metric | Range | Default | Description |
|--------|-------|---------|-------------|
| **`stress`** | 0-100 | 0 | Mental strain. High stress (≥80) blocks thesis progress, triggers crisis events |
| **`fundingMonths`** | 0+ | 36 | Research funding. Burns 0.5/month. Conferences cost funding. At 0 → teaching load |
| **`strategicAlignment`** | 0-100 | 0 | Reputation/advisor alignment. Affects talk success, reviews, defense |
| **`peerNetwork`** | 0-100 | 10 | Peer connections. Helps collaborations, defense, can bypass review delays |
| **`advisorScore`** | 0-100 | 50 | Advisor relationship. Affects interventions, defense skepticism |

---

## Advisor Hidden State

| Metric | Description |
|--------|-------------|
| `advisor.tension` | Hidden tension from aggressive actions. Builds over time |
| `advisor.riskTolerance` | 30-70. Advisor personality trait |
| `advisor.attentionSpan` | 30-70. How often advisor checks in |
| `advisor.strictness` | 30-70. Punishment severity |
| `advisorInterventions` | Count of vacation suggestions. 3+ = patience exhausted |
| `vacationOffered` | Flag: advisor has suggested time off |

---

## Dissertation State (Hidden)

| Metric | Effect |
|--------|--------|
| `dissertation.draft_quality` | Improves from writing. Affects review RNG |
| `dissertation.revision_load` | Slows progress after 75% complete |
| `dissertation.committee_friction` | Increases defense failure chance |

---

## Defense Hidden State

| Metric | Affects |
|--------|---------|
| `defenseState.thesis_quality` | From figures, polish, papers |
| `defenseState.presentation_skill` | From practice, teaching, network |
| `defenseState.committee_support` | From alignment, advisor, past interactions |

---

## Academic Progress (Partially Hidden)

| Metric | Description |
|--------|-------------|
| `qualifyLevel` | 0-5. Quals prep level. Need 3 to pass. Shown in quals messages but no permanent UI |
| `credits` | Coursework credits. Need 30 for MS-Out |
| `thesisProgress` | 0-100. **SHOWN** in graduation panel |

---

## Social/Collaboration

| Metric | Description |
|--------|-------------|
| `socialDebt` | +10 per collaboration use, decays -10/6mo. Increases future collab cost |
| `lastCollabMonth` | For social debt decay tracking |
| `collaborationOffered` | Flag from networking events |

---

## Timing/Cooldown (Hidden)

| Metric | Purpose |
|--------|---------|
| `lastVacationMonth` | Vacation cooldown tracking |
| `vacationsThisYear` | Annual vacation limit |
| `lastScoopMonth` | 6-month scoop cooldown |
| `lastConferenceMonth` | Conference cooldown |
| `conferencesThisYear` | 2/year limit |
| `inspirationsThisYear` | Cap at 2/year |

---

## Buffs/Effects (Hidden Timers)

| Metric | Effect |
|--------|--------|
| `freshPerspectiveUntil` | +research success until this month |
| `renewedPerspectiveUntil` | +10% develop findings success |
| `equipmentStabilizedUntil` | Equipment won't break |
| `peerReviewShieldActive` | Paper protected from harsh reviews |

---

## What's Currently Visible in UI

- **Morale** (main stat bar)
- **Thesis Progress** (graduation panel bar)
- **Papers Published** (graduation panel)
- **Year/Month** (header)
- **Inventory** (ideas, findings, figures, discoveries)
- **Event Log** (scrollable history)

---

## Recommendation: Metrics to Surface

### High Priority (player frustration when hidden)
1. **Stress** - Players don't know why thesis progress is blocked
2. **Funding Months** - Critical resource, only warned at 12/6/0
3. **Quals Prep Level** - Only shown in warning messages

### Medium Priority (nice to know)
4. **Network** - Affects many systems
5. **Alignment/Reputation** - Affects talks and reviews

### Low Priority (intentionally mysterious)
6. Advisor tension
7. Committee friction
8. Social debt
