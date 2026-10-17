# TRANSFER REPORT — Case B: Belinda Juan (迁移测试)

日期：2026-10-12。执行者：migration executor (Case B)。对象技能：
`/Users/xiang-yu/Desktop/GradQuest/.agents/skills/verify-public-person-profile/SKILL.md`
（六步流程 + S1–S4 + 不自动合并 + 四类阻断）。案卷：
`/Users/xiang-yu/Desktop/GradQuest/investigations/case_b_juan/`。
检索后端：本环境没有独立的 WebSearch 工具，全部检索经 WebFetch 与 curl；
18 条查询，其中 6 条被 bot 拦截或连接失败，全部留痕于 `query_logs.jsonl`。

---

## 1. What was found (by S-tier, with claim ids)

**总前提：这不是一个能锁定唯一目标的案子。** "Belinda Juan" 是常见全名，LinkedIn 目录索引
显示 "10+ profiles"（VCLM-10），本次未发现任何占主导的可核实主体。档案按候选分列输出，
没有制造目标。按 S 档：

**S1 — 已确认发生（8 条，集中在两个可读主体；均为自述类来源）**

CAND-01（Bliss Spa & Salon 店主，北安多弗 MA；来源：2018-10-12 Boston Voyager 第一人称访谈）：
- 拥有/经营 Bliss Spa & Salon；2008 年购入时名 "Paradise"（VCLM-01、VCLM-04，十周年佐证）
- 每周四天在店里做美发服务的现职描述，访谈时点的"owner"（VCLM-05）
- 就读 Whittier Regional Vocational High School 美容专业（2001 起）（VCLM-02）
- 就读 SNHU 攻读 business degree（VCLM-03）——注意：原文只说"attended…to pursue"，
  未说获学位，故只写到"就读"。

CAND-02（Belinda **Juang**，钢琴教师，圣迭戈 CA；来源：belindapianostudio.com 第一方自述）：
- 拥有 Belinda's Piano Studio 并任钢琴教师（VCLM-11）
- 从 University of Michigan 获钢琴表演 + 心理学双学士（VCLM-12）
- 2010 年起私人教授古典钢琴（VCLM-13）

两主体同名不同源，地理相隔全美，姓氏拼写有一格之差（Juang），按技能要求**未合并**。

**S2 — 公开意向（1 条）**

- CAND-01 在 2018 访谈中称"今年九月我们将推出 CBD oil massage"（VCLM-06）。
  只记录公开表达的计划；没有任何后续证据表明上线。按模板写成"公开表达计划/期待"而非
  "已推出"。

**S3 — 研究环境关联（0 条）**

本案没有任何致谢/资源关联级证据（非学术目标，无此形态来源出现）。

**S4 — 传闻/索引线索（4 条，全部是"原页面不可读、只有搜索索引摘要"的记录）**

- VCLM-07：LinkedIn 档案摘要（CAND-03，The Green Room Beauty Bar，Methuen MA，SNHU）；
  原页 HTTP 999
- VCLM-08：RocketReach 聚合档案摘要（CAND-04，"Teacher at Assurant"，圣迭戈 CA）；
  原页 HTTP 403 Cloudflare
- VCLM-09：MaxPreps 两份高中足球名录摘要（CAND-05，Fallbrook/West Valley CA）；
  两个 URL 抓取时 404；疑似未成年，只作防混淆
- VCLM-10：LinkedIn 目录"10+ profiles"摘要（CAND-06）；支持不合并，不构成履历

所有 S4 记录的 scope_note 都明确写了"snippet is index text, not a biography"和
"authwall is not biography"，与技能要求一致。未读取、未记录任何 PII
（RocketReach 页本身就是联系信息聚合器，403 挑战页一个字都没进引文）。

## 2. What was obviously missed

**这个人是低足迹目标，必须明说。** 没有找到新闻、奖项、公司登记、学术记录或任何
"Belinda Juan"的公众知名度证据。对精确姓名，本案耗尽并留痕的模式（query_logs.jsonl，18 条）：

1. Google/Bing 的引号短语 `"Belinda Juan"`——Bing 对引号支持弱（返回的全是歌手 Belinda
   Peregrín，与目标无关），Google 网页版返回 JS 重定向存根
2. Google News RSS 精确匹配——10 条无一命中（全是无关讣闻）
3. LinkedIn 直连（/in/belinda-juan-0640961b、/pub/dir/Belinda/Juan）——均 HTTP 999 authwall
4. RocketReach 直连——HTTP 403 挑战
5. 被拦截未能使用的后端：DuckDuckGo（HTML + Lite 均 CAPTCHA）、Mojeek（JS 挑战）、
   Yandex（SmartCaptcha）、Ecosia（403）、Yahoo（500）
6. 公司官网：thegreenroombeautybar.com、blissspaandsalon.com——连接失败（HTTP 000）
7. 语境变体：Philippines/Manila 语境零命中；teaching/teacher/faculty 语境只有聚合器命中

**应该存在但本次没查到的（下一轮队列，已写进 recall_report.md G 节）**：
- 换未被拦主源重跑基础查询（Brave 连续触发 429，只跑出 4 个成功 SERP）
- 马萨诸塞州企业登记（Bliss Spa 的注册现状、Green Room Beauty Bar 是否存在）
- 2018 之后 CAND-01 的现状（商家列表、Instagram @blissspaandsalon2008）
- belindapianostudio.com 全站交叉核对 Juan/Juang 拼写
**诚实边界**：所谓"低足迹"部分是检索后端被拦的产物——Brave 是唯一可用的短语搜索引擎，
所以"没找到"不能等同于"不存在"（OQ-06 记录了这一点）。

## 3. Which judgments required agent/human judgment

工具和机制建立不了、由本次执行者承担语义判断的：

1. **"哪个候选是可读证据最多的主体"**：机器只能返回 URL 列表；决定"2018 访谈比若干条
   索引摘要更可用、但不足以锁定目标"是语义判断。
2. **S2 vs S1 的界线**（VCLM-06）：原文 "we are launching" 是计划时还是进行时，
   要靠时态/语境判断，并决定不写成"已推出"。
3. **"attended to pursue my business degree" ≠ 获得学位**（VCLM-03 的 scope）：跳过这层就会
   造出一个假学历。
4. **"Juang" 是不是同一个姓**（CAND-02）：拼写差一格 + 圣迭戈与 RocketReach 摘要地点吻合，
   合并的诱惑很强；判断依据只有"拼写不同且无身份证明"，所以保留为独立候选 + LEAD-01 假设。
5. **CAND-01 与 CAND-03 的 circumstantial 重叠**（都在 MA、都 SNHU、都沙龙业）为何仍不合并：
   SNHU 一个是 2018 自述、一个是搜索摘要；十里距离 + 同行业不构成身份证据。
6. **CAND-05（高中运动员）疑似未成年**：主动收手、只留防混淆记录、不深挖，
   这是政策判断（来源政策排除条款的精神适配），不是工具阻断的。
7. **authwall/403/404 页面"留证但不取材"**：判定 LinkedIn 999 页和 SERP 摘要的证明力差异，
   需要人读原始 HTML 后决定用途分类。
8. **低足迹结论本身**："查了七类模式都没结果"是否写成"此人不存在"——写成
   "足迹薄 + 后端受限"是选择性判断。

## 4. Could a user understand and use this dossier?

可以，附两个前提。

**可用性**：recall_report.md 开头就是"没有任何主体占主导"的结论句和候选总览表；
每节标了来源性质（第一人称访谈 / 第一方自述 / 索引摘要 / authwall）；
每个 S1 分句挂 claim id，可经 evidence_index.md 定位到原文引文和本地字节。
用户若关心沙龙店主，拿 CAND-01 五条就能开口讲这个人（2018 时点）；
用户若想找的是钢琴教师或某位教师，档案已指出另一条线和对应的开放问题。
G 节的下一轮搜索顺序具体到公司和登记名。

**两个前提**：
- 档案大量使用"2018 年时点"的限定，用户必须接受这些事实可能已过期（沙龙可能易主）。
- S4 四条都依赖同一个 Brave SERP（4 份原始 SERP 文件支撑 4 条同名记录），
  用户应理解为"知道这些档案存在"，而不是"知道这些人的履历"。
  这一点在报告和索引里都明示了，但确实依赖唯一一个未限流的后端。

## 5. SKILL.md friction points

按测试目标写——这是对指令的批评，不是对我执行的辩护。按严重度排序：

1. **六步流程缺"搜索后端选型/降级"指引，这在真实执行里是第一道卡。**
   本案 6/18 条查询死在 bot 墙上；DDG HTML、Lite、Yandex、Mojeek、Ecosia 全拦。
   SKILL 只说"工具自主选择（web 搜索、直接访问已知来源类型、机构 API）"，
   没给任何"主后端被拦时换什么"的默认顺序，也没说 SERP 要不要当证据留
   （本案 Brave SERP 同时承担了"发现候选"和"authwall 内容的唯一可见残片"两个角色）。
   *修法*：加一条"搜索后端降级链 + SERP 快照必须落盘（它常是 authwall 页面唯一证据）"。

2. **"低足迹"指令与"不召回学术模式"没有给出可执行判据。**
   "不使用"节说目标姓名难以区分任何公开身份时"按低足迹预期执行"，
   但没说低足迹判定要基于什么：是全后端零命中，还是主后端不可用时的零命中？
   本环境的真实情况是后者，而报告只能诚实地写"受后端影响"。
   *修法*：明确"低足迹结论必须注明检索后端可用性，主后端被拦时不得声称穷举"。

3. **S4 的定义装不下 authwall/索引摘要这一整个证据类别。**
   S4 写的是"传闻线索——间接、未闭合、历史描述"，导向是"继续搜索的入口"。
   但 HTTP 999/403 的 SERP 摘要和 404 页面不是传闻，是**结构上不可读的高提示性残片**：
   它足以证明"存在多个同名档案"（VCLM-10 用 S4 勉强装下），却不足以写履历。
   yao_sun 案例把六份 LinkedIn authwall 页列为"不是六份人物履历"，
   但 SKILL 的表里没有对应行，执行者只能把 S4 当垃圾桶。
   *修法*：S1–S4 表加一行（或 S4 拆出）"S4-x 不可读残片：authwall/403/404/SERP 摘要，
   只记录'存在'与来源标注，禁止任何属性断言"。

4. **"每页抓取即落盘原文"与"噪声页也留"没有去留规则，产生 13 个 GB 级 SERP。**
   4 份 Brave SERP 共约 690KB，内容高度重复；SKILL 只说噪声页也留，
   但没说 SERP、重定向、挑战页怎么命名和裁留，执行者只能自行决定（我保留全部以证穷尽，
   但如果有人照抄会把 raw_sources 塞满 HTML）。
   *修法*：给一句"同一查询族的 SERP 只保留首份快照 + 其余仅登记 URL 与命中数"。

5. **同名候选表的字段对"非目标同名人"没有兜底。**
   案例要求每个候选"写清本案留存的独立记录或尚未核实"，执行顺利；
   但 MaxPreps 两条暴露盲区：候选疑似未成年人时，SKILL 的来源政策只列了排除类别
   （住址/家属/健康），没有"疑似未成年主体主动停止深挖"的指令，
   执行者只能自行按政策精神收手并写进 OQ-05（OPEN_BY_POLICY 是我自造状态值，
   yao_sun 账本里没有先例，格式上不可比）。
   *修法*：来源政策加一条"疑似未成年公众人物主体，只保留同名消歧所需最少记录"，
   并给 open_questions 一个标准 status 值。

6. **机械自检脚本对本案不可跑，SKILL 没说"不可跑时怎么办"。**
   `verify_investigation_bundle.py --bundle-dir` 按 yao_sun 的形态设计（要求 evidence_index、
   manifest、dossier.json 等）。本案按任务书只产出 6+1 个文件，跑校验只会报缺失。
   *修法*：任务级/迁移级案卷允许最小 bundle，SKILL 明列最小文件集
   （query_logs / source_inventory / verified_claims / corroborated_leads /
   open_questions / recall_report 六件即可过校验）。

7. **轻微：模板语言痕迹。** worked example 强调"事实性分句就近挂 claim_id"，
   很好用；但 S2/S3 写法在中文模板里固定成"公开表达期待"，对非学术小微企业主
   （"今年九月推出"）略显别扭，执行时要自己换词。不是阻塞，记录备查。

**总评**：四类阻断（伪造来源、主体归属、未证推断、来源政策）本案均无违反——
引用闭包自校验通过（13 VCLM / 4 LEAD / 5 OQ 无悬空），
逐条 verbatim 与本地字节核对。真正拖慢执行的是第 1、3、6 条：
后端降级、S4 证据类、最小 bundle 契约。这三处补上，指令可以零解释地交给下一个执行者。
