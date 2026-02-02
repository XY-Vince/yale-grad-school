# 🤖 AGENTS.md - AI Assistant Guide for GradQuest

> **Version**: 2.55 🎯 Focused Mode | **Architecture**: Static JavaScript (GitHub Pages)  
> **Philosophy**: *"Every punishment must unlock a new form of agency."*  
> **Core Tenet**: Mechanics avoid infinite death spirals through mandatory recovery actions.

## Project Overview

**GradQuest** is a strategic PhD life simulator running entirely client-side. Players navigate the research pipeline while managing morale, funding, and advisor relationships.

- **Live Site**: [xy-vince.github.io/GradQuest](https://xy-vince.github.io/GradQuest/)
- **Current**: V2.55 🎯 Focused Mode - Conference Streamline (2/year, one-choice)
- **Architecture**: Pure static JavaScript on GitHub Pages
- **Storage**: Browser LocalStorage for saves
- **Mobile-First**: 4-tab navigation (📊 Status / 🎯 Actions / 🔬 Lab / ⏩ Next)

## 🎯 V3.0 "Gold Release" Roadmap

| Phase | Feature | Key Systems |
|-------|---------|-------------|
| **Phase 0.5** | Architecture Hardening | Central event resolver, hidden metrics audit |
| **Phase 1** | Defense Gauntlet | 3-turn finale with weighted scoring |
| **Phase 2** | Narrative Endings | Multiple paths based on choice history |
| **Phase 3** | Soundscapes | Audio feedback via Web Audio API |
| **Phase 4** | Polish & Release | Performance optimization, bug fixes |

### Defense Scoring (Authoritative Spec)
- **Thesis Quality: 50%** (primary factor)
- **Presentation Skill: 25%**
- **Committee Support: 25%**

## 🛠️ Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Platform** | Static HTML5/JS | GitHub Pages hosting |
| **State** | Immutable JS objects | Object spread updates |
| **Storage** | LocalStorage | JSON serialization |
| **Mobile** | Responsive CSS | 4-tab app-shell pattern |
| **Audio** | Web Audio API | V3.0: sfx_token system |

## 📁 Project Structure

```
docs/
├── index.html          # Main game (V2.55) - single file architecture
├── tests.html          # Test suite
├── rules.md            # Game mechanics documentation
├── memory.md           # Project roadmap & changelog
├── hidden_metrics.md   # Previously hidden game state
└── CONTRIBUTING.md     # Contribution guidelines

data/                   # Game data (if separated in V3.0)
└── rulesets/           # YAML/JSON rulesets (V3.0+ consideration)
```

## 🏗️ Core Architectural Principles

### State Immutability (JavaScript)

All state updates use object spread for immutability:

```javascript
// ✅ Pattern: Functional state updates
updateState(changes) {
    this.state = { ...this.state, ...changes };
    console.log('[STATE]', changes);
}

// ✅ Usage: Never mutate directly
this.updateState({ morale: this.state.morale - 5 });

// ❌ Forbidden: Direct mutation
this.state.morale -= 5;  // Never do this
```

### Central Event Resolver (Critical for V2.55+)

**Problem**: Event handling scattered across systems causes modal collisions, zombie events, state/UI desync.

**Solution**: One authoritative event resolver per tick:

```javascript
// === SYSTEM: Event Resolution ===
// Only the EventResolver may enqueue modals or advance phases

class EventResolver {
    constructor() {
        this.eventQueue = [];
        this.processedThisTick = new Set();
    }
    
    // Central entry point - all events route through here
    resolveTick(state) {
        // 1. Collect all pending events from systems
        const pendingEvents = [
            ...this.checkCrisisTriggers(state),
            ...this.checkRandomEvents(state),
            ...this.checkPhaseTransitions(state)
        ];
        
        // 2. Sort by priority (Emergency > Major > Minor)
        pendingEvents.sort((a, b) => this.priorityWeight(b) - this.priorityWeight(a));
        
        // 3. Process highest priority only (prevents modal spam)
        if (pendingEvents.length > 0) {
            const topEvent = pendingEvents[0];
            this.processEvent(topEvent, state);
        }
        
        // 4. Clear queue for next tick
        this.processedThisTick.clear();
    }
    
    priorityWeight(event) {
        const weights = { Emergency: 100, Major: 50, Minor: 10 };
        return weights[event.priority] || 0;
    }
}
```

### State Ownership & Mutation Rules

Every action/event must declare state ownership:

```javascript
// === SYSTEM: State Ownership ===
// Explicit tags for who can mutate what

const STATE_OWNERS = {
    Core: ['month', 'year', 'phase'],           // EventResolver only
    Player: ['morale', 'items', 'statuses'],    // Player actions
    Advisor: ['advisorTension', 'interventions'], // Advisor system
    Environment: ['funding', 'randomEvents']    // World simulation
};

// ✅ Good: Explicit ownership declaration
const action = {
    id: 'emergencyGrant',
    stateOwner: 'Environment',      // Who mutates
    mutates: ['funding', 'teachingLoad'], // What fields
    priority: 'Emergency',          // Modal priority
    // ...
};

// ❌ Bad: Implicit mutation without ownership
// this.state.funding = 12;  // Who owns this? Unclear.
```

### Hidden Metrics Manifest (Required)

Every hidden metric must be documented:

```javascript
// === HIDDEN METRICS MANIFEST ===
// Each entry: source → sink → decay/reset rule

const HIDDEN_METRICS = {
    advisorTension: {
        source: 'Aggressive player actions',
        sink: 'Advisor interventions, defense skepticism',
        decay: '-10 per month if no aggressive actions',
        surfaced: 'indirect',  // Via advisor dialog tone
        reset: 'On defense completion'
    },
    
    strategicAlignment: {
        source: 'Research focus choices, advisor meetings',
        sink: 'Conference success, defense committee support',
        decay: '-5 per month if neglected',
        surfaced: 'indirect',  // Via conference feedback
        reset: 'Never'
    },
    
    dissertationDraftQuality: {
        source: 'Figure quality, paper acceptance',
        sink: 'Defense thesis quality track',
        decay: 'None',
        surfaced: 'indirect',  // Via defense prep feedback
        reset: 'On defense start'
    }
};

// Rule: Every hidden metric must be surfaced (UI/log) or removed
```

### LocalStorage Persistence

```javascript
// ✅ Save: Serialize with version
save() {
    const saveData = {
        ...this.state,
        statuses: Array.from(this.state.statuses),
        version: '2.55'
    };
    localStorage.setItem('gradquest_save', JSON.stringify(saveData));
}

// ✅ Load: Deserialize with migration check
load() {
    const saveData = JSON.parse(localStorage.getItem('gradquest_save'));
    this.state = {
        ...saveData,
        statuses: new Set(saveData.statuses)
    };
    // V3.0: Add migration logic here
}
```

### Mobile-First UX

- **4-Tab Navigation**: Status | Actions | Lab | Next
- **48px Touch Targets**: All buttons minimum 48×48px
- **Sticky Bottom Bar**: Actions always accessible
- **Horizontal Stats Scroll**: On narrow screens
- **Tab State Persistence**: Remember active tab

## ✅ Core Philosophy

### The "Slog" Check (Mandatory)

Every penalty must unlock agency. Before any feature ships:

1. Identify all crisis states (funding=0, morale<10, burnout≥60)
2. Verify recovery action exists for each
3. Test: Can player recover to playable state?

| Crisis | Recovery Action | Agency |
|--------|----------------|--------|
| Funding=0 | Emergency Grant | +12mo (teaching penalty) |
| Morale<10 | Medical Leave | Reset +40 morale |
| Burnout≥60 | Vacation | −burnout + buff |
| Failed Quals | Retake | 6-month window |

### Action Balance Consistency (Focused Mode)

**Problem**: Actions look equivalent but have different hidden payoffs.

**Solution**: Normalize actions within choice sets with clear archetypes:

```javascript
// === ACTION ARCHETYPES ===
// Every choice set must map to: Safe / Risky / Tempo

const CONFERENCE_ARCHETYPES = {
    poster: {
        archetype: 'Safe',
        payoff: 'Low network, guaranteed morale',
        risk: 'None',
        explainable: 'Safe choice, steady progress'
    },
    talk: {
        archetype: 'Risky',
        payoff: 'High network, possible embarrassment',
        risk: 'Morale loss if failed',
        explainable: 'High reward but risky'
    },
    network: {
        archetype: 'Tempo',
        payoff: 'Immediate network boost',
        risk: 'Opportunity cost (no paper progress)',
        explainable: 'Short-term gain, long-term tradeoff'
    }
};

// Rule: Remove any option that can't be explained in one sentence
```

### Event & Modal Discipline (Critical)

**Enforce**: 1 modal max per turn, highest priority only:

```javascript
// === SYSTEM: Modal Discipline ===

class ModalManager {
    constructor() {
        this.maxModalsPerTurn = 1;
        this.shownThisTurn = 0;
    }
    
    canShowModal(priority) {
        // Only show if under limit and highest priority
        if (this.shownThisTurn >= this.maxModalsPerTurn) {
            return false;
        }
        
        // Check if higher priority event pending
        const pending = this.getPendingEvents();
        const highestPriority = Math.max(...pending.map(e => e.priorityWeight));
        
        return priority >= highestPriority;
    }
    
    showModal(content, priority) {
        if (!this.canShowModal(priority)) {
            // Queue for next turn or log silently
            this.queueForNextTurn(content, priority);
            return false;
        }
        
        // Show modal
        this.renderModal(content);
        this.shownThisTurn++;
        return true;
    }
    
    resetTurn() {
        this.shownThisTurn = 0;
    }
}
```

**Strip legacy flavor**: Remove any text implying unavailable actions.

### Conference Lockout (V2.55 Enforced)

- **Hard limit**: 2 conferences per year
- **One-choice**: Select Poster/Talk/Network, then locked for 2 months
- **Validation**: No overlapping conference actions

## 🎮 Core Game Systems

### Research Pipeline
Idea → Preliminary Findings → Key Discovery → Figures (×3) → Paper → Published

### Win/Lose Conditions
- **Win PhD**: 3 papers + thesis defense
- **Win Master's**: 30 credits + 18mo + advisor approval  
- **Lose**: Morale=0, Year 8+, Failed Quals (no retake)

### UI Modes
- `NORMAL` - Standard gameplay
- `QUALS_WINDOW` - Study actions prioritized (Year 2)
- `PROBATION` - Recovery actions only (post-failure)
- `FINALE` - Defense minigame (V3.0)

### Specializations (V2.20+)
- 🔬 **Experimentalist**: Faster figures (×0.7)
- 📐 **Theoretician**: Auto-idea yearly
- 💻 **Computational**: +50% thesis speed

## 🧪 Testing & Validation

### Manual QA Checklist
- [ ] All crises have recovery paths
- [ ] Conference lockout works (no double-booking)
- [ ] Mobile 4-tab navigation functional
- [ ] Save/load preserves all state
- [ ] Median completion 60-75 months (playtest 10 runs)
- [ ] Event resolver prevents modal collisions
- [ ] Only 1 modal per turn maximum

### V3.0 Testing Strategy (DECISION REQUIRED)

**Before Phase 1 begins, choose one:**

#### Option A: Jest + Testing Library (Recommended)
Automated unit testing for state logic and event resolution.

```bash
# Setup
npm init -y
npm install --save-dev jest @testing-library/dom jsdom

# Test example: tests/state.test.js
test('morale crisis triggers medical leave unlock', () => {
    const state = createTestState({ morale: 5 });
    game.checkCrisisStates(state);
    expect(state.recoveryActions).toContain('medical_leave');
});

# Run tests
npm test
```

**Pros**: Automated regression detection, CI-ready  
**Cons**: Requires build step, learning curve

#### Option B: Enhanced Manual QA (Current)
Documented playtest scenarios with metrics tracking.

**Required Deliverables**:
1. **Playtest Protocol** (10 documented runs per build)
   - Record: completion time, ending, key choices
   - Target: Median 60-75 months

2. **Metrics Tracking Sheet**
   | Run | Seed | Months | Ending | Issues |
   |-----|------|--------|--------|--------|
   | 1 | 12345 | 68 | PhD | None |

3. **Community Beta** (Discord/Reddit)
   - 20+ external playtesters
   - Issue template with save export

**Pros**: No build changes, immediate feedback  
**Cons**: Time-intensive, inconsistent coverage

**Recommendation**: Start with Option B for Phase 1, migrate to Option A for Phase 3+ if complexity warrants.

## 🎨 UI/UX Tokens

| Token | Usage | Accessibility |
|-------|-------|---------------|
| `status-good` | Green - Progress | Icon + Text + ARIA label |
| `status-warning` | Yellow - Warning | Icon + Text + ARIA label |
| `status-critical` | Red - Critical | Icon + Text + ARIA live |
| Emoji | Events (📢, 🏖️) | `aria-label` describing meaning |
| Icons | Field markers (🔬, 📐, 💻) | Consistent symbol usage |

### Accessibility Requirements
- **ARIA Labels**: All emoji and icons have descriptive labels
- **Keyboard Navigation**: All actions accessible via keyboard
- **Screen Reader**: Status announcements on state changes
- **Color Contrast**: WCAG 2.1 AA minimum (4.5:1)
- **Touch Targets**: Minimum 48×48px for mobile

## 🚨 Critical Rules

### Architecture
- ✅ **Central Resolver**: One EventResolver per tick, exclusive modal control
- ✅ **State Ownership**: Every mutation declares owner and priority
- ✅ **Immutability**: Use `updateState()` with object spread
- ✅ **1 Modal Max**: Highest priority only per turn

### Game Balance
- ✅ **Recovery**: Every crisis must have exit ramp (Slog Check)
- ✅ **Action Clarity**: Each choice explainable in one sentence
- ✅ **Conference Lock**: Hard 2-month lock after choice
- ✅ **Hidden Metrics**: Manifest required - surface or remove

### Code Quality
- ✅ **LocalStorage**: Version all saves for migration
- ✅ **ARIA Labels**: All non-text elements need labels
- ✅ **Deterministic**: RNG seeded for reproducibility
- ✅ **Soft Separation**: Use `// === SYSTEM: Name ===` comments

## 📚 Key References

- **Implementation Details**: `CURSORRULES` (JS patterns, mobile UX)
- **Game Mechanics**: `docs/rules.md`
- **Changelog**: `docs/memory.md`
- **Hidden State**: `docs/hidden_metrics.md`

## Version Rollback Plan

**V3.0 must serve V2.55 as fallback**:
```javascript
// In index.html initialization
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('version') === '2.55') {
    loadV255Code(); // Fallback mode
}
```

## Structural Prep for V3.0

Soft-separate logic in single file via system comments:

```javascript
// === SYSTEM: Core Engine ===
// State management, tick loop, event resolution

// === SYSTEM: Defense ===
// Defense minigame logic, scoring, endings

// === SYSTEM: Conferences ===
// Conference selection, lockout, effects

// === SYSTEM: UI ===
// Rendering, transformers, mobile navigation
```

This provides modularity without refactoring cost.

---

*"Every punishment must unlock a new form of agency."* - GradQuest Engineering Standards
