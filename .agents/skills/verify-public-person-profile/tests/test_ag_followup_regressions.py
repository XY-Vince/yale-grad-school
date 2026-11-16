"""Evidence eligibility and target status regressions from the October review."""
import json

import pytest

from scripts.verify_investigation_bundle import BundleVerifier, has_degree_candidacy


def claim_verifier(tmp_path, source_overrides=None):
    excerpt = "Alice Wang works at Yale University."
    (tmp_path / "source.txt").write_text(excerpt)
    (tmp_path / "verified_claims.jsonl").write_text(json.dumps({
        "claim_id": "VCLM-01", "candidate_id": "CAND-01", "subject": "Alice Wang",
        "predicate": "affiliated_with", "object": "Yale University",
        "source_id": "SRC-01", "verbatim_excerpt": excerpt, "evidence_strength": "S1",
    }) + "\n")
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {
        "local_path": "source.txt", "http_status": 200, "evidence_status": "usable",
        **(source_overrides or {}),
    }}
    return verifier


@pytest.mark.parametrize("status", [403, 404, 999, 302, 206, None, "200"])
def test_verified_claim_requires_http_200_even_without_failure_label(tmp_path, status):
    verifier = claim_verifier(tmp_path, {"http_status": status})
    verifier.audit_claims()
    assert any("without HTTP 200" in e for e in verifier.errors)


@pytest.mark.parametrize("overrides", [
    {"intended_use": "authwall"}, {"evidence_use": "AUTHWALL_NO_PROFILE_CONTENT"},
    {"evidence_status": "pending"}, {"evidence_status": ""},
    {"evidence_use": "SEARCH_NOISE"}, {"local_path": None},
])
def test_http_200_alone_does_not_make_a_source_eligible(tmp_path, overrides):
    verifier = claim_verifier(tmp_path, overrides)
    verifier.audit_claims()
    assert verifier.errors


@pytest.mark.parametrize("status", ["usable", "verified"])
def test_eligible_source_has_explicit_review_status(tmp_path, status):
    verifier = claim_verifier(tmp_path, {"evidence_status": status})
    verifier.audit_claims()
    assert not verifier.errors


@pytest.mark.parametrize("heading", [
    "Degree Candidates", "Candidates for Degrees and Certificates 2024",
    "CANDIDATES FO R D EG R E E S A N D C E RT I F I C AT E S 2024",
    "学位候选人",
])
def test_degree_candidacy_variants(heading):
    assert has_degree_candidacy(heading)


@pytest.mark.parametrize("explicit_award", [False, True])
def test_degree_claim_reads_heading_on_an_earlier_pdf_page(tmp_path, explicit_award):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "commencement.pdf"
    excerpt = ("Alice Wang received a Bachelor of Arts degree in 2024." if explicit_award
               else "Alice Wang, BA")
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 50), "CANDIDATES FO R D EG R E E S 2024")
        for _ in range(8):
            doc.new_page().insert_text((50, 50), "Continued")
        doc.new_page().insert_text((50, 50), excerpt)
        doc.save(path)
    verifier = BundleVerifier(tmp_path)
    assert verifier._degree_candidacy_context(path, excerpt, "Page 10") is not explicit_award


def test_degree_context_does_not_use_a_later_candidate_section(tmp_path):
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "program.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((50, 50), "Alice Wang, BA")
        doc.new_page().insert_text((50, 50), "Candidates for Degrees")
        doc.save(path)
    assert not BundleVerifier(tmp_path)._degree_candidacy_context(path, "Alice Wang, BA", "Page 1")


def lead_verifier(tmp_path, content="Alice Wang works at Yale University."):
    (tmp_path / "source.txt").write_text(content)
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {"local_path": "source.txt", "http_status": 200, "evidence_status": "usable"}}
    lead = {
        "lead_id": "LEAD-01", "candidate_id": "CAND-01", "status": "CORROBORATED",
        "corroborating_source_ids": ["SRC-01"], "supporting_evidence": [{
            "source_id": "SRC-01", "subject_raw": "Alice Wang", "object": "Yale University",
            "verbatim_excerpt": "Alice Wang works at Yale University.",
        }],
    }
    return verifier, lead


def test_corroborated_lead_requires_each_sources_owned_replayable_evidence(tmp_path):
    verifier, lead = lead_verifier(tmp_path)
    verifier.audit_lead_support("LEAD-01", lead)
    assert not verifier.errors
    verifier.sources["SRC-02"] = {"local_path": "source.txt", "http_status": 200, "evidence_status": "usable"}
    lead["corroborating_source_ids"].append("SRC-02")
    verifier.audit_lead_support("LEAD-01", lead)
    assert any("sources without grounded evidence" in e for e in verifier.errors)


@pytest.mark.parametrize("mutation", [
    "missing_evidence", "zero_results", "wrong_subject", "wrong_object", "spliced_people",
    "no_positive_sources", "empty_excerpt",
])
def test_corroborated_lead_cannot_use_unrelated_content(tmp_path, mutation):
    verifier, lead = lead_verifier(tmp_path)
    unit = lead["supporting_evidence"][0]
    if mutation == "missing_evidence":
        lead.pop("supporting_evidence")
    elif mutation == "zero_results":
        (tmp_path / "source.txt").write_text('{"results":[]}')
    elif mutation == "wrong_subject":
        unit["subject_raw"] = "Bob Smith"
    elif mutation == "wrong_object":
        unit["object"] = "Harvard University"
    elif mutation == "spliced_people":
        unit["verbatim_excerpt"] = "Alice Wang works at Stanford University; Bob Smith works at Yale University."
        (tmp_path / "source.txt").write_text(unit["verbatim_excerpt"])
    elif mutation == "no_positive_sources":
        lead["context_source_ids"] = lead.pop("corroborating_source_ids")
    else:
        unit["verbatim_excerpt"] = ""
    verifier.audit_lead_support("LEAD-01", lead)
    assert verifier.errors


@pytest.mark.parametrize("source_meta", [
    {"http_status": 403}, {"http_status": 200, "intended_use": "authwall"},
    {"http_status": 200, "evidence_status": "withdrawn"},
])
@pytest.mark.parametrize("field", ["corroborating_source_ids", "source_refs"])
def test_unresolved_leads_cannot_disguise_failed_or_withdrawn_sources_as_support(tmp_path, source_meta, field):
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": source_meta}
    verifier.audit_lead_support("LEAD-01", {"status": "UNRESOLVED", field: ["SRC-01"]})
    assert verifier.errors


def test_history_is_explicit_and_does_not_corroborate_a_lead(tmp_path):
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {
        "SRC-01": {"http_status": 403},
        "SRC-02": {"http_status": 200, "evidence_status": "withdrawn"},
    }
    lead = {"status": "UNRESOLVED", "context_source_ids": ["SRC-01"], "withdrawn_source_ids": ["SRC-02"]}
    verifier.audit_lead_support("LEAD-01", lead)
    assert not verifier.errors
    lead["context_source_ids"].append("SRC-99")
    verifier.audit_lead_support("LEAD-01", lead)
    assert any("unknown source" in e for e in verifier.errors)


@pytest.mark.parametrize("primary,outcome,expected", [
    ("CAND-07", "COMPLETED", False),
    ("CAND-07", "PARTIAL_EVIDENCE", False),
    ("CAND-07", "INSUFFICIENT_EVIDENCE", True),
    ("CAND-07", "RunOutcome.INSUFFICIENT_EVIDENCE", True),
    ("CAND-02", "INSUFFICIENT_EVIDENCE", False),
    (None, "COMPLETED", True),
])
def test_target_outcome_counts_the_declared_candidate_not_all_claims(tmp_path, primary, outcome, expected):
    (tmp_path / "manifest.json").write_text(json.dumps({"run_outcome": outcome}))
    (tmp_path / "dossier.json").write_text(json.dumps({"primary_candidate_id": primary}))
    verifier = BundleVerifier(tmp_path)
    verifier.claims = {"VCLM-01": {"candidate_id": "CAND-02"}}
    verifier.verified_claim_ids = {"VCLM-01"}
    verifier.audit_manifest_full()
    assert (not verifier.errors) == expected


def test_insufficient_target_evidence_still_requires_alternate_claim_citation_closure(tmp_path):
    verifier = claim_verifier(tmp_path)
    claim = json.loads((tmp_path / "verified_claims.jsonl").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps({"run_outcome": "INSUFFICIENT_EVIDENCE"}))
    (tmp_path / "dossier.json").write_text(json.dumps({"primary_candidate_id": "CAND-07", "statements": []}))
    (tmp_path / "recall_report.md").write_text("## Candidate Matrix\n")
    verifier.audit_manifest_preliminary()
    assert not verifier.is_abstention
    verifier.claims = {"VCLM-01": claim}
    verifier.verified_claim_ids = {"VCLM-01"}
    verifier.audit_manifest_full()
    assert not verifier.errors
    verifier.audit_dossier_and_report_closure()
    assert any("fails to cite all verified claims" in e for e in verifier.errors)


@pytest.mark.parametrize("destination", [
    "/Users/someone/OldProject/evidence_index.md",
    "file:///Users/someone/OldProject/raw_sources/",
    "C:\\Users\\someone\\evidence.md",
])
@pytest.mark.parametrize("reference", [False, True])
def test_ordinary_markdown_links_cannot_hide_local_absolute_paths(tmp_path, destination, reference):
    text = (f"[evidence][ref]\n\n[ref]: {destination}" if reference else f"[evidence]({destination})")
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", text)
    assert any("absolute local path" in e for e in verifier.errors)


def test_ordinary_relative_and_web_links_remain_allowed(tmp_path):
    (tmp_path / "raw_sources").mkdir()
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md",
                                  "[raw](raw_sources/) [public](https://university.edu/profile)")
    assert not verifier.errors
