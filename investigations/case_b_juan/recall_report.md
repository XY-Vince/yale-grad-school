# Belinda Juan 人物档案（低足迹案例）

调查日期：2026-10-12。目标：Belinda Juan（常见全名，未提供机构/领域等约束）。本案为非学术来源路径
（本地媒体采访 / LinkedIn 索引 / Piano 商业站 / MaxPreps / RocketReach）。所有页面在本日抓取，
原始字节与 SHA-256 见 `source_inventory.jsonl`，检索留痕（含失败与被拦截的查询）见 `query_logs.jsonl`。

**结论先行**：没有任何单一可核实主体在本次检索中占主导。最具体的可读主体是 **CAND-01
（Bliss Spa & Salon 店主，北安多弗，马萨诸塞）**，证据是一篇 2018 年的第一人称访谈。
但这个名字在 LinkedIn 目录中约有 10+ 个档案（VCLM-10），另有至少 5 个不同身份的同名/近名记录。
本档案不做目标锁定，只做候选分列——这是低足迹场景的诚实输出。

## A. 候选总览

| 候选 | 本案留存的独立记录 | 处理 |
|---|---|---|
| CAND-01 | Belinda Juan，Bliss Spa & Salon（北安多弗，MA）店主；2018-10-12 本地媒体访谈 | 可读证据最多，但仅此一篇；不作为唯一目标 |
| CAND-02 | Belinda **Juang**（拼写不同），Belinda's Piano Studio（圣迭戈，CA）店主 | 姓名拼写有差异，单独一列；不合并 |
| CAND-03 | Belinda Juan，LinkedIn 档案：The Green Room Beauty Bar；地点 Methuen, MA；教育 SNHU | 页面 HTTP 999，仅搜索摘要；单独一列 |
| CAND-04 | Belinda Juan，RocketReach 聚合档案："Teacher at Assurant"，圣迭戈, CA | 页面 HTTP 403，仅搜索摘要；单独一列 |
| CAND-05 | Belinda Juan，加州两所高中足球名录（Fallbrook、West Valley） | 疑似未成年运动员；只作防混淆记录，不深挖 |
| CAND-06 | "10+ Belinda Juan profiles"（LinkedIn 公共目录） | 只证明同名档案众多；不构成任何个人履历 |
| CAND-05 变体 | Instagram "Belinda + Juan" 婚礼帖（未抓取） | 噪声/私人场景，不纳入 |

没有因为"都在沙龙行业/都在美国"或"都在圣迭戈"而合并任何两个候选。GRE 线索
（LEAD-01/02）只是下一步的入口。

## B. CAND-01：目前可读证据最多的主体（2018 访谈，单源）

来源性质：第三方本地生活杂志的**第一人称访谈问答**（Boston Voyager, 2018-10-12）。
页面见 `raw_sources/bostonvoyager_belinda_juan.html`。以下每条都是页面原文，
但请注意：访谈内容是受访者自述，且时点是 2018 年。

### S1 已确认发生（原文明确陈述）

- **沙龙经营**：受访者称 2008 年买下 Bliss（当时名为 Paradise），并在 2018 年 6 月 25 日
  庆祝十周年。[VCLM-01](evidence_index.md#vclm-01)、[VCLM-04](evidence_index.md#vclm-04)
- **现任角色**：自述"我是 Bliss 的老板，同时每周四天在店里做美发服务"。[VCLM-05](evidence_index.md#vclm-05)
- **教育经历（就读，非学位）**：自述 2001 年入读 Whittier Regional Vocational High School
  美容专业；毕业后就读 SNHU 攻读 business degree。[VCLM-02](evidence_index.md#vclm-02)、
  [VCLM-03](evidence_index.md#vclm-03)
- **服务范围**：自述沙龙提供剪、染、角蛋白柔顺、烫发及美容类服务（面部护理、按摩、
  睫毛项目、美甲等）。见访谈原文，未单独建 claim（同句内的经营描述，归 VCLM-01 范围说明）。

### S2 公开意向

- **CBD 按摩服务**：访谈称"今年九月我们将推出 CBD oil massage"。这只是公开表达的计划，
  没有任何证据表明服务已上线。[VCLM-06](evidence_index.md#vclm-06)

### 边界

- "目前经营"是 2018 年时点的陈述。2026 年是否仍在经营、沙龙是否易主或关闭，本案没有证据
  （见 LEAD-03 / OQ-01）。
- SNHU 只证明"就读 + 攻读 business degree"，原文未写"获得学位"（OQ-02）。
- 该页面不构成公司登记、获奖或第三方对其专业的独立认证。

## C. CAND-02：Belinda Juang（钢琴教师，圣迭戈）

来源性质：**第一方商业网站自述**（belindapianostudio.com/about/，原始字节见
`raw_sources/belindapianostudio_about.html`）。姓氏拼写为 Juang 而非 Juan。

### S1 已确认发生（本人自述）

- **工作室经营**：自述是 Belinda's Piano Studio 的 owner 和钢琴教师，工作室位于圣迭戈。[VCLM-11](evidence_index.md#vclm-11)
- **学历**：自述从 University of Michigan 获得钢琴表演与心理学双学士学位。[VCLM-12](evidence_index.md#vclm-12)
- **教龄**：自述 2010 年起私人教授古典钢琴，学生 5 岁起。[VCLM-13](evidence_index.md#vclm-13)

### 边界

- 拼写差异（Juang/Juan）没有解决，不能合并进目标。圣迭戈地点与 CAND-04 的 RocketReach
  摘要一致是一个**假设**（LEAD-01），不是证据。

## D. 其他同名记录：只有索引摘要或 authwall（不进履历）

- **CAND-03（LinkedIn, Green Room Beauty Bar）**：Brave 搜索摘要描述该档案含
  "Experience: The Green Room Beauty Bar, Education: Southern New Hampshire University,
  Location: Methuen"；实际页面 HTTP 999。摘要属第三方索引文本，S4。[VCLM-07](evidence_index.md#vclm-07)
- **CAND-04（RocketReach）**：摘要称"based in San Diego, CA, US, is currently a Teacher
  at Assurant"；页面 HTTP 403 Cloudflare 挑战。未读取任何联系信息，S4。[VCLM-08](evidence_index.md#vclm-08)
- **CAND-05（MaxPreps 两份名录）**：摘要显示 2024-25 Fallbrook、2025-26 West Valley 足球
  名录；两个 URL 抓取时均 404。疑似在读中学生，按职业画像范围不深挖，仅防混淆，S4。
  [VCLM-09](evidence_index.md#vclm-09)
- **CAND-06（LinkedIn 目录）**：摘要显示 "10+ Belinda Juan profiles"；说明同名档案至少十个，
  支持不自动合并，S4。[VCLM-10](evidence_index.md#vclm-10)

## E. 检索 exhausted 的模式（下次接手请先看这里）

`query_logs.jsonl` 共 18 条查询，其中 6 条被拦截或失败。已尝试并确认无结果的模式：

1. **通用网页精确匹配**：`"Belinda Juan"`（Google/Bing 对引号短语支持弱；Brave 支持并返回
   8 条结果，构成本案全部候选来源）
2. **新闻**：Google News RSS 精确匹配 —— 10 条无一命中（噪声全是无关讣闻）
3. **菲律宾语境**（该姓名组合的常见地区）：`"Belinda Juan" Philippines OR Pilipinas OR
   Manila` —— 零命中
4. **教育/教师语境**：`"Belinda Juan" teaching OR teacher OR faculty` —— 仅 RocketReach 命中
5. **LinkedIn 直连**：`/in/belinda-juan-0640961b` 与 `/pub/dir/Belinda/Juan` —— 均 HTTP 999
6. **聚合器直连**：rocketreach.co —— HTTP 403
7. **公司官网**：thegreenroombeautybar.com、blissspaandsalon.com —— 连接失败（HTTP 000）

被 bot 拦截、未产出的后端：DuckDuckGo HTML、DuckDuckGo Lite、Mojeek、Yandex、Ecosia、
Yahoo（500）、Google 网页版（JS 重定向存根）。Brave 是本次唯一可用的短语搜索源，
且连续查询会触发 429 验证码——这意味着**本案的召回率受后端环境影响很大**，
"没找到"不等于"不存在"（OQ-06）。

## F. 用户现在还不知道什么

1. **目标是否唯一**：没有主体占主导。若用户只想查沙龙店主，CAND-01 已是目前最好答案，
   但需确认她指的是哪个 Belinda Juan（OQ-01/OQ-03）。
2. **CAND-01/03 是否同一人**：SNHU + MA 地理 + 同行业， circumstantial 但未证实（OQ-03）。
3. **CAND-02 的拼写问题**：Juang 是变体还是另一个人（OQ-04）。
4. **CAND-01 的现状**：2018 之后的经营状态、二店（Green Room?）、SNHU 是否毕业（OQ-01/02）。
5. **是否存在有公众知名度的人物**：新闻、奖项、公司登记、学术记录都没有出现这个名字
   （OQ-06）；也可能只是检索后端被拦导致召回不足。

## G. 下一轮最值得搜索的内容

1. **换一个未被拦的主搜索源**重跑 `"Belinda Juan"` 与 `"Belinda Juang"`（Google 网页版走
   可渲染路径、Bing 关闭引号弱匹配问题、Startpage）。
2. **马萨诸塞州企业登记**（Secretary of the Commonwealth 公开检索）：Bliss Spa & Salon /
   The Green Room Beauty Bar 的注册与现任管理人。
3. **沙龙现状**：Google/Yelp 商家列表、Instagram @blissspaandsalon2008（访谈中给出的账号）、
   Green Room Beauty Bar 的社媒存在性。
4. **CAND-03 LinkedIn 的可读渲染**：搜索引擎缓存或页内引用文本；不把 999 当履历。
5. **belindapianostudio.com 全站**（联系页、博客）核对是否出现 "Juan" 拼写与社媒 handle，
   以验证 LEAD-01。

## H. 账本说明

`verified_claims.jsonl` 共 13 条：S1 8 条（CAND-01 五条、CAND-02 三条）、S2 1 条、S4 4 条（均为索引摘要/authwall 记录，属于不同候选）。
每条 S4 都注明"Snippet is index text, not a biography"，任何消费程序不得把 S4 当 S1。
`corroborated_leads.jsonl` 4 条、`open_questions.jsonl` 6 条。
`source_inventory.jsonl` 13 条来源：2 条目标/候选证据（访谈、钢琴站）、4 条检索 SERP 噪声、
3 条 authwall（LinkedIn x2、RocketReach）、2 条 404 噪声、1 条新闻噪声、1 条未抓取 Instagram。
