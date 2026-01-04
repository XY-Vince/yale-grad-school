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



Below is a V2.15 improvement plan that is deliberately mechanical, implementable, and disciplining.
The guiding principle is:

V2.15 = Temporal realism + player acknowledgment + credential legitimacy

This is the version where GradQuest stops feeling like a continuous stream of months and starts feeling like an academic calendar with consequences.

⸻

GradQuest V2.15 — Solid Improvement Plan

Theme: Academic Time, Player Agency, and Earned Progress

⸻

0. Non-Negotiable Structural Changes (Your Two Directives)

0.1 Semester Alignment (Global Refactor — High Priority)

Canonical Calendar
	•	Spring Semester: January → May
	•	Summer: June → July
	•	Fall Semester: August → December

Actionable Implementation
	•	Add a currentSemester derived variable:
	•	Spring, Summer, Fall
	•	Replace any month-based conditionals with semester-aware checks:
	•	TA duty → only Spring/Fall
	•	Coursework credits → only Spring/Fall
	•	Internships → only Summer
	•	Quals → Spring of Year 2

UI Upgrade
	•	Display header:
Year 2 — Spring Semester

Why this matters
	•	Removes “floating month soup”
	•	Makes internships, quals, TA duty feel situated
	•	Enables future policies (funding cycles, reviews)

⸻

0.2 Mandatory Acknowledgment for Action Results (High Priority)

Problem
	•	Action → event → immediately next action
	•	Player mentally skips consequences

New Rule

If an action generates a result, time pauses until the player acknowledges it

Actionable UI Change
	•	After any ▶️ Action Event:
	•	Disable all action buttons
	•	Show “Acknowledge & Continue” button
	•	Only then advance to next month

Scope
Triggered by:
	•	Submitting papers
	•	Failing/succeeding quals
	•	Internship outcomes
	•	Advisor confrontations
	•	Dead-end research revelations

Why
	•	Forces reflection
	•	Makes outcomes felt
	•	Reinforces causality loop

⸻

1. Fixing the “Too-Easy MS Exit” (Credential Legitimacy)

1.1 Coursework Credit System (Hard Gate)

New Variable
	•	credits

Earning Credits
	•	+3 credits per semester month (Spring/Fall)
	•	Blocked if:
	•	On TA duty (credits → TA workload)
	•	On Medical Leave

MS-Out Requirements
	•	credits ≥ 30
	•	AND Month ≥ 18

Narrative Framing
	•	Before eligibility:
“You haven’t completed enough coursework to be awarded a degree.”

Result
	•	Trial 1 exploit eliminated
	•	MS feels earned, not a quit button

⸻

2. Semester-Aware Action Differentiation

2.1 Quals Prep Evolves by Year (Your Explicit Request)

Year 1 Action
📖 Foundational Study
	•	Low stress
	•	+0.5 prep
	•	No urgency
	•	Tooltip: “Laying groundwork.”

Year 2 Action
📚 Focused Quals Prep
	•	High stress
	•	+1 prep
	•	Blocks some research
	•	Tooltip: “This is no longer optional.”

Visual
	•	Different icons / colors
	•	Year 2 version pulses when urgency warning active

⸻

3. Internship System: Power With Friction

3.1 Advisor Style × Internship Conflict Matrix

Before Internship
Modal choice:
	•	“Ask advisor for permission”
	•	“Accept offer quietly”

Outcomes

Advisor Type	Ask	Don’t Ask
Hands-on	40% No	-20 Happiness
Strict	50% No	Funding risk
Laissez-faire	Likely Yes	Minor penalty

Why
	•	Turns internship into a political decision
	•	Makes Network gains feel earned, not free

⸻

4. Dead-End Research: Convert Pain into Meta-Progress

4.1 Dead-End Reward Rebalance

When Dead-End Research triggers:

Current
	•	+10 Morale
	•	+1 Idea
	•	Reset progress

V2.15 Add
	•	+5 Strategic Alignment
	•	Permanent -5% chance of future Dead-End events

Narrative:

“You now recognize warning signs earlier.”

Why
	•	Long-term learning
	•	Reduces despair
	•	Encourages risk-taking

⸻

5. Player-Controlled Flow & Emotional Weight

5.1 Event Acknowledgment Types

Different acknowledgment buttons based on event type:

Event Type	Button Text
Success	“Take it in”
Failure	“Process this”
Advisor	“Respond”
System Pressure	“Brace yourself”

Pure UI, huge emotional payoff.

⸻

6. Late-Game Structure: Ending the Drizzle

6.1 Defense Phase Lock-In (From V2.14 → Finalized)

Trigger
	•	≥3 published papers
	•	Funding Horizon warning active

Change
	•	Replace full action list with:
	•	“Prepare Defense”
	•	“Revise Thesis”
	•	“Delay (Risky)”

Time Pressure
	•	Each delay increases committee scrutiny

Result
	•	Climactic ending
	•	No more “it just ended”

⸻

7. Target Outcomes for V2.15 Stress Tests

Metric	Target	Why
Earliest MS Exit	≥18 months	Credential realism
Avg. MS Exit	24–30 months	NA norm
Eternal PhD	Eliminated	Funding horizon + defense
Action Skipping	0	Mandatory acknowledgment
Internship Abuse	Reduced	Advisor conflict


⸻

Final Diagnosis

V2.14 proved resilience.
V2.15 must prove legitimacy.

Degrees must be earned.
Time must be felt.
Outcomes must be acknowledged.

This is the version where GradQuest stops feeling like a clever sim and starts feeling like an institution with rules.

V2.15 is the line between simulation and experience.