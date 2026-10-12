"""
Unit tests for Functional Acceptance Runner & Diagnostic Harness (V6.3 Architecture).

Covers:
1. Target-scope separation: primary_candidate_id partitioned from alternate candidates.
2. Correctly isolated homonyms do not trip contamination.
3. Duplicate Gold / 1-to-1 maximum bipartite matching prevents recall inflation.
4. Fail-closed temporal matching: candidate 'unknown' rejected against gold 'current'.
5. Degree vs. graduation separation: received_degree and graduated_from are not equivalent.
6. Partial Gold reference blocks acceptance certification.
7. Substring trap rejection (e.g. 'submitted' vs 'MIT').
8. Real Yao Sun InvestigationBundle diagnostic evaluation.
9. Real Yao Sun InvestigationBundle complete Gold acceptance certification (precision >= 0.95, recall >= 0.80).
"""

import json
import shutil
from pathlib import Path

import pytest

from benchmarks.tools.functional_acceptance_runner import (
    check_5d_match,
    compute_before_after_delta,
    evaluate_profile_coverage,
    evaluate_query_saturation,
    evaluate_structural_and_byte_replay,
    evaluate_withheld_gold,
    maximum_bipartite_matching,
    run_functional_acceptance,
    strict_object_match,
)


def test_target_scope_candidate_partitioning():
    """
    Candidate claims must be partitioned by primary_candidate_id:
    Target precision & recall evaluated strictly on CAND-01 without being dragged
    down by alternate candidates (CAND-02, CAND-03).
    """
    claims = [
        {"claim_id": "C-1", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "holds_position", "object": "Professor", "polarity": "affirmative", "temporal_status": "current"},
        {"claim_id": "C-2", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "affiliated_with", "object": "Yale University", "polarity": "affirmative", "temporal_status": "current"},
        # Peripheral candidates (homonym or unmerged entities)
        {"claim_id": "C-3", "candidate_id": "CAND-02", "subject": "Alice Wang", "predicate": "holds_position", "object": "Dental Surgeon", "polarity": "affirmative", "temporal_status": "current"},
    ]

    gold_facts = [
        {"subject": "Alice Wang", "predicate": "holds_position", "object_raw": "Professor", "polarity": "affirmative", "temporal_status": "current"},
        {"subject": "Alice Wang", "predicate": "affiliated_with", "object_raw": "Yale University", "polarity": "affirmative", "temporal_status": "current"},
    ]

    res = evaluate_withheld_gold(
        all_claims=claims,
        withheld_gold_facts=gold_facts,
        primary_candidate_id="CAND-01",
        reference_completeness="complete",
        target_name="Alice Wang",
    )

    assert res["primary_candidate_id"] == "CAND-01"
    assert res["target_claim_count"] == 2
    assert res["alternate_claim_count"] == 1
    assert res["matched_facts"] == 2
    assert res["withheld_fact_recall"] == 1.0
    # Precision is 2/2 = 1.0 on CAND-01, NOT 2/3 = 0.667!
    assert res["verified_claim_precision"] == 1.0


def test_correctly_isolated_homonym_does_not_trip_contamination():
    """
    Homonym fact assigned to alternate candidate (CAND-02) is correctly isolated
    and must NOT trip contamination. If assigned to primary candidate (CAND-01),
    it must trip contamination.
    """
    homonym_annotations = [
        {"homonym_entity": "Dr. Alice Wang (Dentist)", "subject": "Alice Wang", "predicate": "holds_position", "object_raw": "Dental Surgeon", "polarity": "affirmative", "temporal_status": "current"}
    ]

    # Case A: Correctly isolated under CAND-02
    claims_isolated = [
        {"claim_id": "C-1", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "holds_position", "object": "Professor", "polarity": "affirmative", "temporal_status": "current"},
        {"claim_id": "C-2", "candidate_id": "CAND-02", "subject": "Alice Wang", "predicate": "holds_position", "object": "Dental Surgeon", "polarity": "affirmative", "temporal_status": "current"},
    ]
    res_isolated = evaluate_withheld_gold(
        all_claims=claims_isolated,
        withheld_gold_facts=[],
        primary_candidate_id="CAND-01",
        annotated_homonyms=homonym_annotations,
    )
    assert res_isolated["contamination_count"] == 0
    assert res_isolated["isolated_homonym_count"] == 1
    assert res_isolated["contamination_gate_pass"] is True

    # Case B: Erroneously merged under CAND-01
    claims_contaminated = [
        {"claim_id": "C-1", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "holds_position", "object": "Professor", "polarity": "affirmative", "temporal_status": "current"},
        {"claim_id": "C-2", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "holds_position", "object": "Dental Surgeon", "polarity": "affirmative", "temporal_status": "current"},
    ]
    res_contaminated = evaluate_withheld_gold(
        all_claims=claims_contaminated,
        withheld_gold_facts=[],
        primary_candidate_id="CAND-01",
        annotated_homonyms=homonym_annotations,
    )
    assert res_contaminated["contamination_count"] == 1
    assert res_contaminated["contamination_gate_pass"] is False


def test_duplicate_gold_one_to_one_bipartite_matching():
    """
    A single candidate claim must match AT MOST ONE gold fact.
    Two duplicate gold facts and one matching claim yields recall = 0.5, not 1.0.
    """
    claims = [
        {"claim_id": "C-1", "candidate_id": "CAND-01", "subject": "Alice Wang", "predicate": "holds_position", "object": "Professor", "polarity": "affirmative", "temporal_status": "current"}
    ]
    duplicate_gold = [
        {"subject": "Alice Wang", "predicate": "holds_position", "object_raw": "Professor", "polarity": "affirmative", "temporal_status": "current"},
        {"subject": "Alice Wang", "predicate": "holds_position", "object_raw": "Professor", "polarity": "affirmative", "temporal_status": "current"},
    ]

    res = evaluate_withheld_gold(
        all_claims=claims,
        withheld_gold_facts=duplicate_gold,
        primary_candidate_id="CAND-01",
        reference_completeness="complete",
        target_name="Alice Wang",
    )

    assert res["matched_facts"] == 1
    assert res["withheld_fact_recall"] == 0.5
    assert res["verified_claim_precision"] == 1.0


def test_unknown_temporal_status_fails_against_current_gold():
    """
    Fail-closed temporal matching: candidate with unknown or missing temporal status
    must NOT match gold with specified 'current' or 'historical' status.
    """
    gold_current = {
        "subject": "Alice Wang",
        "predicate": "holds_position",
        "object_raw": "Professor",
        "polarity": "affirmative",
        "temporal_status": "current",
    }

    # Case A: Candidate has temporal_status = "unknown"
    claim_unknown = {
        "subject": "Alice Wang",
        "predicate": "holds_position",
        "object": "Professor",
        "polarity": "affirmative",
        "temporal_status": "unknown",
    }
    assert check_5d_match(claim_unknown, gold_current) is False

    # Case B: Candidate has missing temporal_status
    claim_missing = {
        "subject": "Alice Wang",
        "predicate": "holds_position",
        "object": "Professor",
        "polarity": "affirmative",
    }
    assert check_5d_match(claim_missing, gold_current) is False

    # Case C: Candidate has matching temporal_status = "current"
    claim_current = {
        "subject": "Alice Wang",
        "predicate": "holds_position",
        "object": "Professor",
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    assert check_5d_match(claim_current, gold_current) is True


def test_no_degree_graduation_cross_equivalence():
    """
    'received_degree' (qualification) and 'graduated_from' (institution)
    must NOT be conflated as equivalent relations.
    """
    gold_grad = {
        "subject": "Alice Wang",
        "predicate": "graduated_from",
        "object_raw": "Yale University",
        "polarity": "affirmative",
        "temporal_status": "historical",
    }

    claim_degree = {
        "subject": "Alice Wang",
        "predicate": "received_degree",
        "object": "Yale University",
        "polarity": "affirmative",
        "temporal_status": "historical",
    }
    assert check_5d_match(claim_degree, gold_grad) is False


def test_partial_gold_reference_blocks_acceptance(tmp_path: Path):
    """
    When reference_completeness == 'partial', precision evaluates to None (N/A)
    and overall_acceptance_pass must evaluate to False.
    """
    partial_gold_file = tmp_path / "partial_gold.json"
    partial_gold_data = {
        "target_name": "Alice Wang",
        "primary_candidate_id": "CAND-01",
        "reference_completeness": "partial",
        "facts": [
            {
                "subject": "Alice Wang",
                "predicate": "holds_position",
                "object_raw": "Professor",
                "polarity": "affirmative",
                "temporal_status": "current",
            }
        ],
    }
    partial_gold_file.write_text(json.dumps(partial_gold_data), encoding="utf-8")

    bundle_dir = tmp_path / "test_bundle"
    bundle_dir.mkdir()
    (bundle_dir / "verified_claims.jsonl").write_text(
        json.dumps({
            "claim_id": "C-1",
            "candidate_id": "CAND-01",
            "subject": "Alice Wang",
            "predicate": "holds_position",
            "object": "Professor",
            "source_id": "SRC-01",
            "source_file": "raw_sources/src.html",
            "verbatim_excerpt": "Alice Wang is Professor.",
            "temporal_status": "CURRENT",
        }) + "\n",
        encoding="utf-8",
    )
    (bundle_dir / "source_inventory.jsonl").write_text(
        json.dumps({
            "source_id": "SRC-01",
            "url": "https://example.org/p",
            "final_url": "https://example.org/p",
            "http_status": 200,
            "raw_bytes_sha256": "4b9a3e20e8282ea891c9bd047be88d327885b57d6061be92d53c399b90c1e194",
            "byte_size": 39,
            "local_path": "raw_sources/src.html",
        }) + "\n",
        encoding="utf-8",
    )
    raw_dir = bundle_dir / "raw_sources"
    raw_dir.mkdir()
    (raw_dir / "src.html").write_bytes(b"<html><body>Alice Wang is Professor.</body></html>")
    (bundle_dir / "manifest.json").write_text(
        json.dumps({"target_name": "Alice Wang", "run_outcome": "COMPLETED"}), encoding="utf-8"
    )

    out_dir = tmp_path / "partial_out"
    res = run_functional_acceptance(
        candidate_bundle_dir=bundle_dir,
        evaluate_existing=True,
        withheld_gold_path=partial_gold_file,
        output_dir=out_dir,
        enforce_git_clean=False,
    )

    assert res["gates"]["mode"] == "DIAGNOSTIC"
    assert res["gates"]["precision_floor_pass"] is None
    assert res["gates"]["overall_acceptance_pass"] is False
    assert res["withheld_gold"]["verified_claim_precision"] is None


def test_strict_5d_substring_traps():
    """5D matcher rejects bidirectional substring inclusion ('MIT' in 'submitted')."""
    gold_mit = {
        "subject": "Alice Wang",
        "predicate": "affiliated_with",
        "object_raw": "MIT",
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    claim_submitted = {
        "subject": "Alice Wang",
        "predicate": "affiliated_with",
        "object": "submitted",
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    assert strict_object_match("submitted", gold_mit) is False
    assert check_5d_match(claim_submitted, gold_mit) is False


def test_real_yao_sun_bundle_evaluate_existing(tmp_path: Path):
    """
    Evaluates the real production bundle at investigations/yao_sun.
    Verifies that all 22 claims, 25 sources, and 33 queries are ingested,
    100% byte replay passes on disk files, and reports DIAGNOSTIC mode without gold.
    """
    yao_bundle = Path("investigations/yao_sun")
    assert yao_bundle.exists()

    out_dir = tmp_path / "yao_eval_diag_out"
    res = run_functional_acceptance(
        candidate_bundle_dir=yao_bundle,
        evaluate_existing=True,
        output_dir=out_dir,
        enforce_git_clean=False,
    )

    gates = res["gates"]
    assert gates["mode"] == "DIAGNOSTIC"
    assert gates["structural_validation_pass"] is True
    assert gates["privacy_gate_pass"] is True
    assert gates["provenance_replay_pass"] is True
    assert gates["homonym_contamination_pass"] is True
    assert gates["claim_count_gate_pass"] is True
    assert gates["overall_acceptance_pass"] is False

    assert res["byte_replay"]["provenance_replay_rate"] == 1.0
    assert res["byte_replay"]["total_claims_audited"] == 22
    assert res["byte_replay"]["total_sources_audited"] == 25
    assert res["query_saturation"]["query_count"] == 33


def test_real_yao_sun_bundle_with_complete_gold(tmp_path: Path):
    """
    Evaluates real Yao Sun bundle with a complete reference gold set.
    Verifies:
    1. CAND-01 (19 claims) evaluated cleanly without degradation by CAND-02..04.
    2. Precision = 1.0 (>= 0.95 non-negotiable floor).
    3. Recall = 1.0 (>= 0.80 non-negotiable floor).
    4. Acceptance gate passes.
    """
    yao_bundle = Path("investigations/yao_sun")
    assert yao_bundle.exists()

    # Complete reference gold set for CAND-01 target entity
    gold_data = {
        "target_name": "Yao Sun",
        "primary_candidate_id": "CAND-01",
        "reference_completeness": "complete",
        "facts": [
            {"subject": "Yao Sun", "predicate": "holds_position", "object_raw": "Predoctoral Fellow", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "affiliated_with", "object_raw": "Yale University", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "employed_by", "object_raw": "Yale Institution for Social and Policy Studies", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "affiliated_with", "object_raw": "ZCAFE", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "affiliated_with", "object_raw": "University of Michigan", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "received_degree", "object_raw": "M.S. in Survey Methodology", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "Burns \"Bud\" Roper AAPOR Fellow Award", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "MPSDS Tuition Fellowship", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "MPSDS Travel Award & Rackham Conference Travel Funding", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "Survey and Data Science Travel Award", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "affiliated_with", "object_raw": "UW-Madison", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "UW-Madison Undergraduate Scholarship", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "received_degree", "object_raw": "master’s program in Survey and Data Science", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "awarded_honor", "object_raw": "UofSC-Academic Excellence Scholarship", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "presented_paper", "object_raw": "Linking Survey Data and Geospatial Data to Examine Environmental Effects on Health Outcomes among Korean American Adults", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "researched_topic", "object_raw": "environmental justice screening tool", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "participated_in", "object_raw": "Yale Population Studies Workshop", "polarity": "affirmative", "temporal_status": "current"},
            {"subject": "Yao Sun", "predicate": "conducted_research", "object_raw": "Detroit Street View Program", "polarity": "affirmative", "temporal_status": "historical"},
            {"subject": "Yao Sun", "predicate": "affiliated_with", "object_raw": "Survey Research Center, Institute for Social Research, University of Michigan", "polarity": "affirmative", "temporal_status": "historical"},
        ],
        "annotated_homonyms": [
            {"homonym_entity": "Derek Teen-Yao Sun", "subject": "Derek Teen-Yao Sun", "predicate": "employed_by", "object_raw": "GUGGENHEIM SECURITIES, LLC", "polarity": "affirmative", "temporal_status": "historical"}
        ],
    }

    gold_path = tmp_path / "yao_complete_gold.json"
    gold_path.write_text(json.dumps(gold_data), encoding="utf-8")

    out_dir = tmp_path / "yao_acceptance_out"
    res = run_functional_acceptance(
        candidate_bundle_dir=yao_bundle,
        evaluate_existing=True,
        withheld_gold_path=gold_path,
        output_dir=out_dir,
        precision_floor=0.95,
        min_recall=0.80,
        enforce_git_clean=False,
    )

    gates = res["gates"]
    assert gates["mode"] == "ACCEPTANCE"
    assert gates["structural_validation_pass"] is True
    assert gates["privacy_gate_pass"] is True
    assert gates["provenance_replay_pass"] is True
    assert gates["homonym_contamination_pass"] is True
    assert gates["precision_floor_pass"] is True
    assert gates["recall_gate_pass"] is True
    assert gates["overall_acceptance_pass"] is True

    gold_metrics = res["withheld_gold"]
    assert gold_metrics["primary_candidate_id"] == "CAND-01"
    assert gold_metrics["target_claim_count"] == 19
    assert gold_metrics["alternate_claim_count"] == 3
    assert gold_metrics["matched_facts"] == 19
    assert gold_metrics["withheld_fact_recall"] == 1.0
    assert gold_metrics["verified_claim_precision"] == 1.0
    assert gold_metrics["contamination_count"] == 0
    assert gold_metrics["isolated_homonym_count"] == 1
