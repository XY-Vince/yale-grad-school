V1.1
1 somehow got into ⚡ Status Effects: Exhaustion
for 9 months and no way to get out of it, tried slacking but it doesn't work
============================================================
  😌 You took some time to relax. (+6 hope)
============================================================
Press Enter to continue...

============================================================
  😫 Your exhaustion is draining your energy... (-5 hope)
============================================================

2. change the name of "hope" to a more general term (probabaly includ)

3. when is qual exam due? the qual exam somehow disappeard and I never took it to pass the 1st year

4. keep getting this after reading papers

============================================================
  😔 You worked hard but didn't make progress this month...
============================================================
Press Enter to continue...

I made major result after 5-6 trials, which is slightly too much

============================================================
  🎉 Success! You've made a Major Result!

5. Unhappyadvisor status effect does not go away

6. Exhaustion status effect does not go away

============================================================
          💔 GAME OVER 💔
============================================================

You've exceeded the time limit...

📊 Final Statistics:
   • Years in program: 9
   • Papers published: 1
   • Final hope: 34%

============================================================

V1.2
1. this is obviosuly a bug
============================================================
------------------------------------------------------------
  📅 Year 1, November
  💪 Morale: [███████░░░░░░░░░░░░░] 38% 😰 Low
  📰 Papers: 0/3 required
------------------------------------------------------------

📋 Actions:
  [1] 📚 Read Papers
  [2] 😴 Slack Off
  [3] 📖 Prepare for Quals
  [4] ⏩ Advance to Next Month
  [5] 🚪 Quit Game

Choose action: 3

============================================================
  📖 You studied for the qualifying exam. (Preparation:
  1/3)
============================================================
Press Enter to continue...

============================================================
  🎉 Congratulations! You passed your qualifying exam!
============================================================

2. this one here still says "hope" when it should say "morale"
============================================================
  😠 Your advisor's disappointment weighs on you... (-5
  hope)
============================================================


3. I got 3 papers but I chose to stay for another year, then the thesis option did not come back

4.============================================================
          💔 GAME OVER 💔
============================================================

You've exceeded the time limit...

📊 Final Statistics:
   • Years in program: 9
   • Papers published: 4
   • Final hope: 62%

============================================================

5. qual exam took place in the 3rd month, and I only prepared for it once and passed

6. in the next run, I completed thesis but nothing happened

V1.4
1. latest event should be much more visible
2. need a clear event of qual exam pass/fail
3. prep for qual should be a slightly random process, requires 1-4 months (mean=3)
4. waited 8 years for the broken equipment, should be more proactive (or it just go away after a while)
also the Brokenequipment status is highly visible, but its mechanical impact (blocking figure production maybe) is not explained

Layout Suggestions for Improvement
1. Core State & Navigation
Opportunity Cost Display: Following the revision plan's goal of "realistically frustrating" gameplay, add a small counter next to "Papers Published" showing "Industry Wealth Lost" to emphasize the opportunity cost of academia. (maybe not the best idea, wait for the next version)

Time Tracking: Add the "Total Months Elapsed" alongside the date, as many YAML event triggers rely on absolute month counts rather than just the year.

2. Enhancing the "Actions" Panel
Contextual Buttons: Actions should be dynamic. For example, if the player has a Major Result but no figures, a "Work on Figures" button should appear (and be greyed out if Brokenequipment is active).

Action Cost/Probability: Hovering over "Read Papers" or "Prepare for Quals" should ideally show the "Exhaustion" cost or the success probability, mirroring the internal engine's logic. (maybe not the best idea, wait for the next version)

3. Data-Driven Sidebar
Relationship Status: The current layout misses the Advisor Relationship metric, which is a key variable in the original's success/failure logic. A "Relationship Bar" (e.g., Advisor Happiness) should be added to the sidebar.

Financial Extension (Phase 3): If the "North American" ruleset is active, the sidebar will need a dedicated "Funding/Debt" section to track the starvation mechanics mentioned in the revision plan. (maybe not the best idea, wait for the next version)

III. Aesthetic & UX Tweaks
Font Consistency: While the modern look is sleek, the "PressStart2P" pixel font mentioned in the project overview would provide a stronger "retro-sim" feel that matches the original project's vibe.

Event Log History: The "Latest Event" box is useful, but a scrollable log or a "Show History" button would help players track how they lost morale or where their items went.

V1.5
1. Advisor relationship should be affected by reasonable current progress (relative to stage)
2. September, Year 1 should be fit in the same line, maybe shrink the font a bit
3. Clear visual pass/fail should be displayed in latest event
4. Currently there's only one way to generate an idea,
5. Locked by "Broken Equipment" again! twice! pls check really closely

V1.6

General Recommendations
Priority,Suggestion,Rationale/Benefits
High,"Fully port original YAMLs verbatim as data/rulesets/original/; add toggle (--ruleset original) for purists. Then layer ""north_american.yaml"" with plan's features (e.g., stipend events, medical bills).",Ensures fidelity; allows A/B testing. Use plan's GameEvent schema for new YAMLs.
High,"Add automated tests: Unit (expression parser, variable clamping) + integration (sim 100 runs, check avg grad time ~5yrs, win rate 20-30%). Use pytest.","Catches regressions like equipment bug; quantifies balance (e.g., morale decay)."
Medium,"Expand README: Add mechanics section (pipeline flowchart like original), YAML mod guide, LLM concrete example (e.g., generate random messages via OpenAI). Include screenshots of CLI/Web UI.",Improves accessibility; attracts contributors for extensions.
Medium,"Optimize Web UI: Use WebSockets (e.g., Flask-SocketIO) for real-time ticks instead of polling. Add save/load (JSON via localStorage/cookies).",Enhances interactivity; mirrors original's smooth browser tick (50ms).
Low,"Analytics Module: Implement plan's pandas logging (e.g., CSV of runs: months, morale, papers). Expose via --log flag.","For balancing; ties into AI (e.g., LLM analyze failure patterns)."
Low,Accessibility: Add color-blind modes for bars (patterns over colors); keyboard nav for web.,"Broadens audience; original had simple text, but UI adds visuals."


Implementation Scoring System for Events Affecting Advisor Happiness:

Core Mechanic: Add advisor.score variable (0-100, start 50) to VariableStore. Events/actions modify it (e.g., paper publish: +15; slack: -5; conference success: +10).
Threshold Effects: Use expressions in YAML conditions (e.g., if advisor.score <40, trigger "unhappyAdvisor" status; >80: "mentorBoost" +idea chance).
YAML Integration: Extend GameEvent schema:YAML- id: publish_paper
  actions:
    - id: UpdateVariable
      variable: advisor.score
      value: advisor.score + 15  # Or expression: min(100, advisor.score + 15)
Random/Choice Variety: For events like conferences, score delta could RNG (e.g., +5-15) or choice-based (e.g., "Network with advisor's peers: +10 score but -morale").
Testing: Sim runs to ensure average score ~60-70 for balanced play; low score increases dropout risk (e.g., via hope decay).

V1.7
1. HTML deployment 
2. change"You are now Dr. You!" to the original version
3. change "Years in program" to "months elapsed"
4. any successful events should boost morale
5. add:Seed The seed for the current timeline is XXX. Shareable link:
6. add:Help button, click to show the game's help

General Recommendations
Priority,Suggestion,Rationale/Details
High,Polish Docs Site,"Build on new index.html: Add sections from README (e.g., mechanics flowchart, YAML mod guide). Embed web UI as playable demo (iframe run_web.py output). Use MkDocs for auto-gen from MD files—quick, keeps it lightweight."
High,Release V1.7 Properly,"Cut a GitHub Release with binaries (e.g., zipped CLI/web), changelog from IMPLEMENTATION_PLAN.md. Add badges (e.g., pytest passing) to README."
Medium,Light Testing Expansion,"Add pytest for sim runs (e.g., 100 games: check avg years ~5-6, win rate 20-30%). Log to CSV (pandas optional) for balance insights."
Medium,Advisor Scoring as Minimal Add,"Per prior: Add subtle score var (0-100) in YAML (e.g., +15 paper, -5 slack) with thresholds (e.g., <50: -morale/month). Test in V1.7 as optional ruleset."
Low,Outreach Tweaks,"Post to Reddit (r/gamedev, r/academia) or itch.io for feedback. Add CONTRIBUTING.md for mods (e.g., ""Submit YAML rulesets!"")."
Low,LLM First Steps,"Demo in README: Env var setup for simple AI (e.g., GPT-4 generates random event messages). Gate as experimental."

v1.8
1. change "slack off" to "take a break" or whatever feels appropriate
2. add more feedback and interaction with advisor
a. feedback on ideas (good to go/not good enough)
b. too tired to do anything, need to take a break
c. other interactions (e.g.,paperrejection, advisor's mood, advisor's availability) that has little actual impact on the game
3. add more events （UNIVERSITY NEWS/General Events）
4. conference: no more than 3 per year
5. the responses to actions (e.g., read papers, developing an idea, prepare for qual, etc.) should be more diverse
6. completely change the wording of "preliminary results" and "major results"
7. set a delay of 2-5 months (mean 3 months) between submitting an paper and getting results (rejects come in 1-2 months)

V1.9
in general: make things slightly harder
don't be too specific on the time durations, are they are always implicit
remove the " (2-5 months)" " (1-3 months)"
rephrase "35% idea"
remove the "/3" in papers, just keep the count
there's only "save" but no "load"
repharase "work on figures" as it's kinda narrow
"Latest Event" updates too fast, change to typing style


V2.0
To transition GradQuest from a functional prototype into a credible software artifact, we must bridge the gap between your modular Python backend and the user-facing experience. The "hard truth" is that while the engine is capable, the lack of transparency in the Research Pipeline and the absence of professional repository standards (documentation, CI/CD, community guides) limit its impact.
I. Consolidated Critical Observations
Based on the project's current state on GitHub and the underlying logic of the PhD Simulator:
The "Invisible" Engine: The UI obscures the complex state machine (Paper Pipeline, Advisor Happiness, and absolute month counts) required to win.
Documentation Void: The lack of a comprehensive README, CONTRIBUTING.md, and Roadmap makes the project appear "unmaintained" to outsiders.
Mechanical Mismatch: There is a disconnect between UI terminology (e.g., "Morale") and the original engine's variables (e.g., player.hope), which can break event triggers.
Quality Assurance: The project lacks visible test coverage and automated CI (GitHub Actions), which is essential for a modular Python project.
II. Ranked Action Plan for Revision
🔥 Phase 1: Professionalization & Visibility (Immediate)
Goal: Treat the project like a "software artifact" rather than a hobby script.
README Overhaul: Include a clear value proposition, architectural diagram (Core Engine vs. GUI), and high-quality screenshots or GIFs of the gameplay.
Repository Standards: Add CONTRIBUTING.md, issue templates, and CHANGELOG.md. Use Conventional Commits (e.g., feat:, fix:) for all future updates.
CI/CD Integration: Set up GitHub Actions to run Python tests on every push. Add status badges to the README to signal build health.
Tagging: Create a formal semantic version release (e.g., v0.1.0-alpha).
⚙️ Phase 2: Mechanical Fidelity & UI Transparency (1–2 Weeks)
Goal: Align the web UI with the "Research Pipeline" and "Advisor" logic from the source.
Pipeline Visualizer: Replace the generic inventory list with a linear stepper: Idea $\rightarrow$ Preliminary $\rightarrow$ Major Result $\rightarrow$ Figures (0/3) $\rightarrow$ Submit.
Status Mapping: Ensure UI "Morale" maps exactly to player.hope in the VariableStore.
The "Advisor" Bar: Add a dedicated Advisor Happiness meter. Low satisfaction should visually trigger the unhappyAdvisor status penalty.
Contextual Actions: Greyscale or disable buttons based on status (e.g., Disable "Generate Figures" if Brokenequipment is active).
🚀 Phase 3: North American Extensions (Long-term)
Goal: Implement your modular vision for MS/PhD transitions and financial survival.
Financial Ruleset: Load an optional north_america.yaml that introduces player.money and player.debt variables.
The MS Pivot: Create a starting state where the player must earn 30 credits (Stage 1) before triggering the "PhD Application" event (Stage 2).
Opportunity Cost Display: Add a UI element showing "Projected Industry Wealth Lost" to emphasize the "frustrating realism" of the simulation.
III. Proposed Revised Roadmap (ROADMAP.md)
Milestone
Deliverables
Target
v0.2.0 (The Faithful Port)
Full Research Pipeline UI; Advisor Relationship meter; Logic-mapped Morale.
Next Week
v0.3.0 (The Robust Engine)
Safe Expression Parser (AST); GitHub Actions CI; 80% test coverage.
2 Weeks
v0.4.0 (US Grad Life)
Finance Module; MS track; Opportunity Cost tracker.
1 Month
v1.0.0 (The AI Integration)
LLM-generated event descriptions based on player state.
TBD

V2.11
This integrated action plan synthesizes the best ideas into a **Modular Realism Expansion**. The goal is to evolve **GradQuest** from an RNG-heavy parody into a "Resilience Simulator" where player agency balances out academic chaos.

---

### Phase 1: The Core Logic & Variable Update

Before adding events, we must expand the `VariableStore` to support these new systems without bloating the UI.

* **Advisor Profiling**: Introduce three hidden/semi-visible traits: `RiskTolerance`, `AttentionSpan`, and `Strictness`. These act as multipliers for all feedback and submission outcomes.
* **The "Peer Network" Variable**: A `peer.network` stat (0-100) that unlocks better "Internal Review" outcomes and collaboration events.
* **Sub-Status Items**: Add `Polished` (from advisor review) and `Revising` (active journal state) to items to track paper quality.

---

### Phase 2: Advisor Interaction (The Stochastic Gatekeeper)

Instead of a simple "Happiness" bar, the advisor becomes a source of **Signal vs. Noise**.

* **The "Pitch Session" Action**: Costs 1 turn.
* **Outcome**: Returns a signal: "Promising but premature" or "Too incremental".
* **Mechanical Impact**: A "Good Pitch" adds a hidden +15% success multiplier to the `Preliminary Result` stage of that specific project.


* **Revision Cycles**: When submitting to a Journal, the outcome isn't binary.
* **Major Revision (Reviewer #2)**: -15 Morale, +3 months delay, but +25% final acceptance chance if you "Resubmit".


* **The "Pester" Trade-off**: You can "Ask for Update" if the advisor sits on a draft.
* **Low Attention Advisor**: 50% chance they finish review, 50% chance `Advisor Mood: Irritated`.



---

### Phase 3: The Dual Publication Track

Differentiating these tracks forces players to choose between **Survival (Conferences)** and **Graduation (Journals)**.

| Track | Timing | Success Rate | Primary Reward |
| --- | --- | --- | --- |
| **Conference** | 4 Months | 60% | `peer.network` + `Hope` boost. |
| **Journal** | 12+ Months | 30% | `Graduation Credit` + `Prestige`. |

* **The "Conference-to-Journal" Pipeline**: A rejected Conference paper can be resubmitted as a Journal paper with a `Polished` buff, simulating the real-world expansion of conference proceedings.

---

### Phase 4: Social Dynamics (Lab Archetypes)

Avoid simulating individual NPCs. Use **Archetypes** to create a "Lab Atmosphere".

* **Lab Archetype Events**: Every year, your lab "rolls" for 2 archetypes:
* **The Overachiever**: +5% research speed for everyone, but -1 morale/month due to comparison.
* **The Burnout**: Chance to trigger "Commiseration" events (Hope boost, but research penalty).


* **Collaborative Credit**: High `peer.network` triggers a "Co-author Offer." You get 0.5 Graduation Credits for half the work time.

---

### Phase 5: The "MS Out" Strategic Exit

This is no longer a "Game Over," but a **Branching Ending**.

* **The Prompt**: Triggered if `Hope < 20` and `Year >= 2`.
* **Exit Profiles**: Your ending text depends on what you've done:
* **High Network + MS**: "Industry R&D Lead".
* **High Papers + MS**: "Data Scientist/Consultant".
* **Low Everything + MS**: "The Great Escape" (High Morale recovery, low wealth).


* **Opportunity Cost**: The UI displays the "Industry Salary" you are currently earning in the MS ending, contrasting it with your current PhD stipend.

---

### Phase 6: Flavored RNG & Seasons

Small, non-cumbersome events to keep the "academic vibe" alive.

* **Imposter Syndrome**: Random monthly chance to lose 8% Morale with "flavored messages" (e.g., "Everyone else seems to know what they're doing").
* **The "Scoop"**: 3% annual chance a `Major Result` is invalidated by another lab's publication. Devastating but realistic.
* **Teaching Duty (TA)**: Recurring status in Fall/Spring that consumes 10% of your research time.

---

### Implementation Priority (The 80/20 Rule)

1. **High Impact/Low Effort**: MS Out branch + Advisor signal feedback.
2. **Medium Impact**: Dual Conference/Journal tracks + Revision cycles.
3. **Flavor/Refinement**: Lab archetypes + Imposter Syndrome.


**V2.2 Strategic Revision Plan** 
reflects a shift from a "burnout simulator" to an **adaptive resilience engine**. Based on the latest critiques, we are moving away from punitive, opaque mechanics toward a system where every challenge unlocks a new form of agency.

---

### I. Updated Strategic Revision Plan

#### 1. Adaptive Competence & Meta-Skills

To ensure resilience is "earned," we introduce a hidden **Strategic Alignment** meta-skill.

* **Mechanic**: Consistently choosing actions that align with the Advisor’s profile (e.g., pitching exploratory ideas to a High-Risk advisor) increases this skill.
* **Benefit**: Higher alignment acts as a "buffering" stat, reducing morale loss from future rejections and narrowing RNG variance in the research pipeline.

#### 2. Advisor Profiling: From Opacity to Inference

Advisor traits (Risk Tolerance, Attention Span, Strictness) are no longer purely hidden.

* **Weak Signals**: Players receive behavioral cues:
* **Attention Span**: Reflected in "Response Delay" (High = instant feedback; Low = 1–2 month wait).
* **Strictness**: Reflected in "Feedback Tone" (High = blunt/critical; Low = encouraging).


* **Soft Reveal**: After three meetings, the UI displays a narrative summary: *"Your advisor seems impatient with exploratory ideas"*.

#### 3. Threshold-Gated Social Dynamics

To prevent `peer.network` from becoming a "god stat," its effects are now gated by specific thresholds.

* **Level 60**: Unlocks "Collaboration" actions.
* **Level 80**: Provides "Scoop Protection" (lab-mates alert you to competitors).
* **Functionality Split**: Interaction with peers now specifically influences **Access** (tools, data) while reputation with the advisor influences **Credibility** (funding, defense).

#### 4. The Non-Linear Pipeline & Revision Loops

The Research Pipeline UI now accounts for academic regression.

* **Backward Transitions**: A "Major Result" can regress to "Preliminary" if a fatal flaw is found during the "Polish" phase.
* **Variance-Based Polishing**: The "Polish" action no longer provides a flat success boost. Instead, it **reduces the RNG spread**, ensuring that a high-quality paper is less likely to receive a "Desk Reject" even if it isn't "Accepted" immediately.

#### 5. Strategic Exit (MS-Out) as Optimization

MS-out is reframed as **Conditional Optimization**.

* **Stay Option**: Players with low morale can choose to "Stay Despite Low Morale," which grants a temporary "Grit" buff but increases the rate of health/morale decay in later years.
* **Reapply Buff**: The +20% reapplication boost is replaced with **Path-Dependent Buffs**. A player only gets a boost if they have "Industry Experience" or "Gap-Year Publications".

#### 6. Contextualized Opportunity Cost

The Opportunity Cost tracker is now **toggleable** and **field-specific**.

* **Asymptotic Drain**: Morale drain from lost salary is no longer linear; it levels off over time as the player "accepts" their academic path.
* **Field Presets**: The benchmark industry salary is determined by the field selected at the start (e.g., CS vs. Humanities).

---

### II. YAML Template: Advisor Profile Randomization

This template defines the logic for generating the advisor's hidden traits and their associated "Weak Signals."

```yaml
# rulesets/default/advisor_profiles.yaml

advisor_generator:
  traits:
    - id: risk_tolerance
      range: [0, 100]
      description: "Affects acceptance of exploratory/high-risk ideas."
      impact:
        high: "Increases success of 'Moonshot Pitch'; decreases success of 'Safe Method'."
        low: "Hard-blocks 'Radical Idea' items; favors 'Incremental Progress'."

    - id: attention_span
      range: [0, 100]
      description: "Determines response delay and feedback depth."
      signals:
        high: { delay: 0, tone: "detailed" }
        low: { delay: 2, tone: "terse" }

    - id: strictness
      range: [0, 100]
      description: "Influences the probability of 'Major Revision' vs 'Accept'."
      impact:
        multiplier: "strictness * 0.01" # Applied to Revision RNG

# Pre-set Field Archetypes
field_presets:
  - id: computer_science
    bias:
      risk_tolerance: [50, 90]   # CS favors rapid, innovative shifts
      strictness: [30, 60]       # Focus on conference speed
  - id: biomedical_science
    bias:
      risk_tolerance: [10, 40]   # High cost of failure; cautious
      strictness: [70, 95]       # High barrier for journal publication

# Narrative Signal Engine
signals:
  - condition: "advisor.attention_span < 30"
    message: "Your email has been unread for two weeks. Your advisor seems absent."
  - condition: "advisor.strictness > 80"
    message: "Your advisor's feedback is covered in red ink. Every comma is scrutinized."
  - condition: "advisor.risk_tolerance > 70"
    message: "Your advisor gets excited by 'disruptive' terminology in your pitch."

# Inference Logic (Soft Reveal)
inference_triggers:
  - count: 3
    event: "soft_reveal_traits"
    actions:
      - id: DisplayMessage
        text: "Based on your meetings, you suspect your advisor favors {{ 'safe results' if advisor.risk_tolerance < 40 else 'bold ideas' }}."

```

---

### III. Next Steps

Based on this plan, please:

1. **Draft the "Strategic Alignment" Logic**: Define exactly how matching an advisor's trait with an action type (e.g., Pitching a High-Risk Idea) contributes to the meta-skill.
2. **Design the "Path-Dependent" Endings**: Map specific MS-out outcomes to the "Industry Experience" and "Network" variables for the reapplication epilogue.



Actionable Plan for V2.4


 (The "Resilience & Refinement" Update)1. Adaptive Consequences (The "Cramming Hangover")The Issue: Currently, "Cramming" allows a player to pass Quals and move on immediately.The Fix: Add a delayed penalty to the Last-Minute Cram.Mechanic: Cramming now triggers a "Burnout Risk" status or a permanent -2 reduction in max Morale for the remainder of Year 2.Action: Update the cram logic in index.html to include a flavored warning: "You passed, but the toll on your mind is permanent".2. Narrative Honesty (Early MS-Out)The Issue: MS-out is currently locked until Year 2.The Fix: Allow rare, early MS-out triggers under severe conditions.Mechanic: If Morale < 15 in Year 1, trigger a "Heart-to-Heart" event with the Advisor.Outcome: The player can exit early as "The Great Escape" profile.3. Morale Dampening (Strategic Alignment Utility)The Issue: Late-game morale decay can feel overwhelming regardless of player skill.The Fix: Use Strategic Alignment as a "shield".Mechanic: High Strategic Alignment (learned via Pitch Sessions) now reduces base monthly Morale decay by 1–2 points.UI Signaling: Add a small note in the "Help" or "Advisor Status" hover: "Alignment with advisor reduces monthly stress".4. Enhancing Reviewer #2 & Advisor FlavorThe Issue: Feedback is becoming mechanical; it needs more personality.The Fix: Expand the "Snark" library.Reviewer #2: Add 5–10 new snarky comments to the rejected_paper logic (e.g., "The author's grasp of basic statistics is... novel").Advisor Signals: Link Pitch Session messages more tightly to hidden traits. A "Strict" advisor should give specific critiques on the "Figures" count.5. Figure Pipeline TransparencyThe Issue: Players are frustrated when figures reset upon submission.The Fix: UI Explanation.Visual: Update the pipelineEl to include a sub-caption: "Figures are integrated into the final manuscript upon submission".III. Summary of V2.4 Target MetricsFeatureProposed ChangeTarget ImpactCrammingAdd "Burnout" status penalty.Prevents dominant strategy abuse.MS-OutUnlock in Year 1 if Morale is critical.Improves narrative honesty.MoraleStrategic Alignment dampens decay.Rewards high-skill play and "alignment".RNGCaps on "Scooped" events; more snark for Reviewer #2.Keeps "Fair RNG" while adding personality.

 in the end, pls fix the "latest events" display, it is not working properly
in the following case, only month 3 activity is shown, month 2 was never shown in latest events, they should be appearing simultaneously
"Month 3: 💡 A sudden flash of inspiration strikes! (+15 morale, +1 idea)
Month 2: 📖 Decent study session!"


V2.8

### Critical Observations on previous V2.7 Stress Test Run

#### **Key Strengths (Stable & Thematic)**
- **Engine Robustness**: Handles 365+ events, 255 turns without overflow/soft-locks. Graduation triggers correctly despite extremes.
- **Cathartic Realism**: Advisor "week off" insists (x30+), imposter/labmate hits, scoops (x3), equipment cycles, frequent confs (x50+) capture PhD chaos—morale volatility feels authentic (dips to low, recovers via breaks).
- **Network Payoff**: Max 100 via confs enables late accepts—strategic, not useless (contra Expert #1 partial critique).
- **Flavor Depth**: Diverse events (holidays/TA/inspirations) prevent total monotony; MS out suggested early (Month 7).

#### **Critical Issues (Unbounded Loops & Fiction Cracks)**
| Issue | Observation from Log | Expert Alignment | Impact |
|-------|----------------------|------------------|--------|
| **Advisor Intervention Dominance** | "Week off" insists x40+, clearing exhaustion +15-25 morale routinely (e.g., Months 11-199 cycles). Benevolent regulator, not constraint. | Both experts: Stall loop (Expert #1); overpowered sustain (Expert #2). | Trivializes burnout; stabilizes morale too well (35% end after 21yrs). |
| **Time Off Overpowered** | No cooldown/diminishing; erases exhaustion freely. | Expert #2 dominant. | Infinite equilibrium—prevents Game Over but stalls progress. |
| **Conference Spam** | x50+ attends (multiple/year); max network early, idea/morale farm. | Expert #2 farming. | Events lose meaning; inflation vs real limits (1-3/yr typical). |
| **Numerical Leakage** | Figures "4/3 needed" (Month 189); no hard caps. | Expert #2 leakage. | Harmless short-term but signals unbounded vars in extremes. |
| **Advisor No Memory/Trajectory** | Feedback oscillates endlessly (harsh → praise → harsh); no aging/impatience. | Expert #2 memory lack; Expert #1 routing need. | Flattens narrative—21yr advisor unchanged. |
| **Emotional Repetition** | Imposter/labmate x20+; flat deltas, blur over time. | Expert #2 lose impact. | Mechanical, not psychological depth. |
| **No Institutional Pressure** | Infinite duration tolerated; no funding cliffs/reviews. | Expert #2 infinite institution. | Fictionally absurd (real caps 7-10yrs). |
| **Late-Game Friction Mismatch** | 4th paper struggles like 1st (Reviewer #2 streaks, redos). | Expert #1 #2 dominance/no experience buff. | Undermines progression sense. |

### Solid Action Plan for V2.8+ "Adaptive Resilience"

Incorporate experts holistically: Expert #1's narrative agency (Field Authority, Peer Pre-print, Financial Pivot, Sunken Cost); Expert #2's systems rigor (fatigue/cooldowns/caps/memory/pressure). Phased, YAML-modular (new `rulesets/adaptive.yaml`). Prioritize high-impact/low-effort; test via 100 sims (target: avg 72-96mo, 30-40% PhD win, 40% MS out, end-morale 50%+).

#### **Phase 1: Break Dominant Loops (Immediate, 1-2 Weeks)**
Goal: Prevent infinite sustain; add friction memory.
1. **Advisor Fatigue/Desensitization** (Expert #2 A + Expert #1 routing):
   - New var: `advisor.interventions` (count).
   - After 10+: Reduced morale gain (50%), or "Stops noticing" (no more insists).
   - YAML: Counter + conditional actions.
2. **Time Off Diminishing Returns/Cooldown** (Expert #2 B):
   - Rolling 12mo: Each subsequent -5 morale gain; or "Advisor disapproves repeated breaks" (-advisor score).
   - No cooldown exploit—real advisors burnout too.
3. **Conference Caps** (Expert #2 C):
   - Hard: Max 2/year (RNG 1-3 early, taper late).
   - Diminishing: >Network 80: +morale halved.
   - Keeps events special.

#### **Phase 2: Add Progression & Agency (2-4 Weeks)**
Goal: Experience buffs; bypass options.
1. **Field Authority Buff** (Expert #1 1):
   - New var: `field_authority` (+10/paper published).
   - Reduces harsh feedback % (e.g., -20% "tear apart" per 20 authority); +submit success.
   - Late papers easier—real expertise growth.
2. **Peer Pre-print Bypass** (Expert #1 3):
   - Unlock Network ≥80: Action "Peer Feedback" (skips 1 advisor review month, +idea chance, risk irritation -10 score).
   - Breaks stalls; agency vs toxic advisor.
3. **Hard Var Bounds** (Expert #2 D):
   - Clamp figures/ideas (max 3/required); no overshoot.
   - Prevent leakage in extremes.

#### **Phase 3: Narrative Depth & Pressure (4-6 Weeks)**
Goal: Evolving humans/institution; scaled emotion.
1. **Advisor Memory/Trajectory** (Expert #2 E):
   - Patience var: Decreases yearly (>Year 10: +harsh %, "Impatient" events).
   - Feedback evolves: Early technical → late political/funding.
2. **Scaled Emotional Events** (Expert #2 F):
   - Imposter/labmate: Early hard hits (-8); late milder/cynical ("Disengaged" -research speed).
   - Transform over time.
3. **Institutional Pressure** (Expert #2 G):
   - >Year 8: Funding questions (-morale); Year 12+: Department review (forced milestones or MS nudge).
   - Ends infinite runs realistically.
4. **Sunken Cost & MS Refinement** (Expert #1 4):
   - >Year 10: MS out → "Academic Martyrdom" (slow morale decay, but +health risks or cynicism).
   - Early triggers stronger; profiles richer (e.g., high authority → "Professor Path" hint).

#### **Phase 4: Polish & Extensions (Ongoing)**
1. **Financial Pivot/Opportunity Cost** (future update):
   - Threshold ($500k lost): "Industry Gig" choice (+money/morale, -advisor irritation).
   - Ties macro interest.
2. **Ivy Overlay** (future update):
   - Optional ruleset: Higher quals, salary benchmark, field-specific (e.g., comp bio events).
3. **Testing/Validation**:
   - Pytest: 100 sims pre/post changes (track avg months, morale curves, loop escapes).
   - Stress: Force 200+mo seeds—verify no infinite equilibrium.

V2.8
### Critical Observations on V2.7 Test Run

This V2.7 run (73 months ≈ 6 years) is a breakthrough—feels like a "strong but realistic" PhD: Efficient progress (quals Month 13, papers steady, defense Year 7), visible friction (scoops x2, revisions, equipment, Reviewer #2), buffered by strategy (confs for network/morale/ideas). 104 events balanced: Positives (inspirations, accepts, holidays/TA) offset negatives without dominance. MS out late (Month 66) adds tension. Incorporating both experts: Comment #1 praises pacing/human advisor but flags conf spam/inspiration power; Comment #2 highlights efficiency but notes late MS-out oddity/scoop brutality.

#### **Strengths (Major Wins Over Prior)**
| Aspect | Observation | Expert Alignment |
|--------|-------------|------------------|
| **Realistic Timeline** | 73mo spot-on (real avg 6-7yrs); quals early, first paper ~Month 34, final sprint Years 5-6. | Comment #1 "believable strong trajectory"; Comment #2 "perfect North American timeline." |
| **Advisor Cadence** | Mixed signals ("Promising" praise, "tear apart" friction); intervention Month 65 saves final push. | Comment #1 "human iteration"; Comment #2 proactive but not overpowered. |
| **Friction Loops** | Scoops/Reviewer #2/equipment add pain without stalling; revisions turnaround realistic (5mo). | Comment #1 "most realistic loop"; no infinite sustains. |
| **Conf Utility** | ~12 attends build network/ideas/heard good—strategic buffer vs scoops. | Comment #2 morale buffer; not yet farmed. |
| **MS Out Placement** | Month 66 (near end, low morale)—emotional, ignorable. | Comment #1 "well-placed"; adds choice weight. |

#### **Remaining Issues (Tuning Needed)**
| Issue | Observation from Log | Expert Alignment | Impact |
|-------|----------------------|------------------|--------|
| **Conference Frequency** | ~12 in 73mo (2-3 some years); early ramp network fast. | Comment #1 main issue (too many, stop special). | Morale/idea inflation; less eventful. |
| **Inspiration Overpowered** | x4 flashes (+15 morale +idea); easy escape. | Comment #1 overpowered jackpot. | Trivializes lows; rare in reality. |
| **Advisor Rescue Generous** | Month 65 insist clears exhaustion—no cost/patience loss. | Comment #1 still generous; Comment #2 prevents Over but subtle. | Safety valve too strong. |
| **Scoop Clustering** | Back-to-back Months 56/60 (-idea/morale mid-pipeline). | Comment #2 brutal back-to-back. | Punitive paralysis feel. |
| **TA Under-Integrated** | Appears/completes Month 52 (+morale/network)—no research stall. | Comment #2 under-integrated; Comment #1 clean. | Missed tradeoff realism. |
| **Late MS Out Oddity** | Month 66 (near defense, 2+ papers)—advisor suggests quit. | Comment #2 unintelligent late. | Undermines tension. |
| **Abrupt Graduation** | Sudden Month 73—no prep/tension. | Comment #1 emotionally abrupt. | Win lacks catharsis. |

### Solid Action Plan for V2.8 "Adaptive Resilience" (Incorporating Experts)

Phased, YAML-modular (`rulesets/adaptive_v32.yaml`). Prioritize high-impact/low-effort; integrate Expert #1 (caps/diminishing, patience, defense prep) + Expert #2 (MS bypass, scoop cooldown, conf alignment, TA visual). Test: 100 sims (avg 60-90mo, 35% PhD, varied morale).

#### **Phase 1: Tune Dominance & Friction (Immediate, 1 Week)**
Goal: Reduce escapes/jackpots; add cooldowns.
1. **Conference Soft Caps/Diminishing** (Expert #1 main):
   - Pre-Year 3: Max 1/yr; rolling 12mo: >2 halved morale/network.
   - Early confs: 20% "Alienating" (-morale, no gain).
   - Bonus: "Heard good" → +Strategic Alignment (next pitch success).
2. **Inspiration Tuning** (Expert #1):
   - Cap 2/yr; post-first: +10 morale (diminishing); 20% "Dead end" follow-up (-idea).
   - Gate: Higher prob low morale/exhaustion.
3. **Scoop Cooldown** (Expert #2):
   - Post-scoop: 6mo immunity; or "Pivot salvage" (+figures speed).
4. **Advisor Patience Counter** (Expert #1 generous + Expert #2):
   - Hidden: Interventions >5: Reduced gain; or "Stops noticing."

#### **Phase 2: Enhance Agency & Progression (1-2 Weeks)**
Goal: Late-game intelligence; tradeoffs.
1. **Late MS Out Bypass** (Expert #2 unintelligent):
   - ≥2 papers: Disable/swap "Pep Talk" (+15-20 morale).
   - Keep early triggers; add "Sunken Cost" >Year 8 (slow decay, cynicism flavor).
2. **TA Integration** (Expert #2 + Comment #1):
   - Active: -20% research speed (figures slower); +morale volatility.
   - UI: Pipeline "Stalled" visual during duty.
3. **Field Authority Memory** (Implicit from experts' progression):
   - +per paper; reduces late harsh %/scoop risk.

#### **Phase 3: Narrative Polish & Depth (2-4 Weeks)**
Goal: Emotional arc; catharsis.
1. **Defense Prep Phase** (Expert #1 abrupt):
   - Pre-defense (2-3 papers): "Prep Thesis" actions (small rev risk, morale spike on success).
   - Post: Minor revision chance; advisor ambiguity.
2. **Phrase Variety** (Expert #1 subtle):
   - 3-4 variants "Reviewer hate"/"Not strong" for repetition relief.
3. **Network Plateau** (Expert #1 linear):
   - >80: Gains halved; focus journals/conf quality.

#### **Testing & Validation**
- Pytest: 100 sims pre/post (track confs/yr, inspiration freq, scoop clusters, MS triggers).
- Stress: Long seeds—no >120mo without choice; morale curves varied.
- Metrics: 30-40% PhD win, avg morale 45-60% end.

V2.9
Below is a concrete, execution-oriented V2.9 Improvement Plan that integrates the expert review and respects your stated design philosophy: interesting, realistic, not cumbersome. I’ll be blunt where tradeoffs exist and explicit about scope control.

⸻

GradQuest V2.9 — Solid Improvement Plan

Theme: Stability, Transparency, and Preventing “Unfair Loss”
Non-goal: No weekly-scale realism, no Pro-mode depth, no new major subsystems

V2.9 should feel like “the fair version” of GradQuest: losses are still harsh, but never opaque or accidental.

⸻

1. Core Objective for V2.9 (Design Anchor)

A player should never lose because they misunderstood priority, timing, or invisible mechanics.

Failure is allowed. Confusion is not.

Every item below serves this principle.

⸻

2. High-Priority Gameplay Fixes (Must Ship)

2.1 Quals Failure Gate → Quals Priority System

Problem
	•	Quals is the #1 failure point
	•	Loss feels abrupt and non-strategic

Actionable Changes
	1.	3-Month Countdown UI
	•	August Y1: yellow “⚠ Quals Approaching”
	•	July Y2: orange “⏳ High Priority”
	•	August Y2: red “🚨 Critical”
	2.	Action Highlighting
	•	“Prep for Quals” button pulses / glows during urgency window
	•	Tooltip explicitly states:
“Failure to prepare = automatic game over in September.”
	3.	Soft Fail Option (Once)
	•	First failure triggers:
	•	−25 morale
	•	+Exhaustion
	•	Forced 3-month delay (retest)
	•	Second failure = game over

Why this works
	•	Keeps realism
	•	Removes “I didn’t know” losses
	•	Still punishing

⸻

2.2 Research Pipeline Buffers (Anti-Frustration)

Problem
	•	Full figure reset after rejection feels excessive
	•	Especially bad after long review times

Actionable Changes
	1.	Major Revision Carryover
	•	On Major Revision:
	•	Retain 1 figure
	•	UI shows “Figure salvaged from revisions”
	2.	Advisor Trait Interaction
	•	High Attention Span advisor → higher chance of carryover
	•	High Strictness → no carryover
	3.	Explicit Messaging
	•	Event text explains why carryover happened or didn’t

Why this works
	•	Keeps grind real
	•	Rewards alignment
	•	Reduces rage quits

⸻

3. Advisor & Resilience Systems (Light, Not Pro-Mode)

3.1 Strategic Alignment (Visible, Simple)

Problem
	•	Advisor traits are opaque
	•	Players can’t tell if they’re “playing well”

Actionable Changes
	1.	Add visible stat: Strategic Alignment (0–100)
	2.	Increases when:
	•	Acting in line with advisor feedback
	•	Using Pitch Sessions effectively
	3.	Effects:
	•	−10–25% morale decay
	•	Slightly reduced review RNG variance

Explicit Non-Goal
	•	No weekly modeling
	•	No advisor micromanagement

Why this works
	•	Makes “learning your advisor” legible
	•	Reinforces resilience framing

⸻

3.2 Advisor Feedback Signal Clarity

Actionable Changes
	•	Every advisor quote tagged internally as:
	•	Positive
	•	Neutral
	•	Warning
	•	UI hint on hover:
“This feedback improves success odds if followed.”

This preserves ambiguity without hiding mechanics.

⸻

4. UI / UX Transparency Fixes (High ROI, Low Cost)

4.1 Pipeline Visibility Upgrade

Problem
	•	Players don’t know how close they are to submission

Actionable Changes
	1.	Inventory line:
	•	“Figures: 2 / 3”
	2.	Action button subtitle:
	•	“1 more figure needed to submit”

Zero mechanical change, massive clarity gain.

⸻

4.2 Status Impact Explanations

Problem
	•	Status effects silently block actions

Actionable Changes
	•	Disabled buttons show tooltip:
	•	“Blocked due to: Broken Equipment”
	•	“Expected resolution: 2 months”

This converts confusion into planning.

⸻

4.3 Event History Expansion

Actionable Changes
	•	Increase history cap from 20 → 50
	•	Add category icons (Advisor / Research / RNG / Personal)

This reinforces GradQuest as a debuggable system, not chaos.

⸻

5. RNG & Event Fairness Adjustments

5.1 Action Hijacking Guardrails

Problem
	•	Player-selected actions overridden by events

Actionable Changes
	1.	Priority Lock
	•	Time-critical actions (Quals, Submission) cannot be hijacked
	2.	Event Deferral
	•	Seasonal events can delay but not cancel chosen actions
	3.	Explicit Messaging
	•	“Your conference trip was delayed due to Holiday Break.”

This preserves realism without stealing agency.

⸻

5.2 RNG Caps & Cooldowns

Actionable Changes
	•	Scooped events:
	•	Cooldown: 6–9 months
	•	Imposter syndrome:
	•	Reduced impact if morale already low
	•	Reviewer #2:
	•	No consecutive Major Revisions without a neutral outcome in between

⸻

6. MS-Out Reframe (Narrative, Not Mechanics)

6.1 MS-Out as Strategic Ending

Actionable Changes
	1.	Rename button:
	•	“Strategic Master’s Exit”
	2.	Ending cards emphasize:
	•	Salary outcomes
	•	Career momentum
	3.	Ending tone:
	•	“You chose stability over uncertainty.”

No new systems needed, just reframing and copy changes.

⸻

7. Technical Debt Reduction (Minimal, Realistic)

7.1 Ruleset Parity Safeguard (V2.9 Scope)

Problem
	•	Dual-engine drift

Actionable V2.9 Compromise
	•	Define one authoritative ruleset (JS or YAML)
	•	Add a “logic checksum” comment block
	•	Manual but auditable parity for now

Explicitly defer
	•	Full YAML runtime parsing → V3.x

⸻

8. Opportunity Cost Visualization (Passive, Optional)

8.1 Toggleable Opportunity Cost Panel

Actionable Changes
	•	Optional UI toggle:
	•	“Industry Salary vs Stipend”
	•	Morale drain:
	•	Slow, asymptotic
	•	Never lethal alone

Important
	•	No forced guilt
	•	Player can hide it

⸻

9. What V2.9 Will NOT Do (Critical)

To avoid collapse:
	•	❌ Weekly time scale
	•	❌ Pro-mode realism
	•	❌ Multiple advisor personalities in one run
	•	❌ New major stats
	•	❌ Agent-based simulation

V2.9 is about fairness and clarity, not depth.

⸻

Final Assessment

If implemented cleanly, V2.9 will be the first version that:
	•	Feels fair even when brutal
	•	Teaches players why they failed
	•	Can survive Reddit / Hacker News scrutiny
	•	Creates trust for future Pro mode




⸻


GradQuest V2.10 Improvement Plan

Theme: Resilience Under Pressure
Design Goal: Players should lose because they made hard tradeoffs — not because the system quietly cornered them.

⸻

0. What V2.10 Is (and Is Not)

V2.10 IS
	•	A stabilization + agency release
	•	Focused on morale collapse, advisor limits, and late-stage survival
	•	About making “almost failed” runs meaningfully recoverable

V2.10 IS NOT
	•	A balance rewrite
	•	A Pro / weekly simulator
	•	A conference rework
	•	A UI overhaul

⸻

1. Critical Bug & Logic Corrections (Must Ship)

1.1 Quals Logic Unification (Blocking Issue)

Problem
	•	Logs show Quals passed with Prep = 1
	•	README + code claim Prep ≥ 2 is required

Actionable Fix
	1.	Single source of truth:
	•	QUALS_REQUIRED_PREP = 2
	2.	Hard assertion in triggerQuals():
	•	Log explicit failure reason
	3.	History entry:
	•	“Quals passed with Prep = X (Required: 2)”

Outcome
	•	Eliminates silent logic drift
	•	Makes Quals debuggable, not mystical

⸻

2. Advisor as Finite Resource (Fixing the “Invisible Guardian”)

2.1 Advisor Intervention Fatigue

Problem
	•	Advisor rescues are unlimited
	•	Yet still fail to prevent death spirals
	•	Feels both overpowered and insufficient

Actionable Changes
	1.	Add hidden counter: advisor_patience (starts at 100)
	2.	Each forced break costs:
	•	−20 patience
	3.	Below 30 patience:
	•	Interventions weaker (shorter rest, less morale restored)
	4.	At 0 patience:
	•	Advisor stops intervening
	•	New message: “You need to handle this yourself now.”

Why
	•	Makes advisor support real but finite
	•	Forces player to build self-resilience

⸻

3. Adaptive Alignment Shield (Core V2.10 Mechanic)

3.1 Alignment → RNG Dampener

Problem
	•	Trial 2 shows correct play still leads to morale collapse
	•	RNG friction compounds uncontrollably

Actionable Changes
	1.	Strategic Alignment (already tracked) now:
	•	Reduces probability of negative research RNG
	2.	Concrete rules:
	•	Alignment ≥ 60:
	•	“Reviewer #2” disabled during Document Findings
	•	Alignment ≥ 80:
	•	“Visualization unclear” cannot occur twice in a row

Design Rationale
	•	Rewards learning the system
	•	Does NOT guarantee success
	•	Breaks death spirals without removing difficulty

⸻

4. Emergency-State Agency (Anti–Dead Man Walking)

4.1 Medical Leave / Therapy Action

Trigger
	•	Appears only when Morale < 15

Action
“Medical Leave”
	•	+40 morale
	•	−1 exhaustion
	•	Costs 3–6 months (randomized)
	•	Resets current project to Idea

Constraints
	•	Can only be used once per run
	•	Cannot be used during review or quals window

Why This Matters
	•	Converts inevitable failure into strategic retreat
	•	Deeply realistic
	•	Preserves consequences

This is the single most important V2.10 addition.

⸻

5. Quals: Forcing the Hard Choice

5.1 Auto-Prompted Last-Minute Cram

Problem
	•	Players miss Cram option even when doomed

Actionable Change
	•	In August Y2, if Prep < 2:
	•	Modal prompt:
“You are unprepared.
Cram (High Cost) or Face the Committee (High Risk)?”

Effects
	•	Cram:
	•	−25 morale
	•	+exhaustion
	•	Guaranteed pass
	•	Face Committee:
	•	Existing logic

Outcome
	•	Failure becomes a choice, not an accident

⸻

6. Figure Grind Decompression (Late-Game Focus)

6.1 Reviewer Fatigue Cooldown

Problem
	•	Repeated figure rejection causes morale freefall

Actionable Change
	•	After 2 consecutive figure rejections:
	•	Next figure attempt has +30% success chance
	•	UI message:
	•	“You’re finally seeing what reviewers want.”

This simulates learning without removing grind.

⸻

7. Review Tracker (Transparency, Not Acceleration)

7.1 Passive Review Progress Bar

Actionable Changes
	•	For each submitted paper:
	•	Show: “Journal Review: 7 / 10 months”
	•	No mechanical effect
	•	Purely informational

Why
	•	Removes “flying blind” stress
	•	Makes waiting psychologically survivable

⸻

8. Network: From Scalar to Tactical Resource

8.1 Peer Review Action (High Network Only)

Unlock
	•	Network ≥ 80

Action
“Peer Review Figures”
	•	Once per paper
	•	Skips one figure RNG check
	•	Costs −10 network

Design Benefits
	•	Makes high network meaningfully different
	•	Adds tradeoff (network is no longer free)

⸻

9. What V2.10 Explicitly Will NOT Add

To prevent scope collapse:
	•	❌ Weekly mechanics
	•	❌ Conference rebalance
	•	❌ New stats
	•	❌ Salary optimization
	•	❌ Multiple advisor archetypes
	•	❌ Pro-mode features

Those belong to V3.x.

⸻

10. Success Criteria for V2.10

V2.10 is successful if:
	•	No player loses Quals due to misunderstanding
	•	Death spirals require multiple bad decisions
	•	Advisor support feels finite and human
	•	Emergency state offers a painful but real escape
	•	High-alignment, high-skill play demonstrably reduces RNG pain

⸻

Final Assessment

V2.9 made GradQuest fair.
V2.10 should make it survivable without making it easy.

This is the release where:
	•	Resilience stops being flavor text
	•	Agency appears exactly when things are worst
	•	The game earns the right to be called a simulator