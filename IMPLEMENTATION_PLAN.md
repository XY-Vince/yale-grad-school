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

