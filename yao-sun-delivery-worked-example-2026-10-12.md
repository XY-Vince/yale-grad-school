# Yao Sun 档案交付：AG Worked Example

日期：2026-10-12。执行者：Codex。范围：用户更新计划的 Step 0 和 Step 1；独立 agent 做一次只读语义过目。本记录不宣称完成 Step 2/3、无人值守能力或发布级评测。

## 1. 已经交付的东西

用户入口是 [Yao Sun 人物档案](/Users/xiang-yu/Desktop/GradQuest/investigations/yao_sun/recall_report.md)。它回答：目标目前可对应到谁、有哪些公开教育与工作记录、研究与奖项涉及什么、哪些人只是同名候选、还不知道什么、下一轮搜索应从哪里开始。

报告中的 VCLM / LEAD / OQ 标识可点入 [证据索引](/Users/xiang-yu/Desktop/GradQuest/investigations/yao_sun/evidence_index.md)，再打开原始载荷。根目录 [recall_report.md](/Users/xiang-yu/Desktop/GradQuest/recall_report.md) 已改为入口，避免两个不同版本都被当作当前报告。

本次没有新增网络请求。25 份原始来源文件及 33 条查询记录沿用已有捕获；对照编辑前 Git HEAD，原始文件哈希、大小和查询日志字节均保持不变。这里的“保留来源”不代表每份来源都有效或独立。

## 2. 怎样做，而不是再造一个系统

1. 先读账本，再读支持该条判断的完整帖子、作者节点或教育字段。只看截取句或之前摘要不足以决定事实强度。
2. 在账本中修正主体、谓词、时态和证据强度；原始载荷不改，旧编号不重排，撤出的记录保留去向。
3. 将用户报告按目标人物、同名候选、线索与未知组织；事实性分句就近挂引用。
4. 列出最值得继续查的缺口，并说明哪些文件是噪声、authwall 或背景资料。
5. 刷新结构化文件与 manifest，做原文/引用核验；一次语义过目发现的实质错误直接修正，随后交付。

版式来自这个已经能读的例子。AG 改写 SKILL.md 时沿用这些决定，不必重新设计交付结构。

## 3. 五组必修问题如何落地

| 记录 | 原来的写法 | 本次交付写法 | 实际原因 |
|---|---|---|---|
| VCLM-16 | 已研究 environmental justice screening tool | 从事实账本撤出，转 LEAD-03，S4 | 原文只说寻找背景数据时发现工具被下架，不能推工具使用、研究专题或合作关系。 |
| VCLM-17 | participated_in，CURRENT | expressed_interest_in，S2；截至帖子日期的期待 | “Looking forward” 不证明参加已经发生。报告比计划中的“将参加”又收紧一步，只说公开期待。 |
| VCLM-18 | conducted_research，Detroit Street View Program | acknowledged_research_resource，S3 | 致谢维护图像的团队不等于在该团队受聘、主持项目或负责移动测绘。 |
| VCLM-19 | Derek 的事实混排在目标事实节 | subject 带 CAND-02 / FINRA；单独候选区 | 保留证券登记历史，不把它变成当前就业或推定 Ross 学历。 |
| VCLM-20/21 | subject 仅写 Yao Sun | subject 带 CAND-03 浙江医学作者 / CAND-04 UCSF；保留 subject_raw | 来源同名，身份不同。账本单独消费也应能识别归属。 |

这里保留“核实了什么”和“还没核实什么”两面。S2/S3 仍在现有 verified_claims.jsonl 文件中，但每条有 `evidence_strength`、收紧后的谓词、解释边界和时态。核实的是公开表达或资源关联，不是活动已发生。任何消费程序都不能把该文件所有行当成 S1。

S4 放在线索账本；缺乏来源的历史候选也保留，但不写成已确认的异人、博士、雇员或“没有 Yale 关联”。

## 4. 具体表示方式

### 同名主体

```json
{
  "claim_id": "VCLM-21",
  "subject": "Yao Sun (CAND-04, UCSF)",
  "subject_raw": "Yao Sun",
  "candidate_id": "CAND-04",
  "predicate": "holds_position",
  "object": "Professor, Pediatrics",
  "evidence_strength": "S1"
}
```

`subject` 是账本里可独立阅读的身份标签；`subject_raw` 是来源使用的名字，不能伪造一段包含 CAND 编号的“原文”。审计器用原名核对原子证据，同时检查限定标签中的姓名和候选 ID 相容；未带 `subject_raw` 的旧案卷继续用原字段核对。

### 引用与边界

报告写法：

> 2026-09-14，本人表达对 Yale Population Studies Workshop 首场报告的期待。没有据此断言实际出席。引用 VCLM-17，定位到本人帖子。

证据索引给出引文、JSON-LD 字段、发布日期和载荷路径。HTML 引文有时来自 JSON 解码，PDF 引文来自文本提取和空白归一化；不把这些误称为未经转换的字节区间。

### 词表与解释

| 档位 | 默认写法 |
|---|---|
| S1 已确认发生 | “机构名册列出……”或“本人自述已经……”；来源性质必须写清。 |
| S2 公开意向 | “公开表达期待 / 宣布将……”；不写“参与了”。 |
| S3 研究环境关联 | “致谢 / 提及 / 资源关联……”；职责与参与程度不明。 |
| S4 传闻线索 | “待核实线索 / 历史候选描述……”；保留供继续搜索。 |

## 5. 读完整原文后额外做出的改进

- 本科教育字段被遮蔽，奖学金和图标不能证明 B.S. in Sociology；该表述撤回到 LEAD-01。
- 原文存在一条名称被遮蔽的 2020-09 至 2021-05 教育记录。把“空档”改成“条目身份未知”，见 OQ-03；没有从遮蔽长度猜院校。
- 不把 2026-05-19 公告日期等同于 Yale 合同开始日期。
- 对 Michigan 的两个硕士名称按同一经历展示，不计作两项学历。
- 恢复已有材料中的三项有用信息：VCLM-23 个人档案教育日期、VCLM-24 本人 AAPOR 汇报自述、VCLM-25 研究方法经历自述。没有为提高条数制造事实。
- MAPOR 程序册支持“列名”；本人后续自述支持“汇报经历”。VCLM-15 同时保存两类支撑，各自的作用不同。
- 25 份来源按用途登记：6 份目标证据、2 份机构/主管背景、3 份替代候选证据、7 份噪声、1 份未关联账号、6 份 authwall。主管跨平台转载与本人多个帖子不是独立身份认证。

## 6. 一次独立语义过目

另一个 agent 在未参与编辑的会话中只读审查报告、账本和相关原文，仅检查四类实质问题：伪造来源、错误主体归属、未证推断当事实、来源政策违规。它没有代替外部独立人工，也没有新做网页调查。

发现一处残留：`dossier.json` 中 CAND-03 的机构字段仍带 `UMich Physiology`。PubMed 的 Yao Sun 作者节点只列浙江机构，Michigan 单位出现在其他作者节点。已移除此关联，保留该作者本人的完整浙江署名单位。报告本来已限定在浙江署名记录；修订同步到了 JSON。

没有因缺少全网穷举、模型独立性证明或更高测试计数而重新阻断这份日常档案。

## 7. 验证与实际范围

使用现有审计命令：

```bash
cd /Users/xiang-yu/Desktop/GradQuest
PYTHONPATH=.agents/skills/verify-public-person-profile \
python3 .agents/skills/verify-public-person-profile/scripts/verify_investigation_bundle.py \
  --bundle-dir investigations/yao_sun
```

最终结果记录在 [交付核验收据](/Users/xiang-yu/Desktop/GradQuest/yao-sun-delivery-verification-2026-10-12.json)：来源哈希与大小、manifest、24 条账本记录、7 条线索、5 个问题及引用闭包通过；补充引文从原始 JSON-LD 解码内容核对。报告中 47 个证据链接的锚点均存在。

审计器只做两项兼容修正：候选限定姓名使用 `subject_raw` 接地；事实词元核验不把 Markdown 链接目标路径当成事实正文。没有修改精度阈值或删去主体污染检查。针对候选标签和既有跨实体注入的两个定向测试通过；语法与补丁检查通过。测试中的 PyMuPDF 依赖弃用警告不是调查质量指标。

这些结果证明本案文件、引用和已读取材料的对应关系；不证明全网覆盖，不把自述变成机构认证，也不声称生产发现器因此具备无人值守能力。

## 8. AG 下一步怎么接

**Step 0/1 已完成；下一步直接做更新计划 Step 2，再做 Step 3。**

1. 把 SKILL.md 改成不超过 150 行的日常调查说明：目标与线索 → Agent 搜索精读 → 原文留存 → 候选消歧 → S1–S4 输出 → 可读档案；以本案作 worked example。
2. 默认路径写成 agent 辅助调查。旧确定性管线与发布基准保留在独立 legacy/内部章节，避免新执行者走错入口。
3. 做两个不同来源形态的真实迁移案例，至少一个不以学术出版 API 为主要来源；可把另一个设为低足迹难例。
4. 每个案例只回答：找到了什么、明显漏了什么、哪些判断靠 Agent 完成、用户能否利用。按已有来源政策工作，授权内工具与实施选择自主决定。
5. 只阻断四类实质错误，其余进 backlog。不要重做 Yao 档案，不要重新引入盲测封印、隔离证明或新的验收引擎。

保留的下一轮调查任务已经写进档案：公开 CV / Yale 人员页、AAPOR 2026 程序册、经消歧的 ORCID / Scholar、街景项目材料和遗留同名候选来源。它们是增加画像覆盖的工作队列，不是撤回本次交付的理由。
