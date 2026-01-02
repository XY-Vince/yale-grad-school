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