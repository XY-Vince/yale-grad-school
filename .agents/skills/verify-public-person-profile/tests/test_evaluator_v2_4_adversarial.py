"""
Adversarial Test Suite for Evaluator V2.4 and Gold Schema V2.2.
Tests cover:
1. Schema V2.2 strict enforcement of non-empty supports and semantic anchors.
2. Evaluator V2.4 strict WARC byte, URL, and slice integrity (fail-closed).
3. Evaluator V2.4 programmatic asset manifest verification.
4. Evaluator V2.4 occurrence-level mention macro denominator correction (N/A handling).
5. Evaluator V2.4 new primary benchmark gates (target recall, entity-source recall, false splits).
6. Evaluator V2.4 six-level funnel metrics and first-failure-stage attribution.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmarks.tools.evaluator_v2_4 import (
    aggregate_suite_v2_4,
    compute_bundle_tree_hash,
    compute_case_funnel,
    evaluate_bundle_v2_4,
    verify_asset_manifest,
    verify_gold_warc_integrity,
)
from models.gold_schema_v2 import GoldCase, GoldClaim, GoldClaimSupport, GoldSuite


def test_schema_v2_2_rejects_empty_supports():
    """V2.4 / Schema V2.2 Rule: A GoldClaim must have at least one support span."""
    with pytest.raises(ValidationError):
        GoldClaim(
            claim_id="C-ERR",
            subject_gold_entity_id="ENT-1",
            predicate="holds_position",
            object_raw="Professor",
            polarity="affirmative",
            temporal_status="current",
            supports=[],
        )


def test_schema_v2_2_accepts_valid_supports_with_anchors():
    """Schema V2.2 accepts valid support spans with optional semantic anchors."""
    sup = GoldClaimSupport(
        source_url="https://example.com/profile",
        source_content_sha256="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        char_start=10,
        char_end=20,
        verbatim_text="Professor X",
        subject_anchor="X",
        relation_anchor="Professor",
        object_anchor="Professor",
        dom_container="div.profile-header",
    )
    claim = GoldClaim(
        claim_id="C-OK",
        subject_gold_entity_id="ENT-1",
        predicate="holds_position",
        object_raw="Professor",
        polarity="affirmative",
        temporal_status="current",
        supports=[sup],
    )
    assert claim.supports[0].subject_anchor == "X"
    assert claim.supports[0].dom_container == "div.profile-header"


def test_warc_replay_verbatim_slice_mismatch_fails_closed():
    """Evaluator V2.4 rejects off-by-one or mismatched verbatim text slices against WARC."""
    real_fixtures = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures" / "real_web_dev_v2"
    warc_file = real_fixtures / "corpus.warc"
    gold_file = real_fixtures / "gold_v2_2.json"

    suite = GoldSuite.model_validate_json(gold_file.read_text(encoding="utf-8"))

    # Verify original gold passes
    verify_gold_warc_integrity(suite, warc_file)

    # Tamper with one character in verbatim_text
    tampered_cases = [c.model_dump() for c in suite]
    tampered_cases[0]["gold_mentions"][0]["verbatim_text"] += "TAMPER"
    tampered_suite = GoldSuite.model_validate(tampered_cases)

    with pytest.raises(ValueError, match="verbatim slice mismatch"):
        verify_gold_warc_integrity(tampered_suite, warc_file)


def test_warc_replay_url_mismatch_fails_closed():
    """Evaluator V2.4 rejects claim support URL mismatch against WARC record target URI."""
    real_fixtures = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures" / "real_web_dev_v2"
    warc_file = real_fixtures / "corpus.warc"
    gold_file = real_fixtures / "gold_v2_2.json"

    suite = GoldSuite.model_validate_json(gold_file.read_text(encoding="utf-8"))

    tampered_cases = [c.model_dump() for c in suite]
    tampered_cases[0]["gold_claims"][0]["supports"][0]["source_url"] = "https://wrong-domain.org/tampered"
    tampered_suite = GoldSuite.model_validate(tampered_cases)

    with pytest.raises(ValueError, match="support URL mismatch"):
        verify_gold_warc_integrity(tampered_suite, warc_file)


def test_warc_replay_missing_sha_fails_closed():
    """Evaluator V2.4 rejects unknown SHA-256 in gold mentions or claim supports."""
    real_fixtures = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures" / "real_web_dev_v2"
    warc_file = real_fixtures / "corpus.warc"
    gold_file = real_fixtures / "gold_v2_2.json"

    suite = GoldSuite.model_validate_json(gold_file.read_text(encoding="utf-8"))

    tampered_cases = [c.model_dump() for c in suite]
    tampered_cases[0]["gold_mentions"][0]["source_content_sha256"] = "9999999999999999999999999999999999999999999999999999999999999999"
    tampered_suite = GoldSuite.model_validate(tampered_cases)

    with pytest.raises(ValueError, match="missing from WARC"):
        verify_gold_warc_integrity(tampered_suite, warc_file)


def test_asset_manifest_verification_passes_on_fixtures():
    """Evaluator V2.4 verify_asset_manifest passes on untouched fixture files."""
    fixtures_dir = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures" / "real_web_dev_v2"
    manifest_path = fixtures_dir / "asset_manifest.json"

    ok, errors = verify_asset_manifest(manifest_path, fixtures_dir)
    assert ok, f"Asset manifest verification failed: {errors}"
    assert len(errors) == 0


def test_asset_manifest_verification_detects_tampering():
    """Evaluator V2.4 verify_asset_manifest detects SHA-256 and size tampering."""
    with tempfile.TemporaryDirectory() as tmpdir:
        td = Path(tmpdir)
        f1 = td / "file1.txt"
        f1.write_text("hello world", encoding="utf-8")
        h1 = hashlib.sha256(f1.read_bytes()).hexdigest()

        manifest_path = td / "asset_manifest.json"
        manifest_data = {
            "file1.txt": {"sha256": h1, "bytes": len(f1.read_bytes())},
            "file2.txt": {"sha256": "aaaa", "bytes": 10},
        }
        manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

        # Missing file2.txt
        ok, errors = verify_asset_manifest(manifest_path, td)
        assert not ok
        assert any("Missing declared asset" in e for e in errors)

        # Create file2 with wrong content
        f2 = td / "file2.txt"
        f2.write_text("bad data", encoding="utf-8")
        ok, errors = verify_asset_manifest(manifest_path, td)
        assert not ok
        assert any("SHA-256 mismatch" in e for e in errors)


def test_occurrence_mention_metrics_exclude_zero_gold_mentions():
    """Non-fact-bearing cases with zero gold mentions do not dilute or inflate occurrence macro metrics."""
    res_with_gold = {
        "case_id": "C-1",
        "is_fact_bearing": True,
        "mention_precision": 0.8,
        "mention_recall": 0.6,
        "er_b3_f1": 1.0,
        "er_pairwise_f1": 1.0,
        "false_merges": 0,
        "false_splits": 0,
        "unmatched_released_claims": 0,
        "released_claims_count": 1,
        "gold_claims_count": 1,
        "tp_5d": 1,
        "actual_outcome": "completed",
        "expected_outcome": "completed",
        "outcome_match": True,
        "claim_precision": 1.0,
        "claim_recall": 1.0,
        "subject_attribution_accuracy": 1.0,
        "seal_verified": True,
        "validation_passed": True,
        "funnel": {
            "l1_gold_sources": {"numerator": 1, "denominator": 1},
            "l2_entity_source_hits": {"numerator": 1, "denominator": 1},
            "l3_target_mentions_covered": {"numerator": 1, "denominator": 1},
            "l4_target_mentions_extracted": {"numerator": 1, "denominator": 1},
            "l5_claim_supports_covered": {"numerator": 1, "denominator": 1},
            "l6a_proposed_claims_tp": {"numerator": 1, "denominator": 1},
            "l6b_released_claims_tp": {"numerator": 1, "denominator": 1},
        },
    }
    res_zero_gold = {
        "case_id": "C-2",
        "is_fact_bearing": False,
        "mention_precision": None,
        "mention_recall": None,
        "er_b3_f1": 1.0,
        "er_pairwise_f1": 1.0,
        "false_merges": 0,
        "false_splits": 0,
        "unmatched_released_claims": 0,
        "released_claims_count": 0,
        "gold_claims_count": 0,
        "tp_5d": 0,
        "actual_outcome": "insufficient_evidence",
        "expected_outcome": "insufficient_evidence",
        "outcome_match": True,
        "claim_precision": None,
        "claim_recall": None,
        "subject_attribution_accuracy": None,
        "abstention_accuracy": 1.0,
        "spurious_claims": 0,
        "spurious_rate": 0.0,
        "seal_verified": True,
        "validation_passed": True,
        "funnel": {
            "l1_gold_sources": {"numerator": 0, "denominator": 0},
            "l2_entity_source_hits": {"numerator": 0, "denominator": 0},
            "l3_target_mentions_covered": {"numerator": 0, "denominator": 0},
            "l4_target_mentions_extracted": {"numerator": 0, "denominator": 0},
            "l5_claim_supports_covered": {"numerator": 0, "denominator": 0},
            "l6a_proposed_claims_tp": {"numerator": 0, "denominator": 0},
            "l6b_released_claims_tp": {"numerator": 0, "denominator": 0},
        },
    }

    suite = aggregate_suite_v2_4([res_with_gold, res_zero_gold], expected_case_ids=["C-1", "C-2"])
    diag = suite["diagnostic_metrics"]
    # Should be exactly 0.6 (from C-1 only), NOT (0.6 + 1.0)/2 = 0.8
    assert diag["occurrence_mention_recall"] == 0.6
    assert diag["occurrence_mention_precision"] == 0.8


def test_false_splits_gate_blocks_release():
    """Evaluator V2.4 fails false_splits_gate when total false splits exceeds max_false_splits."""
    res = {
        "case_id": "C-1",
        "is_fact_bearing": True,
        "mention_precision": 1.0,
        "mention_recall": 1.0,
        "er_b3_f1": 1.0,
        "er_pairwise_f1": 1.0,
        "false_merges": 0,
        "false_splits": 2,  # 2 false splits
        "unmatched_released_claims": 0,
        "released_claims_count": 1,
        "gold_claims_count": 1,
        "tp_5d": 1,
        "actual_outcome": "completed",
        "expected_outcome": "completed",
        "outcome_match": True,
        "claim_precision": 1.0,
        "claim_recall": 1.0,
        "subject_attribution_accuracy": 1.0,
        "seal_verified": True,
        "validation_passed": True,
        "funnel": {
            "l1_gold_sources": {"numerator": 1, "denominator": 1},
            "l2_entity_source_hits": {"numerator": 1, "denominator": 1},
            "l3_target_mentions_covered": {"numerator": 1, "denominator": 1},
            "l4_target_mentions_extracted": {"numerator": 1, "denominator": 1},
            "l5_claim_supports_covered": {"numerator": 1, "denominator": 1},
            "l6a_proposed_claims_tp": {"numerator": 1, "denominator": 1},
            "l6b_released_claims_tp": {"numerator": 1, "denominator": 1},
        },
    }
    suite_strict = aggregate_suite_v2_4([res], expected_case_ids=["C-1"], max_false_splits=0)
    assert not suite_strict["gates"]["false_splits_gate"]

    suite_lenient = aggregate_suite_v2_4([res], expected_case_ids=["C-1"], max_false_splits=2)
    assert suite_lenient["gates"]["false_splits_gate"]


def test_six_level_funnel_first_failure_attribution():
    """Evaluator V2.4 compute_case_funnel correctly identifies first failure stage."""
    gcase = GoldCase(
        case_id="ADV-FUNNEL",
        target_name="Target Person",
        target_gold_entity_id="ENT-1",
        is_fact_bearing=True,
        gold_entities=[{"gold_entity_id": "ENT-1", "canonical_name": "Target Person"}],
        gold_mentions=[
            {"gold_mention_id": "GM-1", "gold_entity_id": "ENT-1", "source_content_sha256": "1111111111111111111111111111111111111111111111111111111111111111", "char_start": 10, "char_end": 23, "verbatim_text": "Target Person"},
        ],
        gold_clusters=[["GM-1"]],
        gold_claims=[
            {
                "claim_id": "GC-1",
                "subject_gold_entity_id": "ENT-1",
                "predicate": "holds_position",
                "object_raw": "Professor",
                "polarity": "affirmative",
                "temporal_status": "current",
                "supports": [{
                    "source_url": "https://example.com/target",
                    "source_content_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
                    "char_start": 30,
                    "char_end": 45,
                    "verbatim_text": "is a Professor",
                }],
            }
        ],
    )

    # Subtest A: Missing source in bundle -> l1_source_retrieval_miss
    f_a = compute_case_funnel(
        gold_case=gcase,
        extracted_sources=[],  # empty sources
        extracted_evidence=[],
        extracted_mentions=[],
        all_proposed_claims=[],
        released_claims=[],
        cand_to_gold_entity={},
        gold_mention_by_sig={},
        evidence_lookup={},
        actual_outcome="completed",
        expected_outcome="completed",
        false_splits=0,
    )
    assert f_a["first_failure_stage"] == "l1_source_retrieval_miss"

    # Subtest B: Source exists, but claim support missing from evidence -> l5_claim_support_window_miss
    f_b = compute_case_funnel(
        gold_case=gcase,
        extracted_sources=[{"source_id": "SRC-1", "raw_payload_sha256": "1111111111111111111111111111111111111111111111111111111111111111"}],
        extracted_evidence=[{"evidence_id": "EVI-1", "raw_payload_sha256": "1111111111111111111111111111111111111111111111111111111111111111", "char_start": 0, "char_end": 25}],  # covers mention [10:23] but NOT support [30:45]
        extracted_mentions=[{"mention_id": "M-1", "evidence_id": "EVI-1", "char_start": 10, "char_end": 23, "raw_name_text": "Target Person"}],
        all_proposed_claims=[],
        released_claims=[],
        cand_to_gold_entity={"CAND-1": "ENT-1"},
        gold_mention_by_sig={"1111111111111111111111111111111111111111111111111111111111111111:10_23:target person": "GM-1"},
        evidence_lookup={"EVI-1": ("1111111111111111111111111111111111111111111111111111111111111111", 0)},
        actual_outcome="completed",
        expected_outcome="completed",
        false_splits=0,
    )
    assert f_b["first_failure_stage"] == "l5_claim_support_window_miss"
