# Benchmark 2: 快照与最小对照对断言抽取基准评测报告

- **评测用例总数**: 31 (涵盖真实网页、最小成对变换、纯对抗噪声)
- **联合 5D 全匹配 F1 (Joint 5D Oracle F1)**: 1.0000 (P: 1.0000, R: 1.0000)
- **宽松规则关系抽取 F1 (Relaxed Relation F1)**: 1.0000 (P: 1.0000, R: 1.0000)
- **极性识别准确率 (Polarity Accuracy)**: 100.0%
- **时态状态准确率 (Temporal Accuracy)**: 100.0%
- **主体归属准确率 (Subject Attribution)**: 100.0%
- **噪声误报率 (Noise False Positive Rate)**: 0.0%
- **噪声正确弃答率 (Abstention Accuracy)**: 100.0%
- **Gold 主体口径**: 每条 fixture 的 `target_name` 是主体真值；object 仅接受标准化精确值或显式 `equivalence_set`。

## 硬性门槛核验表
- 严格 5D 发布门槛（P/R/F1 与四项组件均通过）: ✅ 通过
- 联合 5D 精确率门槛 (≥95%): ✅ 通过
- 联合 5D 召回率门槛 (≥95%): ✅ 通过
- 联合 5D F1 门槛 (≥95%): ✅ 通过
- 主体归属识别门槛 (≥95%): ✅ 通过
- 极性识别门槛 (≥95%): ✅ 通过
- 时态识别门槛 (≥95%): ✅ 通过
- 纯噪声零误报门槛 (0%): ✅ 通过
- 关系精确率门槛 (≥95%): ✅ 通过
- 关系召回率门槛 (≥95%): ✅ 通过
- 关系抽取 F1 门槛 (≥95%): ✅ 通过

## 用例明细
| Fixture ID | Category | Gold Claims | Extracted Claims | Matched (Relaxed) | Matched (Joint 5D) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `real_01_faculty_yale` | real_web | 2 | 2 | 2 | 2 |
| `real_02_postdoc_medicine` | real_web | 3 | 3 | 3 | 3 |
| `pair_01a_affirmative` | minimal_contrast | 2 | 2 | 2 | 2 |
| `pair_01b_negated` | minimal_contrast | 1 | 1 | 1 | 1 |
| `pair_02a_former` | minimal_contrast | 2 | 2 | 2 | 2 |
| `pair_02b_current` | minimal_contrast | 2 | 2 | 2 | 2 |
| `pair_03a_chinese_current` | minimal_contrast | 2 | 2 | 2 | 2 |
| `pair_03b_chinese_former` | minimal_contrast | 2 | 2 | 2 | 2 |
| `pair_04a_subject_reversal` | minimal_contrast | 0 | 0 | 0 | 0 |
| `pair_04b_subject_dean` | minimal_contrast | 2 | 2 | 2 | 2 |
| `noise_01_weather` | noise | 0 | 0 | 0 | 0 |
| `noise_02_tos_navigation` | noise | 0 | 0 | 0 | 0 |
| `noise_03_economy_news` | noise | 0 | 0 | 0 | 0 |
| `distractor_01_other_person_sentence` | distractor | 0 | 0 | 0 | 0 |
| `distractor_02_quotation_frame` | distractor | 0 | 0 | 0 | 0 |
| `distractor_03_appositive_frame` | distractor | 0 | 0 | 0 | 0 |
| `variant_01_discipline_and_role` | linguistic_variant | 3 | 3 | 3 | 3 |
| `variant_02_conjoined_discipline` | linguistic_variant | 2 | 2 | 2 | 2 |
| `variant_03_three_conjoined_subjects` | linguistic_variant | 2 | 2 | 2 | 2 |
| `variant_04_director_of_center` | linguistic_variant | 3 | 3 | 3 | 3 |
| `variant_05_hyphen_accent_coordinated_subjects` | linguistic_variant | 2 | 2 | 2 | 2 |
| `variant_06_unentailed_action_negative` | linguistic_variant | 0 | 0 | 0 | 0 |
| `variant_07_chinese_short_alias_compound_negative` | linguistic_variant | 0 | 0 | 0 | 0 |
| `variant_08_chinese_short_alias_positive` | linguistic_variant | 3 | 3 | 3 | 3 |
| `variant_09_prefix_collision_negative` | distractor | 0 | 0 | 0 | 0 |
| `variant_10_gpe_anaphora_positive` | linguistic_variant | 1 | 1 | 1 | 1 |
| `variant_11_chinese_open_predicates_positive` | linguistic_variant | 2 | 2 | 2 | 2 |
| `variant_12_cross_cultural_pronoun_negative` | distractor | 0 | 0 | 0 | 0 |
| `variant_13_gpe_award_person_negative` | distractor | 0 | 0 | 0 | 0 |
| `variant_14_honorific_surname_negative` | distractor | 0 | 0 | 0 | 0 |
| `variant_15_chinese_maximal_span_negative` | distractor | 0 | 0 | 0 | 0 |