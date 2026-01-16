# GradQuest Playtest Report

**Date**: January 5, 2026  
**Runs**: 10  
**Strategy**: Aggressive Hybrid (Quals in Year 1, Research when Morale >40%)

---

## Raw Data (N=10)

> **Note**: "Papers" column shows **total count** (journal + conference). Graduation requires **3 journal-equivalent** papers, where 2 conference = 1 journal. This simulation did not track the breakdown, so some "2 paper" runs may have had insufficient journal-equivalent.

| Run | Won | Duration | Papers (Total) | Quals Month | 1st Paper Month | Alignment | Network |
|:---:|:---:|:--------:|:------:|:-----------:|:---------------:|:---------:|:-------:|
| 1 | ❌ | 180 mo | 2 | 12 | 76 | 8 | 32 |
| 2 | ✅ | 99 mo | 3 | 12 | 30 | 12 | 38 |
| 3 | ✅ | 65 mo | 3 | 12 | 31 | 6 | 10 |
| 4 | ✅ | 161 mo | 3 | 12 | 70 | 14 | 37 |
| 5 | ❌ | 180 mo | 2 | 12 | 51 | 10 | 48 |
| 6 | ✅ | 144 mo | 3 | 12 | 50 | 6 | 21 |
| 7 | ❌ | 180 mo | 1 | 12 | 46 | 8 | 29 |
| 8 | ✅ | 114 mo | 3 | 12 | 66 | 14 | 30 |
| 9 | ❌ | 180 mo | 2 | 12 | 38 | 4 | 16 |
| 10 | ❌ | 180 mo | 2 | 12 | 37 | 8 | 41 |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Win Rate | 50% (5/10) |
| Timeout Rate | 50% (5/10) |
| Quals Pass Rate | 100% (10/10) |
| Morale Deaths | 0% (0/10) |
| Quals Dismissals | 0% (0/10) |

### Time to Graduate (Winners Only)
- Fastest: 65 months (5.4 years) - Run 3
- Slowest: 161 months (13.4 years) - Run 4
- Average: 117 months (9.8 years)

### Time to First Paper
- Fastest: 30 months (Run 2)
- Slowest: 76 months (Run 1)
- Average: 50 months

### Papers at Timeout (Losers Only)
- Run 1: 2 papers
- Run 5: 2 papers
- Run 7: 1 paper
- Run 9: 2 papers
- Run 10: 2 papers

---

## Observations (Facts)

### 1. Quals Pass Rate = 100%
All 10 runs passed Quals by Month 12 (end of Year 1). The "Year 1 Quals Prep" strategy eliminates academic dismissal as a failure mode.

### 2. Morale Death Rate = 0%
No runs ended due to morale hitting zero. The 20% morale floor for rest actions prevents burnout.

### 3. Sole Failure Mode = Timeout
All 5 failures were due to the 180-month (15-year) cap. Players did not die; they simply ran out of time.

### 4. Paper Production is the Bottleneck
- Winners produced 3 papers each (required to defend)
- Losers produced 1-2 papers despite having the same 15 years
- Run 7 produced only 1 paper in 180 months

### 5. Time to First Paper Varies Widely
- Range: 30 to 76 months
- This variance is due to research RNG, not strategy
- Run 2 got first paper at Month 30 and won at Month 99
- Run 1 got first paper at Month 76 and timed out at Month 180

### 6. Alignment Correlates with Success
- Winners average alignment: 10.4
- Losers average alignment: 7.6
- Higher alignment may improve research success rates

### 7. Network Did Not Reach 50 Threshold
- Range: 10 to 48
- The "Study Group" buff (+1 Quals level at 50 Network) was never triggered
- Strategy did not prioritize Network building

---

## Suggestions for Game Improvement

### 1. Research Variance is Too High
**Fact**: Run 7 produced 1 paper in 15 years. Run 3 produced 3 papers in 5.4 years.  
**Problem**: Same strategy, wildly different outcomes.  
**Suggestion**: Implement diminishing failure chance after repeated research attempts.

### 2. 2-Paper Trap
**Fact**: 4 of 5 losers ended with exactly 2 papers.  
**Problem**: Players can be 1 paper away from winning for years.  
**Suggestion**: Add feedback showing "Papers until defense: X" to help players understand their progress.

### 3. Alignment Impact is Invisible
**Fact**: Winners had higher alignment (10.4 vs 7.6).  
**Problem**: Players cannot see this correlation in-game.  
**Suggestion**: Display alignment and its effects in the UI.

### 4. Year 1 Research Would Help
**Fact**: All runs prioritized Quals in Year 1 and passed by Month 12.  
**Fact**: First paper came at Month 30-76 (after Quals).  
**Fact**: Run 7 produced only 1 paper in 180 months due to bad RNG.  
**Conclusion**: Starting research in Year 1 would give more time to overcome bad RNG and reduce timeout rate.

---

## Key Insight

**Year 1 Research is beneficial** because:
1. Research pipeline has high variance (30-76 months to first paper)
2. Bad RNG can produce only 1 paper in 15 years
3. Starting earlier = more attempts = better chance to graduate before timeout
4. Quals can still be passed by prepping in Year 2 (exam is in Year 2 September)

The current strategy (Quals-only in Year 1) wastes 12 months that could be used to start the research pipeline.

---

## Strategy Used

```
Priority Order:
1. Rest if Morale < 20%
2. Defend Thesis if available
3. Year 1: Prep Quals until Level 3, then Read
4. Year 2: Finish Quals if needed
5. Submit/Write Paper if available
6. Research (Figures/Findings/Ideas) if Morale > 40%
7. Break otherwise
```
