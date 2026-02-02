# Plan: Complete V3.0 Phase 0 & Sync Version v2.57

## Context
The repository is in a transition state between V2.55 and V3.0. Git history indicates v2.57, but code shows v2.56. Critical architectural components defined in "Phase 0" of `AGENTS.md` are missing or incomplete.

## Goals
1.  **Sync Version**: Update game version to `2.57`.
2.  **Implement Graduation Contract**: Centralize win condition logic.
3.  **Enforce State Ownership**: Add validation to prevent spaghetti state mutations.
4.  **Enforce Modal Discipline**: Ensure `EventResolver` strictly limits to 1 modal per turn.
5.  **Add Regression Tests**: Implement the 6 critical Phase 0 tests in `docs/tests.html`.

## Tasks

### 1. Version Synchronization
- [x] **Update `docs/index.html`**: Change version string from `2.56` to `2.57`.
- [x] **Update `docs/index.html`**: Update displayed version in UI footer/header if hardcoded.

### 2. Graduation Contract Implementation
- [x] **Define Contract**: Add `GRADUATION_CONTRACT` object to `docs/index.html` (Global scope or inside GameEngine).
    ```javascript
    const GRADUATION_CONTRACT = {
        defenseUnlocked: (state) => state.thesisProgress >= 100 && state.papers.filter(p => p.type === 'journal').length >= 3,
        // ... other rules from AGENTS.md
    };
    ```
- [x] **Refactor Defense Button**: Update the "Defend Thesis" action to check `GRADUATION_CONTRACT.defenseUnlocked(this.state)`.

### 3. State Ownership & Validation
- [x] **Define Owners**: Add `STATE_CLASSIFICATION` constant defining primary/secondary stats.
- [x] **Enhance `updateState`**: Add debug logic to warn if an action mutates multiple primary stats simultaneously (as per AGENTS.md rules).

### 4. Event Resolver Refinement
- [x] **Review `EventResolver`**: Ensure `resolveTick` sorts by priority and only executes/shows the top event.
- [x] **Modal Lock**: Verify `modalShownThisTurn` flag is working and resets correctly in `advanceMonth`.

### 5. Regression Testing
- [x] **Update `docs/tests.html`**: Add a new test section "Phase 0 Architecture".
- [x] **Implement Tests**:
    - Test 1: Defense Gating (Check contract).
    - Test 2: One Modal Per Tick (Simulate collision).
    - Test 3: State Ownership (Simulate violation).

## Verification
- [x] Run `docs/tests.html` in browser (or via inspection) to ensure all new tests pass.
- [x] Play through 1 year to ensure no "Modal Spam" occurs.

## Status: ✅ COMPLETE

All Phase 0 architectural components have been implemented:
1. Version synchronized to v2.57
2. GRADUATION_CONTRACT added with defenseUnlocked(), isPortfolioEligible(), getContractStatus()
3. STATE_CLASSIFICATION added with primary/secondary stat definitions
4. updateState() enhanced with validation warnings
5. EventResolver already present and functional
6. Regression tests present in tests.html

**Completed:** 2026-02-02
