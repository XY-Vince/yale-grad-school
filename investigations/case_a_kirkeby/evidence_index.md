# Evidence Index — case_a_kirkeby

Each entry: claim id, source, locator, verbatim fragment, and the local raw payload path.
Verbatim fragments are quoted as they appear in the stored payload (HTML text nodes,
JSON fields, or JSON-LD / API response fields). No fragment is reconstructed from
memory. All captures were taken on 2026-10-12 (UTC).

## VCLM-01 — current title(s), Roskilde University portal

- Source: SRC-02 — `raw_sources/ruc_profile_kirkeby.html`
- Locator: profile header title block (rendered `<li>` list items after the name)
- Verbatim (HTML text nodes, whitespace collapsed):
  `Maja Hanne Kirkeby Assistant Professor Associate Professor , Department of People
  and Technology Programming, Logic and Intelligent Systems`
- Source nature: institutional record (Pure portal, self/unit maintained).
- Boundary: two titles appear in one header. This evidence does not order them in
  time and does not resolve which is current.

## VCLM-02 — Roskilde University affiliation

- Source: SRC-02 — `raw_sources/ruc_profile_kirkeby.html`
- Locator: page `<title>` and portal header
- Verbatim: `Maja Hanne Kirkeby - Roskilde University Research Portal`
- Source nature: institutional record.

## VCLM-03 — research group PLIS, Department of People and Technology

- Source: SRC-07 — `raw_sources/crossref_fac_confluence.json`
- Locator: `message.author[1].affiliation[0].name`
- Verbatim:
  `"Research group PLIS: Programming, Logic and Intelligent Systems, Department of
  People and Technology, Roskilde University, Roskilde, Denmark"`
- Additional support: SRC-02 header unit strings.
- Source nature: publisher-deposited metadata (affiliation for the 2017 article).
- Boundary: affiliation as of the 2017 publication; current unit per SRC-02.

## VCLM-04 — PhD thesis record

- Source: SRC-05 — `raw_sources/ruc_thesis_uuid.html`
- Locator: publication metadata block and citation list
- Verbatim:
  `Kirkeby, MH (2018). Probabilistic program analysis . Roskilde Universitet.` …
  `Kirkeby, Maja Hanne . / Probabilistic program analysis . Roskilde : Roskilde
  Universitet, 2018. 139 s.` … `M3 - PhD thesis`
- Source nature: institutional record typed `Publikation : Ph.d.- afhandling`.
- Boundary: 139 pages and 2018 are the record's own values; the defence date and
  committee are not stated on this page.

## VCLM-05 / VCLM-06 — ORCID employment entries

- Source: SRC-01 — `raw_sources/orcid_0000-0003-0033-2438.json`
- Locator: `activities-summary.employments.affiliation-group[].summaries[].employment-summary`
- Verbatim:
  `{"org": "Roskilde University", "dept": "The Department of Communication, Business
  and Information Technologies", "role": "VIP, PhD Fellow", "start": {"year":
  {"value": "2012"}, "month": {"value": "12"}, "day": {"value": "01"}}, "end":
  {"year": {"value": "2015"}, "month": {"value": "12"}, "day": {"value": "17"}}}`
- Verbatim (current entry):
  `{"org": "Roskilde University", "dept": "Department of People and Technology",
  "role": "VIP, Associate Professor", "start": {"year": {"value": "2012"}, "month":
  {"value": "12"}, "day": {"value": "01"}}, "end": null}`
- Source nature: self-report in a registry record.
- Boundary: the identical 2012-12 start on both entries and the pre-2018 start date
  are unresolved; see LEAD-01 / OQ-01.

## VCLM-07 — name variants

- Source: SRC-01 — `raw_sources/orcid_0000-0003-0033-2438.json`
- Locator: `person.name` and `person.other-names.other-name[0].content`
- Verbatim:
  `{"given-names": {"value": "Maja"}, "family-name": {"value": "Kirkeby"}}` …
  `"content": {"value": "Maja Hanne Kirkeby"}`
- Additional support: SRC-04 `authorships[].raw_author_name` values
  (`Maja H. Kirkeby`, `Maja Hanne Kirkeby`, `Maja Kirkeby`, `Kirkeby, Maja H.`,
  `Kirkeby, Maja Hanne; id_orcid 0000-0003-0033-2438`).
- Source nature: self-report plus aggregated index.

## VCLM-08 — ORCID identifier, claimed and email-verified

- Source: SRC-01 — `raw_sources/orcid_0000-0003-0033-2438.json`
- Locator: `person.history` and `person.name`
- Verbatim:
  `"creation-method": "DIRECT", "submission-date": {"value": 1523958411320},
  "last-modified-date": {"value": 1789199896797}, "claimed": true, "verified-email":
  true` …
  `"path": "0000-0003-0033-2438"`
- Additional support: SRC-03 `orcid: "https://orcid.org/0000-0003-0033-2438"`.
- Source nature: registry record.
- Boundary: ORCID verifies the account, not the content added to it.

## VCLM-09 — PhD thesis in OpenAlex

- Source: SRC-06 — `raw_sources/openalex_work_phd_thesis.json`
- Locator: `title`, `authorships[0]`
- Verbatim:
  `"title": "Probabilistic program analysis", "publication_date": "2018-01-01"` …
  `"raw_affiliation_strings": ["Roskilde University, Department of People and
  Technology, DK"]`, `"raw_author_name": "Kirkeby, Maja Hanne; id_orcid
  0000-0003-0033-2438"`
- Source nature: aggregated index.

## VCLM-10 — Formal Aspects of Computing article

- Source: SRC-07 — `raw_sources/crossref_fac_confluence.json`
- Locator: `message.title`, `message.container-title`, `message.published`, `message.author`
- Verbatim:
  `"title": ["On proving confluence modulo equivalence for Constraint Handling
  Rules"], "container-title": ["Formal Aspects of Computing"], "published":
  {"date-parts": [[2017, 1]]}` … author affiliation string quoted in VCLM-03.
- Source nature: publisher-deposited metadata.

## VCLM-11 — IJAR article

- Source: SRC-08 — `raw_sources/crossref_ijar.json`
- Locator: `message.title`, `message.volume`, `message.page`, `message.published`, `message.author`
- Verbatim:
  `"title": ["Confluence and convergence modulo equivalence in probabilistically
  terminating reduction systems"], "volume": "105", "page": "217-228", "published":
  {"date-parts": [[2019, 2]]}` … `authors: [("Maja H.", "Kirkeby"), ("Henning",
  "Christiansen")]`
- Source nature: publisher-deposited metadata.

## VCLM-12 … VCLM-15 — energy-software publication set

- Source: SRC-04 — `raw_sources/openalex_works_A5034230236.json`
- Locator: `results[]` entries, fields `title`, `authorships[].author.display_name`,
  `biblio`, `doi`
- Verbatim examples:
  - `Compiling Haskell for Energy Efficiency: Empirical Analysis of Individual
    Transformations` — authors `Maja H. Kirkeby, Bernardo Santos, João Paulo
    Fernandes, Alberto Pardo` — `10.1145/3605098.3635915`
  - `Power Assumptions Matter: Evaluating End-User Laptop Energy Models for
    Sustainability Reporting of Browser-Based Web Services` — authors
    `Maja H. Kirkeby, Timmie M. R. Lagermann` — pages `189`–`196` —
    `10.1109/SANER-C67878.2026.00031`
  - `Framework Matters: Energy Efficiency of UI Automation Testing Frameworks` —
    authors `Timmie M. R. Lagermann, Kristina Carter, Su Mei Gwen Ho, Luís Cruz,
    Kerstin Eder, Maja H. Kirkeby`
  - `Bridging the gap between industry and academia: sustainability in LLM-assisted
    software engineering` — authors `Maja H. Kirkeby, Pepijn de Reus, Ana Oprescu,
    Kalle Pronk, Qin Zhao, Fernando Castor`
- Source nature: aggregated index. Author order, titles, pages and DOIs are
  index-recorded; the index does not verify authorship contributions.

## VCLM-16 — teaching experience report preprint

- Source: SRC-09 — `raw_sources/arxiv_2504_19707.html`
- Locator: `Authors:` and `Abstract:` blocks
- Verbatim:
  `Authors: Henrik B{\ae}rbak Christensen , Maja Hanne Kirkeby , Bent Thomsen , Lone
  Leth Thomsen` … `Abstract: Environmental sustainability is a major and relevant
  challenge facing computing. Therefore, we must start teaching theory, techniques,
  and practices ... describe teaching approaches from three different universities`
- Source nature: author-submitted preprint abstract.

## VCLM-17 — projects

- Source: SRC-02 — `raw_sources/ruc_profile_kirkeby.html`
- Locator: Projects section listing
- Verbatim:
  `Green IT-procurement Pries-Heje, J. (Project manager), Christensen, T. B.
  (Project participant), Boulus-Rødje, N. (Project participant) & Kirkeby, M. H.
  (Project participant) 01/01/2024 → 31/07/2028 Project : Research` …
  `Energy and Performance Trade-offs in Hardware and Software Implementations
  Kirkeby, M. H. (Project manager), Rosendahl, M. (Project participant), Krabben,
  T. (Project participant) & Schoeberl, M. (Project participant) Digital Research
  Centre Denmark – DIREC 01/02/2022 → 31/01/2023 Project : Research`
- Source nature: institutional record.
- Boundary: role labels as recorded in the portal; tasks not described.

## VCLM-18 — activities and committee memberships

- Source: SRC-02 — `raw_sources/ruc_profile_kirkeby.html`
- Locator: Activities section listing
- Verbatim:
  `CERCIRAS Training School 2022 Vardanega, T. (Organizer), Bilic, I. (Organizer),
  Kirkeby, M. H. (Organizer), Schoeberl, M. (Organizer), Pezzarossa, L.
  (Organizer), Fernandes, J. P. (Organizer), Santos, B. (Organizer), Kertesz, A.
  (Organizer) & Baniata, H. (Organizer) 19 Sept 2022 → 24 Sept 2022 Activity :
  Participating in or organising an event › Participation in workshop, seminar,
  course` … `31st International Symposium onLogic-based Program Synthesis and
  Transformation (Event) Kirkeby, M. H. (Member) 7 Sept 2021 Activity : Membership
  › Membership in committee, council, board`
- Source nature: institutional record. "Member" is the portal's activity type, not
  a described role.

## VCLM-19 — press/media appearances

- Source: SRC-10 — `raw_sources/ruc_clipping_ai_expert.html`
- Locator: Media coverage block
- Verbatim:
  `Title Ekspert om AI-strømforbrug: »Vi lader de store techvirksomheder slippe
  afsted med for meget« Degree of recognition National Media name/outlet Ingeniøren
  Media type Web Country/Territory Denmark Date 01/11/2024 Producer/Author Bjørn
  Godske URL https://ing.dk/artikel/ekspert-om-ai-stroemforbrug-vi-lader-de-store-
  techvirksomheder-slippe-afsted-med-meget Persons Maja Hanne Kirkeby`
- Source nature: portal record of a clipping; the underlying article was not
  captured, so no quotation is attributed.

## VCLM-20 — research topics and keywords

- Source: SRC-02 — `raw_sources/ruc_profile_kirkeby.html`
- Locator: Personal profile section
- Verbatim:
  `Research Energy consumption of Software, Analysis of Software, Program
  Transformation` … `Keywords Computer science, IT Program Inversion Energy-aware
  Software Development Program Analysis`
- Additional support: SRC-03 `topics` (`Logic, programming, and type systems`;
  `Green IT and Sustainability`; `Formal Methods in Verification`).
- Source nature: self-entered fields on an institutional portal.

## VCLM-21 — publication and citation footprint

- Source: SRC-04 — `raw_sources/openalex_works_A5034230236.json`
- Source: SRC-03 — `raw_sources/openalex_author_A5034230236.json`
- Locator: `results[]`, `summary_stats`, `works_count`, `cited_by_count`
- Verbatim:
  `"works_count": 39, "cited_by_count": 81, "summary_stats":
  {"2yr_mean_citedness": 1.2222222222223, "h_index": 5, "i10_index": 2}`
  … publication years present in `results[]` span `2015` to `2026`.
- Source nature: aggregated index. RUC portal counts differ (30 outputs) because
  the index includes preprints and duplicate records; both are reported, neither
  is treated as the authoritative count.

## VCLM-22 — peer-review activity

- Source: SRC-01 — `raw_sources/orcid_0000-0003-0033-2438.json`
- Locator: `activities-summary.peer-reviews.group[].external-ids` and
  `peer-review-summary[].reviewer-role`
- Verbatim:
  `{"external-id-type": "peer-review", "external-id-value":
  "issn:0167-6423"}` … `"reviewer-role": "reviewer"` with source client
  `Elsevier Editorial` and `created-date` value 1718424999835 (2024-06-15).
- Source nature: client-deposited registry entry.
- Boundary: the record shows three journal ISSNs and reviewer role; the reviewed
  manuscript titles are not included.

## VCLM-23 — ORCID ↔ institution profile link

- Source: SRC-01 — `raw_sources/orcid_0000-0003-0033-2438.json`
- Locator: `person.researcher-urls.researcher-url[0]`
- Verbatim:
  `"url-name": "Roskilde University profile page", "url": {"value":
  "https://forskning.ruc.dk/en/persons/6cfe17de-77a5-4277-961e-3be12eba1414"}`,
  deposited by client `0000-0002-7223-7870` / `Roskilde University`.
- Source nature: institution-side registry deposit.

## Non-evidence captures (retained as proof of attempts, per skill §3)

- SRC-11 `raw_sources/ruc_KirkebyThesis_BLOCKED.html` — HTTP 403 Cloudflare
  challenge; thesis PDF bytes not obtained.
- SRC-12 `raw_sources/springer_fac_confluence_BLOCKED.html` — publisher
  fingerprint "Client Challenge"; no article content. Crossref used for the same
  work instead.

## VCLM-14 — Framework Matters (SAC 2026)

- Source: SRC-04 — `raw_sources/openalex_works_A5034230236.json`
- Locator: `results[]` entry, `title` / `authorships` / `biblio`
- Verbatim:
  `Framework Matters: Energy Efficiency of UI Automation Testing Frameworks` …
  authors `Timmie M. R. Lagermann, Kristina Carter, Su Mei Gwen Ho, Luís Cruz,
  Kerstin Eder, Maja H. Kirkeby`
- Source nature: aggregated index.

## Leads and open questions (cross-reference)

These entries live in `corroborated_leads.jsonl` and `open_questions.jsonl`; the index
mirrors their ids so report links resolve.

### LEAD-01 — title sequencing (S4)
Unresolved whether the portal's two title strings are ordered in time, and what the
ORCID 2012-12 start date refers to. Evidence: SRC-01 `employment-summary[0..1]`,
SRC-02 header. Next: dated institutional staff listing or CV.

### LEAD-02 — pre-PhD education (S4)
ORCID `activities-summary.educations` and `qualifications` are both `[]`; no CV
section on the portal. Evidence: SRC-01, SRC-02.

### LEAD-03 — thesis defence details (S4)
The portal record gives type, year, pages, series; not the defence date or
supervisor. Evidence: SRC-05 metadata block; SRC-11 shows the PDF fetch failed.

### LEAD-04 — teaching role (S4)
Evidence: SRC-09 arXiv abstract. The abstract names three universities but not the
courses or her role.

### LEAD-05 — second citation source (S4)
Evidence: SRC-03 `summary_stats`. Scholar returned CAPTCHA, Semantic Scholar 429,
DBLP Anubis. See query_logs QRY-07/08/13/14.

### LEAD-06 — two unread portal projects (S4)
The portal header counts `Projects (7)` while the page body lists five; the
`/projects/` sub-path returned 403. Evidence: SRC-02, query_log QRY-22.

### OQ-01 — current exact rank and promotion date (OPEN)
Same evidence as LEAD-01. Next: dated staff listing or self-published CV.

### OQ-02 — pre-PhD degrees (OPEN)
Same evidence as LEAD-02. Next: thesis front matter, alumni records, CV.

### OQ-03 — whether a second "Maja Kirkeby" exists (OPEN)
PubMed 0 hits; OpenAlex single entity; DBLP and Scholar checks failed. Absence of a
second entity in two sources is not proof of uniqueness. Next: retry DBLP/Scholar
with a browser session.

### OQ-04 — funding and task scope on Green IT-procurement (OPEN)
Evidence: SRC-02 project entry. Next: open the project page from the portal index.

### OQ-05 — secondary affiliations on 2026 co-authored papers (OPEN)
OpenAlex records only Roskilde University for her on the 2026 works. Evidence:
SRC-04 `authorships[].institutions`. Next: read author blocks in the paper PDFs.
