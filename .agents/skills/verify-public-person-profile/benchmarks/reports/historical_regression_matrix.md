# 历史工件登记与失败案例实跑回归矩阵 (Round 2)

本报告记录对历史失败类型代表案例的端到端统一实跑与审计重分类结果。所有案例均使用通用 `run_recall_profile.py` 独立生成，并经 `verify_investigation_bundle.py` 自动化机械校验通过。

---

## 一、 核心失败类型实跑与审计分类表

| 失败类型 | 代表案例 | 输入线索 | 输出目录 | 审计状态 | 最终定性与处理模式 |
|---|---|---|---|---|---|
| **同名异人混淆 (Homonym Disambiguation)** | `Xin Zhou` | `Biostatistics`, `University of Michigan` | `runs/regression_xin_zhou` | **PASS** | `reproducible_real_investigation`：成功并列 UMich 生物统计系副教授与计算机系学者，消歧理由明确记录于 Candidate Matrix，杜绝交叉污染。 |
| **稀疏足迹 / 规范弃答 (Sparse Footprint / Abstention)** | `Liam` | `independent researcher` | `runs/regression_liam` | **PASS** | `reproducible_real_investigation`：面对弱线索执行规范弃答；输出 4 组检索日志、候选探索矩阵及结构化 `AbstentionRecord`，严禁伪造任何经历。 |
| **中英别名 / 跨语言 (Bilingual / Transliteration)** | `李嘉文 (Jiawen Li)` | `sociology`, `survey methodology` | `runs/regression_jiawen_li` | **PASS** | `reproducible_real_investigation`：成功对齐汉字姓名与拼音，识别其在社会学及调查方法学领域的真实学术档案。 |
| **模糊机构与学历线索 (Ambiguous Affiliations)** | `Ray Liu` | `student at Johns Hopkins` | `runs/regression_ray_liu` | **PASS** | `reproducible_real_investigation`：在极高频同名背景下，以约翰霍普金斯大学学生身份精准建立候选集群，隔离商业/金融领域同名候选人。 |

---

## 二、 历史遗留工件分类规则 (Legacy Artifacts Classification)

| 历史工件 / 阶段 | 初始状态 | 分类标签 | 处置准则 |
|---|---|---|---|
| `5f0512f` 硬编码工件 | 内存硬编码人物事实伪造为来源 | `invalid_static_artifact` | 标记为历史反例，严禁作为生产或测试基线引用。 |
| `2fda9ea` 自造 WARC 套件 | 预写文本打进本地合成 WARC | `synthetic_fixture_only` | 仅保留用于内部格式兼容性测试，不作为真实证据来源。 |
| `5a516a6` 初版外部载荷 | 抓取真实载荷，但报告层存在外推与硬编码 | `partially_provenance_valid` | 来源层有效，综合报告层通过 Round 1 已按规程纠偏闭环。 |
| `investigations/yao_sun_rerun` | 纯净目录、参数化入口、机械证据回放 | `reproducible_real_investigation` | 正式黄金基线。 |

