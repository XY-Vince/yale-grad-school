# GradQuest Game Evaluation Report
## HMI and Gameplay Analysis from a General User Perspective

---

## Executive Summary

GradQuest is a PhD life simulator that successfully captures the emotional and strategic challenges of graduate school. The game demonstrates strong thematic design and meaningful mechanics, though it suffers from several critical HMI issues that obscure important information and reduce player clarity. The gameplay loop is engaging but could benefit from better feedback systems and visual hierarchy improvements.

---

## 1. HMI (Human-Machine Interface) Analysis

### 1.1 Strengths

**Visual Organization and Layout**

The game employs a well-structured card-based interface that effectively separates different information categories. The status dashboard at the top provides quick access to six key metrics (Date, Morale, Advisor, Publications, Network, Alignment), while the research pipeline on the right offers clear visual progression tracking. The use of emoji icons throughout the interface provides immediate visual recognition and adds personality to the academic simulation.

**Color Coding System**

The morale and advisor status bars utilize intuitive color coding (green for positive, yellow for neutral, red for critical) that communicates emotional states at a glance. This visual language extends to status effects, where negative conditions like "Exhaustion" appear in red and positive buffs like "Renewed Focus" display in orange/yellow.

**Action Button Design**

Action buttons feature clear emoji prefixes and descriptive subtitles that explain their purpose. For example, "📚 Read Papers - Search for ideas" immediately communicates both the action and its outcome. The buttons also provide contextual information such as remaining uses ("Conference 1/1 remaining for this yr") and costs ("Pre-Register Idea -5 network").

### 1.2 Critical Issues

**Event Feed Information Loss**

The most significant HMI flaw involves the event feed system. The "This Month" and "Last Month" sections display only the most recent events, causing critical information to be hidden. During my playthrough, the qualification exam success (a major milestone) was completely obscured by a subsequent imposter syndrome event. The message "🎓 QUALS PASSED! 🎓 (+23 morale)" only appeared in the History panel, not in the main feed. This creates confusion about whether important milestones were achieved.

**Recommendation**: Implement a priority system where major milestones (quals passing, paper acceptance, thesis defense) are pinned or highlighted in the feed for at least 2-3 turns. Consider adding a dedicated "Achievements" notification area separate from the general event feed.

**Modal Dialog Usability**

The Help modal demonstrates poor interaction design. Standard closing methods fail: pressing Escape does nothing, clicking outside the modal has no effect, and users must scroll to find the "Got it!" button. This violates common UX conventions and creates unnecessary friction when players need to reference game mechanics.

**Recommendation**: Implement standard modal closing behaviors (Escape key, click outside, visible X button in corner) and ensure the close button is always visible without scrolling.

**Unclear Research Pipeline States**

The research pipeline uses multiple visual indicators (arrows, dots, badges with numbers, checkmarks) without clear explanation. During gameplay, it was difficult to distinguish between "in progress" (→), "blocked" (●), and "completed" (×1) states. The red dot indicator that appeared during discovery phase was particularly ambiguous.

**Recommendation**: Add a legend or tooltip system explaining pipeline symbols. Use more distinct visual states (e.g., grayed out for locked, animated for in-progress, green checkmark for completed).

**Button State Feedback**

While recently-used buttons change to purple/blue highlighting, this feedback is inconsistent and sometimes confusing. Multiple buttons may remain highlighted simultaneously, making it unclear which action was most recent or whether the highlighting indicates availability versus recent use.

**Recommendation**: Implement clearer button states with distinct visual treatments for: available (default), recently used (brief highlight that fades), unavailable (grayed), and recommended (subtle glow or border).

### 1.3 Minor Issues

**Text Density in Help Screen**

The help modal contains comprehensive information but presents it in a dense, small-font format that requires scrolling. While the emoji icons help organize sections, the sheer volume of information is overwhelming for new players.

**Recommendation**: Break help content into tabbed sections (Basics, Research, Publications, Events, Strategy) or implement a progressive tutorial that introduces mechanics as they become relevant.

**Status Card Information Hierarchy**

The Publications card displays "0 (0 / 2 / 0 c)" without clear explanation of what each number represents. This cryptic notation requires consulting the help documentation.

**Recommendation**: Use tooltips or expand the display to show "0 Journal / 2 Conference / 0 Complete" with clear labels.

**Inconsistent Action Availability**

Some actions appear and disappear based on game state (e.g., Medical Leave, Summer Internship) while others remain visible but presumably inactive. This inconsistency makes it difficult to understand which actions are contextual versus permanently available.

**Recommendation**: Group actions into categories (Research, Self-Care, Strategic, Emergency) and use visual separators. Add "Coming Soon" or "Unavailable" states with brief explanations.

---

## 2. Gameplay Analysis

### 2.1 Core Mechanics Strengths

**Meaningful Strategic Choices**

The game presents genuinely difficult decisions with clear tradeoffs. The choice between Conference Papers (fast, builds network) and Journal Papers (slow, counts toward graduation) creates strategic tension. The High-Throughput Experiment option (40% success, +2 figures on success, -morale and exhaustion on failure) demonstrates excellent risk-reward design with transparent probability.

**Emergent Narrative**

Random events like "Your labmate just published - why can't you?" and "Everyone else seems so much smarter than you..." effectively simulate the emotional challenges of PhD life. The advisor personality system, revealed through pitch sessions, adds character depth and makes the advisor feel like a real person rather than a game mechanic.

**Resource Management Complexity**

The game balances multiple resources (morale, network, alignment, quals prep, research progress) that interact in interesting ways. Low morale triggers advisor concern and unlocks emergency options, while high network unlocks peer benefits. This creates a satisfying optimization puzzle.

**Time Pressure and Planning**

The qualification exam deadline in September Year 2 provides effective time pressure that forces players to balance research progress with exam preparation. The warning system ("⚠️ This Year" then "URGENT: 3mo left!") escalates appropriately.

### 2.2 Gameplay Issues

**Opaque Probability Systems**

While the High-Throughput Experiment explicitly shows 40% success rate, most research actions have hidden success probabilities. Players cannot tell whether "Develop Findings" has a 50% or 90% chance of success, making it difficult to plan effectively. During my playthrough, one attempt failed (advisor requested redo) while the next succeeded, but the underlying mechanics remained mysterious.

**Recommendation**: Add optional "Advanced Info" tooltips showing approximate success rates based on current game state (e.g., "Develop Findings: ~60% success, improved by alignment and morale").

**Morale Decay Unclear**

Morale decreased at various points without clear explanation. The transition from "Good" to "Okay" to "Low" seemed to involve both random events and passive decay, but the relative contributions were opaque. The help text mentions "-1 morale decay per 25 alignment" but this is difficult to track during gameplay.

**Recommendation**: Add a morale change log in the History panel showing all sources of morale change ("+3 from figure completion, -2 from monthly decay, -7 from imposter syndrome event = -6 total").

**Research Pipeline Reset Confusion**

After submitting the journal paper, the research pipeline partially reset, but it was unclear which elements carried over and which needed to be rebuilt. The Ideas and Findings showed "×1" and "→" respectively, but whether this represented progress toward a second paper was ambiguous.

**Recommendation**: Add clear messaging when paper is submitted: "Paper submitted! Your research pipeline has been partially reset. You can now start working on your next project while waiting for reviews."

**Limited Tutorial or Onboarding**

New players are immediately presented with the full game interface and a dense help screen. There's no guided first turn or tutorial highlighting key mechanics. I had to experiment to understand that actions advance time and that the research pipeline requires sequential completion.

**Recommendation**: Implement a brief interactive tutorial covering: (1) actions advance time, (2) research pipeline progression, (3) morale management, (4) quals deadline. Alternatively, add contextual tooltips that appear on first interaction with each game element.

### 2.3 Balance Observations

**Quals Preparation Timing**

The qualification exam preparation felt well-balanced. With three prep sessions required and warnings starting 6+ months in advance, players have adequate time to prepare while still feeling pressure. The "Need 2 more sessions" guidance was particularly helpful.

**Morale Recovery Options**

The emergency options (Medical Leave, Take Time Off) appeared at appropriate thresholds. However, the High-Throughput Experiment failure that dropped morale to "Critical" felt punishing given the already-stated 60% failure rate. Players who take calculated risks shouldn't be pushed into emergency situations.

**Recommendation**: Reduce the morale penalty for High-Throughput Experiment failure, or add a warning that failure may trigger critical morale. Alternatively, make the exhaustion status less severe.

**Research Progression Pacing**

The research pipeline (Read → Idea → Findings → Discovery → Figures ×3 → Paper) takes approximately 8-10 months with some failures, which aligns with the stated 8-12 month journal paper timeline. This pacing feels realistic and creates satisfying progression milestones.

---

## 3. User Experience Observations

### 3.1 Positive Aspects

**Thematic Consistency**

The game maintains excellent thematic coherence. Every mechanic reinforces the PhD experience: imposter syndrome events, advisor personality quirks, the tension between publishing quickly versus building toward graduation, and the emotional toll of research setbacks. This creates strong immersion.

**Emotional Engagement**

The morale system effectively creates emotional investment. Seeing morale drop to "Critical" after a failed experiment genuinely felt concerning, and the advisor's worried message ("Have you considered the Master's exit?") added narrative weight to the mechanical state.

**Information Accessibility**

The History panel provides a complete event log that allows players to review their entire journey. This is invaluable for understanding long-term patterns and reviewing missed information. The Save/Load system enables experimentation with different strategies.

### 3.2 Areas for Improvement

**Feedback Timing**

Many actions provide feedback only through the event feed, which can be overlooked when multiple events occur simultaneously. The qualification exam success being buried under other events exemplifies this issue.

**Recommendation**: Add brief toast notifications or modal confirmations for major milestones that require explicit acknowledgment.

**Goal Tracking**

While the game states "publish 3 papers and defend your thesis" as the goal, there's no persistent goal tracker showing "Papers: 1/3" or "Thesis Progress: Not Started." Players must infer progress from the Publications card.

**Recommendation**: Add a dedicated "Graduation Progress" card showing papers completed, thesis status, and estimated time to completion.

**Action Consequences Clarity**

Some actions have unexpected consequences. Submitting a paper caused morale to drop significantly, but it was unclear whether this was due to submission stress, time passage, or a random event. Better telegraphing of consequences would help players make informed decisions.

**Recommendation**: Add "Expected Outcomes" to action tooltips: "Submit Journal Paper: Advances 1 month, -5 morale (submission stress), paper enters 8-12 month review period."

---

## 4. Specific Suggestions for Improvement

### 4.1 High Priority

1. **Fix Event Feed Information Loss**: Implement priority messaging for major milestones
2. **Improve Modal Usability**: Add standard closing methods to all modals
3. **Add Success Probability Indicators**: Show approximate chances for research actions
4. **Implement Progressive Tutorial**: Guide new players through first few turns
5. **Create Morale Change Log**: Show detailed breakdown of morale changes

### 4.2 Medium Priority

6. **Add Pipeline Legend**: Explain visual symbols in research pipeline
7. **Improve Button State Feedback**: Clearer visual distinction between button states
8. **Expand Status Card Labels**: Make cryptic numbers more explicit
9. **Add Goal Tracking Card**: Persistent display of graduation progress
10. **Implement Toast Notifications**: Brief pop-ups for important events

### 4.3 Low Priority

11. **Categorize Actions**: Group buttons by type for easier scanning
12. **Add Action Consequence Previews**: Show expected outcomes before taking action
13. **Implement Tabbed Help**: Organize help content into digestible sections
14. **Add Tooltips Throughout**: Contextual help on hover for all game elements
15. **Create Achievement System**: Celebrate milestones with persistent badges

---

## 5. Conclusion

GradQuest successfully captures the complexity and emotional reality of PhD life through thoughtful game design. The core mechanics create meaningful strategic choices, and the thematic elements resonate authentically. However, critical HMI issues around information visibility and feedback clarity significantly diminish the user experience.

The most impactful improvements would focus on ensuring players never miss important information (event feed priority system), making game mechanics more transparent (success probabilities, morale tracking), and following standard UX conventions (modal closing, button states). With these refinements, GradQuest could evolve from a compelling proof-of-concept into a polished, accessible simulation that effectively communicates the PhD experience to a broad audience.

### Overall Assessment

**Strengths**: Thematic coherence, strategic depth, emotional engagement, realistic simulation
**Weaknesses**: Information visibility, feedback clarity, tutorial/onboarding, probability transparency
**Recommendation**: Address high-priority HMI issues before expanding content or features

---

*Report based on 17 months of simulated gameplay (September Year 1 through January Year 3), including successful qualification exam passage and first journal paper submission.*
