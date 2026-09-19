"""Phase 4.4 regression tests for bounded same-document context claims."""

import json
from datetime import datetime, timezone

from core.extractors.content_locator import locate_evidence_slices
from core.extractors.mention_extractor import extract_mentions_and_aliases
from core.run_profile import route_and_extract_claims
from models.schemas import (
    CandidateEntity,
    Evidence,
    EvidenceLocator,
    LocatorType,
    SourceQualityClass,
    TemporalStatus,
)
from scripts.validate_dossier import validate_bundle
from tests.bundle_factory import create_valid_bundle


def _mentions_for(evidence, target_name):
    mentions = []
    for item in evidence:
        if item.locator.selector_or_page.startswith("document-context:"):
            continue
        mentions.extend(
            extract_mentions_and_aliases(
                source_id=item.source_id,
                raw_text=item.verbatim_excerpt,
                target_name=target_name,
                evidence_id=item.evidence_id,
            )
        )
    return mentions


def _candidate_for(mentions):
    return CandidateEntity(
        candidate_entity_id="CAND-DOC-CONTEXT",
        proposed_cluster_id="CLUST-DOC-CONTEXT",
        mention_ids=[item.mention_id for item in mentions],
    )


def test_authoritative_profile_title_yields_affiliation():
    html = (
        "<html><head><title>Sarah Luckart | Yale School of Medicine</title></head>"
        "<body><h1>Sarah Luckart</h1></body></html>"
    )
    evidence = locate_evidence_slices(
        html_text=html,
        target_name="Sarah Luckart",
        source_id="SRC-TITLE",
        raw_payload_sha256="a" * 64,
        url="https://medicine.yale.edu/profile/sarah-luckart/",
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    title_evidence = next(
        item
        for item in evidence
        if item.locator.selector_or_page == "document-context:profile-title"
    )
    mentions = _mentions_for(evidence, "Sarah Luckart")
    claims = route_and_extract_claims(
        evidence_list=evidence,
        mentions_list=mentions,
        candidates=[_candidate_for(mentions)],
        default_target_name="Sarah Luckart",
    )

    assert any(
        claim.predicate == "affiliated_with"
        and claim.object_raw == "Yale School of Medicine"
        and claim.temporal_status == TemporalStatus.CURRENT
        for claim in claims
    )


def test_personal_education_card_uses_same_source_subject_context():
    filler = "<div>portfolio project filler</div>" * 180
    html = (
        "<html><body><h2>Albert Zhao</h2>"
        "<section id=about><p>My name is <strong>Albert Zhao</strong>, and I am "
        "currently an undergraduate student at Boston University.</p></section>"
        f"{filler}<section id=education><div class=card><div class=float-end>"
        "<small>2021 - Current (Expected May 2025)</small></div>"
        "<h5 class=card-title>B.S. in Computer Engineering</h5>"
        "<h6>Boston University, College of Engineering</h6></div></section>"
        "</body></html>"
    )
    evidence = locate_evidence_slices(
        html_text=html,
        target_name="Albert Zhao",
        source_id="SRC-ALBERT",
        raw_payload_sha256="b" * 64,
        url="https://portfolio.example/",
        source_quality_class=SourceQualityClass.CLASS_C,
    )
    mentions = _mentions_for(evidence, "Albert Zhao")
    claims = route_and_extract_claims(
        evidence_list=evidence,
        mentions_list=mentions,
        candidates=[_candidate_for(mentions)],
        default_target_name="Albert Zhao",
    )

    degree = next(
        claim
        for claim in claims
        if claim.predicate == "received_degree"
        and claim.object_raw == "B.S. in Computer Engineering"
    )
    assert degree.temporal_status == TemporalStatus.FORMER
    assert degree.support_clauses[0].subject_resolution == "document_context"


def test_encyclopedic_leadership_paragraph_uses_same_source_subject_context():
    filler = "<p>biographical filler without a supported relation.</p>" * 120
    html = (
        '<html><body><div class="mw-parser-output"><h1>Ray Liu</h1>'
        "<p><b>Ray Liu</b> is an engineer.</p>"
        f"{filler}<p>Liu was the 2022 IEEE President and CEO.</p>"
        "</div></body></html>"
    )
    evidence = locate_evidence_slices(
        html_text=html,
        target_name="Ray Liu",
        source_id="SRC-RAY",
        raw_payload_sha256="c" * 64,
        url="https://en.wikipedia.org/wiki/Ray_Liu",
        source_quality_class=SourceQualityClass.CLASS_C,
    )
    mentions = _mentions_for(evidence, "Ray Liu")
    claims = route_and_extract_claims(
        evidence_list=evidence,
        mentions_list=mentions,
        candidates=[_candidate_for(mentions)],
        default_target_name="Ray Liu",
    )

    role = next(
        claim
        for claim in claims
        if claim.predicate == "holds_position" and claim.object_raw == "IEEE President"
    )
    assert role.temporal_status == TemporalStatus.FORMER
    assert role.support_clauses[0].subject_resolution == "document_context"


def test_document_context_does_not_cross_source_boundaries():
    profile_html = "<html><body><h1>Ray Liu</h1><p><b>Ray Liu</b> is an engineer.</p></body></html>"
    profile_evidence = locate_evidence_slices(
        html_text=profile_html,
        target_name="Ray Liu",
        source_id="SRC-RAY-A",
        raw_payload_sha256="d" * 64,
        url="https://en.wikipedia.org/wiki/Ray_Liu",
        source_quality_class=SourceQualityClass.CLASS_C,
    )
    relation_evidence = Evidence(
        evidence_id="EVI-FOREIGN-CONTEXT",
        source_id="SRC-RAY-B",
        verbatim_excerpt="<p>Liu was the 2022 IEEE President and CEO.</p>",
        locator=EvidenceLocator(
            locator_type=LocatorType.CSS,
            selector_or_page="document-context:encyclopedic-leadership",
        ),
        retrieved_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_C,
    )
    evidence = profile_evidence + [relation_evidence]
    mentions = _mentions_for(evidence, "Ray Liu")
    claims = route_and_extract_claims(
        evidence_list=evidence,
        mentions_list=mentions,
        candidates=[_candidate_for(mentions)],
        default_target_name="Ray Liu",
    )

    assert not any(
        claim.predicate == "holds_position" and claim.object_raw == "IEEE President"
        for claim in claims
    )


def test_validator_accepts_only_same_source_document_context(tmp_path):
    def build_bundle(path, relation_source_id):
        meta = create_valid_bundle(path)
        sources_path = path / "sources.jsonl"
        sources = [json.loads(line) for line in sources_path.read_text().splitlines()]
        source_hash = sources[0]["content_sha256"]
        if relation_source_id != meta["source_id"]:
            sources.append(
                {
                    "source_id": relation_source_id,
                    "url": "https://other.example/biography",
                    "publisher": "other.example",
                    "content_sha256": source_hash,
                    "http_status": 200,
                }
            )
            sources_path.write_text(
                "".join(json.dumps(item) + "\n" for item in sources),
                encoding="utf-8",
            )

        relation_text = "<p>Smith was the 2022 IEEE President and CEO.</p>"
        evidence_path = path / "evidence.jsonl"
        evidence = [json.loads(line) for line in evidence_path.read_text().splitlines()]
        evidence.append(
            {
                "evidence_id": "EV-02",
                "source_id": relation_source_id,
                "verbatim_excerpt": relation_text,
                "locator": {
                    "locator_type": "css",
                    "selector_or_page": "document-context:encyclopedic-leadership",
                },
                "retrieved_at": datetime(2026, 9, 19, tzinfo=timezone.utc).isoformat(),
                "source_quality_class": "class_c",
                "raw_payload_sha256": source_hash,
                "char_start": 0,
                "char_end": len(relation_text),
            }
        )
        evidence_path.write_text(
            "".join(json.dumps(item) + "\n" for item in evidence),
            encoding="utf-8",
        )

        claims_path = path / "claims.jsonl"
        claim = json.loads(claims_path.read_text().strip())
        claim["object_raw"] = "IEEE President"
        claim["temporal_status"] = "former"
        claim["evidence_ids"] = [meta["evidence_id"], "EV-02"]
        claim["support_clauses"] = [
            {
                "evidence_id": "EV-02",
                "subject_mention_id": meta["mention_id"],
                "clause_span_start": 0,
                "clause_span_end": len(relation_text),
                "verbatim_clause": relation_text,
                "relation_span_start": 0,
                "relation_span_end": len(relation_text),
                "provenance_level": "relation",
                "subject_resolution": "document_context",
            }
        ]
        claims_path.write_text(json.dumps(claim) + "\n", encoding="utf-8")

    same_source = tmp_path / "same-source"
    build_bundle(same_source, "SRC-01")
    assert validate_bundle(same_source)["is_valid"] is True

    cross_source = tmp_path / "cross-source"
    build_bundle(cross_source, "SRC-02")
    result = validate_bundle(cross_source)
    assert result["is_valid"] is False
    assert any("same-source document-context" in error for error in result["errors"])
