# Phase 5 Blind Release V2 实施记录

## 1. 准入与进入条件

- Phase 4.4 开发集 18/18 门禁已全部通过，生命周期决策为 `ready_for_blind_evaluation`。
- `DEV-001` 至 `DEV-010` 已用于规则设计，已正式冻结为历史回归资产。
- 生产抽取、解析与状态机规则已严格锁定，禁止继续依据开发集案例修改。

## 2. 已完成的协议与执行基础设施

- `models/blind_protocol.py`：实现了公开预注册、候选池、选择清单、排除名册、Curator 声明、隐藏资产清单，以及单用例 query 预算（`query_budget_per_case`）、macOS Seatbelt 隔离契约（`investigator_isolation_backend = "macos_seatbelt"`）与一次性执行标记（`one_shot_execution_required = True`）的严格 Pydantic 契约。
- `benchmarks/protocols/blind_release_v2/preregistration.schema.json`：已导出并与公开预注册契约保持严格一致。
- `benchmarks/tools/blind_v2_protocol.py`：实现了带 nonce 的规范化承诺、确定性分层抽样、连续 case ID (`BLIND2-001..030`) 校验、执行 query 全覆盖校验 (`validate_execution_assets`)、历史人物排除、Gold 对齐、隐藏资产哈希复核、候选提交复核及基于原子 `O_EXCL` 的一次性消费凭证。
- `benchmarks/tools/blind_v2_runner.py`：实现了一次性盲测执行器。支持 macOS Seatbelt 沙箱 profile 生成 (`build_seatbelt_profile`)、独立工作区隔离 staging (`stage_investigator_assets`，确保无 `gold.json` 或 `capture_manifest.jsonl`)、单用例 query 预算限制、原子运行凭证写入 (`write_result_receipt` 基于 `O_EXCL`)、Bundle 树哈希封印 (`write_bundle_seal`)。
- `benchmarks/tools/evaluator_v2_4.py`：已区分 `development` 与 `blind_release`，支持 `entries` 格式的 `case_manifest.json` 加载 (`load_expected_case_ids`)，并按角色执行显式资产契约。
- 自动化测试集：`tests/test_blind_v2_protocol.py`、`tests/test_evaluator_v2_4_adversarial.py` 与 `tests/test_blind_v2_runner.py`，覆盖了公开文件泄露、配额不一致、承诺篡改、选择清单替换、历史人物污染、资产篡改、Gold 非独立裁决、重复消费反例、沙箱隔离及原子执行阻断。

## 3. Curator 待执行工作（角色隔离）

1. 汇总此前所有开发集、历史盲测集及人工调查人物，形成隐藏排除名册。
2. 建立至少 90 人、建议 120 人的新候选池，并按执行手册的六个互斥主分层标注。
3. 两名 Curator 独立构建 Gold，逐 Claim 绑定 WARC 字符切片；由第三方或独立裁决流程解决分歧。
4. 冻结 WARC、Query Index、Gold、Case Manifest 与捕获日志，生成隐藏资产清单。
5. 生成随机种子与独立 nonce，确定性抽取 30 人并发布仅含承诺值的公开预注册。

## 4. 实现团队已完成工作与交付物

1. 协议模型、校验工具、一键执行器及反例测试集已全部完成并通过回归。
2. 工具链 SHA-256 哈希值与候选提交 SHA 已完成冻结。
3. 从候选提交检出干净独立环境，等待 Curator 交付隐藏盲测资产与公开预注册。
4. 交付后将由执行器一次性在相同隐藏语料上执行 G2/G3 两组共 60 次管线运行，逐 Bundle 封印，杜绝重试与泄露。
5. 最终通过 Evaluator V2.4 `blind_release` 角色生成评测报告。

## 5. 停止条件与门禁

- 任一承诺、候选提交、Gold/WARC 切片、资产哈希或配对输入不一致：本次盲测无效，不计算模型指标。
- 任一主门禁失败：不得针对该 30 人修补后重跑；错误分类进入下一开发集，并重新创建 Blind V3。
- 全部门禁通过：仅进入独立发布复核，不自动形成发布结论。

## 6. 当前验证状态与基线冻结（2026-09-29）

- 技能全目录测试：`201 passed in 24.01s`。
- Blind 协议与 Runner 定向测试：33 passed（含 protocol 12 项、evaluator adversarial 17 项、runner 4 项）。
- GradQuest 宿主浏览器回归：`12 passed`。
- Python 语法检查 (`python3 -m compileall -q`)、代码卫生 (`git diff --check`)：全部通过。
- 冻结工具链核心 SHA-256：
  - Evaluator V2.4: `053490e42fa57590a820cdf6bd14520d07e3efa73aea4c2e539262fb9add2ce4`
  - Gold Schema V2.2: `751025f4bb8e622641757c499cc56fe4f5b51fb5a0301e5b9d1accf90b70c57e`
  - Public Preregistration Schema: `fbc62232b815d58214d6429301d69d6d7c63de338d5a6f9222548be6fb330116`
  - Blind V2 Runner: `f195e74e4c23b3fe06371cf818e195f8c44a90f326eef23e28be3ddb030c8be6`
- 当前状态结论：工程实现、防泄露隔离沙箱与评测协议工具链已全部完成并冻结；当前阻塞项是独立 Curator 尚未交付隐藏候选池、双人独立标注 Gold、WARC 与公开承诺文件。
