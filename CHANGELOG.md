# Changelog

All notable changes to GradQuest are documented here.

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
