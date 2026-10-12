"""
test_general_pipeline_and_auditor.py
Regression tests for universal person profiling runner and mechanical auditor.
Ensures zero synthetic fallbacks, authentic dynamic retrieval, and fail-closed audit gates.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path
import pytest

from scripts.run_recall_profile import extract_claims_from_web_document, run_recall_investigation
from scripts.verify_investigation_bundle import BundleVerifier

FIXTURE_JULIA = Path(__file__).resolve().parents[4] / "investigations" / "julia_moniz_ganem"


def copy_julia_fixture(target_dir: Path) -> Path:
    """Helper to copy the validated Julia Moniz Ganem fixture for hermetic mutation tests."""
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(FIXTURE_JULIA, target_dir)
    return target_dir


def update_manifest_file_checksum(bundle_dir: Path, rel_filename: str):
    """Helper to update byte size and sha256 in manifest.json for mutation tests."""
    fpath = bundle_dir / rel_filename
    man_path = bundle_dir / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    if "files" in man and rel_filename in man["files"]:
        man["files"][rel_filename]["byte_size"] = fpath.stat().st_size
        man["files"][rel_filename]["sha256"] = hashlib.sha256(fpath.read_bytes()).hexdigest()
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")


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
    try:
        result = run_recall_investigation(
            name="Julia Moniz Ganem",
            clue="Public Health",
            additional_clues=["Vaccine"],
            output_dir=out_dir,
        )
    except Exception as e:
        if any(tok in str(e).lower() for tok in ("http", "urlerror", "timeout", "timed out", "connection", "remote end closed")):
            pytest.skip(f"Live network unavailable or rate limited: {e}")
        raise

    assert result == out_dir

    raw_files = list((out_dir / "raw_sources").glob("*"))
    if not raw_files:
        pytest.skip("Live network unavailable or rate limited in sandbox")
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
    copy_julia_fixture(out_dir)

    # Inject phantom citation
    report_file = out_dir / "recall_report.md"
    content = report_file.read_text(encoding="utf-8")
    content += "\n* [VCLM-99] Phantom unbacked fact."
    report_file.write_text(content, encoding="utf-8")
    update_manifest_file_checksum(out_dir, "recall_report.md")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on phantom citation"
    assert any("VCLM-99" in err for err in verifier.errors)


def test_auditor_rejects_synthetic_domains(tmp_path):
    """
    Ensure auditor fails if a synthetic domain like profiles.institution.edu is present.
    """
    out_dir = tmp_path / "test_synthetic_rejection"
    copy_julia_fixture(out_dir)

    inv_file = out_dir / "source_inventory.jsonl"
    lines = inv_file.read_text(encoding="utf-8").splitlines()
    if lines:
        first = json.loads(lines[0])
        first["url"] = "https://profiles.institution.edu/fake_person"
        lines[0] = json.dumps(first)
        inv_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    update_manifest_file_checksum(out_dir, "source_inventory.jsonl")

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
    copy_julia_fixture(out_dir)

    # Mutate query logs
    qlog_file = out_dir / "query_logs.jsonl"
    lines = [json.loads(l) for l in qlog_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    for rec in lines:
        rec["status"] = "PLANNED_NOT_EXECUTED"
        rec["results_count"] = 999
    qlog_file.write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")
    update_manifest_file_checksum(out_dir, "query_logs.jsonl")

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
    copy_julia_fixture(out_dir)

    # Strip all [VCLM-xx], [LEAD-xx], [OQ-xx] from report
    report_file = out_dir / "recall_report.md"
    text = report_file.read_text(encoding="utf-8")
    stripped_text = re.sub(r"\[(VCLM-\d+|LEAD-\d+|OQ-\d+)\]", "", text)
    report_file.write_text(stripped_text, encoding="utf-8")
    update_manifest_file_checksum(out_dir, "recall_report.md")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail when citations are removed from report"
    assert any("fails to cite all verified claims" in err for err in verifier.errors)


def test_auditor_catches_mutation_unbacked_dossier_statement(tmp_path):
    """
    Mutation C: Dossier injects an unbacked statement with empty backed_claim_ids.
    Auditor MUST fail-close.
    """
    out_dir = tmp_path / "test_mutation_unbacked_stmt"
    copy_julia_fixture(out_dir)

    dossier_file = out_dir / "dossier.json"
    dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
    dossier["statements"].append({
        "statement_id": "STMT-UNBACKED",
        "section": "Fake Section",
        "rendered_text": "Unbacked statement text",
        "backed_claim_ids": [],
    })
    dossier_file.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_manifest_file_checksum(out_dir, "dossier.json")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on unbacked dossier statement"
    assert any("empty backed_claim_ids" in err for err in verifier.errors)


def test_auditor_catches_mutation_president_of_mars_semantic_injection(tmp_path):
    """
    Mutation D: Statement claims 'President of Mars' while deceptively citing a valid claim [VCLM-01].
    Auditor semantic inspection MUST detect ungrounded alien entity / token discrepancy and fail-close.
    """
    out_dir = tmp_path / "test_mutation_president_of_mars"
    copy_julia_fixture(out_dir)

    # Inject into dossier statement citing valid claim ID VCLM-01
    dossier_file = out_dir / "dossier.json"
    dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
    dossier["statements"].append({
        "statement_id": "STMT-INJECTED-MARS",
        "section": "Public Health",
        "rendered_text": "[CAND-01] Julia Moniz Ganem is President of Mars.",
        "backed_claim_ids": ["VCLM-01"],
    })
    dossier_file.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_manifest_file_checksum(out_dir, "dossier.json")

    # Inject into report as well
    report_file = out_dir / "recall_report.md"
    content = report_file.read_text(encoding="utf-8")
    content += "\n* [VCLM-01] President of Mars appointment."
    report_file.write_text(content, encoding="utf-8")
    update_manifest_file_checksum(out_dir, "recall_report.md")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail on 'President of Mars' semantic injection"
    assert any("alien" in err.lower() or "grounding" in err.lower() or "injection" in err.lower() for err in verifier.errors)


def test_auditor_catches_mutation_null_primary_with_fake_correlate_leads(tmp_path):
    """
    Mutation E: Bundle has null primary_candidate_id, but a lead falsely asserts clue correlation.
    Auditor MUST fail-close.
    """
    out_dir = tmp_path / "test_mutation_null_primary_lead"
    copy_julia_fixture(out_dir)

    # Set primary_candidate_id to None in dossier
    dossier_file = out_dir / "dossier.json"
    dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
    dossier["primary_candidate_id"] = None
    dossier_file.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
    update_manifest_file_checksum(out_dir, "dossier.json")

    # Inject fake clue-correlation lead
    lead_file = out_dir / "corroborated_leads.jsonl"
    leads = [json.loads(l) for l in lead_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    leads.append({
        "lead_id": f"LEAD-{len(leads)+1:02d}",
        "candidate_id": "CAND-01",
        "description": "Candidate signals correlate with clues provided in investigation query.",
        "corroborating_source_ids": ["SRC-01"],
    })
    lead_file.write_text("\n".join(json.dumps(l) for l in leads) + "\n", encoding="utf-8")
    update_manifest_file_checksum(out_dir, "corroborated_leads.jsonl")

    # Cite in report
    report_file = out_dir / "recall_report.md"
    content = report_file.read_text(encoding="utf-8")
    content += f"\n* [LEAD-{len(leads):02d}] Candidate signals correlate with clues."
    report_file.write_text(content, encoding="utf-8")
    update_manifest_file_checksum(out_dir, "recall_report.md")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must fail when null primary candidate has clue correlation leads"
    assert any("asserts clue correlation when primary_candidate_id is null" in err for err in verifier.errors)


def test_juxtaposition_entity_extraction_prevents_contamination(tmp_path):
    """
    Decisive test 1: Yao/Tian juxtaposition record.
    Tian's Georgetown University and M.S. in Data Science must NOT be attributed to Yao.
    """
    html_content = """<html><body>
    <h2>2025 Graduate Cohort</h2>
    <ul>
      <li>Yao Sun — M.S. in Survey Methodology, University of Michigan</li>
      <li>Tian Tong — M.S. in Data Science, Georgetown University</li>
    </ul>
    </body></html>"""
    test_file = tmp_path / "graduates.html"
    test_file.write_text(html_content, encoding="utf-8")

    src = {
        "file_path": test_file,
        "source_id": "SRC-TEST-01",
        "local_path": "raw_sources/graduates.html",
        "type": "WEB_HTML",
        "publisher": "Academic Department",
    }
    claims, cluster, counter, bridges, leads = extract_claims_from_web_document(
        src=src,
        name="Yao Sun",
        all_clues=["Survey Methodology", "Michigan"],
        claim_counter=1,
    )

    objects = {c["object"] for c in claims}
    assert "University of Michigan" in objects
    assert "M.S. in Survey Methodology" in objects
    assert "Georgetown University" not in objects
    assert "M.S. in Data Science" not in objects

    excerpts_text = " ".join(c.get("verbatim_excerpt", "") for c in claims)
    assert "Tian Tong" not in excerpts_text
    assert "Georgetown" not in excerpts_text
    assert not any("Georgetown" in b[0] or "Georgetown" in b[1] for b in bridges)


def test_adjacent_award_recipients_prevents_contamination(tmp_path):
    """
    Decisive test 2: AAPOR award list.
    Adjacent award winner Alice Smith's University of Chicago must NOT be attributed to Yao.
    """
    html_content = """<html><body>
    <h2>AAPOR Student Paper Awards</h2>
    <p>First Place: Alice Smith, University of Chicago</p>
    <p>Honorable Mention: Yao Sun, University of Michigan</p>
    </body></html>"""
    test_file = tmp_path / "aapor.html"
    test_file.write_text(html_content, encoding="utf-8")

    src = {
        "file_path": test_file,
        "source_id": "SRC-TEST-02",
        "local_path": "raw_sources/aapor.html",
        "type": "WEB_HTML",
        "publisher": "AAPOR",
    }
    claims, cluster, counter, bridges, leads = extract_claims_from_web_document(
        src=src,
        name="Yao Sun",
        all_clues=["AAPOR"],
        claim_counter=1,
    )

    objects = {c["object"] for c in claims}
    assert "University of Michigan" in objects
    assert "University of Chicago" not in objects

    excerpts_text = " ".join(c.get("verbatim_excerpt", "") for c in claims)
    assert "Alice Smith" not in excerpts_text
    assert "Chicago" not in excerpts_text


def test_auditor_rejects_cross_entity_claim_injection(tmp_path):
    """
    Decisive test 3: Forcing an erroneous object from another person into Yao Claim
    MUST cause the Auditor to FAIL.
    """
    out_dir = tmp_path / "test_cross_entity_rejection"
    copy_julia_fixture(out_dir)

    # Add a raw source with juxtaposition
    raw_dir = out_dir / "raw_sources"
    juxt_file = raw_dir / "cohort.html"
    juxt_file.write_text(
        "<p>Yao Sun — M.S. in Survey Methodology, University of Michigan</p>\n"
        "<p>Tian Tong — M.S. in Data Science, Georgetown University</p>",
        encoding="utf-8",
    )

    # Register in source_inventory
    inv_file = out_dir / "source_inventory.jsonl"
    inv_lines = inv_file.read_text(encoding="utf-8").splitlines()
    new_src = {
        "source_id": "SRC-99",
        "url": "https://example.edu/cohort.html",
        "content_sha256": hashlib.sha256(juxt_file.read_bytes()).hexdigest(),
        "byte_size": juxt_file.stat().st_size,
        "local_path": "raw_sources/cohort.html",
        "source_class": "class_a",
        "publisher": "Cohort Registry",
        "title": "Graduation Cohort",
    }
    inv_lines.append(json.dumps(new_src))
    inv_file.write_text("\n".join(inv_lines) + "\n", encoding="utf-8")
    update_manifest_file_checksum(out_dir, "source_inventory.jsonl")

    # Inject erroneous claim attributing Georgetown to Yao Sun
    claims_file = out_dir / "verified_claims.jsonl"
    claims = [json.loads(l) for l in claims_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    claims.append({
        "claim_id": "VCLM-99",
        "candidate_id": "CAND-01",
        "subject": "Yao Sun",
        "predicate": "affiliated_with",
        "object": "Georgetown University",
        "source_id": "SRC-99",
        "source_file": "raw_sources/cohort.html",
        "locator": "Line 2",
        "verbatim_excerpt": "Tian Tong — M.S. in Data Science, Georgetown University",
        "temporal_status": "CURRENT",
    })
    claims_file.write_text("\n".join(json.dumps(c) for c in claims) + "\n", encoding="utf-8")
    update_manifest_file_checksum(out_dir, "verified_claims.jsonl")

    # Cite in report
    report_file = out_dir / "recall_report.md"
    content = report_file.read_text(encoding="utf-8")
    content += "\n* [VCLM-99] Yao Sun is affiliated with Georgetown University."
    report_file.write_text(content, encoding="utf-8")
    update_manifest_file_checksum(out_dir, "recall_report.md")

    # Also update manifest files entry for cohort.html
    man_path = out_dir / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["files"]["raw_sources/cohort.html"] = {
        "byte_size": juxt_file.stat().st_size,
        "sha256": hashlib.sha256(juxt_file.read_bytes()).hexdigest(),
    }
    man_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

    verifier = BundleVerifier(out_dir)
    ok = verifier.audit_all()
    assert ok is False, "Auditor must reject cross-entity claim attribution"
    assert any("cross-entity attribution violation" in err or "subject 'Yao Sun' not grounded" in err for err in verifier.errors)
