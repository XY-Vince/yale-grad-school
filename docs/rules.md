# GradQuest Engineering Standards (v1.1)

> *These standards define the technical direction of GradQuest. Every punishment must unlock a new form of agency.*

## 1. Coding Principles
* **Explicit Type Hinting**: All core logic (Python/JS) must use strict type hinting to manage state consistency during complex branching and JSON serialization.
* **Logical Immutability**: Treat the `PlayerState` as logically immutable. Mutations should only occur through named, logged state transitions to ensure reproducibility.
    * *Bad*: `state.morale -= 5` (inline)
    * *Good*: `state = apply_event(state, "morale_loss_minor")`
* **Self-Documenting Actions**: Every action must include specific telemetry fields:
    * `category`: ("research", "admin", "mental_health")
    * `cost`: Explicit resource drain (e.g., `morale: 5`)
    * `desc`: User-facing explanation.
* **Typed State Contracts**:
  * All PlayerState mutations must pass static type checks.
  * Any field added to PlayerState must:
    * be JSON-serializable
    * have a default initializer
* **Deterministic RNG Rule**:
  * All randomness must be derived from `state.rng`.
  * Random outcomes must emit a log token (e.g., `rng_roll: 0.73`).
* **Action Schema Enforcement**:
  * Actions missing `category`, `cost`, or `desc` must not appear in UI.
  * CI should fail if an action definition is incomplete.

## 2. Architectural Boundaries
* **The Logic/View Interface**: The UI Layer must **never** interpret raw engine state directly. All data must pass through a transformer (e.g., `GameState → UIState`) to prevent information scattering.
* **Data-Driven Design**: Logic resides in data, not code.
    * **Events**: Defined in YAML/JSON.
    * **Advisors**: Defined by Archetypes in data.
    * **Rulesets**: Follow a strict overlay hierarchy (`Base` → `Regional` → `Difficulty`).
* **Core Gameplay Primitives**:
  * **Action**: Player-initiated, consumes time.
  * **Event**: System-triggered, zero-time, reactive.
  * **Status**: Persistent modifier with duration.
  * **Buff**: Positive status; **Debuff**: Negative status.
* **Ruleset Validation**:
  * All YAML rules must validate against a JSON Schema.
  * Rulesets must declare a `version` field.

## 3. Balance & Telemetry
* **The "Slog" Check**: Mechanics must avoid infinite death spirals. Every penalty (e.g., Funding = 0) must have an active recovery mechanism (e.g., "Emergency Grant").
* **Feedback Loops**:
    * **Positive**: Must provide immediate agency (e.g., "Workshop Paper" for quick wins).
    * **Negative**: Must provide a "Exit Ramp" (e.g., "Medical Leave" for Exhaustion).
* **Metrics**:
    * Median Completion: 60–75 months.
    * Inspiration Frequency: < 4 per run.
* **Telemetry Requirements**:
  * Every run must log:
    * total months
    * funding zero duration
    * morale < 20 duration
    * rival scoop count
* **Punishment Density Rule**:
  * No negative event may trigger more than once per N months
    unless explicitly counterable by an action.

## 4. UI/UX Tokens
* **Status Colors**:
    * `status-good` (Green): Progress, High Morale.
    * `status-warning` (Yellow): Quals < 3mo, Morale < 30.
    * `status-critical` (Red): Funding = 0, Morale < 15.
* **Visual Shorthand**: Use Emoji for events (📢, 🏖️) and Icons for field-specifics (🔬, 📐, 💻).
* **UI Stability Rule**:
  * Buttons must not change position between enabled/disabled states.
* **Accessibility Rule**:
  * All critical status states must be conveyed via:
    * color
    * icon
    * text