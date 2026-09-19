"""Phase 4.3 regression tests for structured profile recall."""

from datetime import datetime, timezone

from core.extractors.claim_extractor import extract_claims_from_evidence
from core.extractors.content_locator import locate_evidence_slices
from core.extractors.mention_extractor import extract_mentions_and_aliases
from models.schemas import (
    Evidence,
    EvidenceLocator,
    LocatorType,
    SourceQualityClass,
    TemporalStatus,
)
from scripts.validate_dossier import check_object_presence


def _extract(text: str, name: str, quality: SourceQualityClass = SourceQualityClass.CLASS_A):
    evidence = Evidence(
        evidence_id="EVI-PHASE43",
        source_id="SRC-PHASE43",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="fixture"),
        retrieved_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
        source_quality_class=quality,
    )
    mentions = extract_mentions_and_aliases(
        source_id=evidence.source_id,
        raw_text=text,
        target_name=name,
        evidence_id=evidence.evidence_id,
    )
    assert mentions
    claims = extract_claims_from_evidence(
        evidence=evidence,
        candidate_entity_id="CAND-PHASE43",
        target_name=name,
        evidence_mentions=mentions,
    )
    return evidence, claims


def test_jsonld_person_job_title_is_bound_to_profile_subject():
    text = (
        '<script type="application/ld+json">'
        '{"@type":"ProfilePage","mainEntity":{"@type":"Person",'
        '"name":"Sarah Luckart","jobTitle":["IT, Business Systems Analyst 2"]}}'
        "</script>"
    )

    _, claims = _extract(text, "Sarah Luckart")

    assert any(
        claim.predicate == "holds_position"
        and claim.object_raw == "Business Systems Analyst"
        and claim.temporal_status == TemporalStatus.CURRENT
        for claim in claims
    )


def test_untrusted_jsonld_profile_does_not_create_structured_claim():
    text = (
        '<script type="application/ld+json">'
        '{"@type":"Person","name":"Sarah Luckart",'
        '"jobTitle":"Business Systems Analyst"}'
        "</script>"
    )

    _, claims = _extract(text, "Sarah Luckart", SourceQualityClass.CLASS_C)

    assert not any(claim.predicate == "holds_position" for claim in claims)


def test_profile_position_container_is_bound_to_preceding_name():
    text = (
        '<div class="name">Yao Sun</div>'
        '<div class="position es">Assistant Professor, '
        "Department of Humanities and Social Sciences</div>"
    )

    _, claims = _extract(text, "Yao Sun")

    assert any(
        claim.predicate == "holds_position"
        and claim.object_raw == "Assistant Professor"
        and claim.temporal_status == TemporalStatus.CURRENT
        for claim in claims
    )


def test_profile_education_section_extracts_primary_degree_only():
    text = (
        '<h1 class="title">Xin Zhou</h1>\n<h3>Education</h3>\n<ul>\n'
        "<li>Stanford University, Ph.D. in mathematics (2013)</li>\n"
        "<li>Peking University, M.S. in mathematics (2008)</li>\n"
        "</ul>"
    )

    _, claims = _extract(text, "Xin Zhou")
    degrees = [claim for claim in claims if claim.predicate == "received_degree"]

    assert [(claim.object_raw, claim.temporal_status) for claim in degrees] == [
        ("Ph.D. in mathematics", TemporalStatus.FORMER)
    ]


def test_roster_heading_assigns_role_to_target_in_same_evidence_section():
    filler = "<div>Other Student</div>\n" * 40
    text = f"<h2>Master's Students</h2>\n{filler}<p>Yining Zhang</p>"

    _, claims = _extract(text, "Yining Zhang")

    assert any(
        claim.predicate == "holds_position"
        and claim.object_raw == "Master's Student"
        and claim.temporal_status == TemporalStatus.CURRENT
        for claim in claims
    )
    assert check_object_presence("Master's Student", "<h2>Master's Students</h2>")
    assert not check_object_presence("Master's Student", "student services")


def test_personal_about_locator_starts_at_real_paragraph_tag():
    filler = "<div>navigation filler</div>" * 300
    html = (
        '<html><body><svg><path d="M1 2.75L4 5"/></svg>'
        '<h2>Albert Zhao</h2><p class="hero">Portfolio</p>'
        f"{filler}"
        '<section id="about"><p>My name is <strong>Albert Zhao</strong>, '
        "and I am currently an undergraduate student at Boston University.</p></section>"
        "</body></html>"
    )

    evidence = locate_evidence_slices(
        html_text=html,
        target_name="Albert Zhao",
        source_id="SRC-ALBERT",
        raw_payload_sha256="a" * 64,
        url="https://portfolio.example/",
        source_quality_class=SourceQualityClass.CLASS_C,
    )

    about_items = [item for item in evidence if "My name is" in item.verbatim_excerpt]
    assert len(about_items) == 1
    assert about_items[0].verbatim_excerpt.startswith("<p>")

    mentions = extract_mentions_and_aliases(
        source_id="SRC-ALBERT",
        raw_text=about_items[0].verbatim_excerpt,
        target_name="Albert Zhao",
        evidence_id=about_items[0].evidence_id,
    )
    claims = extract_claims_from_evidence(
        evidence=about_items[0],
        candidate_entity_id="CAND-ALBERT",
        target_name="Albert Zhao",
        evidence_mentions=mentions,
    )
    assert any(
        claim.predicate == "affiliated_with"
        and claim.object_raw == "Boston University"
        and claim.temporal_status == TemporalStatus.CURRENT
        for claim in claims
    )
