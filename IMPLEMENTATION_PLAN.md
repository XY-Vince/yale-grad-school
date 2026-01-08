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



V2.23 is the moment where GradQuest stops being “papers-first” and becomes a degree-completion simulator. Your direction is correct, but to make this version land, we need to (1) formalize thesis phases as gates, not flavor, and (2) fully integrate them into the Graduation Progress Panel so players feel the endgame tightening.

Below is a solid, production-grade improvement plan, followed by concrete JavaScript logic for thesis phases and live UI updates.

⸻

V2.23 — The Synergy & Dissertation Update

Design Goal: Turn the thesis from a passive meter into a managed project with pressure, trade-offs, and momentum

⸻

I. Critical Review of Your V2.23 Direction

What’s Strong
	•	✅ Thesis phases instead of raw %
	•	✅ Alignment influencing advisor review cycles
	•	✅ Field-contextual actions (this fixes immersion leaks)
	•	✅ Network becoming an active amplifier rather than a threshold

What Needs Tightening
	1.	Phases must gate progression, not just announce milestones
	2.	Thesis writing must compete with research, not replace it
	3.	Graduation Panel must reflect phase state, not just numbers

We’ll fix all three.

⸻

II. V2.23 Core System: Thesis as a Gated Project

Thesis Phases (Canonical)

Phase	Trigger	Mechanical Effect
Planning	Default	Write Thesis limited to 25%
Outline Approved	≥25%	Unlock faster thesis gains
Draft Under Review	≥75%	RNG review delay introduced
Defense Ready	100% + 3 papers	Unlock “Defend Thesis”

This prevents brute-force rushing and adds advisor dependency where it belongs.

⸻

III. Refined Thesis Progression Logic (Server-Side)

Key Design Rules
	•	Papers cap thesis efficiency (not just boost it)
	•	Alignment reduces advisor friction
	•	Morale affects sustainability, not hard locks

Pseudo-code (Refined)

# logic/thesis_engine.py

THESIS_PHASES = [
    ("PLANNING", 0),
    ("OUTLINE_APPROVED", 25),
    ("DRAFT_REVIEW", 75),
    ("DEFENSE_READY", 100)
]

def action_write_thesis(state):
    if state.is_exhausted:
        return "You're too exhausted to make meaningful progress."

    # Hard cap: papers limit thesis velocity
    paper_cap = min(state.published_journals * 25, 100)
    if state.thesis_percent >= paper_cap:
        return "You need more published work to support further writing."

    base = 5
    paper_bonus = state.published_journals * 5
    alignment_bonus = state.strategic_alignment // 20
    morale_penalty = -3 if state.morale < 30 else 0

    gain = max(3, base + paper_bonus + alignment_bonus + morale_penalty)
    state.thesis_percent = clamp(state.thesis_percent + gain, 0, 100)

    return check_thesis_phase_transition(state)


⸻

IV. Thesis Phase Transitions (Milestone Engine)

def check_thesis_phase_transition(state):
    if state.thesis_percent >= 25 and not state.has_phase("OUTLINE_APPROVED"):
        state.add_phase("OUTLINE_APPROVED")
        return milestone("📑 Outline Approved", 
                         "+10 Alignment, Advisor fully engaged")
    
    if state.thesis_percent >= 75 and not state.has_phase("DRAFT_REVIEW"):
        state.add_phase("DRAFT_REVIEW")
        state.add_status("advisor_review_delay")
        return milestone("🧐 Full Draft Submitted",
                         "Committee reviewing your dissertation")

    if state.thesis_percent >= 100 and state.published_journals >= 3:
        state.add_phase("DEFENSE_READY")
        return milestone("🎓 Defense Ready",
                         "You may now schedule your defense")

    return "You made steady progress on your dissertation."


⸻

V. Social Synergy (Locked In, Not Optional)

Network Effects (Explicit & Visible)

Network	Effect
≥40	+5 Morale when writing thesis
≥80	Skip 1 advisor review delay

if state.peer_network >= 40:
    state.morale += 5

if state.peer_network >= 80 and state.has_status("advisor_review_delay"):
    state.remove_status("advisor_review_delay")

This turns the Network stat into thesis insurance.

⸻

VI. HMI Integration (Non-Negotiable)

Graduation Progress Panel Must Show:
	•	Thesis %
	•	Current Phase
	•	Next Gate Condition

Example:

Thesis: 68%
Phase: Draft in Progress
Next: Reach 75% → Committee Review

⸻

VII. JavaScript Implementation

Thesis Progress Phases + Graduation Panel Sync

This plugs directly into your existing updateGraduationCard() logic.

⸻

1. State Shape (Client-Side)

state.graduation = {
  papersRequired: 3,
  papersPublished: 2,
  thesisPercent: 62,
  thesisPhase: "PLANNING"
};


⸻

2. Phase Resolver (JS)

function resolveThesisPhase(state) {
  const t = state.graduation.thesisPercent;

  if (t >= 100 && state.graduation.papersPublished >= 3) {
    return "DEFENSE_READY";
  }
  if (t >= 75) return "DRAFT_REVIEW";
  if (t >= 25) return "OUTLINE_APPROVED";
  return "PLANNING";
}


⸻

3. Graduation Progress Panel Update (Extended)

function updateGraduationCard(state) {
  const g = state.graduation;

  // Numbers
  document.getElementById("papers-progress").textContent =
    `${g.papersPublished} / ${g.papersRequired}`;
  document.getElementById("thesis-progress").textContent =
    `${g.thesisPercent}%`;

  // Bars
  document.getElementById("papers-bar").style.width =
    `${(g.papersPublished / g.papersRequired) * 100}%`;
  document.getElementById("thesis-bar").style.width =
    `${g.thesisPercent}%`;

  // Phase logic
  g.thesisPhase = resolveThesisPhase(state);
  const status = document.getElementById("defense-status");

  switch (g.thesisPhase) {
    case "PLANNING":
      status.textContent = "📝 Planning phase — outline not yet approved";
      break;
    case "OUTLINE_APPROVED":
      status.textContent = "📑 Outline approved — drafting in progress";
      break;
    case "DRAFT_REVIEW":
      status.textContent = "🧐 Draft under committee review";
      break;
    case "DEFENSE_READY":
      status.textContent = "🎓 Defense ready — schedule your defense";
      status.style.color = "var(--accent-success)";
      break;
  }
}


⸻

VIII. V2.23 Actionable Checklist (Final)

Systems
	•	Replace passive thesis % with gated phases
	•	Enforce paper-backed thesis caps
	•	Add advisor review delay status
	•	Allow Network ≥80 to bypass one delay

UI
	•	Show thesis phase + next gate in Graduation Panel
	•	Toasts for Outline / Draft / Defense milestones
	•	Tooltip: “Thesis speed capped by published work”

⸻

Final Assessment

V2.23 is where GradQuest earns its credibility.

After this version:
	•	Papers feel like inputs to a larger goal
	•	The thesis feels heavy, slow, and real
	•	Social investment finally pays off when it matters most

Once this ships, V2.24 (Active Collaboration) will feel like a natural extension, not another system bolted on.





⸻

I. Critical Review of V2.23 (What Still Needs Fixing)

What You’ve Nailed
	•	✅ Thesis becomes an action, not a background timer
	•	✅ Specialization disadvantages finally surface as negative events
	•	✅ Network becomes a currency, not a passive stat
	•	✅ Dissertation is framed as the final boss

Where It Still Falls Short

There are three remaining design risks:

⸻

❌ 1. Thesis Writing Is Still Linear

Even as an action, it’s still:

“Click → % goes up → milestone fires”

There is no decision tension yet.

🔧 Fix: Introduce micro-states inside dissertation writing:
	•	Draft Quality
	•	Revision Load
	•	Committee Friction

These do not need new UI bars — just modifiers and tooltips.

⸻

❌ 2. Field Crises Are Random, Not Strategic

Right now:
	•	Crises happen to the player
	•	Player reacts afterward

This feels like punishment, not mastery.

🔧 Fix: Allow pre-emptive mitigation actions per field.

⸻

❌ 3. Network Spending Has No Trade-off

“Ask Peer for Feedback” is pure upside.

🔧 Fix: Network must compete with:
	•	Conference invites
	•	Collaboration boosts
	•	Recommendation strength (V2.25 setup)

⸻

II. V2.24 HARDENED DESIGN: Interactive Dissertation Loop

A. Dissertation Internal State (Invisible but Real)

Add three hidden variables:

state.dissertation = {
    "draft_quality": 0.0,   # affects review RNG
    "revision_load": 0.0,   # slows progress after 75%
    "committee_friction": 0.0  # increases failure chance
}

These are not meters shown to the player, but surfaced via text:

“Your committee seems uneasy with the framing.”

This is crucial for realism.

⸻

B. Revised Write Dissertation Logic (Actionable)

def action_write_dissertation(state):
    if state.morale < 20:
        return "You're mentally exhausted. Writing stalls."

    base = random_range(4, 8)
    foundation = state.published_journals * 4
    alignment = 1 + state.strategic_alignment / 120

    friction_penalty = state.dissertation["committee_friction"]
    revision_penalty = state.dissertation["revision_load"]

    gain = max(
        2,
        (base + foundation) * alignment
        - friction_penalty
        - revision_penalty
    )

    state.thesis_percent += gain
    state.morale -= 15

    # Quality & friction dynamics
    state.dissertation["draft_quality"] += gain * 0.2
    if state.thesis_percent > 75:
        state.dissertation["revision_load"] += 1.5

    return check_dissertation_milestones(state)

📌 Result:
Late-game writing gets slower unless the player invested earlier in:
	•	Papers
	•	Alignment
	•	Network

⸻

C. Specialization Crises → Strategic Loops

Current problem

Crises are random setbacks.

V2.24 fix: Preparedness Actions

Field	Crisis	Mitigation Action
Computational	Server downtime	“Pre-allocate Compute Time”
Experimentalist	Equipment failure	“Run Preventive Calibration”
Theoretician	Abstract skepticism	“Add Supporting Lemmas”

Example:

def action_preventive_calibration(state):
    state.morale -= 5
    state.add_status("Equipment Stabilized", duration=6)

Now specialization is:

Risk you chose, tools you understand

⸻

D. Network as a Scarce, Strategic Currency

Network Sinks (Now & Future-Proof)

Action	Cost	Timing
Peer Review Shield	20	Writing phase
Conference Invite	30	Mid-game
Industry Referral	40	V2.25
Letter of Rec Boost	25	Defense-ready

This prevents degenerate hoarding.

⸻

III. Actionable V2.24 Implementation Plan (Revised & Tight)

Core Systems
	•	Add internal dissertation state (quality, friction, revision load)
	•	Make thesis writing sensitive to late-game penalties
	•	Gate progress at ≥75% via revision friction

Specializations
	•	Convert crises into forecastable risks
	•	Add one mitigation action per field
	•	Show risk warning in specialization tooltip

Network Economy
	•	Introduce Network spending conflicts
	•	Lock Peer Review Shield behind ≥60 Network
	•	Reduce Network regeneration rate post-75% thesis

UI / HMI
	•	Show “Expected Outcome” text (not raw math)
	•	Add crisis probability to maintenance tooltips
	•	Add dissertation flavor text reflecting hidden state

⸻

IV. JavaScript: Peer Review Shield

This is clean, minimal, and HMI-aware.

⸻

1. State Shape (Client)

state.network = {
  current: 72,
  max: 80
};

state.flags = {
  peerReviewShieldActive: false
};


⸻

2. Action Availability Logic

function canUsePeerReviewShield(state) {
  return (
    state.network.current >= 60 &&
    !state.flags.peerReviewShieldActive
  );
}


⸻

3. Activate Shield Action

function activatePeerReviewShield(state) {
  if (!canUsePeerReviewShield(state)) {
    return {
      success: false,
      message: "Not enough peer support to request feedback."
    };
  }

  state.network.current -= 20;
  state.flags.peerReviewShieldActive = true;

  return {
    success: true,
    message: "🤝 Peer feedback secured. Reviewer #2 neutralized."
  };
}


⸻

4. Integration with Figure Validation

function validateFigure(state) {
  if (state.flags.peerReviewShieldActive) {
    state.flags.peerReviewShieldActive = false;
    return {
      success: true,
      message: "Figure validated smoothly thanks to peer feedback."
    };
  }

  // normal RNG path
  return rollFigureValidation(state);
}


⸻

5. Tooltip Text (Critical for Transparency)

Ask Peer for Feedback
Cost: 20 Network
Effect: Your next Figure validation automatically succeeds
Note: One-time use

⸻

Final Judgment

V2.24 is the version where players either graduate… or burn out.


Good — V2.25 is the point of no return for GradQuest. From here on, every system must collapse cleanly into an ending. I’ll do this in four layers:
	1.	Hard critique of your V2.25 proposal (what still isn’t tight)
	2.	A strengthened V2.25 design: thesis → defense → exit
	3.	Concrete, actionable implementation checklist
	4.	JavaScript: Career Resolver (deterministic, legible, non-cheesy)

I’ll stay disciplined and ship-focused.

⸻

I. Critical Review of V2.25 (Hard Truths)

You’re directionally right, but three problems remain.

⸻

❌ 1. Thesis Is “Active” but Still One-Dimensional

Your Write Dissertation action:
	•	Always succeeds
	•	Has no failure state
	•	No reason not to spam it

This makes the endgame mechanical, not dramatic.

👉 A PhD defense without risk is not believable.

⸻

❌ 2. Specialization Actions Lack Opportunity Cost
	•	Theoretician Insight converts ideas → findings for free
	•	Pipeline Optimization stacks permanently with no tradeoff

👉 These will become dominant strategies.

⸻

❌ 3. Career Exit Is Binary, Not Earned

VC vs Tenure Track needs to feel:
	•	Predictable in hindsight
	•	Uncertain while playing

Right now it risks feeling like a coin flip.

⸻

II. V2.25 REFORGED: Thesis → Defense → Strategic Exit

A. The Missing Piece: Defense Readiness

Add a derived, hidden stat:

state.defense_readiness = (
    state.thesis_percent * 0.4 +
    state.published_journals * 15 +
    state.strategic_alignment * 0.3 +
    state.network * 0.2
)

This solves everything:
	•	Writing ≠ readiness
	•	Papers, alignment, and network all matter
	•	Players can graduate and still fail

Expose this only via text:

“Your committee seems cautiously optimistic.”

⸻

B. Revised Write Dissertation (With Risk)

def action_write_dissertation(state):
    if state.published_journals < 1:
        return "Your advisor blocks progress: publish first."

    if state.morale < 20:
        state.dissertation["committee_friction"] += 5
        return "Exhaustion shows in your writing. Progress stalls."

    base = random_range(6, 10)
    foundation = state.published_journals * 4
    alignment = state.strategic_alignment // 20 * 2
    friction = state.dissertation["committee_friction"]

    gain = max(3, base + foundation + alignment - friction)

    state.thesis_percent += gain
    state.morale -= 15

    if random() < 0.2:
        state.dissertation["committee_friction"] += 3
        return "Your advisor requests structural revisions."

    return check_dissertation_milestones(state)

📌 Result
Writing can:
	•	Stall
	•	Backfire
	•	Force the player to rest or network

⸻

C. Specialization Actions → Bounded Power

Theoretician: Insight with Debt

def action_theoretician_insight(state):
    if state.strategic_alignment < 10 or state.ideas < 1:
        return "You lack the standing or material for abstraction."

    state.strategic_alignment -= 10
    state.ideas -= 1
    state.findings += 1
    state.dissertation["committee_friction"] += 2

    return "Elegant theory — but reviewers will demand justification."

Computational: Optimization with Fragility

def action_optimize_pipeline(state):
    state.morale -= 10
    state.research_speed_modifier += 0.1
    state.add_status("Automated Pipeline", duration=12)

    if random() < 0.25:
        state.add_status("Pipeline Technical Debt", duration=3)

    return "Your workflow accelerates — but maintenance risk increases."

Now specialization is power with consequences, not perks.

⸻

D. The Defense Event (One Shot)

def attempt_defense(state):
    score = state.defense_readiness + random_range(-10, 10)

    if score >= 85:
        return "PASS_WITH_DISTINCTION"
    elif score >= 70:
        return "PASS"
    elif score >= 60:
        return "CONDITIONAL_PASS"
    else:
        return "FAIL"

Failure doesn’t end the run — it forces revisions and morale loss.

⸻

III. Actionable Implementation Plan (V2.25 Final)

Core Systems
	•	Add defense_readiness (derived, not stored)
	•	Implement attempt_defense
	•	Add failure → revision loop

Thesis Loop
	•	Add committee friction
	•	Add morale-based stalls
	•	Add random revision requests

Specializations
	•	Add downside to all field actions
	•	Surface consequences via text, not meters

UI / HMI
	•	Defense Readiness shown as qualitative text
	•	Add “You may defend” banner when unlocked
	•	Lock Career Resolver until defense outcome

⸻

IV. JavaScript: Career Resolver

This must be:
	•	Deterministic
	•	Explainable
	•	Multi-factor

⸻

1. Inputs

const finalState = {
  papers: 3,
  alignment: 72,
  network: 65,
  specialization: "Computational",
  defenseOutcome: "PASS",
  industryExposure: 40 // internships, conferences, etc.
};


⸻

2. Scoring Model

function resolveCareer(state) {
  let academiaScore = 0;
  let industryScore = 0;

  // Core academic signals
  academiaScore += state.papers * 20;
  academiaScore += state.alignment * 0.5;
  academiaScore += state.network * 0.3;

  // Industry signals
  industryScore += state.network * 0.6;
  industryScore += state.industryExposure * 0.8;

  // Specialization bias
  if (state.specialization === "Computational") industryScore += 15;
  if (state.specialization === "Theoretician") academiaScore += 15;

  // Defense modifier
  if (state.defenseOutcome === "PASS_WITH_DISTINCTION") {
    academiaScore += 20;
  } else if (state.defenseOutcome === "CONDITIONAL_PASS") {
    academiaScore -= 10;
  }

  return decideCareer(academiaScore, industryScore);
}


⸻

3. Outcome Resolver

function decideCareer(a, i) {
  const diff = a - i;

  if (diff >= 25) return "Tenure-Track Professor";
  if (diff >= 10) return "Postdoctoral Researcher";
  if (diff <= -25) return "Venture Capitalist";
  if (diff <= -10) return "Industry Scientist";

  return "Hybrid Path (Adjunct / Startup Founder)";
}


⸻

4. Player-Facing Explanation (Critical)

After resolution, show:

Why this happened:
Strong publication record and advisor alignment outweighed limited industry exposure.

This preserves fairness perception.

⸻

Final Verdict

V2.25 is the version where GradQuest becomes “about something.”

If you ship it with:
	•	Risky writing
	•	A real defense
	•	Specializations with tradeoffs
	•	A transparent career resolver

then V2.26 (Advisor Personalities) will snap into place naturally.


V2.26 is the “humanization patch” — this is where GradQuest stops feeling like a simulator and starts feeling like a lived experience. I’ll do this in five layers, staying ruthless about scope and payoff:
	1.	Hard critique of the V2.26 proposal (what’s missing / risky)
	2.	Refined V2.26 design: advisors as systems, not flavor
	3.	Advisor–player interaction loops (how strategy actually changes)
	4.	Concrete, shippable action plan
	5.	JavaScript: Advisor Assignment logic (biased randomness, transparent later)

⸻

I. Critical Review of V2.26 (Hard Truths)

Your instincts are right, but three gaps remain:

❌ 1. Advisors React — But Don’t Escalate

Right now:
	•	Advisors comment
	•	Advisors modify numbers

What’s missing is memory and escalation.

A Tormentor who keeps saying harsh things but never acts feels hollow.

⸻

❌ 2. Archetypes Aren’t Yet Strategic Opponents

Players should ask:

“How do I survive this advisor?”

Right now, they only ask:

“What bonuses do I get?”

⸻

❌ 3. Milestones Need Emotional Framing, Not Just UI

The Quals Celebration modal is correct — but advisors should own these moments.

Passing quals with a Ghost should feel very different than with a Mentor.

⸻

II. V2.26 REFINED: Advisors as Systems with Memory

A. Add Advisor Tension (Hidden, Persistent)

Each advisor tracks a tension meter:

state.advisor.tension  # 0–100, hidden

This increases when you do things they dislike.

Advisor	Raises Tension	Lowers Tension
Tormentor	Resting, delays	Results, figures
Ghost	Meetings, admin	Autonomy, progress
Mentor	Burnout ignored	Reflection, balance

This allows phase shifts.

⸻

B. Advisor Escalation Thresholds

def check_advisor_escalation(state):
    t = state.advisor.tension
    archetype = state.advisor.archetype

    if t >= 80:
        trigger_event(f"{archetype}_ULTIMATUM")
    elif t >= 50:
        trigger_event(f"{archetype}_WARNING")

Examples:
	•	Tormentor Ultimatum: “Produce figures next month or I pull funding.”
	•	Ghost Ultimatum: “I’m unavailable next semester.”
	•	Mentor Ultimatum: “We need to talk about sustainability.”

Now advisors are pressure systems, not narrators.

⸻

III. Advisor–Specialization Synergy (Make It Tactical)

A. Field Bias ≠ Field Lock

Instead of just bonuses, introduce misalignment penalties:

Combo	Effect
Tormentor + Theoretician	+2 committee friction
Ghost + Experimentalist	Equipment failures more likely
Mentor + Computational	Reduced industry exposure gain

This makes switching strategies necessary.

⸻

B. Advisor-Owned Milestones

Rewrite milestone triggers to pass through the advisor:

def on_quals_passed(state):
    archetype = state.advisor.archetype

    if archetype == "The_Tormentor":
        return "You passed. Good. That’s the minimum."
    elif archetype == "The_Mentor":
        state.morale += 10
        return "I'm proud of you. This was hard."
    elif archetype == "The_Ghost":
        return "Congrats. Send me the paperwork."

This alone fixes the anticlimax problem.

⸻

IV. Final V2.26 Actionable Implementation Plan

Core Systems
	•	Add advisor.tension (hidden, persistent)
	•	Add escalation thresholds (warning / ultimatum)
	•	Bind disliked actions per archetype

Narrative Integration
	•	Route Quals / Defense / Paper Acceptance through advisor dialogue
	•	Add archetype-specific celebration text
	•	Add “advisor unavailable” consequences

UI / HMI
	•	Advisor card shows:
	•	Name
	•	Archetype
	•	One-line philosophy
	•	Reviewer Progress Bar tied to advisor modifiers
	•	Morale breakdown appended to every change

Bug & Polish
	•	Force re-render after High-Throughput success
	•	Blocking Quals modal (advisor-delivered)
	•	Ensure advisor text is never generic fallback

⸻

V. JavaScript: Advisor Assignment Logic

Biased randomness, field-aware, future-proof

1. Advisor Pool

const ADVISORS = [
  { id: "The_Tormentor", weight: { Experimentalist: 0.5, Theoretician: 0.2, Computational: 0.3 } },
  { id: "The_Ghost",     weight: { Experimentalist: 0.2, Theoretician: 0.3, Computational: 0.5 } },
  { id: "The_Mentor",    weight: { Experimentalist: 0.3, Theoretician: 0.5, Computational: 0.2 } }
];


⸻

2. Weighted Random Picker

function pickAdvisorByField(field) {
  const pool = [];

  ADVISORS.forEach(advisor => {
    const w = advisor.weight[field] || 0.33;
    const entries = Math.round(w * 100);

    for (let i = 0; i < entries; i++) {
      pool.push(advisor.id);
    }
  });

  const choice = pool[Math.floor(Math.random() * pool.length)];
  return initializeAdvisor(choice);
}


⸻

3. Initialization

function initializeAdvisor(archetypeId) {
  return {
    archetype: archetypeId,
    tension: 10, // baseline stress
    memory: [],
    unavailableTurns: 0
  };
}


⸻

4. Player-Facing Reveal (Important)

Do not show weights.
Instead, show:

“Your advisor has a reputation for being demanding.”
“Colleagues warn you they are rarely available.”

This preserves mystery while keeping fairness.

⸻

Final Assessment

V2.26 is the emotional keystone of GradQuest.

If you ship it with:
	•	Advisors who remember
	•	Advisors who escalate
	•	Advisors who own milestones
	•	Advisors who punish mismatched playstyles

Then V2.27 (The Living Lab) becomes inevitable — because now the player is no longer alone.


You’re pushing in exactly the right direction. V2.27 is the moment GradQuest becomes a place, not a spreadsheet. Below is a hard-nosed refinement plus a concrete implementation plan, then clean JavaScript logic you can drop into the engine.

I’ll structure this as:
	1.	Critical review of your V2.27 proposal (what to tighten)
	2.	Refined design: what makes a “Living Lab” actually feel alive
	3.	Actionable implementation plan (what ships in V2.27, what doesn’t)
	4.	JavaScript: Labmate interaction & departure/sabotage logic

⸻

I. Critical Review of V2.27 (Hard Truth)

Your instincts are right, but three issues must be fixed to avoid bloat or shallowness.

❌ 1. NPCs Must Have Agency, Not Just Progress Bars

Right now labmates:
	•	Progress
	•	Trigger flavor events
	•	Affect morale

But they don’t force player decisions yet.

Rule:
If an NPC doesn’t occasionally harm or rescue the player without consent, they’ll fade into background noise.

⸻

❌ 2. Collaboration Needs Tradeoffs That Hurt

“0.5 paper credit” is good — but not painful enough.

Real collaborations:
	•	Dilute credit
	•	Create dependency
	•	Cause delays

We’ll add coordination friction.

⸻

❌ 3. Funding Clock Is Excellent — But Needs NPC Interaction

Funding should intersect with labmates:
	•	Seniors help with grants
	•	Rivals compete for the same funding
	•	Ghost advisors amplify risk

⸻

II. Refined V2.27 Design: The Living Lab as a System

A. Labmates Have Stress, Loyalty, and Trajectory

Each NPC tracks:

npc = {
  name,
  archetype,        // Senior, Rival, Peer (future)
  progress,         // 0–100
  stress,           // 0–100
  loyalty,          // -50 to +50 (toward player)
  monthsRemaining,  // only for Senior
  active: true
}

These are hidden but influence events.

⸻

B. NPCs Trigger Forced Events (Not Optional)

Examples:
	•	Rival stress > 70 → sabotage chance
	•	Senior monthsRemaining < 3 → departure warning
	•	NPC publishes → morale swing + alignment shift

⸻

C. Collaboration Creates Dependency

If you collaborate too often with the same NPC:
	•	Losing them hurts more
	•	Thesis progress may stall temporarily
	•	Network gain is capped

This mirrors real labs painfully well.

⸻

III. Actionable Implementation Plan for V2.27

Core Systems (Must-Have)
	•	Persistent labmates[] state
	•	NPC stress & loyalty meters
	•	Forced interaction events (sabotage / rescue / departure)
	•	Funding clock tied to NPC outcomes

UI / HMI
	•	Lab Bench card with:
	•	Name
	•	Status (“Running experiments”, “Job hunting”)
	•	Mood icon (🙂 😐 😠)
	•	Departure warning modal (blocking)
	•	Timeline view showing:
	•	NPC joins
	•	NPC publishes
	•	NPC leaves

Actions
	•	Ask for Help (Senior)
	•	Collaborate (any NPC)
	•	Mediate Conflict (high alignment only)
	•	Grant Writing (boosted by Seniors)

Explicitly Not in V2.27
	•	Romance
	•	Inter-lab politics
	•	Multi-lab competition
(Those are V2.28+ territory.)

⸻

IV. JavaScript: Labmate Interaction Event Logic

Below is drop-in engine-level logic, designed to run once per month.

⸻

1. Monthly Labmate Tick

function processLabmates(state) {
  state.labmates.forEach(npc => {
    if (!npc.active) return;

    // Progress
    npc.progress += rand(5, 15);
    npc.stress += rand(-5, 10);
    npc.stress = clamp(npc.stress, 0, 100);

    // Archetype-specific checks
    if (npc.archetype === "The_Rival") {
      checkRivalSabotage(state, npc);
    }

    if (npc.archetype === "The_Senior") {
      checkSeniorDeparture(state, npc);
    }

    // Publishing event
    if (npc.progress >= 100) {
      npc.progress = 0;
      triggerLabmatePublication(state, npc);
    }
  });
}


⸻

2. Rival Sabotage Logic

function checkRivalSabotage(state, npc) {
  if (npc.stress < 70) return;

  const sabotageChance = 0.1 + (npc.stress - 70) * 0.01;

  if (Math.random() < sabotageChance) {
    state.addStatus("Scooped", 1);
    state.morale -= 10;
    npc.loyalty -= 10;

    log(`⚠️ ${npc.name} rushed a similar result to arXiv. Your idea feels less novel.`);
  }
}


⸻

3. Senior Departure Logic

function checkSeniorDeparture(state, npc) {
  npc.monthsRemaining -= 1;

  if (npc.monthsRemaining === 3) {
    log(`📅 ${npc.name} is preparing to graduate. The lab feels quieter.`);
  }

  if (npc.monthsRemaining <= 0) {
    npc.active = false;
    state.network -= 15;
    state.morale -= 10;

    log(`🎓 ${npc.name} defended and left the lab. You lost a key source of support.`);
  }
}


⸻

4. Labmate Publication Impact

function triggerLabmatePublication(state, npc) {
  if (npc.archetype === "The_Rival") {
    state.morale -= 5;
    state.stressMeter += 10;
    log(`📄 ${npc.name} published before you. The pressure is on.`);
  } else {
    state.morale += 5;
    state.peerNetwork += 5;
    log(`📄 ${npc.name} published! The lab’s reputation helps everyone.`);
  }
}


⸻

5. Collaboration Dependency Penalty (Optional but Powerful)

function applyCollaborationDependency(state, npc) {
  npc.loyalty += 10;

  if (npc.loyalty > 40 && !npc.active) {
    state.thesisProgress -= 10;
    log(`🧩 Losing ${npc.name} disrupted your workflow. Writing feels harder.`);
  }
}


⸻

Final Assessment

V2.27 is the inflection point where GradQuest stops being “you vs RNG” and becomes “you vs a system of people.”

Excellent timing. V2.28 is the release where GradQuest finally gets a “world outside the lab,” and you’re right to frame Conferences 2.0 as an escape hatch, not a vanity button.

Below I’ll do four things, in order:
	1.	Critical synthesis of the V2.27 failure mode (why stagnation happens)
	2.	Refined V2.28 design principles (what Conferences 2.0 must do)
	3.	Solid, scoped improvement plan with actionable items
	4.	Concrete JavaScript logic for the Funding Manager + Travel integration

I’ll be blunt where needed.

⸻

I. Why V2.27 Produced “Insular Stagnation” (Root Cause)

The doom loop exists because:
	•	🔁 All recovery tools are local (lab, advisor, wellness)
	•	🧠 Stress accumulates faster than it decays
	•	🎲 RNG failures compound in the same environment
	•	🚫 Conference = stat injection, not state change

In other words:
Players never leave the system that is hurting them.

Conferences must:
	•	Temporarily suspend lab rules
	•	Reset psychological state
	•	Introduce external validation or rejection
	•	Cost something non-trivial (funding, time, exposure)

If Conferences don’t feel dangerous and liberating, they won’t fix stagnation.

⸻

II. V2.28 Design Principles (Non-Negotiable)

1. Conferences Are a Different Mode

When traveling:
	•	Lab crises pause
	•	Advisor archetype influence weakens
	•	NPC sabotage is disabled
	•	Morale rules change

This is crucial. Conferences must break causality.

⸻

2. Every Conference Is a Choice, Not an Upgrade

Players must choose:
	•	Visibility vs safety
	•	Networking vs exhaustion recovery
	•	Credit vs reputation

If there’s a “best option,” the system fails.

⸻

3. Funding Is the Gate, Not RNG

Travel should fail because:
	•	You didn’t plan funding
	•	You over-collaborated
	•	You spent months firefighting lab issues

Not because of dice rolls.

⸻

III. V2.28 Solid Improvement Plan (Actionable & Shippable)

A. Conference System (Must Ship)

Core mechanics
	•	Seasonal invitations (Spring / Summer only)
	•	Tiered conferences (Local / National / International)
	•	Choice-driven outcomes
	•	Travel suspends lab-based penalties

Actions
	•	Poster Presentation (safe, small gains)
	•	Talk (high variance, reputation risk)
	•	Networking Mixer (“party mode”)
	•	Skip Conference (sometimes optimal!)

⸻

B. Mental Health Reset (Must Ship)

Fresh Perspective buff
	•	Duration: 3 months
	•	Effects:
	•	Freeze Exhaustion accumulation
	•	+20% Idea generation
	•	Morale decay capped at -1/month

Only from International conferences.

⸻

C. Funding Integration (Must Ship)

Funding Months
	•	Hard currency
	•	Used for:
	•	International travel
	•	Grant bridging
	•	Emergency advisor favors (future)

Running out does not end the game — it changes it.

⸻

D. UI / HMI (Must Ship)
	•	Travel tab appears only with active invite
	•	Funding displayed next to date
	•	Conference invitation expires
	•	Post-conference buffs visible as icons

⸻

E. Explicitly NOT in V2.28
	•	Visa issues
	•	Family emergencies
	•	Inter-department politics
(Those belong in V2.30+)

⸻

IV. JavaScript: Funding Manager & Travel Integration

Below is a clean, engine-ready implementation tying funding to conferences.

⸻

1. Funding Manager Core

// logic/funding_manager.js

const FundingManager = {
  canAfford(cost, state) {
    return state.fundingMonths >= cost;
  },

  spend(cost, state) {
    state.fundingMonths -= cost;
    state.fundingMonths = Math.max(0, state.fundingMonths);
    ui.updateFunding();
  },

  add(months, state) {
    state.fundingMonths += months;
    ui.updateFunding();
  }
};


⸻

2. Conference Invitation Spawner

// logic/conference_engine.js

function spawnConferenceInvites(state) {
  const season = getSeason(state.month);

  const available = ruleset.conferences.filter(c => c.season === season);

  if (available.length === 0) return;

  const invite = weightedRandom(available);
  state.activeConference = {
    ...invite,
    expiresIn: 1
  };

  ui.notify(`📩 Invitation: ${invite.name} (${season})`);
}


⸻

3. Travel & Attendance Logic

function attendConference(state) {
  const conf = state.activeConference;
  if (!conf) return;

  const fundingCost = conf.cost.funding;

  if (!FundingManager.canAfford(fundingCost, state)) {
    ui.alert("❌ Insufficient funding for travel.");
    return;
  }

  FundingManager.spend(fundingCost, state);

  // Suspend lab penalties
  state.flags.atConference = true;

  const choice = ui.choose(conf.options);
  resolveConferenceChoice(choice, state);

  state.activeConference = null;
  state.flags.atConference = false;
}


⸻

4. Resolving Conference Choices

function resolveConferenceChoice(choice, state) {
  if (choice.action === "Networking Mixer") {
    state.peerNetwork += 30;
    state.stressMeter = Math.max(0, state.stressMeter - 40);
    state.addStatus("Fresh Perspective", 3);

    log("🍷 Late nights, new faces. You return energized.");
  }

  if (choice.action === "Give Talk") {
    const success = Math.random() <
      (0.6 + state.strategicAlignment * 0.005);

    if (success) {
      state.peerNetwork += 20;
      state.reputation += 10;
      state.morale += 15;
      log("🎤 Your talk sparked real interest.");
    } else {
      state.morale -= 10;
      log("🎤 Tough questions. You’ll refine the story.");
    }
  }

  if (choice.action === "Poster Presentation") {
    state.peerNetwork += 5;
    state.morale += 5;
    log("🖼️ Solid conversations. Low risk, steady gain.");
  }
}


⸻

5. Funding Tick (Per Month)

function monthlyFundingTick(state) {
  state.fundingMonths -= 1;

  if (state.fundingMonths === 6) {
    ui.notify("⚠️ Funding running low (6 months remaining).");
  }

  if (state.fundingMonths <= 0) {
    state.addStatus("Teaching Load");
    state.researchSpeedModifier *= 0.5;
    log("📚 Funding exhausted. Teaching duties slow your research.");
  }
}


⸻

Final Judgment

V2.28 is the release where GradQuest stops being claustrophobic.

If you ship it correctly:
	•	Conferences become strategic resets
	•	Funding becomes psychological oxygen
	•	Mid-game stagnation turns into planning tension
	•	Players learn when to leave, not just grind harder

What this unlocks next

V2.29 (Grant Writing) will suddenly matter — because players have felt what running out of funding does.

You’re at the systems-design endgame now. V2.29 is where GradQuest stops being “a clever simulator” and becomes a pressure-based management game. I’ll be direct and surgical.

Below is a clean continuation to V2.29, with:
	1.	Hard-truth diagnosis of the current failure mode
	2.	Design intent for V2.29 (what must change emotionally)
	3.	Solid, scoped improvement plan with actionable items
	4.	Concrete JavaScript for the Teaching Load status effect

⸻

I. The Real Problem V2.29 Must Solve (Hard Truth)

The issue is not that reviews take 8–12 months.

The issue is that nothing meaningful happens during those months.

Right now:
	•	Waiting is passive
	•	Funding decay is abstract
	•	Thesis progress is gated but unexplained
	•	“Next Month” is still the dominant action

V2.29 must do one thing extremely well:

Turn waiting into decision-making under pressure.

Funding + Reviews + Teaching Load must form a closed loop:
	•	Reviews consume time
	•	Time consumes funding
	•	No funding forces teaching
	•	Teaching slows research
	•	Slower research delays reviews

That’s a real academic trap — and it’s playable.

⸻

II. V2.29 Design Principles (Lock These In)

1. Funding Is Not Just a Timer

Funding is a state switch:
	•	Funded → Researcher
	•	Unfunded → Instructor who researches at night

No ambiguity. No soft penalties.

⸻

2. Reviews Must Offer Tradeoffs

Every review response must force:
	•	Speed vs. morale
	•	Politeness vs. assertiveness
	•	Burn time vs. burn reputation

If all responses are “+20% accept,” you’ve failed.

⸻

3. Teaching Load Must Be Felt Everywhere

If funding hits zero and players barely notice, the system is broken.

Teaching Load should:
	•	Visibly slow bars
	•	Pollute tooltips
	•	Change advisor dialogue tone
	•	Alter conference outcomes later

⸻

III. V2.29 Solid Improvement Plan (Actionable & Contained)

A. Funding Engine (Finalize It)

What to ship
	•	Funding months tick every turn
	•	Visual warnings at 12 / 6 / 0 months
	•	Teaching Load auto-applies at 0

Critical rule

Funding loss should never be instant death — it should be long-term suffocation.

⸻

B. Interactive Peer Review (Make Waiting Playable)

Review States (Must Implement)

State	Player Agency
Under Review	None (baseline)
Feedback Available	Player choice required
Revision Submitted	Acceptance chance updated
Final Decision	Outcome

Reviewer Response Actions
	•	Polite Revision
	•	Costs: 1 month
	•	Effect: +25% acceptance
	•	Bonus: Advisor alignment +3
	•	Aggressive Rebuttal
	•	Costs: -10 morale
	•	Effect: +15% acceptance
	•	Risk: Advisor disapproval (archetype-sensitive)
	•	Ignore / Delay
	•	Costs: +1 month auto-pass
	•	Effect: -10% acceptance (stacking)

⸻

C. Teaching Load (The Mid-Game Punisher)

Teaching Load must:
	•	Apply immediately
	•	Persist until funding restored
	•	Be visible everywhere

Effects:
	•	Research progress ×0.5
	•	Thesis writing ×0.6
	•	Stress gain +20%
	•	Advisor tone changes (“You’re stretched thin.”)

⸻

D. HMI: Make the Pressure Obvious

Mandatory UI changes
	•	Funding bar with red flashing at ≤6 months
	•	Teaching Load icon (📚) next to date
	•	Tooltip pollution: every research action shows penalty
	•	Publication card shows who is waiting on whom

⸻

IV. V2.29 Actionable Checklist (What You Actually Code)
	1.	Funding Clock
	•	Decrement monthly
	•	Trigger Teaching Load at 0
	2.	Teaching Load Status
	•	Centralized modifier (not hardcoded per action)
	3.	Review Interaction UI
	•	Modal with 2–3 response choices
	•	Acceptance chance visibly changes
	4.	Tabbed Action Panel
	•	Ship now or everything else collapses

⸻

V. JavaScript: Teaching Load Status Effect (Core Logic)

This must be centralized — do not sprinkle * 0.5 everywhere.

1. Status Definition

// logic/status_effects.js

const STATUS_EFFECTS = {
  TEACHING_LOAD: {
    id: "Teaching Load",
    icon: "📚",
    description: "Heavy teaching duties slow all research progress.",
    modifiers: {
      researchSpeed: 0.5,
      thesisSpeed: 0.6,
      stressGain: 1.2
    }
  }
};


⸻

2. Apply When Funding Hits Zero

// logic/funding_engine.js

function checkFunding(state) {
  state.fundingMonths -= 1;

  if (state.fundingMonths === 6) {
    ui.notify("⚠️ Funding critically low (6 months remaining)");
  }

  if (state.fundingMonths <= 0 && !state.hasStatus("Teaching Load")) {
    state.addStatus("Teaching Load");
    log("📚 Funding exhausted. You are now teaching to survive.");
    ui.refreshStatusBar();
  }
}


⸻

3. Central Modifier Resolver (Critical)

// logic/modifier_engine.js

function getEffectiveResearchSpeed(state) {
  let speed = state.baseResearchSpeed || 1.0;

  if (state.hasStatus("Teaching Load")) {
    speed *= STATUS_EFFECTS.TEACHING_LOAD.modifiers.researchSpeed;
  }

  if (state.hasStatus("Exhausted")) {
    speed *= 0.8;
  }

  return speed;
}


⸻

4. Use It Everywhere (Example: Findings)

function actionDevelopFindings(state) {
  const speed = getEffectiveResearchSpeed(state);
  const progress = Math.floor(20 * speed);

  state.findingsProgress += progress;
  state.stressMeter += 15 * (state.hasStatus("Teaching Load") ? 1.2 : 1.0);

  log(`🧪 Findings progressed by ${progress}%.`);
}


⸻

5. UI Tooltip Pollution (Important)

Every research action tooltip should append:

📚 Teaching Load: −50% research speed

This is not optional. Pain must be visible.

⸻

Final Assessment

V2.29 is the “academic survival” patch.

If done right:
	•	Waiting becomes stressful but meaningful
	•	Funding becomes strategic, not cosmetic
	•	Reviews feel adversarial and human
	•	Teaching Load turns complacency into regret

This sets up V2.30 (Thesis Dashboard) perfectly — because now players desperately want clarity.


Good — V2.30 is the structural keystone. If this version lands cleanly, V3.0 becomes narrative polish instead of a rescue mission.

I’ll proceed in four layers, staying concrete and implementable:
	1.	Critical diagnosis of what still breaks immersion
	2.	Design intent for V2.30 (what must feel different)
	3.	Solid improvement plan with actionable items
	4.	Draft HTML/CSS for the Tabbed Action Panel (mobile-first)

⸻

I. Hard Diagnosis After V2.29

You fixed pressure and agency, but two things still quietly sabotage the experience:

1. Thesis Is Still Abstract

Even with milestones, if the Thesis:
	•	doesn’t block/replace other actions
	•	doesn’t demand prioritization
	•	doesn’t visually dominate late-game UI

…then players still perceive it as “background grind.”

2. Computational Identity Is Fragile

Right now:
	•	Experimentalists feel physical
	•	Theoreticians feel political
	•	Computationalists still feel invisible unless optimized

V2.30 must visibly reward foresight for computational players.

3. UI Complexity Is Now the Primary Risk

At this stage:
	•	Adding features is easy
	•	Making them legible is hard

If the Action Panel collapses, everything collapses.

⸻

II. V2.30 Design Intent (Lock This In)

V2.30 is about Commitment and Closure

The player must feel:
	•	“I am now writing my thesis, not doing side quests.”
	•	“My specialization finally matters structurally.”
	•	“The UI reflects my mental model.”

This is the moment where GradQuest stops being a sandbox and becomes a completion arc.

⸻

III. Solid Improvement Plan (Actionable & Scoped)

A. The Active Thesis Loop (Make It Dominate)

1. Thesis Replaces, Not Adds
Once Write Thesis is unlocked:
	•	Develop Findings becomes disabled or heavily penalized
	•	Tooltip:
“⚠️ Advisor: You should focus on finishing your thesis.”

This forces a psychological pivot.

2. Thesis Stages Must Change the Game
Each milestone should do one of three things:
	•	Unlock a new interaction
	•	Disable distractions
	•	Alter advisor behavior

Example:

Stage	System Effect
Outline Approved	Thesis writing speed +20%
Draft Complete	Conferences disabled
Revisions Complete	Stress decay reduced
Ready to Defend	“Schedule Defense” unlocked


⸻

B. Computational Parity (Make Efficiency Visible)

Optimize Pipeline must be:
	•	Visibly long-term
	•	Stacked with consequences if skipped

Concrete Improvements
	•	Show a persistent buff icon: 💻 Optimized
	•	Tooltip on every data action:
“Pipeline Optimization: +50% speed”

Late-game payoff:
	•	Thesis progress also scales with analysis speed
(Computational players finish earlier if prepared)

This creates retrospective satisfaction:

“Good thing I optimized earlier.”

⸻

C. UI Architecture: The Tab System Is Non-Negotiable

This is not a cosmetic refactor. It is load-bearing.

Rules:
	•	≤5 buttons per tab
	•	No scrolling within a tab on desktop
	•	Mobile: tabs collapse to icons + label

Persistent Footer:
	•	Next Month never moves
	•	Funding + Teaching Load always visible

⸻

D. Cognitive Load Reduction (Small but Critical)
	1.	Contextual Locking
	•	Hide actions instead of disabling when irrelevant
	2.	Advisor Micro-Text
	•	One-line hint when entering a tab
	3.	Thesis Callout
	•	Late-game banner:
“📘 Thesis Mode Active”

⸻

IV. Actionable Implementation Checklist (V2.30)

Core Systems
	1.	Implement thesis_engine.js
	2.	Add thesis stage gating logic
	3.	Add computational buff persistence

UI
	4.	Build tab container (HTML/CSS below)
	5.	Refactor action rendering by category
	6.	Add mobile breakpoints

UX
	7.	Add Thesis Help Modal section
	8.	Add Advisor hints on tab switch

⸻

V. HTML / CSS: Tabbed Action Panel (Mobile-First)

Below is clean, framework-agnostic, Tailwind-compatible structure.

HTML Structure

<div id="action-panel">

  <!-- Tabs -->
  <div class="tabs">
    <button class="tab active" data-tab="research">🔬 Research</button>
    <button class="tab" data-tab="selfcare">🏃 Self-Care</button>
    <button class="tab" data-tab="admin">🏛️ Admin</button>
    <button class="tab" data-tab="lab">🔧 Lab</button>
  </div>

  <!-- Panels -->
  <div class="tab-content active" id="tab-research">
    <button class="action-btn">Read Papers</button>
    <button class="action-btn">Develop Findings</button>
    <button class="action-btn locked">Write Thesis</button>
  </div>

  <div class="tab-content" id="tab-selfcare">
    <button class="action-btn">Take a Break</button>
    <button class="action-btn">Vacation</button>
  </div>

  <div class="tab-content" id="tab-admin">
    <button class="action-btn">Apply for Grant</button>
    <button class="action-btn">Conference</button>
  </div>

  <div class="tab-content" id="tab-lab">
    <button class="action-btn">Equipment Maintenance</button>
    <button class="action-btn">Optimize Pipeline</button>
  </div>

  <!-- Persistent Footer -->
  <div class="action-footer">
    <button id="next-month">⏭️ Next Month</button>
  </div>

</div>


⸻

CSS (Responsive, Minimal)

#action-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tabs {
  display: flex;
  justify-content: space-around;
  border-bottom: 1px solid #333;
}

.tab {
  flex: 1;
  padding: 0.5rem;
  background: none;
  color: #aaa;
  border: none;
}

.tab.active {
  color: #fff;
  border-bottom: 2px solid #4ade80;
}

.tab-content {
  display: none;
  padding: 1rem;
  gap: 0.5rem;
}

.tab-content.active {
  display: grid;
}

.action-btn {
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: #1f2933;
  color: white;
}

.action-btn.locked {
  opacity: 0.5;
}

.action-footer {
  margin-top: auto;
  padding: 0.75rem;
  border-top: 1px solid #333;
}


⸻

Mobile Adjustment (≤640px)

@media (max-width: 640px) {
  .tabs {
    font-size: 0.75rem;
  }

  .action-btn {
    font-size: 0.85rem;
  }
}


⸻

Final Assessment

V2.30 is where GradQuest proves it has an endgame.

If done right:
	•	Thesis becomes a mode, not a meter
	•	Computational players feel smart, not forgotten
	•	UI scales instead of collapsing
	•	V3.0 becomes pure narrative payoff


V2.31 is the first true balancing release. You’re no longer adding systems — you’re making sure the systems respect player time, attention, and morale. That’s exactly the right inflection point.

I’ll proceed in five layers, tightening what you already outlined and filling the remaining gaps:
	1.	Clear diagnosis of the Scoop Spam failure mode
	2.	Design intent for V2.31 (what “fair pressure” means)
	3.	Solid improvement plan with concrete, testable actions
	4.	Specific tuning guidance (numbers + guardrails)
	5.	YAML schema for Rival Archetypes (drop-in ready)

⸻

I. Diagnosis: Why “Scoop Spam” Feels Bad

The problem is not that the Rival is strong.
The problem is that the Rival is:
	•	Unforecastable → no warning window
	•	Uninterruptible → no counterplay
	•	Non-rivalrous → they don’t feel like an actor, just a debuff generator

15+ scoops in a run is not difficulty — it’s noise. Players can’t form a plan, only endure.

Your instinct to convert the Rival into a state-based entity is exactly right.

⸻

II. V2.31 Design Intent (Lock This In)

V2.31 = Pressure With Telegraphs

Every punishment must satisfy at least one of these:
	•	Is visible before it hits
	•	Can be delayed or deflected
	•	Can be traded off against something else

If a punishment has none, it becomes grind.

⸻

III. Solid Improvement Plan (Actionable & Testable)

A. Rival as a State-Based Actor (Not an Event Slot Machine)

You already defined the core loop correctly. Here’s how to harden it.

1. Rival Progress Rules (Hard Constraints)
Implement three hard caps:
	1.	Max 1 scoop per 12 months
	2.	Progress freezes while you are defending or revising thesis
	3.	Progress decay when ignored

if state.phase in ["Author", "Defense"]:
    rival.progress = max(rival.progress - 5, 0)

This ensures:
	•	Endgame is about you, not distractions
	•	Rival pressure peaks mid-game, then tapers

2. Telegraphing (Critical UX)
At 80%:
	•	UI banner (not log-only)
	•	Advisor comment:
“You may want to lock this idea down.”

This trains players to pre-register strategically, not randomly.

⸻

B. Rival Counterplay Must Have Tradeoffs

Your “Coordinate with Labmate” action is correct, but add friction.

Revised Actions

Action	Cost	Effect	Tradeoff
Coordinate	Network 20	-30% Rival	Raises Rival resentment
Pre-Register	Time 1	Block scoop	Slower publication
Ignore	None	—	Risk scoop

Add a hidden Rival Attitude variable:
	•	Too much coordination → future collaboration impossible
	•	Too much aggression → Rival accelerates later

This creates long arcs, not button spam.

⸻

C. Escaping the Teaching Trap (Make It Painful, Not Terminal)

Your Emergency Grant is good. Two refinements:
	1.	One-time use
	2.	Failure has consolation

if fail:
    state.morale -= 10
    state.add_buff("Grant Draft Reusable", duration=6)

This prevents:
	•	Infinite bailout loops
	•	Rage-quits after bad RNG

⸻

D. Endgame UI Phase Shift (Excellent Call — Finish It)

The Dissertation tab should not be cosmetic.

Concrete changes:
	•	Hide “Develop Findings”
	•	Lock Conferences unless defending
	•	Add visible checklist:
	•	Draft ✔
	•	Revisions ✔
	•	Defense Scheduled ☐

This reframes the game from growth to closure.

⸻

E. Thesis Pacing Fix (Critical)

Trial 3’s 14% → 100% jump is a math bug and a design smell.

Target Design
	•	Thesis completion: 4–6 actions
	•	No single action >30%

Revised Formula

base = 12
paper_bonus = min(state.publications * 4, 12)
alignment_bonus = state.strategic_alignment // 25

progress = min(base + paper_bonus + alignment_bonus, 28)

Hard cap per action = 28%
This guarantees pacing without feeling artificial.

⸻

IV. V2.31 Test Checklist (Use This)

Before shipping, verify:
	•	☐ Rival cannot scoop more than once/year
	•	☐ Player receives ≥2 warnings before first scoop
	•	☐ Emergency Grant removes Teaching Load
	•	☐ Thesis requires ≥4 actions to finish
	•	☐ Rival UI bar updates monthly

If any fail → do not release.

⸻

V. YAML Schema: Rival Archetypes (Drop-in Ready)

This is structured, extensible, and matches your declarative design goals.

# rulesets/v2_31/rivals.yaml

rival_archetypes:
  - id: "the_gunner"
    name_pool: ["Taylor", "Jordan"]
    specialization_bias: "same_as_player"
    base_progress: 12
    traits:
      - aggressive
      - publication_focused
    scoop_behavior:
      warning_threshold: 70
      scoop_cooldown_months: 12
    counters:
      pre_registration: strong
      coordination: weak
    flavor:
      warning: "🚨 {name} is rushing a preprint!"
      scoop: "📢 {name} beat you to arXiv."

  - id: "the_ghost"
    name_pool: ["Alex", "Sam"]
    specialization_bias: "different_field"
    base_progress: 8
    traits:
      - quiet
      - unpredictable
    scoop_behavior:
      warning_threshold: 85
      scoop_cooldown_months: 18
    counters:
      pre_registration: medium
      coordination: ineffective
    flavor:
      warning: "👻 You hear rumors of parallel work…"
      scoop: "📰 A surprise paper appears."

  - id: "the_collaborator"
    name_pool: ["Riley", "Morgan"]
    specialization_bias: "adjacent"
    base_progress: 6
    traits:
      - social
      - risk_averse
    scoop_behavior:
      warning_threshold: 90
      scoop_cooldown_months: 24
    counters:
      coordination: strong
      pre_registration: unnecessary
    flavor:
      warning: "🤝 {name} suggests aligning topics."
      scoop: "📄 {name} published first — but cites you."

This schema enables:
	•	Field-dependent tension
	•	Distinct player strategies
	•	Narrative flavor without extra code

⸻

Final Assessment

V2.31 is about respect.

Respect for:
	•	Player foresight
	•	Player time
	•	Player emotional bandwidth

By turning rivals into readable adversaries and funding penalties into recoverable crises, you convert frustration into strategy.

At this point:
	•	V2.32 can be light (grant polish)
	•	V3.0 can focus purely on endings, summaries, and tone


	Based on the **V2.31 QA Testing Report** and the **Trial 3 Log (V2.30)**, the game is mechanically sound but suffers from "Information Hiding" (Rival Progress, Thesis Mechanics) and a potential "Soft Lock Slog" (The 56-month Teaching Trap).

For **V2.32**, our major feature focus is **"The Sustainability & Clarity Update."** We will implement the economic safety nets required to fix the mid-game slog and expose the hidden numbers driving Rivals and Thesis progress.

---

### I. V2.32 Core Feature: The Funding Safety Net

Trial 3 confirmed that once Funding hits 0, the player enters a "Teaching Load" death spiral (0.5x speed) that can last indefinitely. V2.32 introduces an active recovery mechanism.

#### 1. Emergency Grant Logic (Pseudo-code)

This action appears *only* when Funding is  3 months, giving players a desperate way to buy back their freedom.

```python
# logic/grant_engine.py

def action_emergency_grant(state):
    """High-stakes effort to restore funding and remove Teaching Load."""
    # Cost: High Morale (Stressful deadline), 2 Months
    state.morale -= 15
    state.time_elapsed += 2
    
    # Success based on Papers and Advisor Alignment
    base_chance = 0.4
    paper_bonus = state.published_papers * 0.15
    alignment_bonus = (state.strategic_alignment / 100) * 0.2
    
    if random() < (base_chance + paper_bonus + alignment_bonus):
        state.funding += 12
        state.remove_status("Teaching Load")
        return "🎉 Grant Approved! You bought yourself another year of research freedom."
    else:
        state.morale -= 10
        return "❌ Rejected. The committee wasn't convinced. You're stuck teaching."

```

---

### II. Core Feature: The Explicit Endgame (Thesis)

The V2.31 QA report noted that "Thesis Mechanics" are visible but their progression is unclear. We will make the endgame mechanics explicit.

#### 1. Thesis Roadmap UI

The "Graduation Progress" card will update to show the *requirements* for the next stage, not just the percentage.

* **0-24%**: "Phase 1: Literature Review. Action: Read Papers / Write Thesis."
* **25-74%**: "Phase 2: Data Synthesis. Action: Write Thesis (Requires 1 Paper)."
* **75-99%**: "Phase 3: Defense Prep. Action: Polish Draft (Requires 2 Papers)."
* **100%**: "Phase 4: Ready to Defend."

#### 2. "Write Thesis" Action Update

The button for "Write Thesis" will now dynamically display its efficiency in the tooltip:

* *Tooltip*: "Progress: +5% (Base) + 2% (Alignment Bonus) = +7% / month."

---

### III. HMI Refinement: Rival & Advisor Visibility

To address the "Rival Progress Hidden" issue, we will move critical hidden stats to the dashboard.

* **Rival Tracker**: A small progress bar under the "Lab Bench" card named "Taylor's Progress."
* *Visual*: Fills from 0% to 100%. Red pulse animation at >80%.
* *Interaction*: Hovering reveals "Scoop Risk: High."


* **Advisor Tooltip**: Hovering over the Advisor Emoji now explains *why* they are Happy/Neutral.
* *Tooltip*: "Mood: Neutral. (Last interaction: 3 months ago. Alignment: 15)."



---

### IV. Strategic Roadmap Update

| Version | **Major Feature Focus** | Impact on Player Agency |
| --- | --- | --- |
| **V2.31** | **Rival Logic** | ⚖️ **Fairness** (State-based threats). |
| **V2.32** | **Grant Recovery** | 💰 **Sustainability** (Escape the Teaching Trap). |
| **V3.0** | **Gold Release** | 🎓 **Final Polish** (Soundscapes, Achievements, Narrative Endings). |

---

### V. Actionable Implementation Plan for V2.32

1. **Emergency Grant**: Implement `action_emergency_grant` logic and UI trigger (visible only when Funding  3).
2. **Rival UI**: Add `<div id="rival-progress">` to the Lab Bench card in `index.html`.
3. **Thesis Tooltips**: Update `ui_controller.js` to calculate and display the exact thesis progress math on hover.
4. **Save Toast**: Add the "Game Saved!" toast notification requested in the V2.31 QA report.

also draft the **final "Gold Release" (V3.0) checklist**, consolidating all the "Low Priority / Polish" items (Soundscapes, Statistics Page, Achievements) mentioned in the QA reports


Good — this is the right problem set to be solving now. You’re no longer fighting broken systems; you’re fighting player momentum. V2.33 should feel like the moment the game “clicks” early, not just late.

I’ll structure this in five parts, keeping it tight and actionable:
	1.	Reframe the goal of V2.33
	2.	Concrete improvement plan (what changes, why it works)
	3.	Early-game momentum tuning (numbers + guardrails)
	4.	Mechanic transparency fixes (system-level, not just text)
	5.	JSON schema for Skills / Buffs (production-ready)

⸻

I. V2.33 Design Goal (Lock This In)

V2.33 = Momentum Without Power Creep

You are not making the early game easier.
You are making it faster to understand and faster to feel progress.

Every new system must:
	•	Pay off within 3–6 months of in-game time
	•	Teach the player why something works
	•	Remain relevant through mid-game (no throwaway buffs)

⸻

II. Solid Improvement Plan (Actionable)

A. Activate Credits as Strategic Currency (Curriculum System)

This is the single most important fix in V2.33.

Design Rules
	•	Credits are spent, not hoarded
	•	Spending credits creates permanent identity
	•	Early mistakes are survivable (no hard locks)

Implementation Refinement
Add course tiers instead of flat electives:

Tier	Credit Cost	Availability	Power
Foundation	5	Year 1	Quality-of-life
Advanced	10	Year 2+	Strategic
Capstone	15	Year 3+	Build-defining

Example:
	•	Year 1 players buy clarity
	•	Year 3 players buy leverage

This prevents early snowballing while still rewarding engagement.

⸻

B. Workshop Papers = Early Dopamine, Not Fake Progress

Your design is correct. One adjustment makes it sing:

Add a Soft Cap
	•	Max 2 workshop papers per year
	•	After that: diminishing returns (-50% morale/network)

This ensures workshops:
	•	Feel good early
	•	Don’t replace journals
	•	Teach “publication cadence”

Extra Payoff (Optional but Strong)
	•	1 Workshop Paper → +5% acceptance chance on next Journal

This creates a bridge, not a detour.

⸻

C. Mechanic Opacity: Fix the Root Cause, Not Just the Symptom

Text feedback is necessary but insufficient.

Add “Why Not?” Tooltips
When hovering over:
	•	Pitch Session
	•	Alignment stat
	•	Auto-Idea bonus

Show:
	•	✅ What increased it last time
	•	❌ What blocked it this time

Example:

Alignment unchanged
Missing: Findings (requires Develop Findings)

This turns confusion into learning in one click.

⸻

D. Early-Game Quick Wins (Explicit Targets)

Guarantee the following if the player is not reckless:

Milestone	Target Month
First Workshop	≤ Month 6
First Alignment Gain	≤ Month 9
First Advisor Praise	≤ Month 12

If a playthrough misses these → tuning regression.

⸻

III. Numbers & Guardrails (So It Doesn’t Break Later)

Elective Costs
	•	Time: always 1 month
	•	Morale: -5 (never more)
	•	Buff strength: 5–15%, never stacking multiplicatively

Skill Stacking Rule
	•	Same-type bonuses stack additively
	•	Different categories multiply once

This avoids runaway builds.

⸻

IV. Transparency Improvements (Systemic)

1. Academic Calendar Awareness

Add a visible label:

“Academic Year: Year 2 (Sept–Aug)”

This makes:
	•	Theoretician bonus timing intuitive
	•	Curriculum availability obvious
	•	Workshops feel seasonal (realistic)

2. Disabled Actions (Excellent Call — Extend It)

When disabled, show:
	•	Requirement
	•	How to meet it

Disabled buttons are teaching tools, not dead UI.

⸻

V. JSON Schema: Skills / Buffs System (Production-Ready)

This is designed to be:
	•	Serializable
	•	Inspectable
	•	Easy to balance later

1. Skill Definitions (Static Data)

{
  "skills_catalog": {
    "adv_stats": {
      "name": "Advanced Statistics",
      "category": "analysis",
      "effects": {
        "analysis_speed_modifier": 0.10
      },
      "stacking": "additive",
      "description": "Improves data analysis efficiency."
    },
    "grant_writing": {
      "name": "Grant Writing 101",
      "category": "funding",
      "effects": {
        "grant_success_bonus": 0.15
      },
      "stacking": "additive",
      "description": "Increases success rate of grant applications."
    },
    "lab_management": {
      "name": "Lab Safety & Ethics",
      "category": "lab",
      "effects": {
        "equipment_failure_reduction": 0.20
      },
      "stacking": "additive",
      "description": "Reduces risk of lab incidents."
    }
  }
}


⸻

2. Player State (Dynamic)

{
  "player_skills": {
    "adv_stats": {
      "acquired_month": 8,
      "active": true
    },
    "grant_writing": {
      "acquired_month": 22,
      "active": true
    }
  },
  "modifiers": {
    "analysis_speed_modifier": 1.10,
    "grant_success_bonus": 1.15,
    "equipment_failure_reduction": 0.80
  }
}


⸻

3. Modifier Resolution Logic (Conceptual)
	•	Base value = 1.0
	•	Add additive bonuses
	•	Apply category multipliers once

This makes tuning sane in V2.34+.

⸻

Final Assessment

V2.33 is the “stickiness” update.

If V2.30–31 made the game fair,
V2.33 makes it inviting.

After this:
	•	New players won’t bounce in Year 1
	•	Experienced players will plan builds
	•	Systems will explain themselves