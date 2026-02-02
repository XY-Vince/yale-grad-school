# 🎓 GradQuest - Cursor IDE Rules

> **Version**: 2.55 🎯 Focused Mode | **Architecture**: Static JavaScript (GitHub Pages)  
> **Philosophy**: *"Every punishment must unlock a new form of agency."*

## Project Context

**GradQuest** is a strategic PhD life simulator running entirely in the browser.
- **Platform**: Pure static JavaScript on GitHub Pages
- **State**: Immutable updates via object spread pattern
- **Storage**: LocalStorage with JSON serialization
- **Mobile-First**: 4-tab navigation (Status / Actions / Lab / Next)
- **Critical Rule**: Every crisis must have recovery action (Slog Check)

## Code Style - JavaScript

### State Immutability (Mandatory)

All state changes use functional updates. Never mutate directly.

```javascript
// ✅ Good: updateState pattern
class GameEngine {
    updateState(changes) {
        this.state = { ...this.state, ...changes };
        if (Object.keys(changes).length <= 3) {
            console.log('[STATE]', changes);
        }
    }
    
    // Usage
    takeBreak() {
        this.updateState({ 
            morale: Math.min(100, this.state.morale + 15),
            burnout: Math.max(0, this.state.burnout - 20)
        });
    }
}

// ❌ Forbidden: Direct mutation
// this.state.morale += 15;
```

### ES6+ Mandatory Features

```javascript
// ✅ Good: const/let, arrow functions, template literals, destructuring
const updateMorale = (current, delta) => {
    const newMorale = Math.max(0, Math.min(100, current + delta));
    return newMorale;
};

const message = `Morale updated to ${newMorale}`;

// ✅ Good: Array/Object methods
const activeStatuses = Object.values(this.state.statuses)
    .filter(s => s.active)
    .map(s => s.name);

// ❌ Bad: var, for loops, manual iteration
// var i; for (i=0; i<arr.length; i++) { ... }
```

### Module Organization (Single File)

Since GradQuest uses single-file architecture:

```javascript
// ✅ Good: Organized by feature in index.html
const GameEngine = {
    // ===========================================
    // STATE MANAGEMENT
    // ===========================================
    state: null,
    
    initState() {
        return {
            morale: 50,
            funding: 36,
            items: {},
            statuses: new Set(),
            // ...
        };
    },
    
    updateState(changes) {
        this.state = { ...this.state, ...changes };
    },
    
    // ===========================================
    // ACTIONS
    // ===========================================
    actions: {
        readPapers() { /* ... */ },
        workOnIdea() { /* ... */ },
        // ...
    },
    
    // ===========================================
    // UI TRANSFORMERS
    // ===========================================
    transformToUI() {
        return {
            morale: this.getMoraleDisplay(),
            actions: this.getAvailableActions(),
            warnings: this.getWarnings()
        };
    }
};
```

## Mobile-First UI Patterns

### 4-Tab Navigation

```javascript
// ✅ Good: Tab state management
class GameUI {
    constructor() {
        this.activeTab = 'status'; // status | actions | lab | next
    }
    
    switchTab(tabName) {
        // Hide all panels
        ['status', 'actions', 'lab', 'next'].forEach(tab => {
            document.getElementById(`${tab}-panel`).style.display = 'none';
            document.getElementById(`${tab}-tab`).classList.remove('active');
        });
        
        // Show selected
        document.getElementById(`${tabName}-panel`).style.display = 'block';
        document.getElementById(`${tabName}-tab`).classList.add('active');
        this.activeTab = tabName;
        
        // Mobile: Scroll to top on tab switch
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}
```

### Touch Targets & Responsive Design

```css
/* ✅ Good: Minimum touch targets */
.action-btn {
    min-height: 48px;
    min-width: 48px;
    padding: 12px 16px;
}

/* ✅ Good: Responsive grid */
.stats-bar {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 15px;
}

/* Mobile: Stack on narrow screens */
@media (max-width: 640px) {
    .stats-bar {
        grid-template-columns: 1fr;
    }
}
```

### Sticky Bottom Action Bar

```javascript
// ✅ Good: Actions always accessible
class GameUI {
    renderActionBar() {
        const availableActions = this.getAvailableActions();
        const actionBar = document.getElementById('action-bar');
        
        actionBar.innerHTML = availableActions.map(action => `
            <button class="action-btn" 
                    data-action="${action.id}"
                    aria-label="${action.desc}">
                ${action.icon} ${action.name}
            </button>
        `).join('');
        
        // Sticky positioning
        actionBar.style.position = 'sticky';
        actionBar.style.bottom = '0';
        actionBar.style.zIndex = '100';
    }
}
```

## Game Mechanics Implementation

### Conference Lockout (V2.55)

```javascript
// ✅ Good: Hard 2-month lock after conference choice
class GameEngine {
    selectConferenceOption(conferenceId, option) {
        // Apply choice
        this.applyConferenceEffect(conferenceId, option);
        
        // Lockout for 2 months
        const lockoutEnd = this.state.month + 2;
        this.updateState({
            conferenceLockout: lockoutEnd,
            [`conference_${conferenceId}_attended`]: true
        });
        
        // Remove from available actions
        this.removeAvailableAction(`conference_${conferenceId}`);
    }
    
    canAttendConference(conferenceId) {
        // Check year limit (2/year)
        const conferencesThisYear = this.getConferencesAttendedThisYear();
        if (conferencesThisYear >= 2) return false;
        
        // Check lockout
        if (this.state.conferenceLockout > this.state.month) return false;
        
        // Check if already attended
        if (this.state[`conference_${conferenceId}_attended`]) return false;
        
        return true;
    }
}
```

### Recovery Actions (Slog Check)

Every crisis must unlock agency:

```javascript
// ✅ Good: Recovery action unlocks automatically
class GameEngine {
    checkCrisisStates() {
        const available = [...this.state.availableActions];
        
        // Funding crisis
        if (this.state.funding <= 0 && !available.includes('emergency_grant')) {
            available.push('emergency_grant');
            this.showMessage('🚨 Funding exhausted! Emergency Grant available.');
        }
        
        // Morale crisis
        if (this.state.morale < 10 && !available.includes('medical_leave')) {
            available.push('medical_leave');
            this.showMessage('💔 Critical morale! Medical Leave available.');
        }
        
        // Burnout crisis
        if (this.state.burnout >= 60 && !available.includes('vacation')) {
            available.push('vacation');
            this.showMessage('🔥 High burnout! Vacation recommended.');
        }
        
        this.updateState({ availableActions: available });
    }
    
    // Recovery actions
    emergencyGrant() {
        this.updateState({
            funding: 12,
            teachingLoad: true,  // Permanent penalty
            availableActions: this.state.availableActions.filter(
                a => a !== 'emergency_grant'
            )
        });
    }
}
```

## LocalStorage & Save Management

### Save Format

```javascript
// ✅ Good: Versioned saves with metadata
save() {
    const saveData = {
        ...this.state,
        statuses: Array.from(this.state.statuses),
        version: '2.55',
        savedAt: new Date().toISOString(),
        checksum: this.generateChecksum(this.state)  // Integrity check
    };
    
    try {
        localStorage.setItem('gradquest_save', JSON.stringify(saveData));
        this.showSaveToast();
    } catch (e) {
        console.error('Save failed:', e);
        this.showError('Save failed - storage may be full');
    }
}
```

### Load with Validation

```javascript
// ✅ Good: Validate before loading
load() {
    try {
        const data = localStorage.getItem('gradquest_save');
        if (!data) {
            this.showError('No saved game found!');
            return false;
        }
        
        const saveData = JSON.parse(data);
        
        // Validate version
        if (!saveData.version) {
            console.warn('Legacy save detected');
        }
        
        // Validate required fields
        const required = ['morale', 'funding', 'month', 'year'];
        for (const field of required) {
            if (!(field in saveData)) {
                throw new Error(`Corrupted save: missing ${field}`);
            }
        }
        
        // Restore state
        this.state = {
            ...saveData,
            statuses: new Set(saveData.statuses || [])
        };
        
        return true;
    } catch (e) {
        console.error('Load failed:', e);
        this.showError(`Failed to load: ${e.message}`);
        return false;
    }
}
```

## V2.55+ Architecture Improvements

### Central Event Resolver (V2.55)

Prevents modal collisions and zombie events. All events route through here.

```javascript
// ===========================================
// SYSTEM: Event Resolution
// Prevents modal spam and enforces priority
// ===========================================
class EventResolver {
    constructor() {
        this.eventQueue = [];
        this.processedThisTick = new Set();
        this.maxModalsPerTurn = 1;
        this.shownThisTurn = 0;
    }

    // Priority: Emergency (100) > Major (50) > Minor (10)
    priorityWeight(event) {
        const weights = { Emergency: 100, Major: 50, Minor: 10 };
        return weights[event.priority] || 0;
    }

    // Called once per game tick
    resolveTick(state) {
        // Collect pending events
        const pending = this.collectPendingEvents(state);
        
        // Sort by priority
        pending.sort((a, b) => this.priorityWeight(b) - this.priorityWeight(a));
        
        // Process highest priority only
        if (pending.length > 0) {
            this.processEvent(pending[0], state);
        }
        
        // Reset for next tick
        this.shownThisTurn = 0;
        this.processedThisTick.clear();
    }

    processEvent(event, state) {
        if (this.processedThisTick.has(event.id)) return;
        
        // 1 modal max per turn
        if (this.shownThisTurn >= this.maxModalsPerTurn) {
            console.log(`[EventResolver] Queued: ${event.id}`);
            return;
        }
        
        // Process based on owner
        console.log(`[EventResolver] ${event.id} (${event.owner}, ${event.priority})`);
        this.shownThisTurn++;
        this.processedThisTick.add(event.id);
    }
}
```

### Hidden Metrics Manifest (V2.55)

Every hidden metric must have documented source/sink/decay. See AGENTS.md for full manifest.

**Required Documentation per Metric:**
```javascript
const HIDDEN_METRICS = {
    advisorTension: {
        source: 'Aggressive player actions',
        sink: 'Advisor interventions, defense skepticism', 
        decay: '-10 per month if no aggressive actions',
        surfaced: 'indirect',  // Via advisor dialog tone
        reset: 'On defense completion'
    },
    strategicAlignment: {
        source: 'Research focus choices',
        sink: 'Conference success, committee support',
        decay: '-5 per month if neglected',
        surfaced: 'indirect',
        reset: 'Never'
    }
    // Rule: Surface to UI/log or remove
};
```

## V3.0 Technical Implementation

### State Migration (V2.55 → V3.0)

```javascript
// ✅ Good: Graceful migration with defaults
migrateSaveV2ToV3(saveData) {
    const version = saveData.version || '2.0';
    
    if (version.startsWith('3')) {
        return saveData;  // Already current
    }
    
    console.log(`Migrating save from ${version} to 3.0...`);
    
    const migrated = { ...saveData };
    
    // V3.0 Defense Minigame fields
    migrated.defenseThesisQuality = saveData.defenseThesisQuality || 0;
    migrated.defensePresentation = saveData.defensePresentation || 0;
    migrated.defenseCommittee = saveData.defenseCommittee || 0;
    migrated.defenseTurn = saveData.defenseTurn || 0;
    migrated.defenseHistory = saveData.defenseHistory || [];
    
    // V3.0 Choice tracking (for narrative endings)
    migrated.choiceHistory = saveData.choiceHistory || {
        ethicalDecisions: [],
        mentorshipInteractions: [],
        collaborationCount: 0,
        conferenceChoices: []
    };
    
    // V3.0 Audio settings
    migrated.audioSettings = saveData.audioSettings || {
        sfxEnabled: true,
        ambientEnabled: true,
        volume: 0.8
    };
    
    // Update version
    migrated.version = '3.0';
    migrated.migratedFrom = version;
    
    return migrated;
}

// Usage in load()
load() {
    const saveData = JSON.parse(localStorage.getItem('gradquest_save'));
    
    // Auto-migrate if needed
    if (saveData.version && saveData.version.startsWith('2')) {
        const migrated = this.migrateSaveV2ToV3(saveData);
        this.state = {
            ...migrated,
            statuses: new Set(migrated.statuses)
        };
    } else {
        this.state = saveData;
    }
}
```

### Defense Minigame Scoring (Weighted)

**Authoritative weights**:
- Thesis Quality: 50%
- Presentation Skill: 25%
- Committee Support: 25%

```javascript
// ✅ Good: Weighted defense scoring
calculateDefenseScore() {
    const weights = {
        thesis: 0.50,      // 50% - Primary factor
        presentation: 0.25, // 25%
        committee: 0.25    // 25%
    };
    
    const score = (
        this.state.defenseThesisQuality * weights.thesis +
        this.state.defensePresentation * weights.presentation +
        this.state.defenseCommittee * weights.committee
    );
    
    return Math.min(100, Math.max(0, score));
}

determineEndingBranch(defenseScore) {
    // Base ending from defense score
    let ending;
    if (defenseScore >= 85) ending = 'excellent';
    else if (defenseScore >= 70) ending = 'good';
    else if (defenseScore >= 55) ending = 'acceptable';
    else if (defenseScore >= 40) ending = 'poor';
    else ending = 'disaster';
    
    // Modify by choice history (tracked throughout game)
    const history = this.state.choiceHistory;
    
    if (history.ethicalDecisions.filter(e => !e.ethical).length > 2) {
        ending = this.downgradeEnding(ending);  // Penalty
    }
    
    if (history.mentorshipScore > 80) {
        ending = this.upgradeEnding(ending);  // Bonus
    }
    
    return ending;
}
```

### Audio Trigger System (V3.0)

```javascript
// ✅ Good: SFX tokens via transformer
class GameAudio {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.sfxCache = new Map();
    }
    
    // Map actions to sounds
    getSfxToken(actionId) {
        const sfxMap = {
            'submit_paper': { sound: 'paper_submit', volume: 0.8 },
            'paper_accepted': { sound: 'success_fanfare', volume: 0.9, priority: 2 },
            'funding_crisis': { sound: 'alert_tone', volume: 1.0, priority: 3 },
            'defense_start': { sound: 'fanfare', volume: 0.9, priority: 2 },
            'complete_figures': { sound: 'success_chime', volume: 0.6 }
        };
        
        return sfxMap[actionId] || null;
    }
    
    // Play sound
    playSfx(token) {
        if (!this.state.audioSettings.sfxEnabled) return;
        
        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = token.volume * this.state.audioSettings.volume;
        
        // Load and play sound...
    }
}

// In UI transformer
transformToUI() {
    const lastAction = this.state.lastAction;
    
    return {
        // ... other fields ...
        sfxToken: this.audio.getSfxToken(lastAction),
        ambientSound: this.getAmbientForMode(this.state.uiMode)
    };
}
```

## Accessibility Requirements

### ARIA Labels (Mandatory)

```javascript
// ✅ Good: All non-text elements labeled
renderStatCard(stat) {
    return `
        <div class="stat-card" role="region" aria-label="${stat.name} statistic">
            <div class="stat-label">${stat.name}</div>
            <div class="stat-value" aria-live="polite">
                ${stat.icon} ${stat.value}
            </div>
            ${stat.warning ? `
                <div class="stat-warning" role="alert">
                    ${stat.warning}
                </div>
            ` : ''}
        </div>
    `;
}

// Emoji with ARIA labels
const EVENT_ICONS = {
    'funding_crisis': { icon: '🚨', label: 'Critical funding alert' },
    'paper_accepted': { icon: '🎉', label: 'Paper accepted celebration' },
    'advisor_angry': { icon: '😤', label: 'Advisor frustrated' }
};
```

### Keyboard Navigation

```javascript
// ✅ Good: Keyboard accessible actions
document.addEventListener('keydown', (e) => {
    // Number keys 1-4 for tabs
    if (e.key >= '1' && e.key <= '4') {
        const tabs = ['status', 'actions', 'lab', 'next'];
        this.switchTab(tabs[parseInt(e.key) - 1]);
    }
    
    // Space/Enter to activate focused action
    if (e.key === 'Enter' || e.key === ' ') {
        const focused = document.activeElement;
        if (focused.classList.contains('action-btn')) {
            focused.click();
        }
    }
});
```

## Testing Patterns

### State Snapshot Tests

```javascript
// ✅ Good: Test state transitions
function testCrisisRecovery() {
    // Setup crisis state
    const state = createTestState({ funding: 0, morale: 20 });
    const engine = new GameEngine(state);
    
    // Trigger crisis check
    engine.checkCrisisStates();
    
    // Verify recovery action unlocked
    assert(engine.state.availableActions.includes('emergency_grant'),
        'Funding crisis must unlock emergency grant');
}

function testConferenceLockout() {
    const engine = new GameEngine();
    engine.selectConferenceOption('neuro_conf_2025', 'poster');
    
    // Verify lockout
    assert(engine.state.conferenceLockout === engine.state.month + 2,
        'Conference lockout must be 2 months');
    assert(!engine.canAttendConference('neuro_conf_2025'),
        'Should not be able to attend same conference again');
}
```

### Playtest Metrics

```javascript
// ✅ Good: Track metrics during playtesting
class MetricsTracker {
    constructor() {
        this.runs = [];
    }
    
    recordRun(finalState) {
        this.runs.push({
            totalMonths: finalState.month + (finalState.year * 12),
            graduated: finalState.graduated,
            papersPublished: finalState.papers,
            inspirationCount: finalState.inspirationCount,
            ending: finalState.ending
        });
    }
    
    getStats() {
        const graduated = this.runs.filter(r => r.graduated);
        const completionTimes = graduated.map(r => r.totalMonths);
        
        return {
            medianCompletion: median(completionTimes),
            avgInspirations: mean(this.runs.map(r => r.inspirationCount)),
            graduationRate: graduated.length / this.runs.length
        };
    }
}
```

## Critical Reminders

- ✅ **Immutability**: Always use `updateState()` with object spread
- ✅ **Slog Check**: Every crisis must have recovery action
- ✅ **Mobile-First**: 48px touch targets, 4-tab navigation
- ✅ **Conference Lock**: Hard 2-month lock after choice
- ✅ **ARIA Labels**: All non-text elements need labels
- ✅ **LocalStorage**: Version saves, handle corruption gracefully
- ✅ **Defense Weights**: Thesis 50%, Presentation 25%, Committee 25%
- ✅ **No LLM in Core**: Deterministic logic only (V3.0: AI for flavor text only)

---

*"Every punishment must unlock a new form of agency."* - GradQuest Engineering Standards
