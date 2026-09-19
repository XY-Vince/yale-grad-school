# Phase 4 召回漏斗诊断与通用修复实施计划

## 1. 当前基线与口径纠偏

- 当前检出分支为 `feat/v5-alpha-integration@b63a733`；`main` 仍停在 `319c72d`。当前状态应称为“集成分支完成”，尚未实际合并到 `main`。
- 2026-09-19 在干净工作树复跑 `python3 -m pytest . -q -p no:cacheprovider`，结果为 `142 passed`。
- Evaluator V2.3 的当前权威结果为：0 假合并、0 未匹配释放断言、释放 Precision 1.0、Micro Recall 3/17（17.65%）、Outcome Accuracy 5/10；综合门禁失败。
- `asset_manifest.json` 当前记录值与 6 个资产的实际 SHA-256 一致，但尚无程序化门禁重算该清单。
- Gold V2.1 当前 138 个 Mention 和 17 个 Claim Support 的字符切片均与 WARC 字节载荷解码文本一致；但现有 `verify_gold_warc_integrity()` 只检查 SHA 是否存在，未强制核验 URL、区间与 `verbatim_text`。
- `GoldClaim.supports` 仍允许空列表；与“每条 Claim 必须有证据”的文档契约不一致。
- 当前 `mention_recall=0.518` 将 3 个 Gold Mention 分母为 0 的弃答案例各计作 1.0。排除空分母后，7 个事实型案例的 occurrence-level 宏召回约为 31.1%。
- occurrence-level Mention Recall 不适合作为主要发布门槛：当前 14/14 个 Gold “实体×来源”均至少检测到一次，说明实体来源覆盖率已经是 100%；继续追逐页面内每次重复姓名会鼓励扩大窗口并引入噪声。

## 2. 已量化的六级漏斗基线

| 漏斗层 | 当前结果 | 结论 |
|---|---:|---|
| Gold 来源进入 Bundle | 7/7 事实型人物均为 100% | 检索不是当前主瓶颈 |
| 实体×来源至少命中一次 | 14/14（100%） | 所有目标与同名干扰实体均已被发现 |
| Target Gold Mention 被 Evidence 窗口覆盖 | 25/114（21.9%） | 页面定位窗口覆盖偏窄，但大量遗漏属于重复出现次数 |
| Evidence 内 Target Mention 抽取 | 24/25（96.0%） | Mention 抽取器在已定位文本内表现良好 |
| Gold Claim Support 被 Evidence 窗口覆盖 | 8/17（47.1%） | 结构化内容定位是 Claim 召回的重要瓶颈 |
| 全部 proposed Claims 的严格 5D TP | 5/17（29.4%） | Claim 解析仍漏掉已进入 Evidence 的事实 |
| 最终 released Claims 的严格 5D TP | 3/17（17.6%） | 候选假拆分与状态机进一步损失召回 |
| Outcome Accuracy | 5/10 | Sarah、Yao、Rohini、Yining、Albert 未达到预期状态 |

逐案例主瓶颈：

| Case | 主瓶颈 | 直接修复方向 |
|---|---|---|
| DEV-001 Xin Zhou | 学位已进入 Evidence 但未抽取；机构上下文未定位 | 教育模式与结构化 profile 上下文 |
| DEV-002 Sarah Luckart | 同一人物拆为 2 个 Candidate；职位对象被截短为 `Clerk` 且时态未知 | 同页 profile must-link；JSON-LD/jobTitle；完整职位短语 |
| DEV-003 Yao Sun | Assistant Professor 已进入 Evidence 但 0 Claim | profile 字段与部门/机构组合抽取 |
| DEV-004 Rohini Dutta | proposed 2/2 Gold Claim 已命中，但同一人物被拆分 | 只修 Candidate 合并，不动抽取规则 |
| DEV-006 Ray Liu | 已释放 2/3；IEEE President 证据未进入有效窗口 | 定向传记段落覆盖，不放宽释放门槛 |
| DEV-009 Yining Zhang | 目标 Candidate 已存在，栏目标题已进入 Evidence，但 0 Claim | “栏目标题 + 人物卡片”结构关系抽取 |
| DEV-010 Albert Zhao | 目标 Candidate 已存在，教育/履历区未进入 Evidence | target-centric DOM 卡片与时间线定位 |

## 3. Phase 4.0：先冻结 Evaluator V2.4

生产代码修改前先完成以下 Red Tests，并把 Evaluator 升级为 V2.4：

1. `GoldClaim.supports = Field(..., min_length=1)`；空证据 Claim 必须在 Schema 层失败。
2. WARC 重放必须逐项核验唯一记录、`WARC-Target-URI`、payload SHA、`char_start:char_end` 与 `verbatim_text`；任一 off-by-one、错误 URL 或错误文本均 Fail-Closed。
3. 新增 `verify_asset_manifest()`：重算文件大小与 SHA-256，要求必需资产集合完整；缺失、篡改或未声明资产均失败。
4. 将零 Gold Mention 的案例记为 `N/A`，不进入 occurrence-level Macro P/R/F1 分母。
5. 新增并设为主门禁：
   - `target_entity_case_recall_gate = 100%`；
   - `entity_source_recall_gate >= 95%`；
   - `zero_false_merges_gate`；
   - `false_splits <= 0`（开发集）或预注册上限（盲测集）。
6. 将 occurrence-level Mention Recall 和 common-universe B3 F1 降为诊断指标；报告必须注明它们不代表端到端实体覆盖。
7. 程序化输出六级漏斗的逐案例分子、分母、缺失 ID 和首个失败阶段。

Gold V2.2 在生产修复前冻结：

- 对 17 条 Claim 做语义支持复核，而不只做字符闭包复核。
- 普通文本支持必须包含主体/可验证别名、关系线索和宾语/等价项。
- 结构化页面允许多片段支持，但必须显式标注 `subject_anchor`、`relation_or_role_anchor`、`object_or_context_anchor` 与共同 DOM 容器。
- 优先复核 Yining 的栏目标题/页脚、Albert 的过期 `currently ... Class of 2025`、NJIT logo、Cornell logo等弱支持；不得依据系统当前输出增删 Gold。
- 冻结后生成 `gold_v2_2.json` 和新资产清单；后续生产实验只读使用。

## 4. Phase 4.1：修复 Candidate 假拆分

仅实现通用、可解释的同页 profile 合并：

- 充分条件：同一 SourceSnapshot、同一 canonical URL/JSON-LD `Person.@id`/目标绑定 profile 容器、规范全名精确一致、且无 Cannot-Link 或页面内同名竞争主体。
- 禁止条件：跨来源仅凭同名合并；仅凭同领域、同机构或姓氏尊称合并。
- Red Tests 必须覆盖 Sarah、Rohini 正例，以及同页两个同名人物、目录页、会议页三个硬负例。
- 独立消融只改 Resolver，目标：DEV-002/004 `false_splits` 从 2 降至 0，0 假合并保持，其他案例候选簇哈希不变。

## 5. Phase 4.2：结构化 Evidence 与 Claim 抽取

按收益顺序实现，不再扩充人物专属词典：

1. JSON-LD `Person`：读取 `name`, `jobTitle`, `affiliation`, `alumniOf`，每个 Claim 保留原始 JSON 字符区间。
2. Profile header：绑定 `h1/name` 与同一容器内 title/role/department；禁止从全站 logo 或 footer 单独推导人物 affiliation。
3. Section membership：建立“栏目标题 + 同一列表/卡片内姓名”的结构关系，覆盖 Yining；跨卡片不得传播。
4. Education/timeline card：绑定卡片标题、时间和院校，覆盖 Albert 与 Xin Zhou；处理 stale `current` 与显式年份冲突时输出 `unknown`/`former`，不得盲从页面中的 `currently`。
5. Biography paragraph：增加目标名/姓氏照应后的局部段落窗口，覆盖 Ray Liu IEEE President；继续执行竞争主体与句界门禁。
6. 完整职位短语：保留 `Clerk of the Corporation`、`Business Systems Analyst 2` 等修饰成分，规范化只进入 equivalence，不修改原始对象。

每一类适配器必须有正例、最小对照、跨卡片串扰、同名竞争和错误时态测试。禁止通过降低 5D 匹配、Claim Precision 或状态机阈值获得分数。

## 6. Phase 4.3：实验矩阵与进入标准

固定 Gold V2.2、WARC、Query Index 与 Evaluator V2.4，依次运行：

1. `A0`: `b63a733` 原基线。
2. `A1`: 仅 Candidate 假拆分修复。
3. `A2`: `A1 +` 结构化 Locator。
4. `A3`: `A2 +` 结构化 Claim Extractor。
5. 每组使用相同上游资产，输出规范化输入哈希；任何输入漂移使消融无效。

开发集完成标准：

- 0 假合并、0 未匹配 released Claim、Release Precision >= 0.95。
- Entity-source Recall >= 0.95，Target entity case recall = 1.0。
- False Splits = 0。
- Strict 5D Claim Recall >= 0.80，即至少 14/17 Gold Claims 命中。
- Outcome Accuracy >= 0.90，即至少 9/10 用例正确。
- 三个稀疏负例继续 3/3 安全弃答。
- 全量测试、宿主回归、资产清单、Git clean 与程序化报告全部通过。

## 7. 合流与 Blind V2 决策

- `feat/v5-alpha-integration` 尚未进入 `main`。在 Phase 4.0 的评测契约修复完成前，不执行 main 合并。
- Phase 4.0 通过后，可先将 benchmark/evaluator 修复作为独立提交合入；TargetPrior 继续默认关闭。
- Phase 4.1 至 4.3 达成开发集门槛后，才冻结候选代码和所有哈希，预注册 `blind_release_v2`。
- `blind_release_v2` 必须使用未进入 DEV-001~010、未参与规则设计的新人物；Curator 与实现者分离，运行前只公布种子承诺哈希，运行后一次性揭盲。
- Blind V2 失败后只能进入下一开发版本，不得在同一盲测集上修补后重复宣称通过。

## 8. 明确禁止事项

- 不降低 5D、Precision、Recall 或 Outcome 门槛来制造通过。
- 不为 Sarah、Yao、Rohini、Yining、Albert 添加姓名级硬编码。
- 不把 occurrence-level 重复姓名抓取量当作人物发现能力。
- 不把开发集结果称为盲测或发布结果。
- 不在 Gold V2.2 冻结后根据系统输出调整 Gold。
