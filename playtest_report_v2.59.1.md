# GradQuest V2.59.1 Playtest Report

**Date:** Feb 9, 2026
**Runs:** 10 Automated "Competent Human" Simulations
**Result:** 0% Completion (100% Timeout at ~138 months)

## 🚨 Critical Findings

### 1. Progression Logic Trap ("The Conference Loop" & Inconsistency)
*   **Inconsistency Detected:** The user noted "2 conference counts as 1 journal", implying fungibility. However, the code (`GRADUATION_CONTRACT`) strictly enforces **Minimum 2 Journal Papers** (`journalPapers >= 3 || (journalPapers >= 2 && confPapers >= 2)`).
*   **The "Journal Gate":** Furthermore, the `Write Thesis` action is **hard-gated by `journalPapers >= 1`**. A player with 10 Conference Papers (equivalent to 5 Journals by the "2:1" rule) cannot write a single word of their thesis.
*   **Result:** Bots fell into a trap of publishing easier Conference papers (3mo) to meet the "3 papers" goal, but remained locked out of the Thesis and Defense forever because they failed to land a Journal paper (likely due to missing `Revise` logic in the bot).
*   **Recommendation:**
    *   **Logic Fix:** Align code with the "2 Conf = 1 Journal" rule. Change Graduation Contract to `(journal + conf/2) >= 3`.
    *   **Unlock:** Allow `Write Thesis` if `total_papers >= 1` (regardless of type).
    *   **UX:** Don't hide `Write Thesis`. Show it as disabled with tooltip if requirements aren't met.

### 2. Pacing is Too Slow
*   **Data:** Median duration **134.5 months** (11+ years) without graduation.
*   **Analysis:** Even with high paper output (e.g., Run 3: 7 papers), the "PhD" end state was not reached. Real PhDs average 60-75 months. The current tuning (Idea → Findings → Discovery → 3x Figures → Review) is too grinding.
*   **Recommendation:**
    *   Reduce "Make Figures" requirement from 3 to 2.
    *   Reduce Journal Review time (currently 8-12mo?) or increase acceptance rate.

### 3. Morale Economy: "Survivable Purgatory"
*   **Observation:** Average lowest morale was **22.4** (Critical). Exhaustion occurred **~3.5 times per run**.
*   **Success:** The "Death Spiral" was avoided. No runs ended in Dropout/Mental Health failure. The "Competent" logic (taking breaks when low) effectively keeps the player alive indefinitely.
*   **Issue:** The game allows "zombie mode" where a player survives forever without progressing (11+ years).
*   **Recommendation:** Implement a "Departmental Review" or "Funding Cap" that forces a Game Over (Master's Exit) if no graduation by Year 7/8, to prevent infinite stalling.

### 4. Quals Wall
*   **Status:** **PASSED**.
*   **Analysis:** All 10 runs survived past Month 21 (Quals). The new weighted random study logic and "Bad Luck Protection" appear to make Quals passable for a diligent player.

### 5. Defense Gauntlet
*   **Status:** **UNTESTED**.
*   **Reason:** No run reached the defense stage due to the "Conference Loop" progression blocker.

---

## 🛠️ Technical Fixes Applied
During this session, the `smart_playtest.py` suite was repaired:
1.  **Regex Update:** Fixed parsing of pipeline items (Icons changed `💡`→`📚`, format `(N)`→`×N`).
2.  **Action Logic:** Updated button text matching to support `Validate Discovery` (was `Make Figures`) and `Journal/Conference Paper` split.

## 📋 Summary of Runs
| Run | Outcome | Months | Papers | Lowest Morale | Note |
|-----|---------|--------|--------|---------------|------|
| 1 | Timeout | 132 | 4 | 22 | Stuck in paper loop |
| 3 | Timeout | 135 | 7 | 22 | High output, no thesis |
| 7 | Timeout | 133 | 8 | 24 | Extreme paper spam |
| ... | ... | ... | ... | ... | (All similar) |

## ✅ Action Items for V3.0
1.  [ ] **UI**: Surface `Write Thesis` requirements (don't hide button).
2.  [ ] **Balance**: Tune down research pipeline friction (Figures 3→2).
3.  [ ] **Logic**: Add "Time Limit" to force ending (Master's out at Year 7).
