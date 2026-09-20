# Phase 5 Blind Release V2 实施计划

## 1. 当前进入条件

- Phase 4.4 开发集 18/18 门禁已通过，生命周期决策为 `ready_for_blind_evaluation`。
- `DEV-001` 至 `DEV-010` 已用于规则设计，仅保留为回归资产。
- 当前禁止继续依据上述人物修改生产抽取、解析或状态机规则。

## 2. 已完成的协议基础设施

- `models/blind_protocol.py`：公开预注册、候选池、选择清单、排除名册、Curator 声明与隐藏资产清单的严格 Pydantic 契约。
- `benchmarks/tools/blind_v2_protocol.py`：带 nonce 的规范化承诺、确定性分层抽样、历史人物排除、Gold 对齐、隐藏资产哈希复核、候选提交复核及一次性消费凭证。
- `tests/test_blind_v2_protocol.py`：公开文件泄露、配额不一致、承诺篡改、选择清单替换、历史人物污染、资产篡改、Gold 非独立裁决及重复消费反例。
- Evaluator V2.4 已区分 `development` 与 `blind_release`，并按角色选择显式资产契约。

## 3. Curator 待执行工作

1. 汇总此前所有开发集、历史盲测集及人工调查人物，形成隐藏排除名册。
2. 建立至少 90 人、建议 120 人的新候选池，并按执行手册的六个互斥主分层标注。
3. 两名 Curator 独立构建 Gold，逐 Claim 绑定 WARC 字符切片；由第三方或独立裁决流程解决分歧。
4. 冻结 WARC、Query Index、Gold、Case Manifest 与捕获日志，生成隐藏资产清单。
5. 生成随机种子与独立 nonce，确定性抽取 30 人并发布仅含承诺值的公开预注册。

## 4. 实现团队待执行工作

1. 完成协议代码全量回归并冻结候选提交 SHA。
2. 从候选提交创建独立 worktree；不接触隐藏资产。
3. 由 Curator 在揭示时运行协议校验并消费唯一一次尝试。
4. 在相同隐藏语料上执行 G2/G3 两组共 60 次管线运行，逐 Bundle 封印。
5. 运行 Evaluator V2.4 `blind_release` 角色并程序化生成报告。

## 5. 停止条件

- 任一承诺、候选提交、Gold/WARC 切片、资产哈希或配对输入不一致：本次盲测无效，不计算模型指标。
- 任一主门禁失败：不得针对该 30 人修补后重跑；错误分类进入下一开发集，并重新创建 Blind V3。
- 全部门禁通过：仅进入独立发布复核，不自动形成发布结论。

## 6. 当前验证状态（2026-09-19）

- Blind 协议与 Evaluator 定向测试：29 passed。
- 技能全目录测试：195 passed。
- GradQuest 宿主浏览器回归：12 passed（沙箱内 Chrome 启动失败后，按项目规则在沙箱外复跑）。
- Python 语法检查、术语 Linter 与 `git diff --check`：通过。
- 当前阻塞项不是生产代码，而是独立 Curator 尚未交付隐藏候选池、双人独立标注 Gold、WARC 与公开承诺文件。
