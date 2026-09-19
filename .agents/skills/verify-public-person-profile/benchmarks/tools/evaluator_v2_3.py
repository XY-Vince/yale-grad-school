"""
Blind Evaluation Protocol v1.3 - Evaluator V2.3 (Strict Contract & Audit Engine).
Key Upgrades over V2.2:
1. Zero False Released Claims:
   - Eliminates statistical blind spot by defining:
     false_released_claims = released_claims_count - tp_5d
   - Enforces zero_false_released_claims_gate across all cases (completed and abstained).
2. Paired Input Identity Gate (paired_input_identity_gate):
   - When paired runs directory (e.g. Group 2 vs Group 3) is provided, verifies that
     sources, evidence, mentions, candidates, and clusters are byte/semantic identical
     after stripping dynamic timestamps.
3. Provenance and Integrity Hashing:
   - Injects git_commit_sha, git_dirty, evaluator_sha256, gold_sha256, warc_sha256,
     and query_index_sha256 into execution metadata.
4. Programmatic Markdown Audit Generation:
   - render_markdown_report() automatically generates objective audit reports
     directly from evaluation JSON without subjective narrative drift.
5. Strict Gold Contract & Fail-Closed Integrity:
   - Uses strict Pydantic GoldSuite validation.
   - Rejects missing evidence references, duplicate mention signatures, and tampered Merkle seals.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

# Resolve skill root relative to this file
SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from benchmarks.tools.er_metrics import compute_b3, compute_pairwise
from models.gold_schema_v2 import GoldCase, GoldSuite
from scripts.validate_dossier import validate_bundle

REQUIRED_BUNDLE_FILES = [
    "manifest.json",
    "sources.jsonl",
    "mentions.jsonl",
    "candidates.jsonl",
    "claims.jsonl",
    "dossier.json",
    "evidence.jsonl",
]

PAIR_COMPARISON_FILES = [
    "sources.jsonl",
    "evidence.jsonl",
    "mentions.jsonl",
    "candidates.jsonl",
    "clusters.jsonl",
]


def compute_file_sha256(path: Path) -> str:
    """Computes standard SHA-256 digest of a file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def compute_bundle_tree_hash(bundle_dir: Path) -> str:
    """Computes deterministic Merkle tree root hash of all files in bundle_dir, excluding seal.json."""
    files = sorted([p for p in bundle_dir.rglob("*") if p.is_file() and p.name != "seal.json" and not p.name.startswith(".")])
    h = hashlib.sha256()
    for f in files:
        rel_path = f.relative_to(bundle_dir).as_posix()
        file_sha = hashlib.sha256(f.read_bytes()).hexdigest()
        h.update(f"{rel_path}:{file_sha}".encode("utf-8"))
    return h.hexdigest()


def get_git_provenance() -> Tuple[str, bool]:
    """Retrieves current git commit hash and dirty status."""
    try:
        commit_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = commit_proc.stdout.strip()

        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        is_dirty = bool(status_proc.stdout.strip())
        return commit_sha, is_dirty
    except Exception:
        return "unknown", True


def normalize_text(val: str) -> str:
    s = unicodedata.normalize("NFKC", val or "").strip().lower()
    return re.sub(r"\s+", " ", s)


def make_mention_sig(source_sha256: str, span_start: int, span_end: int, text: str) -> str:
    norm_t = normalize_text(text)
    return f"{source_sha256}:{span_start}_{span_end}:{norm_t}"


def parse_warc_payload_shas(warc_path: Path) -> Set[str]:
    """Extracts raw HTTP response payload SHA-256 hashes from standard WARC file."""
    if not warc_path.exists():
        raise FileNotFoundError(f"WARC file not found: {warc_path}")

    data = warc_path.read_bytes()
    shas = set()
    idx = 0
    total_len = len(data)

    while idx < total_len:
        while idx < total_len and data[idx:idx+1] in (b"\r", b"\n", b" ", b"\t"):
            idx += 1
        if idx >= total_len:
            break
        if not data[idx:].startswith(b"WARC/"):
            next_warc = data.find(b"WARC/", idx)
            if next_warc == -1:
                break
            idx = next_warc

        header_end = data.find(b"\r\n\r\n", idx)
        if header_end == -1:
            header_end = data.find(b"\n\n", idx)
            if header_end == -1:
                break
            payload_start = header_end + 2
        else:
            payload_start = header_end + 4

        header_bytes = data[idx:header_end]
        warc_headers = {}
        for line in header_bytes.decode("latin-1", errors="ignore").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                warc_headers[k.strip().lower()] = v.strip()

        content_len = int(warc_headers.get("content-length", 0))
        payload_bytes = data[payload_start:payload_start + content_len]
        idx = payload_start + content_len

        if warc_headers.get("warc-type", "").lower() == "response":
            http_parts = payload_bytes.split(b"\r\n\r\n", 1)
            html_payload = http_parts[1] if len(http_parts) > 1 else b""
            shas.add(hashlib.sha256(html_payload).hexdigest())

    return shas


def verify_gold_warc_integrity(gold_suite: GoldSuite, warc_path: Path):
    """Verifies that all source_content_sha256 in Gold mentions exist in the WARC archive."""
    warc_shas = parse_warc_payload_shas(warc_path)
    missing = []
    for case in gold_suite:
        for gm in case.gold_mentions:
            if gm.source_content_sha256 not in warc_shas:
                missing.append((case.case_id, gm.gold_mention_id, gm.source_content_sha256))
    if missing:
        raise ValueError(
            f"FAIL-CLOSED: {len(missing)} Gold mentions reference missing WARC payloads: {missing[:5]}"
        )


def read_jsonl_strict(file_path: Path) -> List[Dict[str, Any]]:
    """Reads JSONL file strictly; any malformed line raises JSONDecodeError."""
    if not file_path.exists():
        return []
    records = []
    content = file_path.read_text(encoding="utf-8")
    for line_no, line in enumerate(content.splitlines(), 1):
        line_str = line.strip()
        if not line_str:
            continue
        try:
            records.append(json.loads(line_str))
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"FAIL-CLOSED: Malformed JSON at {file_path}:{line_no}: {line_str}", e.doc, e.pos
            )
    return records


def canonicalize_value(val: Any) -> Any:
    """Recursively removes transient fields and sorts primitive lists for deterministic comparison."""
    if isinstance(val, dict):
        transient = {"created_at", "timestamp", "run_id", "retrieved_at", "generated_at"}
        return {k: canonicalize_value(v) for k, v in sorted(val.items()) if k not in transient}
    elif isinstance(val, list):
        items = [canonicalize_value(x) for x in val]
        if items and all(isinstance(x, (str, int, float)) for x in items):
            return sorted(items)
        return items
    return val


def compute_canonical_jsonl_hash(file_path: Path) -> str:
    """Computes a deterministic hash of JSONL records ignoring transient timestamps and non-deterministic set orders."""
    if not file_path.exists():
        return "missing"
    records = read_jsonl_strict(file_path)
    cleaned = [canonicalize_value(r) for r in records]
    serialized = [json.dumps(r, sort_keys=True, ensure_ascii=False) for r in cleaned]
    serialized.sort()
    return hashlib.sha256("\n".join(serialized).encode("utf-8")).hexdigest()


def verify_paired_input_identity(group_a_dir: Path, group_b_dir: Path, case_id: str) -> Tuple[bool, List[str]]:
    """Verifies that upstream input assets are semantically identical between two paired runs."""
    mismatches = []
    bundle_a = group_a_dir / case_id
    bundle_b = group_b_dir / case_id

    for fname in PAIR_COMPARISON_FILES:
        fa = bundle_a / fname
        fb = bundle_b / fname
        ha = compute_canonical_jsonl_hash(fa)
        hb = compute_canonical_jsonl_hash(fb)
        if ha != hb:
            mismatches.append(f"{case_id}/{fname} hash mismatch: {ha} != {hb}")

    return len(mismatches) == 0, mismatches


def match_claim_5d_strict(
    extracted_claim: Dict[str, Any],
    gold_claim: Dict[str, Any],
    cand_to_gold_entity: Dict[str, Optional[str]],
) -> Tuple[bool, Dict[str, bool]]:
    """Evaluates True 5D match: subject entity, predicate, object, polarity, temporal."""
    details = {
        "subject": False,
        "predicate": False,
        "object": False,
        "polarity": False,
        "temporal": False,
    }

    # 1. Subject Entity Match
    cand_id = extracted_claim.get("candidate_entity_id")
    expected_entity_id = gold_claim.get("subject_gold_entity_id")
    mapped_entity_id = cand_to_gold_entity.get(cand_id)

    if mapped_entity_id and expected_entity_id and mapped_entity_id == expected_entity_id:
        details["subject"] = True

    # 2. Predicate Match
    e_pred = extracted_claim.get("predicate", "").strip()
    g_pred = gold_claim.get("predicate", "").strip()
    if e_pred == g_pred and e_pred:
        details["predicate"] = True

    # 3. Object Match
    e_obj = normalize_text(extracted_claim.get("object_raw", ""))
    g_obj = normalize_text(gold_claim.get("object_raw", ""))
    g_equiv = [normalize_text(x) for x in gold_claim.get("equivalence_set", [])]
    if e_obj and (e_obj == g_obj or e_obj in g_equiv):
        details["object"] = True

    # 4. Polarity Match
    e_pol = str(extracted_claim.get("polarity", "")).lower().replace("factpolarity.", "")
    g_pol = str(gold_claim.get("polarity", "")).lower().replace("factpolarity.", "")
    if e_pol == g_pol and e_pol:
        details["polarity"] = True

    # 5. Temporal Match
    e_temp = str(extracted_claim.get("temporal_status", "")).lower().replace("temporalstatus.", "")
    g_temp = str(gold_claim.get("temporal_status", "")).lower().replace("temporalstatus.", "")
    if e_temp == g_temp and e_temp:
        details["temporal"] = True

    is_5d = all(details.values())
    return is_5d, details


def compute_max_cardinality_5d_matching(
    extracted_claims: List[Dict[str, Any]],
    gold_claims: List[Dict[str, Any]],
    cand_to_gold_entity: Dict[str, Optional[str]],
) -> Tuple[int, int, List[Tuple[int, int, Dict[str, bool]]]]:
    """Pure binary 0/1 Maximum Cardinality Bipartite Matching for True 5D claims."""
    n_ext = len(extracted_claims)
    n_gold = len(gold_claims)

    if n_ext == 0 or n_gold == 0:
        return 0, 0, []

    cost_matrix = np.zeros((n_ext, n_gold))
    details_matrix = [[None for _ in range(n_gold)] for _ in range(n_ext)]

    for i, ec in enumerate(extracted_claims):
        for j, gc in enumerate(gold_claims):
            is_5d, det = match_claim_5d_strict(ec, gc, cand_to_gold_entity)
            details_matrix[i][j] = det
            cost_matrix[i, j] = -1.0 if is_5d else 0.0

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    tp_5d = 0
    matched_5d_pairs = []
    matched_ext_idx = set()
    matched_gold_idx = set()

    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] == -1.0:
            tp_5d += 1
            matched_5d_pairs.append((r, c, details_matrix[r][c]))
            matched_ext_idx.add(r)
            matched_gold_idx.add(c)

    # Diagnostic 4D matching on remaining pairs
    tp_4d_diag = 0
    for i, ec in enumerate(extracted_claims):
        if i in matched_ext_idx:
            continue
        for j, gc in enumerate(gold_claims):
            if j in matched_gold_idx:
                continue
            det = details_matrix[i][j]
            if det["predicate"] and det["object"] and det["polarity"] and det["temporal"]:
                tp_4d_diag += 1
                matched_ext_idx.add(i)
                matched_gold_idx.add(j)
                break

    return tp_5d, tp_4d_diag, matched_5d_pairs


def evaluate_bundle_v2_3(
    bundle_dir: Path,
    gold_case: GoldCase,
    expected_outcome: str,
    warc_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates a single investigation bundle under Evaluator V2.3:
    - Merkle seal check
    - Structural 4-layer check
    - Required files check
    - Duplicate mention signature fail-closed check
    - Evidence closure check
    - Mention Detection P/R/F1
    - Cluster ER B^3 and Pairwise on common universe
    - Pure 5D Bipartite Matching
    - Explicit calculation of false_released_claims = released_claims - TP_5D across ALL cases
    """
    case_id = gold_case.case_id
    target_name = gold_case.target_name

    # 1. Merkle Tree Seal Verification
    curr_tree_hash = compute_bundle_tree_hash(bundle_dir)
    seal_path = bundle_dir / "seal.json"
    if not seal_path.exists():
        raise FileNotFoundError(f"FAIL-CLOSED: Missing seal.json in {bundle_dir}!")
    seal_data = json.loads(seal_path.read_text(encoding="utf-8"))
    seal_verified = (curr_tree_hash == seal_data.get("bundle_tree_hash"))

    # 2. Check Required Bundle Files
    for req_file in REQUIRED_BUNDLE_FILES:
        if not (bundle_dir / req_file).exists():
            raise FileNotFoundError(f"FAIL-CLOSED: Missing required file {req_file} in {bundle_dir}!")

    # 3. Four-layer Structural Validation
    val_res = validate_bundle(bundle_dir, warc_path=warc_path)

    # 4. Read Manifest and Dossier
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    actual_outcome = manifest.get("run_outcome", "unknown")

    dossier_data = json.loads((bundle_dir / "dossier.json").read_text(encoding="utf-8"))
    released_claim_ids = set()
    for stmt in dossier_data.get("statements", []):
        for cid in stmt.get("backed_claim_ids", []):
            released_claim_ids.add(cid)
    # If statements is empty/absent, fall back to dossier.claims list (supporting minimal fixtures)
    if not released_claim_ids and dossier_data.get("claims"):
        for cid in dossier_data["claims"]:
            released_claim_ids.add(cid)

    # 5. Read Sources and Evidence
    sources = read_jsonl_strict(bundle_dir / "sources.jsonl")
    source_sha_by_id = {s["source_id"]: s.get("content_sha256", "") for s in sources}

    evidence_records = read_jsonl_strict(bundle_dir / "evidence.jsonl")
    ev_by_id = {e["evidence_id"]: e for e in evidence_records}
    ev_offset_by_id = {e["evidence_id"]: (e.get("char_start", 0) or 0) for e in evidence_records}

    extracted_mentions = read_jsonl_strict(bundle_dir / "mentions.jsonl")
    extracted_candidates = read_jsonl_strict(bundle_dir / "candidates.jsonl")
    all_proposed_claims = read_jsonl_strict(bundle_dir / "claims.jsonl")

    # Filter released claims from dossier
    released_claims = [c for c in all_proposed_claims if c.get("claim_id") in released_claim_ids]
    n_released = len(released_claims)

    # 6. Mention Signature Construction and Validation
    gold_mentions = gold_case.gold_mentions
    gold_mention_by_sig = {}
    gold_entity_by_sig = {}
    for gm in gold_mentions:
        gsig = make_mention_sig(gm.source_content_sha256, gm.char_start, gm.char_end, gm.verbatim_text)
        gold_mention_by_sig[gsig] = gm.gold_mention_id
        gold_entity_by_sig[gsig] = gm.gold_entity_id

    sys_mention_by_sig = {}
    sig_by_sys_mid = {}
    seen_sigs = []

    for m in extracted_mentions:
        mid = m["mention_id"]
        sid = m["source_id"]
        src_sha = source_sha_by_id.get(sid)
        if not src_sha:
            raise KeyError(f"FAIL-CLOSED: Mention {mid} references missing source {sid}!")

        ev_id = m.get("evidence_id")
        if not ev_id or ev_id not in ev_by_id:
            raise KeyError(f"FAIL-CLOSED: Mention {mid} references missing evidence {ev_id}!")

        ev_offset = ev_offset_by_id.get(ev_id, 0)
        sig_abs = make_mention_sig(src_sha, ev_offset + m["char_start"], ev_offset + m["char_end"], m["raw_name_text"])
        sig_rel = make_mention_sig(src_sha, m["char_start"], m["char_end"], m["raw_name_text"])

        # Signature resolution
        if sig_abs in gold_mention_by_sig:
            sig = sig_abs
        elif sig_rel in gold_mention_by_sig:
            sig = sig_rel
        else:
            sig = sig_abs if ev_offset > 0 else sig_rel

        # Fail-closed on duplicate signature in extracted mentions
        if sig in sys_mention_by_sig:
            raise ValueError(f"FAIL-CLOSED: Duplicate mention signature '{sig}' found in bundle {case_id}!")

        sys_mention_by_sig[sig] = mid
        sig_by_sys_mid[mid] = sig
        seen_sigs.append(sig)

    # 7. Mention Detection Metrics (Universe-level)
    u_sys = set(sys_mention_by_sig.keys())
    u_gold = set(gold_mention_by_sig.keys())
    u_common = u_sys.intersection(u_gold)

    mention_prec = (len(u_common) / len(u_sys)) if u_sys else 1.0
    mention_rec = (len(u_common) / len(u_gold)) if u_gold else 1.0
    mention_f1 = (2 * mention_prec * mention_rec / (mention_prec + mention_rec)) if (mention_prec + mention_rec) > 0 else 0.0

    # 8. Candidate -> GoldEntity Mapping (from Aligned Mentions)
    cand_to_gold_entity: Dict[str, Optional[str]] = {}
    false_merges = 0

    for cand in extracted_candidates:
        cand_id = cand["candidate_entity_id"]
        c_mids = cand.get("mention_ids", [])
        associated_gold_entities = set()

        for mid in c_mids:
            msig = sig_by_sys_mid.get(mid)
            if msig and msig in gold_entity_by_sig:
                associated_gold_entities.add(gold_entity_by_sig[msig])

        if len(associated_gold_entities) > 1:
            false_merges += (len(associated_gold_entities) - 1)
            cand_to_gold_entity[cand_id] = None
        elif len(associated_gold_entities) == 1:
            cand_to_gold_entity[cand_id] = list(associated_gold_entities)[0]
        else:
            cand_to_gold_entity[cand_id] = None

    # Check for False Splits
    false_splits = 0
    for ge in gold_case.gold_entities:
        ge_id = ge.gold_entity_id
        cands_with_ge = [cid for cid, mapped_ge in cand_to_gold_entity.items() if mapped_ge == ge_id]
        if len(cands_with_ge) > 1:
            false_splits += (len(cands_with_ge) - 1)

    # 9. Clustered Entity Resolution Metrics (B^3 and Pairwise on common universe)
    gold_clusters = gold_case.gold_clusters
    er_b3 = {"b3_precision": 1.0, "b3_recall": 1.0, "b3_f1": 1.0}
    er_pairwise = {"pairwise_precision": 1.0, "pairwise_recall": 1.0, "pairwise_f1": 1.0}

    if u_common and gold_clusters and extracted_candidates:
        g_clust_common = []
        for gc in gold_clusters:
            sigs = []
            for mid in gc:
                gm = next((m for m in gold_mentions if m.gold_mention_id == mid), None)
                if gm:
                    sigs.append(make_mention_sig(gm.source_content_sha256, gm.char_start, gm.char_end, gm.verbatim_text))
            common_sigs = [s for s in sigs if s in u_common]
            if common_sigs:
                g_clust_common.append(common_sigs)

        s_clust_common = []
        for cand in extracted_candidates:
            sigs = [sig_by_sys_mid[mid] for mid in cand.get("mention_ids", []) if mid in sig_by_sys_mid]
            common_sigs = [s for s in sigs if s in u_common]
            if common_sigs:
                s_clust_common.append(common_sigs)

        if g_clust_common and s_clust_common:
            er_b3 = compute_b3(g_clust_common, s_clust_common, list(u_common))
            er_pairwise = compute_pairwise(g_clust_common, s_clust_common, list(u_common))

    # 10. Claim Evaluation with True false_released_claims = released_claims - TP_5D
    gold_claims_dicts = [c.model_dump() for c in gold_case.gold_claims]
    n_gold = len(gold_claims_dicts)
    is_fact_bearing = gold_case.is_fact_bearing
    outcome_match = (actual_outcome == expected_outcome)

    if is_fact_bearing:
        if actual_outcome == "completed":
            claims_to_evaluate = released_claims
            n_ext = len(claims_to_evaluate)

            tp_5d, tp_4d_diag, matches = compute_max_cardinality_5d_matching(
                extracted_claims=claims_to_evaluate,
                gold_claims=gold_claims_dicts,
                cand_to_gold_entity=cand_to_gold_entity,
            )
            claim_prec = (tp_5d / n_ext) if n_ext > 0 else 0.0
            claim_rec = (tp_5d / n_gold) if n_gold > 0 else 0.0
            claim_f1 = (2 * claim_prec * claim_rec / (claim_prec + claim_rec)) if (claim_prec + claim_rec) > 0 else 0.0
            subj_acc = (tp_5d / (tp_5d + tp_4d_diag)) if (tp_5d + tp_4d_diag) > 0 else (1.0 if n_ext == 0 else 0.0)

            # Evaluator V2.3: false_released_claims covers ungrounded claims in completed runs
            false_released_claims = max(0, n_ext - tp_5d)
            spurious_claims = false_released_claims
            spurious_rate = (false_released_claims / n_ext) if n_ext > 0 else 0.0
            abstention_accuracy = 1.0 if outcome_match else 0.0
        else:
            # Fact-bearing case where system conservatively abstained
            claims_to_evaluate = released_claims
            n_ext = len(claims_to_evaluate)
            tp_5d = 0
            tp_4d_diag = 0
            claim_prec = None
            claim_rec = 0.0
            claim_f1 = 0.0
            subj_acc = 1.0

            false_released_claims = n_ext
            spurious_claims = n_ext
            spurious_rate = 1.0 if n_ext > 0 else 0.0
            abstention_accuracy = 1.0 if outcome_match else 0.0
    else:
        # Ground truth abstention case (e.g. insufficient_evidence negative control)
        tp_5d = 0
        tp_4d_diag = 0
        claim_prec = None
        claim_rec = None
        claim_f1 = None
        subj_acc = 1.0

        false_released_claims = n_released
        spurious_claims = n_released
        spurious_rate = 1.0 if n_released > 0 else 0.0
        abstention_accuracy = 1.0 if actual_outcome in {"ambiguous_identity", "insufficient_evidence"} else 0.0

    return {
        "case_id": case_id,
        "target_name": target_name,
        "bundle_tree_hash": curr_tree_hash,
        "seal_verified": seal_verified,
        "validation_passed": val_res.get("is_valid", False),
        "validation_errors": val_res.get("error_count", 0),
        "actual_outcome": actual_outcome,
        "expected_outcome": expected_outcome,
        "outcome_match": outcome_match,
        "is_fact_bearing": is_fact_bearing,
        "gold_claims_count": n_gold,
        "extracted_claims_count": n_released,
        "proposed_claims_count": len(all_proposed_claims),
        "released_claims_count": n_released,
        "tp_5d": tp_5d,
        "tp_4d_diag": tp_4d_diag,
        "false_released_claims": false_released_claims,
        "claim_precision": round(claim_prec, 4) if claim_prec is not None else None,
        "claim_recall": round(claim_rec, 4) if claim_rec is not None else None,
        "claim_f1": round(claim_f1, 4) if claim_f1 is not None else None,
        "subject_attribution_accuracy": round(subj_acc, 4),
        "mention_precision": round(mention_prec, 4),
        "mention_recall": round(mention_rec, 4),
        "mention_f1": round(mention_f1, 4),
        "er_b3_f1": round(er_b3.get("b3_f1", 1.0), 4),
        "er_pairwise_f1": round(er_pairwise.get("pairwise_f1", 1.0), 4),
        "false_merges": false_merges,
        "false_splits": false_splits,
        "spurious_claims": spurious_claims,
        "spurious_rate": spurious_rate,
        "abstention_accuracy": abstention_accuracy,
    }


def aggregate_suite_v2_3(
    results: List[Dict[str, Any]],
    expected_case_ids: List[str],
    provenance: Optional[Dict[str, Any]] = None,
    paired_identity_passed: bool = True,
    paired_mismatches: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Aggregates Evaluator V2.3 suite results and enforces strict release gates."""
    n = len(results)
    actual_cids = [r["case_id"] for r in results]

    completeness_pass = (set(actual_cids) == set(expected_case_ids))
    seal_intact = all(r["seal_verified"] for r in results)
    val_rate = sum(1.0 if r["validation_passed"] else 0.0 for r in results) / n if n else 0.0
    total_false_merges = sum(r["false_merges"] for r in results)
    total_false_splits = sum(r["false_splits"] for r in results)
    total_false_released = sum(r["false_released_claims"] for r in results)

    # Mention & ER Aggregation
    macro_mention_prec = sum(r["mention_precision"] for r in results) / n if n else 0.0
    macro_mention_rec = sum(r["mention_recall"] for r in results) / n if n else 0.0
    macro_mention_f1 = sum(r["mention_f1"] for r in results) / n if n else 0.0
    macro_b3_f1 = sum(r["er_b3_f1"] for r in results) / n if n else 0.0
    macro_pairwise_f1 = sum(r["er_pairwise_f1"] for r in results) / n if n else 0.0

    # Fact-bearing cases
    fb_cases = [r for r in results if r["is_fact_bearing"]]
    n_fb = len(fb_cases)
    if n_fb > 0:
        completed_fb = [r for r in fb_cases if r["actual_outcome"] == "completed" and r["claim_precision"] is not None]
        macro_prec = (sum(r["claim_precision"] for r in completed_fb) / len(completed_fb)) if completed_fb else 0.0
        macro_rec = sum(r["claim_recall"] for r in fb_cases if r["claim_recall"] is not None) / n_fb
        macro_f1 = (2 * macro_prec * macro_rec / (macro_prec + macro_rec)) if (macro_prec + macro_rec) > 0 else 0.0
        macro_subj = sum(r["subject_attribution_accuracy"] for r in fb_cases) / n_fb

        total_tp_5d = sum(r["tp_5d"] for r in fb_cases)
        total_ext_fb = sum(r["released_claims_count"] for r in fb_cases)
        total_gold_fb = sum(r["gold_claims_count"] for r in fb_cases)

        micro_prec = (total_tp_5d / total_ext_fb) if total_ext_fb > 0 else 0.0
        micro_rec = (total_tp_5d / total_gold_fb) if total_gold_fb > 0 else 0.0
        micro_f1 = (2 * micro_prec * micro_rec / (micro_prec + micro_rec)) if (micro_prec + micro_rec) > 0 else 0.0
    else:
        macro_prec = macro_rec = macro_f1 = macro_subj = 0.0
        micro_prec = micro_rec = micro_f1 = 0.0

    # Abstention cases
    abs_cases = [r for r in results if not r["is_fact_bearing"]]
    n_abs = len(abs_cases)
    if n_abs > 0:
        abs_accuracy = sum(r["abstention_accuracy"] for r in abs_cases) / n_abs
        total_spurious = sum(r["spurious_claims"] for r in abs_cases)
        spurious_case_rate = sum(r["spurious_rate"] for r in abs_cases) / n_abs
    else:
        abs_accuracy = None
        total_spurious = 0
        spurious_case_rate = None

    outcome_acc = sum(1.0 if r["outcome_match"] else 0.0 for r in results) / n if n else 0.0

    gates = {
        "seal_integrity_gate": seal_intact,
        "structural_validation_gate": (val_rate == 1.0),
        "case_completeness_gate": completeness_pass,
        "zero_false_merges_gate": (total_false_merges == 0),
        "zero_false_released_claims_gate": (total_false_released == 0),
        "ambiguity_safety_gate": (abs_accuracy == 1.0 if abs_accuracy is not None else True),
        "paired_input_identity_gate": paired_identity_passed,
        "mention_recall_gate": (macro_mention_rec >= 0.95),
        "b3_f1_gate": (macro_b3_f1 >= 0.95),
        "claim_precision_gate": (macro_prec >= 0.95),
        "claim_recall_gate": (macro_rec >= 0.80),
        "subject_attribution_gate": (macro_subj >= 0.95),
        "outcome_accuracy_gate": (outcome_acc >= 0.90),
        "completed_released_claims_gate": all(
            (r["released_claims_count"] > 0)
            for r in results
            if r["is_fact_bearing"] and r["actual_outcome"] == "completed"
        ),
    }
    all_gates_pass = all(gates.values())

    return {
        "evaluator_version": "2.3.0",
        "provenance": provenance or {},
        "total_cases_evaluated": n,
        "expected_case_count": len(expected_case_ids),
        "completeness_pass": completeness_pass,
        "seal_intact": seal_intact,
        "structural_validation_rate": round(val_rate, 4),
        "total_false_merges": total_false_merges,
        "total_false_splits": total_false_splits,
        "total_false_released_claims": total_false_released,
        "outcome_accuracy": round(outcome_acc, 4),
        "mention_evaluation": {
            "macro_precision": round(macro_mention_prec, 4),
            "macro_recall": round(macro_mention_rec, 4),
            "macro_f1": round(macro_mention_f1, 4),
            "b3_f1": round(macro_b3_f1, 4),
            "pairwise_f1": round(macro_pairwise_f1, 4),
        },
        "fact_bearing_evaluation": {
            "case_count": n_fb,
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
            "subject_attribution_accuracy": round(macro_subj, 4),
            "micro_precision": round(micro_prec, 4),
            "micro_recall": round(micro_rec, 4),
            "micro_f1": round(micro_f1, 4),
        },
        "abstention_evaluation": {
            "case_count": n_abs,
            "abstention_accuracy": round(abs_accuracy, 4) if abs_accuracy is not None else "N/A",
            "total_spurious_claims": total_spurious,
            "spurious_claim_rate": round(spurious_case_rate, 4) if spurious_case_rate is not None else "N/A",
        },
        "paired_input_check": {
            "passed": paired_identity_passed,
            "mismatch_count": len(paired_mismatches or []),
            "mismatches": (paired_mismatches or [])[:10],
        },
        "gates": gates,
        "all_gates_passed": all_gates_pass,
        "case_details": results,
    }


def render_markdown_report(suite_eval: Dict[str, Any]) -> str:
    """Generates an objective, unvarnished Markdown report directly from evaluation results."""
    prov = suite_eval.get("provenance", {})
    gates = suite_eval.get("gates", {})
    all_pass = suite_eval.get("all_gates_passed", False)
    status_str = "**PASSED**" if all_pass else "**FAILED**"

    lines = [
        f"# Evaluator V2.3 严谨评测审计报告",
        f"",
        f"## 1. 评测执行概况与审计元数据",
        f"- **评测器版本**: Evaluator {suite_eval.get('evaluator_version')}",
        f"- **Git Commit SHA**: `{prov.get('git_commit_sha', 'unknown')}` (dirty: `{prov.get('git_dirty', 'unknown')}`)",
        f"- **Evaluator SHA-256**: `{prov.get('evaluator_sha256', 'unknown')}`",
        f"- **Gold Contract SHA-256**: `{prov.get('gold_sha256', 'unknown')}`",
        f"- **WARC Corpus SHA-256**: `{prov.get('corpus_warc_sha256', 'unknown')}`",
        f"- **Query Index SHA-256**: `{prov.get('query_index_sha256', 'unknown')}`",
        f"- **综合裁决**: {status_str} (`all_gates_passed: {all_pass}`)",
        f"",
        f"## 2. 权威发布门禁状态 (Official Gates Checklist)",
        f"| 门禁名称 | 门禁检验标准 | 实际测量值 / 状态 | 门禁结果 |",
        f"|---|---|---|---|",
        f"| `seal_integrity_gate` | Merkle 根密封 100% 校验通过 | seal_intact={suite_eval.get('seal_intact')} | {'PASS' if gates.get('seal_integrity_gate') else 'FAIL'} |",
        f"| `structural_validation_gate` | 4 层结构校验 100% 通过 | rate={suite_eval.get('structural_validation_rate')} | {'PASS' if gates.get('structural_validation_gate') else 'FAIL'} |",
        f"| `case_completeness_gate` | 所有预期用例完全覆盖 | completeness={suite_eval.get('completeness_pass')} | {'PASS' if gates.get('case_completeness_gate') else 'FAIL'} |",
        f"| `zero_false_merges_gate` | 跨实体假合并总数绝对为 0 | false_merges={suite_eval.get('total_false_merges')} | {'PASS' if gates.get('zero_false_merges_gate') else 'FAIL'} |",
        f"| `zero_false_released_claims_gate` | 未核验释放断言数绝对为 0 | false_released={suite_eval.get('total_false_released_claims')} | {'PASS' if gates.get('zero_false_released_claims_gate') else 'FAIL'} |",
        f"| `ambiguity_safety_gate` | 稀疏与对照组 100% 拒答 | abstention_acc={suite_eval.get('abstention_evaluation', {}).get('abstention_accuracy')} | {'PASS' if gates.get('ambiguity_safety_gate') else 'FAIL'} |",
        f"| `paired_input_identity_gate` | G2/G3 对应输入去除时间戳后哈希一致 | passed={gates.get('paired_input_identity_gate')} | {'PASS' if gates.get('paired_input_identity_gate') else 'FAIL'} |",
        f"| `mention_recall_gate` | 实体提及召回率 $\\ge 95.0\\%$ | recall={suite_eval.get('mention_evaluation', {}).get('macro_recall')} | {'PASS' if gates.get('mention_recall_gate') else 'FAIL'} |",
        f"| `b3_f1_gate` | 聚类消歧 B³ F1 $\\ge 95.0\\%$ | b3_f1={suite_eval.get('mention_evaluation', {}).get('b3_f1')} | {'PASS' if gates.get('b3_f1_gate') else 'FAIL'} |",
        f"| `claim_precision_gate` | 释放断言精确率 $\\ge 95.0\\%$ | prec={suite_eval.get('fact_bearing_evaluation', {}).get('macro_precision')} | {'PASS' if gates.get('claim_precision_gate') else 'FAIL'} |",
        f"| `claim_recall_gate` | 释放断言召回率 $\\ge 80.0\\%$ | rec={suite_eval.get('fact_bearing_evaluation', {}).get('macro_recall')} | {'PASS' if gates.get('claim_recall_gate') else 'FAIL'} |",
        f"| `subject_attribution_gate` | 主体归属准确率 $\\ge 95.0\\%$ | subj_acc={suite_eval.get('fact_bearing_evaluation', {}).get('subject_attribution_accuracy')} | {'PASS' if gates.get('subject_attribution_gate') else 'FAIL'} |",
        f"| `outcome_accuracy_gate` | 运行状态匹配率 $\\ge 90.0\\%$ | acc={suite_eval.get('outcome_accuracy')} | {'PASS' if gates.get('outcome_accuracy_gate') else 'FAIL'} |",
        f"| `completed_released_claims_gate` | 完成用例必须至少释放 1 条有效断言 | passed={gates.get('completed_released_claims_gate')} | {'PASS' if gates.get('completed_released_claims_gate') else 'FAIL'} |",
        f"",
        f"## 3. 逐案例详细审计表 (Case-Level Breakdown)",
        f"| Case ID | 目标人物 | 实际状态 | 期望状态 | 匹配 | 释放数 | TP_5D | False Rel | Precision | Recall | F-Merge | F-Split |",
        f"|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for c in suite_eval.get("case_details", []):
        lines.append(
            f"| `{c['case_id']}` | {c['target_name']} | `{c['actual_outcome']}` | `{c['expected_outcome']}` | "
            f"{'✓' if c['outcome_match'] else '✗'} | {c['released_claims_count']} | {c['tp_5d']} | {c['false_released_claims']} | "
            f"{c['claim_precision'] if c['claim_precision'] is not None else 'N/A'} | "
            f"{c['claim_recall'] if c['claim_recall'] is not None else 'N/A'} | "
            f"{c['false_merges']} | {c['false_splits']} |"
        )

    lines.append("")
    lines.append("## 4. 结论与发布门槛对照")
    if all_pass:
        lines.append("所有预注册门禁均已通过，满足发布与合流标准。")
    else:
        failed_gates = [k for k, v in gates.items() if not v]
        lines.append(f"**当前未达标门禁 ({len(failed_gates)} 项)**: {', '.join(failed_gates)}")
        lines.append("依据预注册合流协议，当前产物**严禁作为正式发布版合流**，必须定性为未通过并进入缺陷修复。")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Evaluator V2.3: Strict Contract Engine.")
    parser.add_argument("--runs-dir", type=Path, required=True, help="Directory containing run bundles")
    parser.add_argument("--gold-file", type=Path, required=True, help="Path to gold_v2.json")
    parser.add_argument("--case-manifest", type=Path, required=True, help="Path to manifest containing expected case IDs")
    parser.add_argument("--expected-count", type=int, required=True, help="Expected number of cases")
    parser.add_argument("--warc-file", type=Path, default=None, help="Path to corpus.warc")
    parser.add_argument("--query-index", type=Path, default=None, help="Path to query_index.jsonl")
    parser.add_argument("--track-name", type=str, default="name_only", choices=["name_only", "hinted"])
    parser.add_argument("--paired-runs-dir", type=Path, default=None, help="Path to paired run bundles (e.g. Group 2 for Group 3)")
    parser.add_argument("--output-json", type=Path, required=True, help="Path to write evaluation JSON")
    parser.add_argument("--output-md", type=Path, default=None, help="Path to write generated Markdown report")
    args = parser.parse_args()

    # 1. Provenance Information
    git_sha, git_dirty = get_git_provenance()
    evaluator_sha = compute_file_sha256(Path(__file__))
    gold_sha = compute_file_sha256(args.gold_file)
    warc_sha = compute_file_sha256(args.warc_file) if args.warc_file else "none"
    qidx_sha = compute_file_sha256(args.query_index) if args.query_index else "none"

    provenance = {
        "evaluator_version": "2.3.0",
        "git_commit_sha": git_sha,
        "git_dirty": git_dirty,
        "evaluator_sha256": evaluator_sha,
        "gold_sha256": gold_sha,
        "corpus_warc_sha256": warc_sha,
        "query_index_sha256": qidx_sha,
    }

    # 2. Load Expected Cases from Manifest
    manifest_data = json.loads(args.case_manifest.read_text(encoding="utf-8"))
    if isinstance(manifest_data, list):
        expected_cids = [c["case_id"] for c in manifest_data]
    elif "cases" in manifest_data:
        expected_cids = [c["case_id"] for c in manifest_data["cases"]]
    elif "primary_cases" in manifest_data:
        expected_cids = [c["case_id"] for c in manifest_data["primary_cases"]]
    elif "results" in manifest_data:
        expected_cids = [c["case_id"] for c in manifest_data["results"]]
    else:
        raise ValueError("Unknown manifest schema!")

    if len(expected_cids) != args.expected_count:
        raise ValueError(f"Expected count ({args.expected_count}) != manifest case count ({len(expected_cids)})!")

    # 3. Load Gold Truth via Strict Pydantic RootModel
    gold_suite = GoldSuite.model_validate_json(args.gold_file.read_text(encoding="utf-8"))
    gold_by_id = {c.case_id: c for c in gold_suite}

    # 4. WARC Payload Verification if provided
    if args.warc_file:
        verify_gold_warc_integrity(gold_suite, args.warc_file)
        print(f"Verified all Gold mention source payloads against {args.warc_file.name}: 100% intact")

    # 5. Paired Input Identity Check if provided
    paired_identity_passed = True
    paired_mismatches = []
    if args.paired_runs_dir:
        for cid in expected_cids:
            ok, errs = verify_paired_input_identity(args.paired_runs_dir, args.runs_dir, cid)
            if not ok:
                paired_identity_passed = False
                paired_mismatches.extend(errs)

    bundle_dirs = sorted([d for d in args.runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])
    results = []

    print(f"Evaluator V2.3 running on {len(bundle_dirs)} bundles in {args.runs_dir} (Track: {args.track_name})...")

    for bdir in bundle_dirs:
        cid = bdir.name
        if cid not in gold_by_id:
            raise KeyError(f"FAIL-CLOSED: Bundle {cid} not found in Gold truth {args.gold_file}!")

        gcase = gold_by_id[cid]
        if args.track_name == "name_only" and gcase.expected_outcome_name_only:
            exp_outcome = gcase.expected_outcome_name_only
        elif args.track_name == "hinted" and gcase.expected_outcome_hinted:
            exp_outcome = gcase.expected_outcome_hinted
        else:
            exp_outcome = gcase.expected_outcome

        res = evaluate_bundle_v2_3(
            bundle_dir=bdir,
            gold_case=gcase,
            expected_outcome=exp_outcome,
            warc_path=args.warc_file,
        )
        results.append(res)
        fb_tag = "Fact" if res["is_fact_bearing"] else "Abstain"
        print(f"  [{cid}|{fb_tag}] Outcome: {res['actual_outcome']} (exp: {res['expected_outcome']}), "
              f"P: {res['claim_precision']}, R: {res['claim_recall']}, "
              f"TP_5D: {res['tp_5d']}/{res['gold_claims_count']}, FalseRel: {res['false_released_claims']}, "
              f"FMerges: {res['false_merges']}, FSplits: {res['false_splits']}")

    suite_eval = aggregate_suite_v2_3(
        results,
        expected_case_ids=expected_cids,
        provenance=provenance,
        paired_identity_passed=paired_identity_passed,
        paired_mismatches=paired_mismatches,
    )

    print("\n==================================================")
    print(f"EVALUATOR V2.3 EVALUATION COMPLETE: {suite_eval['total_cases_evaluated']} cases")
    print(f"  Seal Intact: {suite_eval['seal_intact']}")
    print(f"  Completeness: {suite_eval['completeness_pass']}")
    print(f"  False Merges: {suite_eval['total_false_merges']}, False Splits: {suite_eval['total_false_splits']}")
    print(f"  Total False Released Claims: {suite_eval['total_false_released_claims']}")
    print(f"  Paired Input Identity: {suite_eval['paired_input_check']['passed']}")
    print(f"  Mention Rec: {suite_eval['mention_evaluation']['macro_recall']}, B3 F1: {suite_eval['mention_evaluation']['b3_f1']}")
    print(f"  Fact-Bearing ({suite_eval['fact_bearing_evaluation']['case_count']} cases): "
          f"Macro P={suite_eval['fact_bearing_evaluation']['macro_precision']}, "
          f"R={suite_eval['fact_bearing_evaluation']['macro_recall']}, "
          f"F1={suite_eval['fact_bearing_evaluation']['macro_f1']}, "
          f"SubjAcc={suite_eval['fact_bearing_evaluation']['subject_attribution_accuracy']}")
    print(f"  Abstention ({suite_eval['abstention_evaluation']['case_count']} cases): "
          f"Safety={suite_eval['abstention_evaluation']['abstention_accuracy']}, "
          f"Spurious Claims={suite_eval['abstention_evaluation']['total_spurious_claims']}")
    print(f"  Gates: {suite_eval['gates']}")
    print(f"  ALL GATES PASSED: {suite_eval['all_gates_passed']}")
    print("==================================================")

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(suite_eval, indent=2), encoding="utf-8")
    print(f"Saved Evaluator V2.3 JSON to: {args.output_json}")

    if args.output_md:
        md_content = render_markdown_report(suite_eval)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_content, encoding="utf-8")
        print(f"Saved Evaluator V2.3 Markdown Report to: {args.output_md}")

    if not suite_eval["all_gates_passed"]:
        print("FAIL-CLOSED: Release gates failed! Exiting with code 1.")
        sys.exit(1)


if __name__ == "__main__":
    main()
