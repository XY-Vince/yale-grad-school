# Conference Logic Comprehensive Review
## GradQuest V2.59.2 - Analysis Report

**Date:** 2026-02-11  
**File:** docs/index.html  
**Status:** 🚨 CRITICAL ISSUES FOUND

---

## 1. EXECUTIVE SUMMARY

The conference system has **4 critical bugs** causing user-reported issues:

1. **Conference gains immediately decayed** - Monthly morale decay cancels out conference benefits
2. **Direct state mutation** - Bypasses validation/logging architecture  
3. **Dead code** - `conferenceChoiceMade` flag never set
4. **Hidden metrics inconsistency** - Multiple tracking fields with unclear purposes

**Playtest Impact:** 0% win rate, 100% timeouts at 134 months (target: 60-75)

---

## 2. CONFERENCE ACTION FLOW

### Complete Call Chain:

```
User clicks conference action
    ↓
doAction('conf_poster'|'conf_talk'|'conf_network')
    ↓ (line 6250-6254)
switch case matches
    ↓
resolveConferenceChoice(id) called
    ↓ (line 3206-3303)
Direct state mutation: s.morale = ..., s.stress = ...
    ↓
Returns message string
    ↓
showMessage(msg) displays result (line 6296)
    ↓
advanceMonth() called (line 6297)
    ↓
Monthly morale decay applied (line 4673)
    ↓
updateUI() refreshes display
```

### The Problem:

**Conference gives +10 morale → decay takes -4 to -13 → net gain is minimal or negative**

User sees: "+10 morale" message, but UI shows little/no change because decay happened immediately after.

---

## 3. CRITICAL BUGS DETAILED

### BUG #1: Conference Gains Cancelled by Monthly Decay ⭐ HIGHEST PRIORITY

**Location:** `advanceMonth()` line 4673

**Issue:** 
```javascript
// Flow:
resolveConferenceChoice() {  // Conference gives +10 morale
    s.morale = Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 10);
}

advanceMonth() {
    // ... other processing ...
    this.updateState({ morale: Math.max(0, this.state.morale - decay) }, 'Wellness');
    // Decay is 4-13 points depending on statuses
}
```

**Impact:** 
- POSTER: +10 morale, -20 stress → After decay: +0 to +6 morale
- TALK (success): +20 morale → After decay: +7 to +16 morale  
- TALK (failure): -15 morale → After decay: -19 to -28 morale (DEVASTATING)
- NETWORK: +5 morale → After decay: -8 to +1 morale (OFTEN NEGATIVE!)

**Evidence:** Playtest shows avg lowest morale 22.4, 100% timeouts

**Fix Options:**
1. Apply conference effects AFTER monthly decay
2. Suppress decay in the month of conference attendance
3. Add decay immunity for conference month (`s.conferenceDecayImmunity = true`)

---

### BUG #2: Direct State Mutation (Architectural Violation)

**Location:** `resolveConferenceChoice()` lines 3221, 3222, 3247, 3256, 3257, 3269, 3270

**Issue:**
```javascript
// ❌ VIOLATES AGENTS.md pattern:
s.morale = Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 10);
s.stress = Math.max(0, (s.stress || 0) - 20);

// ✅ Should be:
this.updateState({ 
    morale: Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 10),
    stress: Math.max(0, (s.stress || 0) - 20)
}, 'Wellness');
```

**Impact:**
- Bypasses state ownership logging
- No validation warnings
- Telemetry misses these changes
- UI may not detect changes if using immutable comparison

**Count:** 39 direct `s.morale =` mutations, 7 direct `s.stress =` mutations in entire codebase

---

### BUG #3: conferenceChoiceMade Flag Never Set

**Location:** 
- Checked: Line 5155 (`if (s.conferenceChoiceMade)`)
- Never assigned: Search found no `s.conferenceChoiceMade = true`

**Issue:**
```javascript
// Line 5155 - checked but never true:
if (s.conferenceChoiceMade) {
    actions.push({ id: 'conf_status', name: `🎤 Conference - ${s.conferenceChoiceMade}`, disabled: true });
}
```

**Impact:** Dead code - intended to show "disabled" status after choosing, but never works

**Fix:** Either remove or implement:
```javascript
// In resolveConferenceChoice():
s.conferenceChoiceMade = choiceId;  // Set the flag

// In advanceMonth() or when conference ends:
s.conferenceChoiceMade = null;  // Clear when appropriate
```

---

### BUG #4: Conference State Management Confusion

**Multiple tracking fields with overlapping purposes:**

| Field | Purpose | Reset Timing |
|-------|---------|--------------|
| `conferencesThisYear` | Count for 2/year limit | Line 4643: reset on year change |
| `lastConferenceMonth` | Cooldown tracking | Set on conference, never reset |
| `conferenceCount` | Total attended (telemetry?) | Never reset |
| `conferenceChoices` | History array | Never cleared |
| `conferenceChoiceMade` | Current choice flag | NEVER SET (dead code) |

**Issues:**
- `conferenceCount` vs `conferencesThisYear` - which is authoritative?
- `lastConferenceMonth` persists across years (intentional?)
- No cleanup of `conferenceChoices` array (memory leak potential)

---

## 4. CONFERENCE EFFECT CALCULATIONS

### POSTER (conf_poster) - Line 3218

```javascript
s.peerNetwork = Math.min(GAME_CONSTANTS.MAX_NETWORK, (s.peerNetwork || 0) + Math.floor(conf.networkGain * 0.3));
s.morale = Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 10);
s.stress = Math.max(0, (s.stress || 0) - 20);
```

**Effects:**
- Network: +30% of conference's network gain
- Morale: +10
- Stress: -20
- 10% chance for idea

**After Decay (4-13 points):**
- Best case: +6 morale, -20 stress
- Worst case: -3 morale, -20 stress (if decay > 10)

---

### TALK (conf_talk) - Line 3234

```javascript
// Success chance calculation:
const talkSuccessChance = 0.4 + (alignment * 0.004) + (morale * 0.002);
// Base 40% + up to 40% from alignment + up to 20% from morale = 100% max

if (talkSuccess) {
    s.peerNetwork = Math.min(GAME_CONSTANTS.MAX_NETWORK, (s.peerNetwork || 0) + conf.networkGain * 1.5);
    s.morale = Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 20);
    s.strategicAlignment = Math.min(100, (s.strategicAlignment || 0) + 5);
    // 50% idea chance
} else {
    s.morale = Math.max(0, s.morale - 15);
    s.stress = Math.min(GAME_CONSTANTS.MAX_STRESS, (s.stress || 0) + 15);
    s.strategicAlignment = Math.max(0, (s.strategicAlignment || 0) - 3);
}
```

**Balance Issue:**
- Success: +20 morale → after decay: +7 to +16
- Failure: -15 morale → after decay: -19 to -28 (CRIPPLING)
- Risk/reward heavily skewed toward failure

---

### NETWORK (conf_network) - Line 3264

```javascript
const networkBonus = Math.floor(conf.networkGain * (1 + existingNetwork * 0.01));
s.peerNetwork = Math.min(GAME_CONSTANTS.MAX_NETWORK, existingNetwork + networkBonus);
s.morale = Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + 5);
s.stress = Math.max(0, (s.stress || 0) - 15);
```

**Critical Bug:**
- +5 morale - decay (4-13) = **OFTEN NEGATIVE NET GAIN**
- This makes "Network" choice actually HARM morale in many cases!

**Example:**
- Player has exhaustion (+6 decay), teaching (+3 decay) = 13 total decay
- Conference gives +5 morale
- Net result: -8 morale (player sees "+5 morale" message but loses 8!)

---

## 5. HIDDEN METRICS ANALYSIS

### Documented in hidden_metrics.md vs Actual Code:

| Metric | Documented | In Code | Issue |
|--------|-----------|---------|-------|
| `conferencesThisYear` | ✅ | ✅ | Correct |
| `lastConferenceMonth` | ✅ | ✅ | Correct |
| `conferenceChoiceMade` | ❌ | ✅ (checked only) | Dead code |
| `conferenceCount` | ❌ | ✅ (telemetry) | Undocumented |
| `conferenceChoices` | ❌ | ✅ (history) | Undocumented |

### Hidden Metrics That Affect Conferences:

**From hidden_metrics.md:**
- `strategicAlignment` - affects talk success chance
- `advisorScore` - not directly used in conferences
- `advisor.tension` - not directly used in conferences

**Not Surfaced to Players:**
- Exact talk success chance
- Network bonus calculation
- Why morale gains seem small

---

## 6. CONFERENCE AVAILABILITY LOGIC

### spawnConferenceInvite() - Line 3124

```javascript
spawnConferenceInvite() {
    const s = this.state;
    
    // V2.51: No conferences before month 6
    if (s.totalMonths < 6) return;
    
    // V2.46: Limit to 2 conferences per year
    if ((s.conferencesThisYear || 0) >= 2) return;
    
    // Clear expired
    if (s.activeConference && s.activeConference.expiresIn <= 0) {
        s.activeConference = null;
    }
    
    // Don't spawn if already have one
    if (s.activeConference) return;
    
    // 30% chance per month (after month 6, under limit, no active)
    if (this.random() < 0.3) {
        // ... spawn logic
    }
}
```

**Issues:**
1. No check for `lastConferenceMonth` cooldown here
2. Cooldown only checked in `getAvailableActions()` (line 5351)
3. Conference can spawn but not be available due to cooldown confusion

---

### getAvailableActions() - Line 5351

```javascript
const confCooldown = s.lastConferenceMonth ? s.totalMonths - s.lastConferenceMonth : 99;
if (!s.activeConference && 
    (s.conferencesThisYear || 0) < GAME_CONSTANTS.MAX_CONFERENCES_PER_YEAR && 
    confCooldown >= GAME_CONSTANTS.CONFERENCE_COOLDOWN_MONTHS) {
    // Show "Seek Conference" action
}
```

**Issue:** Cooldown is 2 months but player sees conference spawn, can't attend, expires - frustrating UX

---

## 7. RECOMMENDATIONS

### Priority 1: Fix Decay Timing (CRITICAL)

**Option A - Simplest:**
```javascript
// In resolveConferenceChoice(), set a flag:
s.conferenceJustAttended = true;
s.pendingConferenceMorale = moraleGain;
s.pendingConferenceStress = stressChange;

// In advanceMonth(), apply after decay:
if (s.conferenceJustAttended) {
    this.updateState({ 
        morale: s.morale + s.pendingConferenceMorale,
        stress: s.stress + s.pendingConferenceStress
    }, 'Wellness');
    s.conferenceJustAttended = false;
}
```

**Option B - Better Architecture:**
Move conference effects to apply AFTER `advanceMonth()` completes its decay calculations.

---

### Priority 2: Convert to updateState() Pattern

```javascript
// Replace all direct mutations in resolveConferenceChoice()
this.updateState({
    peerNetwork: Math.min(GAME_CONSTANTS.MAX_NETWORK, (s.peerNetwork || 0) + networkGain),
    morale: Math.min(GAME_CONSTANTS.MAX_MORALE, s.morale + moraleGain),
    stress: Math.max(0, (s.stress || 0) + stressChange),
    conferencesThisYear: (s.conferencesThisYear || 0) + 1,
    lastConferenceMonth: s.totalMonths,
    conferenceCount: (s.conferenceCount || 0) + 1
}, 'Social'); // Or 'Wellness' for morale/stress
```

---

### Priority 3: Fix conferenceChoiceMade

Either:
1. Remove dead code (lines 5155-5157)
2. OR implement properly:
   - Set in `resolveConferenceChoice()`
   - Clear in `advanceMonth()` when conference month ends

---

### Priority 4: Balance Adjustments

**NETWORK choice is broken:**
- Currently: +5 morale → often negative after decay
- Fix: Increase to +15 morale or suppress decay

**TALK failure is too harsh:**
- Currently: -15 morale + decay = -19 to -28
- Fix: Reduce to -10 morale or suppress decay on failure

**POSTER should be safe:**
- Currently: +10 morale → often minimal after decay
- Fix: Ensure minimum +5 net gain

---

### Priority 5: Clarify State Tracking

Consolidate conference tracking:
```javascript
// Instead of 5 separate fields:
conferenceState: {
    thisYear: 0,           // replaces conferencesThisYear
    total: 0,              // replaces conferenceCount
    lastMonth: null,       // replaces lastConferenceMonth
    currentChoice: null,   // replaces conferenceChoiceMade
    history: []            // replaces conferenceChoices
}
```

---

## 8. FILES TO MODIFY

| File | Lines | Changes |
|------|-------|---------|
| docs/index.html | 3218-3292 | Fix resolveConferenceChoice mutations |
| docs/index.html | 4643-4673 | Move decay before conference or add immunity |
| docs/index.html | 5155-5157 | Remove or implement conferenceChoiceMade |
| docs/index.html | 3124-3168 | Clarify spawn vs availability logic |
| docs/hidden_metrics.md | - | Document all conference metrics |

---

## 9. TESTING RECOMMENDATIONS

Add tests for:
1. Conference morale gains persist after month advance
2. Conference stress reductions persist
3. Talk failure doesn't cause death spiral
4. Network choice always gives net positive morale
5. conferenceChoiceMade flag works (if keeping)
6. Cooldown and availability are consistent

---

## CONCLUSION

The conference system **appears to work but is effectively broken** due to immediate decay cancellation. Players see "+10 morale" messages but experience minimal or negative gains, leading to frustration and the reported "conference effects not working" perception.

**Root cause:** Architecture issue where conference effects and monthly decay are in the wrong order.

**Fix complexity:** LOW - reorder operations or add decay immunity

**Impact:** HIGH - fixes 0% win rate, improves player experience

---

*Analysis by: Atlas Orchestrator*  
*Date: 2026-02-11*  
*Version: V2.59.2*
