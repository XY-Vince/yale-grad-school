# Evaluator V2.4 开发集门禁审计报告

**评测结论**: `PASSED`  
**评测角色**: `development` | **生命周期决策**: `ready_for_blind_evaluation`  
**评测器版本**: `v2.4.0` | **时间戳**: `78871c9` (`dirty=False`)  

## 1. 资产与溯源自检清单
- Git Commit SHA: `78871c9342de023b8ccad54e9e0745d5666016ae`
- Git 工作区状态: `CLEAN`
- Evaluator SHA-256: `4120a180d1e8417dddeb735fb4050f45e4275f54993718841252a2228a64c517`
- Gold File SHA-256: `438c16f254c9d3b3c4e348d15a3689b8308e95828c043079d64d82c9d052c1fd`
- WARC Payload SHA-256: `f67066a877a8f51877f941c78f1142c006154c4c7fd6fdd02389dee6e188671a`
- Query Index SHA-256: `d6c2cd1da2bdc53b2d444b6bf401868ad934c3431d85ba7520dd97e42c71843b`
- 资产清单程序化核验: `PASS`

## 2. 核心评测门禁状态 (Primary Evaluation Gates)
| 门禁项 | 规则与标准 | 实际观测值 | 状态 |
|---|---|---|:---:|
| `clean_git_tree_gate` | Git 工作区干净（无未提交修改） | dirty=False | PASS |
| `provenance_complete_gate` | 关键输入哈希全量记录 | prov_complete=True | PASS |
| `asset_manifest_gate` | 评测资产清单重算 100% 一致 | asset_manifest=True | PASS |
| `seal_integrity_gate` | Merkle 密封签名全量校验通过 | seal_intact=True | PASS |
| `structural_validation_gate` | Schema 结构校验通过率 100% | val_rate=1.0 | PASS |
| `case_completeness_gate` | 期望案例全量完成评估 | actual=10/10 | PASS |
| `paired_input_identity_gate` | 对照实验上游输入哈希完全一致 | matched=True | PASS |
| `target_entity_case_recall_gate` | 事实型案例目标实体发现率 100% | rec=1.0 | PASS |
| `entity_source_recall_gate` | 实体×来源对发现率 $\ge 95.0\%$ | rec=1.0 | PASS |
| `zero_false_merges_gate` | 绝对不允许不同实体错误合并 | false_merges=0 | PASS |
| `false_splits_gate` | 同一实体假拆分 $\le 0$ | false_splits=0 | PASS |
| `zero_unmatched_released_claims_gate` | 释放断言必须 100% 具备真值支撑 | unmatched=0 | PASS |
| `ambiguity_safety_gate` | 稀疏/歧义负例必须 100% 安全弃答 | abs_acc=1.0 | PASS |
| `claim_precision_gate` | 释放断言 Macro Precision $\ge 95.0\%$ | macro_prec=1.0 | PASS |
| `claim_recall_gate` | 释放断言 Macro Recall $\ge 80.0\%$ | macro_rec=0.8095 | PASS |
| `subject_attribution_gate` | 主体归属准确率 $\ge 95.0\%$ | subj_acc=1.0 | PASS |
| `outcome_accuracy_gate` | 运行状态匹配率 $\ge 90.0\%$ | acc=1.0 | PASS |
| `completed_released_claims_gate` | 完成用例每个必须满足 TP_5D $\ge 1$ | passed=True | PASS |

## 3. 六级召回漏斗分析 (Six-Level Recall Funnel)
| 漏斗阶段 | 覆盖分子/分母 | 转化率 | 阶段诊断 |
|---|:---:|:---:|---|
| Level 1: Gold 来源进入 Bundle | 14/14 | 100.0% | 页面检索与抓取覆盖 |
| Level 2: 实体×来源至少命中一次 | 14/14 | 100.0% | 目标与同名干扰实体粗召回 |
| Level 3: Target Gold Mention 进入 Evidence | 28/114 | 24.6% | 页面上下文窗口定位覆盖 |
| Level 4: Evidence 内 Target Mention 抽取 | 25/28 | 89.3% | 定位文本内的 Mention 抽取 |
| Level 5: Gold Claim Support 进入 Evidence | 13/17 | 76.5% | 结构化事实证据窗口定位 |
| Level 6a: 全部 Proposed Claims 5D TP | 14/17 | 82.3% | 候选事实产生率 |
| Level 6b: 最终 Released Claims 5D TP | 14/17 | 82.3% | 最终发布事实真值命中率 |

## 4. 诊断性指标 (Diagnostic Indicators - Not Release Blockers)
> **说明**: 以下指标按出现频次或局部实体簇统计，不代表端到端实体召回能力，已降级为仅供工程诊断参考。
- Occurrence-level Mention Precision: `0.9388`
- Occurrence-level Mention Recall (非空分母宏平均): `0.3244`
- Occurrence-level Mention F1: `0.4822`
- Common Universe $B^3$ F1: `1.0`
- Common Universe Pairwise F1: `1.0`

## 5. 逐案例详细审计与首个失败阶段 (Case-Level Funnel Breakdown)
| Case ID | 目标人物 | 实际状态 | 期望状态 | 匹配 | TP_5D (Rel/Prop/Gold) | Unmatched | F-Split | 首个失败阶段 |
|---|---|---|---|:---:|:---:|:---:|:---:|---|
| `DEV-001` | Xin Zhou | `completed` | `completed` | ✓ | 2/2/3 | 0 | 0 | `l5_claim_support_window_miss` |
| `DEV-002` | Sarah Luckart | `completed` | `completed` | ✓ | 3/3/3 | 0 | 0 | `all_stages_passed` |
| `DEV-003` | Yao Sun | `completed` | `completed` | ✓ | 1/1/2 | 0 | 0 | `l5_claim_support_window_miss` |
| `DEV-004` | Rohini Dutta | `completed` | `completed` | ✓ | 2/2/2 | 0 | 0 | `all_stages_passed` |
| `DEV-005` | 段世泽 | `insufficient_evidence` | `insufficient_evidence` | ✓ | 0/0/0 | 0 | 0 | `none_abstention_passed` |
| `DEV-006` | Ray Liu | `completed` | `completed` | ✓ | 3/3/3 | 0 | 0 | `l5_claim_support_window_miss` |
| `DEV-007` | Logan Chen | `insufficient_evidence` | `insufficient_evidence` | ✓ | 0/0/0 | 0 | 0 | `none_abstention_passed` |
| `DEV-008` | Adeline Miao | `insufficient_evidence` | `insufficient_evidence` | ✓ | 0/0/0 | 0 | 0 | `none_abstention_passed` |
| `DEV-009` | Yining Zhang | `completed` | `completed` | ✓ | 1/1/2 | 0 | 0 | `l5_claim_support_window_miss` |
| `DEV-010` | Albert Zhao | `completed` | `completed` | ✓ | 2/2/2 | 0 | 0 | `all_stages_passed` |

## 6. 结论与下一步指引
开发集门禁已通过；该结果仅支持冻结候选并进入全新预注册盲测，不构成发布结论。
