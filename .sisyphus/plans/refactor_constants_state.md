# Plan: Code Quality Refactoring - Constants & State Access

## Context
The codebase has 6,552 lines with significant technical debt:
- Magic numbers scattered throughout (3, 100, 12, etc.)
- 174 instances of direct state mutation bypassing updateState()
- Monolithic 311KB file needs gradual refactoring

## Goals
1. **Extract Constants**: Replace all magic numbers with named constants
2. **Fix State Access**: Replace direct mutations with updateState() calls

## Scope
File: `docs/index.html` (6,552 lines, 311KB)

## Phase 1: Extract Constants (Priority: High)

### Constants to Define
```javascript
const GAME_CONSTANTS = {
  // Graduation Requirements
  REQUIRED_JOURNAL_PAPERS: 3,
  REQUIRED_CONF_PAPERS_FOR_HYBRID: 2,
  MIN_JOURNAL_PAPERS_FOR_HYBRID: 2,
  MAX_THESIS_PROGRESS: 100,
  
  // Stats
  MAX_MORALE: 100,
  MAX_STRESS: 120,
  MAX_NETWORK: 100,
  MAX_ALIGNMENT: 100,
  MIN_MORALE_FOR_CRITICAL: 15,
  MIN_MORALE_FOR_WARNING: 30,
  
  // Timing
  MONTHS_PER_YEAR: 12,
  QUALS_YEAR: 2,
  QUALS_MONTH: 9,
  QUALS_PREP_REQUIRED: 3,
  
  // Paper Review
  MIN_PAPER_WAIT_MONTHS: 3,
  MAX_PAPER_WAIT_MONTHS: 6,
  REVISION_WAIT_MONTHS: 2,
  MAX_REVISION_WAIT_MONTHS: 3,
  
  // Conference
  MAX_CONFERENCES_PER_YEAR: 2,
  CONFERENCE_COOLDOWN_MONTHS: 2,
  
  // Defense
  DEFENSE_TURNS: 3,
  BASE_COMMITTEE_APPROVAL: 35,
  
  // Items
  MAX_FIGURES: 3,
  MAX_IDEAS: 5,
  MAX_KEY_DISCOVERIES: 3,
};
```

### Tasks
- [x] Define GAME_CONSTANTS object near top of script
- [x] Replace all instances of `3` (paper requirement) with constant
- [x] Replace all instances of `100` (max stats) with constant
- [x] Replace `2 * 12 + 9` with QUALS_MONTH calculation
- [x] Replace hardcoded month counts with constants
- [x] Verify no regressions in game logic

## Phase 2: Fix State Access (Priority: High)

### Pattern to Find and Replace
**Before:**
```javascript
this.state.morale = Math.min(100, this.state.morale + 5);
```

**After:**
```javascript
this.updateState({ 
  morale: Math.min(GAME_CONSTANTS.MAX_MORALE, this.state.morale + 5) 
}, 'Wellness');
```

### State Owner Mapping
- `morale`, `stress`, `burnout` → 'Wellness'
- `peerNetwork`, `strategicAlignment` → 'Social'
- `fundingMonths`, `credits` → 'Academic'
- `items` (ideas, figures, papers) → 'Inventory'
- `thesisProgress`, `graduation` → 'Progression'

### Tasks
- [x] Replace direct morale mutations with updateState('Wellness')
- [x] Replace direct stress mutations with updateState('Wellness')
- [x] Replace direct network mutations with updateState('Social')
- [x] Replace direct alignment mutations with updateState('Social')
- [x] Replace direct funding mutations with updateState('Academic')
- [x] Replace direct item mutations with updateState('Inventory')
- [x] Replace direct thesis progress mutations with updateState('Progression')

## Verification
- [x] Game loads without errors
- [x] All mechanics work (test 1 year of gameplay)
- [x] Console shows [STATE] logs with correct owners
- [x] No direct `this.state.x = y` assignments remain

## Risks
- **High risk of breaking game logic** - Must test thoroughly
- **Performance impact** - updateState() adds overhead
- **Merge conflicts** - Large file changes

## Rollback Plan
- Keep git commit history clean
- Test each batch of changes before proceeding
- Use browser console to verify state changes
