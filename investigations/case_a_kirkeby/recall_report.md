# Maja H. Kirkeby 人物档案

调查日期：2026-10-12。执行者：fresh executor（Case A，技能迁移测试）。本案是
verify-public-person-profile 技能的迁移试用：目标由测试方指定，未附带种子链接或机构线索；
全部证据来自本轮直接抓取的 13 份原始来源。检索痕迹见 [query_logs.jsonl](query_logs.jsonl)
（30 条，含 12 条失败/受限查询）。

报告中的标识可点入 [evidence_index.md](evidence_index.md) 查看原文、定位与本地载荷。
每项都标明来源性质；本人自述与机构独立记录分别呈现。

**关于 verbatim 的格式说明。** 本案的 `verbatim_excerpt` 是对被保存文件内容的
**原值引用**：HTML 条目取标签剥离后的文本节点串接，JSON 取响应中的原样键值字符串
（Crossref 列表响应为紧凑 `"key":"value"` 形式，ORCID 为带空格缩进的
`"key" : "value"` 形式，两种都以被保存文件的真实字节为准）。这些引文不是"原始字节区间"，
也不假装是。凡是来源同一文件存在单条与列表两种保存形态的（Crossref），已同时保留两种，
claim 指向列表形态那份。

## A. 目标人物：CAND-01 — Maja Hanne Kirkeby（Roskilde University）

### 身份结论

Maja Hanne Kirkeby 的 Roskilde University 研究门户个人页确立了她的机构归属。
[VCLM-02](evidence_index.md#vclm-02)

ORCID `0000-0003-0033-2438` 的记录为 claimed 且邮箱已验证。
[VCLM-09](evidence_index.md#vclm-09)

OpenAlex 索引对该作者实体记录 39 项成果、81 次被引、h-index 5。
[VCLM-25](evidence_index.md#vclm-25)

Roskilde University 研究门户 profile 由 ORCID 链接，且由 RUC 客户端存入。
[VCLM-27](evidence_index.md#vclm-27)

Maja Kirkeby 与 Maja Hanne Kirkeby 两个姓名形式同属一个作者实体。
[VCLM-08](evidence_index.md#vclm-08)

### 强度读法

| 档位 | 本案使用方式 |
|---|---|
| S1 已确认发生 | 原文明确陈述：机构门户条目、出版方元数据、被领取的注册表记录。 |
| S2 公开意向 | 本案未产生 S2：没有找到"将做/期待"类原文。 |
| S3 研究环境关联 | 本案未产生 S3：没有致谢型或引用型关联需要弱化处理。 |
| S4 传闻线索 | 职衔先后顺序、博士前教育、防守日期等未闭合项，全部进线索账本。 |

[VCLM-01](evidence_index.md#vclm-01) 属机构记录（Associate Professor）。
[VCLM-11](evidence_index.md#vclm-11) 属出版方元数据（Formal Aspects of Computing）。
[VCLM-05](evidence_index.md#vclm-05) 属本人自述（ORCID employment）。

### S1：任职与研究单位（机构记录）

门户个人页列出 Associate Professor、Department of People and Technology 与
Programming, Logic and Intelligent Systems；同一页眉还保留 Assistant Professor 字符串。
[VCLM-01](evidence_index.md#vclm-01)

研究方向自述：energy consumption of software、analysis of software、program
transformation；关键词含 Program Inversion、Energy-aware Software Development、
Program Analysis。[VCLM-24](evidence_index.md#vclm-24)

Crossref 对 2017 年论文记录的作者单位是 Research group PLIS: Programming, Logic and
Intelligent Systems, Department of People and Technology, Roskilde University。
[VCLM-03](evidence_index.md#vclm-03)
该单位是 2017 年发表时的单位，与当前单位分开读。

### S1：教育（机构记录 + 注册表自述）

门户出版物记录：**PhD 论文《Probabilistic program analysis》**，Roskilde Universitet，
2018 年，139 页，系列 `Roskilde Universitet. Computer Science. Computer Science
Research Report`，类型标注为丹麦语 `Ph.d.-afhandling`（博士论文）。
[VCLM-04](evidence_index.md#vclm-04) [VCLM-28](evidence_index.md#vclm-28)
OpenAlex 记录 Probabilistic program analysis 的唯一作者署名单位为 Roskilde University。
[VCLM-10](evidence_index.md#vclm-10)

ORCID（自述，非人事记录）登记 2012-12 至 2015-12 在 Roskilde University
**PhD Fellow / VIP**，单位为 Department of Communication, Business and Information
Technologies；另有一条 2012-12 起、无结束日期的 `Associate Professor` 条目和一条
`Programming, Logic and Intelligent Systems` 条目。博士前学历、本科/硕士院校名称与年份
[VCLM-05](evidence_index.md#vclm-05) 的 PhD Fellow、
[VCLM-06](evidence_index.md#vclm-06) 的 Associate Professor 与
[VCLM-07](evidence_index.md#vclm-07) 的 PLIS 条目均为 ORCID 自述；
博士前学历没有来源支撑。[LEAD-02](evidence_index.md#lead-02)

**时间线（条目级聚合引用）**

| 时间 | 可支撑事件 | 来源与边界 |
|---|---|---|
| 2012-12 → 2015-12 | ORCID 自述 PhD Fellow / VIP（RUC） | 自述；与 2018 年博士完成的口径不明。[VCLM-05](evidence_index.md#vclm-05) |
| 2015 → 2016 | On proving confluence modulo equivalence for Constraint Handling Rules 等 CHR 汇合性早期发表 | Formal Aspects of Computing 出版方元数据。[VCLM-11](evidence_index.md#vclm-11) |
| 2017 | Formal Aspects of Computing 期刊论文，author affiliation 为 PLIS | Crossref author affiliation。[VCLM-03](evidence_index.md#vclm-03) |
| 2018 | 《Probabilistic program analysis》 | 机构记录。[VCLM-04](evidence_index.md#vclm-04) [VCLM-28](evidence_index.md#vclm-28) |
| 2019 | IJAR 论文（vol. 105, 217–228） | 出版方元数据。[VCLM-12](evidence_index.md#vclm-12) |
| 2024 | Compiling Haskell for Energy Efficiency: Empirical Analysis of Individual Transformations（SAC 2024） | authorships 索引。[VCLM-13](evidence_index.md#vclm-13) |
| 2026 | Framework Matters: Energy Efficiency of UI Automation Testing Frameworks（SAC 2026） | authorships 索引。[VCLM-14](evidence_index.md#vclm-14) |
| 2026 | Power Assumptions Matter（SANER-C 2026 companion） | authorships 索引。[VCLM-15](evidence_index.md#vclm-15) |
| 2026 | Bridging the gap between industry and academia（GREENS 2026） | authorships 索引。[VCLM-16](evidence_index.md#vclm-16) |
| 2024-06 | 期刊审稿人，ISSN 0167-6423（Elsevier 客户端存入） | 客户端存入。[VCLM-26](evidence_index.md#vclm-26) |

### S1：项目与活动（机构记录）

门户登记 7 个项目，页面可见 5 项。Green IT-procurement 项目她列为 project participant，
期间 2024-01-01 → 2028-07-07。[VCLM-18](evidence_index.md#vclm-18)
Energy and Performance Trade-offs in Hardware and Software Implementations 项目她列为
project manager，DIREC 资助，期间 2022-02 → 2023-01。[VCLM-19](evidence_index.md#vclm-19)
另三项为 Energy Analysis of Transformed Programs、Energicertificeret
softwareudvikling og drift、CERCIRAS COST Action CA19135。

CERCIRAS Training School 2022 她被列为 Organizer，期间 2022-09-19 → 24。
[VCLM-20](evidence_index.md#vclm-20)
31st International Symposium on Logic-based Program Synthesis and Transformation
她被列为 Member，日期 2021-09-07。[VCLM-21](evidence_index.md#vclm-21)
Energy-Labeling Web-based IT Systems 她被列为 Speaker，日期 2021-03-17。
[VCLM-22](evidence_index.md#vclm-22)
门户的 Member 活动类型不描述职责范围。
[VCLM-21](evidence_index.md#vclm-21)

### S1：媒体露面（机构记录）

门户登记 10 条媒体记录，主题集中在丹麦数据中心与 AI 用电。本案抓取一条：
Ingeniøren（全国级，网页，2024-11-01，作者 Bjørn Godske），"Persons" 字段列出
Maja Hanne Kirkeby。记录本身不等于引用核实——原文章未抓取，本案不断言她说过任何具体句子。
[VCLM-23](evidence_index.md#vclm-23)

### S1：出版物与引用足迹

OpenAlex 索引对该作者实体记录 39 项成果、81 次被引、h-index 5。
[VCLM-25](evidence_index.md#vclm-25)
门户页自报 30 项研究产出。两个计数不一致的原因可解释为索引含预印本与重复记录，
但本案不裁定哪个权威。

被引最高的单篇是 2016 年的 **ENTRA: Whole-systems energy transparency**
（21 次，索引口径）。本期抓取的近期代表性论文四篇：
[VCLM-13](evidence_index.md#vclm-13)–[VCLM-16](evidence_index.md#vclm-16)。
arXiv 预印本 **"Teaching Energy-Efficient Software — An Experience Report"**
（arXiv:2504.19707）把她列为四位作者之一，摘要自述覆盖三所大学的教学经验；
Teaching Energy-Efficient Software -- An Experience Report 她是四位合著者之一。
[VCLM-17](evidence_index.md#vclm-17)
arXiv 摘要没有说明她在 RUC 具体教什么课。

### S1：ORCID 与身份链接

ORCID 记录为 claimed、email verified；机构 profile URL 由 RUC 客户端存入。
注册表验证的是账户，不是其中的任职与成果内容。
[VCLM-09](evidence_index.md#vclm-09) [VCLM-27](evidence_index.md#vclm-27)

## B. 同名候选实体

本案没有发现第二个可辨识的 "Maja Kirkeby"：PubMed 零命中；OpenAlex 作者检索只返回
一个实体；通用搜索引擎对全名的查询只返回 "Maja" 一词的多语言噪声页。这是"未发现"，
不是"证明不存在"——DBLP 与 Google Scholar 两个检查都因反爬失败，Semantic Scholar 被限流，
所以同类候选的排查是不完整的。[OQ-03](evidence_index.md#oq-03)

| 检查 | 结果 | 处理 |
|---|---|---|
| PubMed | 0 命中 | S4：该姓名在生物医学域无记录。[OQ-03](evidence_index.md#oq-03) |
| OpenAlex 作者 | 1 个实体（39 works, 81 citations） | 目标即该实体。[VCLM-25](evidence_index.md#vclm-25) |
| Crossref 作者检索 | 只返回姓氏噪声（Per Kirkeby、Overgaard 等） | 未据此建候选。 |
| DBLP | Anubis 反爬，未取得数据 | 排查不完整。[LEAD-05](evidence_index.md#lead-05) |
| Google Scholar | CAPTCHA，未取得作者页 | 排查不完整。[LEAD-05](evidence_index.md#lead-05) |
| 通用搜索引擎 | 仅 "Maja" 词条/商品页噪声 | 未据此建候选。[OQ-03](evidence_index.md#oq-03) |

**没有为凑数制造同名候选。** 若后续检索发现第二个 Maja Kirkeby，按 CAND-02 起编号单列，
不与本案目标合并。

## C. 缺口、检索留痕与下一步

### 用户现在还不知道什么

1. **当前确切职衔与晋升时间**：门户同时显示 Assistant Professor 与 Associate
   Professor；ORCID 的 2012-12 起始日既等于博士早期条目起始日、又早于 2018 年博士完成，
   两条记录本身互相矛盾。[OQ-01](evidence_index.md#oq-01)
   [LEAD-01](evidence_index.md#lead-01)
2. **博士前教育**：ORCID education/qualifications 全空；没有本科/硕士院校来源。
   [OQ-02](evidence_index.md#oq-02) [LEAD-02](evidence_index.md#lead-02)
3. **博士论文细节**：导师、答辩日期、答辩委员会均未取得（PDF 被 Cloudflare 拦）。
   [LEAD-03](evidence_index.md#lead-03)
4. **教学职责**：只知道她参与写了一篇三校教学经验报告；在 RUC 具体课程与角色未知。
   [LEAD-04](evidence_index.md#lead-04)
5. **引用指标的第二来源**：Scholar CAPTCHA、S2 限流；OpenAlex 一家口径未被他源交叉。
   [LEAD-05](evidence_index.md#lead-05)
6. **两个未读项目**：门户计数 7、页面可见 5；`/projects/` 子路径 403。
   [LEAD-06](evidence_index.md#lead-06)
7. **同名候选**：排查不完整，见第二节。[OQ-03](evidence_index.md#oq-03)

### 已保存的来源如何使用

| 来源 | 用途 |
|---|---|
| SRC-01 | ORCID 记录：自述任职、姓名变体、审稿条目、机构链接。 |
| SRC-02 | RUC 门户主页：当前单位/职衔、项目、活动、媒体、产出计数。 |
| SRC-03 / SRC-04 / SRC-06 | OpenAlex 作者实体、作品清单、论文记录：聚合索引，用于足迹与作者顺序。 |
| SRC-05 | RUC 门户论文记录：博士论文学机构记录。 |
| SRC-07 / SRC-08 | Crossref 单条记录（FAC、IJAR）的原始抓取，作为 SRC-13 的原始形态保留。 |
| SRC-09 | arXiv 摘要：教学报告 preprint，作者自述。 |
| SRC-10 | RUC clipping 记录：媒体露面登记。 |
| SRC-11 / SRC-12 | 抓取失败页（403 / 指纹挑战）：证明查过，不作文证据。 |
| SRC-13 | Crossref 列表响应：VCLM-03/11/12 的 claim 来源。 |

### 下一轮最值得搜索的内容

1. **RUC 人员/系里页面与自发布 CV**：定职衔顺序、起始日期、本科/硕士学历。
2. **丹麦皇家图书馆（KB）书目与论文 front matter**：补导师、答辩日期；绕过 Cloudflare。
3. **RUC 课程目录**：把"三校教学经验报告"落到具体课程与角色（[OQ-04](evidence_index.md#oq-04) 的相关项目页）。
4. **DBLP / Google Scholar 浏览器会话**：完成同名排查与第二引用口径。
5. **2026 年国际合著论文 PDF**：核对作者块是否有第二署名单位
   （[OQ-05](evidence_index.md#oq-05)）。
6. **Green IT-procurement 项目页**：资金来源、预算、她的任务边界
   （[OQ-04](evidence_index.md#oq-04)）。

### 账本说明

本案账本含 28 条记录，全部 S1；其中 7 条来自 ORCID（自述或客户端存入），
已在 `subject_raw` 用该来源自己的姓名形式（`Maja Kirkeby`），并在 scope_note 注明。
另有 6 条线索与 5 个开放问题。没有产生 S2/S3/S4 断言：不是因为本案"更强"，
而是因为这个目标没有需要降档处理的意向型或致谢型原文——强度分档是按证据判的，
不是按目标分的。

撤销的断言编号不回收；本案没有撤出任何记录。门户条目中的姓名形式为
`Kirkeby, M. H.`（该页面人物链接的原样标签），已如实保留在 `subject_raw`，
没有改写成 `Maja H. Kirkeby` 冒充原文。

**机械自检的一处已知边界。** 案卷审计器（`verify_investigation_bundle.py`）的
JSON 原子单元查找只覆盖 Crossref 列表、OpenAlex `results` 与 FINRA `hits` 三种形态，
**没有 ORCID 分支**。因此 7 条 ORCID 来源断言无法通过它的主体接地检查；
这些引文都在保存的 ORCID 记录里逐字节可回放，断言本身有据。这是工具覆盖缺口，
不是断言无据——已在该 7 条的 scope_note 中注明。
