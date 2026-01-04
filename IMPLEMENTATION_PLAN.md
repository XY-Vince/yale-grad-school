# GradQuest Implementation Plan

## V1.0 - Core Implementation

A faithful Python port of the PhD Simulator game engine with modular architecture.

### Project Structure
```
gradquest/
├── core/           # VariableStore, ExpressionParser, EventEngine, GameEngine
├── effects/        # Attributes, Items, Status system
├── events/         # Event loading and conditions
├── interface/      # CLI interface
└── extensions/     # LLM API preparation
```

### Components Implemented
- **VariableStore**: State management with clamping, callbacks, JSON serialization
- **ExpressionParser**: Safe evaluation (no `eval()`) with game functions
- **EventEngine**: Trigger queue, conditions, probability, action handlers
- **CLI**: Full game loop with stats, choices, inventory
- **LLM Interface**: Abstract base class for future API expansion

---

## V1.1 - Bugfix Update

Based on user playtesting feedback.

### Issues Fixed

| Issue | Fix |
|-------|-----|
| Exhaustion never goes away | 35% cure on slack + 12% monthly recovery event |
| Unhappy Advisor never goes away | 25% cure on slack + 15% monthly forgiveness event |
| Qualifying exam missing | Changed `month === 12` to `month >= 12` |
| Success rates too low | Ideas 40%, Major 35%, Figures 60% |
| Hope renamed | Now displays as "Morale" |

---

## V1.2 - Major Fixes

### Issues Fixed

| Issue | Fix |
|-------|-----|
| Qual exam triggers too early | Now triggers in **September year 2** (`year === 2 && month === 9`) |
| Qual exam too easy | Requires qualifyLevel >= 2 to pass reliably |
| Thesis doesn't re-trigger | Removed `once: true`, added explicit "Work on Thesis" action |
| Graduation doesn't work | Thesis action properly sets EndGameState |
| "hope" text remaining | Changed to "morale" in event messages |

### Files Modified
- `gradquest/interface/cli.py` - Added thesis action, fixed quals prep
- `data/rulesets/default/events.yaml` - Fixed qual timing, thesis event, message text

---

## V1.4 - UI & Gameplay Enhancements

### Issues Fixed

| Issue | Fix |
|-------|-----|
| Event log too small | Enhanced event panel with history |
| Qual prep predictable | Randomized 0-2 points per session |
| Equipment persists forever | Added auto-repair (50%/month, guaranteed at 3 months) |
| Status effects unclear | Added tooltips with descriptions |

### New Features
- Total months counter
- Advisor happiness bar
- Disabled action states for blocked actions

---

## V1.5 - Critical Fixes & New Features (Current)

### Issues Fixed

| Issue | Fix |
|-------|-----|
| Equipment STILL persists | Moved repair logic directly into web app |
| Advisor always neutral | Dynamic happiness based on actions |
| Only one way to get ideas | Added "Attend Conference" action |
| Date too wide | Compact format (Sep, Year 1) |

### Advisor Happiness Changes
- +15 on paper published
- +10 on staying for more research
- -5 on slacking

### New Action: Attend Conference
- 35% chance to get idea
- +8 morale from networking
- 10% chance advisor hears good things


These five trials of **V2.12** represent a landmark in the "Resilience Simulator" evolution. By introducing the **Renewed Perspective** buff and visible **Learning Loops**, the game has successfully moved from a "stall-heavy" RNG experience to a strategic management simulation where every setback provides a mechanical path forward.

### I. Critical Observations: The Efficacy of V2.12 Mechanics

* **Breaking the "Stall State"**: The **Renewed Perspective** (+10% success for 3 months) is highly effective. In Trial 1, the player utilized this buff to secure a journal acceptance immediately following a forced break (Month 58), turning a potential loss of momentum into a victory.
* **The Figure Learning Buff**: The mechanic "You're learning what works. Next attempt will be easier" appears consistently across all trials when figure creation fails. This mitigates the "Figure Grind" frustration identified in earlier reviews by ensuring that failure is never a total waste of time.
* **Administrative Gate Competence**: All five trials successfully passed the **Qualifying Exam** at Month 13. This indicates that the **Quals Urgency Warning** (starting 3 months prior) and the **Study Group** buff (Network ≥ 50) have effectively reduced "accidental" early game-overs.
* **Morale/Mental Health Resilience**: Trial 5 provides a striking example of the system's "life-saving" capacity. Despite hitting a **CRITICAL mental health status** at Month 70, the player survived through to graduation at Month 90, largely due to the advisor-forced interventions and the morale-restoring properties of the new buffs.

### II. Strategic Analysis: Speed vs. Resilience

The trials reveal two distinct "Meta-Strategies" now viable in the engine:

1. **The "Researcher" (Trial 1)**: Ignored conferences entirely (0 papers). Finished fastest at **71 months** by focusing purely on the journal pipeline.
2. **The "Networker" (Trials 2, 4, 5)**: Balanced journal work with 2 conference papers. While these runs took longer (**85-91 months**), they maintained higher **Peer Network** (99-100) and **Advisor Happiness** (80-90%), making them much more resilient to negative RNG like being "Scooped".

---

### III. Suggestions for V2.13 and Beyond

* **Visibility of Buff Status**: While the "Renewed Perspective" text appears in the log, it is not currently visible as a status badge.
* **Suggestion**: Add a temporary **"Renewed Focus"** status badge to the UI when the +10% buff is active so players can prioritize high-risk actions (like "Develop Findings") while they have the advantage.


* **Refining the "MS-Out" Narrative**: In Trial 4, the advisor offered the Master's exit at Month 12—exactly when the player was preparing for Quals.
* **Suggestion**: Per the **Strategic Revision Plan**, the MS-Out option should provide different "Exit Profiles" based on timing. An exit at Month 12 should be themed as "The Early Career Pivot" with a higher chance of a successful industry job hunt.


* **North American "Vibe" Extension**: The current logs focus heavily on research and morale.
* **Suggestion**: To integrate the "North American Vibe" from your original request, consider adding a **"Summer Internship" action**. It could cost 3 months but provide a massive "Industry Wealth" boost and a permanent Network buff, while slightly irritating a "Hands-on" advisor.


* **The "Final Stretch" Buff**: In several trials, the player was ground down in the final few months before the defense.
* **Suggestion**: Once a player reaches **3 Journal Papers**, trigger a **"Light at the End of the Tunnel"** status that reduces Morale decay by 50% during the final "Thesis Work" phase.