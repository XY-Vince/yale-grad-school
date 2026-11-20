"""Counterexamples from dossier review; local consistency is not factual certification."""
import json
from pathlib import Path

import pytest

from scripts.verify_investigation_bundle import BundleVerifier
from benchmarks.tools.functional_acceptance_runner import check_5d_match


@pytest.mark.parametrize("citation", ["VCLM-01", "LEAD-01", "OQ-01"])
@pytest.mark.parametrize("style", ["inline", "reference"])
def test_evidence_link_requires_its_actual_anchor(tmp_path, citation, style):
    index = tmp_path / "evidence_index.md"
    index.write_text("# Evidence\n## unrelated\n")
    destination = f"evidence_index.md#{citation.lower()}"
    report = (f"[{citation}]({destination})" if style == "inline" else
              f"[{citation}][support]\n\n[support]: {destination}")
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", report)
    assert any("missing anchor" in error for error in verifier.errors)

    index.write_text(f"# Evidence\n## {citation}\n")
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", report)
    assert not verifier.errors


@pytest.mark.parametrize("destination", [
    "missing.md#lead-01", "evidence_index.md#oq-01",
    "https://example.org/#lead-01", "../outside.md#lead-01",
])
def test_evidence_links_reject_missing_wrong_or_nonlocal_targets(tmp_path, destination):
    (tmp_path / "evidence_index.md").write_text("## OQ-01\n")
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", f"[LEAD-01]({destination})")
    assert verifier.errors


def test_explicit_anchor_and_fenced_decoy(tmp_path):
    index = tmp_path / "evidence_index.md"
    index.write_text('```\n## LEAD-01\n```\n')
    verifier = BundleVerifier(tmp_path)
    report = "[LEAD-01](evidence_index.md#lead-01)"
    verifier.audit_evidence_links(tmp_path / "recall_report.md", report)
    assert verifier.errors
    index.write_text('<a id="lead-01"></a>\n')
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", report)
    assert not verifier.errors


@pytest.mark.parametrize("destination", ["https://[/#lead-01", "binary.md#lead-01"])
def test_invalid_evidence_destination_reports_error_without_crashing(tmp_path, destination):
    (tmp_path / "binary.md").write_bytes(b"\xff\xfe")
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", f"[LEAD-01]({destination})")
    assert any("cannot be read" in error for error in verifier.errors)


def test_uncited_prose_is_visible_to_human_reviewer(tmp_path):
    verifier = BundleVerifier(tmp_path)
    verifier.warn_uncited_report_prose(
        "# Timeline\n\nAlice enrolled in Yale in 2024 and received a doctorate in 2027.\n"
        "* [VCLM-01] Alice holds_position Professor at Yale University.\n"
        "```\nAn uncited example inside a code fence should be ignored.\n```\n"
    )
    assert len(verifier.warnings) == 1
    assert "recall_report.md:3: uncited prose" in verifier.warnings[0]
    assert not verifier.errors  # A deterministic check does not classify prose as true/false.


@pytest.mark.parametrize("predicate,excerpt,expected", [
    ("graduated_from", "Yale University Degree Candidates: Alice Wang", "degree candidacy"),
    ("received_degree", "Yale University Degree Candidates: Alice Wang", "degree candidacy"),
    ("employed_by", "Alice Wang is a shareholder of Yale University", "shareholding"),
])
def test_predicates_cannot_upgrade_candidacy_or_ownership(tmp_path, predicate, excerpt, expected):
    (tmp_path / "source.txt").write_text(excerpt)
    claim = {
        "claim_id": "VCLM-01", "candidate_id": "CAND-01", "subject": "Alice Wang",
        "predicate": predicate, "object": "Yale University",
        "source_id": "SRC-01", "verbatim_excerpt": excerpt,
    }
    (tmp_path / "verified_claims.jsonl").write_text(json.dumps(claim) + "\n")
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {"local_path": "source.txt", "http_status": 200, "evidence_status": "usable"}}
    verifier.audit_claims()
    assert any(expected in error for error in verifier.errors)


@pytest.mark.parametrize("status", ["withdrawn", "unverified", "retrieval_failed"])
def test_retained_rejected_source_cannot_back_a_verified_claim(tmp_path, status):
    (tmp_path / "source.txt").write_text("Alice Wang works at Yale University.")
    (tmp_path / "verified_claims.jsonl").write_text(json.dumps({
        "claim_id": "VCLM-01", "subject": "Alice Wang", "predicate": "affiliated_with",
        "object": "Yale University", "source_id": "SRC-01",
        "verbatim_excerpt": "Alice Wang works at Yale University.",
    }))
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {"local_path": "source.txt", "http_status": 200, "evidence_status": status}}
    verifier.audit_claims()
    assert any(f"cites {status} source" in error for error in verifier.errors)


def test_s4_is_a_lead_even_when_its_excerpt_replays(tmp_path):
    excerpt = "Alice Wang works at Yale University."
    (tmp_path / "source.txt").write_text(excerpt)
    (tmp_path / "verified_claims.jsonl").write_text(json.dumps({
        "claim_id": "VCLM-01", "subject": "Alice Wang", "predicate": "affiliated_with",
        "object": "Yale University", "source_id": "SRC-01",
        "evidence_strength": "S4", "verbatim_excerpt": excerpt,
    }))
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {"local_path": "source.txt", "http_status": 200, "evidence_status": "usable"}}
    verifier.audit_claims()
    assert any("S4 evidence strength" in error for error in verifier.errors)


def test_openalex_author_institution_is_grounded_without_inserted_summary(tmp_path):
    source = tmp_path / "author.json"
    # Pretty printing ensures the subject cannot pass via same-line coincidence.
    source.write_text(json.dumps({
        "id": "https://openalex.org/A123", "display_name": "Alice Wang",
        "last_known_institutions": [{"display_name": "Yale University"}],
    }, indent=2))
    verifier = BundleVerifier(tmp_path)
    assert verifier._find_enclosing_atomic_unit(source, "Yale University", "Alice Wang") == "Alice Wang — Yale University"
    wrong = verifier._find_enclosing_atomic_unit(source, "Yale University", "Bob Smith")
    assert wrong is None or "Bob Smith" not in wrong


@pytest.mark.parametrize("name,count,heading,expected", [
    ("Alice Wang", 1, "About me", True),
    ("Bob Smith", 1, "About me", False),
    ("Alice Wang", 2, "About me", False),
    ("Alice Wang", 1, "News", False),
])
def test_first_person_bio_requires_unique_named_person_and_about_article(tmp_path, name, count, heading, expected):
    source = tmp_path / "bio.html"
    source.write_text(
        ('<div itemscope itemtype="https://schema.org/Person">'
         f'<h3 class="author__name">Dr. {name}</h3></div>') * count
        + '<article itemtype="https://schema.org/CreativeWork">'
        + f'<h1>{heading}</h1><section itemprop="text">'
        + '<p>I received my Ph.D from Yale University.</p></section></article>'
    )
    unit = BundleVerifier(tmp_path)._find_enclosing_atomic_unit(source, "I received my Ph.D from Yale University.", "Alice Wang")
    assert bool(unit and "Alice Wang" in unit) == expected


@pytest.mark.parametrize("current_predicate,old_predicate,obj", [
    ("expressed_interest_in", "participated_in", "Example Population Workshop"),
    ("acknowledged_research_resource", "conducted_research", "Example Imaging Program"),
    ("listed_conference_contribution", "presented_paper", "Conference paper"),
])
def test_regression_reference_does_not_equate_weak_and_completed_actions(current_predicate, old_predicate, obj):
    gold = {"subject": "Mia Fox", "predicate": current_predicate, "object_raw": obj,
            "polarity": "affirmative", "temporal_status": "historical"}
    claim = {"subject": "Mia Fox", "predicate": old_predicate, "object": obj,
             "polarity": "affirmative", "temporal_status": "historical"}
    assert not check_5d_match(claim, gold)


@pytest.fixture
def orcid_record():
    return {
        "orcid-identifier": {"host": "orcid.org", "path": "0000-0000-0000-0001",
                             "uri": "https://orcid.org/0000-0000-0000-0001"},
        "person": {"name": {"given-names": {"value": "Alice"}, "family-name": {"value": "Wang"}},
                   "other-names": {"other-name": [{"content": "Alice Mei Wang"}]},
                   "researcher-urls": {"researcher-url": [{"url-name": "Staff profile",
                                                          "url": {"value": "https://university.edu/alice"}}]}},
        "activities-summary": {
            "employments": {"affiliation-group": [{"summaries": [{"employment-summary": {
                "role-title": "Professor", "department-name": "Computing",
                "organization": {"name": "Yale University"},
                "source": {"source-name": {"value": "Bob Smith"}},
            }}]}]},
            "peer-reviews": {"group": [{"peer-review-group": [{"peer-review-summary": [
                {"reviewer-role": "reviewer", "review-group-id": "issn:1234-5678"}
            ]}]}]},
            "works": {"group": [{"work-summary": {"title": {"value": "Unrelated title"},
                                                 "coauthor": "Bob Smith"}}]},
        },
    }


@pytest.mark.parametrize("subject,excerpt", [
    ("Alice Wang", '"role-title": "Professor"'),
    ("Alice Mei Wang", '"role-title": "Professor", "organization": {"name": "Yale University"}'),
    ("Alice Wang", '"given-names": {"value": "Alice"}, "family-name": {"value": "Wang"}'),
    ("Alice Wang", '"content": "Alice Mei Wang"'),
    ("Alice Wang", '"path": "0000-0000-0000-0001"'),
    ("Alice Wang", '"reviewer-role": "reviewer"'),
    ("Alice Wang", '"url-name": "Staff profile", "url": {"value": "https://university.edu/alice"}'),
])
def test_orcid_owner_fields_are_structurally_grounded(tmp_path, orcid_record, subject, excerpt):
    source = tmp_path / "record.json"
    source.write_text(json.dumps(orcid_record, indent=2))
    unit = BundleVerifier(tmp_path)._find_enclosing_atomic_unit(source, excerpt, subject)
    assert unit == f"{subject} — {excerpt}"


@pytest.mark.parametrize("subject,excerpt", [
    ("Bob Smith", '"role-title": "Professor"'),
    ("Alice Wang", '"title": {"value": "Unrelated title"}'),
    ("Alice Wang", '"source-name": {"value": "Bob Smith"}'),
    ("Alice Wang", '"department-name": "Computing", "reviewer-role": "reviewer"'),
    ("Alice Wang", '"role-title": "Professor", "organization": {"name": "Other University"}'),
    ("Alice Wang", "Professor"),
])
@pytest.mark.parametrize("indent", [None, 2])
def test_orcid_rejects_wrong_owner_unrelated_fields_and_spliced_fragments(tmp_path, orcid_record, subject, excerpt, indent):
    source = tmp_path / "record.json"
    source.write_text(json.dumps(orcid_record, indent=indent))
    assert BundleVerifier(tmp_path)._find_enclosing_atomic_unit(source, excerpt, subject) is None


@pytest.mark.parametrize("title,count,placement,expected", [
    ("Meet Alice Wang of A Studio", 1, "body", True),
    ("Meet Bob Smith of A Studio", 1, "body", False),
    ("Meet Alice Wang and Bob Smith", 1, "body", False),
    ("Meet Alice Wang of A Studio", 2, "body", False),
    ("Meet Alice Wang of A Studio", 1, "outside", False),
    ("Meet Alice Wang of A Studio", 1, "blockquote", False),
    ("Meet Alice Wang of A Studio", 1, "comments", False),
])
def test_interview_requires_named_single_subject_and_owned_paragraph(tmp_path, title, count, placement, expected):
    excerpt = "I studied piano at Yale University."
    paragraph = f"<p>{excerpt}</p>"
    inner = {"body": paragraph, "outside": "", "blockquote": f"<blockquote>{paragraph}</blockquote>",
             "comments": f'<div class="comments">{paragraph}</div>'}[placement]
    content = (f'<article class="interview"><h1>{title}</h1>{inner}</article>') * count
    if placement == "outside":
        content += paragraph
    source = tmp_path / "interview.html"
    source.write_text(content)
    unit = BundleVerifier(tmp_path)._find_enclosing_atomic_unit(source, excerpt, "Alice Wang")
    assert bool(unit and "Alice Wang" in unit) == expected


@pytest.mark.parametrize("name,count,placement,expected", [
    ("Alice Wang", 1, "profile", True),
    ("Bob Smith", 1, "profile", False),
    ("Alice Wang", 2, "profile", False),
    ("Alice Wang", 1, "sidebar", False),
])
def test_portal_research_paragraph_requires_unique_named_person(tmp_path, name, count, placement, expected):
    person = json.dumps({"@type": "Person", "name": name})
    paragraph = "<p>Energy consumption of Software</p>"
    source = tmp_path / "profile.html"
    source.write_text(
        f'<script type="application/ld+json">{person}</script>' * count
        + f"<h1>{name}</h1>"
        + '<section class="person-profileinformation">'
        + (paragraph if placement == "profile" else "") + "</section>"
        + (paragraph if placement == "sidebar" else "")
    )
    unit = BundleVerifier(tmp_path)._find_enclosing_atomic_unit(
        source, "Energy consumption of Software", "Alice Wang"
    )
    assert bool(unit and "Alice Wang" in unit) == expected
