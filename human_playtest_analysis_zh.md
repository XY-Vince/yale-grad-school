# GradQuest 人类玩家模拟测试分析

生成时间：2026-07-27 23:40

## 本轮改动

本轮针对上一轮 50 局模拟暴露的问题做了小范围 gameplay/UX 修复：

- Hybrid 毕业路线：明确显示 `2 journal + 2 conference`，不再暗示 `2 conference = 1 journal` 可以无限替代 journal。
- 新增 `Expand Conf → Journal`：会议论文足够但 journal 不足时，可把会议成果扩展成 journal review，仍走现有 peer-review 管线。
- Quals onboarding：修正 September Year 2 倒计时计算，并在 12 个月窗口内置顶 Study for Quals。
- Critical Path 排序：把“下一步具体研究动作”排在继续读论文前；portfolio 达标后优先写 thesis；defense ready 后优先 prepare/defend。
- Defense strain：低士气、高压力、长期低士气、exhaustion/burnout 会提高 skepticism 并压低 defense 起始轨道。

## 最终 50 局结果

| 画像 | 胜率 | 平均月份 | 中位月份 | 平均 journal | 平均 conf | 平均最低士气 | 平均最高压力 | 主要结局 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| balanced | 100% | 61.4 | 61.5 | 3.0 | 0.0 | 27.8 | 3.8 | 10 graduation |
| cautious | 100% | 73.1 | 76.0 | 3.0 | 0.0 | 41.3 | 3.0 | 10 graduation |
| aggressive | 100% | 60.6 | 61.5 | 3.0 | 0.0 | 13.4 | 28.1 | 10 graduation |
| conference_hybrid | 100% | 66.5 | 63.5 | 2.3 | 2.0 | 25.0 | 24.0 | 10 graduation |
| novice | 100% | 63.5 | 64.5 | 3.0 | 0.0 | 18.9 | 15.0 | 10 graduation |

总体：

- 总局数：50
- 胜率：100%
- timeout：0
- 中位毕业时间：64.5 个月
- 平均毕业时间：65.0 个月
- 平均 journal papers：2.86
- 平均 conference papers：0.40
- 平均最低士气：25.3
- 平均最高压力：14.8

## 前后对比

- `conference_hybrid`：从 3/10 毕业、7/10 timeout，提升到 10/10 毕业。平均时间从 195.8 月降到 66.5 月，平均会议论文从 11.2 降到 2.0，说明路线已经收束。
- `novice`：从 0/10 毕业、主要 quals failed，变成 10/10 毕业。中间测试曾暴露 15J/0% thesis、100% thesis 不答辩的问题，Critical Path 排序修复后已解决。
- `balanced/cautious/aggressive`：仍保持 10/10 毕业，主线节奏没有被破坏。

## 观察

1. 这轮修复显著提升了可理解性。失败不再来自“玩家没看懂隐藏合同”，而是所有画像都能按 UI 路标走到毕业。
2. Hybrid 路线现在不再是陷阱。`Expand Conf → Journal` 是关键桥梁，它没有直接赠送 journal，而是把会议成果接入 journal review。
3. Critical Path 现在非常强，甚至可能过强。50/50 全毕业说明 onboarding 很顺，但长期目标如果是 30-70% PhD 胜率，需要在后续平衡里恢复风险。
4. Aggressive 路线仍然 10/10 毕业，平均最低士气 13.4。Defense strain 已接入，但当前样本里还没有明显压低高手胜率。
5. Novice 有 3 局 defense action 为 6，说明 major revisions 已经能发生，但最终仍能恢复毕业。这是比直接失败更好的教学型 friction。

## 建议

1. 保留本轮 UI/route 修复。它们解决的是理解问题，不是单纯降难度。
2. 下一轮不要继续加强引导，应该转向 difficulty calibration：让 aggressive 和 novice 有少量 major revisions、MS-out 或 timeout 风险。
3. 给模拟测试增加验收区间，而不是只看通过/失败：例如 hybrid 胜率 >= 70%，novice 早期 quals failed <= 20%，总体胜率目标 70-90% 或按设计再定。
4. 继续记录 defense final score、major revision 次数、prepare defense 次数，这样才能判断 defense strain 是否真的有效。

## 生成文件

- 原始数据：`human_playtest_results.json`
- 自动摘要：`human_playtest_report.md`
- 本分析：`human_playtest_analysis_zh.md`
