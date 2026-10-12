"""
Functional Acceptance Runner & Diagnostic Harness (V6.3 Architecture).

Evaluates person investigation runs against canonical InvestigationBundle artifacts:
1. Canonical InvestigationBundle Artifact Ingestion:
   (raw_sources/, source_inventory.jsonl, verified_claims.jsonl,
    corroborated_leads.jsonl, open_questions.jsonl, query_logs.jsonl,
    manifest.json, dossier.json, recall_report.md)
2. Substantive Byte Replay & File Closure:
   Directly integrates BundleVerifier to verify disk raw source byte hashes,
   recalculate SHA-256, and confirm verbatim excerpt replay in raw files.
3. Strict 5D Bipartite Maximum Matching:
   One-to-one maximum bipartite matching between target claims and reference gold facts.
   Fail-closed temporal and subject verification; strict normalized object matching with equivalence sets.
4. Candidate Partitioning & Scoped Homonym Contamination:
   Evaluates target precision/recall exclusively on primary_candidate_id claims.
   Only flags homonyms erroneously merged into primary_candidate_id as contamination.
5. Unified Predicate Ontology (V1.2.0):
   Normalizes and scores all legitimate investigation dimensions from PREDICATE_REGISTRY.
6. Honest Diagnostic / Acceptance State:
   Requires reference_completeness == 'complete', precision >= 0.95, and clean git tree.
   Without complete gold, runs in DIAGNOSTIC mode without issuing acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SKILL_ROOT = Path(__file__).resolve().parents[2]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from models.predicate_registry import (
    CANONICAL_PREDICATE_ALIASES,
    PREDICATE_ALLOWLIST,
    PREDICATE_REGISTRY,
    canonicalize_predicate,
)
from scripts.verify_investigation_bundle import BundleVerifier

# Strictly prohibited privacy categories per references/source-policy.md
PROHIBITED_PRIVACY_PATTERNS = [
    r"\b(?:residential|home)\s+(?:address|street|apt|apartment|suite)\b",
    r"\b(?:personal|private)\s+(?:phone|mobile|cell|telephone)\b",
    r"\b(?:spouse|wife|husband|married\s+to|son|daughter|children|father|mother)\b",
    r"\b(?:ssn|social\s+security\s+number|passport\s+number|driver'?s\s+license)\b",
    r"\b(?:medical\s+history|health\s+records?|clinical\s+diagnosis|blood\s+type|patient\s+records?)\b",
    r"\b(?:password|credential\s+leak|dark\s+web\s+dump|breached\s+db)\b",
    r"\b(?:biometric|face\s+recognition|voiceprint|retina\s+scan)\b",
]

PREDICATE_KEYWORD_PATTERNS: Dict[str, List[str]] = {
    "holds_position": ["professor", "fellow", "director", "chair", "position", "appointment", "scientist", "engineer", "faculty", "postdoc"],
    "employed_by": ["employed", "works for", "company", "firm", "institution", "organization"],
    "affiliated_with": ["yale", "university", "institute", "hospital", "center", "school", "department", "lab"],
    "received_degree": ["phd", "m.s.", "b.s.", "degree", "master", "doctor", "bachelor"],
    "graduated_from": ["graduated", "alumni", "alumnus", "university", "college"],
    "member_of": ["member", "fellow", "society", "association", "board", "committee"],
    "authored_publication": ["paper", "publication", "journal", "author", "authored", "conference", "pubmed", "doi"],
    "presented_paper": ["presented", "presentation", "session", "talk", "conference", "speaker"],
    "conducted_research": ["project", "program", "street view", "initiative", "study"],
    "researched_topic": ["topic", "theme", "environmental justice", "methodology", "screening tool"],
    "participated_in": ["workshop", "panel", "symposium", "seminar", "working group"],
    "awarded_honor": ["award", "honor", "fellowship", "prize", "grant", "scholarship"],
    "based_in": ["new haven", "connecticut", "california", "city", "location", "based"],
}


def get_git_commit(repo_dir: Path) -> Optional[str]:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


def is_git_dirty(repo_dir: Path) -> bool:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return bool(res.stdout.strip())
    except Exception:
        pass
    return False


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_bundle_digest(bundle_dir: Path) -> str:
    h = hashlib.sha256()
    tracked_files = [
        "source_inventory.jsonl",
        "verified_claims.jsonl",
        "corroborated_leads.jsonl",
        "open_questions.jsonl",
        "query_logs.jsonl",
        "dossier.json",
        "recall_report.md",
        "manifest.json",
    ]
    for fname in sorted(tracked_files):
        fpath = bundle_dir / fname
        if fpath.exists() and fpath.is_file():
            h.update(f"{fname}:{compute_file_sha256(fpath)}\n".encode())

    raw_dir = bundle_dir / "raw_sources"
    if raw_dir.exists() and raw_dir.is_dir():
        for rpath in sorted(raw_dir.glob("*")):
            if rpath.is_file() and not rpath.name.startswith("."):
                h.update(f"raw_sources/{rpath.name}:{compute_file_sha256(rpath)}\n".encode())

    return h.hexdigest()


def _normalize_match_text(value: str) -> str:
    """Normalize text for strict matching: NFKC casefold, strip punctuation."""
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def _normalize_temporal(temp_str: Optional[str]) -> str:
    """Normalize temporal semantics into canonical classes."""
    val = (temp_str or "").strip().lower()
    if val in ("current", "present", "active", "as_of_publication"):
        return "current"
    if val in ("historical", "past", "former", "alumni", "completed"):
        return "historical"
    if val in ("future", "stated_future", "upcoming"):
        return "stated_future"
    return "unknown"


def strict_object_match(extracted_object: str, gold_claim: Dict[str, Any]) -> bool:
    """
    Require exact normalized object identity or explicit gold equivalence set.
    Rejects bidirectional substring inclusion (e.g. 'MIT' in 'submitted').
    """
    extracted = _normalize_match_text(extracted_object)
    accepted = {
        _normalize_match_text(gold_claim.get("object_raw", "") or gold_claim.get("object", "")),
        *(
            _normalize_match_text(value)
            for value in gold_claim.get("equivalence_set", [])
        ),
    }
    accepted.discard("")
    return bool(extracted and extracted in accepted)


def check_5d_match(
    claim: Dict[str, Any],
    gold_fact: Dict[str, Any],
    target_name: Optional[str] = None,
) -> bool:
    """
    Strict 5D entailment matching (Fail-Closed):
    1. Subject: Must match target name.
    2. Predicate: Canonical predicate identity (no degree/graduation conflation).
    3. Object: Strict normalized match or explicit gold equivalence set.
    4. Polarity: Exact match.
    5. Temporal status: Candidate with unknown/missing temporal status fails against specified gold.
    """
    c_sub = claim.get("subject") or claim.get("subject_raw") or target_name or ""
    g_sub = gold_fact.get("subject") or target_name or ""
    if not c_sub or not g_sub:
        return False
    if _normalize_match_text(c_sub) != _normalize_match_text(g_sub):
        return False

    c_raw_pred = str(claim.get("predicate", "")).strip().lower()
    g_raw_pred = str(gold_fact.get("predicate", "")).strip().lower()
    c_canon = canonicalize_predicate(c_raw_pred) or c_raw_pred
    g_canon = canonicalize_predicate(g_raw_pred) or g_raw_pred
    if c_canon != g_canon:
        return False

    c_obj = str(claim.get("object") or claim.get("object_raw") or "").strip()
    if not strict_object_match(c_obj, gold_fact):
        return False

    c_pol = str(claim.get("polarity", "affirmative")).strip().lower()
    g_pol = str(gold_fact.get("polarity", "affirmative")).strip().lower()
    if c_pol != g_pol:
        return False

    c_temp_norm = _normalize_temporal(claim.get("temporal_status"))
    g_temp_norm = _normalize_temporal(gold_fact.get("temporal_status"))
    if g_temp_norm != "unknown":
        if c_temp_norm == "unknown" or c_temp_norm != g_temp_norm:
            return False

    return True


def maximum_bipartite_matching(adj: List[List[bool]]) -> Dict[int, int]:
    """
    Kuhn's algorithm for maximum cardinality bipartite matching.
    U: Gold facts (rows, size M)
    V: Candidate claims (cols, size N)
    adj[u][v] is True if candidate claim v entails gold fact u.
    Returns {u: v} mapping ensuring 1-to-1 matching.
    """
    if not adj or not adj[0]:
        return {}

    num_u = len(adj)
    num_v = len(adj[0])
    match_v = [-1] * num_v  # match_v[v] = u

    def dfs(u: int, visited: List[bool]) -> bool:
        for v in range(num_v):
            if adj[u][v] and not visited[v]:
                visited[v] = True
                if match_v[v] < 0 or dfs(match_v[v], visited):
                    match_v[v] = u
                    return True
        return False

    for u in range(num_u):
        visited = [False] * num_v
        dfs(u, visited)

    return {u: v for v, u in enumerate(match_v) if u >= 0}


def load_investigation_claims(bundle_dir: Path) -> List[Dict[str, Any]]:
    claims_file = bundle_dir / "verified_claims.jsonl"
    if not claims_file.exists():
        return []
    claims: List[Dict[str, Any]] = []
    with claims_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    claims.append(json.loads(line))
                except Exception:
                    continue
    return claims


def load_query_logs(bundle_dir: Path) -> List[Dict[str, Any]]:
    q_file = bundle_dir / "query_logs.jsonl"
    if not q_file.exists():
        return []
    queries: List[Dict[str, Any]] = []
    with q_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    queries.append(json.loads(line))
                except Exception:
                    continue
    return queries


def evaluate_structural_and_byte_replay(bundle_dir: Path) -> Dict[str, Any]:
    """
    Substantive Byte Replay & File Closure via BundleVerifier.
    Recalculates SHA-256 for all disk files in raw_sources/,
    verifies verbatim excerpt presence in raw payload bytes,
    and checks citation closure.
    """
    verifier = BundleVerifier(bundle_dir)
    audit_ok = verifier.audit_all()

    total_claims = len(verifier.claims)
    broken_claims: List[Dict[str, Any]] = []

    for err in verifier.errors:
        if "verbatim excerpt not replayable" in err or "cannot be resolved" in err or "missing source" in err:
            broken_claims.append({"error": err})

    replay_rate = 1.0
    if total_claims > 0:
        replay_rate = max(0.0, (total_claims - len(broken_claims)) / total_claims)
    elif not verifier.is_abstention:
        replay_rate = 0.0

    return {
        "structural_pass": audit_ok,
        "is_abstention": verifier.is_abstention,
        "total_sources_audited": len(verifier.sources),
        "total_claims_audited": total_claims,
        "total_leads_audited": len(verifier.leads),
        "broken_claim_count": len(broken_claims),
        "provenance_replay_rate": replay_rate,
        "replay_gate_pass": audit_ok and (replay_rate == 1.0),
        "verifier_errors": verifier.errors,
        "verifier_warnings": verifier.warnings,
        "verifier_info": verifier.info,
    }


def evaluate_profile_coverage(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluates coverage of allowlisted dimensions and privacy compliance."""
    dimension_claim_counts: Dict[str, int] = {p: 0 for p in PREDICATE_REGISTRY}
    privacy_violations: List[Dict[str, Any]] = []

    for c in claims:
        raw_pred = str(c.get("predicate", "")).strip().lower()
        pred = canonicalize_predicate(raw_pred) or raw_pred
        obj = str(c.get("object") or c.get("object_raw") or "")
        sub = str(c.get("subject") or "")
        exc = str(c.get("verbatim_excerpt") or "")
        cid = c.get("claim_id", "unknown")

        if pred in dimension_claim_counts:
            dimension_claim_counts[pred] += 1

        full_claim_text = f"{sub} {raw_pred} {obj} {exc}"
        for pat in PROHIBITED_PRIVACY_PATTERNS:
            if re.search(pat, full_claim_text, re.IGNORECASE):
                privacy_violations.append({
                    "claim_id": cid,
                    "predicate": raw_pred,
                    "pattern": pat,
                    "snippet": full_claim_text[:120],
                })

    covered = [p for p, count in dimension_claim_counts.items() if count > 0]
    uncovered = [p for p, count in dimension_claim_counts.items() if count == 0]
    total_dims = len(PREDICATE_REGISTRY)
    cov_ratio = len(covered) / total_dims if total_dims > 0 else 0.0

    return {
        "total_in_scope_dimensions": total_dims,
        "covered_dimensions_count": len(covered),
        "covered_dimensions": covered,
        "uncovered_dimensions": uncovered,
        "dimension_counts": dimension_claim_counts,
        "coverage_ratio": cov_ratio,
        "privacy_violations": privacy_violations,
        "privacy_gate_pass": len(privacy_violations) == 0,
    }


def evaluate_query_saturation(
    bundle_dir: Path,
    manifest_data: Dict[str, Any],
    total_claims: int,
) -> Dict[str, Any]:
    """Parses executed query logs and analyzes yield curves."""
    q_logs = load_query_logs(bundle_dir)
    query_count = len(q_logs)
    if query_count == 0:
        query_count = manifest_data.get("queries_executed", 0)

    query_budget = manifest_data.get("query_budget", 20)
    budget_utilization = query_count / query_budget if query_budget > 0 else 1.0
    yield_per_query = total_claims / query_count if query_count > 0 else 0.0

    diminishing_returns = (query_count >= query_budget and yield_per_query < 0.5)

    return {
        "query_count": query_count,
        "query_budget": query_budget,
        "budget_utilization": budget_utilization,
        "total_claims": total_claims,
        "claims_per_query": yield_per_query,
        "diminishing_returns": diminishing_returns,
        "saturation_status": "exhausted" if budget_utilization >= 1.0 else "normal",
        "sample_queries": [q.get("query_text", "") for q in q_logs[:5]],
    }


def evaluate_withheld_gold(
    all_claims: List[Dict[str, Any]],
    withheld_gold_facts: List[Dict[str, Any]],
    primary_candidate_id: str = "CAND-01",
    reference_completeness: str = "complete",
    annotated_homonyms: Optional[List[Dict[str, Any]]] = None,
    target_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates 1-to-1 maximum bipartite matching, candidate partitioning,
    and scoped homonym contamination.
    """
    annotated_homonyms = annotated_homonyms or []

    # 1. Candidate Partitioning
    target_claims = [c for c in all_claims if c.get("candidate_id") == primary_candidate_id]
    alternate_claims = [c for c in all_claims if c.get("candidate_id") != primary_candidate_id]

    # 2. Scoped Homonym Contamination Audit
    # Contamination is ONLY flagged if a homonym fact is erroneously merged into primary_candidate_id!
    contaminated_claims: List[Dict[str, Any]] = []
    isolated_homonym_claims: List[Dict[str, Any]] = []

    for c in target_claims:
        for hom in annotated_homonyms:
            if check_5d_match(c, hom, target_name=target_name):
                contaminated_claims.append({
                    "claim_id": c.get("claim_id"),
                    "matched_homonym": hom.get("homonym_entity") or hom.get("subject"),
                    "predicate": c.get("predicate"),
                    "object": c.get("object") or c.get("object_raw"),
                })
                break

    for c in alternate_claims:
        for hom in annotated_homonyms:
            if check_5d_match(c, hom, target_name=target_name):
                isolated_homonym_claims.append({
                    "claim_id": c.get("claim_id"),
                    "candidate_id": c.get("candidate_id"),
                    "matched_homonym": hom.get("homonym_entity") or hom.get("subject"),
                })
                break

    if not withheld_gold_facts:
        return {
            "has_withheld_gold": False,
            "status": "UNVERIFIED_WITHOUT_GOLD",
            "reference_completeness": reference_completeness,
            "primary_candidate_id": primary_candidate_id,
            "target_claim_count": len(target_claims),
            "alternate_claim_count": len(alternate_claims),
            "withheld_fact_count": 0,
            "matched_facts": 0,
            "withheld_fact_recall": None,
            "verified_claim_precision": None,
            "contamination_count": len(contaminated_claims),
            "contaminated_claims": contaminated_claims,
            "isolated_homonym_count": len(isolated_homonym_claims),
            "contamination_gate_pass": len(contaminated_claims) == 0,
        }

    # 3. Build Adjacency Matrix for 1-to-1 Bipartite Matching on Target Claims
    num_gold = len(withheld_gold_facts)
    num_target = len(target_claims)
    adj: List[List[bool]] = [[False] * num_target for _ in range(num_gold)]

    for g_idx, gf in enumerate(withheld_gold_facts):
        for c_idx, tc in enumerate(target_claims):
            adj[g_idx][c_idx] = check_5d_match(tc, gf, target_name=target_name)

    matching = maximum_bipartite_matching(adj)
    matched_count = len(matching)

    recall = matched_count / num_gold if num_gold > 0 else 0.0

    # Strict contract: Precision is ONLY computed if reference_completeness == 'complete'
    if reference_completeness == "complete":
        precision = matched_count / num_target if num_target > 0 else 0.0
    else:
        precision = None

    return {
        "has_withheld_gold": True,
        "status": "EVALUATED_WITH_GOLD" if reference_completeness == "complete" else "PARTIAL_REFERENCE_GOLD",
        "reference_completeness": reference_completeness,
        "primary_candidate_id": primary_candidate_id,
        "target_claim_count": num_target,
        "alternate_claim_count": len(alternate_claims),
        "withheld_fact_count": num_gold,
        "matched_facts": matched_count,
        "withheld_fact_recall": recall,
        "verified_claim_precision": precision,
        "contamination_count": len(contaminated_claims),
        "contaminated_claims": contaminated_claims,
        "isolated_homonym_count": len(isolated_homonym_claims),
        "contamination_gate_pass": len(contaminated_claims) == 0,
        "matching_pairs": [{"gold_idx": g, "claim_idx": c, "claim_id": target_claims[c].get("claim_id")} for g, c in matching.items()],
    }


def classify_omissions_and_failures(
    uncovered_dimensions: List[str],
    query_logs: List[Dict[str, Any]],
    manifest_data: Dict[str, Any],
    verifier_errors: List[str],
) -> List[Dict[str, Any]]:
    """Attributes failures to query formulation, retrieval, or byte grounding."""
    failures: List[Dict[str, Any]] = []

    for err in verifier_errors:
        if "verbatim excerpt not replayable" in err:
            failures.append({
                "target": "evidence_grounding",
                "failure_category": "REPLAY_FAILED",
                "explanation": err,
            })
        elif "SHA-256 mismatch" in err:
            failures.append({
                "target": "source_byte_integrity",
                "failure_category": "BYTE_TAMPER_DETECTED",
                "explanation": err,
            })

    queries_text = " ".join([q.get("query_text", "").lower() for q in query_logs])
    budget = manifest_data.get("query_budget", 20)
    queries_run = len(query_logs)

    for dim in uncovered_dimensions:
        keywords = PREDICATE_KEYWORD_PATTERNS.get(dim, [])
        query_targeted = any(kw in queries_text for kw in keywords)

        if not query_targeted:
            cat = "QUERY_FORMULATION_OMISSION"
            expl = f"No search queries formulated terms targeting '{dim}'."
        elif queries_run >= budget:
            cat = "QUERY_BUDGET_SATURATED"
            expl = f"Queries targeting '{dim}' attempted, but budget ({budget}) was exhausted."
        else:
            cat = "DISCOVERY_UNRETRIEVED"
            expl = f"Queries targeting '{dim}' executed, but returned no extractable documents."

        failures.append({
            "target": f"dimension:{dim}",
            "failure_category": cat,
            "explanation": expl,
        })

    return failures


def compute_before_after_delta(
    baseline_claims: List[Dict[str, Any]],
    candidate_claims: List[Dict[str, Any]],
    baseline_gold_eval: Optional[Dict[str, Any]] = None,
    candidate_gold_eval: Optional[Dict[str, Any]] = None,
    delta_min: float = 0.05,
) -> Dict[str, Any]:
    """
    Computes delta comparison.
    Contract Rule: Never substitute raw claim counts for recall!
    """
    base_sig_set = {
        (c.get("predicate"), _normalize_match_text(str(c.get("object") or c.get("object_raw"))))
        for c in baseline_claims
    }
    cand_sig_set = {
        (c.get("predicate"), _normalize_match_text(str(c.get("object") or c.get("object_raw"))))
        for c in candidate_claims
    }

    retained = base_sig_set.intersection(cand_sig_set)
    added = cand_sig_set.difference(base_sig_set)
    lost = base_sig_set.difference(cand_sig_set)

    b_recall = baseline_gold_eval.get("withheld_fact_recall") if baseline_gold_eval else None
    c_recall = candidate_gold_eval.get("withheld_fact_recall") if candidate_gold_eval else None

    b_prec = baseline_gold_eval.get("verified_claim_precision") if baseline_gold_eval else None
    c_prec = candidate_gold_eval.get("verified_claim_precision") if candidate_gold_eval else None

    delta_recall = (c_recall - b_recall) if (b_recall is not None and c_recall is not None) else None
    delta_prec = (c_prec - b_prec) if (b_prec is not None and c_prec is not None) else None

    if delta_recall is not None:
        meets_threshold = delta_recall >= delta_min
        delta_status = "EVALUATED_AGAINST_GOLD"
    else:
        meets_threshold = False
        delta_status = "UNVERIFIED_WITHOUT_GOLD"

    return {
        "status": delta_status,
        "baseline_claim_count": len(baseline_claims),
        "candidate_claim_count": len(candidate_claims),
        "retained_claims_count": len(retained),
        "new_claims_count": len(added),
        "lost_claims_count": len(lost),
        "net_claim_count_delta": len(added) - len(lost),
        "baseline_recall": b_recall,
        "candidate_recall": c_recall,
        "delta_recall": delta_recall,
        "baseline_precision": b_prec,
        "candidate_precision": c_prec,
        "delta_precision": delta_prec,
        "delta_min_threshold": delta_min,
        "meets_improvement_threshold": meets_threshold,
    }


def render_markdown_report(results: Dict[str, Any]) -> str:
    cov = results["coverage_matrix"]
    rep = results["byte_replay"]
    sat = results["query_saturation"]
    gold = results["withheld_gold"]
    delta = results.get("before_after_delta")
    gates = results["gates"]

    lines = [
        "# Investigation Bundle — Functional Acceptance & Diagnostic Report",
        "",
        f"**Run Timestamp (UTC)**: {results['timestamp_utc']}  ",
        f"**Candidate Bundle**: `{results['candidate_bundle_dir']}`  ",
        f"**Candidate Git SHA**: `{results.get('candidate_commit', 'unknown')}`  ",
        f"**Git Dirty**: `{'YES' if results.get('git_dirty') else 'NO'}`  ",
        f"**Evaluator SHA-256**: `{results.get('evaluator_sha256', 'unknown')[:16]}...`  ",
        f"**Bundle Digest**: `{results['bundle_digest_sha256']}`  ",
        "",
        "---",
        "",
        "## 1. Executive Gate Decisions",
        "",
        "| Gate | Requirement | Measured | Status |",
        "| :--- | :--- | :--- | :---: |",
        f"| **Structural Validation** | BundleVerifier audit passes | {rep['total_sources_audited']} sources, {rep['total_claims_audited']} claims | {'✅ PASS' if gates['structural_validation_pass'] else '❌ FAIL'} |",
        f"| **Privacy Compliance** | Zero prohibited category violations | {len(cov['privacy_violations'])} violations | {'✅ PASS' if gates['privacy_gate_pass'] else '❌ FAIL'} |",
        f"| **Substantive Byte Replay** | 100% trace to source bytes on disk | {rep['provenance_replay_rate']*100:.1f}% ({rep['broken_claim_count']} broken) | {'✅ PASS' if gates['provenance_replay_pass'] else '❌ FAIL'} |",
        f"| **Homonym Contamination** | 0 false merges in primary candidate | {gold['contamination_count']} false merges ({gold['isolated_homonym_count']} isolated) | {'✅ PASS' if gates['homonym_contamination_pass'] else '❌ FAIL'} |",
        f"| **Git Working Tree Clean** | Clean tree without unstaged edits | {'Clean' if gates['git_clean_gate_pass'] else 'Dirty'} | {'✅ PASS' if gates['git_clean_gate_pass'] else '❌ FAIL'} |",
    ]

    if gold.get("has_withheld_gold"):
        if gold.get("reference_completeness") == "complete":
            lines.append(
                f"| **Precision Floor** | >= {results['precision_floor']:.2f} | {gold['verified_claim_precision']:.3f} | {'✅ PASS' if gates['precision_floor_pass'] else '❌ FAIL'} |"
            )
        else:
            lines.append(
                "| **Precision Floor** | >= 0.95 (complete gold required) | N/A (Partial Gold) | ⚠️ UNVERIFIED |"
            )
        lines.append(
            f"| **Target Recall Floor** | >= {results['min_recall']:.2f} | {gold['withheld_fact_recall']:.3f} ({gold['matched_facts']}/{gold['withheld_fact_count']}) | {'✅ PASS' if gates['recall_gate_pass'] else '❌ FAIL'} |"
        )
    else:
        lines.append(
            "| **Acceptance Certification** | Requires complete reference gold | None provided (DIAGNOSTIC MODE) | ⚠️ UNVERIFIED |"
        )

    lines.extend([
        "",
        f"**Overall Functional Acceptance**: {'✅ ACCEPTED' if gates['overall_acceptance_pass'] else '❌ BLOCKED / DIAGNOSTIC'}",
        "",
        "---",
        "",
        "## 2. In-Scope Profile Dimension Coverage (Predicate Registry V1.2.0)",
        "",
        f"- **Coverage Ratio**: {cov['covered_dimensions_count']} / {cov['total_in_scope_dimensions']} ({cov['coverage_ratio']*100:.1f}%)",
        f"- **Covered Dimensions**: {', '.join(cov['covered_dimensions']) if cov['covered_dimensions'] else 'None'}",
        f"- **Uncovered Dimensions**: {', '.join(cov['uncovered_dimensions']) if cov['uncovered_dimensions'] else 'None'}",
        "",
        "---",
        "",
        "## 3. Query Saturation & Marginal Yield",
        "",
        f"- **Queries Executed**: {sat['query_count']} / {sat['query_budget']} (Utilization: {sat['budget_utilization']*100:.1f}%)",
        f"- **Verified Claims**: {sat['total_claims']} (Target: {gold['target_claim_count']}, Alternate: {gold['alternate_claim_count']})",
        f"- **Yield per Query**: {sat['claims_per_query']:.2f}",
        f"- **Diminishing Returns Detected**: {'Yes' if sat['diminishing_returns'] else 'No'}",
        "",
        "---",
        "",
        "## 4. Failure Attribution",
        "",
    ])

    failures = results.get("failures", [])
    if failures:
        lines.append("| Target | Category | Explanation |")
        lines.append("| :--- | :--- | :--- |")
        for f in failures:
            lines.append(f"| `{f['target']}` | `{f['failure_category']}` | {f['explanation']} |")
    else:
        lines.append("No failures recorded.")

    if delta:
        lines.extend([
            "",
            "---",
            "",
            "## 5. Before / After Delta Analysis",
            "",
            f"- **Status**: `{delta['status']}`",
            f"- **Baseline Claims**: {delta['baseline_claim_count']} -> **Candidate Claims**: {delta['candidate_claim_count']}",
            f"- **Retained**: {delta['retained_claims_count']} | **New**: {delta['new_claims_count']} | **Lost**: {delta['lost_claims_count']}",
        ])
        if delta.get("delta_recall") is not None:
            lines.append(f"- **Delta Recall**: {delta['delta_recall']:+.3f}")
            lines.append(
                f"- **Meets Improvement Threshold (δ >= {delta['delta_min_threshold']})**: {'✅ YES' if delta['meets_improvement_threshold'] else '❌ NO'}"
            )
        else:
            lines.append("- **Recall Delta**: N/A (Withheld gold required to certify improvement)")

    lines.append("")
    return "\n".join(lines)


def run_functional_acceptance(
    candidate_bundle_dir: Path,
    evaluate_existing: bool = True,
    name: Optional[str] = None,
    clue: Optional[str] = None,
    additional_clues: Optional[List[str]] = None,
    query_budget: int = 20,
    baseline_bundle_dir: Optional[Path] = None,
    withheld_gold_path: Optional[Path] = None,
    annotated_homonyms_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    precision_floor: float = 0.95,
    min_recall: float = 0.80,
    delta_min: float = 0.05,
    enforce_git_clean: bool = True,
) -> Dict[str, Any]:
    """
    Executes functional acceptance evaluation against an InvestigationBundle.
    """
    target_out = output_dir or (candidate_bundle_dir.parent / f"{candidate_bundle_dir.name}_eval")
    target_out.mkdir(parents=True, exist_ok=True)

    # 1. Live execution mode if requested on clean directory
    if not evaluate_existing:
        if not name:
            raise ValueError("Target --name required for live execution mode.")
        from scripts.run_recall_profile import run_recall_investigation
        candidate_bundle_dir = run_recall_investigation(
            name=name,
            clue=clue or "",
            additional_clues=additional_clues or [],
            output_dir=candidate_bundle_dir,
            query_budget=query_budget,
            discover_live=True,
        )

    if not candidate_bundle_dir.exists():
        raise FileNotFoundError(f"Candidate bundle dir not found: {candidate_bundle_dir}")

    # 2. Substantive Byte Replay & File Closure Audit
    replay_eval = evaluate_structural_and_byte_replay(candidate_bundle_dir)

    # 3. Ingest Claims, Inventory, Manifest, Dossier
    claims = load_investigation_claims(candidate_bundle_dir)
    manifest_file = candidate_bundle_dir / "manifest.json"
    manifest_data = {}
    if manifest_file.exists():
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    dossier_file = candidate_bundle_dir / "dossier.json"
    dossier_data = {}
    if dossier_file.exists():
        try:
            dossier_data = json.loads(dossier_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Determine primary_candidate_id
    primary_candidate_id = dossier_data.get("primary_candidate_id") or manifest_data.get("primary_candidate_id") or "CAND-01"
    target_name = name or dossier_data.get("target_name") or manifest_data.get("target_name")

    # 4. Profile Dimension Coverage & Privacy
    cov_eval = evaluate_profile_coverage(claims)

    # 5. Query Saturation Analysis
    sat_eval = evaluate_query_saturation(candidate_bundle_dir, manifest_data, len(claims))

    # 6. Withheld Reference Gold & Homonyms
    annotated_homonyms: List[Dict[str, Any]] = []
    homonym_set_sha256 = None
    if annotated_homonyms_path and annotated_homonyms_path.exists():
        homonym_set_sha256 = compute_file_sha256(annotated_homonyms_path)
        loaded_h = json.loads(annotated_homonyms_path.read_text(encoding="utf-8"))
        annotated_homonyms = loaded_h.get("homonyms", loaded_h) if isinstance(loaded_h, dict) else loaded_h

    withheld_gold_facts: List[Dict[str, Any]] = []
    reference_completeness = "complete"
    gold_sha256 = None
    if withheld_gold_path and withheld_gold_path.exists():
        gold_sha256 = compute_file_sha256(withheld_gold_path)
        loaded = json.loads(withheld_gold_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            withheld_gold_facts = loaded.get("facts", [])
            reference_completeness = loaded.get("reference_completeness", "complete")
            if "primary_candidate_id" in loaded:
                primary_candidate_id = loaded["primary_candidate_id"]
            if not annotated_homonyms and "annotated_homonyms" in loaded:
                annotated_homonyms = loaded["annotated_homonyms"]
        elif isinstance(loaded, list):
            withheld_gold_facts = loaded

    gold_eval = evaluate_withheld_gold(
        all_claims=claims,
        withheld_gold_facts=withheld_gold_facts,
        primary_candidate_id=primary_candidate_id,
        reference_completeness=reference_completeness,
        annotated_homonyms=annotated_homonyms,
        target_name=target_name,
    )

    # 7. Query Logs & Failure Classification
    q_logs = load_query_logs(candidate_bundle_dir)
    failures = classify_omissions_and_failures(
        cov_eval["uncovered_dimensions"], q_logs, manifest_data, replay_eval["verifier_errors"]
    )

    # 8. Before / After Delta
    delta_eval = None
    if baseline_bundle_dir and baseline_bundle_dir.exists():
        base_claims = load_investigation_claims(baseline_bundle_dir)
        base_gold = evaluate_withheld_gold(
            all_claims=base_claims,
            withheld_gold_facts=withheld_gold_facts,
            primary_candidate_id=primary_candidate_id,
            reference_completeness=reference_completeness,
            annotated_homonyms=annotated_homonyms,
            target_name=target_name,
        )
        delta_eval = compute_before_after_delta(
            baseline_claims=base_claims,
            candidate_claims=claims,
            baseline_gold_eval=base_gold,
            candidate_gold_eval=gold_eval,
            delta_min=delta_min,
        )

    # 9. Gate Synthesis
    struct_pass = replay_eval["structural_pass"]
    privacy_pass = cov_eval["privacy_gate_pass"]
    replay_pass = replay_eval["replay_gate_pass"]
    contam_pass = gold_eval["contamination_gate_pass"]
    has_gold = gold_eval["has_withheld_gold"]
    is_complete_gold = has_gold and (reference_completeness == "complete")

    prec_pass = (
        gold_eval["verified_claim_precision"] >= precision_floor
        if is_complete_gold and gold_eval["verified_claim_precision"] is not None
        else None
    )
    recall_pass = (
        gold_eval["withheld_fact_recall"] >= min_recall
        if has_gold and gold_eval["withheld_fact_recall"] is not None
        else None
    )
    claim_count_pass = len(claims) > 0 or replay_eval["is_abstention"]

    # Git tree cleanliness
    git_dirty_flag = is_git_dirty(candidate_bundle_dir) or is_git_dirty(SKILL_ROOT)
    git_clean_pass = (not git_dirty_flag) if enforce_git_clean else True

    # Hard acceptance decision:
    overall_acceptance_pass = bool(
        is_complete_gold
        and struct_pass
        and privacy_pass
        and replay_pass
        and contam_pass
        and claim_count_pass
        and git_clean_pass
        and (prec_pass is True)
        and (recall_pass is True)
    )

    gates = {
        "structural_validation_pass": struct_pass,
        "privacy_gate_pass": privacy_pass,
        "provenance_replay_pass": replay_pass,
        "homonym_contamination_pass": contam_pass,
        "claim_count_gate_pass": claim_count_pass,
        "git_clean_gate_pass": git_clean_pass,
        "precision_floor_pass": prec_pass,
        "recall_gate_pass": recall_pass,
        "overall_acceptance_pass": overall_acceptance_pass,
        "mode": "ACCEPTANCE" if is_complete_gold else "DIAGNOSTIC",
    }

    evaluator_path = Path(__file__).resolve()
    evaluator_sha256 = compute_file_sha256(evaluator_path) if evaluator_path.exists() else None

    results: Dict[str, Any] = {
        "suite_id": "functional_acceptance_v6_3",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_bundle_dir": str(candidate_bundle_dir.resolve()),
        "candidate_commit": get_git_commit(candidate_bundle_dir) or get_git_commit(SKILL_ROOT),
        "git_dirty": git_dirty_flag,
        "evaluator_sha256": evaluator_sha256,
        "gold_sha256": gold_sha256,
        "homonym_set_sha256": homonym_set_sha256,
        "bundle_digest_sha256": compute_bundle_digest(candidate_bundle_dir),
        "precision_floor": precision_floor,
        "min_recall": min_recall,
        "delta_min": delta_min,
        "gates": gates,
        "byte_replay": replay_eval,
        "coverage_matrix": cov_eval,
        "query_saturation": sat_eval,
        "withheld_gold": gold_eval,
        "failures": failures,
        "before_after_delta": delta_eval,
    }

    # 10. Write Deliverables
    receipt_data = {
        "suite_id": results["suite_id"],
        "timestamp_utc": results["timestamp_utc"],
        "candidate_commit": results["candidate_commit"],
        "git_dirty": results["git_dirty"],
        "evaluator_sha256": results["evaluator_sha256"],
        "gold_sha256": results["gold_sha256"],
        "homonym_set_sha256": results["homonym_set_sha256"],
        "bundle_digest_sha256": results["bundle_digest_sha256"],
        "primary_candidate_id": primary_candidate_id,
        "gates": gates,
        "thresholds": {
            "precision_floor": precision_floor,
            "min_recall": min_recall,
            "delta_min": delta_min,
        },
        "metrics": {
            "total_claims": len(claims),
            "target_claims": gold_eval["target_claim_count"],
            "alternate_claims": gold_eval["alternate_claim_count"],
            "dimension_coverage_ratio": cov_eval["coverage_ratio"],
            "provenance_replay_rate": replay_eval["provenance_replay_rate"],
            "withheld_fact_recall": gold_eval["withheld_fact_recall"],
            "verified_claim_precision": gold_eval["verified_claim_precision"],
            "contamination_count": gold_eval["contamination_count"],
        },
        "query_summary": {
            "queries_executed": sat_eval["query_count"],
            "query_budget": sat_eval["query_budget"],
            "claims_per_query": sat_eval["claims_per_query"],
        },
    }
    (target_out / "run_receipt.json").write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")
    (target_out / "coverage_matrix.json").write_text(json.dumps(cov_eval, indent=2), encoding="utf-8")
    (target_out / "before_after_delta.json").write_text(
        json.dumps(delta_eval or {"status": "NO_BASELINE_PROVIDED"}, indent=2), encoding="utf-8"
    )
    (target_out / "recall_report.md").write_text(render_markdown_report(results), encoding="utf-8")

    return results


def main():
    parser = argparse.ArgumentParser(description="Investigation Bundle Functional Acceptance Runner")
    parser.add_argument("--candidate-dir", type=Path, required=True, help="Candidate InvestigationBundle dir")
    parser.add_argument("--evaluate-existing", action="store_true", default=True, help="Evaluate existing bundle")
    parser.add_argument("--live", action="store_true", default=False, help="Run live investigation from empty directory")
    parser.add_argument("--name", type=str, default=None, help="Target person name for live investigation")
    parser.add_argument("--clue", type=str, default=None, help="Primary search clue for live mode")
    parser.add_argument("--additional-clues", type=str, nargs="*", default=[], help="Additional search clues")
    parser.add_argument("--baseline-dir", type=Path, default=None, help="Optional baseline bundle dir for delta")
    parser.add_argument("--withheld-gold", type=Path, default=None, help="Withheld gold facts JSON")
    parser.add_argument("--annotated-homonyms", type=Path, default=None, help="Annotated homonyms JSON")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for reports")
    parser.add_argument("--precision-floor", type=float, default=0.95, help="Minimum precision floor (default: 0.95)")
    parser.add_argument("--min-recall", type=float, default=0.80, help="Minimum recall floor (default: 0.80)")
    parser.add_argument("--delta-min", type=float, default=0.05, help="Minimum recall delta threshold (default: 0.05)")
    parser.add_argument("--allow-diagnostic", action="store_true", default=False, help="Allow exit 0 for diagnostic runs without gold")
    parser.add_argument("--ignore-git-dirty", action="store_true", default=False, help="Allow running evaluation on dirty git tree")
    parser.add_argument("--json", action="store_true", default=False, help="Print summary JSON to stdout")
    args = parser.parse_args()

    eval_existing = not args.live

    results = run_functional_acceptance(
        candidate_bundle_dir=args.candidate_dir,
        evaluate_existing=eval_existing,
        name=args.name,
        clue=args.clue,
        additional_clues=args.additional_clues,
        baseline_bundle_dir=args.baseline_dir,
        withheld_gold_path=args.withheld_gold,
        annotated_homonyms_path=args.annotated_homonyms,
        output_dir=args.output_dir,
        precision_floor=args.precision_floor,
        min_recall=args.min_recall,
        delta_min=args.delta_min,
        enforce_git_clean=not args.ignore_git_dirty,
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        gates = results["gates"]
        print("=" * 60)
        print("INVESTIGATION ACCEPTANCE & DIAGNOSTIC RESULT")
        print("=" * 60)
        print(f"Mode:                  {gates['mode']}")
        print(f"Structural Validation: {'PASS' if gates['structural_validation_pass'] else 'FAIL'}")
        print(f"Privacy Compliance:    {'PASS' if gates['privacy_gate_pass'] else 'FAIL'}")
        print(f"Byte Provenance Replay:{'PASS' if gates['provenance_replay_pass'] else 'FAIL'}")
        print(f"Homonym Contamination: {'PASS' if gates['homonym_contamination_pass'] else 'FAIL'}")
        print(f"Claim Count Gate:      {'PASS' if gates['claim_count_gate_pass'] else 'FAIL'}")
        print(f"Git Clean Gate:        {'PASS' if gates['git_clean_gate_pass'] else 'FAIL'}")
        if gates.get("precision_floor_pass") is not None:
            print(f"Precision Floor Gate:  {'PASS' if gates['precision_floor_pass'] else 'FAIL'}")
        if gates.get("recall_gate_pass") is not None:
            print(f"Target Recall Gate:    {'PASS' if gates['recall_gate_pass'] else 'FAIL'}")
        print("-" * 60)
        print(f"Overall Acceptance:    {'PASS' if gates['overall_acceptance_pass'] else 'BLOCKED / DIAGNOSTIC'}")
        print("=" * 60)

    overall_pass = results["gates"]["overall_acceptance_pass"]
    if overall_pass:
        sys.exit(0)

    if args.allow_diagnostic and results["gates"]["mode"] == "DIAGNOSTIC":
        diagnostic_pass = (
            results["gates"]["structural_validation_pass"]
            and results["gates"]["privacy_gate_pass"]
            and results["gates"]["provenance_replay_pass"]
            and results["gates"]["claim_count_gate_pass"]
        )
        sys.exit(0 if diagnostic_pass else 1)

    sys.exit(1)


if __name__ == "__main__":
    main()
