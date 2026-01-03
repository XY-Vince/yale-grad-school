# Changelog

All notable changes to GradQuest are documented here.

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
