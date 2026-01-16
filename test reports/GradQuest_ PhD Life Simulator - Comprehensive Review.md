# GradQuest: PhD Life Simulator - Comprehensive Review

GradQuest is a text-based simulation game that captures the essence of the doctoral journey through a series of strategic decisions and random events. This review provides a detailed account of the gameplay experience, a technical analysis of the codebase, and a set of recommendations for future development.

## Gameplay Documentation

The following table summarizes the key milestones and outcomes from a full playthrough of GradQuest. The session lasted 13 in-game months, starting in September of Year 1 and ending abruptly in September of Year 2.

| Month | In-Game Date | Primary Action | Key Outcome | Morale Change |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Sep, Year 1 | Start Game | Initialized with 10 Network and "Okay" Morale. | N/A |
| 2-3 | Oct-Nov, Year 1 | Read Papers | Explored literature; no immediate ideas found. | Neutral |
| 4 | Dec, Year 1 | Conference | Triggered "Holiday Break" event instead of conference. | +5 |
| 5 | Jan, Year 2 | Read Papers | **New Idea Gained!** Research pipeline initiated. | Neutral |
| 6 | Feb, Year 2 | Work on Idea | Developed "Initial Findings." | +5 |
| 7 | Mar, Year 2 | Develop Findings | Achieved **Key Discovery** milestone. | +5 |
| 8 | Apr, Year 2 | Document Findings | Created Figure 1/3. | +3 |
| 9 | May, Year 2 | Document Findings | Negative event: "Reviewer 2 would hate this figure." | Neutral |
| 10 | Jun, Year 2 | Pitch Session | Learned advisor style; increased network. | +3 Network |
| 11 | Jul, Year 2 | Document Findings | Created Figure 2/3. | +3 |
| 12 | Aug, Year 2 | Document Findings | Created Figure 3/3; gained "Flash of Inspiration." | +15 |
| 13 | Sep, Year 2 | Write Paper | **Game Over**: Dismissed for failing Qualifying Exams. | Dismissed |

> "You were dismissed after failing quals. You needed at least 2 preparation sessions." — *GradQuest Game Over Screen*

## Technical Observations

The GradQuest repository [1] reveals a dual-architecture approach, maintaining both a static web version for easy deployment and a more robust Python-based engine for complex logic.

### 1. Architecture and Design
The project is split into two main components:
*   **Static Frontend**: Located in `docs/index.html`, this is a self-contained "single-file" game using vanilla JavaScript and CSS. It handles the UI, state management, and event triggers for the web version.
*   **Python Backend**: Located in the `gradquest/` directory, this version uses a YAML-driven event engine. It features a `VariableStore` for state management and an `EventEngine` for processing game logic based on rulesets defined in `data/rulesets/`.

### 2. Event System Analysis
The YAML-based event system [2] is highly modular. Events are triggered by specific conditions (e.g., `year === 2 && month === 9`) and can execute a variety of actions such as updating variables, setting statuses, or ending the game. This design allows for easy expansion of game content without modifying the core engine code.

### 3. Gameplay Balance
The "Qualifying Exam" (Quals) serves as a hard gate in the game. As observed in the gameplay log, failing to use the "Prep for Quals" action at least twice before Month 13 results in an immediate game over, regardless of research progress. This accurately reflects the high-stakes nature of real-world academic milestones but can be frustrating for new players who prioritize research over preparation.

## Suggestions for Improvement

Based on the gameplay experience and code review, the following improvements are suggested to enhance player engagement and game depth.

### Feature Enhancements
| Category | Suggestion | Impact |
| :--- | :--- | :--- |
| **UI/UX** | **Quals Warning System**: Implement a countdown or visual reminder starting 3-6 months before the exam. | Reduces "unfair" game overs for new players. |
| **Mechanics** | **Collaboration System**: Allow players to spend "Network" points to speed up figure creation or paper writing. | Makes the Network stat more meaningful. |
| **Content** | **Grant Writing Mini-game**: Add a "Write Grant" action to secure funding, which could provide morale or research bonuses. | Adds another layer of academic realism. |
| **Technical** | **Unified Logic**: Sync the JavaScript logic in `docs/index.html` with the YAML rulesets to ensure consistency across versions. | Simplifies maintenance and content updates. |

### Strategic Recommendations
1.  **Dynamic Advisor Traits**: Expand the advisor system so that different advisors have unique hidden modifiers (e.g., "The Perfectionist" increases figure requirements but boosts paper acceptance rates).
2.  **Branching Career Paths**: Introduce more "Strategic Exits" beyond the Master's degree, such as "Industry Internship" or "Post-doc" opportunities based on the player's final stats.
3.  **Visual Pipeline**: Enhance the "Research Pipeline" UI element to show a progress bar for each paper currently in the review cycle.

## References
[1] [GradQuest GitHub Repository](https://github.com/XY-Vince/GradQuest)
[2] [GradQuest Default Rulesets (YAML)](https://github.com/XY-Vince/GradQuest/tree/main/data/rulesets/default)
