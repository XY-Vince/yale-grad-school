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


Below is a V2.16 improvement plan that is tightly scoped, implementation-ready, and aligned with your stated rule:
one major feature focus per version.

This is not a mechanics expansion release.
V2.16 is an interface and cognition release.

⸻

GradQuest V2.16 — Solid Improvement Plan

Theme: Make the invisible legible
Primary Objective: Eliminate the “black box” feeling without dumbing down the simulation
Constraint: No new core mechanics unless they directly support UI clarity

⸻

I. Core Diagnosis (Hard Truth, Restated)

By V2.15, GradQuest has:
	•	✅ A strong resilience engine
	•	✅ Meaningful failure recovery loops
	•	❌ A UI that hides critical information and forces players to guess

Players are no longer losing because of bad strategy.
They are losing because they cannot see the state space.

V2.16 fixes that, and nothing else.

⸻

II. Major Feature Focus: Status Dashboard & HUD Overhaul

(Desktop + Mobile-first)

1. Status Dashboard (Persistent, Compact, Always Visible)

Add a collapsible “Status Dashboard” panel at the top (or bottom on mobile).

1.1 Visible Strategic Alignment Meter (High Priority)
What
	•	Convert Strategic Alignment from hidden → visible bar (0–100)

UI
	•	Label: Advisor Alignment
	•	Tooltip:
“Higher alignment reduces morale decay and softens negative randomness.”

Mechanical Transparency
	•	Show thresholds visually:
	•	30+: fewer morale hits
	•	60+: RNG variance reduction
	•	80+: Pep Talks, advisor protection

Why
	•	Pitch Sessions become legible investments, not folklore

⸻

1.2 Morale Decay Breakdown (On Hover / Tap)
When hovering Morale:

Base Decay: -4
Exhaustion: -6
Imposter Syndrome: -3
Alignment Buffer: +4
Net: -9 / month

Mobile
	•	Tap opens modal

Why
	•	Players stop blaming “bad RNG”
	•	They learn how decay actually works

⸻

2. Research Pipeline 2.0 (Stepper, Not Text)

Replace text-heavy pipeline with a visual stepper:

Idea → Findings → Discovery → Figures (1/3) → Submitted → Review (7/10)

2.1 Explicit Figure Progress (Already Requested, Fully Enforced)
	•	Always display Figures: X / 3
	•	Add small + icon when Learning Buff active

Tooltip:

“Previous failures are making this easier.”

⸻

2.2 Review Countdown (Journal / Conference)
For each submitted paper:
	•	Show:
	•	Type: Journal / Conference
	•	Status: Under Review
	•	Progress bar: 7 / 10 months

Important
	•	No more “(4 month review)” in logs
	•	Time pressure is visual, not textual

⸻

3. Quals Prep Visualizer (Critical)

3.1 Prep Meter Appears Automatically
When Year ≥ 1:

Quals Prep: 1 / 3

3.2 Context-Sensitive Styling
	•	Year 1: Neutral color, informational
	•	Year 2 (Spring–Summer): Yellow warning
	•	Final 3 months: Red + pulsing

Tooltip:

“Failing Quals ends the program. Retake has permanent costs.”

Why
	•	Eliminates accidental Month-13 failures permanently

⸻

4. Action Availability Transparency

4.1 Dynamic Action Surfacing (No More Hidden Tools)
Actions must appear grayed-out with explanation, not disappear.

Examples:
	•	Pitch Session
	•	Shown when Advisor exists
	•	Disabled if cooldown active
	•	Tooltip explains cooldown
	•	Medical Leave
	•	Always visible
	•	Enabled only if Morale < 15
	•	Tooltip:
“Available only during critical burnout.”

Why
	•	Players learn what they could do, not just what they can do now

⸻

5. Event Categorization & Visual Semantics (From V2.14 → Finalized)

Every event must be visually tagged:

Event Type	Icon	Color
Player Action Result	▶️	Blue
Random Event	🎲	Gray
Advisor Intervention	🧑‍🏫	Purple
System Pressure	⚠️	Red
Buff / Learning	✨	Green

Implementation
	•	Tag injected at event creation
	•	No logic change required

Why
	•	Players stop conflating RNG with consequence
	•	Accountability becomes clear

⸻

III. Secondary Improvements (Allowed, Minimal Scope)

6. MS-Out Credit Gate (Finalize Fix)

Rule
	•	MS-Out disabled until:
	•	Credits ≥ 30
	•	Month ≥ 18

UI
	•	Show MS-Out button grayed out
	•	Tooltip:
“Insufficient coursework for degree.”

⸻

7. Scoop Cooldown (Anti-Cruelty Rule)
	•	After being scooped:
	•	24-month immunity
	•	UI indicator:
“Recently scooped — reduced risk.”

⸻

8. Advisor Tone Refinement (Text-Only)

Based on advisor trait:
	•	Strict → blunt, formal
	•	Hands-on → disappointed but supportive
	•	Laissez-faire → detached, permissive

No new mechanics
Pure narrative differentiation

⸻

IV. Mobile Optimization Checklist (Non-Optional)
	•	One-column layout
	•	Dashboard collapsible
	•	All meters tap-expand
	•	No hover-only info
	•	Buttons ≥ 44px height

⸻

V. Success Metrics for V2.16

Metric	Target
Accidental Quals Failures	0
“I didn’t know that existed” feedback	0
Avg. time to understand Alignment	<5 minutes
Mobile usability complaints	Minimal
Rage quits due to opacity	Eliminated


⸻

Final Judgment

V2.16 is not about adding content.
It is about respecting the player’s intelligence.

By this point, GradQuest already:
	•	Punishes mistakes fairly
	•	Rewards learning
	•	Models academic endurance honestly

What it lacks is nervous system transparency.

After V2.16, when a player fails, they should be able to say: “I understand exactly why that happened.”

Great — V2.17 is the right moment to change the game’s feel, not just its numbers.
Below is a clean, consolidated, actionable improvement plan for V2.17, explicitly focused on pacing + agency, while keeping scope disciplined.

I’ll do three things:
	1.	Sharpen the design intent (what problem each change solves)
	2.	Lock the mechanics (no vague ideas)
	3.	Translate into implementable action items (engine + UI)


⸻

GradQuest V2.17 — The Pacing & Agency Update

First of all, whenever an event is triggered by player action, it should be visually distinct from other events, and requiring player to press acknowledge button to confirm.

Design Pillar:

The player is no longer a victim of RNG — they are a risk manager.

Primary Goal:
Reduce median PhD completion time from ~95 months → 65–75 months
without lowering difficulty or removing failure.

⸻

I. Core Problem Diagnosis (Post-V2.16)

What’s wrong
	•	Discovery / Findings loop is too linear and repetitive
	•	Review periods are dead time
	•	Summer Internship is dominant, not strategic
	•	Negative events feel inevitable, not avoidable

What must change
	•	Add acceleration levers
	•	Add insurance mechanics
	•	Add meaningful trade-offs
	•	Preserve tension

⸻

II. Major Feature Set (V2.17)

A. Research Acceleration — Shorten the Core Loop

1. Compress the Discovery Phase (High Priority)
Change
	•	Reduce Develop Findings required successes:
	•	From 4 → 2–3, scaled by Alignment

Rule

Required iterations = 3 − floor(StrategicAlignment / 40)
(min = 2)

Effect
	•	Skilled players finish faster
	•	Low-alignment players still grind

⸻

2. New Action: High-Throughput Experiment
Purpose: Break mid-game stagnation with risk

Action

🔬 High-Throughput Experiment
Cost: 2× morale cost
Chance: 40%
Outcome:
  Success → +2 Figures
  Failure → −Morale, +Exhaustion
Cooldown: 6 months

Why it works
	•	Voluntary risk
	•	Speeds expert play
	•	Creates memorable moments

UI
	•	Marked as ⚡ High Risk
	•	Tooltip shows exact odds

⸻

B. Proactive Defense — Let Players Buy Safety

3. New Action: Pre-Register Idea
Purpose: Eliminate rage-inducing Scoops

Action

📄 Pre-register Idea
Cost: −5 Network
Effect: Prevents "Scooped" for current idea
Permanent (per idea)

Design Note
	•	Network finally has defensive value
	•	Mirrors real academia

⸻

4. New Action: Equipment Maintenance
Purpose: Remove pure bad-luck losses

Action

🔧 Equipment Maintenance
Cost: 1 month (no research)
Effect: Blocks Equipment Failure for 12 months

UI
	•	Adds “Equipment Stable (12m)” badge

⸻

C. Internship Rebalance — From Mandatory to Meaningful

5. Internship Penalty Scaling (Critical Fix)
New Rule

Advisor Type → Penalty
Laissez-faire → −5 happiness
Hands-on → −12 happiness
Strict → −20 happiness + Funding Risk (6m)

Funding at Risk
	•	+2 morale decay
	•	Advisor interventions less likely

Result
	•	Internship becomes a strategic gamble
	•	“Ask Permission” vs “Do It Anyway” remains relevant

⸻

D. Passive Review Agency — No More Waiting in the Dark

6. New Action: Respond to Reviewers (During Review)
Availability
	•	Only while paper is under review

Options

📝 Light Response
Cost: −3 Morale
Effect: +10% acceptance chance

🧠 Major Rebuttal
Cost: −8 Morale, −1 Month
Effect: Skip "Major Revision"

Why
	•	Turns dead time into decisions
	•	Introduces resource tension

⸻

E. Network Finally Matters — Instrumental Power

7. Network Threshold Abilities (Lock Them In)

Network	Unlock
40	Study Group (already exists)
60	Pre-register discount (−3 cost)
80	Peer Review Assist (skip one Figure RNG)
100	Reviewer Influence (−1 review month)

Design Rule
	•	Network is spent, not just accumulated

⸻

III. Advisor Friction & Alignment Shields

8. Alignment-Based RNG Shield (Small but Important)

Every 10 Alignment:
  −5% chance of negative research RNG

Visible in UI:

“Advisor alignment is protecting you.”

⸻

IV. Endgame Flow (Tie-in, Minimal Scope)

9. Defense Trigger (Finalize)
Once:

Journal Papers ≥ 3

Then:
	•	All actions disabled
	•	Only track:

🎓 Prepare Defense

Morale decay reduced by 50%
Internships disabled
Focus narrows

⸻

V. Updated Gameplay Loop (Mental Model)

Old

Action → RNG → Wait → RNG → Suffer

New

Plan → Invest → Insure → Accelerate → Risk → Recover


⸻

VI. Implementation Checklist (Actionable)

Engine
	•	Reduce discovery iterations
	•	Add High-Throughput Experiment
	•	Add event mitigation flags
	•	Rebalance internship penalties
	•	Add review-phase actions
	•	Network threshold hooks

UI / HMI
	•	Mark “Risk / Defense / Acceleration” actions visually
	•	Add status badges (Maintenance, Pre-registered)
	•	Show review interaction buttons conditionally

⸻

VII. V2.17 Success Metrics

Metric	Target
Median PhD duration	65–75 months
“Nothing to do” months	0
Internship usage	<100% of runs
Rage quits due to Scoops	Near zero
Network perceived usefulness	High


⸻

Final Verdict

V2.17 is the version where GradQuest stops being about endurance
and becomes about judgment.

After this update:
	•	Skilled players finish faster
	•	Careless players burn out faster
	•	Smart players feel smart

That’s the inflection point between
a good simulator and a game people replay to master.




This schema defines the logic for calculating your post-PhD (or post-MS) career path. In **V2.18/2.19**, the game no longer just "ends"; it evaluates your accumulated **Social Capital** (Network/Alignment) and **Academic Output** to determine your professional legacy.

### I. Career Endings YAML Schema (`career_endings.yaml`)

```yaml
# rulesets/default/endings.yaml

endings:
  # --- PhD PATH ENDINGS (Requires 3+ Journal Papers) ---
  - id: tenure_track_professor
    name: "Tenure-Track Professor"
    conditions: 
      papers: ">= 4"
      peer_network: ">= 80"
      strategic_alignment: ">= 70"
    desc: "The holy grail. You secured a position at an R1 institution. Your advisor's advocacy was the final key."

  - id: industry_rd_director
    name: "R&D Director"
    conditions:
      papers: ">= 3"
      peer_network: ">= 90"
      internships_taken: ">= 1"
    desc: "You traded the ivory tower for a corner office. Your massive network ensured a seamless transition."

  - id: academic_martyr
    name: "Permanent Post-doc"
    conditions:
      papers: ">= 3"
      morale: "< 20"
    desc: "You have the degree, but at what cost? You continue the grind, one one-year contract at a time."

  # --- MS-OUT PATH ENDINGS (Requires 30 Credits + 18 Months) ---
  - id: startup_founder
    name: "Tech Startup Founder"
    conditions:
      exit_type: "MS"
      peer_network: ">= 70"
      ideas_generated: ">= 5"
    desc: "You took your half-finished discovery and turned it into a seed-round deck. Disruption awaits."

  - id: data_scientist
    name: "Data Scientist"
    conditions:
      exit_type: "MS"
      papers: ">= 1" # Published at least one thing
    desc: "Your ability to survive Reviewer #2 made you overqualified for industry analytics. +15% salary boost."

  - id: great_escape
    name: "The Great Escape"
    conditions:
      exit_type: "MS"
      morale: "< 10"
    desc: "You left academia and never looked back. Your health is recovering, and you've rediscovered hobbies."

```

---

### II. Finale Logic: The Career Resolver (Pseudo-code)

The engine will run this "Resolver" during the `endGame()` sequence to determine which narrative profile to display.

```python
# logic/career_resolver.py

def resolve_career_ending(state):
    # 1. Determine base path
    if state.exit_type == "PhD":
        available_endings = ruleset.endings.filter(path="PhD")
    else:
        available_endings = ruleset.endings.filter(path="MS")
    
    # 2. Check conditions (Highest Priority first)
    # Endings in YAML should be ordered from most prestigious to least
    for ending in available_endings:
        if evaluate_conditions(ending.conditions, state):
            return ending
            
    # 3. Default fallback
    return ruleset.endings.get(id="career_pivot")

def evaluate_conditions(conditions, state):
    # Example AST evaluation for YAML conditions
    # if state.papers >= 3 and state.peer_network >= 80...
    return all(parser.eval(cond, state) for cond in conditions)

```

---

### III. Strategic Refinements (V2.18 Preview)

* **The "MS-Out" Rebalance**: Per your observation that Trial 1 was "too easy," the MS-Out action is now gated by `credits >= 30`.
* **The "Alignment" Legacy**: Strategic Alignment now influences the "Professor" ending. If alignment is low (<30), the advisor gives a "lukewarm" recommendation letter, increasing the requirements for the Tenure-Track ending.
* **HMI Upgrade**: The ending screen will now display a **"Stipend vs. Salary"** chart, showing the immediate financial jump of an MS exit vs. the long-term prestige of the PhD.



⸻

V2.19 IMPROVEMENT PLAN

Theme: UX Clarity + Defense as a Proper Third Act
Design goal: Fewer buttons, clearer stakes, one unmistakable climax

⸻

A. Action Overcrowding → Intentional Mode Switching (Core Fix)

1. Replace “Tabbed Actions” with Context Modes

Tabs are a good start, but still cognitively noisy. Academia doesn’t feel like tabbing — it feels like being stuck in phases.

Actionable Upgrade
Introduce explicit game modes instead of free tabbing:

state.mode ∈ {
  "NORMAL",
  "QUALS_WINDOW",
  "PROBATION",
  "FINALE"
}

Each mode exposes only 3–4 actions, hard-capped.

Example
	•	NORMAL: Research / Advisor / Wellness
	•	QUALS_WINDOW: Prep Quals / Study Group / Advisor Check-in
	•	PROBATION: Prep / Rest / Emergency Pitch
	•	FINALE: Thesis-only actions

This does three things:
	•	Solves overcrowding structurally
	•	Prevents “wrong action at wrong time”
	•	Makes the game feel narratively paced

Do this instead of adding more UI filters.

⸻

B. Qualifying Exam: From Event → Arc (Major UX Win)

You fixed invisibility. Now fix emotional flatness.

2. Turn Quals into a 3-Month Countdown Arc

Right now:
	•	Month 13 → modal → done

That’s still abrupt.

Action items
Add a Quals Countdown Banner starting Month 10:

🎓 Qualifying Exam in 3 months
Required Prep: 3 | Current: 1 (+1 Network)

With escalating UI pressure:
	•	Month 10: neutral
	•	Month 11: warning yellow
	•	Month 12: danger red + advisor emails change tone

Mechanical impact
None.
Pure UX tension. Massive payoff.

⸻

3. Explicit Retake Contract (After Failure)

Your modal is good, but players still won’t internalize consequences.

Add a forced choice after FAIL:
	•	“Commit to Retake” (+Prep efficiency, morale drain)
	•	“Explore Exit Options” (unlocks MS-Out advisory)

This preserves realism:
	•	Many students fail quals and reassess life

⸻

C. Defense Finale: Make It a Mini-Game, Not a Dice Roll

Right now the Defense is still:

Grind → click → RNG

That’s not worthy of a climax.

4. Defense Readiness = 3 Independent Tracks

Instead of a single “100% Thesis Progress”, split into:

defense_state = {
  thesis_quality: 0–100,
  presentation_skill: 0–100,
  committee_support: 0–100
}

Each maps cleanly to existing stats:
	•	Thesis Quality ← Figures, Polish, Papers
	•	Presentation ← Practice Defense, Teaching, Network
	•	Committee ← Alignment, Advisor Style, Past Conflicts

Pass rule
	•	Must pass 2 of 3
	•	Failures cause targeted revisions, not full reset

This:
	•	Reduces pure RNG
	•	Makes different builds viable
	•	Creates post-defense stories

⸻

5. Visible Committee Personalities (Lightweight)

Do not add full NPCs. Just tags.

Example:
	•	Prof. Chen — Methodology Hawk
	•	Prof. Smith — Industry Friendly
	•	Prof. Alvarez — Silent but Deadly

Each biases one defense track.

Low cost, high narrative return.

⸻

D. UX Polishing That Actually Matters

6. Replace Tooltips with Explain-on-Hover Panels

Tooltips are already saturated.

Upgrade key stats (Morale, Alignment, Network) to:
	•	Hover → small panel
	•	Shows:
	•	What it affects
	•	What will unlock next
	•	What’s currently blocked

This aligns perfectly with your Aspirational Standards (self-documenting actions).

⸻

7. One-Click “Why Can’t I Do This?” Feedback

If an action is disabled:
	•	Clicking it shows a short reason
	•	Example:
“Defense unavailable: Committee Support < 60”

This kills guesswork permanently.

⸻

E. Engine / Architecture Cleanups (Quiet but Critical)

8. Formalize Milestones as First-Class Objects

Quals, Defense, MS-Out — these are not “events”, they’re milestones.

Action item:

class Milestone(BaseModel):
    id: str
    status: locked | active | completed | failed
    requirements: dict
    consequences: dict

This will:
	•	Simplify UI logic
	•	Prevent edge-case bugs
	•	Make V3.0 narrative generation trivial

⸻

9. End-of-Run Timeline (Zero Gameplay Cost, Huge Payoff)

At game end, render a vertical timeline:
	•	Quals Passed / Failed
	•	Major Scoops
	•	Internships
	•	Defense Outcome

Players love post-mortems.

⸻

F. What NOT to Add in V2.19 (Be Ruthless)

Do not add:
	•	Money / rent / stipends (V2.20)
	•	Immigration stress
	•	Relationship mechanics
	•	Reviewer personalities

V2.19 must feel cleaner, not richer.

⸻

G. V2.19 Final Checklist

UX
	•	Mode-based action gating
	•	Quals countdown banner
	•	Defense tracks UI

Logic
	•	Milestone abstraction
	•	Defense pass 2-of-3 logic

Narrative
	•	Committee tags
	•	End-of-run timeline

⸻

Final Assessment

If V2.18 made GradQuest intellectually honest,
V2.19 is where it becomes emotionally correct.

This is the version where:
	•	Players stop asking “what just happened?”
	•	And start saying “yeah… that’s exactly how it felt.”


V2.20 is a conceptually strong pivot, and you’re aiming at exactly the right abstraction level: discipline shapes tempo. Below is a critical review + concrete improvement plan, with explicit actionable items, guardrails, and a few hard corrections to prevent future balance and UX regressions.

I’ll structure this as:
	1.	Hard truths (what works, what risks breaking)
	2.	Core improvements to lock V2.20 in
	3.	Actionable implementation checklist
	4.	What to deliberately defer

⸻

I. High-Level Assessment (Hard Truths)

What You Got Right
	1.	Specialization as asymmetry, not flavor
	•	The modifiers meaningfully affect research velocity, not just RNG.
	•	This is exactly how real PhDs diverge.
	2.	Active Peer Network
	•	Spending Network for guaranteed Figures is a huge design win.
	•	This converts social capital from “stat padding” into decision tension.
	3.	Event Pool Tied to Field
	•	Field-specific hazards (server crash vs lab audit) are elegant and legible.
	•	This avoids generic “bad luck” frustration.
	4.	Tooltips over Text Dumps
	•	You’re now meeting your own Aspirational Standards.

⸻

The Two Biggest Risks in V2.20

⚠️ Risk 1: Specialization Lock-In → Early Game Traps
Right now, specialization is chosen at start and permanent. That’s realistic—but dangerous.

A new player choosing Experimentalist without understanding:
	•	equipment risk
	•	maintenance importance
	•	slower idea generation

…may soft-lock themselves into a morale death spiral.

⚠️ Risk 2: Network Spend Can Collapse the Social Game
Spending 25 Network → 1 guaranteed Figure is powerful.

If unbounded, optimal play becomes:

hoard network → spam collaborate → ignore research loop

That breaks pacing and fantasy.

⸻

II. Core Improvements to Make V2.20 Robust

1. Add a “Soft Pivot” Mechanism (Critical)

Do not allow full respec.
Do allow partial drift.

Actionable Change
Introduce Secondary Skill Adoption at mid-game (Month ≥ 24):

state.secondary_focus ∈ { "Experimental", "Theoretical", "Computational", None }

Effects:
	•	Gain 50% of secondary modifiers
	•	Increase event complexity slightly
	•	Adds realism (people evolve)

Narrative framing:

“Your work has begun to cross disciplinary boundaries.”

This:
	•	Prevents early mistakes from ruining runs
	•	Preserves replay value
	•	Enables hybrid builds without balance explosion

⸻

2. Cap Network Spend with “Social Fatigue”

You must prevent infinite collaboration spam.

Actionable Rule
Each collaboration action adds a temporary status:

status: "social_debt"
effect: collaboration_cost +10
decays: -10 every 6 months

Example:
	•	First collab: 25 Network
	•	Second (soon after): 35
	•	Third: 45 → probably not worth it

This models real favors and preserves strategic weight.

⸻

3. Specialization-Specific “Fast Lanes” (Positive Identity)

Right now, specializations mostly change penalties. Add signature accelerators.

Concrete Additions

Field	Unique Accelerator
Experimentalist	Protocol Reuse: After first Figure, next Figure needs 1 fewer step
Theoretician	Conceptual Breakthrough: Once per year, auto-generate an Idea
Computational	Pipeline Automation: Reduce Develop Findings time by 1 month

These are:
	•	Predictable
	•	Non-RNG
	•	Identity-defining

⸻

4. Make Collaboration Contextual, Not Generic

Right now:

Spend Network → +1 Figure

That’s too flat.

Actionable Upgrade
Tie collaboration outcome to specialization:

if specialization == "Experimental":
    figure += 1
    morale += 3
elif specialization == "Theoretical":
    alignment += 2
    discovery_progress += 30%
elif specialization == "Computational":
    figure += 1
    equipment_failure_chance -= 0.2

This reinforces fantasy and prevents dominant strategies.

⸻

III. Event System: Tighten, Don’t Expand Further

Your event YAML is good. Don’t add more events.

Instead:

5. Add Event Counterplay Indicators

When an event fires, show:

“Preventable via: Maintenance / Network / Alignment”

Even if the player didn’t have the shield.

This converts frustration into learning.

⸻

6. Make Financial Stress a Status, Not a Money System

You did this correctly—keep it shallow.

But: ensure it interacts with specialization.

Example:
	•	Theoreticians less affected (grants flexible)
	•	Experimentalists hit harder (consumables)

This gives “money” texture without spreadsheets.

⸻

IV. HMI: Final Cleanups for V2.20

7. Specialization Card on Main HUD

Always visible:
	•	Field icon
	•	2 bullet modifiers
	•	1 warning

No hiding. No menus.

⸻

8. Network Tooltip → “Spendable Uses”

Change from:

“Next threshold: 80”

To:

“Spend:
• Collaborate on Figures (25)
• Pre-register (5)
• Study Group (Passive)”

This is huge for clarity.

⸻

V. Concrete V2.20 Implementation Checklist

Core Mechanics
	•	Specialization selection at game start
	•	Secondary focus unlock at Month ≥ 24
	•	Field-specific accelerators
	•	Network spend scaling (social debt)

Events
	•	Field-weighted event probabilities
	•	Event counterplay hints

UI
	•	Specialization HUD card
	•	Network “uses” tooltip
	•	Advisor tooltip shows field bias

⸻

VI. What NOT to Add in V2.20 (Firm)

Do not add:
	•	Funding balance sheets
	•	Teaching load optimization
	•	Relationship drama
	•	Multiple advisors

You’re at the edge of bloat. Hold.

⸻


V2.21 is the right corrective move, and you’ve correctly diagnosed the problem: the system became too honest. Realistic ≠ playable. The solution is not to weaken failure, but to add believable human buffers.

Below is a careful review + tightened improvement plan, with specific corrections, missing pieces, and actionable items that make V2.21 resilient without turning it into “easy mode.”

⸻

I. High-Level Assessment (Hard Truths)

What V2.21 Gets Exactly Right
	1.	Death Spiral is now systemic, not RNG
	•	Exhaustion → Burnout → Morale collapse was mathematically inevitable.
	•	You correctly target intervention, not nerfs.
	2.	Social Support as automatic, not player-taxed
	•	Advisor interventions triggering without consuming a month is critical.
	•	This mirrors real academia: help often comes when things look dire.
	3.	Stress Meter replaces binary punishment
	•	This is one of the best design upgrades so far.
	•	Players can now see danger accumulating and plan around it.

⸻

II. Core Design Risks to Fix in V2.21

⚠️ Risk 1: Alignment Becomes a God Stat

Right now:
	•	Alignment halves penalties
	•	Triggers exhaustion clearing
	•	Buffs morale decay
	•	Shortens review time

This risks dominant play: “always farm alignment.”

⚠️ Risk 2: Social Support Triggers Too Late

Most Game Overs happen before morale < 20 or stress = 100.

You need early warning soft landings, not just emergency parachutes.

⸻

III. Critical Improvements to Lock V2.21

1. Split Advisor Support into Passive and Active

Right now, alignment does everything. Split it.

Actionable Change
Introduce two advisor effects:

advisor_support = {
    "passive_shield": alignment >= 40,   # always-on mitigation
    "active_intervention": alignment >= 60 and cooldown == 0
}

Rules
	•	Passive Shield: −25% morale penalties (not 50%)
	•	Active Intervention:
	•	Clears Exhaustion OR Burnout
	•	Has 12-month cooldown
	•	Triggers only once per crisis

This prevents alignment from trivializing adversity.

⸻

2. Add Peer Intervention (Non-Advisor Safety Net)

Right now, all rescue flows through the advisor. That’s unrealistic and brittle.

New Mechanic: Peer Check-In

if state.peer_network >= 60 and state.morale < 30:
    trigger_peer_intervention()

Effect:
	•	−30 stress
	•	+10 morale
	•	Does NOT remove Burnout
	•	Narrative: labmates notice you disappearing

This:
	•	Gives Network independent value
	•	Prevents advisor from being the sole savior
	•	Feels human, not mechanical

⸻

3. Exhaustion Should Precede Burnout (Explicitly)

Right now, Burnout is still too sudden.

Actionable Status Ladder

State	Trigger	Effect
Stressed	Stress ≥ 60	Tooltips warn, no penalties
Exhausted	Stress ≥ 100	−20% success
Burnout	Exhausted + morale < 15	−40%, blocks High-Throughput

Burnout should feel like mismanagement over time, not one bad roll.

⸻

4. Quals Window Protection (Critical)

Month 12–14 is the kill zone.

Add a Quals Grace Mechanic
If any of the following are true:
	•	peer_network ≥ 40
	•	alignment ≥ 50
	•	qual_prep ≥ 2

Then:
	•	First Quals failure cannot cause Game Over
	•	Always grants a structured recovery path

Narrative framing:

“The committee sees potential but demands improvement.”

This preserves stakes without nuking runs.

⸻

IV. Stress Meter Improvements (Fine-Tuning)

Your stress system is good. Make it legible earlier.

5. Stress Forecast (One-Month Lookahead)

Add:

“If you repeat this action next month, you will become Exhausted.”

This turns stress into planning, not reaction.

⸻

6. Specialization-Specific Stress Modifiers

Stress should feel different by field.

Field	Stress Pattern
Experimental	Spikes from failures
Theoretical	Slow accumulation
Computational	Bursty (server crashes)

Implement via action-level multipliers, not global tweaks.

⸻

V. HMI: Make Support Visible Before It Triggers

7. “Support Available” Indicators

On HUD:
	•	🧑‍🏫 Advisor Available (if intervention off cooldown)
	•	🤝 Peers Watching (if network ≥ 60)

Greyed out when unavailable.

This avoids the feeling of random salvation.

⸻

8. Morale Tooltip → Add “Projected Next Month”

Change tooltip to:

Current Morale: 22
Next Month Projection: 16
Drivers:
- Base Decay: -4
- Exhaustion: -2
+ Alignment: +1

This is the single most important anti-frustration feature.

⸻

VI. Concrete V2.21 Implementation Checklist

Core Systems
	•	Stress → Exhaustion → Burnout ladder
	•	Advisor intervention with cooldown
	•	Peer intervention trigger (network ≥ 60)

Quals Protection
	•	Grace rule for first failure
	•	Explicit recovery narrative

UI
	•	Stress forecast tooltip
	•	Support availability icons
	•	Morale projection display

⸻

VII. What NOT to Add in V2.21 (Firm)

Do not add:
	•	Therapy systems
	•	Romance / drama
	•	Additional currencies
	•	Permanent morale regen

This is support, not a wellness simulator.

⸻

Final Verdict

V2.21 is the patch that decides whether GradQuest is brutal-but-beloved or brutal-and-abandoned.

If V2.20 defined identity,
V2.21 must define human survivability.

V2.22 is the necessary nervous-system upgrade. You’re no longer fixing balance or mechanics—you’re fixing perception, and that’s the right call. Below is a tightened, production-ready improvement plan with corrections, missing pieces, and a concrete JS implementation for the Graduation Progress Card.

I’ll be blunt where needed, because this version determines whether GradQuest feels fair.

⸻

I. Critical Review of Your V2.22 Direction

What You Diagnosed Correctly
	1.	Information loss is now the #1 failure mode
	•	The player didn’t fail because of bad strategy.
	•	They failed because they didn’t know something important happened.
	2.	Milestones must interrupt, not notify
	•	Quals, paper acceptance, defense readiness are state transitions, not log entries.
	•	Requiring acknowledgment is absolutely correct.
	3.	Probabilities > Flavor Text
	•	At this complexity level, players expect estimates, not mystery.
	•	“Estimated Success” is the right abstraction (not exact odds).

⸻

II. Hard Constraints for V2.22 (Do Not Violate)

Before improvements, two guardrails:
	1.	Never show exact RNG formulas
	•	Percentages must be rounded (e.g. 60–70%, not 63.4%).
	2.	No decision without visibility
	•	If an action can cause Game Over, its preview must signal risk.

Everything below respects this.

⸻

III. V2.22 Core Improvements (Refined)

1. Priority Notifications: Add Severity Levels

Your current system is good but incomplete. Add severity tiers so UI behavior is consistent.

Actionable Change

PRIORITY_MAP = {
    "PAPER_ACCEPTED": "BLOCKING",
    "QUALS_RESULT": "BLOCKING",
    "DEFENSE_READY": "BLOCKING",
    "CRITICAL_FAILURE": "BLOCKING",
    "BURNOUT": "HIGH",
    "EXHAUSTION": "HIGH",
    "MORALE_CHANGE": "LOW"
}

Rules
	•	BLOCKING → modal + acknowledgment required
	•	HIGH → toast + highlighted log entry
	•	LOW → log only

This prevents modal spam while preserving salience.

⸻

2. Probabilities Must Be Directional, Not Precise

Your pseudo-code works mechanically, but the output should be categorical.

Replace numeric output with tiers

Estimated Outcome:
🟢 Likely (70–85%)
🟡 Uncertain (45–70%)
🔴 Risky (≤45%)

This avoids false precision and decision paralysis.

⸻

3. Graduation Progress Is a First-Class System (Not UI Sugar)

The Graduation Progress Card must be state-driven, not derived.

Add to state:

state.graduation = {
    "papers_required": 3,
    "papers_published": 2,
    "thesis_progress": 65,
    "defense_unlocked": False
}

And update it only through milestone logic.

⸻

4. Quals & Paper Events Must “Pin” Themselves

Add:
	•	📌 “Pinned” icon for last milestone
	•	Persistent banner until next milestone

This ensures players cannot forget where they stand.

⸻

IV. V2.22 Missing Pieces You Should Add

5. Risk Forecast on Actions (One-Step Ahead)

In addition to success chance, add:

“⚠️ On failure: −15 Morale, +30 Stress”

This turns opaque punishment into informed consent.

⸻

6. Timeline Awareness (Months Matter)

Add a subtle indicator:

“📆 Month 13 / Typical PhD: Month 60–72”

This prevents early panic and late surprise.

⸻

V. Concrete V2.22 Actionable Checklist

Systems
	•	Priority notification severity levels
	•	Graduation state object (single source of truth)
	•	Categorical probability previews
	•	Failure consequence previews

UI
	•	Persistent Graduation Progress Card
	•	Milestone pinning
	•	Blocking modals for Quals / Acceptance / Defense

⸻

VI. JavaScript Implementation

Graduation Progress Card

This is minimal, framework-agnostic, and matches your current architecture.

⸻

1. HTML (add to index.html)

<div id="graduation-card" class="status-card">
  <h3>🎓 Graduation Progress</h3>
  <div class="progress-item">
    <span>Papers</span>
    <span id="papers-progress">0 / 3</span>
  </div>

  <div class="progress-bar">
    <div id="papers-bar" class="bar-fill"></div>
  </div>

  <div class="progress-item">
    <span>Thesis</span>
    <span id="thesis-progress">0%</span>
  </div>

  <div class="progress-bar">
    <div id="thesis-bar" class="bar-fill"></div>
  </div>

  <div id="defense-status" class="muted-text">
    Defense not yet available
  </div>
</div>


⸻

2. CSS (Tailwind-compatible logic)

.status-card {
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 12px;
}

.progress-bar {
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 6px;
  margin: 4px 0 10px;
}

.bar-fill {
  height: 100%;
  width: 0%;
  background: var(--accent-success);
  border-radius: 6px;
  transition: width 0.3s ease;
}

.muted-text {
  font-size: 0.8rem;
  opacity: 0.7;
}


⸻

3. JavaScript Logic

function updateGraduationCard(state) {
  const papers = state.graduation.papers_published;
  const required = state.graduation.papers_required;
  const thesis = state.graduation.thesis_progress;

  // Text updates
  document.getElementById('papers-progress').textContent =
    `${papers} / ${required}`;
  document.getElementById('thesis-progress').textContent =
    `${thesis}%`;

  // Bars
  document.getElementById('papers-bar').style.width =
    `${(papers / required) * 100}%`;
  document.getElementById('thesis-bar').style.width =
    `${thesis}%`;

  // Defense readiness
  const defenseStatus = document.getElementById('defense-status');
  if (papers >= required) {
    defenseStatus.textContent = "🟢 Defense track unlocked";
    defenseStatus.style.color = "var(--accent-success)";
  } else {
    defenseStatus.textContent = "Defense locked — publish more papers";
    defenseStatus.style.color = "";
  }
}

Call this:
	•	After paper decisions
	•	After thesis progress actions
	•	On game load

⸻

VII. Final Verdict

V2.22 is not a feature release—it’s a trust repair patch.

After this version:
	•	Players should always know:
	•	What just happened
	•	How close they are to finishing
	•	How risky their next action is

If V2.21 saved players from dying,
V2.22 teaches them how not to die.

Once this lands cleanly, V2.23 (Active Networking) will finally feel empowering instead of overwhelming.