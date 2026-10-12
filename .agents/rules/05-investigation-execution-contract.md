# Public Person Investigation — Execution Contract & Governance Rule

Activation: Antigravity Workspace Rule for Investigation & Profile Verification Tasks (`verify-public-person-profile`).

Use this rule for all autonomous and human-guided profiling, investigation, and recall optimization tasks.

---

## 1. Goal & Metric Hierarchy

### Primary Objective
Within the assigned query budget and strictly in-scope profile dimensions, maximize **verified claim recall** relative to pre-registered, complete withheld reference sets.

### Decisive Metric
$$\max(\text{Verified Claim Recall})$$
subject to:
1. $\text{Precision} \ge \text{agreed floor}$ (non-negotiable default: $\ge 0.95$).
2. $\text{Target Recall} \ge \text{preregistered floor}$ (default: $\ge 0.80$).
3. $\text{Cross-Entity Contamination} = 0$ on annotated homonym reference sets within the primary target entity cluster.
4. $\text{Provenance Replay} = 100\%$ against captured source bytes on disk.
5. $\text{Git Clean} = \text{True}$ (no uncommitted dirty files when certifying acceptance).
6. Zero out-of-scope privacy collection attempts.

> [!CAUTION]
> **Prohibited Metric Substitutes & Gating Invariants**:
> - Raw claim count, raw source count, unit test count, or generic auditor `PASS` verdicts must **never** be used as substitutes for verified claim recall.
> - Acceptance certification requires a verified reference gold set with `reference_completeness == "complete"`.
> - When withheld reference gold is absent or declared `"partial"`, evaluation is strictly **DIAGNOSTIC / UNVERIFIED_WITHOUT_GOLD**, precision is reported as `N/A`, and the runner must never issue acceptance certification.

---

## 2. In-Scope Dimensions & Versioned Predicate Registry (V1.2.0)

Per `references/source-policy.md`, investigation adheres to purpose limitation and data minimization:

### In-Scope Profile Dimensions (`PREDICATE_ALLOWLIST` / `PREDICATE_REGISTRY`)
- **Career & Appointments**: `holds_position`, `employed_by`, `based_in`.
- **Education & Qualifications**: `graduated_from`, `received_degree`. (Note: `received_degree` denotes degree type/qualification; `graduated_from` denotes institution; they are never globally conflated).
- **Affiliations & Memberships**: `affiliated_with`, `member_of`.
- **Honors & Recognition**: `awarded_honor` (canonical for `honored_with`, `received_award`).
- **Scholarship & Research Activities**: `authored_publication` (canonical for `authored_work`), `presented_paper` (canonical for `presented_work`), `conducted_research`, `researched_topic`, `participated_in`.

### Strictly Prohibited Categories (Out of Scope — Never Penalized)
The pipeline must **never** attempt to search for, extract, or score the following:
- Residential addresses and personal physical locations.
- Personal phone numbers and non-public personal email addresses.
- Family members, spousal relationships, or personal kinship.
- Personal health, medical, or genetic records.
- Credential leak dumps, dark web databases, or breached registries.
- Content behind authentication, paywalls, or CAPTCHA barriers.
- Biometric surveillance data (facial recognition, voiceprints).

---

## 3. Candidate Separation & Homonym Contamination Scope

To prevent conflation between target person precision and multi-candidate clustering:

1. **Target Claims vs. Alternate Candidate Claims**:
   - The primary candidate is designated via `dossier.primary_candidate_id` (default: `CAND-01`).
   - Claims with `candidate_id == primary_candidate_id` are **target claims** and are evaluated for target Precision and Recall against target Gold facts.
   - Claims assigned to other candidates (`CAND-02`, `CAND-03`, etc.) are **alternate candidate claims**. They represent legitimate homonyms or peripheral entities.
2. **Contamination Gating**:
   - Only annotated homonym facts incorrectly attributed to the **primary target candidate** constitute homonym contamination.
   - Homonym facts correctly assigned to alternate candidate clusters (`CAND-02`, etc.) demonstrate correct identity disambiguation and do **not** trigger contamination penalties.

---

## 4. Reference Gold Contract & 1-to-1 Maximum Bipartite Matching

When evaluating against reference sets:
- **Gold Reference Schema**:
  ```json
  {
    "target_name": "...",
    "primary_candidate_id": "CAND-01",
    "reference_completeness": "complete",
    "facts": [
      {
        "subject": "...",
        "predicate": "...",
        "object_raw": "...",
        "polarity": "affirmative",
        "temporal_status": "current"
      }
    ],
    "explicit_equivalence_sets": {},
    "annotated_homonyms": [],
    "gold_sha256": "..."
  }
  ```
- **1-to-1 Maximum Bipartite Matching**:
  - Evaluation of Recall and Precision uses maximum bipartite matching.
  - A single candidate claim can match at most one Gold fact.
  - A single Gold fact can be matched by at most one candidate claim.
- **Fail-Closed 5D Semantics**:
  - Subject: Must match target name.
  - Predicate: Must match canonical predicate.
  - Object: Strict normalized match or explicit gold equivalence set (`strict_object_match`). Bidirectional substring inclusion (`a in b or b in a`) is strictly forbidden.
  - Polarity: Exact match (`affirmative` / `negative`).
  - Temporal: Candidate claims with `unknown` / unspecified temporal status fail against specified Gold temporal statuses (`current`, `historical`).

---

## 5. Two-Track Operational Protocols

### Track A: Routine Investigation Execution Contract
When executing a live investigation for a named target (routine user task):
1. Produce a standard `InvestigationBundle` (`source_inventory.jsonl`, `raw_sources/`, `verified_claims.jsonl`, `corroborated_leads.jsonl`, `open_questions.jsonl`, `query_logs.jsonl`, `manifest.json`, `dossier.json`, `recall_report.md`).
2. Run end-to-end, verify byte closure via `BundleVerifier`, and deliver the dossier without requiring benchmark freezes or held-out validation for routine queries.

### Track B: Skill Code Iteration & Optimization Protocol
When modifying extractor, clustering, or collector code in `core/`:
1. Phase 0 (Baseline Execution) $\to$ Phase 1 (Diagnosis) $\to$ Human Review $\to$ Phase 2 (Generic Mechanism Patching) $\to$ Phase 3 (Replay & Held-Out Validation).
2. Max 2 remediation cycles per optimization task. If $\Delta \text{recall} < 0.05$, stop and emit an architectural analysis.
3. Evaluator and benchmark versions are locked per experiment. All tests must pass, and the Git working tree must be clean.

---

## 6. Required Acceptance Deliverables

Functional acceptance evaluation emits 4 machine-verifiable deliverables in a dedicated evaluation directory:
1. `run_receipt.json`: Candidate Git SHA, `git_dirty` boolean, evaluator SHA-256, gold SHA-256, gate decisions, query summary.
2. `coverage_matrix.json`: Matrix of in-scope predicates explored vs. covered, zero-violation privacy attestations.
3. `before_after_delta.json`: Fact-level delta against baseline ($\Delta \text{recall}$ strictly grounded in gold).
4. `recall_report.md`: Structured markdown report rendering recall, precision, byte replay closure, and remaining open questions.
