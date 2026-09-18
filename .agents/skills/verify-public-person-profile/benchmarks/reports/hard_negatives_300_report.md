# 300+ 独立实体难负例基准评测报告 (Hard Negatives >= 300 Benchmark)

- **有效独立实体组数 (Entity-Disjoint Groups)**: 320 组
- **总测评提及数 (Total Mentions)**: 960 条
- **派生相关负例对数 (Derived Negative Pairs)**: 640 条 (派生自 320 个互斥试验群组)
- **假合并数 (False Merges)**: 0 (必须为 0)
- **B³ F1 聚类分数**: 1.0000 (点估计，95% CI: [1.0, 1.0])
- **正例 Pairwise Recall**: 100.0% (点估计，95% CI: [100.0%, 100.0%])
- **Pairwise Precision**: 100.0% (95% CI: [100.0%, 100.0%])
- **单侧 Clopper-Pearson 95% 精确置信上限**: 0.932% (必须 ≤ 1.000%)
- **Group Bootstrap 重抽样次数**: 1000 次 (按 Entity-Disjoint Group 整体重抽样)

## 硬性门槛判定
- 零假合并门槛 (Zero False Merges): ✅ 通过
- 正例 B³ F1 门槛 (≥0.90): ✅ 通过
- 正例召回率门槛 (≥90%): ✅ 通过
- 三法则置信上限门槛 (≤1.0%): ✅ 通过
- Bootstrap B³ F1 下界门槛 (≥0.90): ✅ 通过
- Bootstrap Pairwise Precision 下界门槛 (≥0.99): ✅ 通过
- **综合判定**: 🏆 全部通过 (PASSED)