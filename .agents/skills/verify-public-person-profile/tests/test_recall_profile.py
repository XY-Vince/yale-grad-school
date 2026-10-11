"""
Tests for dynamic recall-first person profiling runner and bundle verification.
"""

import json
from pathlib import Path
import pytest
from scripts.run_recall_profile import run_recall_investigation
from scripts.validate_dossier import validate_bundle


def test_cli_name_sensitivity_abstention(tmp_path):
    """
    Ensure the runner does NOT output Yao Sun facts or dossiers when
    invoked with an unverified or different name.
    """
    out_dir = tmp_path / "test_unknown_entity"
    result = run_recall_investigation(
        name="Unknown Candidate X",
        clue="Astrophysics Department",
        additional_clues=["No prior record"],
        output_dir=out_dir,
    )
    assert result == out_dir
    dossier_file = out_dir / "dossier.json"
    assert dossier_file.exists()
    dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
    assert dossier.get("candidate_entity_id") is None
    assert len(dossier.get("statements", [])) == 0

    report_text = (out_dir / "recall_report.md").read_text(encoding="utf-8")
    assert ("INSUFFICIENT_EVIDENCE" in report_text) or ("COLLECTION_FAILED" in report_text)
    assert "Yao Sun" not in report_text


def test_pilot_bundle_warc_provenance_replay():
    """
    Verify that the generated Yao Sun pilot bundle replays with zero errors
    against corpus.warc using validate_bundle.
    """
    skill_dir = Path(__file__).resolve().parent.parent
    bundle_dir = skill_dir / "runs" / "pilot_yao_sun_recall"
    warc_file = bundle_dir / "corpus.warc"

    assert bundle_dir.exists(), f"Bundle dir {bundle_dir} must exist"
    assert warc_file.exists(), f"WARC archive {warc_file} must exist"

    res = validate_bundle(bundle_dir, warc_path=warc_file)
    assert res["is_valid"] is True, f"Validation failed with errors: {res['errors']}"
    assert res["layers"]["provenance_replay_valid"] is True
    assert res["layers"]["warc_record_ids_present"] is True
    assert res["layers"]["relation_precision_enforced"] is True
    assert res["error_count"] == 0


def test_yale_connection_and_candidacy_claims():
    """
    Verify that CAND-01 contains the verified Yale University predoctoral fellowship claims,
    and CAND-02 (Derek Teen-Yao Sun) has zero Yale associations.
    """
    skill_dir = Path(__file__).resolve().parent.parent
    bundle_dir = skill_dir / "runs" / "pilot_yao_sun_recall"

    claims_file = bundle_dir / "claims.jsonl"
    claims = [json.loads(line) for line in claims_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    cand01_claims = [c for c in claims if c["candidate_entity_id"] == "CAND-01"]
    cand02_claims = [c for c in claims if c["candidate_entity_id"] == "CAND-02"]

    # Verify CAND-01 key facts
    pred_objs_01 = {(c["predicate"], c["object_raw"]) for c in cand01_claims}
    assert ("holds_position", "predoctoral fellow") in pred_objs_01
    assert ("employed_by", "Yale University") in pred_objs_01
    assert ("affiliated_with", "Z-CAFE") in pred_objs_01
    assert ("graduated_from", "University of Wisconsin-Madison") in pred_objs_01
    assert ("received_degree", "Bachelor of Science in Sociology") in pred_objs_01
    assert ("affiliated_with", "University of Michigan") in pred_objs_01

    # Verify CAND-02 has zero Yale affiliation
    for c in cand02_claims:
        assert "Yale" not in c["object_raw"]
        assert "Z-CAFE" not in c["object_raw"]


def test_relation_level_provenance_spans():
    """
    Ensure all claims have relation-level provenance spans covering verbatim excerpts.
    """
    skill_dir = Path(__file__).resolve().parent.parent
    bundle_dir = skill_dir / "runs" / "pilot_yao_sun_recall"

    claims_file = bundle_dir / "claims.jsonl"
    claims = [json.loads(line) for line in claims_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    for c in claims:
        assert len(c["support_clauses"]) > 0
        for sup in c["support_clauses"]:
            assert sup["provenance_level"] == "relation"
            assert sup["relation_span_start"] is not None
            assert sup["relation_span_end"] is not None
            assert sup["relation_span_end"] > sup["relation_span_start"]
            assert len(sup["verbatim_clause"]) > 0
