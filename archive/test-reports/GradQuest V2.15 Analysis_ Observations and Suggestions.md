# GradQuest V2.15 Analysis: Observations and Suggestions

## Executive Summary

GradQuest V2.15 represents a significant improvement over the previous version, with several critical HMI issues addressed and new features implemented. This analysis documents the improvements, remaining issues, and suggestions for further enhancement.

**Version**: 2.15  
**Analysis Date**: January 4, 2026  
**Gameplay Duration**: 40+ months of exploration

---

## Part 1: Major Improvements in V2.15

### 1.1 Pitch Session is Now Available

**Previous Issue**: Pitch Session was mentioned in help but not available as an action button.

**V2.15 Status**: Pitch Session is now available as an action (confirmed in help text: "Use Pitch Session to learn their preferences").

**Observation**: The button is not visible in the initial action panel, but the help system clearly states it's available. This suggests it may appear as a new action after certain conditions are met, or it may be accessible through a different mechanism.

**Recommendation**: Make Pitch Session visible as a button from the start, with description "Learn advisor preferences (+3 network)".

---

### 1.2 Qualification Exam Now Has Clear Mechanics

**Previous Issue**: Quals exam was prepared for but didn't trigger visibly; players didn't know if they passed.

**V2.15 Status**: Help now specifies: "Qual exam: September Year 2 (prep level 3+ to pass!)" and "First failure gives ONE retake chance (3 months)".

**Observation**: The help text is much clearer about exam mechanics. The requirement of "prep level 3+" is explicit, and the retake mechanism is documented.

**Remaining Issue**: The exam still doesn't appear to trigger visibly in gameplay. Players must prepare and then wait to see if they pass. No clear pass/fail event is displayed.

**Recommendation**: Create a visible exam event in September Year 2 that shows:
- Current prep level (e.g., "Prep Level: 2/3")
- Pass/fail result
- Consequences (if failed, retake opportunity)

---

### 1.3 Alignment System Still Opaque

**Previous Issue**: Alignment accumulated but had no visible meter or explanation.

**V2.15 Status**: Help mentions alignment ("+2 alignment" in feedback), but no meter is visible in the UI.

**Observation**: The feedback shows alignment changes, but the system remains largely opaque. No meter, no explanation of effects.

**Remaining Issue**: Same as before—alignment is invisible and unexplained.

**Recommendation**: Add alignment meter to status bar showing current value and effects.

---

### 1.4 Emergency Options Now Documented

**Previous Issue**: Medical Leave and other emergency options were mentioned but not clearly explained.

**V2.15 Status**: Help now includes "Emergency Options" section:
- Medical Leave: +40 morale when critical, costs 3-6 months (one-time)
- Vacation: Advisor may suggest rest when morale low
- After 2 failed figures: learning bonus (+30% success)

**Observation**: Excellent improvement! These mechanics are now clearly documented.

**Remaining Issue**: These options are still not visible as buttons in the main UI. Players must know to look for them or read the help.

**Recommendation**: Add "Medical Leave" button when morale is critical. Show "Vacation" option when advisor suggests it.

---

### 1.5 Research Pipeline Visualization Unchanged

**Previous Issue**: Pipeline notation was confusing (e.g., "Ideas ×2, Findings, Discovery ×2, Figures ×1").

**V2.15 Status**: Same notation as before. No visual improvements.

**Observation**: The pipeline still shows "Ideas → Findings → Discovery → Figures" without quantities or progress indicators.

**Remaining Issue**: Same as before—ambiguous notation about how many figures per discovery.

**Recommendation**: Clarify that each discovery requires 3 figures. Show "Figures ×3" only when all figures are complete.

---

### 1.6 Help System Improvements

**Previous Issue**: Critical information was hidden in Help dialog.

**V2.15 Status**: Help dialog is more comprehensive and better organized:
- Clear goal statement
- Research pipeline with visual icons
- Publication tracks explained
- Advisor system with Pitch Session mentioned
- Peer network explained
- Strategic exits (R&D Lead, Data Scientist, Great Escape)
- Key events with specific requirements (e.g., "prep level 3+ to pass")
- Emergency options section

**Observation**: Significant improvement in help content organization and clarity.

**Remaining Issue**: Help is still hidden behind a button. New players may not discover it.

**Recommendation**: Show a brief tutorial on first playthrough that covers the main systems.

---

## Part 2: Current Gameplay Observations (V2.15)

### 2.1 Initial State (Sep, Year 1)

**Status at Start**:
- Date: Sep, Year 1 (Fall · Month 1 · 0 credits)
- Morale: Okay (yellow bar)
- Advisor: Happy (green bar)
- Publications: 0 (0 J + 0 C) [Note: New notation showing Journal and Conference separately]
- Network: 10
- Status Effects: First Year

**Observation**: The publications display now shows "0 (0 J + 0 C)" which clearly separates journal and conference papers. This is an improvement over the previous "0 papers + 0 conference" notation.

### 2.2 First Action: Read Papers

**Action**: Read Papers (Oct, Year 1)

**Result**: "You read papers and gained perspective. (+2 alignment)"

**Observations**:
- Alignment is now explicitly shown in feedback
- No visible alignment meter in UI
- Research pipeline still shows "Ideas → Findings → Discovery → Figures" without quantities
- Morale remains "Okay"
- Advisor remains "Happy"

**HMI Issue**: The feedback mentions alignment, but there's no way to see the total alignment value. Players can't track progress toward any alignment-based rewards.

---

### 2.3 Help System Content Review

The help dialog now includes:

**Research Pipeline**: 📚 Read → 💡 Idea → 🔬 Findings → 🎯 Discovery → 📊 Figures (×3) → 📝 Paper

**Key Improvement**: The help now explicitly shows "(×3)" for figures, clarifying that 3 figures are needed.

**Publication Tracks**:
- Journal Paper: 8-12 months, counts toward graduation
- Conference Paper: 4 months, builds network (+15)

**Advisor System**:
- Hidden traits that affect outcomes
- Pitch Session to learn preferences
- Signals: fast/slow response, harsh/encouraging tone

**Key Events**:
- Qual exam: September Year 2 (prep level 3+ to pass!)
- First failure gives ONE retake chance (3 months)
- Imposter syndrome, getting scooped, teaching duty
- Reviewer #2 may request major revisions

**Emergency Options**:
- Medical Leave: +40 morale when critical, costs 3-6 months (one-time)
- Vacation: Advisor may suggest rest when morale low
- After 2 failed figures: learning bonus (+30% success)

---

## Part 3: Remaining HMI Issues in V2.15

### 3.1 Critical Issues

**Issue 1: Pitch Session Not Visible**
- Help mentions "Use Pitch Session to learn their preferences"
- No "Pitch Session" button is visible in the actions panel
- Players must guess when/how to access it
- **Severity**: High - Core mechanic is hidden
- **Recommendation**: Add Pitch Session as a visible button from the start

**Issue 2: Alignment Meter Missing**
- Alignment accumulates but has no visible meter
- No explanation of what alignment does
- Players can't track progress
- **Severity**: High - System is opaque
- **Recommendation**: Add alignment display to status bar

**Issue 3: Qualification Exam Not Visible**
- Help says "Qual exam: September Year 2 (prep level 3+ to pass!)"
- No visible exam event in gameplay
- Players don't know if they passed or failed
- **Severity**: High - Critical milestone is invisible
- **Recommendation**: Create visible exam event with pass/fail result

**Issue 4: Emergency Options Not Accessible**
- Medical Leave and Vacation are documented but not visible as buttons
- Players must know to look for them
- **Severity**: Medium - Important safety valves are hidden
- **Recommendation**: Show Medical Leave button when morale is critical

---

### 3.2 Medium Priority Issues

**Issue 5: Research Pipeline Notation Confusing**
- "Ideas → Findings → Discovery → Figures" without quantities
- Unclear how many figures per discovery
- Help clarifies "(×3)" but UI doesn't
- **Severity**: Medium - Causes confusion about progression
- **Recommendation**: Show quantities in pipeline (e.g., "Figures ×3 needed")

**Issue 6: Publications Display Improved But Still Minimal**
- Now shows "0 (0 J + 0 C)" which is clearer
- But no indication of progress toward graduation (e.g., "1/3 papers published")
- **Severity**: Medium - Players can't see graduation progress
- **Recommendation**: Show "1/3 papers published, 2 under review"

**Issue 7: No Progress Dashboard**
- Players must manually track: papers published, papers under review, current research stage
- No single view showing "estimated time to graduation"
- **Severity**: Medium - Players feel lost about overall progress
- **Recommendation**: Create Status/Dashboard button showing graduation progress

**Issue 8: Event Log Still Hard to Scan**
- Small text, two-tab system (This Month / Last Month)
- No filtering or search
- **Severity**: Low - Information is available but not well-organized
- **Recommendation**: Add filter by event type (research, morale, advisor, milestones)

---

### 3.3 Low Priority Issues

**Issue 9: Keyboard Shortcuts Not Visible**
- Actions are numbered 1-5 but shortcuts aren't shown on buttons
- **Severity**: Low - Discoverable through trial
- **Recommendation**: Display "Press 1" on button corners

**Issue 10: Help Content Not Integrated**
- Critical information is still hidden in Help dialog
- New players may not discover it
- **Severity**: Low - Help is accessible
- **Recommendation**: Show brief tutorial on first playthrough

---

## Part 4: Detailed Recommendations for V2.15+

### Priority 1: Make Hidden Actions Visible

**Recommendation 1.1: Add Pitch Session Button**
- **Current**: Mentioned in help but not visible
- **Change**: Add "🎤 Pitch Session" button to actions panel
- **Description**: "Learn advisor preferences (+3 network)"
- **Expected Impact**: Players can discover advisor traits through gameplay

**Recommendation 1.2: Add Medical Leave Button**
- **Current**: Documented in help but not accessible
- **Change**: Show "🏥 Medical Leave" button when morale is critical (< 10%)
- **Description**: "Take medical leave (+40 morale, costs 3-6 months, one-time use)"
- **Expected Impact**: Players have a clear safety valve when morale is critical

**Recommendation 1.3: Show Vacation Option**
- **Current**: "Advisor may suggest rest when morale low"
- **Change**: When morale is low, show advisor message: "You look exhausted. Why don't you take a week off?"
- **Add Button**: "☀️ Vacation" - Rest and recover (similar to Take a Break)
- **Expected Impact**: Clear guidance when morale is declining

---

### Priority 2: Add Missing Meters and Displays

**Recommendation 2.1: Add Alignment Meter**
- **Current**: Alignment accumulates but is invisible
- **Change**: Add to status bar or advisor card
- **Display**: "Alignment: 12/20" with bar indicator
- **Explanation**: "Alignment affects advisor mood and research success"
- **Expected Impact**: Players can track alignment progress

**Recommendation 2.2: Add Prep Level Display**
- **Current**: Help mentions "prep level 3+ to pass" but no meter exists
- **Change**: Show prep level when "Prep for Quals" is available
- **Display**: "Qual Prep Level: 2/3" with progress bar
- **Expected Impact**: Players know exactly how prepared they are

**Recommendation 2.3: Add Graduation Progress**
- **Current**: Publications show "0 (0 J + 0 C)" but no graduation progress
- **Change**: Show "Papers: 1/3 published, 2 under review"
- **Add**: "Estimated time to graduation: 8-12 months"
- **Expected Impact**: Players can see how close they are to finishing

---

### Priority 3: Make Critical Events Visible

**Recommendation 3.1: Visible Qualification Exam**
- **Current**: Exam is prepared for but doesn't trigger visibly
- **Change**: Create exam event in September Year 2
- **Event Content**:
  - Show prep level (e.g., "Prep Level: 3/3")
  - Show pass/fail result
  - If failed: "You may retake in 3 months"
  - If passed: "Congratulations! You passed your qualification exam"
- **Expected Impact**: Players know the outcome of their preparation

**Recommendation 3.2: Paper Decision Events**
- **Current**: Papers under review have no progress indication
- **Change**: Add random events during review period
  - "Reviewer 1 approves your paper"
  - "Reviewer 2 requests major revisions"
  - "Editor requests clarification"
- **Add Countdown**: Show "Decision expected in 4 months"
- **Expected Impact**: Waiting period feels less passive

**Recommendation 3.3: Scooped Event**
- **Current**: Help mentions "getting scooped" but it's not observed
- **Change**: Implement scooped event when similar research is published
- **Event Content**:
  - "Your research topic has been scooped by another lab!"
  - Options: Pivot research, rush to publish, collaborate
- **Expected Impact**: Adds dramatic tension and teaches adaptation

---

### Priority 4: Improve Information Architecture

**Recommendation 4.1: Create Status Dashboard**
- **Current**: Information scattered across status cards
- **Change**: Add "📊 Status" button that shows:
  - Papers until graduation (e.g., "1/3 published, 2 under review")
  - Estimated time to degree
  - Current research focus
  - Upcoming milestones
  - Advisor mood and recent feedback
- **Expected Impact**: Players can see overall progress at a glance

**Recommendation 4.2: Improve Research Pipeline Display**
- **Current**: "Ideas → Findings → Discovery → Figures" without quantities
- **Change**: Show quantities and progress
  - "Ideas ×2 → Findings ×1 → Discovery ×1 → Figures ×3"
  - Show which discovery each figure set belongs to
  - Display estimated time to completion
- **Expected Impact**: Players understand research progress clearly

**Recommendation 4.3: Enhance Event Log**
- **Current**: Two-tab system with small text
- **Change**:
  - Remove two-tab system; show all events chronologically
  - Add filter by type (research, morale, advisor, milestones)
  - Add search functionality
  - Highlight important events
- **Expected Impact**: Players can find relevant information quickly

---

### Priority 5: Improve Feedback and Communication

**Recommendation 5.1: Show Action Costs**
- **Current**: Button descriptions don't show time/morale cost
- **Change**: Add tooltip showing:
  - Time cost (1 month)
  - Morale impact (e.g., "+8 morale")
  - Prerequisites (if any)
  - Success probability (if applicable)
- **Expected Impact**: Players make informed decisions

**Recommendation 5.2: Clarify Status Effects**
- **Current**: Status effects lack explanation
- **Change**: Hover over status badges to see:
  - Exact mechanical effects (e.g., "Exhaustion: -20% research success")
  - How to remove the effect
  - Duration (if applicable)
- **Expected Impact**: Players understand status effect consequences

**Recommendation 5.3: Show Advisor Mood Trend**
- **Current**: Advisor mood changes without explanation
- **Change**:
  - Display mood trend (improving, stable, declining)
  - Explain mood changes (e.g., "Advisor is pleased with your progress")
  - Suggest actions to improve relationship
- **Expected Impact**: Players understand advisor dynamics

---

## Part 5: Comparison with Previous Version

| Feature | Previous Version | V2.15 | Status |
|---|---|---|---|
| Pitch Session | Hidden, not available | Documented in help, still not visible | Partially improved |
| Alignment Meter | No meter, no explanation | No meter, feedback shows changes | No improvement |
| Quals Exam | Invisible, no feedback | Documented (prep level 3+), still invisible | Partially improved |
| Emergency Options | Mentioned in help | Clearly documented with mechanics | Improved |
| Publications Display | "0 papers + 0 conference" | "0 (0 J + 0 C)" | Slightly improved |
| Help System | Basic | More comprehensive, better organized | Significantly improved |
| Research Pipeline | Confusing notation | Same notation, help clarifies "(×3)" | Slightly improved |
| Event Log | Two-tab system | Same | No improvement |
| Progress Dashboard | None | None | No improvement |
| Status Effects Explanation | Minimal | Minimal | No improvement |

---

## Part 6: Summary of Key Findings

### What Improved in V2.15

1. **Help System**: Much more comprehensive and better organized. Includes emergency options, clear exam requirements, and research pipeline visualization.

2. **Publications Display**: Changed from "0 papers + 0 conference" to "0 (0 J + 0 C)", making it clearer that journal and conference papers are tracked separately.

3. **Documentation**: Critical mechanics (Pitch Session, Medical Leave, learning bonus) are now documented in help.

4. **Clarity**: Help text is more explicit about requirements (e.g., "prep level 3+ to pass").

### What Still Needs Improvement

1. **Hidden Actions**: Pitch Session, Medical Leave, and Vacation are documented but not visible as buttons.

2. **Invisible Systems**: Alignment meter is still missing. Qualification exam still doesn't trigger visibly.

3. **Progress Tracking**: No dashboard showing graduation progress or estimated time to degree.

4. **Event Log**: Still uses two-tab system; no filtering or search.

5. **Information Architecture**: Critical information is still scattered across multiple locations.

### Most Impactful Changes

The most impactful improvements for V2.15+ would be:

1. **Make Pitch Session visible** as a button - enables advisor trait discovery
2. **Add alignment meter** - makes invisible system visible
3. **Create visible qualification exam** - clarifies critical milestone
4. **Add graduation progress display** - shows how close to finishing
5. **Show Medical Leave button** when morale is critical - provides clear safety valve

---

## Conclusion

GradQuest V2.15 represents solid progress on documentation and help system organization. The core improvements focus on making information more accessible through better help content organization.

However, the fundamental HMI issues remain: critical actions and systems are still hidden from the main interface. The next version should focus on making hidden mechanics visible by adding buttons, meters, and dashboards to the main UI.

The game's mechanics are sophisticated and engaging. With the suggested improvements to visibility and information architecture, V2.15+ could become significantly more accessible to new players while maintaining the strategic depth that makes the game engaging for experienced players.

---

## Quick Reference: V2.15 Status

| System | Status | HMI Rating | Priority |
|---|---|---|---|
| Research Pipeline | Unchanged | ⭐⭐ (Confusing notation) | Medium |
| Morale | Unchanged | ⭐⭐⭐ (Good feedback) | Low |
| Advisor | Pitch Session documented but hidden | ⭐⭐ (Traits still opaque) | High |
| Publication | Display improved slightly | ⭐⭐⭐ (Clear tracking) | Low |
| Network | Unchanged | ⭐⭐⭐ (Clear gains) | Low |
| Alignment | Still invisible | ⭐ (No meter) | High |
| Quals Exam | Documented but invisible | ⭐⭐ (Requirements clear, event hidden) | High |
| Emergency Options | Documented, buttons hidden | ⭐⭐ (Known but not accessible) | Medium |
| Help System | Significantly improved | ⭐⭐⭐⭐ (Comprehensive) | Low |
| Progress Dashboard | Still missing | ⭐ (No overview) | High |

---

*Analysis based on V2.15 gameplay exploration and comparison with previous version*
