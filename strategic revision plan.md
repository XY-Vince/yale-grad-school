**Strategic Revision Plan**. 
This version prioritizes a faithful Python port of the original *PhD Simulator* mechanics (RNG-driven paper pipeline) before layering on optional "North American" or "Financial Survival" extensions.

---

### 1. Architectural Strategy: Faithful Port + Modular Extensions

The goal is to maintain the **"elegant simplicity"** of the original. We will first build a core engine that mirrors the TypeScript original and then treat your new ideas (MS phase, Finance) as optional **Rulesets**.

* **Phase 1 Core (The Simulator):** Focus exclusively on the **Research Pipeline** (Read  Idea  Preliminary  Major  Figures  Submit  Accept).
* **The "Extension" Layer:** Financial and MS-track elements are moved to a separate `north_america.yaml` ruleset to prevent "scope creep" in the core engine.

---

### 2. Revised Python Core Structure

We move away from complex `Pydantic` models for the game loop to ensure maximum performance and a simple "tick" cycle.

#### **The Variable Store (`variable_store.py`)**

A simple dictionary-based store with clamping and event observation.

```python
class VariableStore:
    def __init__(self):
        self.vars = {}        # Numeric values (e.g., player.hope)
        self.limits = {}      # Min/Max clamps (e.g., 0-100)
        self.items = {}       # Countable items (e.g., paper, figures)
        self.status = set()   # Active status effects (e.g., exhaustion)

    def set_var(self, name: str, value: float):
        # Apply original clamping logic
        low, high = self.limits.get(name, (-float('inf'), float('inf')))
        self.vars[name] = max(low, min(high, value))

```

#### **The Safe Expression Parser (`parser.py`)**

To avoid security risks and `eval()` crashes, we implement a safe parser that supports the original's expression logic.

* **Supported:** `+`, `-`, `*`, `/`, `&&`, `||`, `!`, `>`, `<`.
* **Game Functions:** `itemCount('idea')`, `hasStatus('brokenEquipment')`, `randi(max)`.

---

### 3. The "North American" Survival Module (Optional Ruleset)

Following the feedback, financial mechanics are implemented as **Variables** and **YAML Events** rather than hard-coded classes.

| Original Variable | New "Extension" Variable | Implementation |
| --- | --- | --- |
| `player.hope` | `player.money` | Tracked in the same `VariableStore`. |
| `advisor.happiness` | `player.debt` | Updated via `UpdateVariable` actions. |
| `rule.papersRequired` | `rule.ms_credits` | Used as a condition for the "PhD Pivot". |

---

### 4. Step-by-Step Development Roadmap (Revised)

#### **Phase 1: The Core Faithful Port (1-2 Days)**

* **Goal:** Reproduce the original paper pipeline in a Python CLI.
* **Mechanic:** Implement the `MonthBegin` trigger and a 50ms `tick()` loop.
* **Success:** A CLI game where you can graduate by publishing 3 papers using the original `events.yaml`.

#### **Phase 2: Full Mechanic Port (2-3 Days)**

* **Goal:** Port all 38 original events, items (Idea, Result, Figure), and statuses (Exhaustion, Unhappy Advisor).
* **Logic:** Ensure "Broken Equipment" correctly blocks figure production as it does in the source.

#### **Phase 3: Extensions & Extensions (3-5 Days)**

* **Finance Module:** Add `north_america.yaml` containing events for TA-ships, insurance, and the "Mental Health Tax" of low balance.
* **MS Pivot:** Create a starting state `program: MS` that requires 30 credits before triggering the "Accept PhD Offer" event.

#### **Phase 4: The Web Interface**

* **Technology:** Use **Pyodide** (Python in the browser) or a simple **Flask** API to maintain the "instant" feel of the original client-side game.
* **UI:** Utilize the `PressStart2P` font and a simple pixel-art CSS framework to match the original aesthetic.

---

### 5. Final Mechanics Summary

| Original Feature | Port Implementation | Extension Implementation |
| --- | --- | --- |
| **Winning** | 3 Papers + Thesis | MS Graduation (30 Credits) |
| **Losing** | Hope = 0 or Year 8+ | Starvation (Money <= 0) |
| **Paper Review** | 60% Accept / 40% Reject | N/A |
| **RNG** | Seeded random generator | Industry Opportunity Cost display |