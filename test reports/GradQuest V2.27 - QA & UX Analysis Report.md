# GradQuest V2.27 - QA & UX Analysis Report

**Tester:** Manus (Lead Game QA & UX Analyst)  
**Date:** January 7, 2026  
**Game Version:** V2.27  
**URL:** [https://xy-vince.github.io/GradQuest/](https://xy-vince.github.io/GradQuest/)

---

## 1. Executive Summary
GradQuest V2.27 is a highly engaging, text-based resource management simulation that effectively captures the psychological and procedural hurdles of a PhD journey. The game balances research progression with mental health (Morale) and external pressures (Advisor, Quals). 

### Win/Loss Rate (Simulated Runs)
| Run Type | Strategy | Outcome | Key Factor |
| :--- | :--- | :--- | :--- |
| **Run 1 (Safe)** | Computational, High Morale Focus | **In Progress** | Steady progress, but slow. |
| **Run 2 (Risky)** | Experimentalist, Aggressive RNG | **In Progress** | High-Throughput success accelerated figures but tanked Morale. |
| **Run 3 (Edge Case)**| Theoretician, Resource Hoarding | **In Progress** | Testing auto-generation mechanics. |

*Note: Due to the long-term nature of the simulation (5-6 years), full completion requires significant time. Observations are based on the first 2-3 years of each run.*

---

## 2. Mechanic Analysis

### RNG & Balance
*   **Morale Penalty:** The RNG events (e.g., "You wonder if you really belong here") feel thematic but can be punishing when they chain together. The -3 to -5 Morale hits are significant in "Crisis Mode."
*   **High-Throughput Risk:** The 40% success rate for +2 figures is a well-balanced "gambler's" mechanic. It provides a meaningful shortcut at a high cost of exhaustion.
*   **Paper Review Times:** The 8-12 month wait for Journal papers is realistic and creates a necessary "dead zone" where the player must manage other tasks, preventing a simple click-to-win loop.

### Morale & Stress
*   **Crisis Mode:** The transition into Crisis Mode is a strong UX element, changing available actions (e.g., Medical Leave). However, the recovery can feel slightly too slow without "Take Time Off," which is advisor-dependent.

---

## 3. UX & UI Feedback

### Clarity of State
*   **Research Pipeline:** The "Ideas → Findings → Discovery → Figures" flow is clear. However, when a "High-Throughput Success" occurs, the UI says "+2 Figures ready," but the "Validate Discovery" button still shows "0/3" until clicked. This is a minor **UX friction point**—players might expect the count to update automatically.
*   **Quals Warning:** The "URGENT" and "CRITICAL" warnings for Quals are excellent. They effectively create a sense of panic that mirrors real academic deadlines.
*   **Advisor Status:** The emoji-based advisor status is intuitive.

### Pain Points
*   **Button Layout:** As the game progresses, the number of buttons increases significantly. On smaller viewports, this could lead to "button fatigue."
*   **Feedback Loop:** Some random events don't have a clear "Continue" button immediately visible if the "What Happened" log is long, requiring a scroll.

---

## 4. Bug Hunting & Technical Observations

### Potential Issues
*   **Soft Locks:** No hard soft-locks were found. However, if a player enters "Crisis Mode" with an unhappy advisor who refuses "Time Off," the player can get stuck in a loop of "Take a Break" (+2 morale) vs. random negative events (-3 morale), making progress nearly impossible.
*   **Text Rendering:** In the "Quals" window, some text overlaps slightly with the "Previously" log on certain screen widths.
*   **State Persistence:** The Save/Load functionality works correctly across sessions.

---

## 5. Suggestions for Improvement

1.  **Figure Collection UX:** When a "High-Throughput" or "Bonus" figure is generated, consider auto-incrementing the figure count or changing the button color to indicate "Collection" is needed.
2.  **Morale Tooltips:** Provide a small tooltip or hover effect on "Morale" to show the current numerical value or the threshold for "Crisis Mode."
3.  **Advisor Interaction:** Allow players to "Gift" or "Email" the advisor (using Network or Morale) to slightly improve relations, giving more agency over the "Take Time Off" unlock.
4.  **End-of-Year Summary:** A brief popup at the end of each academic year summarizing papers published and network gained would improve the sense of long-term achievement.

---

## 6. Final Verdict
**GradQuest V2.27 is a robust and polished simulation.** It successfully turns the "tedium" of research into a compelling management game. The balance is tight, and the UX is mostly intuitive, with only minor polish needed on the feedback of certain RNG successes.
