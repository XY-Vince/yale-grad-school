"""
Tests for dynamic recall-first person profiling runner and bundle verification.
"""

import json
from pathlib import Path
import pytest
from scripts.run_recall_profile import run_recall_investigation
from scripts.validate_dossier import validate_bundle
from scripts.run_live_blind_test import run_targeted_warc_replay
from core.run_profile import run_pipeline
from synthetic_investigation import make_synthetic_warc


def test_cli_name_sensitivity_abstention(tmp_path):
    """
    Ensure the runner does NOT output Mia Fox facts or dossiers when
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
    assert "Mia Fox" not in report_text


@pytest.fixture
def synthetic_pipeline(tmp_path):
    warc = make_synthetic_warc(tmp_path / "synthetic.warc")
    bundle = run_pipeline(target_name="Alice Example", hints=[], output_dir=tmp_path / "bundle", offline_corpus=warc)
    return bundle, warc


def test_synthetic_bundle_warc_provenance_replay(synthetic_pipeline):
    """
    Verify the synthetic disambiguation bundle against its WARC.
    """
    bundle_dir, warc_file = synthetic_pipeline

    assert bundle_dir.exists(), f"Bundle dir {bundle_dir} must exist"
    assert warc_file.exists(), f"WARC archive {warc_file} must exist"

    res = validate_bundle(bundle_dir, warc_path=warc_file)
    assert res["is_valid"] is True, f"Validation failed with errors: {res['errors']}"
    assert res["layers"]["provenance_replay_valid"] is True
    assert res["layers"]["warc_record_ids_present"] is True
    assert res["layers"]["relation_precision_enforced"] is True
    assert res["error_count"] == 0


def test_synthetic_candidate_claims_remain_separate(synthetic_pipeline):
    """
    Verify that synthetic professor and dean claims remain in separate candidates.
    """
    bundle_dir, _ = synthetic_pipeline

    claims_file = bundle_dir / "claims.jsonl"
    claims = [json.loads(line) for line in claims_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    by_candidate = {}
    for claim in claims:
        by_candidate.setdefault(claim["candidate_entity_id"], set()).add(claim["object_raw"])
    professor = next(objects for objects in by_candidate.values() if "Professor" in objects)
    dean = next(objects for objects in by_candidate.values() if "Dean" in objects)
    assert "Dean" not in professor
    assert "Professor" not in dean


def test_relation_level_provenance_spans(synthetic_pipeline):
    """
    Ensure all claims have relation-level provenance spans covering verbatim excerpts.
    """
    bundle_dir, _ = synthetic_pipeline

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


def test_targeted_replay_requires_explicit_inputs(tmp_path):
    with pytest.raises(ValueError, match="target_name is required"):
        run_targeted_warc_replay(output_dir=tmp_path / "missing_name")
    with pytest.raises(ValueError, match="offline_corpus WARC is required"):
        run_targeted_warc_replay(target_name="Alice Example", output_dir=tmp_path / "missing_warc")

    warc = make_synthetic_warc(tmp_path / "supplied.warc")
    _, result = run_targeted_warc_replay(
        target_name="Alice Example", output_dir=tmp_path / "replay", offline_corpus=warc
    )
    assert result["is_valid"] is True
    assert result["layers"]["provenance_replay_valid"] is True


def test_outcome_attribution_collection_failed_when_network_unreachable(monkeypatch, tmp_path):
    """
    Ensure the runner outputs COLLECTION_FAILED when all external
    search and API queries fail due to network, timeout, or block.
    """
    from core.collectors.discovery_engine import UniversalDiscoveryEngine
    from scripts.run_recall_profile import UniversalEvidenceRetriever, run_recall_investigation

    out_dir = tmp_path / "test_failed_bundle"

    def mock_disc_failed(self, *args, **kwargs):
        self.query_logs.append({
            "query_type": "WEB_SEARCH",
            "query_string": "test query",
            "endpoint": "bing",
            "status": "FAILED",
            "error": "Connection timeout",
        })
        return []

    def mock_oa_failed(self, *args, **kwargs):
        self.query_logs.append({
            "query_type": "API_OPENALEX_AUTHORS",
            "query_string": "test query",
            "endpoint": "openalex",
            "status": "FAILED",
            "error": "Network unreachable",
        })
        return 0, None, "", []

    monkeypatch.setattr(UniversalDiscoveryEngine, "run_discovery", mock_disc_failed)
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_openalex_authors", mock_oa_failed)
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_openalex_works", lambda self, *args, **kwargs: (0, None, "", []))
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_crossref_works", lambda self, *args, **kwargs: (0, None, "", []))
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_pubmed", lambda self, *args, **kwargs: [])

    run_recall_investigation(
        name="Mock Offline Person",
        clue="Some Clue",
        output_dir=out_dir,
    )

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == "COLLECTION_FAILED"
    report_text = (out_dir / "recall_report.md").read_text(encoding="utf-8")
    assert "COLLECTION_FAILED" in report_text


def test_outcome_attribution_insufficient_evidence_when_queries_return_zero_hits(monkeypatch, tmp_path):
    """
    Ensure the runner outputs INSUFFICIENT_EVIDENCE when search and API queries
    succeed (HTTP 200 / COMPLETED) but return zero candidate hits.
    """
    from core.collectors.discovery_engine import UniversalDiscoveryEngine
    from scripts.run_recall_profile import UniversalEvidenceRetriever, run_recall_investigation

    out_dir = tmp_path / "test_insufficient_bundle"

    def mock_disc_ok(self, *args, **kwargs):
        self.query_logs.append({
            "query_type": "WEB_SEARCH",
            "query_string": "test query",
            "endpoint": "bing",
            "status": "COMPLETED",
            "results_count": 0,
        })
        return []

    def mock_oa_ok(self, *args, **kwargs):
        self.query_logs.append({
            "query_type": "API_OPENALEX_AUTHORS",
            "query_string": "test query",
            "endpoint": "openalex",
            "status": "EXECUTED",
            "http_status": 200,
            "results_count": 0,
        })
        return 200, None, "", []

    monkeypatch.setattr(UniversalDiscoveryEngine, "run_discovery", mock_disc_ok)
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_openalex_authors", mock_oa_ok)
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_openalex_works", lambda self, *args, **kwargs: (200, None, "", []))
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_crossref_works", lambda self, *args, **kwargs: (200, None, "", []))
    monkeypatch.setattr(UniversalEvidenceRetriever, "search_pubmed", lambda self, *args, **kwargs: [])

    run_recall_investigation(
        name="Mock Nonexistent Person",
        clue="Some Clue",
        output_dir=out_dir,
    )

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == "INSUFFICIENT_EVIDENCE"
    report_text = (out_dir / "recall_report.md").read_text(encoding="utf-8")
    assert "INSUFFICIENT_EVIDENCE" in report_text
