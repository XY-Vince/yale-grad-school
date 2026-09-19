"""Phase 4.2 regression tests for released-claim precision."""

from datetime import datetime, timezone

from core.extractors.claim_extractor import extract_claims_from_evidence
from core.run_profile import route_and_extract_claims
from models.schemas import (
    CandidateEntity,
    EntityMention,
    Evidence,
    EvidenceLocator,
    LocatorType,
    SourceQualityClass,
    TemporalStatus,
)


def _evidence(evidence_id: str, text: str, quality: SourceQualityClass) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        source_id="SRC-PHASE42",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="fixture"),
        retrieved_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
        source_quality_class=quality,
    )


def _mention(evidence: Evidence, mention_id: str, name: str) -> EntityMention:
    start = evidence.verbatim_excerpt.index(name)
    return EntityMention(
        mention_id=mention_id,
        raw_name_text=name,
        source_id=evidence.source_id,
        context_snippet=evidence.verbatim_excerpt,
        evidence_id=evidence.evidence_id,
        mention_key=f"key-{mention_id.lower()}",
        char_start=start,
        char_end=start + len(name),
    )


def test_governance_heading_preserves_complete_role_and_current_temporal_status():
    text = '<h3 class="wp-block-heading">Sarah Luckart, Clerk of the Corporation</h3>'
    evidence = _evidence("EVI-SARAH", text, SourceQualityClass.CLASS_C)
    mention = _mention(evidence, "MEN-SARAH", "Sarah Luckart")

    claims = extract_claims_from_evidence(
        evidence=evidence,
        evidence_mentions=[mention],
        mention_to_cand_id={mention.mention_id: "CAND-SARAH"},
    )

    role_claims = [claim for claim in claims if claim.predicate == "holds_position"]
    assert [(claim.object_raw, claim.temporal_status) for claim in role_claims] == [
        ("Clerk of the Corporation", TemporalStatus.CURRENT)
    ]


def test_route_deduplicates_same_semantic_claim_across_repeated_metadata():
    text_one = (
        '<meta name="description" property="og:description" '
        'content="Rohini Dutta is a Hospital Resident at Yale School of Medicine">'
    )
    text_two = (
        '<meta property="og:description" '
        'content="Rohini Dutta is a Hospital Resident at Yale School of Medicine">'
    )
    evidence_one = _evidence("EVI-ROHINI-1", text_one, SourceQualityClass.CLASS_A)
    evidence_two = _evidence("EVI-ROHINI-2", text_two, SourceQualityClass.CLASS_A)
    mention_one = _mention(evidence_one, "MEN-ROHINI-1", "Rohini Dutta")
    mention_two = _mention(evidence_two, "MEN-ROHINI-2", "Rohini Dutta")
    candidate = CandidateEntity(
        candidate_entity_id="CAND-ROHINI",
        proposed_cluster_id="CLUST-ROHINI",
        mention_ids=[mention_one.mention_id, mention_two.mention_id],
    )

    claims = route_and_extract_claims(
        evidence_list=[evidence_one, evidence_two],
        mentions_list=[mention_one, mention_two],
        candidates=[candidate],
        default_target_name="Rohini Dutta",
    )

    semantic_claims = [(claim.predicate, claim.object_raw) for claim in claims]
    assert semantic_claims.count(("holds_position", "Hospital Resident")) == 1
    assert semantic_claims.count(("affiliated_with", "Yale School of Medicine")) == 1
    assert len(claims) == 2


def test_route_keeps_same_object_when_temporal_status_differs():
    current_text = "Alice Smith is Professor."
    former_text = "Alice Smith was Professor."
    current_evidence = _evidence("EVI-ALICE-CURRENT", current_text, SourceQualityClass.CLASS_A)
    former_evidence = _evidence("EVI-ALICE-FORMER", former_text, SourceQualityClass.CLASS_A)
    current_mention = _mention(current_evidence, "MEN-ALICE-CURRENT", "Alice Smith")
    former_mention = _mention(former_evidence, "MEN-ALICE-FORMER", "Alice Smith")
    candidate = CandidateEntity(
        candidate_entity_id="CAND-ALICE",
        proposed_cluster_id="CLUST-ALICE",
        mention_ids=[current_mention.mention_id, former_mention.mention_id],
    )

    claims = route_and_extract_claims(
        evidence_list=[current_evidence, former_evidence],
        mentions_list=[current_mention, former_mention],
        candidates=[candidate],
        default_target_name="Alice Smith",
    )

    professor_claims = [
        claim
        for claim in claims
        if claim.predicate == "holds_position" and claim.object_raw == "Professor"
    ]
    assert {claim.temporal_status for claim in professor_claims} == {
        TemporalStatus.CURRENT,
        TemporalStatus.FORMER,
    }
