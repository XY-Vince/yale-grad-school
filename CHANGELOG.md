# Changelog

All notable changes to GradQuest are documented here.

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
