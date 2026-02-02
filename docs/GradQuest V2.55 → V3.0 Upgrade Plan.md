# GradQuest V2.55 → V3.0 Gold

## Pre-Flight Checklist (Complete Before Phase 1)

**Architecture Decisions (Make Now):**
- [ ] **Testing Strategy**: Choose Jest (Option A) or Enhanced Manual QA (Option B)
- [ ] **Event Resolver**: Confirm single-file implementation or extract to module
- [ ] **Data Separation**: Keep inline JS objects or migrate to external JSON
- [ ] **V2.55 Fallback**: Implement `?version=2.55` URL param now or defer to Phase 5

**Documentation Sync:**
- [ ] Add Central EventResolver code example to CURSORRULES
- [ ] Cross-reference Hidden Metrics Manifest between AGENTS.md and code
- [ ] Create V3.0 branch in Git with protected `main` branch

---

## Phase 0: Critical Infrastructure
**Goal:** Lock down state integrity rules before any feature work.

### 0.1 Graduation Contract
```javascript
// Add to game state validation
const GRADUATION_CONTRACT = {
    defenseUnlocked: () => {
        return this.state.thesisProgress >= 100 && 
               this.isPortfolioEligible();
    },
    
    isPortfolioEligible: () => {
        const journalPapers = this.state.papers.filter(p => p.type === 'journal').length;
        const confPapers = this.state.papers.filter(p => p.type === 'conference').length;
        
        // Standard: 3 journal papers OR Hybrid: 2 journal + 2 conference
        return journalPapers >= 3 || 
               (journalPapers >= 2 && confPapers >= 2);
    }
};
```

**Implementation:**
- [ ] Add `GRADUATION_CONTRACT` object to game engine
- [ ] Replace all graduation checks with contract methods
- [ ] Update "Defense" button to use `defenseUnlocked()`
- [ ] Add debug panel showing contract status (removable in production)

**Validation:**
- [ ] Test: Thesis 100% + 2 papers → Defense locked ✓
- [ ] Test: Thesis 100% + 3 journals → Defense unlocked ✓
- [ ] Test: Thesis 100% + 2J + 2C → Defense unlocked ✓

---

### 0.2 Automated QA Regression Checks

**Six Critical Tests (from V3 plan §8):**

```javascript
// tests/regression.test.js (if using Jest)
// OR tests.html enhancement (if manual QA)

const REGRESSION_TESTS = {
    test1_defenseGatingEnforced: () => {
        const state = createTestState({ thesisProgress: 99, papers: 3 });
        assert(!GRADUATION_CONTRACT.defenseUnlocked(), 
            'FAIL: Defense unlocked before thesis=100');
    },
    
    test2_oneModalPerTick: () => {
        const events = [
            { priority: 'Emergency', id: 'funding_crisis' },
            { priority: 'Major', id: 'advisor_meeting' },
            { priority: 'Minor', id: 'random_event' }
        ];
        const shown = EventResolver.resolveTick(events);
        assert(shown.length === 1, 
            `FAIL: ${shown.length} modals shown (expected 1)`);
    },
    
    test3_noEmptyMonthLogs: () => {
        const state = simulateFullGame();
        const emptyMonths = state.history.filter(h => h.events.length === 0);
        assert(emptyMonths.length === 0,
            `FAIL: ${emptyMonths.length} months with zero log output`);
    },
    
    test4_conferenceNoOverlap: () => {
        const engine = new GameEngine();
        engine.selectConferenceOption('conf1', 'poster');
        const canAttendConf2 = engine.canAttendConference('conf2');
        assert(!canAttendConf2 || engine.state.month >= engine.state.conferenceLockout,
            'FAIL: Conference overlap detected');
    },
    
    test5_singlePrimaryStatMutation: () => {
        // Track state changes during action
        const before = { ...engine.state };
        engine.actions.submitPaper();
        const after = engine.state;
        
        const primaryStats = ['thesisProgress', 'papers', 'alignment'];
        const mutatedPrimary = primaryStats.filter(stat => 
            before[stat] !== after[stat]
        );
        
        assert(mutatedPrimary.length <= 1,
            `FAIL: Action mutated ${mutatedPrimary.length} primary stats (max 1)`);
    },
    
    test6_defenseStateCleanup: () => {
        const engine = new GameEngine();
        engine.startDefense();
        engine.completeDefense('success');
        
        assert(!engine.state.defenseActive,
            'FAIL: Defense state persists after completion');
        assert(engine.state.uiMode !== 'FINALE',
            'FAIL: UI mode stuck in FINALE after defense');
    }
};
```

**Implementation:**
- [ ] Create `tests/regression.test.js` or enhance `tests.html`
- [ ] Add CI script to run tests (GitHub Actions or pre-commit hook)
- [ ] Document expected test output in README

**Validation:**
- [ ] All 6 tests pass on current V2.55 build
- [ ] Tests fail when breaking changes introduced (verify sensitivity)

---

### 0.3 Event Priority & Modal Discipline

**Central Event Resolver** (code from AGENTS.md):

```javascript
// === SYSTEM: Event Resolution ===
class EventResolver {
    constructor() {
        this.priorityWeights = { Emergency: 100, Major: 50, Minor: 10 };
        this.modalShownThisTurn = false;
    }
    
    resolveTick(state) {
        // 1. Collect pending events
        const pending = [
            ...this.checkCrisisEvents(state),    // Emergency
            ...this.checkPhaseEvents(state),     // Major
            ...this.checkRandomEvents(state)     // Minor
        ];
        
        // 2. Sort by priority
        pending.sort((a, b) => 
            this.priorityWeights[b.priority] - this.priorityWeights[a.priority]
        );
        
        // 3. Process ONLY highest priority
        if (pending.length > 0 && !this.modalShownThisTurn) {
            const topEvent = pending[0];
            this.processEvent(topEvent, state);
            
            if (topEvent.showsModal) {
                this.modalShownThisTurn = true;
            }
        }
        
        return pending[0] || null;
    }
    
    resetTurn() {
        this.modalShownThisTurn = false;
    }
}
```

**Implementation:**
- [ ] Add `EventResolver` class to game engine
- [ ] Refactor `advanceMonth()` to call `resolver.resolveTick()`
- [ ] Tag all events with priority: `Emergency` / `Major` / `Minor`
- [ ] Add `resetTurn()` call at end of month advance

**Validation:**
- [ ] Test: Trigger 3 events simultaneously → Only 1 modal shown
- [ ] Test: Emergency overrides Major when both trigger
- [ ] Regression test #2 passes

---

### 0.4 Defense State Cleanup

**Problem:** Defense flags persist after completion, causing zombie state.

**Fix:**
```javascript
// In defense completion handler
completeDefense(outcome) {
    // Calculate results
    const score = this.calculateDefenseScore();
    const ending = this.determineEnding(score);
    
    // Show results modal
    this.showDefenseResults(outcome, score, ending);
    
    // CRITICAL: Clear all defense flags immediately
    this.updateState({
        defenseActive: false,
        defenseTurn: 0,
        defenseThesisQuality: 0,
        defensePresentation: 0,
        defenseCommittee: 0,
        uiMode: 'NORMAL',  // Exit FINALE mode
        graduated: outcome === 'success'
    });
    
    // Clear any defense-specific actions
    const actions = this.state.availableActions.filter(
        a => !a.startsWith('defense_')
    );
    this.updateState({ availableActions: actions });
}
```

**Implementation:**
- [ ] Add state cleanup to `completeDefense()` method
- [ ] Add cleanup to failure path (`failDefense()`)
- [ ] Verify no defense flags remain in state after completion

**Validation:**
- [ ] Regression test #6 passes
- [ ] Manual test: Complete defense → Start new game → No defense artifacts

---

### 0.5 Log Sanitization

**Remove from event messages:**
1. "Qualifying exam time! (Remember to study)"  ← Repetitive
2. "(Response actions will appear after this)" ← Instructional clutter
3. "👉 Go to Actions to Accept/Decline" ← UI instruction

**Implementation:**
```javascript
// In event logger
logEvent(message, priority = 'Minor') {
    // Blacklist patterns
    const SUPPRESS_PATTERNS = [
        /\(Remember to study\)/i,
        /Response actions will appear/i,
        /Go to Actions to/i,
        /👉/  // Remove pointing emoji instructions
    ];
    
    // Filter message
    let cleanMessage = message;
    for (const pattern of SUPPRESS_PATTERNS) {
        cleanMessage = cleanMessage.replace(pattern, '').trim();
    }
    
    // Remove double spaces
    cleanMessage = cleanMessage.replace(/\s+/g, ' ');
    
    if (cleanMessage.length > 0) {
        this.state.eventLog.push({
            message: cleanMessage,
            priority: priority,
            timestamp: `${this.state.year}/${this.state.month}`
        });
    }
}
```

**Implementation:**
- [ ] Add message filter to event logger
- [ ] Audit all event messages for instructional text
- [ ] Replace with implicit UI affordances (buttons appear automatically)

**Validation:**
- [ ] Play 12 months → No repetitive warnings in log
- [ ] Regression test #3 passes (no empty month logs)

---

## Phase 1: Balance & Playability
**Goal:** Fix loss rate and mid-game momentum problems.

### 1.1 Stat Classification & Mutation Rules

**Explicit State Ownership:**
```javascript
const STATE_CLASSIFICATION = {
    primary: {
        thesisProgress: { owner: 'ProgressionEngine', actions: ['writeThesis'] },
        papers: { owner: 'InventoryManager', actions: ['submitPaper', 'acceptPaper'] },
        alignment: { owner: 'SocialEngine', actions: ['pitchSession', 'conference'] }
    },
    secondary: {
        network: { owner: 'SocialEngine', actions: ['conference', 'collaborate'] },
        morale: { owner: 'WellnessEngine', actions: ['takeBreak', 'vacation'] },
        funding: { owner: 'ResourceEngine', actions: ['emergencyGrant', 'advanceMonth'] }
    }
};

// Validation in updateState()
updateState(changes) {
    // Count primary stat mutations
    const primaryMutations = Object.keys(changes).filter(key =>
        STATE_CLASSIFICATION.primary.hasOwnProperty(key)
    );
    
    if (primaryMutations.length > 1) {
        console.warn(`[WARNING] Action mutated ${primaryMutations.length} primary stats:`, 
                     primaryMutations);
        // Regression test #5 would catch this
    }
    
    this.state = { ...this.state, ...changes };
}
```

**Implementation:**
- [ ] Add `STATE_CLASSIFICATION` object
- [ ] Add mutation count validation to `updateState()`
- [ ] Audit existing actions for multi-primary-stat mutations
- [ ] Fix violations or justify exceptions in comments

---

### 1.2 Exhaustion & Morale Tuning

**Changes:**
1. Exhaustion clears 50% on "Break" (up from implied ~25%)
2. Morale floor at 15% triggers Crisis Mode
3. Advisor rescue cooldown: every 6 months max

```javascript
// In wellness engine
takeBreak() {
    const moraleGain = 15;
    const exhaustionClear = this.state.exhaustion * 0.5;  // 50% clear
    
    this.updateState({
        morale: Math.min(100, this.state.morale + moraleGain),
        exhaustion: Math.max(0, this.state.exhaustion - exhaustionClear),
        month: this.state.month + 1
    });
}

// Morale floor enforcement
applyMonthlyDecay() {
    let newMorale = this.state.morale - this.getMoraleDecay();
    
    // Floor at 15%
    if (newMorale < 15) {
        newMorale = 15;
        
        // Trigger Crisis Mode
        if (!this.state.crisisModeActive) {
            this.enterCrisisMode();
        }
    }
    
    this.updateState({ morale: newMorale });
}

enterCrisisMode() {
    this.updateState({
        crisisModeActive: true,
        availableActions: [...this.state.availableActions, 'medicalLeave']
    });
    
    this.showModal({
        title: '💔 Crisis Mode',
        message: 'Your morale has hit critical levels. Consider taking Medical Leave.',
        priority: 'Emergency'
    });
}
```

**Implementation:**
- [ ] Update `takeBreak()` exhaustion formula
- [ ] Add morale floor logic to monthly decay
- [ ] Implement Crisis Mode state + recovery action
- [ ] Add advisor rescue cooldown tracking

**Validation:**
- [ ] Test: Morale never drops below 15
- [ ] Test: Crisis Mode activates at 15%
- [ ] Test: Medical Leave restores to playable state

---

### 1.3 Workshop Paper (Early Momentum)

**Action Spec:**
- **Availability:** Years 1-2 only, requires 1 Idea
- **Success Rate:** 60%
- **Outcome:** +10 Morale, +5 Network, does NOT count toward graduation
- **Purpose:** Gives players tangible progress in early game

```javascript
// Add to actions
workshopPaper: {
    id: 'workshopPaper',
    name: 'Submit Workshop Paper',
    category: 'research',
    available: () => {
        return this.state.year <= 2 && 
               this.state.ideas.length > 0 &&
               !this.state.workshopPaperSubmitted;
    },
    cost: { time: 1, ideas: 1 },
    execute: () => {
        const success = this.rng.next() < 0.6;  // 60% success
        
        if (success) {
            this.updateState({
                morale: Math.min(100, this.state.morale + 10),
                network: this.state.network + 5,
                workshopPaperSubmitted: true
            });
            
            this.logEvent('🎉 Workshop paper accepted! Great early progress.');
        } else {
            this.updateState({
                morale: Math.max(0, this.state.morale - 5),
                workshopPaperSubmitted: true
            });
            
            this.logEvent('📝 Workshop paper rejected, but you learned from the feedback.');
        }
    }
}
```

**Implementation:**
- [ ] Add `workshopPaper` action
- [ ] Add `workshopPaperSubmitted` flag to state
- [ ] Add to action panel in Years 1-2
- [ ] Write 3+ variant success/failure messages

**Validation:**
- [ ] Test: Action appears Year 1 with idea
- [ ] Test: Action disappears Year 3+
- [ ] Test: Success grants morale but no grad credit

---

### 1.4 Debug-Lite HUD

**Visual Indicators (Non-Numeric):**

```javascript
// In UI transformer
getDebugHUD() {
    return {
        alignment: this.getAlignmentIndicator(),
        burnoutRisk: this.getBurnoutRiskIndicator(),
        advisorStatus: this.getAdvisorAvailability()
    };
}

getAlignmentIndicator() {
    const align = this.state.alignment;
    if (align < 20) return { level: 'Low', color: 'red', icon: '⚠️' };
    if (align < 60) return { level: 'Neutral', color: 'yellow', icon: '😐' };
    return { level: 'High', color: 'green', icon: '✅' };
}

getBurnoutRiskIndicator() {
    const burnout = this.state.burnout;
    if (burnout < 30) return { level: 'Calm', color: 'green', icon: '😌' };
    if (burnout < 60) return { level: 'Strained', color: 'yellow', icon: '😰' };
    return { level: 'Critical', color: 'red', icon: '🔥' };
}

getAdvisorAvailability() {
    if (this.state.advisorType === 'phantom') {
        const available = this.rng.next() > 0.5;
        return available ? 
            { status: 'Present', icon: '👨‍🏫' } : 
            { status: 'Absent', icon: '👻' };
    }
    return { status: 'Present', icon: '👨‍🏫' };
}
```

**HTML Implementation:**
```html
<div class="debug-hud">
    <div class="hud-item">
        <span class="hud-label">Advisor Trust</span>
        <span class="hud-value" data-level="{{alignment.level}}" 
              style="color: {{alignment.color}}">
            {{alignment.icon}} {{alignment.level}}
        </span>
    </div>
    <div class="hud-item">
        <span class="hud-label">Burnout Risk</span>
        <span class="hud-value" data-level="{{burnout.level}}"
              style="color: {{burnout.color}}">
            {{burnout.icon}} {{burnout.level}}
        </span>
    </div>
    <div class="hud-item">
        <span class="hud-label">Advisor Status</span>
        <span class="hud-value">
            {{advisor.icon}} {{advisor.status}}
        </span>
    </div>
</div>
```

**Implementation:**
- [ ] Add HUD transformer methods
- [ ] Create HUD HTML section in Status tab
- [ ] Style with color indicators
- [ ] Add tooltips explaining each indicator

**Validation:**
- [ ] Test: Alignment changes reflected in HUD
- [ ] Test: Burnout color updates correctly
- [ ] Test: Phantom advisor shows "Absent" sometimes

---

### 1.5 Diminishing Returns Warning

**When to Show:**
- Consecutive research actions without break (3+ in a row)
- High exhaustion (>60)
- Low morale during research (<30)

```javascript
// In action execution
checkDiminishingReturns(actionCategory) {
    const fatigueActive = 
        this.state.consecutiveResearchActions >= 3 ||
        this.state.exhaustion > 60 ||
        (this.state.morale < 30 && actionCategory === 'research');
    
    if (fatigueActive && !this.state.fatigueWarningShown) {
        this.showToast({
            message: '⚠️ Fatigue is slowing your progress. Consider taking a break.',
            type: 'warning',
            duration: 5000
        });
        
        this.updateState({ fatigueWarningShown: true });
        
        // Reset warning shown after break
        if (actionCategory === 'mental_health') {
            this.updateState({ fatigueWarningShown: false });
        }
    }
    
    return fatigueActive;
}

// Reduce progress when fatigued
executeResearchAction(action) {
    const isFatigued = this.checkDiminishingReturns('research');
    let progressGain = action.baseProgress;
    
    if (isFatigued) {
        progressGain *= 0.7;  // 30% penalty
    }
    
    // ... apply progress
}
```

**Implementation:**
- [ ] Add fatigue detection logic
- [ ] Add toast/warning system
- [ ] Apply progress penalty when fatigued
- [ ] Clear warning after break

**Validation:**
- [ ] Test: 3 research actions → Warning appears
- [ ] Test: Break → Warning clears
- [ ] Test: Progress reduced when fatigued

---

### 1.6 Qualifying Exam Rebalance

**Changes:**
1. Randomize prep: 0-2 points per study action (mean 1.5)
2. Lower threshold: 2-3 required (down from 3+)
3. Specialization bonus: +0.5 prep per action

```javascript
// In quals system
studyForQuals() {
    // Random prep gain: 0, 1, or 2 points
    const baseGain = Math.floor(this.rng.next() * 3);  // 0-2
    
    // Specialization bonus
    const specializationBonus = this.state.specialization === 'theoretician' ? 0.5 : 0;
    
    const totalGain = baseGain + specializationBonus;
    
    this.updateState({
        qualsPrep: this.state.qualsPrep + totalGain,
        month: this.state.month + 1
    });
    
    this.logEvent(`📚 Studied for quals (+${totalGain.toFixed(1)} prep)`);
}

checkQualsPass() {
    // Dynamic threshold based on specialization
    const threshold = this.state.specialization === 'theoretician' ? 2 : 3;
    
    return this.state.qualsPrep >= threshold;
}
```

**Implementation:**
- [ ] Update `studyForQuals()` with RNG gain
- [ ] Lower passing threshold
- [ ] Add specialization bonus
- [ ] Update help text with new requirements

**Validation:**
- [ ] Playtest 10 runs → Quals pass rate >80%
- [ ] Test: Theoretician reaches threshold faster

---

## Phase 2: UX Polish & Clarity

### 2.1 Field-Specific Action Renaming

**Mapping:**

| Generic Action | Experimentalist | Theoretician | Computational |
|----------------|-----------------|--------------|---------------|
| Validate Discovery | Run Experiment | Formalize Proof | Run Simulation |
| Make Figures | Photograph Results | Draw Diagrams | Generate Plots |
| Develop Findings | Collect Data | Derive Lemma | Process Dataset |

**Implementation:**
```javascript
// In action transformer
getActionName(actionId, specialization) {
    const nameMap = {
        validateDiscovery: {
            experimentalist: 'Run Experiment',
            theoretician: 'Formalize Proof',
            computational: 'Run Simulation'
        },
        makeFigures: {
            experimentalist: 'Photograph Results',
            theoretician: 'Draw Diagrams',
            computational: 'Generate Plots'
        }
        // ... more mappings
    };
    
    return nameMap[actionId]?.[specialization] || 
           this.getDefaultActionName(actionId);
}
```

**Implementation:**
- [ ] Create action name mapping object
- [ ] Update UI transformer to use specialized names
- [ ] Update action descriptions for flavor
- [ ] Test all three specializations

---

### 2.2 Visual State Indicators

**Morale/Stress Tints:**

```css
/* Blue filter for low morale */
.game-container[data-morale="low"] {
    filter: brightness(0.85) sepia(0.2) hue-rotate(180deg);
    transition: filter 0.5s ease;
}

/* Red pulse for high stress */
.game-container[data-stress="high"] {
    animation: stress-pulse 2s infinite;
}

@keyframes stress-pulse {
    0%, 100% { filter: brightness(1); }
    50% { filter: brightness(0.95) sepia(0.15) hue-rotate(-10deg); }
}
```

**JavaScript:**
```javascript
// Update container attributes
updateVisualState() {
    const container = document.querySelector('.game-container');
    
    // Morale tint
    if (this.state.morale < 30) {
        container.setAttribute('data-morale', 'low');
    } else {
        container.removeAttribute('data-morale');
    }
    
    // Stress pulse
    if (this.state.stress > 70) {
        container.setAttribute('data-stress', 'high');
    } else {
        container.removeAttribute('data-stress');
    }
}
```

**Implementation:**
- [ ] Add CSS filters and animations
- [ ] Update `updateVisualState()` in render loop
- [ ] Test transitions are smooth
- [ ] Ensure accessibility (don't rely solely on color)

---

### 2.3 Four-Tab Action Panel

**Tab Structure:**
- **Research:** Pipeline actions (Read Papers, Work on Idea, etc.)
- **Self-Care:** Wellness actions (Break, Vacation, Medical Leave)
- **Admin:** High-stakes actions (Defend, Emergency Grant, Quals)
- **Lab:** Social actions (Pitch Session, Conference, Collaboration)

**HTML Structure:**
```html
<div class="action-tabs">
    <button class="tab-btn active" data-tab="research">🔬 Research</button>
    <button class="tab-btn" data-tab="selfcare">💆 Self-Care</button>
    <button class="tab-btn" data-tab="admin">📋 Admin</button>
    <button class="tab-btn" data-tab="lab">🤝 Lab</button>
</div>

<div class="action-panels">
    <div class="action-panel active" id="research-panel">
        <!-- Research actions -->
    </div>
    <div class="action-panel" id="selfcare-panel">
        <!-- Self-care actions -->
    </div>
    <div class="action-panel" id="admin-panel">
        <!-- Admin actions -->
    </div>
    <div class="action-panel" id="lab-panel">
        <!-- Lab/social actions -->
    </div>
</div>
```

**Implementation:**
- [ ] Categorize all actions by tab
- [ ] Build tab switching UI
- [ ] Persist active tab in state
- [ ] Add keyboard shortcuts (Alt+1/2/3/4)

**Validation:**
- [ ] Test: All actions appear in correct tab
- [ ] Test: Tab state persists across months
- [ ] Test: Keyboard navigation works

---

### 2.4 Enhanced Tooltips

**Stat Tooltips:**

```javascript
// Tooltip content generator
getStatTooltip(statName) {
    const tooltips = {
        stress: {
            title: 'Stress',
            affects: [
                'Research speed decreases above 70',
                'Burnout risk increases above 80'
            ],
            sources: [
                'Deadlines (+10)',
                'Paper rejection (+15)',
                'Funding pressure (+5/month)'
            ],
            recovery: [
                'Take Break (-20)',
                'Vacation (-40)'
            ]
        },
        alignment: {
            title: 'Advisor Alignment',
            affects: [
                'Defense committee support',
                'Advisor intervention likelihood',
                'Conference recommendation letters'
            ],
            sources: [
                'Pitch sessions (+10)',
                'Following advisor suggestions (+5)',
                'Aggressive review responses (-15)'
            ],
            warning: 'Low alignment increases defense difficulty!'
        }
        // ... more stats
    };
    
    return tooltips[statName];
}
```

**HTML:**
```html
<div class="stat-card" 
     data-tooltip="true"
     data-tooltip-content="{{getStatTooltip('stress')}}">
    <div class="stat-label">😰 Stress</div>
    <div class="stat-value">{{stress}}</div>
</div>

<!-- Tooltip overlay -->
<div class="tooltip-overlay" style="display: none;">
    <div class="tooltip-content">
        <h4>{{tooltip.title}}</h4>
        <div class="tooltip-section">
            <strong>Affects:</strong>
            <ul>
                {{#each tooltip.affects}}
                <li>{{this}}</li>
                {{/each}}
            </ul>
        </div>
        <!-- ... more sections -->
    </div>
</div>
```

**Implementation:**
- [ ] Create tooltip content for all stats
- [ ] Implement hover/press event handlers
- [ ] Add mobile long-press support
- [ ] Style tooltip overlays

---

### 2.5 Seasonal Backgrounds

**TimeEngine Integration:**

```javascript
// In month advance
advanceMonth() {
    this.state.month++;
    if (this.state.month > 12) {
        this.state.month = 1;
        this.state.year++;
    }
    
    // Update season
    this.updateSeason();
}

updateSeason() {
    const month = this.state.month;
    let season;
    
    if (month >= 9 && month <= 11) season = 'autumn';
    else if (month >= 12 || month <= 2) season = 'winter';
    else if (month >= 3 && month <= 5) season = 'spring';
    else season = 'summer';
    
    if (season !== this.state.season) {
        this.updateState({ season });
        this.applySeasonalBackground(season);
    }
}

applySeasonalBackground(season) {
    const container = document.querySelector('.game-container');
    
    // Remove old season classes
    container.classList.remove('autumn', 'winter', 'spring', 'summer');
    
    // Add new season
    container.classList.add(season);
}
```

**CSS Animations:**
```css
/* Autumn: Falling leaves */
.game-container.autumn::before {
    content: '🍂';
    position: absolute;
    animation: fall-leaves 15s infinite linear;
}

@keyframes fall-leaves {
    0% { top: -50px; left: 10%; transform: rotate(0deg); }
    100% { top: 100%; left: 15%; transform: rotate(360deg); }
}

/* Winter: Snow */
.game-container.winter::before {
    content: '❄️';
    animation: fall-snow 10s infinite linear;
}

/* Spring: Cherry blossoms */
.game-container.spring {
    background: linear-gradient(to bottom, #ffeef8 0%, #ffffff 100%);
}

/* Summer: Clear sky */
.game-container.summer {
    background: linear-gradient(to bottom, #87CEEB 0%, #ffffff 100%);
}
```

**Implementation:**
- [ ] Add season tracking to state
- [ ] Create CSS animations for each season
- [ ] Trigger season change in `advanceMonth()`
- [ ] Add option to disable animations (accessibility)

---

### 2.6 Funding Crisis Indicators

**Teaching Mode Banner:**

```javascript
// In UI renderer
renderFundingStatus() {
    if (this.state.funding <= 0 && this.state.teachingLoad) {
        return `
            <div class="crisis-banner teaching-mode">
                ⚠️ TEACHING MODE ACTIVE
                <div class="banner-detail">
                    Research speed: -50% until funding restored
                </div>
            </div>
        `;
    }
    return '';
}
```

**Emergency Grant Highlight:**

```css
/* Flash effect for Emergency Grant button */
.action-btn[data-action="emergencyGrant"] {
    animation: emergency-flash 1.5s infinite;
}

@keyframes emergency-flash {
    0%, 100% { background-color: #dc3545; box-shadow: 0 0 0 rgba(220, 53, 69, 0); }
    50% { background-color: #ff4555; box-shadow: 0 0 20px rgba(220, 53, 69, 0.8); }
}
```

**Implementation:**
- [ ] Add teaching mode banner to UI
- [ ] Add flash animation to Emergency Grant
- [ ] Trigger when `funding < 2` months
- [ ] Clear effects when funding restored

---

## Phase 3: Content Depth

### 3.1 Dr. Phantom Advisor Logic

**Availability System:**

```javascript
// Advisor archetypes
const ADVISOR_ARCHETYPES = {
    supportive: {
        availability: 0.9,  // 90% present
        interventionRate: 0.8,
        alignmentGainMultiplier: 1.0
    },
    phantom: {
        availability: 0.5,  // 50% present
        interventionRate: 0.3,
        alignmentGainMultiplier: 0.5,
        icon: '👻'
    },
    micromanager: {
        availability: 1.0,  // Always present
        interventionRate: 0.9,
        alignmentGainMultiplier: 1.2
    }
};

// Check advisor availability
checkAdvisorAvailable() {
    const archetype = ADVISOR_ARCHETYPES[this.state.advisorType];
    return this.rng.next() < archetype.availability;
}

// Apply advisor effects
pitchSession() {
    if (!this.checkAdvisorAvailable()) {
        this.logEvent('👻 Your advisor was unavailable for the meeting.');
        return;
    }
    
    const archetype = ADVISOR_ARCHETYPES[this.state.advisorType];
    const alignmentGain = 10 * archetype.alignmentGainMultiplier;
    
    this.updateState({
        alignment: this.state.alignment + alignmentGain,
        month: this.state.month + 1
    });
    
    this.logEvent(`🎓 Productive meeting with advisor (+${alignmentGain} alignment)`);
}
```

**Implementation:**
- [ ] Add advisor archetype selection at game start
- [ ] Implement availability checks
- [ ] Add ghost icon indicator when unavailable
- [ ] Log advisor absence explicitly

**Validation:**
- [ ] Test: Phantom advisor absent ~50% of time
- [ ] Test: Alignment gains reduced for Phantom
- [ ] Test: Ghost icon appears in HUD

---

### 3.2 TA Duty Event (2 days)

**Event Spec:**
- **Trigger:** Random, Years 2-3, 20% chance per year
- **Effects:** +6 months funding, +20 stress, locks "Take Break" for 1 month
- **Narrative:** Teaching heavy load for funding

```javascript
// In random event system
checkTADutyEvent() {
    if (this.state.year >= 2 && this.state.year <= 3) {
        if (this.rng.next() < 0.20 && !this.state.taDutyCompleted) {
            this.triggerTADuty();
        }
    }
}

triggerTADuty() {
    this.showModal({
        title: '📚 TA Assignment',
        message: 'You\'ve been assigned a heavy TA load. This will provide funding but increase stress and limit your break time for the next month.',
        priority: 'Major',
        actions: [
            {
                label: 'Accept (unavoidable)',
                callback: () => this.acceptTADuty()
            }
        ]
    });
}

acceptTADuty() {
    this.updateState({
        funding: this.state.funding + 6,
        stress: this.state.stress + 20,
        taBlocksBreak: this.state.month + 1,  // Lock break for 1 month
        taDutyCompleted: true
    });
    
    this.logEvent('📚 TA duties increase your workload significantly.');
}

// In Take Break action
takeBreak() {
    if (this.state.taBlocksBreak >= this.state.month) {
        this.showToast({
            message: 'You can\'t take a break this month due to TA responsibilities.',
            type: 'warning'
        });
        return;
    }
    
    // ... normal break logic
}
```

**Implementation:**
- [ ] Add TA event to random event pool
- [ ] Implement break lockout logic
- [ ] Add visual indicator when break is locked
- [ ] Write narrative variants

---

### 3.3 Marcus Collaboration

**Action Spec:**
- **Availability:** Requires 2+ Findings, appears Year 2+
- **Trade:** Give 1 Finding → Gain +10 Network, -1 month to Morgan's progress
- **Strategic:** Helps player but also helps rival

```javascript
// Add action
marcusCollaboration: {
    id: 'marcusCollaboration',
    name: 'Collaborate with Marcus',
    category: 'lab',
    available: () => {
        return this.state.year >= 2 && 
               this.state.findings >= 2 &&
               !this.state.marcusCollaborated;
    },
    execute: () => {
        this.updateState({
            findings: this.state.findings - 1,
            network: this.state.network + 10,
            morganProgress: Math.max(0, this.state.morganProgress - 1),
            marcusCollaborated: true
        });
        
        this.logEvent('🤝 Collaboration with Marcus was productive (+10 Network). ' +
                     'Your shared insights also helped Morgan.');
    }
}
```

**Implementation:**
- [ ] Add Marcus collaboration action
- [ ] Update Morgan's progress system
- [ ] Add one-time flag
- [ ] Write dialogue variants

---

### 3.4 Conference Rebalance

**Three Distinct Archetypes:**

```javascript
const CONFERENCE_OPTIONS = {
    poster: {
        archetype: 'Safe',
        successRate: 0.9,
        effects: {
            onSuccess: {
                alignment: 5,
                network: 3,
                morale: 5
            },
            onFailure: {
                morale: -2
            }
        },
        description: 'Safe visibility. Low risk, steady progress.',
        previewText: 'Poster sessions are low-pressure and build steady connections.'
    },
    
    talk: {
        archetype: 'Risky',
        successRate: 0.6,
        effects: {
            onSuccess: {
                alignment: 15,
                network: 10,
                morale: 10
            },
            onFailure: {
                morale: -15,
                stress: 20
            }
        },
        description: 'High-stakes presentation. Big rewards or embarrassment.',
        previewText: 'Talks can make your reputation, but a poor performance is costly.'
    },
    
    network: {
        archetype: 'Tempo',
        successRate: 1.0,  // Always succeeds
        effects: {
            onSuccess: {
                network: 15,
                alignment: 0
            }
        },
        cost: {
            opportunityCost: 'No research progress this month'
        },
        description: 'Pure networking. Immediate connections, no research.',
        previewText: 'Spend the conference making connections instead of presenting.'
    }
};

// Conference choice handler
selectConferenceOption(conferenceId, option) {
    const config = CONFERENCE_OPTIONS[option];
    
    // Show preview before final selection
    this.showModal({
        title: `Conference: ${option}`,
        message: config.previewText,
        priority: 'Major',
        actions: [
            {
                label: 'Confirm',
                callback: () => this.executeConferenceChoice(conferenceId, option, config)
            },
            {
                label: 'Cancel',
                callback: () => {}
            }
        ]
    });
}

executeConferenceChoice(conferenceId, option, config) {
    const success = this.rng.next() < config.successRate;
    const effects = success ? config.effects.onSuccess : config.effects.onFailure;
    
    // Apply effects
    this.updateState(effects);
    
    // Lockout for 2 months
    this.updateState({
        conferenceLockout: this.state.month + 2,
        [`conference_${conferenceId}_attended`]: true
    });
    
    // Log outcome
    const outcomeMsg = success ? 
        `🎉 ${option} was successful!` : 
        `😰 ${option} didn't go as planned.`;
    this.logEvent(outcomeMsg);
}
```

**Implementation:**
- [ ] Define conference option configs
- [ ] Add preview modal before selection
- [ ] Implement 2-month hard lockout
- [ ] Lock remaining options after one chosen
- [ ] Update UI to show lockout timer

**Validation:**
- [ ] Test: Can only choose one option per conference
- [ ] Test: 2-month lockout prevents overlap
- [ ] Test: All three archetypes feel distinct

---

### 3.5 Review Response Mechanics (2 days)

**Three Responses:**

```javascript
const REVIEW_RESPONSES = {
    polite: {
        name: 'Polite Revision',
        effect: {
            acceptanceChance: +0.15,
            timeDelay: +2  // 2 extra months
        },
        preview: 'Carefully address all reviewer concerns. Higher acceptance, but slower.',
        tradeoff: 'Time for acceptance'
    },
    
    aggressive: {
        name: 'Aggressive Rebuttal',
        effect: {
            timeDelay: -1,  // 1 month faster
            alignment: -15,
            acceptanceChance: -0.05
        },
        preview: 'Push back on unfair criticisms. Faster, but may annoy advisor.',
        tradeoff: 'Speed for alignment'
    },
    
    delay: {
        name: 'Request Extension',
        effect: {
            stress: -10,
            timeDelay: +3,
            momentum: -1  // Hidden penalty
        },
        preview: 'Ask for more time to revise. Reduces stress but loses momentum.',
        tradeoff: 'Stress for momentum'
    }
};

// Review response action
respondToReview(paperId, responseType) {
    const paper = this.state.papers.find(p => p.id === paperId);
    const response = REVIEW_RESPONSES[responseType];
    
    // Show preview
    this.showModal({
        title: `Review Response: ${response.name}`,
        message: response.preview,
        detail: `Tradeoff: ${response.tradeoff}`,
        priority: 'Major',
        actions: [
            {
                label: 'Confirm',
                callback: () => {
                    this.applyReviewResponse(paper, response);
                }
            },
            {
                label: 'Choose Different Response',
                callback: () => {}
            }
        ]
    });
}
```

**Implementation:**
- [ ] Add review response configs
- [ ] Show preview modal with tradeoff
- [ ] Apply effects to paper timeline
- [ ] Track alignment changes
- [ ] Add to action panel when paper status = `feedback_received`

---

### 3.6 Morgan Rival Progress Bar

**Visual Indicator:**

```javascript
// In UI renderer
renderRivalProgress() {
    const morganProgress = this.state.morganProgress || 0;
    const morganPapers = this.state.morganPapers || 0;
    
    return `
        <div class="rival-tracker">
            <div class="rival-header">
                <span class="rival-name">Morgan (Rival)</span>
                <span class="rival-papers">${morganPapers} papers</span>
            </div>
            <div class="rival-progress-bar">
                <div class="rival-progress-fill" 
                     style="width: ${morganProgress}%"
                     data-progress="${morganProgress}">
                </div>
            </div>
            <div class="rival-status">
                ${this.getMorganStatusText(morganProgress)}
            </div>
        </div>
    `;
}

getMorganStatusText(progress) {
    if (progress < 30) return 'Morgan is struggling';
    if (progress < 60) return 'Morgan is making steady progress';
    if (progress < 90) return 'Morgan is ahead of schedule';
    return '⚠️ Morgan is about to publish!';
}

// Update Morgan's progress monthly
updateMorganProgress() {
    let gain = 1 + (this.rng.next() * 2);  // 1-3% per month
    
    // Check if Morgan publishes
    if (this.state.morganProgress >= 100) {
        this.state.morganProgress = 0;
        this.state.morganPapers++;
        
        this.logEvent('📰 Morgan published a paper!');
        
        // Morale hit if Morgan ahead
        if (this.state.morganPapers > this.state.papers.length) {
            this.updateState({ morale: this.state.morale - 5 });
        }
    }
    
    this.updateState({
        morganProgress: Math.min(100, this.state.morganProgress + gain)
    });
}
```

**Sabotage Action:**

```javascript
sabotageRival: {
    id: 'sabotageRival',
    name: 'Interfere with Morgan',
    category: 'lab',
    available: () => {
        return this.state.network >= 20 && 
               !this.state.sabotageUsed;
    },
    cost: { network: -20 },
    execute: () => {
        this.updateState({
            morganProgress: Math.max(0, this.state.morganProgress - 30),
            sabotageUsed: true,
            alignment: this.state.alignment - 5  // Advisor disapproves
        });
        
        this.logEvent('⚠️ You interfered with Morgan\'s project. This may have consequences...');
    }
}
```

**Implementation:**
- [ ] Add Morgan progress tracking
- [ ] Create progress bar UI component
- [ ] Update Morgan monthly
- [ ] Add sabotage action
- [ ] Write rivalry event narratives

---

## Phase 4: Endgame & V3.0 Features

### 4.1 Defense Preparation Phase

**1-2 Month Prep Window:**

```javascript
// Trigger defense prep
startDefensePrep() {
    if (!GRADUATION_CONTRACT.defenseUnlocked()) {
        this.showToast({
            message: 'Not ready to defend yet!',
            type: 'warning'
        });
        return;
    }
    
    this.updateState({
        uiMode: 'DEFENSE_PREP',
        defenseMonthsRemaining: 2
    });
    
    this.logEvent('🎓 Defense preparation phase begins. Use these months wisely.');
}

// Defense prep actions
const DEFENSE_PREP_ACTIONS = {
    rehearsal: {
        name: 'Rehearse Defense',
        effect: {
            defensePresentation: +15,
            stress: +5
        },
        description: 'Practice your presentation skills'
    },
    
    reviseThesis: {
        name: 'Polish Thesis',
        effect: {
            defenseThesisQuality: +10
        },
        description: 'Final improvements to thesis quality'
    },
    
    meetCommittee: {
        name: 'Meet Committee Members',
        effect: {
            defenseCommittee: +10,
            network: +5
        },
        description: 'Build rapport with committee'
    }
};

// Auto-advance to defense after prep
checkDefenseStart() {
    if (this.state.uiMode === 'DEFENSE_PREP') {
        this.state.defenseMonthsRemaining--;
        
        if (this.state.defenseMonthsRemaining <= 0) {
            this.startDefense();
        }
    }
}
```

**Implementation:**
- [ ] Add defense prep mode to UI
- [ ] Create prep actions
- [ ] Add countdown timer
- [ ] Auto-transition to defense

---

### 4.2 Career Epilogue Resolver

**Three Career Paths:**

```javascript
determineCareerPath() {
    const score = this.calculateDefenseScore();
    const papers = this.state.papers.length;
    const network = this.state.network;
    const alignment = this.state.alignment;
    
    // Tenure-Track: High quality, good advisor relationship
    if (papers >= 3 && alignment >= 60 && score >= 75) {
        return {
            path: 'tenure_track',
            title: 'Assistant Professor',
            description: 'You secured a tenure-track position at a research university. Your strong publication record and advisor support made you a competitive candidate.',
            icon: '👨‍🏫'
        };
    }
    
    // Industry: High network, moderate quality
    if (network >= 25 && score >= 60) {
        return {
            path: 'industry',
            title: 'Research Scientist (Industry)',
            description: 'Your strong professional network led to a well-paid industry position. You\'ll apply your expertise to practical problems.',
            icon: '💼'
        };
    }
    
    // Research Scientist: Balanced stats
    if (papers >= 2 && network >= 15 && score >= 55) {
        return {
            path: 'research_scientist',
            title: 'Research Scientist',
            description: 'You joined a research institute where you can continue your academic work without teaching responsibilities.',
            icon: '🔬'
        };
    }
    
    // Default: Adjunct/Postdoc
    return {
        path: 'postdoc',
        title: 'Postdoctoral Researcher',
        description: 'You\'ll continue as a postdoc, building your publication record before applying for permanent positions.',
        icon: '📚'
    };
}

// Show epilogue after defense
showEpilogue() {
    const career = this.determineCareerPath();
    
    this.showModal({
        title: '🎓 Your Journey Concludes',
        content: `
            <div class="epilogue-card">
                <div class="career-icon">${career.icon}</div>
                <h2>${career.title}</h2>
                <p>${career.description}</p>
                
                <div class="final-stats">
                    <div>Papers Published: ${this.state.papers.length}</div>
                    <div>Network Score: ${this.state.network}</div>
                    <div>Defense Score: ${this.calculateDefenseScore()}/100</div>
                    <div>Time to Degree: ${this.state.totalMonths} months</div>
                </div>
            </div>
        `,
        priority: 'Emergency',
        actions: [
            {
                label: '🎲 Play Again',
                callback: () => this.resetGame()
            }
        ]
    });
}
```

**Implementation:**
- [ ] Create career path logic
- [ ] Design epilogue modal
- [ ] Add final stats summary
- [ ] Connect to defense completion

---

### 4.3 Grant Mini-Game

**3-Stage Grant Process:**

```javascript
// Replace simple Emergency Grant
startGrantApplication() {
    this.updateState({
        grantStage: 1,
        grantAbstractQuality: 0,
        grantBudgetQuality: 0,
        grantImpactQuality: 0
    });
    
    this.showModal({
        title: '📝 Grant Application',
        message: 'Writing a grant proposal requires careful preparation across three sections.',
        priority: 'Major'
    });
}

// Stage 1: Abstract
const GRANT_STAGE_1 = {
    name: 'Write Abstract',
    requirements: {
        ideas: 2
    },
    action: () => {
        const quality = this.state.ideas.length * 10 + (this.rng.next() * 20);
        
        this.updateState({
            grantAbstractQuality: quality,
            ideas: this.state.ideas.slice(0, -2),  // Consume 2 ideas
            grantStage: 2
        });
    }
};

// Stage 2: Budget
const GRANT_STAGE_2 = {
    name: 'Prepare Budget',
    requirements: {
        findings: 1
    },
    action: () => {
        const quality = this.state.findings * 15 + (this.rng.next() * 15);
        
        this.updateState({
            grantBudgetQuality: quality,
            findings: this.state.findings - 1,
            grantStage: 3
        });
    }
};

// Stage 3: Impact Statement
const GRANT_STAGE_3 = {
    name: 'Impact Statement',
    requirements: {
        network: 15
    },
    action: () => {
        const baseQuality = Math.min(100, this.state.network * 2);
        const quality = baseQuality + (this.rng.next() * 20) - 10;
        
        this.updateState({
            grantImpactQuality: quality,
            grantStage: 4  // Ready to submit
        });
    }
};

// Calculate grant success
calculateGrantSuccess() {
    const totalQuality = (
        this.state.grantAbstractQuality * 0.4 +
        this.state.grantBudgetQuality * 0.3 +
        this.state.grantImpactQuality * 0.3
    );
    
    return {
        success: totalQuality >= 60,
        quality: totalQuality
    };
}

// Submit grant
submitGrant() {
    const result = this.calculateGrantSuccess();
    
    if (result.success) {
        this.updateState({
            funding: 12,
            teachingLoad: false
        });
        
        this.logEvent('🎉 Grant funded! 12 months of funding secured.');
    } else {
        this.updateState({
            funding: 3,  // Partial funding
            statuses: this.state.statuses.add('demoralized')
        });
        
        this.logEvent('😞 Grant partially funded. Keep trying.');
    }
    
    // Reset grant state
    this.updateState({
        grantStage: 0,
        grantAbstractQuality: 0,
        grantBudgetQuality: 0,
        grantImpactQuality: 0
    });
}
```

**Implementation:**
- [ ] Build 3-stage grant UI
- [ ] Create stage progression logic
- [ ] Add quality calculations
- [ ] Implement "Demoralized" status effect
- [ ] Write stage-specific narratives

---

### 4.4 Validation Suite

**100-Sim Automated Test:**

```javascript
// tests/validation.test.js
class ValidationSuite {
    constructor() {
        this.runs = [];
        this.targetWinRate = [0.35, 0.45];  // 35-45%
        this.targetDuration = [60, 90];     // 60-90 months
        this.targetMorale = 40;             // >40% at end
    }
    
    runSimulations(count = 100) {
        console.log(`Running ${count} validation simulations...`);
        
        for (let i = 0; i < count; i++) {
            const result = this.simulateGame();
            this.runs.push(result);
            
            if (i % 10 === 0) {
                console.log(`Progress: ${i}/${count}`);
            }
        }
        
        this.analyzeResults();
    }
    
    simulateGame() {
        const engine = new GameEngine({ seed: Date.now() + Math.random() });
        engine.initGame();
        
        let monthsElapsed = 0;
        const maxMonths = 120;  // 10 years max
        
        while (monthsElapsed < maxMonths && !engine.isGameOver()) {
            // Simple AI: Choose random valid action
            const actions = engine.getAvailableActions();
            const action = actions[Math.floor(Math.random() * actions.length)];
            
            engine.executeAction(action.id);
            engine.advanceMonth();
            monthsElapsed++;
        }
        
        return {
            graduated: engine.state.graduated,
            monthsElapsed: monthsElapsed,
            finalMorale: engine.state.morale,
            papersPublished: engine.state.papers.length,
            defenseScore: engine.calculateDefenseScore()
        };
    }
    
    analyzeResults() {
        const graduated = this.runs.filter(r => r.graduated);
        const winRate = graduated.length / this.runs.length;
        
        const durations = graduated.map(r => r.monthsElapsed);
        const avgDuration = durations.reduce((a, b) => a + b, 0) / durations.length;
        
        const morales = graduated.map(r => r.finalMorale);
        const avgMorale = morales.reduce((a, b) => a + b, 0) / morales.length;
        
        console.log('=== VALIDATION RESULTS ===');
        console.log(`Win Rate: ${(winRate * 100).toFixed(1)}% (target: ${this.targetWinRate[0] * 100}-${this.targetWinRate[1] * 100}%)`);
        console.log(`Avg Duration: ${avgDuration.toFixed(1)} months (target: ${this.targetDuration[0]}-${this.targetDuration[1]})`);
        console.log(`Avg Final Morale: ${avgMorale.toFixed(1)} (target: >${this.targetMorale})`);
        
        // Check if targets met
        const passed = 
            winRate >= this.targetWinRate[0] && winRate <= this.targetWinRate[1] &&
            avgDuration >= this.targetDuration[0] && avgDuration <= this.targetDuration[1] &&
            avgMorale > this.targetMorale;
        
        if (passed) {
            console.log('✅ VALIDATION PASSED');
        } else {
            console.log('❌ VALIDATION FAILED - Rebalancing needed');
        }
        
        return { winRate, avgDuration, avgMorale, passed };
    }
}

// Run validation
const suite = new ValidationSuite();
suite.runSimulations(100);
```

**Implementation:**
- [ ] Create `ValidationSuite` class
- [ ] Implement simple AI for simulation
- [ ] Add statistical analysis
- [ ] Document results in `validation-report.md`
- [ ] Iterate balance until targets met

---

## Phase 5: Launch & Rollback Plan

### 5.1 V2.55 Fallback Mechanism

**URL Parameter Rollback:**

```javascript
// In index.html initialization
(function initGradQuest() {
    const urlParams = new URLSearchParams(window.location.search);
    const version = urlParams.get('version');
    
    if (version === '2.55') {
        console.log('Loading V2.55 fallback mode...');
        loadV255();
    } else {
        console.log('Loading V3.0...');
        loadV3();
    }
})();

function loadV255() {
    // Load V2.55 code from separate file
    const script = document.createElement('script');
    script.src = './gradquest-v2.55.js';
    document.body.appendChild(script);
    
    // Show version indicator
    document.getElementById('version-badge').textContent = 'V2.55 (Fallback)';
}

function loadV3() {
    // Load V3.0 code (default)
    const script = document.createElement('script');
    script.src = './gradquest-v3.0.js';
    document.body.appendChild(script);
    
    document.getElementById('version-badge').textContent = 'V3.0 Gold';
}
```

**Implementation:**
- [ ] Extract current V2.55 code to `gradquest-v2.55.js`
- [ ] Add version loading logic
- [ ] Test fallback via `?version=2.55` URL param
- [ ] Add version badge to UI

---

### 5.2 Performance Optimization

**Key Optimizations:**
1. Lazy-load seasonal backgrounds
2. Debounce UI updates
3. Cache DOM queries
4. Minimize reflows

```javascript
// Debounced render
let renderTimeout;
function scheduleRender() {
    if (renderTimeout) clearTimeout(renderTimeout);
    
    renderTimeout = setTimeout(() => {
        render();
    }, 16);  // ~60fps
}

// Cache DOM queries
const DOM_CACHE = {};
function $(selector) {
    if (!DOM_CACHE[selector]) {
        DOM_CACHE[selector] = document.querySelector(selector);
    }
    return DOM_CACHE[selector];
}

// Lazy-load images
function loadSeasonalAssets(season) {
    const img = new Image();
    img.src = `/assets/backgrounds/${season}.jpg`;
    img.onload = () => {
        $('game-container').style.backgroundImage = `url(${img.src})`;
    };
}
```

**Implementation:**
- [ ] Add render debouncing
- [ ] Cache frequent DOM queries
- [ ] Lazy-load backgrounds
- [ ] Profile with Chrome DevTools

---

### 5.3 Final Bug Sweep

**Critical Checks:**
- [ ] All 6 regression tests pass
- [ ] Defense state clears correctly
- [ ] No modal collisions
- [ ] Conference lockout enforced
- [ ] Save/load preserves all state
- [ ] Mobile tabs work on iOS/Android
- [ ] Keyboard shortcuts functional
- [ ] ARIA labels present

**Browser Testing:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

---

### 5.4 Launch Checklist

**Pre-Launch:**
- [ ] All phases complete
- [ ] Validation suite passes
- [ ] Documentation updated (AGENTS.md, CURSORRULES, README)
- [ ] V2.55 fallback tested
- [ ] Performance benchmarks acceptable
- [ ] Browser compatibility verified

**Launch:**
- [ ] Deploy V3.0 to GitHub Pages
- [ ] Update version badge
- [ ] Post changelog
- [ ] Monitor for bug reports

**Post-Launch:**
- [ ] Collect user feedback
- [ ] Monitor analytics (if added)
- [ ] Plan V3.1 patches

---

## Summary Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 0**  | Graduation contract, regression tests, event resolver |
| **Phase 1**  | Balance fixes, exhaustion tuning, momentum actions |
| **Phase 2**  | Field theming, visual polish, 4-tab UI, tooltips |
| **Phase 3**  | Advisor logic, events, conferences, Morgan system |
| **Phase 4**  | Defense prep, epilogues, grant mini-game, validation |
| **Phase 5**  | Rollback plan, optimization, launch |
| **TOTAL**  | **V3.0 Gold Release** |

**Critical Path:** Phase 0 → Phase 1 → Phase 4 (validation) → Phase 5  
**Parallel Work:** Phases 2 & 3 can overlap with Phase 1

**Success Criteria:**
✅ All regression tests pass  
✅ Validation suite: 35-45% win rate, 60-90 month avg, >40% morale  
✅ V2.55 fallback functional  
✅ Mobile UX smooth on iOS/Android  
✅ All documentation synchronized