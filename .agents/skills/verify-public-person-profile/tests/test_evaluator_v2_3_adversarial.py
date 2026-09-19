"""
Comprehensive Adversarial Unit Test Suite for Evaluator V2.3.
Tests 17 adversarial attack and failure vectors:
1. Candidate order permutation invariance.
2. Homonym separation: Different entity IDs with identical names.
3. Missing source reference in mentions -> KeyError.
4. False split detection.
5. False merge detection.
6. Malformed JSONL line error -> JSONDecodeError.
7. Seal tampering -> seal_verified = False.
8. Case completeness gate failure.
9. Abstention case: spurious claims only counted if released in dossier.
10. CLI non-zero exit on gate failure.
11. Pydantic Gold validation: broken foreign key or inverted span raises ValidationError.
12. Pydantic Gold validation: incomplete gold_clusters partition raises ValidationError.
13. WARC payload verification: mention referencing missing payload raises ValueError.
14. Duplicate mention signature within mentions.jsonl raises ValueError fail-closed.
15. Mention referencing missing evidence_id raises KeyError fail-closed.
16. Evaluator V2.3: false_released_claims correctly captures ungrounded claims in completed cases.
17. Evaluator V2.3: paired_input_identity_gate fails closed on upstream input mismatch.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from benchmarks.tools.evaluator_v2_3 import (
    compute_bundle_tree_hash,
    evaluate_bundle_v2_3,
    aggregate_suite_v2_3,
    read_jsonl_strict,
    verify_gold_warc_integrity,
    verify_paired_input_identity,
)
from models.gold_schema_v2 import GoldCase, GoldSuite


def create_minimal_bundle_v2_3(
    bundle_dir: Path,
    outcome: str = "completed",
    candidate_id: str = None,
    sources: list = None,
    evidence: list = None,
    mentions: list = None,
    candidates: list = None,
    claims: list = None,
    dossier_claims: list = None,
) -> Path:
    """Helper to generate a minimal sealed bundle compliant with Evaluator V2.3."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(json.dumps({"run_outcome": outcome}), encoding="utf-8")

    cand_id = candidate_id
    if not cand_id:
        if candidates:
            cand_id = candidates[0].get("candidate_entity_id", "CAND-1")
        else:
            cand_id = "CAND-1"

    rel_cids = dossier_claims if dossier_claims is not None else ([c["claim_id"] for c in (claims or [])])
    statements = [
        {"statement_id": f"STMT-{i}", "text": f"Fact statement {i}", "backed_claim_ids": [cid]}
        for i, cid in enumerate(rel_cids)
    ]

    dossier = {
        "dossier_id": f"DOS-{bundle_dir.name}",
        "candidate_entity_id": cand_id,
        "target_name": "Target",
        "confidence_score": 0.9,
        "run_outcome": outcome,
        "claims": rel_cids,
        "statements": statements,
    }
    (bundle_dir / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")

    def write_jsonl(filename: str, records: list):
        lines = [json.dumps(r) for r in (records or [])]
        content = "\n".join(lines) + ("\n" if lines else "")
        (bundle_dir / filename).write_text(content, encoding="utf-8")

    if mentions and not evidence:
        evidence = [
            {"evidence_id": m.get("evidence_id", "EVI-1"), "source_id": m.get("source_id", "SRC-1"), "verbatim_excerpt": "...", "char_start": 0, "char_end": 100}
            for m in mentions
        ]

    write_jsonl("sources.jsonl", sources or [])
    write_jsonl("evidence.jsonl", evidence or [])
    write_jsonl("mentions.jsonl", mentions or [])
    write_jsonl("candidates.jsonl", candidates or [])
    write_jsonl("claims.jsonl", claims or [])
    write_jsonl("clusters.jsonl", [{"cluster_id": "CLU-1", "candidate_entity_id": cand_id, "mention_ids": [m["mention_id"] for m in (mentions or [])]}])

    tree_hash = compute_bundle_tree_hash(bundle_dir)
    (bundle_dir / "seal.json").write_text(json.dumps({"bundle_tree_hash": tree_hash}), encoding="utf-8")
    return bundle_dir


def test_adversarial_1_candidate_permutation():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b1 = td / "b1"
        b2 = td / "b2"

        sources = [{"source_id": "SRC-1", "content_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [
            {"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"},
            {"mention_id": "M-2", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 10, "char_end": 13, "raw_name_text": "Bob"},
        ]
        cands_a = [
            {"candidate_entity_id": "CAND-A", "mention_ids": ["M-1"]},
            {"candidate_entity_id": "CAND-B", "mention_ids": ["M-2"]},
        ]
        cands_b = [
            {"candidate_entity_id": "CAND-B", "mention_ids": ["M-2"]},
            {"candidate_entity_id": "CAND-A", "mention_ids": ["M-1"]},
        ]
        claims = [
            {"claim_id": "C-1", "candidate_entity_id": "CAND-A", "predicate": "holds_position", "object_raw": "Prof", "polarity": "affirmative", "temporal_status": "current"}
        ]

        create_minimal_bundle_v2_3(b1, candidate_id="CAND-A", sources=sources, evidence=evidence, mentions=mentions, candidates=cands_a, claims=claims)
        create_minimal_bundle_v2_3(b2, candidate_id="CAND-A", sources=sources, evidence=evidence, mentions=mentions, candidates=cands_b, claims=claims)

        gcase = GoldCase(
            case_id="ADV-01",
            target_name="Alice",
            is_fact_bearing=True,
            gold_entities=[
                {"gold_entity_id": "ENT-ALICE", "canonical_name": "Alice"},
                {"gold_entity_id": "ENT-BOB", "canonical_name": "Bob"},
            ],
            gold_mentions=[
                {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-ALICE", "source_content_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "char_start": 0, "char_end": 5, "verbatim_text": "Alice"},
                {"gold_mention_id": "GM-2", "gold_entity_id": "ENT-BOB", "source_content_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "char_start": 10, "char_end": 13, "verbatim_text": "Bob"},
            ],
            gold_clusters=[["GM-1"], ["GM-2"]],
            gold_claims=[
                {"claim_id": "GC-1", "subject_gold_entity_id": "ENT-ALICE", "predicate": "holds_position", "object_raw": "Prof", "polarity": "affirmative", "temporal_status": "current"}
            ],
        )

        r1 = evaluate_bundle_v2_3(b1, gcase, "completed")
        r2 = evaluate_bundle_v2_3(b2, gcase, "completed")
        assert r1["tp_5d"] == r2["tp_5d"] == 1
        assert r1["false_released_claims"] == r2["false_released_claims"] == 0


def test_adversarial_2_homonym_separation():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [
            {"source_id": "SRC-A", "content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
            {"source_id": "SRC-B", "content_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        ]
        evidence = [
            {"evidence_id": "EVI-A", "source_id": "SRC-A", "char_start": 0, "char_end": 20},
            {"evidence_id": "EVI-B", "source_id": "SRC-B", "char_start": 0, "char_end": 20},
        ]
        mentions = [
            {"mention_id": "M-A", "source_id": "SRC-A", "evidence_id": "EVI-A", "char_start": 0, "char_end": 8, "raw_name_text": "John Doe"},
            {"mention_id": "M-B", "source_id": "SRC-B", "evidence_id": "EVI-B", "char_start": 0, "char_end": 8, "raw_name_text": "John Doe"},
        ]
        candidates = [
            {"candidate_entity_id": "CAND-MIT", "mention_ids": ["M-B"]},
        ]
        claims = [
            {"claim_id": "C-1", "candidate_entity_id": "CAND-MIT", "predicate": "holds_position", "object_raw": "Stanford Prof", "polarity": "affirmative", "temporal_status": "current"}
        ]
        create_minimal_bundle_v2_3(b, candidate_id="CAND-MIT", sources=sources, evidence=evidence, mentions=mentions, candidates=candidates, claims=claims)

        gcase = GoldCase(
            case_id="ADV-02",
            target_name="John Doe",
            is_fact_bearing=True,
            gold_entities=[
                {"gold_entity_id": "ENT-STANFORD", "canonical_name": "John Doe"},
                {"gold_entity_id": "ENT-MIT", "canonical_name": "John Doe"},
            ],
            gold_mentions=[
                {"gold_mention_id": "GM-A", "gold_entity_id": "ENT-STANFORD", "source_content_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "char_start": 0, "char_end": 8, "verbatim_text": "John Doe"},
                {"gold_mention_id": "GM-B", "gold_entity_id": "ENT-MIT", "source_content_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "char_start": 0, "char_end": 8, "verbatim_text": "John Doe"},
            ],
            gold_clusters=[["GM-A"], ["GM-B"]],
            gold_claims=[
                {"claim_id": "GC-1", "subject_gold_entity_id": "ENT-STANFORD", "predicate": "holds_position", "object_raw": "Stanford Prof", "polarity": "affirmative", "temporal_status": "current"}
            ],
        )

        res = evaluate_bundle_v2_3(b, gcase, "completed")
        assert res["tp_5d"] == 0
        assert res["tp_4d_diag"] == 1
        assert res["false_released_claims"] == 1


def test_adversarial_3_missing_source_keyerror():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        mentions = [{"mention_id": "M-1", "source_id": "SRC-MISSING", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"}]
        create_minimal_bundle_v2_3(b, mentions=mentions)

        gcase = GoldCase(case_id="ADV-03", target_name="Alice", is_fact_bearing=False)
        with pytest.raises(KeyError, match="FAIL-CLOSED: Mention M-1 references missing source SRC-MISSING"):
            evaluate_bundle_v2_3(b, gcase, "completed")


def test_adversarial_4_false_split_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [
            {"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"},
            {"mention_id": "M-2", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 10, "char_end": 15, "raw_name_text": "Alice"},
        ]
        candidates = [
            {"candidate_entity_id": "CAND-1", "mention_ids": ["M-1"]},
            {"candidate_entity_id": "CAND-2", "mention_ids": ["M-2"]},
        ]
        create_minimal_bundle_v2_3(b, sources=sources, evidence=evidence, mentions=mentions, candidates=candidates)

        gcase = GoldCase(
            case_id="ADV-04",
            target_name="Alice",
            is_fact_bearing=False,
            gold_entities=[{"gold_entity_id": "ENT-ALICE", "canonical_name": "Alice"}],
            gold_mentions=[
                {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-ALICE", "source_content_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "char_start": 0, "char_end": 5, "verbatim_text": "Alice"},
                {"gold_mention_id": "GM-2", "gold_entity_id": "ENT-ALICE", "source_content_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", "char_start": 10, "char_end": 15, "verbatim_text": "Alice"},
            ],
            gold_clusters=[["GM-1", "GM-2"]],
        )

        res = evaluate_bundle_v2_3(b, gcase, "completed")
        assert res["false_splits"] == 1


def test_adversarial_5_false_merge_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [
            {"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"},
            {"mention_id": "M-2", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 10, "char_end": 13, "raw_name_text": "Bob"},
        ]
        candidates = [{"candidate_entity_id": "CAND-MERGED", "mention_ids": ["M-1", "M-2"]}]
        create_minimal_bundle_v2_3(b, sources=sources, evidence=evidence, mentions=mentions, candidates=candidates)

        gcase = GoldCase(
            case_id="ADV-05",
            target_name="Alice",
            is_fact_bearing=False,
            gold_entities=[
                {"gold_entity_id": "ENT-ALICE", "canonical_name": "Alice"},
                {"gold_entity_id": "ENT-BOB", "canonical_name": "Bob"},
            ],
            gold_mentions=[
                {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-ALICE", "source_content_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd", "char_start": 0, "char_end": 5, "verbatim_text": "Alice"},
                {"gold_mention_id": "GM-2", "gold_entity_id": "ENT-BOB", "source_content_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd", "char_start": 10, "char_end": 13, "verbatim_text": "Bob"},
            ],
            gold_clusters=[["GM-1"], ["GM-2"]],
        )

        res = evaluate_bundle_v2_3(b, gcase, "completed")
        assert res["false_merges"] == 1


def test_adversarial_6_malformed_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        bad_f = td / "bad.jsonl"
        bad_f.write_text('{"ok": 1}\n{"bad":', encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_jsonl_strict(bad_f)


def test_adversarial_7_seal_tampering():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        create_minimal_bundle_v2_3(b)

        gcase = GoldCase(case_id="ADV-07", target_name="Alice", is_fact_bearing=False)
        res1 = evaluate_bundle_v2_3(b, gcase, "completed")
        assert res1["seal_verified"]

        (b / "manifest.json").write_text(json.dumps({"run_outcome": "tampered"}), encoding="utf-8")
        res2 = evaluate_bundle_v2_3(b, gcase, "completed")
        assert not res2["seal_verified"]


def test_adversarial_8_case_completeness_gate():
    results = [
        {"case_id": f"C-{i}", "is_fact_bearing": False, "seal_verified": True, "validation_passed": True, "outcome_match": True,
         "mention_precision": 1.0, "mention_recall": 1.0, "mention_f1": 1.0, "er_b3_f1": 1.0, "er_pairwise_f1": 1.0,
         "false_merges": 0, "false_splits": 0, "false_released_claims": 0, "spurious_claims": 0, "spurious_rate": 0.0, "abstention_accuracy": 1.0}
        for i in range(4)
    ]
    suite = aggregate_suite_v2_3(results, expected_case_ids=[f"C-{i}" for i in range(5)])
    assert not suite["completeness_pass"]
    assert not suite["gates"]["case_completeness_gate"]
    assert not suite["all_gates_passed"]


def test_adversarial_9_abstention_spurious_claims_distinction():
    """Attack 9: Pipeline proposed claims in cluster, but dossier correctly omitted them -> 0 spurious."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [{"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"}]
        candidates = [{"candidate_entity_id": "CAND-1", "mention_ids": ["M-1"]}]
        proposed_claims = [{"claim_id": "C-1", "candidate_entity_id": "CAND-1", "predicate": "p", "object_raw": "o", "polarity": "affirmative", "temporal_status": "current"}]

        # dossier_claims is EMPTY!
        create_minimal_bundle_v2_3(b, outcome="ambiguous_identity", sources=sources, evidence=evidence, mentions=mentions, candidates=candidates, claims=proposed_claims, dossier_claims=[])

        gcase = GoldCase(case_id="ADV-09", target_name="Alice", is_fact_bearing=False)
        res = evaluate_bundle_v2_3(b, gcase, "ambiguous_identity")
        assert res["false_released_claims"] == 0
        assert res["spurious_claims"] == 0


def test_adversarial_10_cli_exit_code_on_gate_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        runs_dir = td / "runs"
        b1 = runs_dir / "C-01"
        create_minimal_bundle_v2_3(b1)

        gcase = {
            "case_id": "C-01",
            "target_name": "Target",
            "is_fact_bearing": True,
            "gold_entities": [{"gold_entity_id": "ENT-1", "canonical_name": "Target"}],
            "gold_mentions": [],
            "gold_clusters": [],
            "gold_claims": [{"claim_id": "GC-1", "subject_gold_entity_id": "ENT-1", "predicate": "p", "object_raw": "o", "polarity": "affirmative", "temporal_status": "current"}],
        }
        gold_file = td / "gold_v2.json"
        gold_file.write_text(json.dumps([gcase]), encoding="utf-8")

        manifest_file = td / "manifest.json"
        manifest_file.write_text(json.dumps([{"case_id": "C-01"}]), encoding="utf-8")

        cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent.parent / "benchmarks" / "tools" / "evaluator_v2_3.py"),
            "--runs-dir", str(runs_dir),
            "--gold-file", str(gold_file),
            "--case-manifest", str(manifest_file),
            "--expected-count", "1",
            "--output-json", str(td / "out.json"),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 1


def test_adversarial_11_pydantic_gold_validation_failure():
    """Attack 11: Broken foreign key in GoldCase raises ValidationError."""
    broken_case = {
        "case_id": "ADV-11",
        "target_name": "Broken",
        "is_fact_bearing": True,
        "gold_entities": [{"gold_entity_id": "ENT-1", "canonical_name": "Valid"}],
        "gold_mentions": [
            {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-UNKNOWN", "source_content_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "char_start": 0, "char_end": 5, "verbatim_text": "Txt"}
        ],
        "gold_clusters": [["GM-1"]],
        "gold_claims": [],
    }
    with pytest.raises(ValidationError):
        GoldSuite.model_validate_json(json.dumps([broken_case]))


def test_adversarial_12_pydantic_gold_clusters_partition_failure():
    """Attack 12: Incomplete cluster partition raises ValidationError."""
    broken_case = {
        "case_id": "ADV-12",
        "target_name": "Broken Clusters",
        "is_fact_bearing": False,
        "gold_entities": [{"gold_entity_id": "ENT-1", "canonical_name": "Valid"}],
        "gold_mentions": [
            {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-1", "source_content_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "char_start": 0, "char_end": 5, "verbatim_text": "M1"},
            {"gold_mention_id": "GM-2", "gold_entity_id": "ENT-1", "source_content_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "char_start": 10, "char_end": 15, "verbatim_text": "M2"},
        ],
        "gold_clusters": [["GM-1"]],  # GM-2 omitted!
        "gold_claims": [],
    }
    with pytest.raises(ValidationError, match="Gold clusters do not fully partition mentions"):
        GoldSuite.model_validate_json(json.dumps([broken_case]))


def test_adversarial_13_warc_payload_sha_mismatch():
    """Attack 13: Mention references SHA not present in WARC file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        dummy_warc = td / "dummy.warc"
        dummy_warc.write_bytes(b"WARC/1.0\r\nWARC-Type: response\r\nContent-Length: 10\r\n\r\nHTTP/1.1 200 OK\r\n\r\nhello world")

        suite = GoldSuite([
            GoldCase(
                case_id="ADV-13",
                target_name="Target",
                is_fact_bearing=False,
                gold_entities=[{"gold_entity_id": "ENT-1", "canonical_name": "T"}],
                gold_mentions=[
                    {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-1", "source_content_sha256": "0000000000000000000000000000000000000000000000000000000000000000", "char_start": 0, "char_end": 1, "verbatim_text": "T"}
                ],
                gold_clusters=[["GM-1"]],
            )
        ])
        with pytest.raises(ValueError, match="Gold mentions reference missing WARC payloads"):
            verify_gold_warc_integrity(suite, dummy_warc)


def test_adversarial_14_duplicate_mention_signature_fail_closed():
    """Attack 14: Duplicate mention signatures inside mentions.jsonl raise ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "1111111111111111111111111111111111111111111111111111111111111111"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [
            {"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"},
            {"mention_id": "M-2", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"},
        ]
        create_minimal_bundle_v2_3(b, sources=sources, evidence=evidence, mentions=mentions)

        gcase = GoldCase(case_id="ADV-14", target_name="Alice", is_fact_bearing=False)
        with pytest.raises(ValueError, match="Duplicate mention signature"):
            evaluate_bundle_v2_3(b, gcase, "completed")


def test_adversarial_15_missing_evidence_reference_fail_closed():
    """Attack 15: Mention referencing missing evidence_id raises KeyError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "2222222222222222222222222222222222222222222222222222222222222222"}]
        evidence = [{"evidence_id": "EVI-VALID", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [
            {"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-MISSING", "char_start": 0, "char_end": 5, "raw_name_text": "Alice"}
        ]
        create_minimal_bundle_v2_3(b, sources=sources, evidence=evidence, mentions=mentions)

        gcase = GoldCase(case_id="ADV-15", target_name="Alice", is_fact_bearing=False)
        with pytest.raises(KeyError, match="references missing evidence EVI-MISSING"):
            evaluate_bundle_v2_3(b, gcase, "completed")


def test_adversarial_16_false_released_claims_completed_zero_tp():
    """Attack 16: Completed case releases 2 claims with 0 true matches -> false_released_claims == 2."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        b = td / "bundle"
        sources = [{"source_id": "SRC-1", "content_sha256": "3333333333333333333333333333333333333333333333333333333333333333"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions = [{"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Target"}]
        candidates = [{"candidate_entity_id": "CAND-1", "mention_ids": ["M-1"]}]
        # 2 released claims that do not match Gold object
        claims = [
            {"claim_id": "C-1", "candidate_entity_id": "CAND-1", "predicate": "holds_position", "object_raw": "Wrong Role 1", "polarity": "affirmative", "temporal_status": "current"},
            {"claim_id": "C-2", "candidate_entity_id": "CAND-1", "predicate": "holds_position", "object_raw": "Wrong Role 2", "polarity": "affirmative", "temporal_status": "current"},
        ]
        create_minimal_bundle_v2_3(b, candidate_id="CAND-1", sources=sources, evidence=evidence, mentions=mentions, candidates=candidates, claims=claims)

        gcase = GoldCase(
            case_id="ADV-16",
            target_name="Target",
            is_fact_bearing=True,
            gold_entities=[{"gold_entity_id": "ENT-1", "canonical_name": "Target"}],
            gold_mentions=[
                {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-1", "source_content_sha256": "3333333333333333333333333333333333333333333333333333333333333333", "char_start": 0, "char_end": 5, "verbatim_text": "Target"},
            ],
            gold_clusters=[["GM-1"]],
            gold_claims=[
                {"claim_id": "GC-1", "subject_gold_entity_id": "ENT-1", "predicate": "holds_position", "object_raw": "True Role", "polarity": "affirmative", "temporal_status": "current"}
            ],
        )

        res = evaluate_bundle_v2_3(b, gcase, "completed")
        assert res["tp_5d"] == 0
        assert res["released_claims_count"] == 2
        assert res["false_released_claims"] == 2

        suite = aggregate_suite_v2_3([res], expected_case_ids=["ADV-16"])
        assert suite["total_false_released_claims"] == 2
        assert not suite["gates"]["zero_false_released_claims_gate"]
        assert not suite["all_gates_passed"]


def test_adversarial_17_paired_input_identity_gate():
    """Attack 17: Paired input verification detects upstream mismatch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        g2_dir = td / "g2"
        g3_dir = td / "g3"
        b_g2 = g2_dir / "CASE-01"
        b_g3 = g3_dir / "CASE-01"

        sources = [{"source_id": "SRC-1", "content_sha256": "4444444444444444444444444444444444444444444444444444444444444444"}]
        evidence = [{"evidence_id": "EVI-1", "source_id": "SRC-1", "char_start": 0, "char_end": 50}]
        mentions_g2 = [{"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Target"}]
        mentions_g3 = [{"mention_id": "M-1", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 0, "char_end": 5, "raw_name_text": "Target"}]

        create_minimal_bundle_v2_3(b_g2, sources=sources, evidence=evidence, mentions=mentions_g2)
        create_minimal_bundle_v2_3(b_g3, sources=sources, evidence=evidence, mentions=mentions_g3)

        # Identical inputs pass
        ok, errs = verify_paired_input_identity(g2_dir, g3_dir, "CASE-01")
        assert ok
        assert len(errs) == 0

        # Tampered upstream mention in G3 fails closed
        tampered_mentions = mentions_g3 + [{"mention_id": "M-TAMPER", "source_id": "SRC-1", "evidence_id": "EVI-1", "char_start": 10, "char_end": 20, "raw_name_text": "Phantom"}]
        (b_g3 / "mentions.jsonl").write_text("\n".join(json.dumps(m) for m in tampered_mentions) + "\n", encoding="utf-8")

        ok2, errs2 = verify_paired_input_identity(g2_dir, g3_dir, "CASE-01")
        assert not ok2
        assert len(errs2) > 0
