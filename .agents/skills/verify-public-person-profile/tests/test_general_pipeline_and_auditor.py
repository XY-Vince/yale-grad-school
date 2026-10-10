"""
test_general_pipeline_and_auditor.py
Regression tests for universal person profiling runner and mechanical auditor.
Ensures zero synthetic fallbacks, authentic dynamic retrieval, and fail-closed audit gates.
"""

import json
import shutil
from pathlib import Path
import pytest

from scripts.run_recall_profile import run_recall_investigation
from scripts.verify_investigation_bundle import BundleVerifier


def test_unconfigured_nonexistent_entity_abstains_without_synthetic_files(tmp_path):
    """
    Ensure an unconfigured non-existent target (e.g. Jane Q Public) triggers
    genuine search, zero synthetic files, zero fake claims, and clean abstention.
    """
    out_dir = tmp_path / "test_jane_q_public"
    result = run_recall_investigation(
        name="Jane Q Public",
        clue="Astrophysics at Yale",
        output_dir=out_dir,
    )
    assert result == out_dir

    raw_files = list((out_dir / "raw_sources").glob("*"))
    assert len(raw_files) == 0, f"Expected 0 raw sources for non-existent target, got {raw_files}"

    claims_text = (out_dir / "verified_claims.jsonl").read_text(encoding="utf-8").strip()
    assert claims_text == "", "verified_claims.jsonl must be empty on abstention"

    manifest_data = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data.get("run_outcome") == "INSUFFICIENT_EVIDENCE"

    verifier = BundleVerifier(out_dir)
    assert verifier.audit_all() is True, f"Auditor failed on valid abstention bundle: {verifier.errors}"


def test_unconfigured_real_entity_dynamic_retrieval(tmp_path):
    """
    Ensure an unconfigured real entity (Julia Moniz Ganem) dynamically fetches
    authentic sources, extracts claims from raw bytes, and passes the auditor.
    """
    out_dir = tmp_path / "test_julia_moniz_ganem"
    result = run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    assert result == out_dir

    raw_files = list((out_dir / "raw_sources").glob("*"))
    assert len(raw_files) >= 1, "Must have fetched at least 1 authentic source"

    claims_lines = [l.strip() for l in (out_dir / "verified_claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(claims_lines) >= 1, "Must have extracted verified claims"

    verifier = BundleVerifier(out_dir)
    assert verifier.audit_all() is True, f"Auditor failed on real investigation bundle: {verifier.errors}"


def test_auditor_catches_phantom_citation(tmp_path):
    """
    Ensure auditor fails when recall_report.md cites a phantom claim [VCLM-99].
    """
    out_dir = tmp_path / "test_phantom"
    run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    # Inject phantom citation
    report_file = out_dir / "recall_report.md"
    content = report_file.read_text(encoding="utf-8")
    content += "\n* [VCLM-99] Phantom unbacked fact."
    report_file.write_text(content, encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on phantom citation"
    assert any("VCLM-99" in err for err in verifier.errors)


def test_auditor_rejects_synthetic_domains(tmp_path):
    """
    Ensure auditor fails if a synthetic domain like profiles.institution.edu is present.
    """
    out_dir = tmp_path / "test_synthetic_rejection"
    run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    inv_file = out_dir / "source_inventory.jsonl"
    lines = inv_file.read_text(encoding="utf-8").splitlines()
    if lines:
        first = json.loads(lines[0])
        first["url"] = "https://profiles.institution.edu/fake_person"
        lines[0] = json.dumps(first)
        inv_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on synthetic domain"
    assert any("synthetic domain" in err.lower() for err in verifier.errors)


def test_auditor_catches_mutation_unexecuted_queries(tmp_path):
    """
    Mutation A: All queries set to PLANNED_NOT_EXECUTED with fake count 999.
    Auditor MUST fail-close.
    """
    out_dir = tmp_path / "test_mutation_queries"
    run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    # Mutate query logs
    qlog_file = out_dir / "query_logs.jsonl"
    lines = [json.loads(l) for l in qlog_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    for rec in lines:
        rec["status"] = "PLANNED_NOT_EXECUTED"
        rec["results_count"] = 999
    qlog_file.write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")

    # Update manifest to match mutated file
    import hashlib
    man_path = out_dir / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["files"]["query_logs.jsonl"]["byte_size"] = qlog_file.stat().st_size
    man["files"]["query_logs.jsonl"]["sha256"] = hashlib.sha256(qlog_file.read_bytes()).hexdigest()
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail when all queries are unexecuted"
    assert any("query_logs.jsonl must contain at least one query with status EXECUTED" in err for err in verifier.errors)


def test_auditor_catches_mutation_deleted_citations(tmp_path):
    """
    Mutation B: Report deletes all Claim/Lead/Open Question citations.
    Auditor MUST fail-close.
    """
    out_dir = tmp_path / "test_mutation_deleted_citations"
    run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    # Strip all [VCLM-xx], [LEAD-xx], [OQ-xx] from report
    import re, hashlib
    report_file = out_dir / "recall_report.md"
    text = report_file.read_text(encoding="utf-8")
    stripped_text = re.sub(r"\[(VCLM-\d+|LEAD-\d+|OQ-\d+)\]", "", text)
    report_file.write_text(stripped_text, encoding="utf-8")

    # Update manifest
    man_path = out_dir / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["files"]["recall_report.md"]["byte_size"] = report_file.stat().st_size
    man["files"]["recall_report.md"]["sha256"] = hashlib.sha256(report_file.read_bytes()).hexdigest()
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail when citations are removed from report"
    assert any("fails to cite all verified claims" in err for err in verifier.errors)


def test_auditor_catches_mutation_unbacked_dossier_statement(tmp_path):
    """
    Mutation C: Dossier injects an unbacked statement ('President of Mars').
    Auditor MUST fail-close.
    """
    out_dir = tmp_path / "test_mutation_unbacked_stmt"
    run_recall_investigation(
        name="Julia Moniz Ganem",
        clue="Public Health",
        additional_clues=["Vaccine"],
        output_dir=out_dir,
    )
    import hashlib
    dossier_file = out_dir / "dossier.json"
    dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
    dossier["statements"].append({
        "statement_id": "STMT-UNBACKED",
        "section": "Fake Section",
        "rendered_text": "President of Mars",
        "backed_claim_ids": [],
    })
    dossier_file.write_text(json.dumps(dossier, indent=2), encoding="utf-8")

    # Update manifest
    man_path = out_dir / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["files"]["dossier.json"]["byte_size"] = dossier_file.stat().st_size
    man["files"]["dossier.json"]["sha256"] = hashlib.sha256(dossier_file.read_bytes()).hexdigest()
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on unbacked dossier statement"
    assert any("empty backed_claim_ids" in err for err in verifier.errors)
