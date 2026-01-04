---

### **Aspirational Standards List v2.1 (`ASPIRATIONAL_STANDARDS.md`)**

> *“These standards define the technical direction of GradQuest, not immediate compliance requirements. Every punishment must unlock a new form of agency.”*

#### **1. Coding Styles & Principles**

* **Explicit Type Hinting (Python)**: Mandated for all core logic to manage state consistency during complex branching and JSON serialization.
* **Optimized Immutability**: Use shallow copies for performance in long-running simulations (100+ months). Mutations are allowed only through named, logged state transitions to maintain debuggability.
* **Self-Documenting Actions**: Every YAML action must include a `telemetry: category` ("research", "admin", "mental_health") and at least **3 variant phrases** per event to reduce repetition fatigue.

#### **2. Architectural Boundaries**

* **The Logic/View Interface**: The Full Engine must use a `GameState → UIState` transformer. For the Static Web UI, direct state reading is permitted for simplicity but discouraged for new features.
* **Ruleset Precedence (Overlays)**: Strict hierarchy: `Base`  `Regional`  `Difficulty`. Overlays only override or extend; they cannot delete base keys.
* **Non-Goal: LLM Core Logic**: AI/LLM integration is strictly for **flavor text generation** (e.g., specific advisor snark). Core mechanical logic (RNG, state changes) must remain deterministic or based on the AST expression parser.

#### **3. Balance & Telemetry Specifications (New)**

Every simulation run must generate a telemetry summary (CSV/JSON) to calibrate the "Resilience Engine".

* **Primary Metrics**:
* **Median Completion Time**: Target 60–75 months.
* **Inspiration Frequency**: Target < 4 per run.
* **Conference Density**: Target 1.0–1.5 per year.


* **Failure Diagnostics**: Track "Scoop Clusters" and the exact Morale/Paper count at the time of an MS-Out prompt.

#### **4. Difficulty Profiles (YAML Examples)**

Difficulty is codified via coefficients rather than unique code paths.

* **`standard.yaml`**: `conf_cap: 2/yr`, `inspiration_morale: 1.0x`
* **`brutal.yaml`**: `conf_cap: 1/yr`, `scoop_prob_mod: 1.5x`, `inspiration_morale: 0x`

---

### **Revised Logic Blueprint: Resilience & Finale**

This blueprint adds the **Advisor Patience** check and the **Defense Finale** gate to prevent abrupt endings or infinite "safety nets."

```python
# aspirational/simulation_blueprint.py

def advance_simulation(state: PlayerState, action_id: str) -> PlayerState:
    next_state = state.shallow_copy()
    
    # 1. Advisor Patience Check (prevents infinite "forced rescues")
    if next_state.advisor_interventions > next_state.patience_threshold:
        next_state.rescue_available = False # Advisor stops insisting on breaks
    
    # 2. Execute Action
    next_state = engine.apply_action(next_state, action_id)
    
    # 3. Mandatory Defense Prep Gate
    if next_state.papers_published >= 3 and not next_state.defense_prepared:
        next_state.available_actions = ["prep_defense", "polish_thesis"]
        # Abrupt graduation is blocked; player must engage in the "finale" loop
        
    # 4. Apply Decay (Dampened by Strategic Alignment)
    alignment_bonus = next_state.strategic_alignment // 10
    next_state.morale -= (calculate_base_decay(next_state) - alignment_bonus)
    
    return next_state

def trigger_quals(state: PlayerState) -> PlayerState:
    # Logic moved to engine to keep YAML readable
    effective_prep = state.prep_level + (1 if state.network >= 50 else 0)
    if effective_prep >= 2:
        return pass_quals(state)
    return fail_quals(state)

```

### **HMI Design Tokens**

To ensure UI scanability, visual signals must follow semantic tokens:

* **`status-good`**: Green (Research progress, successful prep).
* **`status-warning`**: Yellow (Quals < 3 months away, morale < 30).
* **`status-critical`**: Red (Morale < 15, equipment broken, failed quals).