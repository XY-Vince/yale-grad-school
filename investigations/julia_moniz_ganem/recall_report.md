# 人物全景调查报告: Julia Moniz Ganem (通用召回优先证据闭环版)

> **调查对象**: Julia Moniz Ganem
> **先验线索**: Public Health; Vaccine
> **生成时间**: 2026-10-10 23:23:34 UTC
> **调查状态**: `PLAUSIBLE_PRIMARY_MATCH_WITH_HOMONYMS`
> **候选宇宙规模**: 检测到 3 个候选实体
> **证据闭环**: 3 份真实原始来源，全部通过 SHA-256 校验与载荷全文回放

---

## 一、 候选实体比对矩阵 (Candidate Matrix)

| 候选 ID | 姓名标识 | 关联机构与角色 | 匹配结论 | 消歧依据与引用 |
|---|---|---|---|---|
| **CAND-01** | **Julia Moniz Ganem** | **Section of Pediatric Infectious Diseases, Department of Pediatrics, Yale School of Medicine, New Haven, Connecticut** | **PRIMARY_TARGET** | Matches provided institutional and topical clues. [VCLM-01] |
| **CAND-02** | **Julia Moniz Ganem** | **Biomedical / Academic Institution** | **DIFFERENTIATED_HOMONYM** | Distinct institutional affiliation or disciplinary focus (Biomedical / Academic Institution). [VCLM-02] |
| **CAND-03** | **Julia Moniz Ganem** | **Yale School of Medicine Department of Pediatrics, New Haven, Connecticut, USA.** | **DIFFERENTIATED_HOMONYM** | Distinct institutional affiliation or disciplinary focus (Yale School of Medicine Department of Pediatrics, New Haven, Connecticut, USA.). [VCLM-03] |

---

## 二、 三层证据账本 (Tri-tier Evidence Ledgers)

### 1. Tier 1: 已验证硬事实 (Verified Claims)
* [VCLM-01] **affiliated_with**: `Section of Pediatric Infectious Diseases, Department of Pediatrics, Yale School of Medicine, New Haven, Connecticut` (候选人: `CAND-01`, 时间语义: `AS_OF_PUBLICATION`, 来源: `SRC-01`, 依据: "Section of Pediatric Infectious Diseases, Department of Pediatrics, Yale School ")
* [VCLM-02] **authored_work**: `Real-World Effectiveness of Maternal RSVpreF Vaccination and Durability of Infant Protection.` (候选人: `CAND-02`, 时间语义: `HISTORICAL`, 来源: `SRC-02`, 依据: "Real-World Effectiveness of Maternal RSVpreF Vaccination and Durability of Infan")
* [VCLM-03] **authored_work**: `Real-world effectiveness of perinatal RSV immunoprophylaxis: protocol for a test-negative case-control study.` (候选人: `CAND-03`, 时间语义: `HISTORICAL`, 来源: `SRC-03`, 依据: "Real-world effectiveness of perinatal RSV immunoprophylaxis: protocol for a test")
* [VCLM-04] **affiliated_with**: `Yale School of Medicine Department of Pediatrics, New Haven, Connecticut, USA.` (候选人: `CAND-03`, 时间语义: `AS_OF_PUBLICATION`, 来源: `SRC-03`, 依据: "Yale School of Medicine Department of Pediatrics, New Haven, Connecticut, USA.")

### 2. Tier 2: 可信但待核实线索 (Corroborated Leads)
* [LEAD-01] Target entity Julia Moniz Ganem exhibits verified scholarly publication activity in scientific registries. (支持来源: SRC-01)
* [LEAD-02] Domain and institutional signals correlate with clues: Public Health; Vaccine. (支持来源: SRC-01)

### 3. Tier 3: 未决问题清单 (Open Questions)
* [OQ-01] **Career Trajectory & Trajectory Closure**: Longitudinal career history and institutional transitions of Julia Moniz Ganem pending additional archival records.
* [OQ-02] **Homonym Separation & Verification**: Disambiguation between primary candidate and Julia Moniz Ganem (Biomedical / Academic Institution).

---

## 三、 检索轨迹与审计日志
共执行了 7 次定向阶梯检索：
- **OPENALEX_AUTHORS**: `https://api.openalex.org/authors?search=Julia%20Moniz%20Ganem&per_page=3` (状态: EXECUTED, HTTP 200, 命中数: 0)
- **CROSSREF_WORKS**: `https://api.crossref.org/works?query.author=Julia%20Moniz%20Ganem&rows=5&query=Public%20Health` (状态: EXECUTED, HTTP 200, 命中数: 1)
- **PUBMED_ESEARCH**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22Julia%20Moniz%20Ganem%22&retmode=json&retmax=5` (状态: EXECUTED, HTTP 200, 命中数: 2)
- **PUBMED_ESEARCH**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22Julia%20Moniz%20Ganem%22%20AND%20%28Public%20Health%29&retmode=json&retmax=3` (状态: EXECUTED, HTTP 200, 命中数: 0)
- **PUBMED_ESEARCH**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%22Julia%20Moniz%20Ganem%22%20AND%20%28Vaccine%29&retmode=json&retmax=3` (状态: EXECUTED, HTTP 200, 命中数: 0)
- **PUBMED_EFETCH**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=42780177&retmode=xml` (状态: EXECUTED, HTTP 200, 命中数: 0)
- **PUBMED_EFETCH**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=41856594&retmode=xml` (状态: EXECUTED, HTTP 200, 命中数: 0)
