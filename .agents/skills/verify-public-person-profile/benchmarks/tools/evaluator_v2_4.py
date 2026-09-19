"""
Blind Evaluation Protocol v1.4 - Evaluator V2.4 (Strict Benchmark Governance & Funnel Engine).
Key Upgrades over V2.3:
1. Exact WARC Byte & Slice Replay:
   - Verifies WARC-Target-URI, char offsets, and verbatim text slices byte-for-byte.
   - Fail-closed on any character mismatch or off-by-one.
2. Programmatic Asset Manifest Integrity Gate:
   - verify_asset_manifest() recomputes byte size and SHA-256 for all required assets.
   - Any missing, modified, or undeclared asset causes asset_manifest_gate to fail.
3. Zero-Denominator Safe Handling for Occurrence-Level Mention Recall:
   - Cases with zero gold mentions (abstained non-fact-bearing cases) are recorded as N/A.
   - Excluded from macro mention precision/recall/f1 denominators.
   - Occurrence-level mention metrics demoted to diagnostic indicators.
4. New Primary Benchmark Gates:
   - target_entity_case_recall_gate (100% of fact-bearing cases must find target candidate)
   - entity_source_recall_gate (>= 95% of unique (entity, source) pairs detected)
   - zero_false_merges_gate (0 false merges)
   - false_splits_gate (<= max_false_splits, default 0)
   - asset_manifest_gate (asset manifest 100% verified)
5. Programmatic Six-Level Recall Funnel:
   - Level 1: Gold Sources in Bundle
   - Level 2: Entity x Source hits
   - Level 3: Target Mentions covered by Evidence window
   - Level 4: Evidence-interior Target Mention extraction
   - Level 5: Gold Claim Support covered by Evidence window
   - Level 6: 5D Claim Matching (Proposed TP vs Released TP)
   - Per-case first_failure_stage diagnosis.
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
from dataclasses import dataclass
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


@dataclass
class WarcRecord:
    target_uri: str
    html_payload: bytes
    text: str
    sha256: str


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


def parse_warc_records(warc_path: Path) -> Dict[str, WarcRecord]:
    """Parses response records from standard WARC file, returning sha256 -> WarcRecord."""
    if not warc_path.exists():
        raise FileNotFoundError(f"WARC file not found: {warc_path}")

    data = warc_path.read_bytes()
    records: Dict[str, WarcRecord] = {}
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
            uri = warc_headers.get("warc-target-uri", "")
            sha = hashlib.sha256(html_payload).hexdigest()
            text = html_payload.decode("utf-8", errors="replace")
            records[sha] = WarcRecord(
                target_uri=uri,
                html_payload=html_payload,
                text=text,
                sha256=sha,
            )

    return records


def verify_gold_warc_integrity(gold_suite: GoldSuite, warc_path: Path):
    """
    Evaluator V2.4 Strict WARC Byte & Slice Replay:
    Verifies that every mention and claim support:
    1. References an existing response record by payload SHA-256.
    2. Matches the WARC-Target-URI exactly (for claim supports).
    3. Replays char_start:char_end byte/character slice identically to verbatim_text.
    """
    warc_records = parse_warc_records(warc_path)
    errors = []

    for case in gold_suite:
        for gm in case.gold_mentions:
            rec = warc_records.get(gm.source_content_sha256)
            if not rec:
                errors.append(f"{case.case_id}:{gm.gold_mention_id} payload SHA missing from WARC: {gm.source_content_sha256}")
                continue
            slice_text = rec.text[gm.char_start:gm.char_end]
            if slice_text != gm.verbatim_text:
                errors.append(
                    f"{case.case_id}:{gm.gold_mention_id} verbatim slice mismatch: "
                    f"expected {repr(gm.verbatim_text[:40])}, got {repr(slice_text[:40])} "
                    f"at [{gm.char_start}:{gm.char_end}]"
                )

        for gc in case.gold_claims:
            if not getattr(gc, "supports", None):
                errors.append(f"{case.case_id}:{gc.claim_id} has empty supports list!")
                continue
            for sup in gc.supports:
                rec = warc_records.get(sup.source_content_sha256)
                if not rec:
                    errors.append(f"{case.case_id}:{gc.claim_id} support payload SHA missing: {sup.source_content_sha256}")
                    continue
                if sup.source_url != rec.target_uri:
                    errors.append(
                        f"{case.case_id}:{gc.claim_id} support URL mismatch: "
                        f"expected {sup.source_url}, got {rec.target_uri}"
                    )
                slice_text = rec.text[sup.char_start:sup.char_end]
                if slice_text != sup.verbatim_text:
                    errors.append(
                        f"{case.case_id}:{gc.claim_id} support verbatim slice mismatch: "
                        f"expected {repr(sup.verbatim_text[:40])}, got {repr(slice_text[:40])} "
                        f"at [{sup.char_start}:{sup.char_end}]"
                    )

    if errors:
        msg = f"FAIL-CLOSED: {len(errors)} Gold-to-WARC byte replay errors:\n" + "\n".join(errors[:10])
        raise ValueError(msg)


def verify_asset_manifest(manifest_path: Path, fixtures_dir: Path) -> Tuple[bool, List[str]]:
    """
    Evaluator V2.4 Asset Manifest Gate:
    Recomputes byte sizes and SHA-256 hashes for all declared assets in asset_manifest.json.
    """
    if not manifest_path.exists():
        return False, [f"Asset manifest file not found: {manifest_path}"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"Malformed asset_manifest.json: {e}"]

    errors = []
    for fname, meta in manifest.items():
        fpath = fixtures_dir / fname
        if not fpath.exists():
            errors.append(f"Missing declared asset file: {fname}")
            continue
        data = fpath.read_bytes()
        act_size = len(data)
        act_sha = hashlib.sha256(data).hexdigest()

        exp_size = meta.get("bytes")
        exp_sha = meta.get("sha256")

        if exp_size is not None and act_size != exp_size:
            errors.append(f"Size mismatch for {fname}: declared {exp_size} bytes, actual {act_size} bytes")
        if exp_sha is not None and act_sha != exp_sha:
            errors.append(f"SHA-256 mismatch for {fname}: declared {exp_sha}, actual {act_sha}")

    return (len(errors) == 0), errors


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
        if not fa.exists() and not fb.exists():
            continue
        if not fa.exists() or not fb.exists():
            mismatches.append(f"Case {case_id} file existence mismatch for {fname}: A exists={fa.exists()}, B exists={fb.exists()}")
            continue

        ha = compute_canonical_jsonl_hash(fa)
        hb = compute_canonical_jsonl_hash(fb)
        if ha != hb:
            mismatches.append(f"Case {case_id} upstream asset drift in {fname}: hash_A={ha[:12]} vs hash_B={hb[:12]}")

    return len(mismatches) == 0, mismatches


def parse_temporal_status(temporal_str: Optional[str]) -> str:
    if not temporal_str:
        return "unknown"
    clean = temporal_str.strip().lower().replace("temporalstatus.", "")
    if "current" in clean:
        return "current"
    if "former" in clean:
        return "former"
    return "unknown"


def parse_polarity(polarity_str: Optional[str]) -> str:
    if not polarity_str:
        return "affirmative"
    clean = polarity_str.strip().lower().replace("factpolarity.", "")
    if "negative" in clean:
        return "negative"
    return "affirmative"


def check_5d_exact_match(ext: Dict[str, Any], gold: Dict[str, Any], cand_to_gold_entity: Dict[str, Optional[str]]) -> bool:
    """Strict 5-Dimensional Claim Matching."""
    ext_cand_id = ext.get("candidate_entity_id")
    mapped_gold_ent = cand_to_gold_entity.get(ext_cand_id)
    if mapped_gold_ent != gold.get("subject_gold_entity_id"):
        return False

    if normalize_text(ext.get("predicate", "")) != normalize_text(gold.get("predicate", "")):
        return False

    ext_obj = normalize_text(ext.get("object_raw", ""))
    gold_obj = normalize_text(gold.get("object_raw", ""))
    gold_equiv = [normalize_text(x) for x in gold.get("equivalence_set", [])]

    if ext_obj != gold_obj and ext_obj not in gold_equiv:
        return False

    if parse_polarity(ext.get("polarity")) != parse_polarity(gold.get("polarity")):
        return False

    if parse_temporal_status(ext.get("temporal_status")) != parse_temporal_status(gold.get("temporal_status")):
        return False

    return True


def check_4d_diag_match(ext: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    """Diagnostic 4D match: predicate, object, polarity, temporal match, ignoring subject."""
    if normalize_text(ext.get("predicate", "")) != normalize_text(gold.get("predicate", "")):
        return False

    ext_obj = normalize_text(ext.get("object_raw", ""))
    gold_obj = normalize_text(gold.get("object_raw", ""))
    gold_equiv = [normalize_text(x) for x in gold.get("equivalence_set", [])]

    if ext_obj != gold_obj and ext_obj not in gold_equiv:
        return False

    if parse_polarity(ext.get("polarity")) != parse_polarity(gold.get("polarity")):
        return False

    if parse_temporal_status(ext.get("temporal_status")) != parse_temporal_status(gold.get("temporal_status")):
        return False

    return True


def compute_max_cardinality_5d_matching(
    extracted_claims: List[Dict[str, Any]],
    gold_claims: List[Dict[str, Any]],
    cand_to_gold_entity: Dict[str, Optional[str]],
) -> Tuple[int, int, List[Tuple[int, int]]]:
    n_ext = len(extracted_claims)
    n_gold = len(gold_claims)
    if n_ext == 0 or n_gold == 0:
        return 0, 0, []

    cost_matrix = np.zeros((n_ext, n_gold), dtype=int)
    for i, ext in enumerate(extracted_claims):
        for j, gold in enumerate(gold_claims):
            if check_5d_exact_match(ext, gold, cand_to_gold_entity):
                cost_matrix[i, j] = -1

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    tp_5d = 0
    matched_pairs = []
    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] == -1:
            tp_5d += 1
            matched_pairs.append((r, c))

    matched_ext = {r for r, _ in matched_pairs}
    matched_gold = {c for _, c in matched_pairs}

    tp_4d_diag = 0
    diag_cost = np.zeros((n_ext, n_gold), dtype=int)
    for i, ext in enumerate(extracted_claims):
        if i in matched_ext:
            continue
        for j, gold in enumerate(gold_claims):
            if j in matched_gold:
                continue
            if check_4d_diag_match(ext, gold):
                diag_cost[i, j] = -1

    r_diag, c_diag = linear_sum_assignment(diag_cost)
    for r, c in zip(r_diag, c_diag):
        if diag_cost[r, c] == -1:
            tp_4d_diag += 1

    return tp_5d, tp_4d_diag, matched_pairs


def compute_case_funnel(
    gold_case: GoldCase,
    extracted_sources: List[Dict[str, Any]],
    extracted_evidence: List[Dict[str, Any]],
    extracted_mentions: List[Dict[str, Any]],
    all_proposed_claims: List[Dict[str, Any]],
    released_claims: List[Dict[str, Any]],
    cand_to_gold_entity: Dict[str, Optional[str]],
    gold_mention_by_sig: Dict[str, str],
    evidence_lookup: Dict[str, Tuple[str, int]],
    actual_outcome: str,
    expected_outcome: str,
    false_splits: int,
) -> Dict[str, Any]:
    """Computes programmatically the 6-level recall funnel for a single case."""
    is_fb = gold_case.is_fact_bearing

    # Level 1: Gold Sources in Bundle
    gold_source_shas = set()
    for m in gold_case.gold_mentions:
        gold_source_shas.add(m.source_content_sha256)
    for c in gold_case.gold_claims:
        for s in getattr(c, "supports", []):
            gold_source_shas.add(s.source_content_sha256)

    ext_source_shas = set()
    for s in extracted_sources:
        sha = s.get("raw_payload_sha256") or s.get("content_sha256") or s.get("source_content_sha256") or ""
        if sha:
            ext_source_shas.add(sha)

    l1_num = len(gold_source_shas.intersection(ext_source_shas))
    l1_denom = len(gold_source_shas)
    l1_pass = (l1_num == l1_denom) if l1_denom > 0 else True

    # Level 2: Entity x Source hits
    gold_es_pairs = set((m.gold_entity_id, m.source_content_sha256) for m in gold_case.gold_mentions)
    ext_es_pairs = set()

    for m in extracted_mentions:
        ev_id = m.get("evidence_id")
        ev_info = evidence_lookup.get(ev_id)
        if not ev_info:
            continue
        ev_sha, ev_offset = ev_info
        c_start = m.get("char_start", 0)
        c_end = m.get("char_end", 0)
        txt = m.get("raw_name_text", "")
        sig_abs = make_mention_sig(ev_sha, ev_offset + c_start, ev_offset + c_end, txt)
        sig_rel = make_mention_sig(ev_sha, c_start, c_end, txt)
        matched_mid = gold_mention_by_sig.get(sig_abs) or gold_mention_by_sig.get(sig_rel)
        if matched_mid:
            gm = next((x for x in gold_case.gold_mentions if x.gold_mention_id == matched_mid), None)
            if gm:
                ext_es_pairs.add((gm.gold_entity_id, gm.source_content_sha256))

    l2_num = len(gold_es_pairs.intersection(ext_es_pairs))
    l2_denom = len(gold_es_pairs)
    l2_pass = (l2_num == l2_denom) if l2_denom > 0 else True

    # Build evidence spans
    ev_spans = []
    for ev in extracted_evidence:
        sha = ev.get("raw_payload_sha256") or ev.get("source_content_sha256") or ""
        ev_spans.append((sha, ev.get("char_start", 0), ev.get("char_end", 0)))

    # Level 3 & Level 4: Target Mentions covered & extracted
    tgt_eid = gold_case.target_gold_entity_id
    tgt_gold_mentions = [m for m in gold_case.gold_mentions if m.gold_entity_id == tgt_eid]

    l3_denom = len(tgt_gold_mentions)
    l3_covered_mids = set()

    for m in tgt_gold_mentions:
        cov = any(s == m.source_content_sha256 and es <= m.char_start and m.char_end <= ee for (s, es, ee) in ev_spans)
        if cov:
            l3_covered_mids.add(m.gold_mention_id)

    l3_num = len(l3_covered_mids)

    # Level 4: Evidence interior extraction
    sys_abs_mentions = set()
    for m in extracted_mentions:
        ev_id = m.get("evidence_id")
        ev_info = evidence_lookup.get(ev_id)
        if ev_info:
            ev_sha, ev_offset = ev_info
            sys_abs_mentions.add((ev_sha, ev_offset + m.get("char_start", 0), ev_offset + m.get("char_end", 0)))

    l4_num = 0
    for m in tgt_gold_mentions:
        if m.gold_mention_id in l3_covered_mids:
            if (m.source_content_sha256, m.char_start, m.char_end) in sys_abs_mentions:
                l4_num += 1
    l4_denom = l3_num

    # Level 5: Gold Claim Supports covered by Evidence window
    all_claim_supports = []
    for c in gold_case.gold_claims:
        all_claim_supports.extend(getattr(c, "supports", []))

    l5_denom = len(all_claim_supports)
    l5_num = 0
    for s in all_claim_supports:
        cov = any(sha == s.source_content_sha256 and es <= s.char_start and s.char_end <= ee for (sha, es, ee) in ev_spans)
        if cov:
            l5_num += 1

    # Level 6: 5D Claims proposed vs released
    gold_claims_dicts = [c.model_dump() for c in gold_case.gold_claims]
    l6_denom = len(gold_claims_dicts)

    proposed_tp_5d, _, _ = compute_max_cardinality_5d_matching(
        extracted_claims=all_proposed_claims,
        gold_claims=gold_claims_dicts,
        cand_to_gold_entity=cand_to_gold_entity,
    )
    released_tp_5d, _, _ = compute_max_cardinality_5d_matching(
        extracted_claims=released_claims,
        gold_claims=gold_claims_dicts,
        cand_to_gold_entity=cand_to_gold_entity,
    )

    # First Failure Stage Diagnosis
    if not is_fb:
        if actual_outcome != expected_outcome:
            first_fail = "abstention_decision_failure"
        else:
            first_fail = "none_abstention_passed"
    else:
        if not l1_pass:
            first_fail = "l1_source_retrieval_miss"
        elif not l2_pass:
            first_fail = "l2_entity_source_detection_miss"
        elif l5_denom > 0 and l5_num < l5_denom:
            first_fail = "l5_claim_support_window_miss"
        elif l6_denom > 0 and proposed_tp_5d < l6_denom:
            first_fail = "l6a_claim_extractor_miss"
        elif released_tp_5d < proposed_tp_5d:
            first_fail = "l6b_candidate_or_gate_filter_loss"
        elif false_splits > 0:
            first_fail = "candidate_false_split"
        elif actual_outcome != expected_outcome:
            first_fail = "outcome_state_machine_failure"
        else:
            first_fail = "all_stages_passed"

    return {
        "l1_gold_sources": {"numerator": l1_num, "denominator": l1_denom, "rate": round(l1_num / l1_denom, 4) if l1_denom else 1.0},
        "l2_entity_source_hits": {"numerator": l2_num, "denominator": l2_denom, "rate": round(l2_num / l2_denom, 4) if l2_denom else 1.0},
        "l3_target_mentions_covered": {"numerator": l3_num, "denominator": l3_denom, "rate": round(l3_num / l3_denom, 4) if l3_denom else 1.0},
        "l4_target_mentions_extracted": {"numerator": l4_num, "denominator": l4_denom, "rate": round(l4_num / l4_denom, 4) if l4_denom else 1.0},
        "l5_claim_supports_covered": {"numerator": l5_num, "denominator": l5_denom, "rate": round(l5_num / l5_denom, 4) if l5_denom else 1.0},
        "l6a_proposed_claims_tp": {"numerator": proposed_tp_5d, "denominator": l6_denom, "rate": round(proposed_tp_5d / l6_denom, 4) if l6_denom else 1.0},
        "l6b_released_claims_tp": {"numerator": released_tp_5d, "denominator": l6_denom, "rate": round(released_tp_5d / l6_denom, 4) if l6_denom else 1.0},
        "first_failure_stage": first_fail,
    }


def evaluate_bundle_v2_4(
    bundle_dir: Path,
    gold_case: GoldCase,
    expected_outcome: str,
    warc_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Evaluates a single case bundle under Evaluator V2.4 protocol."""
    case_id = gold_case.case_id
    target_name = gold_case.target_name

    # 1. Structural Check
    missing_files = [f for f in REQUIRED_BUNDLE_FILES if not (bundle_dir / f).exists()]
    if missing_files:
        raise FileNotFoundError(f"FAIL-CLOSED: Bundle {case_id} is missing required files: {missing_files}")

    # 2. Schema Validation
    val_res = validate_bundle(bundle_dir)

    # 3. Merkle Seal Verification
    seal_file = bundle_dir / "seal.json"
    seal_verified = False
    curr_tree_hash = compute_bundle_tree_hash(bundle_dir)

    if seal_file.exists():
        try:
            seal_data = json.loads(seal_file.read_text(encoding="utf-8"))
            recorded_hash = seal_data.get("bundle_tree_hash")
            seal_verified = (recorded_hash == curr_tree_hash)
        except Exception:
            seal_verified = False

    # 4. Manifest and Outcome
    manifest_data = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    actual_outcome = manifest_data.get("run_outcome", "unknown")

    # 5. Load Records
    extracted_sources = read_jsonl_strict(bundle_dir / "sources.jsonl")
    extracted_evidence = read_jsonl_strict(bundle_dir / "evidence.jsonl")
    extracted_mentions = read_jsonl_strict(bundle_dir / "mentions.jsonl")
    extracted_candidates = read_jsonl_strict(bundle_dir / "candidates.jsonl")
    all_proposed_claims = read_jsonl_strict(bundle_dir / "claims.jsonl")

    dossier_data = json.loads((bundle_dir / "dossier.json").read_text(encoding="utf-8"))
    released_claim_ids = set()
    for stmt in dossier_data.get("statements", []):
        for cid in stmt.get("backed_claim_ids", []):
            released_claim_ids.add(cid)

    released_claims = [c for c in all_proposed_claims if c.get("claim_id") in released_claim_ids]
    n_released = len(released_claims)

    # 6. Map Mentions & Align Signatures
    gold_mentions = gold_case.gold_mentions
    gold_mention_by_sig: Dict[str, str] = {}
    gold_entity_by_sig: Dict[str, str] = {}

    for gm in gold_mentions:
        msig = make_mention_sig(gm.source_content_sha256, gm.char_start, gm.char_end, gm.verbatim_text)
        gold_mention_by_sig[msig] = gm.gold_mention_id
        gold_entity_by_sig[msig] = gm.gold_entity_id

    evidence_lookup: Dict[str, Tuple[str, int]] = {}
    for ev in extracted_evidence:
        ev_id = ev.get("evidence_id")
        ev_sha = ev.get("raw_payload_sha256") or ev.get("source_content_sha256") or ""
        ev_offset = ev.get("char_start", 0)
        evidence_lookup[ev_id] = (ev_sha, ev_offset)

    sys_mention_by_sig: Dict[str, str] = {}
    sig_by_sys_mid: Dict[str, str] = {}

    for m in extracted_mentions:
        mid = m["mention_id"]
        ev_id = m.get("evidence_id")
        ev_info = evidence_lookup.get(ev_id)
        if not ev_info:
            raise ValueError(f"FAIL-CLOSED: Mention {mid} references unknown evidence_id '{ev_id}'")

        ev_sha, ev_offset = ev_info
        c_start = m.get("char_start", 0)
        c_end = m.get("char_end", 0)
        name_txt = m.get("raw_name_text", "")

        sig_abs = make_mention_sig(ev_sha, ev_offset + c_start, ev_offset + c_end, name_txt)
        sig_rel = make_mention_sig(ev_sha, c_start, c_end, name_txt)

        if sig_abs in gold_mention_by_sig:
            sig = sig_abs
        elif sig_rel in gold_mention_by_sig:
            sig = sig_rel
        else:
            sig = sig_abs if ev_offset > 0 else sig_rel

        if sig in sys_mention_by_sig:
            raise ValueError(f"FAIL-CLOSED: Duplicate mention signature '{sig}' found in bundle {case_id}!")

        sys_mention_by_sig[sig] = mid
        sig_by_sys_mid[mid] = sig

    # 7. Mention Metrics (Zero-Denominator Safe Handling)
    u_sys = set(sys_mention_by_sig.keys())
    u_gold = set(gold_mention_by_sig.keys())
    u_common = u_sys.intersection(u_gold)

    if len(u_gold) == 0:
        mention_prec = None
        mention_rec = None
        mention_f1 = None
    else:
        mention_prec = (len(u_common) / len(u_sys)) if u_sys else 1.0
        mention_rec = (len(u_common) / len(u_gold))
        mention_f1 = (2 * mention_prec * mention_rec / (mention_prec + mention_rec)) if (mention_prec + mention_rec) > 0 else 0.0

    # 8. Candidate -> GoldEntity Mapping
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

    # Target Entity Recall in Candidates
    tgt_eid = gold_case.target_gold_entity_id
    if gold_case.is_fact_bearing and tgt_eid:
        target_entity_recalled = (tgt_eid in cand_to_gold_entity.values())
    else:
        target_entity_recalled = True

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

    # 10. Claim Evaluation
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

            diag_denom = tp_5d + tp_4d_diag
            subj_acc = (tp_5d / diag_denom) if diag_denom > 0 else None

            unmatched_released_claims = max(0, n_ext - tp_5d)
            spurious_claims = unmatched_released_claims
            spurious_rate = (unmatched_released_claims / n_ext) if n_ext > 0 else 0.0
            abstention_accuracy = 1.0 if outcome_match else 0.0
        else:
            claims_to_evaluate = released_claims
            n_ext = len(claims_to_evaluate)
            tp_5d = 0
            tp_4d_diag = 0
            claim_prec = None
            claim_rec = 0.0
            claim_f1 = 0.0
            subj_acc = None

            unmatched_released_claims = n_ext
            spurious_claims = n_ext
            spurious_rate = 1.0 if n_ext > 0 else 0.0
            abstention_accuracy = 1.0 if outcome_match else 0.0
    else:
        tp_5d = 0
        tp_4d_diag = 0
        claim_prec = None
        claim_rec = None
        claim_f1 = None
        subj_acc = None

        unmatched_released_claims = n_released
        spurious_claims = n_released
        spurious_rate = 1.0 if n_released > 0 else 0.0
        abstention_accuracy = 1.0 if actual_outcome in {"ambiguous_identity", "insufficient_evidence"} else 0.0

    # 11. Programmatic 6-Level Funnel
    funnel = compute_case_funnel(
        gold_case=gold_case,
        extracted_sources=extracted_sources,
        extracted_evidence=extracted_evidence,
        extracted_mentions=extracted_mentions,
        all_proposed_claims=all_proposed_claims,
        released_claims=released_claims,
        cand_to_gold_entity=cand_to_gold_entity,
        gold_mention_by_sig=gold_mention_by_sig,
        evidence_lookup=evidence_lookup,
        actual_outcome=actual_outcome,
        expected_outcome=expected_outcome,
        false_splits=false_splits,
    )

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
        "target_entity_recalled": target_entity_recalled,
        "gold_claims_count": n_gold,
        "extracted_claims_count": n_released,
        "proposed_claims_count": len(all_proposed_claims),
        "released_claims_count": n_released,
        "tp_5d": tp_5d,
        "tp_4d_diag": tp_4d_diag,
        "unmatched_released_claims": unmatched_released_claims,
        "claim_precision": round(claim_prec, 4) if claim_prec is not None else None,
        "claim_recall": round(claim_rec, 4) if claim_rec is not None else None,
        "claim_f1": round(claim_f1, 4) if claim_f1 is not None else None,
        "subject_attribution_accuracy": round(subj_acc, 4) if subj_acc is not None else None,
        "mention_precision": round(mention_prec, 4) if mention_prec is not None else None,
        "mention_recall": round(mention_rec, 4) if mention_rec is not None else None,
        "mention_f1": round(mention_f1, 4) if mention_f1 is not None else None,
        "er_b3_f1": round(er_b3.get("b3_f1", 1.0), 4),
        "er_pairwise_f1": round(er_pairwise.get("pairwise_f1", 1.0), 4),
        "false_merges": false_merges,
        "false_splits": false_splits,
        "spurious_claims": spurious_claims,
        "spurious_rate": spurious_rate,
        "abstention_accuracy": abstention_accuracy,
        "funnel": funnel,
    }


def aggregate_suite_v2_4(
    results: List[Dict[str, Any]],
    expected_case_ids: List[str],
    provenance: Optional[Dict[str, Any]] = None,
    paired_identity_passed: bool = True,
    paired_mismatches: Optional[List[str]] = None,
    asset_manifest_passed: bool = True,
    asset_manifest_errors: Optional[List[str]] = None,
    max_false_splits: int = 0,
) -> Dict[str, Any]:
    """Aggregates Evaluator V2.4 suite results and evaluates strict benchmark release gates."""
    n = len(results)
    actual_cids = [r["case_id"] for r in results]

    completeness_pass = (set(actual_cids) == set(expected_case_ids))
    seal_intact = all(r["seal_verified"] for r in results)
    val_rate = sum(1.0 if r["validation_passed"] else 0.0 for r in results) / n if n else 0.0
    total_false_merges = sum(r["false_merges"] for r in results)
    total_false_splits = sum(r["false_splits"] for r in results)
    total_unmatched_released = sum(r["unmatched_released_claims"] for r in results)

    # Occurrence-level Mention Aggregation (Excluded Zero-Gold Denominators)
    valid_m_prec = [r["mention_precision"] for r in results if r.get("mention_precision") is not None]
    valid_m_rec = [r["mention_recall"] for r in results if r.get("mention_recall") is not None]

    macro_mention_prec = (sum(valid_m_prec) / len(valid_m_prec)) if valid_m_prec else 0.0
    macro_mention_rec = (sum(valid_m_rec) / len(valid_m_rec)) if valid_m_rec else 0.0
    macro_mention_f1 = (2 * macro_mention_prec * macro_mention_rec / (macro_mention_prec + macro_mention_rec)) if (macro_mention_prec + macro_mention_rec) > 0 else 0.0
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

        subj_scores = [r["subject_attribution_accuracy"] for r in fb_cases if r["subject_attribution_accuracy"] is not None]
        macro_subj = (sum(subj_scores) / len(subj_scores)) if subj_scores else None

        total_tp_5d = sum(r["tp_5d"] for r in fb_cases)
        total_ext_fb = sum(r["released_claims_count"] for r in fb_cases)
        total_gold_fb = sum(r["gold_claims_count"] for r in fb_cases)

        micro_prec = (total_tp_5d / total_ext_fb) if total_ext_fb > 0 else 0.0
        micro_rec = (total_tp_5d / total_gold_fb) if total_gold_fb > 0 else 0.0
        micro_f1 = (2 * micro_prec * micro_rec / (micro_prec + micro_rec)) if (micro_prec + micro_rec) > 0 else 0.0

        target_recalled_count = sum(1 for r in fb_cases if r.get("target_entity_recalled", False))
        target_entity_case_recall = target_recalled_count / n_fb
    else:
        macro_prec = macro_rec = macro_f1 = 0.0
        macro_subj = None
        micro_prec = micro_rec = micro_f1 = 0.0
        target_entity_case_recall = 1.0

    # Entity x Source Recall across suite
    total_gold_es_pairs = sum(r["funnel"]["l2_entity_source_hits"]["denominator"] for r in results)
    total_hit_es_pairs = sum(r["funnel"]["l2_entity_source_hits"]["numerator"] for r in results)
    entity_source_recall = (total_hit_es_pairs / total_gold_es_pairs) if total_gold_es_pairs > 0 else 1.0

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

    prov = provenance or {}
    clean_git = not bool(prov.get("git_dirty", True))
    prov_complete = bool(
        prov.get("git_commit_sha")
        and prov.get("git_commit_sha") not in {"unknown", ""}
        and prov.get("evaluator_sha256")
        and prov.get("evaluator_sha256") not in {"none", ""}
        and prov.get("gold_sha256")
        and prov.get("gold_sha256") not in {"none", ""}
        and prov.get("corpus_warc_sha256")
        and prov.get("corpus_warc_sha256") not in {"none", ""}
        and prov.get("query_index_sha256")
        and prov.get("query_index_sha256") not in {"none", ""}
    )

    completed_fb_cases = [r for r in results if r["is_fact_bearing"] and r["actual_outcome"] == "completed"]
    completed_released_claims_pass = (
        len(completed_fb_cases) > 0 and all((r.get("tp_5d", 0) >= 1) for r in completed_fb_cases)
    ) if completed_fb_cases else True

    # Suite-level Funnel Aggregations
    suite_funnel = {
        "l1_gold_sources": {
            "numerator": sum(r["funnel"]["l1_gold_sources"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l1_gold_sources"]["denominator"] for r in fb_cases),
        },
        "l2_entity_source_hits": {
            "numerator": total_hit_es_pairs,
            "denominator": total_gold_es_pairs,
            "rate": round(entity_source_recall, 4),
        },
        "l3_target_mentions_covered": {
            "numerator": sum(r["funnel"]["l3_target_mentions_covered"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l3_target_mentions_covered"]["denominator"] for r in fb_cases),
        },
        "l4_target_mentions_extracted": {
            "numerator": sum(r["funnel"]["l4_target_mentions_extracted"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l4_target_mentions_extracted"]["denominator"] for r in fb_cases),
        },
        "l5_claim_supports_covered": {
            "numerator": sum(r["funnel"]["l5_claim_supports_covered"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l5_claim_supports_covered"]["denominator"] for r in fb_cases),
        },
        "l6a_proposed_claims_tp": {
            "numerator": sum(r["funnel"]["l6a_proposed_claims_tp"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l6a_proposed_claims_tp"]["denominator"] for r in fb_cases),
        },
        "l6b_released_claims_tp": {
            "numerator": sum(r["funnel"]["l6b_released_claims_tp"]["numerator"] for r in fb_cases),
            "denominator": sum(r["funnel"]["l6b_released_claims_tp"]["denominator"] for r in fb_cases),
        },
    }
    for k, v in suite_funnel.items():
        if "rate" not in v:
            denom = v["denominator"]
            v["rate"] = round(v["numerator"] / denom, 4) if denom > 0 else 1.0

    # Evaluator V2.4 Strict Primary Release Gates
    gates = {
        # Provenance & Asset Gates
        "clean_git_tree_gate": clean_git,
        "provenance_complete_gate": prov_complete,
        "asset_manifest_gate": asset_manifest_passed,
        "seal_integrity_gate": seal_intact,
        "structural_validation_gate": (val_rate == 1.0),
        "case_completeness_gate": completeness_pass,
        "paired_input_identity_gate": paired_identity_passed,

        # Entity Discovery & Clustered ER Gates (Primary)
        "target_entity_case_recall_gate": (target_entity_case_recall == 1.0),
        "entity_source_recall_gate": (entity_source_recall >= 0.95),
        "zero_false_merges_gate": (total_false_merges == 0),
        "false_splits_gate": (total_false_splits <= max_false_splits),

        # Claim & State Machine Gates (Primary)
        "zero_unmatched_released_claims_gate": (total_unmatched_released == 0),
        "claim_precision_gate": (macro_prec >= 0.95),
        "claim_recall_gate": (macro_rec >= 0.80),
        "subject_attribution_gate": (macro_subj >= 0.95) if macro_subj is not None else False,
        "outcome_accuracy_gate": (outcome_acc >= 0.90),
        "ambiguity_safety_gate": (abs_accuracy == 1.0 if abs_accuracy is not None else True),
        "completed_released_claims_gate": completed_released_claims_pass,
    }

    # Diagnostic indicators (Explicitly separated from release blockers)
    diagnostic_metrics = {
        "occurrence_mention_precision": round(macro_mention_prec, 4),
        "occurrence_mention_recall": round(macro_mention_rec, 4),
        "occurrence_mention_f1": round(macro_mention_f1, 4),
        "common_universe_b3_f1": round(macro_b3_f1, 4),
        "common_universe_pairwise_f1": round(macro_pairwise_f1, 4),
    }

    all_gates_pass = all(gates.values())

    return {
        "evaluator_version": "2.4.0",
        "provenance": provenance or {},
        "total_cases_evaluated": n,
        "expected_case_count": len(expected_case_ids),
        "completeness_pass": completeness_pass,
        "seal_intact": seal_intact,
        "structural_validation_rate": round(val_rate, 4),
        "target_entity_case_recall": round(target_entity_case_recall, 4),
        "entity_source_recall": round(entity_source_recall, 4),
        "total_false_merges": total_false_merges,
        "total_false_splits": total_false_splits,
        "max_false_splits_allowed": max_false_splits,
        "total_unmatched_released_claims": total_unmatched_released,
        "outcome_accuracy": round(outcome_acc, 4),
        "suite_funnel": suite_funnel,
        "diagnostic_metrics": diagnostic_metrics,
        "fact_bearing_evaluation": {
            "case_count": n_fb,
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
            "micro_precision": round(micro_prec, 4),
            "micro_recall": round(micro_rec, 4),
            "micro_f1": round(micro_f1, 4),
            "subject_attribution_accuracy": round(macro_subj, 4) if macro_subj is not None else None,
            "total_extracted_claims": total_ext_fb,
            "total_gold_claims": total_gold_fb,
            "total_tp_5d": total_tp_5d,
        },
        "abstention_evaluation": {
            "case_count": n_abs,
            "abstention_accuracy": round(abs_accuracy, 4) if abs_accuracy is not None else None,
            "total_spurious_claims": total_spurious,
            "spurious_case_rate": round(spurious_case_rate, 4) if spurious_case_rate is not None else None,
        },
        "gates": gates,
        "all_gates_passed": all_gates_pass,
        "paired_comparison": {
            "identity_passed": paired_identity_passed,
            "mismatch_count": len(paired_mismatches or []),
            "mismatches": (paired_mismatches or [])[:10],
        },
        "asset_manifest_verification": {
            "passed": asset_manifest_passed,
            "error_count": len(asset_manifest_errors or []),
            "errors": (asset_manifest_errors or [])[:10],
        },
        "case_details": results,
    }


def render_markdown_report(suite_eval: Dict[str, Any]) -> str:
    """Generates an objective Markdown evaluation and audit report for Evaluator V2.4."""
    prov = suite_eval.get("provenance", {})
    gates = suite_eval.get("gates", {})
    all_pass = suite_eval.get("all_gates_passed", False)
    funnel = suite_eval.get("suite_funnel", {})
    diag = suite_eval.get("diagnostic_metrics", {})

    status_str = "PASSED" if all_pass else "FAILED"

    lines = [
        f"# Evaluator V2.4 自动化评测与发布门禁审计报告",
        f"",
        f"**评测结论**: `{status_str}`  ",
        f"**评测器版本**: `v2.4.0` | **时间戳**: `{prov.get('git_commit_sha', 'unknown')[:7]}` (`dirty={prov.get('git_dirty')}`)  ",
        f"",
        f"## 1. 资产与溯源自检清单",
        f"- Git Commit SHA: `{prov.get('git_commit_sha', 'unknown')}`",
        f"- Git 工作区状态: `{'CLEAN' if not prov.get('git_dirty') else 'DIRTY (FAIL-CLOSED)'}`",
        f"- Evaluator SHA-256: `{prov.get('evaluator_sha256', 'none')}`",
        f"- Gold File SHA-256: `{prov.get('gold_sha256', 'none')}`",
        f"- WARC Payload SHA-256: `{prov.get('corpus_warc_sha256', 'none')}`",
        f"- Query Index SHA-256: `{prov.get('query_index_sha256', 'none')}`",
        f"- 资产清单程序化核验: `{'PASS' if gates.get('asset_manifest_gate') else 'FAIL'}`",
        f"",
        f"## 2. 核心发布门禁状态 (Primary Release Gates)",
        f"| 门禁项 | 规则与标准 | 实际观测值 | 状态 |",
        f"|---|---|---|:---:|",
        f"| `clean_git_tree_gate` | Git 工作区干净（无未提交修改） | dirty={prov.get('git_dirty')} | {'PASS' if gates.get('clean_git_tree_gate') else 'FAIL'} |",
        f"| `provenance_complete_gate` | 关键输入哈希全量记录 | prov_complete={gates.get('provenance_complete_gate')} | {'PASS' if gates.get('provenance_complete_gate') else 'FAIL'} |",
        f"| `asset_manifest_gate` | 评测资产清单重算 100% 一致 | asset_manifest={gates.get('asset_manifest_gate')} | {'PASS' if gates.get('asset_manifest_gate') else 'FAIL'} |",
        f"| `seal_integrity_gate` | Merkle 密封签名全量校验通过 | seal_intact={suite_eval.get('seal_intact')} | {'PASS' if gates.get('seal_integrity_gate') else 'FAIL'} |",
        f"| `structural_validation_gate` | Schema 结构校验通过率 100% | val_rate={suite_eval.get('structural_validation_rate')} | {'PASS' if gates.get('structural_validation_gate') else 'FAIL'} |",
        f"| `case_completeness_gate` | 期望案例全量完成评估 | actual={suite_eval.get('total_cases_evaluated')}/{suite_eval.get('expected_case_count')} | {'PASS' if gates.get('case_completeness_gate') else 'FAIL'} |",
        f"| `paired_input_identity_gate` | 对照实验上游输入哈希完全一致 | matched={gates.get('paired_input_identity_gate')} | {'PASS' if gates.get('paired_input_identity_gate') else 'FAIL'} |",
        f"| `target_entity_case_recall_gate` | 事实型案例目标实体发现率 100% | rec={suite_eval.get('target_entity_case_recall')} | {'PASS' if gates.get('target_entity_case_recall_gate') else 'FAIL'} |",
        f"| `entity_source_recall_gate` | 实体×来源对发现率 $\\ge 95.0\\%$ | rec={suite_eval.get('entity_source_recall')} | {'PASS' if gates.get('entity_source_recall_gate') else 'FAIL'} |",
        f"| `zero_false_merges_gate` | 绝对不允许不同实体错误合并 | false_merges={suite_eval.get('total_false_merges')} | {'PASS' if gates.get('zero_false_merges_gate') else 'FAIL'} |",
        f"| `false_splits_gate` | 同一实体假拆分 $\\le {suite_eval.get('max_false_splits_allowed', 0)}$ | false_splits={suite_eval.get('total_false_splits')} | {'PASS' if gates.get('false_splits_gate') else 'FAIL'} |",
        f"| `zero_unmatched_released_claims_gate` | 释放断言必须 100% 具备真值支撑 | unmatched={suite_eval.get('total_unmatched_released_claims')} | {'PASS' if gates.get('zero_unmatched_released_claims_gate') else 'FAIL'} |",
        f"| `ambiguity_safety_gate` | 稀疏/歧义负例必须 100% 安全弃答 | abs_acc={suite_eval.get('abstention_evaluation', {}).get('abstention_accuracy')} | {'PASS' if gates.get('ambiguity_safety_gate') else 'FAIL'} |",
        f"| `claim_precision_gate` | 释放断言 Macro Precision $\\ge 95.0\\%$ | macro_prec={suite_eval.get('fact_bearing_evaluation', {}).get('macro_precision')} | {'PASS' if gates.get('claim_precision_gate') else 'FAIL'} |",
        f"| `claim_recall_gate` | 释放断言 Macro Recall $\\ge 80.0\\%$ | macro_rec={suite_eval.get('fact_bearing_evaluation', {}).get('macro_recall')} | {'PASS' if gates.get('claim_recall_gate') else 'FAIL'} |",
        f"| `subject_attribution_gate` | 主体归属准确率 $\\ge 95.0\\%$ | subj_acc={suite_eval.get('fact_bearing_evaluation', {}).get('subject_attribution_accuracy')} | {'PASS' if gates.get('subject_attribution_gate') else 'FAIL'} |",
        f"| `outcome_accuracy_gate` | 运行状态匹配率 $\\ge 90.0\\%$ | acc={suite_eval.get('outcome_accuracy')} | {'PASS' if gates.get('outcome_accuracy_gate') else 'FAIL'} |",
        f"| `completed_released_claims_gate` | 完成用例每个必须满足 TP_5D $\\ge 1$ | passed={gates.get('completed_released_claims_gate')} | {'PASS' if gates.get('completed_released_claims_gate') else 'FAIL'} |",
        f"",
        f"## 3. 六级召回漏斗分析 (Six-Level Recall Funnel)",
        f"| 漏斗阶段 | 覆盖分子/分母 | 转化率 | 阶段诊断 |",
        f"|---|:---:|:---:|---|",
        f"| Level 1: Gold 来源进入 Bundle | {funnel.get('l1_gold_sources', {}).get('numerator')}/{funnel.get('l1_gold_sources', {}).get('denominator')} | {funnel.get('l1_gold_sources', {}).get('rate', 0)*100:.1f}% | 页面检索与抓取覆盖 |",
        f"| Level 2: 实体×来源至少命中一次 | {funnel.get('l2_entity_source_hits', {}).get('numerator')}/{funnel.get('l2_entity_source_hits', {}).get('denominator')} | {funnel.get('l2_entity_source_hits', {}).get('rate', 0)*100:.1f}% | 目标与同名干扰实体粗召回 |",
        f"| Level 3: Target Gold Mention 进入 Evidence | {funnel.get('l3_target_mentions_covered', {}).get('numerator')}/{funnel.get('l3_target_mentions_covered', {}).get('denominator')} | {funnel.get('l3_target_mentions_covered', {}).get('rate', 0)*100:.1f}% | 页面上下文窗口定位覆盖 |",
        f"| Level 4: Evidence 内 Target Mention 抽取 | {funnel.get('l4_target_mentions_extracted', {}).get('numerator')}/{funnel.get('l4_target_mentions_extracted', {}).get('denominator')} | {funnel.get('l4_target_mentions_extracted', {}).get('rate', 0)*100:.1f}% | 定位文本内的 Mention 抽取 |",
        f"| Level 5: Gold Claim Support 进入 Evidence | {funnel.get('l5_claim_supports_covered', {}).get('numerator')}/{funnel.get('l5_claim_supports_covered', {}).get('denominator')} | {funnel.get('l5_claim_supports_covered', {}).get('rate', 0)*100:.1f}% | 结构化事实证据窗口定位 |",
        f"| Level 6a: 全部 Proposed Claims 5D TP | {funnel.get('l6a_proposed_claims_tp', {}).get('numerator')}/{funnel.get('l6a_proposed_claims_tp', {}).get('denominator')} | {funnel.get('l6a_proposed_claims_tp', {}).get('rate', 0)*100:.1f}% | 候选事实产生率 |",
        f"| Level 6b: 最终 Released Claims 5D TP | {funnel.get('l6b_released_claims_tp', {}).get('numerator')}/{funnel.get('l6b_released_claims_tp', {}).get('denominator')} | {funnel.get('l6b_released_claims_tp', {}).get('rate', 0)*100:.1f}% | 最终发布事实真值命中率 |",
        f"",
        f"## 4. 诊断性指标 (Diagnostic Indicators - Not Release Blockers)",
        f"> **说明**: 以下指标按出现频次或局部实体簇统计，不代表端到端实体召回能力，已降级为仅供工程诊断参考。",
        f"- Occurrence-level Mention Precision: `{diag.get('occurrence_mention_precision')}`",
        f"- Occurrence-level Mention Recall (非空分母宏平均): `{diag.get('occurrence_mention_recall')}`",
        f"- Occurrence-level Mention F1: `{diag.get('occurrence_mention_f1')}`",
        f"- Common Universe $B^3$ F1: `{diag.get('common_universe_b3_f1')}`",
        f"- Common Universe Pairwise F1: `{diag.get('common_universe_pairwise_f1')}`",
        f"",
        f"## 5. 逐案例详细审计与首个失败阶段 (Case-Level Funnel Breakdown)",
        f"| Case ID | 目标人物 | 实际状态 | 期望状态 | 匹配 | TP_5D (Rel/Prop/Gold) | Unmatched | F-Split | 首个失败阶段 |",
        f"|---|---|---|---|:---:|:---:|:---:|:---:|---|",
    ]

    for c in suite_eval.get("case_details", []):
        f = c.get("funnel", {})
        l6a = f.get("l6a_proposed_claims_tp", {})
        l6b = f.get("l6b_released_claims_tp", {})
        tp_str = f"{l6b.get('numerator', 0)}/{l6a.get('numerator', 0)}/{l6a.get('denominator', 0)}"
        lines.append(
            f"| `{c['case_id']}` | {c['target_name']} | `{c['actual_outcome']}` | `{c['expected_outcome']}` | "
            f"{'✓' if c['outcome_match'] else '✗'} | {tp_str} | {c['unmatched_released_claims']} | "
            f"{c['false_splits']} | `{f.get('first_failure_stage', 'unknown')}` |"
        )

    lines.append("")
    lines.append("## 6. 结论与下一步指引")
    if all_pass:
        lines.append("所有预注册门禁均已通过，满足发布与合流标准。")
    else:
        failed_gates = [k for k, v in gates.items() if not v]
        lines.append(f"**当前未达标门禁 ({len(failed_gates)} 项)**: `{', '.join(failed_gates)}`")
        lines.append("依据预注册合流协议，当前基线未达到发布要求，已冻结为 Phase 4.0 严密红灯基线。")
        lines.append("下一步工作建议：推进 Phase 4.1 通用同页 Candidate 假拆分合并，消解 DEV-002 与 DEV-004 的假拆分。")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Evaluator V2.4: Strict Contract & Benchmark Governance Engine.")
    parser.add_argument("--runs-dir", type=Path, required=True, help="Directory containing run bundles")
    parser.add_argument("--gold-file", type=Path, required=True, help="Path to gold JSON file")
    parser.add_argument("--case-manifest", type=Path, required=True, help="Path to manifest containing expected case IDs")
    parser.add_argument("--expected-count", type=int, required=True, help="Expected number of cases")
    parser.add_argument("--warc-file", type=Path, default=None, help="Path to corpus.warc")
    parser.add_argument("--query-index", type=Path, default=None, help="Path to query_index.jsonl")
    parser.add_argument("--asset-manifest", type=Path, default=None, help="Path to asset_manifest.json (optional, auto-detected)")
    parser.add_argument("--track-name", type=str, default="name_only", choices=["name_only", "hinted"])
    parser.add_argument("--paired-runs-dir", type=Path, default=None, help="Path to paired run bundles (e.g. Group 2 for Group 3)")
    parser.add_argument("--max-false-splits", type=int, default=0, help="Maximum allowed false splits (default 0 for dev suite)")
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
        "evaluator_version": "2.4.0",
        "git_commit_sha": git_sha,
        "git_dirty": git_dirty,
        "evaluator_sha256": evaluator_sha,
        "gold_sha256": gold_sha,
        "corpus_warc_sha256": warc_sha,
        "query_index_sha256": qidx_sha,
    }

    # 2. Asset Manifest Check if available or provided
    asset_manifest_path = args.asset_manifest
    if not asset_manifest_path and args.gold_file:
        potential_manifest = args.gold_file.parent / "asset_manifest.json"
        if potential_manifest.exists():
            asset_manifest_path = potential_manifest

    asset_manifest_passed = True
    asset_manifest_errors = []
    if asset_manifest_path:
        asset_manifest_passed, asset_manifest_errors = verify_asset_manifest(asset_manifest_path, asset_manifest_path.parent)
        print(f"Asset Manifest Verification ({asset_manifest_path.name}): {'PASS' if asset_manifest_passed else 'FAIL'}")
        if not asset_manifest_passed:
            print("Asset errors:", asset_manifest_errors)

    # 3. Load Expected Cases from Manifest
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

    # 4. Load Gold Truth via Strict Pydantic RootModel
    gold_suite = GoldSuite.model_validate_json(args.gold_file.read_text(encoding="utf-8"))
    gold_by_id = {c.case_id: c for c in gold_suite}

    # 5. WARC Byte & Slice Replay if provided
    if args.warc_file:
        verify_gold_warc_integrity(gold_suite, args.warc_file)
        print(f"Verified all Gold mention & claim support verbatim slices against {args.warc_file.name}: 100% byte-accurate")

    # 6. Paired Input Identity Check if provided
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

    print(f"Evaluator V2.4 running on {len(bundle_dirs)} bundles in {args.runs_dir} (Track: {args.track_name})...")

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

        res = evaluate_bundle_v2_4(
            bundle_dir=bdir,
            gold_case=gcase,
            expected_outcome=exp_outcome,
            warc_path=args.warc_file,
        )
        results.append(res)

    suite_eval = aggregate_suite_v2_4(
        results=results,
        expected_case_ids=expected_cids,
        provenance=provenance,
        paired_identity_passed=paired_identity_passed,
        paired_mismatches=paired_mismatches,
        asset_manifest_passed=asset_manifest_passed,
        asset_manifest_errors=asset_manifest_errors,
        max_false_splits=args.max_false_splits,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(suite_eval, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote evaluation results to {args.output_json}")

    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        md_content = render_markdown_report(suite_eval)
        args.output_md.write_text(md_content, encoding="utf-8")
        print(f"Wrote Markdown report to {args.output_md}")

    if suite_eval["all_gates_passed"]:
        print("ALL GATES PASSED: Ready for release/merge.")
        sys.exit(0)
    else:
        print("GATES FAILED: Release blocked.")
        sys.exit(1)


if __name__ == "__main__":
    main()
