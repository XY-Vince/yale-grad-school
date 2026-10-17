# SKILL.md 重写记录（Step 2，2026-10-12）

执行：AG。依据 delivery-plan-2026-10-12.md Step 2。

## 改动

旧 SKILL.md（60 行）指导执行者跑 `python3 -m core.run_profile`（确定性正则管线），
并附大段回归治理（Benchmark 2、gold 版本、V1 历史）——新执行者照做会进入已被
agent_synthesized 工作流取代的入口，且把发布评测当作日常必经路径。

新 SKILL.md（116 行）：

- description 改为触发导向（调查这个人/查背景/档案是真的吗），含拒绝触发条件；
- 正文六步默认流程：目标与线索 → 搜索精读 → 原文留存 → 候选消歧 → S1–S4 分层 → 输出档案；
- S1–S4 词表直接内嵌（不引用 worked example 才可读）；
- 引用 worked example 绝对路径（Yao Sun 交付）作样式与决策来源；
- legacy 附录：core.run_profile / benchmarks / 执行契约标明"非日常路径"；
- 机械自检命令改为 verify_investigation_bundle.py（当前案卷的真实校验器），
  删去已废弃的 validate_dossier.py / score_candidates.py 入口。

## 有意保留

- 来源政策与威胁模型的引用（原 Skills 的第 1、4 原则内联到流程中，两份 references 仍保留
  供深读）；
- no-auto-merge 原则扩展为可执行的账本表示（subject 带候选 ID + subject_raw）。

## 同步状态

harness 副本（ABCD/GradQuest-agent-eval-harness）未同步——按"工作区权威"状态保留分叉，
由用户决定何时/是否回灌（涉及评测仓治理，不属于本计划范围）。

## 待验证

Step 3 两个迁移案例是这份 SKILL.md 的第一批真实测试。摩擦点在各自案例的
TRANSFER_REPORT.md 第 5 节汇总。
