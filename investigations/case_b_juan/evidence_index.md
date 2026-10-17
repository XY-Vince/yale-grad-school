# Belinda Juan 证据索引

日期：2026-10-12。与 [recall_report.md](recall_report.md) 配套。每条给出引文、来源性质与本地载荷。
索引摘要（SERP snippet）不是传记；authwall 页面不是履历。

| ID | 候选 | 档位 | 谓词 / 对象 | 引文 | 来源性质 |
|---|---|---|---|---|---|
| VCLM-01 | CAND-01 | S1 | owns_business / Bliss Spa & Salon | "In 2008 I was presented with the opportunity to purchase Bliss (at the time it was named Paradise)." | 第一人称访谈（2018） |
| VCLM-02 | CAND-01 | S1 | attended_school / Whittier Regional Vocational High, Cosmetology (2001) | "I started my journey at Whittier Regional Vocational High school in the Cosmetology program (2001)." | 第一人称访谈 |
| VCLM-03 | CAND-01 | S1 | attended_school / SNHU, business degree | "After graduating I attended SNHU as a full-time student while working at the salon, I currently own to pursue my business degree (2005)." | 第一人称访谈；就读非毕业 |
| VCLM-04 | CAND-01 | S1 | acquired_business / Bliss 2008 | "On June 25th we celebrated our ten year anniversary." | 第一人称访谈 |
| VCLM-05 | CAND-01 | S1 | works_in_role / on-floor hair services, 4 days/week | "I am the owner of Bliss and also work on the floor providing hair services four days a week." | 第一人称访谈 |
| VCLM-06 | CAND-01 | S2 | plans_activity / CBD oil massage | "This September we are launching our CBD oil massage." | 公开意向，未证实上线 |
| VCLM-07 | CAND-03 | S4 | indexed_on_platform / LinkedIn: Green Room Beauty Bar | "Belinda Juan - The Green Room Beauty Bar \| LinkedIn ... Experience: The Green Room Beauty Bar - Education: Southern New Hampshire University - Location: Methuen" | Brave 索引摘要；原页 HTTP 999 |
| VCLM-08 | CAND-04 | S4 | indexed_on_platform / RocketReach: Teacher at Assurant | "Belinda Juan, based in San Diego, CA, US, is currently a Teacher at Assurant." | Brave 索引摘要；原页 HTTP 403 |
| VCLM-09 | CAND-05 | S4 | indexed_on_platform / MaxPreps rosters (CA) | "Belinda has been added to the West Valley 2025-26 soccer roster." | Brave 索引摘要；两 URL 抓取时 404 |
| VCLM-10 | CAND-06 | S4 | indexed_on_platform / LinkedIn directory 10+ profiles | "10+ \"Belinda Juan\" profiles" | Brave 索引摘要 + HTTP 999 目录页 |
| VCLM-11 | CAND-02 | S1 | owns_business / Belinda's Piano Studio, San Diego | "Belinda Juang is the owner of and piano instructor at Belinda's Piano Studio located in San Diego, CA." | 第一方商业站自述；姓名拼写 Juang |
| VCLM-12 | CAND-02 | S1 | attended_school / U-Michigan dual bachelor's | "She received her dual bachelor's degrees in piano performance and psychology from the University of Michigan." | 第一方自述 |
| VCLM-13 | CAND-02 | S1 | works_in_role / private piano teacher since 2010 | "Belinda has been teaching classical piano privately since 2010 to children ages 5 and up" | 第一方自述 |

## 线索

| ID | 候选 | 标题 | 入口 |
|---|---|---|---|
| LEAD-01 | CAND-02 | Juang（圣迭戈钢琴）与 CAND-04（RocketReach 圣迭戈）或为同一人 | 假设，未证实 |
| LEAD-02 | CAND-01 | CAND-01 与 CAND-03（Methuen, MA, SNHU）或为同一人 | 假设，未证实 |
| LEAD-03 | CAND-01 | Bliss Spa 2018 之后的经营现状 | MA 企业登记、社媒 |
| LEAD-04 | CAND-03 | The Green Room Beauty Bar 独立存在性 | 单独搜公司名 |

原始载荷：`raw_sources/bostonvoyager_belinda_juan.html`（访谈）、
`raw_sources/belindapianostudio_about.html`（钢琴站）、
`raw_sources/brave_search*.html`（4 份 SERP）、
`raw_sources/linkedin_authwall_999_*.html`（2 份 999 页）、
`raw_sources/rocketreach_belinda_juan.html`（403 挑战页）、
`raw_sources/maxpreps_*.html`（2 份 404 页）、
`raw_sources/news_google_rss_belinda_juan.xml`（新闻噪声）。
哈希与字节见 `source_inventory.jsonl`。
