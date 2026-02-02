# Changelog

All notable changes to GradQuest are documented here.

## [2.56.0] - 2026-02-01 "V3.0 Upgrade - Phase 0.2"

**Theme**: Regression test suite for V3.0 upgrade quality assurance.

### 🧪 Regression Test Suite
Six critical regression tests added to ensure system stability:

1. **Defense Gating Enforced**: Validates defense unlock only with complete requirements (3 papers, 100% thesis, quals passed)
2. **One Modal Per Tick**: Ensures maximum 1 modal shown per game tick to prevent UI spam
3. **No Empty Month Logs**: Blocks empty or whitespace-only log entries from appearing
4. **Conference No Overlap**: Prevents duplicate conference registrations and same-month overlaps
5. **Single Primary Stat Mutation**: Verifies actions affect ≤2 primary stats (maintainable design)
6. **Defense State Cleanup**: Ensures defense state properly cleaned up after completion without affecting other stats

### 🔧 Implementation
- **Test Location**: `docs/tests.html`
- **New Button**: "Run Regression Tests" (orange) in test suite UI
- **Test Framework**: JavaScript-based assertions with pass/fail reporting
- **Integration**: Tests run independently or as part of full test suite

### 📋 V3.0 Upgrade Plan Phase 0.2
- Quality assurance foundation for Phase 1 (Defense Gauntlet)
- Validates core game mechanics before narrative endings implementation
- Automated regression detection for future development

---

## [2.56.0] - 2026-02-01 "V3.0 Upgrade - Phase 0.1"

**Theme**: Graduation Contract system for centralized defense eligibility logic.

### 🎓 Graduation Contract System
- **Centralized Logic**: New `GRADUATION_CONTRACT` object consolidates all defense eligibility checks.
- **Replaces Scattered Checks**: Single source of truth for defense unlock conditions.
- **Functions**:
  - `defenseUnlocked(state)`: Checks if thesis complete, portfolio eligible, and quals passed.
  - `isPortfolioEligible(state)`: Validates paper requirements (3 journal OR 2 journal + 2 conference).
  - `getDefenseDebugInfo(state)`: Returns debug object with all graduation requirements status.

### 🔧 Architecture Improvements
- **Debug Integration**: Graduation contract info available in game state for development.
- **V3.0 Preparation**: Foundation for Phase 1 Defense Gauntlet and future narrative endings.

---

## [2.55.0] - 2026-01-20 "Transparency Phase 1"

**Theme**: No more invisible timers. Buffs and social states are now legible.

### ✨ Active Buffs Display
- **Visual Timers**: Shows remaining months for buffs in the stats panel.
- **Supported Buffs**:
  - `✨ Fresh Perspective`: From international conferences.
  - `🔄 Renewed Perspective`: From advisor-mandated vacations.
  - `🛡️ Peer Shield`: From network spend.

### 🤝 Advisor Tension Indicator
- **Surfaced State**: Replaces hidden number with 3-tier status.
- **States**:
  - 😊 **Good** (0-29): Safe zone.
  - 😐 **Tense** (30-59): Warning zone.
  - 😠 **Strained** (60+): Danger of intervention/ultimatum.

---

## [2.54.0] - 2026-01-19 "Hidden Metrics Surfaced"

**Theme**: Critical failure states (stress blockade, funding collapse) are now visible *before* they kill your run.

### 😤 Stress & Funding Indicators
- **Stress State**: 
  - 😌 **Normal** (<50)
  - ⚠️ **High** (50-79) - Blocks complex actions.
  - 🔥 **Critical** (80+) - Triggers crisis events.
- **Funding State**:
  - ✅ **Stable** (>12mo)
  - ⚠️ **Tight** (7-12mo)
  - 🚨 **Critical** (≤6mo) - Danger of Teaching Load.

### ⚖️ Research Balance
- **Read Papers**: Increased idea rate (40% → 45%).
- **Develop Findings**: Increased success rate (35% → 45%).
- Reduced early-game grind frustration.

---

## [2.53.0] - 2026-01-19 "Meaningful Choices"

**Theme**: Every choice has a distinct identity (Safety vs. Risk vs. Future).

### 🎪 Conference Actions Rebalance
- **🖼️ Poster**: **SAFE**. Guaranteed progress, -20 stress. No downside.
- **🎤 Talk**: **GAMBLE**. High reward (Reputation) or Penalty (Stress/Align).
- **🤝 Network**: **FUTURE**. Low immediate payout, unlocks Collabs/Grants.

### 📝 Review Replies Rebalance
- **📝 Polite**: **RELATIONSHIP**. Slow (+2mo), high accept chance, +Alignment.
- **⚔️ Aggressive**: **SPEED/RISK**. Immediate result, risk of backlash/tension.
- **⏳ Delay**: **PROTECTION**. No penalty, reduces stress, waits for better RNG.

---

## [2.52.0] - 2026-01-19 "State Ownership"

**Theme**: Architectural hygiene. Established single sources of truth.

### 🔧 Logic Audit
- **Thesis Progress**: Consolidated to `state.thesisProgress`. UI is now a passive observer.
- **Defense Fix**: Prevented defense modal from re-triggering post-completion.

---

## [2.51.0] - 2026-01-18 "Advisor Personality Engine"

**Theme**: Advisors are systems, not just flavor text.

### 🧠 Personality Engine
- Centralized advisor state in `state.advisor`.
- Behaviors driven by `riskTolerance`, `patience`, and `tension` variables.
- Removed global variable pollution.

---

## [2.45.0] - 2026-01-14 "Critical Path"

**Theme**: Helping players find the signal in the noise.

### 🎯 Critical Path Mode
- **Focused View**: Toggles to show only essential progression actions.
- **Context Aware**: Hides specialized/side actions when main goal is blocked.
- Great for new players or mid-game stagnation.

---

## [2.40.0] - 2026-01-12 "Defense Gauntlet"

**Theme**: The final boss fight.

### 🛡️ Interactive Defense
- **Real-time Battle**: Interaction loop instead of single click.
- **Skepticism Meter**: Committee resistance fluctuates based on answers.
- **Outcomes**: Distinction / Pass / Revision / Fail based on performance.

---

## [2.38.0] - 2026-01-10 "Stats Evolution"

**Theme**: UI that evolves with your career stage.

### 📊 Adaptive Stats Panel
- **Quals Prep**: Shows during years 1-2.
- **Alignment**: Replaces Quals Prep once exam is passed.
- **Full-Width Events**: History log expanded for better readability.

---

## [2.37.0] - 2026-01-09 "Focus & Modals"

**Theme**: Modernizing the UI flow.

### 🖼️ Centered Modal System
- Replaced browser alerts with custom DOM modals.
- Clean, non-blocking notification flow.
- Removed redundant "Acknowledge" buttons for smoother clicking.

---

## [2.36.0] - 2026-01-09 "Tab Content Panels"

**Theme**: Proper show/hide tab panels so users don't miss info.

### 📊 Status Tab
- Stats bar (date, morale, advisor, publications, network, alignment)
- Event messages ("What Happened" + "Previously")
- Default tab on mobile

### 🎯 Actions Tab
- Action buttons grid only
- Focused gameplay view

### 🔬 Lab Tab  
- Research Pipeline (Ideas → Findings → Discovery → Figures)
- Status Effects
- Graduation Progress (papers, thesis, defense status)
- Save/Load/Help buttons

### ⚙️ Tab Switching
- switchTab() now shows/hides content panels
- Desktop: all content visible (no tabs needed)

---

## [2.35.0] - 2026-01-08 "Tab Navigation"

**Theme**: Mobile app-shell pattern with bottom tab navigation.

### 📱 Tab Navigation Bar
- **4 tabs**: 🎯 Actions | 📊 Progress | 🔬 Lab | ⏩ Next
- Fixed to bottom on mobile (≤768px)
- Smooth scroll to relevant section on tap
- Hidden on desktop (full layout visible)

### 🎨 Tab Styling
- Active tab highlighted with accent color
- "Next" tab has gradient background (primary action)
- Touch feedback with scale animation

---

## [2.34.0] - 2026-01-08 "Mobile UX Optimization"

**Theme**: Thumb-zone ergonomics and breathing room for mobile players.

### 📱 Sticky Bottom Action Bar
- **Save + Advance Month** buttons fixed to bottom
- Visible only on mobile (≤768px)
- Thumb-zone placement for one-handed play

### 👆 Larger Tap Targets
- Minimum 48px button height on mobile
- Touch active states (`scale(0.97)`)

### 📊 Horizontal Stats Scroll
- Stats bar now scrolls horizontally on mobile
- Prevents vertical content crush

### 🎯 Single-Column Actions (≤480px)
- Full-width action buttons on narrow screens
- Improved readability

### 📐 Layout Refinements
- Compact header (16px padding vs 30px)
- Body bottom padding for sticky bar
- Modal fullscreen on mobile

---

## [2.33.0] - 2026-01-08 "Momentum Without Power Creep"

**Theme**: Early game feels sticky without becoming trivial — skills pay off within months, not years.

### 📚 Curriculum System
Tiered courses that spend credits for permanent skills:

| Tier | Year | Cost | Examples |
|------|------|------|----------|
| Foundation | 1+ | 5 cr | Statistics, Lab Safety, Writing |
| Advanced | 2+ | 10 cr | Grant Writing, Peer Review |
| Capstone | 3+ | 15 cr | Thesis Bootcamp |

### 📋 Workshop Papers
Early dopamine with soft cap:
- **Max 2/year** (diminished returns after)
- **+8 morale, +5 network** on success
- **+5% journal boost** per workshop (stacks!)
- Teaches publication cadence

### ✨ Skills System
`SKILLS_CATALOG` with additive stacking:
- `analysisSpeed` — faster data work
- `paperAcceptance` — better publication odds
- `grantSuccess` — funding applications
- `thesisSpeed` — late-game acceleration
- `equipmentFailure` — reduced lab incidents

### 💡 "Why Not?" Tooltips
`getWhyNot(actionId)` explains action blockers:
- ❌ Missing: Ideas (use Read Papers)
- ❌ Missing: Figures (use Develop Findings)
- ✅ All requirements met

---

## [2.32.0] - 2026-01-08 "Sustainability & Clarity"

**Theme**: Hidden numbers become visible metrics — rivals are legible, thesis efficiency is explicit.

### ⚔️ Rival Progress Visibility
`getRivalProgressInfo()` exposes:

| Field | Value |
|-------|-------|
| progress | 0-100% |
| scoopRisk | Low/Medium/High/IMMINENT |
| isWarning | true when 80%+ warning shown |
| resentment | Coordination tension level |

### 📋 Thesis Roadmap
`getThesisRoadmap()` provides:
- **Phase 1 (0-24%)**: Literature Review — Build foundation
- **Phase 2 (25-74%)**: Data Synthesis — Requires 1+ paper
- **Phase 3 (75-99%)**: Defense Prep — Requires 2+ papers
- **Phase 4 (100%)**: Ready to Defend

**Efficiency Display**: Hover thesis progress to see:
- Base progress per action
- Paper bonus
- Alignment bonus
- Pipeline bonus (computational)

### 😊 Advisor Mood Tooltip
`getAdvisorMoodTooltip()` explains:
- Current mood (Furious → Pleased)
- Tension level
- Alignment level
- Months since last meeting

### 💾 Save Toast Notification
- Replaced intrusive `alert()` with smooth toast
- Appears bottom-right for 2.5 seconds
- Animated slide-in/fade-out

---

## [2.31.0] - 2026-01-08 "Pressure With Telegraphs"

**Theme**: Every punishment is now visible, delayable, or tradeable — pressure becomes strategy.

### ⚔️ Rival Scoop Limits
Scoops are no longer random spam:

| Constraint | Effect |
|------------|--------|
| 12-month cooldown | Max 1 scoop per year |
| 80% warning | "🚨 Rival is rushing a preprint!" |
| 90%+ required | Scoop needs high progress AND stress |
| Thesis immunity | Progress decays during defense phase |

### 📋 Pre-register Idea
New counterplay action:
- **Cost**: -5 morale
- **Effect**: Blocks next scoop attempt
- **Duration**: 12 months or until used
- **Bonus**: +10% paper acceptance

### 🤝 Coordinate with Rival
Strategic collaboration:
- **Cost**: -20 network
- **Effect**: -30% rival progress
- **Risk**: Builds resentment (caps at 50)
- **Warning**: High resentment blocks future coordination

### 🆘 Emergency Grant
Escape teaching load (one-time):
- **Cost**: -10 morale
- **Success (50%)**: +12 funding months, remove teaching load
- **Failure**: +3 funding months, grant draft reusable for 6 months

### 🔧 Rival State Tracking
- `lastScoopMonth` - enforces cooldown
- `warnedAt80` - prevents warning spam
- `resentment` - tracks coordination tension

---

## [2.30.0] - 2026-01-08 "Thesis Dashboard"

**Theme**: Thesis becomes a mode, not a meter — late-game focus with computational parity.

### 📘 Thesis Stages with System Effects
Each thesis phase modifies gameplay:

| Stage | Speed Bonus | Actions Blocked |
|-------|------------|-----------------|
| 📋 Planning | — | None |
| 📝 Outline Approved | +20% thesis | None |
| 📖 Draft Complete | — | Conferences |
| 🎓 Ready to Defend | — | Research, Conferences |

### 🧠 Thesis Mode System
- `isThesisModeActive()` - detects late-game (25%+ thesis, quals passed)
- `getThesisModeText()` - banner: "📘 THESIS MODE: [Stage]"
- `shouldHideAction()` - hides distracting actions by stage

### 💻 Computational Parity
**Optimize Pipeline** action for computational specialization:
- One-time investment: -10 morale
- Permanent: +50% analysis speed, +50% thesis speed
- `getComputationalBonus()` returns 1.5× when optimized
- Tooltip: "💻 Optimized Pipeline: +50% analysis speed"

### 🎭 Advisor Context Hints
`getAdvisorContextHint()` provides archetype-specific guidance:
- **Thesis Mode**: Different advice per advisor
- **Teaching Load**: Different sympathy levels

### 📋 Engine Functions
- `THESIS_STAGES` constant with effects
- `getThesisStageEffects()` - returns current stage modifiers
- `isPipelineOptimized()` - checks computational buff
- `getComputationalBonusText()` - tooltip text

---

## [2.29.0] - 2026-01-08 "Academic Survival"

**Theme**: Waiting becomes decision-making under pressure — funding suffocates, reviews demand responses.

### 📊 Centralized Modifier System
All status effects now use a central resolver:

| Modifier | Teaching Load | Fresh Perspective | Exhaustion |
|----------|---------------|-------------------|------------|
| Research Speed | ×0.5 | ×1.2 | ×0.8 |
| Thesis Speed | ×0.6 | — | ×0.8 |
| Stress Gain | +20% | -20% | +50% |

### 🔧 STATUS_EFFECTS Constant
- `getEffectiveResearchSpeed()` - central research modifier
- `getEffectiveThesisSpeed()` - central thesis modifier
- `getEffectiveStressGain()` - central stress modifier
- `getTeachingLoadPenaltyText()` - tooltip pollution

### 💰 Enhanced Funding Warnings
- **12 months**: Early warning, suggest networking
- **6 months**: Critical warning with urgency
- **0 months**: Teaching Load applied with full breakdown

### 📬 Interactive Peer Review
When reviewers respond, players must choose:
- **📝 Polite Revision**: +1 month, +25% acceptance, +3 alignment
- **⚔️ Aggressive Rebuttal**: -10 morale, +15% acceptance (advisor-sensitive!)
- **⏳ Delay Response**: +1 month delay, -10% acceptance (stacking)

### 🎭 Advisor-Sensitive Responses
- **Tormentor**: Approves aggressive rebuttals (+2 alignment)
- **Mentor**: Disapproves aggressive rebuttals (-5 alignment, +10 tension)
- **Ghost**: Neutral

### 📅 Integration
- `triggerReviewFeedback()` in advanceMonth()
- Review actions appear when feedback available
- Teaching Load penalty shown in tooltips

---

## [2.28.0] - 2026-01-08 "Conferences 2.0"

**Theme**: GradQuest stops being claustrophobic — conferences become strategic resets, funding becomes oxygen.

### 🎪 Tiered Conference System
Seasonal invitations with different costs and rewards:

| Tier | Cost | Network | Special |
|------|------|---------|---------|
| 📍 **Local Workshop** | 0 | +5 | Spring/Fall |
| 🏛️ **National Conference** | 2 | +15 | Spring/Summer |
| 🌍 **International Conference** | 4 | +30 | Summer only, +Fresh Perspective |

### 🎯 Conference Choices
Each conference offers 4 options:
- **🖼️ Poster Presentation**: Safe, +30% network, +5 morale
- **🎤 Give Talk**: Risky (60% success), full network gain or -10 morale
- **🍷 Networking Mixer**: Full network, +15 morale, -40 stress
- **❌ Skip Conference**: Save funding, lose opportunity

### 💰 Funding System
- Start with **36 funding months** (3 years)
- Burns **0.5 months** each month
- **Warning at 6 months** remaining
- **Funding exhausted = Teaching Load** (50% research slowdown)

### ✨ Fresh Perspective Buff
From international conferences only:
- **Duration**: 3 months
- **Effects**: Stress recovery, morale stability, idea generation boost

### 📅 Integration
- `spawnConferenceInvite()` in advanceMonth() (seasonal)
- `monthlyFundingTick()` handles funding decay and conference expiration
- Conference actions appear in action list when invited

---

## [2.27.0] - 2026-01-07 "The Living Lab"

**Theme**: GradQuest becomes a place, not a spreadsheet — labmates with agency, not flavor.

### 🧪 Labmate System
Two NPCs with their own progress, stress, loyalty, and events:

| Archetype | Role | Behavior |
|-----------|------|----------|
| 🎓 **The Senior** | Mentor figure | Leaves in 12-18 months, provides network |
| ⚔️ **The Rival** | Competitor | Publishes competitively, may sabotage |

### 📊 NPC Stats
Each labmate tracks hidden state:
- **progress** (0-100): Toward their next publication
- **stress** (0-100): Affects behavior
- **loyalty** (-50 to +50): Toward player
- **monthsRemaining**: Senior departure countdown

### ⚡ Forced Events
NPCs create unavoidable drama:
- **Rival Stress > 70**: Sabotage chance (scoop your idea, -10 morale)
- **Senior monthsRemaining = 3**: Departure warning
- **Senior leaves**: -15 network, -10 morale, thesis penalty if collaborated

### 📄 Publication Impact
- **Rival publishes**: -5 morale, +10 stress ("The pressure is on")
- **Senior publishes**: +5 morale, +5 network (lab reputation boost)

### 🤝 Collaboration System
- `collaborateWithLabmate()` action increases loyalty
- Senior collaborations give +3 alignment
- Dependency penalty if collaborator leaves

---

## [2.26.0] - 2026-01-07 "Advisor Personalities"

**Theme**: The humanization patch — advisors become systems with memory, not flavor text.

### 👹👻🧑‍🏫 Advisor Archetypes
Three distinct advisor types, assigned via field-weighted randomness:

| Archetype | Name | Philosophy | Field Bias |
|-----------|------|------------|------------|
| 👹 **The Tormentor** | Dr. Hardwick | "Results speak. Excuses don't." | Experimentalist |
| 👻 **The Ghost** | Dr. Phantom | "You'll figure it out." | Computational |
| 🧑‍🏫 **The Mentor** | Dr. Shepherd | "Slow progress is still progress." | Theoretician |

### 📊 Advisor Tension System
Hidden meter (0-100) that tracks advisor relationship:
- **Raises**: Actions the advisor dislikes
- **Lowers**: Actions the advisor approves
- **Warning** at 50: Archetype-specific concern message
- **Ultimatum** at 80: Serious consequences threat

### 🎭 Advisor-Owned Milestones
Key moments now have archetype-specific responses:
- **Quals Passed**: Tormentor → "That's the minimum." | Mentor → "I'm proud of you."
- **Paper Accepted**: Ghost → "Where next?" | Mentor → "Let's celebrate!"
- **Defense Ready**: Each archetype has unique framing

### 🔧 Implementation Details
- `ADVISOR_ARCHETYPES` constant with weights, triggers, modifiers
- `pickAdvisorByField()` - weighted random assignment
- `initializeAdvisor()` - creates advisor state with memory
- `updateAdvisorTension()` - called on every action
- `checkAdvisorEscalation()` - triggers warnings/ultimatums
- `getAdvisorMilestoneText()` - personalized milestone responses

---

## [2.25.0] - 2026-01-07 "Defense & Career Resolution"

**Theme**: The point of no return — thesis defense becomes real, career paths become earned.

### 🎓 Defense Readiness System
Derived stat from thesis%, papers, alignment, network:
- `getDefenseReadiness()` calculates readiness score
- Qualitative text display: "Your committee seems cautiously optimistic"
- Score determines defense outcome variance

### 🛡️ Thesis Defense (One-Shot Event)
Four possible outcomes:

| Outcome | Score | Effect |
|---------|-------|--------|
| **PASS_WITH_DISTINCTION** | 85+ | PhD with honors, +20 academia score |
| **PASS** | 70-84 | PhD earned, normal career resolution |
| **CONDITIONAL_PASS** | 60-69 | +2 months revisions, -15 morale |
| **FAIL** | <60 | +6 months wait, -30 morale, +10 friction |

### 📝 Write Dissertation Action (With Risk)
- **Cost**: 15 morale per session
- **Gain**: 6-10% base + papers×4 + alignment bonus - friction penalty
- **Risk**: 20% chance of revision request → +3 committee friction
- **Block**: Stalls if morale < 20 (increases friction)
- **Requires**: 1+ published papers, quals passed

### 💼 Career Resolution System
Multi-factor scoring: academia vs industry
- **Academia signals**: papers, alignment, network
- **Industry signals**: network, internships, industry exposure
- **Specialization bias**: Computational → industry, Theoretician → academia
- **Defense modifier**: Distinction → +20 academia, Conditional → -10 academia

### 🗺️ Career Paths

| Path | Type | Trigger |
|------|------|---------|
| 🏛️ **Tenure-Track Professor** | Academia | academia-industry ≥ 25 |
| 🔬 **Postdoctoral Researcher** | Academia | academia-industry ≥ 10 |
| 💼 **Industry Executive** | Industry | industry-academia ≥ 25 |
| 🧪 **Industry Scientist** | Industry | industry-academia ≥ 10 |
| 🚀 **Startup Founder** | Hybrid | Balanced scores |

### 📊 Player-Facing Explanation
- `getCareerExplanation()` generates "Why this path:" text
- Lists contributing factors: publications, alignment, network, defense outcome

---

## [2.24.0] - 2026-01-07 "Interactive Dissertation & Field Mastery"

**Theme**: Network as strategic currency, field-specific crisis mitigation — closing endgame design loopholes.

### 🤝 Peer Review Shield
- **Cost**: 20 Network (requires 60+ Network)
- **Effect**: Next figure validation **automatically succeeds**
- One-time use per activation
- "Your colleague's notes helped you nail the visualization"

### 🔬 Field-Specific Mitigation Actions
Each specialization now has a preventive action (costs 5 morale, 6-month protection):

| Field | Action | Effect |
|-------|--------|--------|
| 🔬 **Experimentalist** | Preventive Calibration | Equipment stabilized |
| 📐 **Theoretician** | Add Supporting Lemmas | Committee skepticism reduced |
| 💻 **Computational** | Pre-allocate Compute | Server stability guaranteed |

### 📝 Dissertation Internal State
Hidden variables affecting endgame:
- **draft_quality**: Affects review RNG
- **revision_load**: Slows progress after 75%
- **committee_friction**: Increases failure chance
- `getDissertationFlavorText()` for hidden state feedback

---

## [2.23.0] - 2026-01-07 "Thesis Phases & Dissertation"

**Theme**: The thesis is no longer a passive meter — it's a gated project with pressure, trade-offs, and momentum.

### 📑 Thesis Phase System
Four distinct phases that gate progression:

| Phase | Threshold | Effect |
|-------|-----------|--------|
| 📝 **PLANNING** | 0% | Default state, outline not approved |
| 📑 **OUTLINE_APPROVED** | 25% | +10 Alignment, faster thesis gains |
| 🧐 **DRAFT_REVIEW** | 75% | Committee reviewing, advisor_review status |
| 🎓 **DEFENSE_READY** | 100% + 3 papers | Can schedule thesis defense |

### 📄 Paper-Backed Thesis Caps
- Each journal paper = 25% thesis cap
- 0 papers → thesis capped at 0%
- 2 papers → thesis capped at 50%
- 4+ papers → full 100% unlocked

### 🤝 Network Synergy
- **Network ≥ 80**: Bypasses advisor review delay automatically
- Message: "Your strong peer network helped expedite the committee review!"

### 🎓 Graduation Panel Updates
- Shows current phase with emoji
- Shows "Next: [gate condition]" for clarity
- Phase transitions trigger milestone toasts

---

## [2.22.0] - 2026-01-06 "Information Clarity"

**Theme**: Trust repair — players should always know what just happened and how close they are to finishing.

### 🎓 Graduation Progress Card
New persistent UI panel showing:
- **Papers**: X / 3 with progress bar
- **Thesis**: X% with progress bar  
- **Defense Status**: Shows remaining requirements

### 📊 Categorical Probability Previews
Actions now show estimated outcomes:
- 🟢 **Likely** (70-85%)
- 🟡 **Uncertain** (45-70%)
- 🔴 **Risky** (≤45%)

### 📣 Priority Notification Levels
Events classified by severity:
- **BLOCKING**: Paper accepted, quals result, defense ready → Modal required
- **HIGH**: Burnout, exhaustion, scoop → Highlighted toast
- **LOW**: Morale changes → Log only

### State System
- `graduation` state object as single source of truth
- `syncGraduationState()` for derived value calculation
- `updateGraduationCard()` for UI sync

---

## [2.21.0] - 2026-01-06 "Support Systems"

**Theme**: Human survivability — interventions prevent death spirals without trivializing adversity.

### 📊 Stress Meter (0-100)
Replaces binary exhaustion:

| Level | Threshold | Effect |
|-------|-----------|--------|
| Normal | < 60 | No penalty |
| Stressed | 60-99 | Tooltip warnings |
| Exhausted | 100+ | −20% success, stacks |

### 🧑‍🏫 Advisor Intervention (Split)
- **Passive Shield** (Alignment ≥ 40): −25% morale penalties always active
- **Active Intervention** (Alignment ≥ 60, 12-month cooldown):
  - Clears exhaustion/burnout statuses
  - +15 morale, −40 stress
  - Triggers when morale < 20 or stress ≥ 100

### 🤝 Peer Intervention (Network Safety Net)
- **Trigger**: Network ≥ 60, morale < 30
- **Cooldown**: 6 months
- **Effect**: +10 morale, −30 stress
- Message: "Your labmates noticed you disappearing..."

### 📈 Morale Projection
- `calculateMoraleProjection()` forecasts next month's morale
- Shows current, projected, decay, and alignment buffer

### 🎓 Quals Grace
- `qualsGraceUsed` flag for first failure protection

---

## [2.20.0] - 2026-01-05 "Field Specialization"

**Theme**: Identity through choice — your research field shapes gameplay, not just flavor.

### 🔬 Three Specializations
Choose at game start:

| Field | Accelerator | Warning | Key Modifier |
|-------|-------------|---------|--------------|
| 🔬 **Experimentalist** | Protocol Reuse | Equipment-dependent | +equipment risk, better figures |
| 📐 **Theoretician** | Conceptual Breakthrough | Abstract results | Faster ideas, harder figures |
| 💻 **Computational** | Pipeline Automation | Server-dependent | Automated plot generation |

### 🎮 Start Screen Selection
- Three clickable specialization cards
- Must select before starting
- Welcome message includes field description and accelerator bonus

### State Fields Added
- `specialization`: Selected field type
- `secondaryFocus`: Unlocks at Month ≥ 24
- `socialDebt`: Increases collaboration cost
- `figuresThisRun`, `yearlyIdeaUsed`: For accelerator tracking

---

## [2.19.0] - 2026-01-05 "UX Clarity & Defense Finale"

**Theme**: Structural clarity — game modes make action availability predictable.

### 🎮 Game Mode System
Automatic mode switching:

| Mode | Trigger | Action Restrictions |
|------|---------|---------------------|
| **NORMAL** | Default | All actions available |
| **QUALS_WINDOW** | Year 2, months 6-9 | Focus on exam prep |
| **PROBATION** | Low morale | Limited risky actions |
| **FINALE** | 3+ papers, thesis prep done | Defense-focused actions |

### 🛡️ Defense 3-Track System
Three tracks for thesis defense:
- **Thesis Quality**: From figures, polish, papers
- **Presentation Skill**: From practice, teaching, network
- **Committee Support**: From alignment, advisor relationship

### 👥 Committee Personalities
Lightweight NPCs with biases:
- Prof. Chen ("Methodology Hawk") → thesis_quality
- Prof. Smith ("Industry Friendly") → presentation_skill
- Prof. Alvarez ("Silent but Deadly") → committee_support

### 📅 Quals Countdown Banner
- Color-coded urgency (green → yellow → red)
- Shows months remaining until exam

### 📍 Milestones Tracking
Tracks quals, first paper, and defense status with completion months.

---

## [2.18.0] - 2026-01-05 "Career Endings"

**Theme**: Personalized endings — your final stats determine your career path.

### 🎓 Career Endings System
8 distinct career paths based on game outcome:

**PhD Paths (4):**
| Career | Condition | Description |
|--------|-----------|-------------|
| 🏛️ **Tenure Track Professor** | High alignment + papers | Academic career |
| 🔬 **Research Scientist** | High papers, moderate alignment | Industry R&D |
| 📊 **Data Science Lead** | High network | Tech leadership |
| 🎓 **PhD Graduate** | Default | Standard completion |

**MS-Out Paths (4):**
| Career | Condition | Description |
|--------|-----------|-------------|
| 🚀 **R&D Technical Lead** | High alignment | Tech leadership |
| 📈 **Senior Data Scientist** | High network | Data career |
| 💻 **Software Engineer (ML)** | Moderate balance | ML engineering |
| 🌅 **The Great Escape** | Low morale exit | Career pivot |

### 🔧 Defense Prep Gate
- `defensePrepared` flag required before graduation
- Prevents rushing to defense unprepared

### 😤 Advisor Patience
- `advisorPatienceExhausted` after 3+ interventions
- Affects ending options

---

## [2.17.0] - 2026-01-04 "Pacing & Agency"

**Theme**: The player is no longer a victim of RNG — they are a risk manager.

### 📄 Pre-Register Idea
- Cost: **-5 Network** (or -3 if Network ≥60)
- Effect: **Prevents being scooped**
- Shows protection message when scoop attempt blocked

### 🔧 Equipment Maintenance
- Cost: **1 month** (no research)
- Effect: **Equipment stable for 12 months**
- Removes broken equipment status

### ⚡ High-Throughput Experiment
- Requires: Key Discovery
- Cooldown: 6 months
- **40% Success**: +2 Figures
- **60% Failure**: -20 morale, +Exhaustion

### 📝 Review Response Actions
| Action | Cost | Effect |
|--------|------|--------|
| **Light Response** | -3 morale | +10% accept |
| **Major Rebuttal** | -8 morale | Skip revision |

---

## [2.16.0] - 2026-01-04 "Transparent Systems"

**Theme**: Make the invisible legible

### 🎯 Strategic Alignment Meter
- **Visible bar** (0-100) with gradient coloring
- Shows effects at 30/60/80 thresholds
- Now players understand pitch sessions

### 📚 Quals Prep Visualizer
- **Visible counter** (X/3) in stats bar
- **Color-coded warnings**:
  - Year 1: Neutral (informational)
  - Year 2: Yellow ⚠️
  - Final 3 months: Red 🚨 IMMINENT!

### 🏷️ Event Categorization
- **🎲** Random events (imposter, scoop, seasonal)
- **🧑‍🏫** Advisor interventions
- **⚠️** System pressure warnings

---

## [2.15.0] - 2026-01-04 "Academic Time"

**Theme**: Temporal realism + credential legitimacy

### 📅 Semester System
- **Spring** (Jan-May), **Summer** (Jun-Jul), **Fall** (Aug-Dec)
- UI shows: `Fall · Month 1 · 0 credits`

### 📚 Coursework Credits
- **+3 credits** per Spring/Fall month (if not TA or on medical leave)
- Required for Master's Exit

### 🎓 MS-Out Requirements
- **30 credits + 18 months** minimum
- Shows blocked state with missing requirements

### 💼 Summer Internship Restricted
- Now **June-July only** (true Summer)

---

## [2.14.0] - 2026-01-04 "Career Trajectories"

**Theme**: Your departure is as meaningful as your arrival.

### 🚪 MS-Out Exit Profiles
Timing-based exit narratives with salary bonuses:

| Years | Profile | Narrative | Salary |
|-------|---------|-----------|--------|
| ≤2 | 🚀 **Early Career Pivot** | "Smart move." | - |
| 3-4 | 🔧 **Deep Technical Specialist** | "Domain expert." | +10% |
| 5+ | 🎖️ **Veteran Problem-Solver** | "Resilience is key." | +15% |

### 💼 Summer Internship Action
- Available **May-August** (Year 2+)
- Cost: **3 months**
- Effect: **+25 Network, +15 morale**
- Tradeoff: **-5 Advisor happiness**
- Once per year

### 📰 Review Status Display
Publications panel now shows pending reviews:
- **📝 X Journal in review** | **📋 X Conf in review**
- Updates in real-time as papers progress

### 🎲 Visual Event Distinction
Random events now show **"🎲 [RANDOM EVENT]"** prefix:
- Inspiration, Imposter Syndrome, Getting Scooped
- Seasonal events (Holiday, Summer, New Semester)

Player actions remain unmarked, making causality clear.

---

## [2.12.0] - 2026-01-04 "Recovery Trajectories"

**Theme**: Once the system saves you, what helps you move again?

### ✨ Renewed Perspective Buff
- After **advisor-suggested vacation**, you get a 3-month buff
- **+10% success** to Develop Findings and Document Figures
- Turns forced rest into reset-with-momentum

### 🧘 Imposter Syndrome Soft Cap
- Tracks imposter events in rolling 6-month window
- After **2 events in 6 months**, third event becomes:
  - "You recognize this feeling again. It passes faster."
  - **Reduced impact** (1-2 morale instead of 3-7)
  - **+2 Strategic Alignment** (self-awareness)

### 👁️ Visible Status Badges
- **✨ Renewed Focus (Xmo)**: Shows when +10% buff active
- **🌟 New Lease (Xmo)**: Shows after passing quals retake
- **🏁 Almost There!**: Shows when 3 journal papers reached

### 🏁 Light at the End of the Tunnel
- When **3 journal papers** reached: **50% morale decay reduction**
- Makes the final thesis push more survivable

---

## [2.11.0] - 2026-01-03 "Recovery & Dignified Exit"

**Theme**: Survival should feel earned, exits should feel intentional, and suffering should feel meaningful—not arbitrary.

### Quals Retake: New Lease on Life
- After passing the **retake exam**, you get the "🌟 New Lease on Life" buff
- **Morale decay reduced by 50%** for 6 months
- Models psychological relief after surviving a near-terminal event

### MS-Out Dignity System
- **Escalating warnings** based on low morale duration:
  - 3 months: "Are you doing okay?"
  - 6 months: "We need to discuss the Master's option."
  - 9 months: "This may be your best remaining option."
- **Dignified exit**: If morale hits 0 but you have ≥1 paper, you get a Master's degree (not a failure!)

### Cruelty Control
- **Scoop immunity extended**: 6 months → **24 months**
- No more back-to-back scoops destroying runs

---

## [2.10.0] - 2026-01-03 "Resilience Under Pressure"

**Theme**: Players should lose because they made hard tradeoffs — not because the system quietly cornered them.

### Quals Difficulty Increase
- **Required prep level**: 2 → **3** (harder!)
- Each prep session gives 0/1/2 points
- Countdown warnings now show "need 3 to pass"
- Study group bonus (+1 if network ≥ 50) still applies

### Medical Leave (Emergency Escape)
- Appears when **morale < 15**
- **Effect**: +40 morale, clears exhaustion/burnout
- **Cost**: 3-6 months (random), resets current project
- **One-time use** per run
- Converts inevitable failure into strategic retreat

### Figure Decompression
- Tracks **consecutive figure rejections**
- After 2 rejections: **+30% success bonus** on next attempt
- Message: "You're learning what works. Next attempt will be easier."
- Simulates learning without removing grind

---

## [2.9.0] - 2026-01-03 "Fairness & Clarity"

**Theme**: A player should never lose because they misunderstood priority, timing, or invisible mechanics.

### Bug Fixes
- **Copy Game Link**: Fixed! Now copies full game URL with seed parameter
  - Click "🔗 Copy Game Link" to share your run

### Quals Countdown UI
- **Year 1, Month 9**: "⚠️ QUALS APPROACHING" warning (12 months out)
- **Year 2, Month 7**: "⏳ QUALS IN 2 MONTHS" with prep level shown
- **Year 2, Month 8**: "🚨 QUALS NEXT MONTH - CRITICAL" 

### Quals Soft Fail (Once)
- **First failure**: -25 morale, +Exhaustion, 3-month delay for retake
- **Second failure**: Game over (as before)
- Gives players ONE second chance - still punishing, but not opaque

---

## [2.8.0] - 2026-01-03 "Adaptive Resilience Phase 2"

Based on V2.7 73-month stress test (6-year PhD run). Tunes dominant loops while preserving realism.

### V2.7 Features (Now Documented)
- ⚠️ **Morale Warnings**: CRITICAL at ≤10%, EMERGENCY at ≤5%
- 📜 **End Screen**: Full history, seed display/copy, publication breakdown, advisor happiness

### Breaking Dominant Loops

#### Conference Early Caps
- **Year 1-2**: Max 1 conference per year (was always 2)
- **20% Alienating**: Early conferences may feel isolating (-3 morale)

#### Inspiration Tuning
- **Capped at 2/year**: No more inspiration farming
- **Diminishing returns**: 1st = +15 morale, 2nd = +10 morale
- **20% dead end**: Second inspiration may be flagged as dead end

#### Scoop Cooldown
- **6-month immunity** after being scooped (prevents back-to-back brutality)
- Tracks `lastScoopMonth` in state

#### MS-Out Intelligence
- **If ≥2 papers**: Disable MS-Out offer, give pep talk instead (+15-20 morale)
- Makes late-game MS-Out less absurd

### Balance Changes
- Inspiration reset yearly
- Conference caps tighter for new students
- Productive students get encouragement, not quit suggestions

---

## [2.7.0] - 2026-01-03 "Adaptive Resilience"

Based on 256-month stress test observations. Prevents infinite equilibrium and adds friction.

### Breaking Dominant Loops

#### Advisor Fatigue
- New state: `advisorInterventions` tracks vacation suggestions
- After 5 interventions: Reduced enthusiasm ("You really need to manage your energy...")
- After 10 interventions: Advisor stops offering (no more vacation suggestions)
- 10% chance of "advisor stopped checking" message when struggling alone

#### Vacation Diminishing Returns
- New state: `vacationsThisYear` resets each year
- Each vacation reduces next gain by -5 morale (base 15-25 → min 5)
- Only first vacation of year clears burnout status
- Message changes to "diminishing returns" after 2+ vacations

#### Conference Caps
- Reduced from 3/year to **2/year** (after Year 1)
- Conferences now give +5 network (or +2 if network > 80)
- Morale gain halved when network > 80

#### Hard Variable Bounds
- Figures capped at 3 (prevents "4/3 needed" bug)
- Ideas capped at 5 (prevents hoarding)
- Key discoveries capped at 3

### Balance Changes
- Advisor happiness level effects (added in V2.6)
- Network panel layout fixed

---

## [2.6.0] - 2026-01-03

### Added
- **Read Papers Incentives**: Now gives +2 alignment or +2 network even when no idea gained
- **Advisor Vacation**: Optional rest when morale drops below 25 (+15-25 morale)
- **Advisor Research Feedback**: Ideas/findings feedback now comes from advisor

### Changed
- Publication breakdown: "0 Journal + 0 Conference" (full words)
- Removed "📝 Papers" from Research Pipeline (now in Publications panel)
- Publications panel shows total with J+C breakdown
- "Take Time Off" renamed from "Advisor Vacation"
- Action buttons: "🔬 Develop Findings" and "📊 Validate Discovery"
- TA aligned with semester schedules (Spring Jan-May, Fall Sep-Dec, Summer rare)

---

## [2.5.0] - 2026-01-02

### Added
- **2 Conference = 1 Journal**: Thesis now counts conference papers (2C = 1J equivalent)
- **Conference Paper Count**: Track and display published conference papers
- **Network Utility**: Peer network boosts conf paper acceptance (+0.2% per point)
- **TA Morale Decay**: Teaching duty adds +3 to monthly morale decay
- **Dual Event Display**: "This Month" + "Last Month" side by side
- **Full Event History**: Shows all events (not just 20)

### Changed
- Conference button always visible with (x/3 remaining for this yr)
- Journal Paper next to Conference Paper in actions
- Thesis shows "(XJ + YC)" paper count
- Shortened "Doc Findings" for better display
- Single-line spacing between appended messages

---

## [2.4.0] - 2026-01-02

### Added
- **Burnout Penalty**: Last-Minute Cram now reduces max morale by 10 and adds "burnout" status
- **Early MS-Out**: Year 1 advisor heart-to-heart if morale drops below 15
- **Strategic Alignment Shield**: Alignment reduces monthly morale decay (1 point per 25 alignment)
- **Expanded Reviewer #2**: 9 snarky revision request messages

### Changed
- Burnout status adds +2 to monthly morale decay
- Morale now capped by maxMorale (can be reduced by burnout)
- Alignment rewards skilled play with reduced stress

---

## [2.3.0] - 2026-01-02

### Added
- **Quals Urgency Warning**: Visual indicator 3 months before exam deadline
- **Last-Minute Cram**: Emergency action in August Y2 (-25 morale, +exhaustion, passes quals)
- **Study Group Buff**: Peer Network ≥50 counts as +1 quals prep session
- **Figure Progress**: Document Findings now shows "Figures: X/3"
- **Event Log History**: All events stored and viewable via History button

### Changed
- Quals button shows urgency when unprepared and deadline approaching
- TriggerQuals respects Study Group buff
- Help modal comprehensively updated for V2.2 Pro features

---

## [2.2.0 Pro] - 2026-01-02

### Added
- **Advisor Profiling**: Hidden traits (Risk Tolerance, Attention Span, Strictness) affect outcomes
- **Peer Network Stat**: Build connections through pitches and conferences
- **Pitch Session Action**: Get advisor feedback, learn their preferences (+network)
- **Conference Paper Track**: Quick publish (4mo, 60%, +15 network) vs Journal (8-12mo, graduation)
- **MS-Out Strategic Exit**: Master's ending with 3 profiles (R&D Lead, Data Scientist, Great Escape)
- **Strategic Alignment**: Hidden stat that buffers morale loss and improves outcomes

### Changed
- Conference paper success increases with strategic alignment
- MS-Out appears when morale < 20 and year >= 2
- Network stat displayed in UI

---

## [2.1.0] - 2026-01-02

### Added
- **Imposter Syndrome** (~8% chance per month): Morale hit with flavored messages
- **Getting Scooped** (~3% chance): Another lab publishes your idea first
- **Seasonal Events**: December holiday boost, summer focus, September chaos
- **Teaching Duty** (~10% in fall/spring): Random TA assignment for 3-4 months
- **Reviewer #2** (25% on papers): Major revision requests with snarky messages

### Changed
- **Morale decay 20% steeper**: Base 4/month (was 3), +6 per status (was +5)
- **Figures cleared on submit**: Can't reuse figures for next paper
- Paper acceptance rate: 50% new, 70% revision

---

### Added
- Professional README with badges and architecture diagram
- CONTRIBUTING.md with contribution guidelines
- CHANGELOG.md (this file)
- Pipeline visualizer in UI
- Enhanced stats display

### Changed
- README completely rewritten for clarity

---

## [1.9.0] - 2026-01-02

### Added
- Load button in-game (next to Save)
- Typewriter effect for messages

### Changed
- "35% idea" → "May inspire ideas"
- "Work on Figures" → "Document Findings"
- Papers display: removed "/3"
- Quals prep: removed progress fraction
- Conference limit: 1 in Year 1, 3 after

---

## [1.8.0] - 2026-01-01

### Added
- Paper submission delay (3-6 months wait)
- Pending papers display
- Diverse message variants for actions

### Changed
- "Slack Off" → "Take a Break"  
- "Preliminary Result" → "Initial Findings"
- "Major Result" → "Key Discovery"

---

## [1.7.0] - 2026-01-01

### Added
- Help button with game mechanics modal
- Shareable seed URLs (?seed=X)
- Morale boost on successful actions

---

## [1.6.0] - 2026-01-01

### Added
- pytest suite with automated tests
- Save/Load to browser localStorage
- Load button on start screen

---

## [1.5.0] - 2025-12-31

### Fixed
- Equipment repair bug (now guaranteed within 3 months)

### Added
- Total months counter
- Advisor happiness bar

---

## [1.0.0] - 2025-12-30

### Added
- Initial release
- Core engine port from TypeScript PhD Simulator
- Full research pipeline
- CLI and web interfaces
