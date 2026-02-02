# Plan: Event System Refactoring (Phase 3)

## Context
The game currently uses scattered direct calls (`showMessage`, `appendSystemEvent`) to trigger events and modals. This leads to:
- Modal collisions (multiple modals popping up at once)
- Priority issues (minor events blocking critical ones)
- "Zombie" events (events triggering in invalid states)

The `EventResolver` class exists but is currently a skeleton that doesn't control the actual UI rendering.

## Goals
1. **Centralize**: Route ALL modal/event triggers through `EventResolver`.
2.  **Enforce Discipline**: Strictly 1 modal per turn, highest priority wins.
3.  **Prioritize**: Explicit 'Emergency' > 'Major' > 'Minor' tiers.

## Architecture

### Target Flow
1. Game System (e.g., `checkCrisis`) -> `EventResolver.enqueue(event)`
2. `Game.advanceMonth()` -> `EventResolver.resolveTick(state)`
3. `EventResolver` picks ONE highest-priority modal.
4. `EventResolver` triggers UI rendering for that modal.
5. Lower priority events are either queued or converted to log messages.

### Event Structure
```javascript
{
  id: 'unique_event_id',
  type: 'modal', // or 'log', 'toast'
  priority: 'Emergency', // 'Major', 'Minor'
  content: "Message text...",
  actions: [ ...options... ], // optional
  owner: 'Wellness' // State owner
}
```

## Tasks

### 1. Enhance EventResolver Implementation
- [ ] Implement `enqueue(event)` method to accept events from anywhere.
- [ ] Implement `renderModal(event)` (moved/adapted from current `showMessage`).
- [ ] Implement `renderLog(event)` (moved/adapted from current `appendSystemEvent`).
- [ ] Update `resolveTick` to actually render the chosen event.

### 2. Refactor Modal Events (`showMessage`)
- [ ] Identify all 25 `showMessage` calls.
- [ ] Convert critical crises (Morale < 10, Funding = 0) to `Emergency` events.
- [ ] Convert progression events (Quals, Paper Accept) to `Major` events.
- [ ] Convert flavor events (Seasonal, etc.) to `Minor` events.
- [ ] Replace direct calls with `game.eventResolver.enqueue(...)`.

### 3. Refactor Log Events (`appendSystemEvent`)
- [ ] Identify all 27 `appendSystemEvent` calls.
- [ ] Convert them to `EventResolver.log()` calls (bypassing modal queue, or low priority).

### 4. Game Loop Integration
- [ ] Ensure `game.advanceMonth()` calls `eventResolver.resolveTick()`.
- [ ] Verify `resolveTick` clears the queue/state correctly for the next turn.

## Verification
- [ ] Trigger two conflicting events (e.g., Funding Crisis + Random Flavor Event) -> Crisis should win.
- [ ] Check game logs for correct "Processing event..." messages.
- [ ] Ensure game still loads and plays normally.

## Risks
- **UI Breakage**: If `renderModal` fails, the game becomes unplayable.
- **Event Loss**: If the queue isn't managed right, critical story events might be dropped.

## Rollback
- Keep legacy `showMessage` available as a fallback until full conversion.
