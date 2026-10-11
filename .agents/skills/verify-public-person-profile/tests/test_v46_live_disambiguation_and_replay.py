"""
Test suite for V4.6 Live Disambiguation and Substantive WARC Provenance Replay.
Covers:
1. Substantive WARC replay verification (tamper detection in WARC payload, nonexistent record IDs).
2. Claim-level Evidence-to-WARC provenance closure (tamper detection in verbatim_excerpt).
3. Clean decoupling of structural_valid vs provenance_replay_valid.
4. Yale Biostatistics vs Internal Medicine direct Cannot-Link without CIRA anchor.
5. Joint appointment exception in collegiate unit conflict: exempts hard cannot-link but remains in REVIEW (no auto-merge).
6. Claim extraction for Ph.D. without "Ph." truncation, SUNY Albany, and Associate Research Scientist.
7. Clean organization extraction without job title contamination or split fragments.
"""

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError
from core.extractors.claim_extractor import extract_claims_from_evidence
from core.resolver import (
    EntityMention,
    detect_cannot_link,
    resolve_mentions,
    extract_organizations,
)
from models.schemas import (
    Evidence,
    EvidenceLocator,
    LocatorType,
    MachineRelation,
    SourceQualityClass,
)
from core.run_profile import route_and_extract_claims, run_pipeline
from scripts.run_live_blind_test import run_live_blind_test, run_targeted_warc_replay
from scripts.validate_dossier import validate_bundle, verify_warc_replay


SKILL_ROOT = Path(__file__).resolve().parent.parent
DISAMB_DIR = SKILL_ROOT / "runs" / "xin_zhou_disambiguation"
DISAMB_BUNDLE = DISAMB_DIR / "bundle"
DISAMB_WARC = DISAMB_DIR / "corpus.warc"

LIVE_DIR = SKILL_ROOT / "runs" / "live_xin_zhou"
LIVE_BUNDLE = LIVE_DIR / "bundle"
LIVE_WARC = LIVE_DIR / "corpus.warc"


def make_evidence(text: str, ev_id: str = "EV-TEST", src_id: str = "SRC-TEST") -> Evidence:
    return Evidence(
        evidence_id=ev_id,
        source_id=src_id,
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )


def make_mention(name: str, snippet: str, mid: str = "MEN-1", sid: str = "SRC-1", eid: str = "EV-1") -> EntityMention:
    c_start = snippet.find(name)
    if c_start < 0:
        c_start = 0
        snippet = f"{name} {snippet}"
    c_end = c_start + len(name)
    mkey = hashlib.sha256(f"{sid}:{c_start}:{c_end}".encode("utf-8")).hexdigest()[:16]
    return EntityMention(
        mention_id=mid,
        raw_name_text=name,
        source_id=sid,
        evidence_id=eid,
        context_snippet=snippet,
        mention_key=mkey,
        char_start=c_start,
        char_end=c_end,
    )


def test_xin_zhou_bundle_replays_successfully():
    """Verify that the actual dual-entity synthetic fixture bundle validates cleanly with WARC replay."""
    assert DISAMB_BUNDLE.exists(), f"Bundle dir {DISAMB_BUNDLE} must exist"
    assert DISAMB_WARC.exists(), f"WARC fixture {DISAMB_WARC} must exist"

    # Validation without WARC -> provenance_replay_valid is None
    res_no_warc = validate_bundle(DISAMB_BUNDLE, warc_path=None)
    assert res_no_warc["is_valid"] is True
    assert res_no_warc["layers"]["structural_valid"] is True
    assert res_no_warc["layers"]["warc_record_ids_present"] is True
    assert res_no_warc["layers"]["provenance_replay_valid"] is None

    # Validation with WARC -> substantive replay passes
    res_with_warc = validate_bundle(DISAMB_BUNDLE, warc_path=DISAMB_WARC)
    assert res_with_warc["is_valid"] is True
    assert res_with_warc["layers"]["structural_valid"] is True
    assert res_with_warc["layers"]["provenance_replay_valid"] is True
    assert res_with_warc["error_count"] == 0


def test_warc_replay_detects_tampered_warc_payload(tmp_path):
    """
    If bytes inside the physical WARC payload are tampered with,
    substantive replay MUST fail while structural validation remains decoupled and passing.
    """
    tampered_warc = tmp_path / "tampered.warc"
    warc_bytes = DISAMB_WARC.read_bytes()
    assert b"precision medicine" in warc_bytes
    # Tamper payload bytes directly in the WARC archive
    tampered_bytes = warc_bytes.replace(b"precision medicine", b"invented medicine")
    tampered_warc.write_bytes(tampered_bytes)

    res = validate_bundle(DISAMB_BUNDLE, warc_path=tampered_warc)
    assert res["is_valid"] is False
    assert res["layers"]["structural_valid"] is True  # Decoupled!
    assert res["layers"]["provenance_replay_valid"] is False
    assert any("does not match recomputed WARC payload SHA-256" in e for e in res["errors"])


def test_warc_replay_detects_tampered_evidence_verbatim_excerpt(tmp_path):
    """
    Claim-level evidence closure: If Evidence.verbatim_excerpt is altered to content
    not found in the WARC payload (even if hashes are kept constant), replay MUST fail.
    """
    bundle_copy = tmp_path / "bundle"
    shutil.copytree(DISAMB_BUNDLE, bundle_copy)

    ev_file = bundle_copy / "evidence.jsonl"
    text = ev_file.read_text(encoding="utf-8")
    assert "precision medicine" in text
    # Replace precision medicine (18 chars) with invented statement (18 chars)
    tampered_text = text.replace("precision medicine", "invented statement")
    ev_file.write_text(tampered_text, encoding="utf-8")

    res = validate_bundle(bundle_copy, warc_path=DISAMB_WARC)
    assert res["is_valid"] is False
    assert res["layers"]["structural_valid"] is True  # Decoupled!
    assert res["layers"]["provenance_replay_valid"] is False
    assert any("verbatim_excerpt is not found in the WARC record payload" in e for e in res["errors"])


def test_warc_replay_detects_nonexistent_warc_id(tmp_path):
    """If a source references a fabricated warc_record_id, replay MUST fail closed."""
    bundle_copy = tmp_path / "bundle"
    shutil.copytree(DISAMB_BUNDLE, bundle_copy)

    sources_file = bundle_copy / "sources.jsonl"
    lines = sources_file.read_text(encoding="utf-8").strip().splitlines()
    first_src = json.loads(lines[0])
    first_src["warc_record_id"] = "<urn:uuid:00000000-0000-0000-0000-000000000000>"
    lines[0] = json.dumps(first_src)
    sources_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    res = validate_bundle(bundle_copy, warc_path=DISAMB_WARC)
    assert res["is_valid"] is False
    assert res["layers"]["structural_valid"] is True  # Decoupled!
    assert res["layers"]["provenance_replay_valid"] is False
    assert any("not found in WARC" in e for e in res["errors"])


def test_cira_ablation_direct_cannot_link():
    """
    Yale Biostatistics (YSPH) vs Yale Internal Medicine (mHealth) MUST trigger
    Cannot-Link directly without relying on an intermediate CIRA anchor.
    """
    m_biostat = make_mention(
        name="Xin Zhou",
        snippet="Xin Zhou, Assistant Professor of Biostatistics at Yale School of Public Health (YSPH).",
        mid="MEN-BIOSTAT",
        sid="SRC-1",
        eid="EV-1",
    )
    m_medicine = make_mention(
        name="Xin Zhou",
        snippet="Xin Zhou, Associate Research Scientist in Internal Medicine at Yale School of Medicine working on mHealth.",
        mid="MEN-MEDICINE",
        sid="SRC-2",
        eid="EV-2",
    )

    assert detect_cannot_link(m_biostat, m_medicine) is True

    matches, clusters = resolve_mentions([m_biostat, m_medicine])
    assert len(clusters) == 2
    assert matches[0].machine_relation == MachineRelation.NONMATCH
    assert matches[0].match_probability == 0.0


def test_joint_appointment_exception_allows_link_or_review():
    """
    If an entity profile explicitly indicates a joint or secondary appointment:
    1. The collegiate unit Cannot-Link rule MUST NOT falsely fire.
    2. Crucially, the joint cue MUST NOT serve as positive identity corroboration!
       Mentions across collegiate units MUST remain in REVIEW and NOT auto-merge.
    """
    m_primary = make_mention(
        name="Xin Zhou",
        snippet="Xin Zhou, Assistant Professor of Biostatistics at Yale School of Public Health.",
        mid="MEN-PRIM",
        sid="SRC-1",
        eid="EV-1",
    )
    m_joint = make_mention(
        name="Xin Zhou",
        snippet="Xin Zhou holds a secondary appointment in Internal Medicine at Yale School of Medicine.",
        mid="MEN-JOINT",
        sid="SRC-2",
        eid="EV-2",
    )

    # Cannot-link must not trigger
    assert detect_cannot_link(m_primary, m_joint) is False

    # Resolution graph: must NOT auto-merge! Must remain in REVIEW and 2 separate clusters
    matches, clusters = resolve_mentions([m_primary, m_joint])
    assert len(clusters) == 2
    assert matches[0].machine_relation == MachineRelation.REVIEW
    assert matches[0].match_probability == 0.50


def test_claim_extraction_phd_without_truncation():
    """
    Ph.D. in sentences must not cause the sentence splitter to truncate
    at Ph., and must extract both degree and institution cleanly.
    """
    text = (
        "Xin Zhou received his Ph.D. in Biostatistics from the University of North Carolina at Chapel Hill in 2019. "
        "He subsequently joined Harvard as a postdoctoral fellow."
    )
    ev = make_evidence(text)
    claims = extract_claims_from_evidence(ev, "CAND-TEST-1", subject_mention_id="MEN-TEST-1", target_name="Xin Zhou")

    degree_claims = [c for c in claims if c.predicate in ("received_degree", "holds_position")]
    assert any("Biostatistics" in c.object_raw for c in degree_claims)

    inst_claims = [c for c in claims if c.predicate == "graduated_from"]
    assert any("University of North Carolina at Chapel Hill" in c.object_raw for c in inst_claims)

    for c in claims:
        assert c.object_raw != "Ph"
        assert not c.object_raw.startswith("D. in")


def test_claim_extraction_suny_albany_and_associate_research_scientist():
    """
    Verify extraction of SUNY at Albany degree and Associate Research Scientist position.
    """
    text = (
        "Xin Zhou is an Associate Research Scientist at Yale School of Medicine. "
        "He received his Ph.D. in Communication from SUNY at Albany."
    )
    ev = make_evidence(text)
    claims = extract_claims_from_evidence(ev, "CAND-TEST-2", subject_mention_id="MEN-TEST-2", target_name="Xin Zhou")

    pos_claims = [c for c in claims if c.predicate == "holds_position"]
    assert any("Associate Research Scientist" in c.object_raw for c in pos_claims)

    grad_claims = [c for c in claims if c.predicate == "graduated_from"]
    assert any("SUNY at Albany" in c.object_raw for c in grad_claims)


def test_extract_organizations_filters_generic_and_punctuation():
    """
    extract_organizations should extract clean institution entities and enforce negative
    constraints against job title contamination and split fragment tokens.
    """
    text = (
        "Dr. Xin Zhou is an Assistant Professor of Biostatistics at Yale University. "
        "He completed his training at Harvard T.H. Chan School of Public Health. "
        "He collaborates with the Center for Interdisciplinary Research on AIDS at Yale University."
    )
    orgs = extract_organizations(text)
    lower_orgs = [o.lower() for o in orgs]

    # Positive expectations
    assert any("yale university" in o for o in lower_orgs)
    assert any("harvard t.h. chan school of public health" in o for o in lower_orgs)
    assert any("center for interdisciplinary research on aids" in o for o in lower_orgs)

    # Negative constraints: forbid contaminating phrases and fragments
    assert "chan school of public health" not in lower_orgs
    assert "assistant professor of biostatistics at yale university" not in lower_orgs
    assert "center for interdisciplinary research on aids at yale university" not in lower_orgs
    assert "department" not in lower_orgs
    assert not any(o.endswith(".") for o in orgs)


def test_prohibit_of_biostatistics_and_preposition_fragment():
    """
    TDD Test 1: Forbid 'of Biostatistics' preposition fragment.
    Must extract clean 'Department of Biostatistics' and 'Yale School of Public Health'.
    """
    text = (
        "<p>Biography: Dr. Xin Zhou is an Assistant Professor in the Department of "
        "Biostatistics at the Yale School of Public Health.</p>"
    )
    ev = make_evidence(text)
    claims = extract_claims_from_evidence(ev, "CAND-BIOSTAT", subject_mention_id="MEN-BIOSTAT", target_name="Xin Zhou")
    affils = [c.object_raw for c in claims if c.predicate == "affiliated_with"]
    lower_affils = [a.lower() for a in affils]

    # Negative constraints: forbid prepositional fragment
    assert "of biostatistics" not in lower_affils
    assert not any(a.startswith("of ") for a in lower_affils)

    # Positive requirements: full organization headword must be captured
    assert any("department of biostatistics" in a for a in lower_affils)
    assert any("yale school of public health" in a for a in lower_affils)


def test_mhealth_candidate_extracts_yale_medicine_affiliation():
    """
    TDD Test 2: mHealth candidate profile line and biography must extract
    Yale School of Medicine and Department of Internal Medicine affiliation.
    """
    text = (
        "<h1>Xin Zhou, PhD</h1>\n"
        "<p>Position: Associate Research Scientist, Section of Infectious Diseases, "
        "Department of Internal Medicine, Yale School of Medicine.</p>\n"
        "<p>Biography: Dr. Xin Zhou is a junior faculty member in the Yale School of Medicine AIDS Program.</p>"
    )
    ev = make_evidence(text)
    claims = extract_claims_from_evidence(ev, "CAND-MHEALTH", subject_mention_id="MEN-MHEALTH", target_name="Xin Zhou")
    affils = [c.object_raw for c in claims if c.predicate == "affiliated_with"]
    lower_affils = [a.lower() for a in affils]

    assert any("yale school of medicine" in a for a in lower_affils), f"Missing Yale School of Medicine in {affils}"
    assert any("internal medicine" in a for a in lower_affils), f"Missing Internal Medicine in {affils}"
    assert all(
        c.temporal_status.value == "current"
        for c in claims
        if c.predicate in {"affiliated_with", "holds_position"}
    ), "Current Profile fields must not inherit temporal state from a preceding clause"


def test_extract_chinese_school_beijing_101_middle_school():
    """
    TDD Test 3: Chinese education extraction must recognize '北京一零一中'
    in graduation context without using an overly broad bare '中' suffix.
    """
    text = "李嘉文毕业于北京一零一中，现为耶鲁大学游泳队，荣获 CSCAA Individual Scholar All-America Team 荣誉"
    ev = make_evidence(text)
    claims = extract_claims_from_evidence(ev, "CAND-LJW", subject_mention_id="MEN-LJW", target_name="李嘉文")
    grad_claims = [c.object_raw for c in claims if c.predicate == "graduated_from"]

    assert any("北京一零一中" in g for g in grad_claims), f"Failed to extract 北京一零一中, got {grad_claims}"

    noisy_ev = make_evidence("李嘉文毕业于北京中，随后参加校友活动", ev_id="EV-LJW-NOISE")
    noisy_claims = extract_claims_from_evidence(
        noisy_ev,
        "CAND-LJW",
        subject_mention_id="MEN-LJW",
        target_name="李嘉文",
    )
    assert not any(
        c.predicate == "graduated_from" and c.object_raw == "北京中"
        for c in noisy_claims
    ), "A bare 中 suffix must not create a school claim"


@pytest.mark.skipif(not (LIVE_BUNDLE.exists() and LIVE_WARC.exists()), reason="live_xin_zhou fixture required")
def test_live_xin_zhou_warc_replay_and_bundle_validity():
    """
    Targeted Real-Web Integration Test:
    Verify that the targeted real-page crawl bundle for Zhou Xin (Yale)
    validates with 0 errors and passes provenance replay against
    the authentic 766KB WARC archive.
    """
    assert LIVE_BUNDLE.exists(), f"Live bundle dir {LIVE_BUNDLE} must exist"
    assert LIVE_WARC.exists(), f"Live WARC file {LIVE_WARC} must exist"
    assert LIVE_WARC.stat().st_size > 500_000, f"Live WARC must contain recorded crawl payload, got {LIVE_WARC.stat().st_size} bytes"

    # Validation with WARC -> 3 structural/provenance layers pass, semantic layer is PARTIAL (9 unadjudicated claims)
    res = validate_bundle(LIVE_BUNDLE, warc_path=LIVE_WARC)
    assert res["is_valid"] is True
    assert res["error_count"] == 0
    assert res["layers"]["structural_valid"] is True
    assert res["layers"]["warc_record_ids_present"] is True
    assert res["layers"]["provenance_replay_valid"] is True
    assert res["layers"]["semantic_review_passed"] is False, "Semantic review must be PARTIAL pending claim adjudication"
    assert res["audit_details"]["warc_replay_verified"] is True
    assert res["audit_details"]["unadjudicated_claim_count"] == 9

    # Manifest and outcome check
    manifest_path = LIVE_BUNDLE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == "ambiguous_identity"
    assert manifest["pages_fetched"] == 3

    # Dossier ambiguity check: candidate clusters separated cleanly
    dossier_path = LIVE_BUNDLE / "dossier.json"
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    assert len(dossier["ambiguous_candidates"]) >= 2
    assert "CAND-1940fe4aefdf" in dossier["ambiguous_candidates"]
    assert "CAND-238ef964c826" in dossier["ambiguous_candidates"]


@pytest.mark.skipif(not LIVE_WARC.exists(), reason="live_xin_zhou WARC fixture required")
def test_live_xin_zhou_pipeline_execution_from_warc(tmp_path):
    """
    Targeted Integration Test:
    Verify that executing the full pipeline directly against the 766KB WARC
    dynamically produces a complete valid bundle with 0 errors rather than only reading pre-baked files.
    """
    out_dir = tmp_path / "live_xin_zhou"
    bundle_dir, res = run_targeted_warc_replay(
        target_name="Xin Zhou",
        output_dir=out_dir,
        offline_corpus=LIVE_WARC,
    )
    assert res["is_valid"] is True
    assert res["error_count"] == 0
    assert res["layers"]["structural_valid"] is True
    assert res["layers"]["warc_record_ids_present"] is True
    assert res["layers"]["provenance_replay_valid"] is True
    assert res["layers"]["semantic_review_passed"] is False  # Unadjudicated claims -> PARTIAL
    assert res["audit_details"]["unadjudicated_claim_count"] == 10

    # Verify dossier content in tmp_path
    dossier_md = (bundle_dir / "dossier.md").read_text(encoding="utf-8")
    assert "CAND-1940fe4aefdf" in dossier_md
    assert "CAND-238ef964c826" in dossier_md
    assert "关联断言数: 6" in dossier_md
    assert "holds_position`: Postdoc Fellow" in dossier_md  # All 6 claims rendered without truncation


def test_run_pipeline_warc_convergence(tmp_path):
    """
    P0 Official Pipeline WARC Convergence Gate:
    Directly invokes the canonical run_pipeline() entry point against the recorded WARC archive.
    Enforces that:
    1. Outcome is strictly ambiguous_identity.
    2. Primary candidate is not automatically selected (None in dossier, statements is empty).
    3. Both candidate entities have their claims extracted (Medicine: 4 claims, Biostatistics: 6 claims).
    4. Review edges between candidate entities never accompany completed.
    5. Four-layer quality validator passes with 3 structural/provenance layers True, semantic layer PARTIAL.
    """
    out_dir = tmp_path / "pipeline_convergence_bundle"
    bundle_dir = run_pipeline(
        target_name="Xin Zhou",
        hints=["Yale"],
        output_dir=out_dir,
        offline_corpus=LIVE_WARC,
        aliases=["xinzhoubiostat"],
    )

    # 1. Outcome & Manifest verification
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == "ambiguous_identity", "Outcome must be ambiguous_identity, not completed"

    # 2. Dossier structure verification
    dossier = json.loads((bundle_dir / "dossier.json").read_text(encoding="utf-8"))
    assert dossier["candidate_entity_id"] is None, "Dossier candidate_entity_id must be None on ambiguous outcome"
    assert len(dossier["statements"]) == 0, "Dossier statements must be empty on ambiguous outcome"
    assert len(dossier["ambiguous_candidates"]) >= 2, "Candidate entities must be reported in ambiguous_candidates"

    # 3. Cluster Purity & Anti-Merge Assertions
    candidates = [json.loads(line) for line in (bundle_dir / "candidates.jsonl").read_text(encoding="utf-8").strip().split("\n") if line]
    mentions = [json.loads(line) for line in (bundle_dir / "mentions.jsonl").read_text(encoding="utf-8").strip().split("\n") if line]
    m_by_id = {m["mention_id"]: m for m in mentions}

    # Identify Medicine and Biostatistics candidates
    c_med = next(c for c in candidates if c["candidate_entity_id"] == "CAND-1940fe4aefdf")
    c_bio = next(c for c in candidates if c["candidate_entity_id"] == "CAND-238ef964c826")

    # Medicine cluster purity: 100% of mentions must come from Yale Medicine source (SRC-7e855f47616b8fae)
    # Crucially: MUST NOT contain any mentions from GitHub (SRC-5641f40184aa20cc)
    med_mentions = [m_by_id[m_id] for m_id in c_med["mention_ids"]]
    assert len(med_mentions) == 2, f"Expected 2 medicine mentions, got {len(med_mentions)}"
    assert all(m["source_id"] == "SRC-7e855f47616b8fae" for m in med_mentions), "Medicine candidate must only contain Yale Medicine mentions"
    assert not any(m["source_id"] == "SRC-5641f40184aa20cc" for m in med_mentions), "GitHub mentions must NEVER merge into Medicine candidate"

    # Biostatistics cluster purity: 100% of mentions must come from CIRA/YSPH source (SRC-1762db822896a788)
    bio_mentions = [m_by_id[m_id] for m_id in c_bio["mention_ids"]]
    assert len(bio_mentions) == 3, f"Expected 3 biostatistics mentions, got {len(bio_mentions)}"
    assert all(m["source_id"] == "SRC-1762db822896a788" for m in bio_mentions), "Biostatistics candidate must only contain CIRA mentions"
    assert not any(m["source_id"] == "SRC-5641f40184aa20cc" for m in bio_mentions), "GitHub mentions must NEVER merge into Biostatistics candidate"

    # GitHub mentions must form their own isolated cluster/candidate
    github_cands = [c for c in candidates if any(m_by_id[m_id]["source_id"] == "SRC-5641f40184aa20cc" for m_id in c["mention_ids"])]
    assert len(github_cands) >= 1
    assert all(c["candidate_entity_id"] not in ("CAND-1940fe4aefdf", "CAND-238ef964c826") for c in github_cands)

    # Ensure NO modal/dialog/overlay mentions exist in the bundle
    assert not any("block or report" in m["context_snippet"].lower() for m in mentions), "Overlay mention 'Block or report' must be excluded"
    assert not any("overlay-title" in m["context_snippet"].lower() for m in mentions), "Overlay-title must be excluded from mentions"
    assert not any("block or report" in m["raw_name_text"].lower() for m in mentions), "Overlay text must not be extracted as raw name"

    # 4. Two-candidate claims extracted
    claims = [json.loads(line) for line in (bundle_dir / "claims.jsonl").read_text(encoding="utf-8").strip().split("\n") if line]
    assert len(claims) == 10, f"Expected exactly 10 claims across both candidates, got {len(claims)}"
    c1_claims = [c for c in claims if c["candidate_entity_id"] == "CAND-1940fe4aefdf"]
    c2_claims = [c for c in claims if c["candidate_entity_id"] == "CAND-238ef964c826"]
    assert len(c1_claims) == 4, f"Expected 4 medicine claims, got {len(c1_claims)}"
    assert len(c2_claims) == 6, f"Expected 6 biostatistics claims, got {len(c2_claims)}"
    assert any(
        c["predicate"] == "holds_position"
        and c["object_raw"] == "Associate Research Scientist"
        and c["temporal_status"] == "current"
        for c in c1_claims
    ), "The structured Yale Medicine profile title must be retained as a current claim"

    # 5. Review edges discipline: review edges must NOT accompany completed
    matches = [json.loads(line) for line in (bundle_dir / "matches.jsonl").read_text(encoding="utf-8").strip().split("\n") if line]
    has_review = any(m["machine_relation"] == "review" for m in matches)
    assert has_review, "Cross-entity review edges must be recorded"
    assert manifest["run_outcome"] != "completed", "Review edges must never accompany completed"

    # 6. Validator pass
    res = validate_bundle(bundle_dir, warc_path=LIVE_WARC)
    assert res["is_valid"] is True
    assert res["error_count"] == 0
    assert res["layers"]["structural_valid"] is True
    assert res["layers"]["warc_record_ids_present"] is True
    assert res["layers"]["provenance_replay_valid"] is True
    assert res["layers"]["semantic_review_passed"] is False
    assert res["audit_details"]["unadjudicated_claim_count"] == 10


def test_candidate_scoped_contradiction_detection():
    """
    Verifies:
    1. Two DIFFERENT candidates having affirmative and negative claims on the same predicate/object
       does NOT trigger CONTRADICTORY_EVIDENCE (returns AMBIGUOUS_IDENTITY).
    2. The SAME candidate having affirmative and negative claims with overlapping validity
       DOES trigger CONTRADICTORY_EVIDENCE.
    3. The SAME candidate having non-overlapping past vs current claims does NOT trigger CONTRADICTORY_EVIDENCE.
    """
    from core.run_profile import determine_state_outcome
    from models.schemas import CandidateEntity, Claim, FactPolarity, TemporalStatus, RunOutcome, ClaimEvidenceSupport

    support = [ClaimEvidenceSupport(
        evidence_id="EVI-01",
        subject_mention_id="MEN-01",
        clause_span_start=0,
        clause_span_end=20,
        verbatim_clause="Held position of Dean",
    )]

    cand_a = CandidateEntity(candidate_entity_id="CAND-A", proposed_cluster_id="CLUST-A", mention_ids=["MEN-01"])
    cand_b = CandidateEntity(candidate_entity_id="CAND-B", proposed_cluster_id="CLUST-B", mention_ids=["MEN-02"])

    # 1. Cross-candidate opposite statements: CAND-A is Dean, CAND-B is NOT Dean
    claim_a = Claim(
        claim_id="CLM-01",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    claim_b = Claim(
        claim_id="CLM-02",
        candidate_entity_id="CAND-B",
        subject_mention_id="MEN-02",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.CURRENT,
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    outcome, primary, ambig = determine_state_outcome(
        candidates=[cand_a, cand_b],
        claims=[claim_a, claim_b],
        pages_fetched=2,
    )
    assert outcome != RunOutcome.CONTRADICTORY_EVIDENCE, "Cross-candidate statements must not be treated as contradiction"

    # 2. Same candidate opposite statements with temporal overlap (both CURRENT):
    claim_a_neg = Claim(
        claim_id="CLM-03",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.CURRENT,
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    outcome2, _, _ = determine_state_outcome(
        candidates=[cand_a],
        claims=[claim_a, claim_a_neg],
        pages_fetched=1,
    )
    assert outcome2 == RunOutcome.CONTRADICTORY_EVIDENCE, "Same candidate overlapping contradiction must trigger CONTRADICTORY_EVIDENCE"

    # 3. Same candidate non-overlapping past vs current:
    claim_a_past_neg = Claim(
        claim_id="CLM-04",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.FORMER,
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    outcome3, _, _ = determine_state_outcome(
        candidates=[cand_a],
        claims=[claim_a, claim_a_past_neg],
        pages_fetched=1,
    )
    assert outcome3 != RunOutcome.CONTRADICTORY_EVIDENCE, "Past vs current non-overlapping statements must not trigger contradiction"


def test_explicit_date_interval_overlap_disjoint_and_boundary_cases():
    """
    P0 Test: Explicit date interval comparison with precision-aware boundary conversion.
    Verifies that:
    1. Overlapping intervals trigger CONTRADICTORY_EVIDENCE.
    2. Disjoint intervals do NOT trigger CONTRADICTORY_EVIDENCE.
    3. Contiguous boundary touching intervals (e.g. adjacent years/months/days) do NOT trigger CONTRADICTORY_EVIDENCE.
    4. DateWithPrecision methods to_iso_date() and get_bounds() operate without AttributeError.
    """
    from datetime import date
    from core.run_profile import determine_state_outcome, check_temporal_overlap
    from models.schemas import (
        CandidateEntity,
        Claim,
        ClaimEvidenceSupport,
        DatePrecision,
        DateWithPrecision,
        FactPolarity,
        RunOutcome,
        TemporalStatus,
    )

    # 0. Test DateWithPrecision methods directly
    dwp_year = DateWithPrecision(date_value=date(2020, 1, 1), precision=DatePrecision.YEAR)
    assert dwp_year.to_iso_date() == "2020-01-01"
    assert dwp_year.get_bounds() == (date(2020, 1, 1), date(2020, 12, 31))

    dwp_month = DateWithPrecision(date_value=date(2020, 5, 1), precision=DatePrecision.MONTH)
    assert dwp_month.get_bounds() == (date(2020, 5, 1), date(2020, 5, 31))

    dwp_day = DateWithPrecision(date_value=date(2020, 5, 31), precision=DatePrecision.DAY)
    assert dwp_day.get_bounds() == (date(2020, 5, 31), date(2020, 5, 31))

    support = [
        ClaimEvidenceSupport(
            evidence_id="EVI-01",
            subject_mention_id="MEN-01",
            clause_span_start=0,
            clause_span_end=20,
            verbatim_clause="Held position of Dean",
        )
    ]
    cand = CandidateEntity(candidate_entity_id="CAND-A", proposed_cluster_id="CLUST-A", mention_ids=["MEN-01"])

    # 1. Overlapping intervals: Claim 1 [2018, 2021], Claim 2 [2020, 2023] (both YEAR)
    c_aff_overlap = Claim(
        claim_id="CLM-O1",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2018, 1, 1), precision=DatePrecision.YEAR),
        valid_to=DateWithPrecision(date_value=date(2021, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_overlap = Claim(
        claim_id="CLM-O2",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2020, 1, 1), precision=DatePrecision.YEAR),
        valid_to=DateWithPrecision(date_value=date(2023, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_overlap, c_neg_overlap) is True
    outcome, _, _ = determine_state_outcome(candidates=[cand], claims=[c_aff_overlap, c_neg_overlap], pages_fetched=1)
    assert outcome == RunOutcome.CONTRADICTORY_EVIDENCE

    # 1b. Overlapping interval with CURRENT vs FORMER (User Counterexample):
    # c_aff: 2024-01-01 to 2025-12-31 (CURRENT)
    # c_neg: 2025-01-01 to 2026-01-01 (FORMER)
    # Explicitly overlap in 2025 -> must trigger CONTRADICTORY_EVIDENCE despite CURRENT vs FORMER
    c_aff_2025 = Claim(
        claim_id="CLM-O25A",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2024, 1, 1), precision=DatePrecision.DAY),
        valid_to=DateWithPrecision(date_value=date(2025, 12, 31), precision=DatePrecision.DAY),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_2025 = Claim(
        claim_id="CLM-O25B",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.FORMER,
        valid_from=DateWithPrecision(date_value=date(2025, 1, 1), precision=DatePrecision.DAY),
        valid_to=DateWithPrecision(date_value=date(2026, 1, 1), precision=DatePrecision.DAY),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_2025, c_neg_2025) is True
    outcome_2025, _, _ = determine_state_outcome(candidates=[cand], claims=[c_aff_2025, c_neg_2025], pages_fetched=1)
    assert outcome_2025 == RunOutcome.CONTRADICTORY_EVIDENCE

    # 2. Disjoint intervals (相离): Claim 1 [2015, 2018], Claim 2 [2021, 2024]
    c_aff_disjoint = Claim(
        claim_id="CLM-D1",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.FORMER,
        valid_from=DateWithPrecision(date_value=date(2015, 1, 1), precision=DatePrecision.YEAR),
        valid_to=DateWithPrecision(date_value=date(2018, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_disjoint = Claim(
        claim_id="CLM-D2",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.FORMER,
        valid_from=DateWithPrecision(date_value=date(2021, 1, 1), precision=DatePrecision.YEAR),
        valid_to=DateWithPrecision(date_value=date(2024, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_disjoint, c_neg_disjoint) is False
    outcome_d, _, _ = determine_state_outcome(candidates=[cand], claims=[c_aff_disjoint, c_neg_disjoint], pages_fetched=1)
    assert outcome_d != RunOutcome.CONTRADICTORY_EVIDENCE

    # 3. Contiguous boundary touching (边界相接 / adjacent intervals):
    # Year precision: 2019 (ends 2019-12-31) and 2020 (starts 2020-01-01) -> Disjoint
    # Both use CURRENT status to prove date bound comparison runs without FORMER/CURRENT shortcut!
    c_aff_touch_year = Claim(
        claim_id="CLM-T1",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_to=DateWithPrecision(date_value=date(2019, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_touch_year = Claim(
        claim_id="CLM-T2",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2020, 1, 1), precision=DatePrecision.YEAR),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_touch_year, c_neg_touch_year) is False
    outcome_t, _, _ = determine_state_outcome(candidates=[cand], claims=[c_aff_touch_year, c_neg_touch_year], pages_fetched=1)
    assert outcome_t != RunOutcome.CONTRADICTORY_EVIDENCE

    # Month precision: May 2020 (ends 2020-05-31) vs June 2020 (starts 2020-06-01) -> Disjoint
    # Both use FORMER status to prove date bound comparison runs without shortcut!
    c_aff_touch_month = Claim(
        claim_id="CLM-TM1",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.FORMER,
        valid_to=DateWithPrecision(date_value=date(2020, 5, 1), precision=DatePrecision.MONTH),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_touch_month = Claim(
        claim_id="CLM-TM2",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.FORMER,
        valid_from=DateWithPrecision(date_value=date(2020, 6, 1), precision=DatePrecision.MONTH),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_touch_month, c_neg_touch_month) is False

    # 4. Single-day equality (Exact same date opposite claim -> triggers contradiction):
    c_aff_same_day = Claim(
        claim_id="CLM-SD1",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2025, 5, 1), precision=DatePrecision.DAY),
        valid_to=DateWithPrecision(date_value=date(2025, 5, 1), precision=DatePrecision.DAY),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    c_neg_same_day = Claim(
        claim_id="CLM-SD2",
        candidate_entity_id="CAND-A",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Dean",
        polarity=FactPolarity.NEGATIVE,
        temporal_status=TemporalStatus.CURRENT,
        valid_from=DateWithPrecision(date_value=date(2025, 5, 1), precision=DatePrecision.DAY),
        valid_to=DateWithPrecision(date_value=date(2025, 5, 1), precision=DatePrecision.DAY),
        evidence_ids=["EVI-01"],
        support_clauses=support,
    )
    assert check_temporal_overlap(c_aff_same_day, c_neg_same_day) is True
    outcome_sd, _, _ = determine_state_outcome(candidates=[cand], claims=[c_aff_same_day, c_neg_same_day], pages_fetched=1)
    assert outcome_sd == RunOutcome.CONTRADICTORY_EVIDENCE

    # 5. Inverted bounds fail-closed validation (valid_from > valid_to raises ValidationError):
    with pytest.raises(ValidationError) as exc_info:
        Claim(
            claim_id="CLM-INV1",
            candidate_entity_id="CAND-A",
            subject_mention_id="MEN-01",
            predicate="holds_position",
            object_raw="Dean",
            polarity=FactPolarity.AFFIRMATIVE,
            temporal_status=TemporalStatus.CURRENT,
            valid_from=DateWithPrecision(date_value=date(2025, 12, 31), precision=DatePrecision.DAY),
            valid_to=DateWithPrecision(date_value=date(2024, 1, 1), precision=DatePrecision.DAY),
            evidence_ids=["EVI-01"],
            support_clauses=support,
        )
    assert "Invalid temporal interval" in str(exc_info.value)


def test_honorific_same_source_multi_person_anti_merge():
    """
    P0 Minimal Counterexample Test:
    'Xin Zhou presented first. Ming Zhou presented next. Dr. Zhou is a dentist.'
    Enforces that Dr. Zhou is NOT auto-merged into Xin Zhou or Ming Zhou,
    even though they reside in the same source.
    """
    from core.resolver import resolve_mentions
    from models.schemas import EntityMention, MachineRelation

    text = "Xin Zhou presented first. Ming Zhou presented next. Dr. Zhou is a dentist."
    src_id = "SRC-PRESENTATION-PAGE"

    m1 = EntityMention(
        mention_id="MEN-XZ",
        raw_name_text="Xin Zhou",
        source_id=src_id,
        context_snippet=text,
        evidence_id="EVI-01",
        mention_key="key-xz",
        char_start=0,
        char_end=8,
    )
    m2 = EntityMention(
        mention_id="MEN-MZ",
        raw_name_text="Ming Zhou",
        source_id=src_id,
        context_snippet=text,
        evidence_id="EVI-01",
        mention_key="key-mz",
        char_start=26,
        char_end=35,
    )
    m3 = EntityMention(
        mention_id="MEN-DZ",
        raw_name_text="Dr. Zhou",
        source_id=src_id,
        context_snippet=text,
        evidence_id="EVI-01",
        mention_key="key-dz",
        char_start=52,
        char_end=60,
    )

    decisions, clusters = resolve_mentions([m1, m2, m3])

    dec_map = {(d.source_mention_id, d.target_mention_id): d for d in decisions}

    # Dr. Zhou vs Xin Zhou must be REVIEW, never MATCH
    d_xz_dz = dec_map.get(("MEN-DZ", "MEN-XZ")) or dec_map.get(("MEN-XZ", "MEN-DZ"))
    assert d_xz_dz.machine_relation == MachineRelation.REVIEW, f"Expected REVIEW for Dr. Zhou vs Xin Zhou, got {d_xz_dz.machine_relation}"

    # Dr. Zhou vs Ming Zhou must be REVIEW, never MATCH
    d_mz_dz = dec_map.get(("MEN-DZ", "MEN-MZ")) or dec_map.get(("MEN-MZ", "MEN-DZ"))
    assert d_mz_dz.machine_relation == MachineRelation.REVIEW, f"Expected REVIEW for Dr. Zhou vs Ming Zhou, got {d_mz_dz.machine_relation}"

    # Xin Zhou vs Ming Zhou must be NONMATCH
    d_xz_mz = dec_map.get(("MEN-MZ", "MEN-XZ")) or dec_map.get(("MEN-XZ", "MEN-MZ"))
    assert d_xz_mz.machine_relation == MachineRelation.NONMATCH, f"Expected NONMATCH for Xin Zhou vs Ming Zhou, got {d_xz_mz.machine_relation}"

    # Verify that exactly 3 distinct clusters are formed (zero false merges!)
    clust_ids = {c.cluster_id for c in clusters}
    assert len(clust_ids) == 3, f"Expected 3 distinct clusters, got {len(clust_ids)}"


def test_irregular_transitive_verbs_coreference():
    """
    P1 Test: Heuristic transitive verb object rejection for irregular past tense verbs.
    Verifies that verbs like 'told', 'gave', 'saw', 'taught', 'led' properly reject
    the object noun from being falsely attributed as the subject.
    """
    from benchmarks.eval_extraction import clause_has_target_subject

    # 1. "Bob Smith told Alice Wang. She was appointed director."
    # Target "Alice Wang" is the object of "told", so clause "Bob Smith told Alice Wang" does NOT attribute to Alice Wang.
    assert clause_has_target_subject("Bob Smith told Alice Wang", "Alice Wang") is False

    # 2. "Bob Smith gave Alice Wang an award"
    assert clause_has_target_subject("Bob Smith gave Alice Wang an award", "Alice Wang") is False

    # 3. "Bob Smith saw Alice Wang in Boston"
    assert clause_has_target_subject("Bob Smith saw Alice Wang in Boston", "Alice Wang") is False

    # 4. "Bob Smith taught Alice Wang at MIT"
    assert clause_has_target_subject("Bob Smith taught Alice Wang at MIT", "Alice Wang") is False

    # 5. "Bob Smith led Alice Wang to the podium"
    assert clause_has_target_subject("Bob Smith led Alice Wang to the podium", "Alice Wang") is False

    # 6. Compound subject with coordination "and" IS allowed:
    assert clause_has_target_subject("Bob Smith and Alice Wang founded the company", "Alice Wang") is True


def test_honorific_pipeline_integration_multi_person_anti_merge():
    """
    P0 Official Extraction -> Resolution Pipeline Integration Test:
    'Xin Zhou presented first. Ming Zhou presented next. Dr. Zhou is a dentist.'
    Enforces that:
    1. extract_mentions_and_aliases(target_name='Xin Zhou') extracts Xin Zhou and Dr. Zhou.
    2. resolve_mentions() detects competing surname presence or lack of single-subject profile,
       routing Dr. Zhou vs Xin Zhou to MachineRelation.REVIEW (confidence 0.50).
    3. Exactly 2 distinct clusters are formed; Xin Zhou and Dr. Zhou are NEVER auto-merged.
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from core.resolver import resolve_mentions
    from models.schemas import MachineRelation

    text = "Xin Zhou presented first. Ming Zhou presented next. Dr. Zhou is a dentist."
    src_id = "SRC-PRESENTATION-PAGE"

    extracted_mentions = extract_mentions_and_aliases(
        source_id=src_id,
        raw_text=text,
        target_name="Xin Zhou",
        evidence_id="EVI-01",
        base_char_offset=0,
    )
    # Extracted mentions include Xin Zhou and Dr. Zhou
    assert any(m.raw_name_text == "Xin Zhou" for m in extracted_mentions)
    assert any(m.raw_name_text == "Dr. Zhou" for m in extracted_mentions)

    decisions, clusters = resolve_mentions(extracted_mentions)

    # Assert relation is REVIEW, not MATCH
    for d in decisions:
        assert d.machine_relation != MachineRelation.MATCH, f"Must not MATCH Dr. Zhou into Xin Zhou, got {d.machine_relation}"
        assert d.machine_relation == MachineRelation.REVIEW

    # Assert exactly 2 distinct clusters formed (ZERO false merge)
    assert len(clusters) == 2, f"Expected 2 separate clusters for Xin Zhou and Dr. Zhou, got {len(clusters)}"


def test_mention_universe_mutation_rejects_dangling_id():
    """
    P1 Mutation Test:
    Verifies that a syntactically valid but nonexistent mention ID (e.g. 'MEN-deadbeef1234')
    is strictly rejected by clause_has_target_subject when validated against an independent Mention Universe.
    """
    from benchmarks.eval_extraction import clause_has_target_subject

    independent_universe = {"MEN-111111111111", "MEN-222222222222"}

    # Valid ID present in universe -> passes
    assert clause_has_target_subject(
        clause="Dr. Alice Smith is Dean.",
        target_name="Alice Smith",
        subject_mention_id="MEN-111111111111",
        known_mention_ids=independent_universe,
    ) is True

    # Dangling valid-format ID NOT in universe -> strictly rejected!
    assert clause_has_target_subject(
        clause="Dr. Alice Smith is Dean.",
        target_name="Alice Smith",
        subject_mention_id="MEN-deadbeef1234",
        known_mention_ids=independent_universe,
    ) is False


def test_source_quality_classification():
    """
    P1 Test: Verifies URL-based source quality classification.
    - Official .edu/.gov domains -> CLASS_A
    - Peer-reviewed / scientific databases -> CLASS_B
    - User-generated / code hosting (github) / blogs -> CLASS_C
    - Unknown / unverified -> CLASS_C
    """
    from core.extractors.content_locator import classify_source_quality
    from models.schemas import SourceQualityClass

    assert classify_source_quality("https://medicine.yale.edu/profile/xin_zhou/") == SourceQualityClass.CLASS_A
    assert classify_source_quality("https://cira.yale.edu/people/xin-zhou") == SourceQualityClass.CLASS_A
    assert classify_source_quality("https://nih.gov/health") == SourceQualityClass.CLASS_A
    # PubMed is priority CLASS_B (peer-reviewed / scientific database)
    assert classify_source_quality("https://pubmed.ncbi.nlm.nih.gov/123456/") == SourceQualityClass.CLASS_B
    assert classify_source_quality("https://nature.com/articles/s41586-021-00000") == SourceQualityClass.CLASS_B
    assert classify_source_quality("https://sciencedirect.com/science/article/pii/12345") == SourceQualityClass.CLASS_B
    assert classify_source_quality("https://github.com/xinzhoubiostat") == SourceQualityClass.CLASS_C
    assert classify_source_quality("https://linkedin.com/in/someone") == SourceQualityClass.CLASS_C
    assert classify_source_quality("https://unverified-personal-blog.org/about") == SourceQualityClass.CLASS_C

    # Hostname security: prevents sub-string spoofing and query parameter bypass
    assert classify_source_quality("https://yale.edu.evil.example/profile") == SourceQualityClass.CLASS_C
    assert classify_source_quality("https://evil.example/?next=https://harvard.edu") == SourceQualityClass.CLASS_C
    assert classify_source_quality("https://example.edu.fake.org/person") == SourceQualityClass.CLASS_C


def test_honorific_distant_same_surname_full_source_index_anti_merge():
    """
    P0 Counterexample Test:
    Distant same-surname competition and non-target container rejection:
    1. 'Ming Hao Zhou' (3 tokens) is 600+ chars away from 'Xin Zhou' and 'Dr. Zhou'.
       Verifies that multi-token competitor names trigger veto and force Dr. Zhou to REVIEW.
    2. Generic heading <h1>Annual Conference Program</h1> with Xin Zhou and Dr. Zhou (no competitors):
       Verifies that non-target-bound containers do NOT trigger auto-merge and stay in REVIEW.
    3. Target-bound heading <h1>Xin Zhou, Ph.D.</h1> on profile page (no competitors):
       Verifies that legitimate target-bound container enables corroborated auto-merge.
    """
    from core.resolver import resolve_mentions
    from models.schemas import EntityMention, MachineRelation

    # 1. Distant three-token competitor 'Ming Hao Zhou' 600+ chars away
    header = "<h1>Xin Zhou</h1><p>Biography: Dr. Zhou is an associate research scientist at Yale University.</p>"
    padding = " " + ("Section paragraph discussing global biomedical methods and experimental observations. " * 8)
    footer = "<p>Keynote lecture was presented by Ming Hao Zhou from Beijing institute on statistics.</p>"
    full_html = header + padding + footer
    src_id = "SRC-DISTANT-ZHOU-PAGE"

    m1 = EntityMention(
        mention_id="MEN-XZ-01",
        raw_name_text="Xin Zhou",
        source_id=src_id,
        context_snippet=full_html[:150],
        evidence_id="EVI-01",
        mention_key="key-xz-01",
        char_start=4,
        char_end=12,
    )
    m2 = EntityMention(
        mention_id="MEN-DZ-01",
        raw_name_text="Dr. Zhou",
        source_id=src_id,
        context_snippet=full_html[20:170],
        evidence_id="EVI-01",
        mention_key="key-dz-01",
        char_start=32,
        char_end=40,
    )

    assert "Ming Hao Zhou" not in m1.context_snippet
    assert "Ming Hao Zhou" not in m2.context_snippet

    import re
    raw_names = re.findall(r"\b([A-Z][a-zA-Z\.\-]+(?:\s+[A-Z][a-zA-Z\.\-]+)+)\b", full_html)
    source_names_by_surname = {src_id: {}}
    for full_n in raw_names:
        toks = full_n.strip().split()
        if len(toks) >= 2:
            sname = toks[-1].lower().rstrip(".,")
            source_names_by_surname[src_id].setdefault(sname, set()).add(full_n.strip().lower())

    assert "xin zhou" in source_names_by_surname[src_id]["zhou"]
    assert "ming hao zhou" in source_names_by_surname[src_id]["zhou"]

    decisions, clusters = resolve_mentions(
        [m1, m2],
        source_names_by_surname=source_names_by_surname,
        source_profile_containers={src_id: {"h1_text": "Xin Zhou", "has_bio": True, "url": "https://yale.edu/profile/xin-zhou"}},
    )
    dec_map = {(d.source_mention_id, d.target_mention_id): d for d in decisions}
    d_xz_dz = dec_map.get(("MEN-DZ-01", "MEN-XZ-01")) or dec_map.get(("MEN-XZ-01", "MEN-DZ-01"))
    assert d_xz_dz.machine_relation == MachineRelation.REVIEW
    assert "competing same-surname entities" in d_xz_dz.explanation
    assert len(clusters) == 2

    # 2. Generic non-target heading <h1>Annual Conference Program</h1> with no competitors
    src_conf = "SRC-CONF-PAGE"
    conf_html = "<h1>Annual Conference Program</h1><p>Xin Zhou gave an opening remark. In the afternoon session, Dr. Zhou answered questions.</p>"
    m_conf1 = EntityMention(
        mention_id="MEN-CONF-01",
        raw_name_text="Xin Zhou",
        source_id=src_conf,
        context_snippet=conf_html,
        evidence_id="EVI-CONF-01",
        mention_key="key-conf-01",
        char_start=40,
        char_end=48,
    )
    m_conf2 = EntityMention(
        mention_id="MEN-CONF-02",
        raw_name_text="Dr. Zhou",
        source_id=src_conf,
        context_snippet=conf_html,
        evidence_id="EVI-CONF-01",
        mention_key="key-conf-02",
        char_start=95,
        char_end=103,
    )
    decisions_conf, clusters_conf = resolve_mentions(
        [m_conf1, m_conf2],
        source_names_by_surname={src_conf: {"zhou": {"xin zhou"}}},
        source_profile_containers={src_conf: {"h1_text": "Annual Conference Program", "has_bio": False, "url": "https://conf.org/program"}},
    )
    dec_map_conf = {(d.source_mention_id, d.target_mention_id): d for d in decisions_conf}
    d_conf = dec_map_conf.get(("MEN-CONF-02", "MEN-CONF-01")) or dec_map_conf.get(("MEN-CONF-01", "MEN-CONF-02"))
    assert d_conf.machine_relation == MachineRelation.REVIEW
    assert len(clusters_conf) == 2

    # 3. Valid target-bound container <h1>Xin Zhou, Ph.D.</h1> on profile page
    src_prof = "SRC-PROF-PAGE"
    prof_html = "<h1>Xin Zhou, Ph.D.</h1><p>Biography: Dr. Zhou is Assistant Professor of Biostatistics at Yale.</p>"
    m_prof1 = EntityMention(
        mention_id="MEN-PROF-01",
        raw_name_text="Xin Zhou",
        source_id=src_prof,
        context_snippet=prof_html,
        evidence_id="EVI-PROF-01",
        mention_key="key-prof-01",
        char_start=4,
        char_end=12,
    )
    m_prof2 = EntityMention(
        mention_id="MEN-PROF-02",
        raw_name_text="Dr. Zhou",
        source_id=src_prof,
        context_snippet=prof_html,
        evidence_id="EVI-PROF-01",
        mention_key="key-prof-02",
        char_start=35,
        char_end=43,
    )
    decisions_prof, clusters_prof = resolve_mentions(
        [m_prof1, m_prof2],
        source_names_by_surname={src_prof: {"zhou": {"xin zhou"}}},
        source_profile_containers={src_prof: {"h1_text": "Xin Zhou, Ph.D.", "has_bio": True, "url": "https://yale.edu/people/xin-zhou"}},
    )
    dec_map_prof = {(d.source_mention_id, d.target_mention_id): d for d in decisions_prof}
    d_prof = dec_map_prof.get(("MEN-PROF-02", "MEN-PROF-01")) or dec_map_prof.get(("MEN-PROF-01", "MEN-PROF-02"))
    assert d_prof.machine_relation == MachineRelation.MATCH
    assert len(clusters_prof) == 1


def test_multi_subject_routing_joint_appointment_isolation():
    """
    P1 Test: Multi-subject mention routing using the shared production route_and_extract_claims function.
    In an evidence containing both Alice Smith (Stanford Professor) and Bob Jones (MIT Dean):
    1. Mentions are clustered into separate candidates (CAND-Alice and CAND-Bob).
    2. route_and_extract_claims() extracts claims with strict subject mention and candidate attribution.
    3. Alice strictly obtains holds_position: Professor and affiliated_with: Stanford (no Dean, no MIT).
    4. Bob strictly obtains holds_position: Dean and affiliated_with: MIT (no Professor, no Stanford).
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from core.resolver import resolve_mentions
    from core.run_profile import route_and_extract_claims
    from models.schemas import CandidateEntity, Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from typing import Dict, List

    text = "Alice Smith is a Professor of Computer Science at Stanford University. Meanwhile, Bob Jones serves as Dean of Engineering at Massachusetts Institute of Technology."
    ev = Evidence(
        evidence_id="EVI-MULTI-01",
        source_id="SRC-MULTI-01",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )

    m_alice = extract_mentions_and_aliases(
        source_id=ev.source_id,
        raw_text=text,
        target_name="Alice Smith",
        evidence_id=ev.evidence_id,
    )
    m_bob = extract_mentions_and_aliases(
        source_id=ev.source_id,
        raw_text=text,
        target_name="Bob Jones",
        evidence_id=ev.evidence_id,
    )
    all_mentions = m_alice + m_bob
    assert len(all_mentions) >= 2

    # Attach inferred organizations from evidence excerpt (consistent with Phase 1 production flow)
    from core.resolver import extract_organizations
    orgs = extract_organizations(ev.verbatim_excerpt)
    for m in all_mentions:
        m.inferred_affiliations = list(orgs)

    # Phase 2: Entity Resolution
    matches, clusters = resolve_mentions(all_mentions)
    assert len(clusters) == 2

    candidates: List[CandidateEntity] = []
    for cluster in clusters:
        cand_id_suffix = cluster.cluster_id.replace("CLUST-", "")
        candidates.append(CandidateEntity(
            candidate_entity_id=f"CAND-{cand_id_suffix}",
            proposed_cluster_id=cluster.cluster_id,
            mention_ids=cluster.mention_ids,
        ))

    # Invoke shared production Phase 3 routing layer
    extracted_claims = route_and_extract_claims(
        evidence_list=[ev],
        mentions_list=all_mentions,
        candidates=candidates,
        default_target_name="Alice Smith",
    )

    assert len(extracted_claims) >= 2

    alice_claims = [c for c in extracted_claims if c.subject_mention_id in {m.mention_id for m in m_alice}]
    bob_claims = [c for c in extracted_claims if c.subject_mention_id in {m.mention_id for m in m_bob}]

    assert len(alice_claims) > 0
    assert len(bob_claims) > 0
    assert len(alice_claims) + len(bob_claims) == len(extracted_claims)

    # Strict fact-level attribution assertions
    alice_positions = {c.object_raw.lower() for c in alice_claims if c.predicate == "holds_position"}
    alice_affiliations = {c.object_raw.lower() for c in alice_claims if c.predicate == "affiliated_with"}
    assert any("professor" in p for p in alice_positions)
    assert any("stanford" in a for a in alice_affiliations)
    assert not any("dean" in p for p in alice_positions)
    assert not any("massachusetts" in a or "mit" in a for a in alice_affiliations)

    bob_positions = {c.object_raw.lower() for c in bob_claims if c.predicate == "holds_position"}
    bob_affiliations = {c.object_raw.lower() for c in bob_claims if c.predicate == "affiliated_with"}
    assert any("dean" in p for p in bob_positions)
    assert any("massachusetts" in a or "mit" in a for a in bob_affiliations)
    assert not any("professor" in p for p in bob_positions)
    assert not any("stanford" in a for a in bob_affiliations)


def test_multi_subject_run_pipeline_warc_e2e(tmp_path):
    """
    P1 Test: End-to-end multi-subject investigation using official run_pipeline() entry point
    against a minimal WARC archive.
    Verifies that running run_pipeline() for Alice Smith extracts only Stanford/Professor claims into bundle,
    and running run_pipeline() for Bob Jones extracts only MIT/Dean claims into bundle.
    Validates that both bundles satisfy validate_bundle().
    """
    from core.run_profile import run_pipeline
    from scripts.validate_dossier import validate_bundle

    html_content = (
        "<html><head><title>Faculty Directory</title></head><body>"
        "<h1>Faculty Directory</h1>"
        "<div class='faculty-card'><p>Alice Smith is a Professor of Computer Science at Stanford.</p></div>"
        "<div class='faculty-card'><p>Bob Jones serves as Dean of Engineering at MIT.</p></div>"
        "</body></html>"
    )
    http_payload = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html_content}".encode("utf-8")
    content_len = len(http_payload)
    rec_id = "urn:uuid:11111111-2222-3333-4444-555555555555"
    target_url = "https://example.edu/faculty"

    warc_bytes = (
        f"WARC/1.0\r\n"
        f"WARC-Type: response\r\n"
        f"WARC-Target-URI: {target_url}\r\n"
        f"WARC-Date: 2026-09-15T00:00:00Z\r\n"
        f"WARC-Record-ID: <{rec_id}>\r\n"
        f"Content-Type: application/http; msgtype=response\r\n"
        f"Content-Length: {content_len}\r\n"
        f"\r\n"
    ).encode("utf-8") + http_payload + b"\r\n\r\n"

    warc_file = tmp_path / "minimal_multi.warc"
    with open(warc_file, "wb") as f:
        f.write(warc_bytes)

    # 1. Run pipeline for Alice Smith
    out_alice = tmp_path / "bundle_alice"
    bundle_alice = run_pipeline(
        target_name="Alice Smith",
        hints=["Stanford"],
        output_dir=out_alice,
        offline_corpus=warc_file,
    )
    val_alice = validate_bundle(bundle_alice, warc_path=warc_file)
    assert val_alice["is_valid"] is True
    assert val_alice["layers"]["structural_valid"] is True
    assert val_alice["layers"]["warc_record_ids_present"] is True

    # Read Alice's claims
    with open(bundle_alice / "claims.jsonl", "r", encoding="utf-8") as f:
        alice_claims = [json.loads(line) for line in f if line.strip()]
    assert len(alice_claims) >= 1
    alice_objs = {c["object_raw"].lower() for c in alice_claims}
    assert any("stanford" in o or "professor" in o for o in alice_objs)
    assert not any("dean" in o or "mit" in o for o in alice_objs)

    # 2. Run pipeline for Bob Jones
    out_bob = tmp_path / "bundle_bob"
    bundle_bob = run_pipeline(
        target_name="Bob Jones",
        hints=["MIT"],
        output_dir=out_bob,
        offline_corpus=warc_file,
    )
    val_bob = validate_bundle(bundle_bob, warc_path=warc_file)
    assert val_bob["is_valid"] is True
    assert val_bob["layers"]["structural_valid"] is True
    assert val_bob["layers"]["warc_record_ids_present"] is True

    # Read Bob's claims
    with open(bundle_bob / "claims.jsonl", "r", encoding="utf-8") as f:
        bob_claims = [json.loads(line) for line in f if line.strip()]
    assert len(bob_claims) >= 1
    bob_objs = {c["object_raw"].lower() for c in bob_claims}
    assert any("mit" in o or "dean" in o for o in bob_objs)
    assert not any("professor" in o or "stanford" in o for o in bob_objs)


def test_honorific_large_offset_distant_antecedent_anti_merge():
    """
    P0 Counterexample Test:
    Coordinate system fix for large-offset antecedents:
    [1260 chars prefix] Xin Zhou ended his talk.
    Bob Smith responded; Dr. Zhou is a dentist.
    Verifies that when names appear late in the evidence text, coordinates are properly sliced
    from the authentic evidence text rather than truncated context snippets,
    blocking false auto-merge across sentence/third-party boundaries and forcing REVIEW.
    """
    from core.resolver import resolve_mentions
    from models.schemas import EntityMention, MachineRelation

    prefix = "A" * 1260 + " "
    sentence1 = "Xin Zhou ended his talk."
    sentence2 = "\nBob Smith responded; Dr. Zhou is a dentist."
    full_text = prefix + sentence1 + sentence2
    src_id = "SRC-LARGE-OFFSET"
    ev_id = "EVI-LARGE-OFFSET"

    xz_start = full_text.index("Xin Zhou")
    xz_end = xz_start + len("Xin Zhou")
    dz_start = full_text.index("Dr. Zhou")
    dz_end = dz_start + len("Dr. Zhou")

    m1 = EntityMention(
        mention_id="MEN-XZ-L",
        raw_name_text="Xin Zhou",
        source_id=src_id,
        context_snippet=full_text[max(0, xz_start - 150):xz_end + 150],
        evidence_id=ev_id,
        mention_key="key-xz-l",
        char_start=xz_start,
        char_end=xz_end,
    )
    m2 = EntityMention(
        mention_id="MEN-DZ-L",
        raw_name_text="Dr. Zhou",
        source_id=src_id,
        context_snippet=full_text[max(0, dz_start - 150):dz_end + 150],
        evidence_id=ev_id,
        mention_key="key-dz-l",
        char_start=dz_start,
        char_end=dz_end,
    )

    evidence_text_by_id = {ev_id: full_text}
    decisions, clusters = resolve_mentions(
        [m1, m2],
        source_names_by_surname={src_id: {"zhou": {"xin zhou"}}},
        source_profile_containers={src_id: {"h1_text": "Generic Page", "has_bio": False, "url": "https://example.com"}},
        evidence_text_by_id=evidence_text_by_id,
    )

    dec_map = {(d.source_mention_id, d.target_mention_id): d for d in decisions}
    d = dec_map.get(("MEN-DZ-L", "MEN-XZ-L")) or dec_map.get(("MEN-XZ-L", "MEN-DZ-L"))
    assert d.machine_relation == MachineRelation.REVIEW
    assert len(clusters) == 2, f"Expected 2 clusters to prevent false merge, got {len(clusters)}"


def test_repeated_name_clause_level_mention_anchoring_and_validation():
    """
    P0 Counterexample Test:
    Repeated name mention anchoring:
    Alice Smith was Dean at MIT. Later Alice Smith is Professor at Stanford University.
    Verifies:
    1. Dean at MIT anchors to the first Alice Smith mention.
    2. Professor at Stanford anchors to the second Alice Smith mention.
    3. Neither claim misattributes its support clause to an out-of-span mention.
    4. Validate subject span containment within support clause.
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from core.resolver import resolve_mentions
    from core.run_profile import route_and_extract_claims
    from models.schemas import CandidateEntity, Evidence, EvidenceLocator, LocatorType, SourceQualityClass

    text = "Alice Smith was Dean at MIT. Later Alice Smith is Professor at Stanford University."
    ev = Evidence(
        evidence_id="EVI-REP-01",
        source_id="SRC-REP-01",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )

    mentions = extract_mentions_and_aliases(
        source_id=ev.source_id,
        raw_text=text,
        target_name="Alice Smith",
        evidence_id=ev.evidence_id,
    )
    assert len(mentions) == 2
    m1, m2 = sorted(mentions, key=lambda m: m.char_start)

    from core.resolver import extract_organizations
    orgs = extract_organizations(ev.verbatim_excerpt)
    for m in mentions:
        m.inferred_affiliations = list(orgs)

    matches, clusters = resolve_mentions(mentions, evidence_text_by_id={ev.evidence_id: text})
    assert len(clusters) == 1

    candidates = [
        CandidateEntity(
            candidate_entity_id="CAND-ALICE",
            proposed_cluster_id=clusters[0].cluster_id,
            mention_ids=[m.mention_id for m in mentions],
        )
    ]

    claims = route_and_extract_claims(
        evidence_list=[ev],
        mentions_list=mentions,
        candidates=candidates,
        default_target_name="Alice Smith",
    )

    dean_claims = [c for c in claims if "dean" in c.object_raw.lower()]
    prof_claims = [c for c in claims if "professor" in c.object_raw.lower()]

    assert len(dean_claims) == 1
    assert len(prof_claims) == 1

    # First sentence mention anchors Dean claim
    assert dean_claims[0].subject_mention_id == m1.mention_id
    assert dean_claims[0].support_clauses[0].subject_mention_id == m1.mention_id
    assert m1.char_start >= dean_claims[0].support_clauses[0].clause_span_start
    assert m1.char_end <= dean_claims[0].support_clauses[0].clause_span_end

    # Second sentence mention anchors Professor claim
    assert prof_claims[0].subject_mention_id == m2.mention_id
    assert prof_claims[0].support_clauses[0].subject_mention_id == m2.mention_id
    assert m2.char_start >= prof_claims[0].support_clauses[0].clause_span_start
    assert m2.char_end <= prof_claims[0].support_clauses[0].clause_span_end


def test_untrusted_class_c_profile_page_rejects_auto_merge():
    """
    P1 Counterexample Test:
    Untrusted domain (https://untrusted.example/profile/xin) with Class C quality
    must NOT trigger auto-merge under Proof A, and must stay in REVIEW.
    """
    from core.resolver import resolve_mentions
    from models.schemas import EntityMention, MachineRelation, SourceQualityClass

    html = "<h1>Xin Zhou</h1><p>Biography: Dr. Zhou is a researcher.</p>"
    src_id = "SRC-UNTRUSTED"
    ev_id = "EVI-UNTRUSTED"

    m1 = EntityMention(
        mention_id="MEN-XZ-U",
        raw_name_text="Xin Zhou",
        source_id=src_id,
        context_snippet=html,
        evidence_id=ev_id,
        mention_key="key-xz-u",
        char_start=4,
        char_end=12,
    )
    m2 = EntityMention(
        mention_id="MEN-DZ-U",
        raw_name_text="Dr. Zhou",
        source_id=src_id,
        context_snippet=html,
        evidence_id=ev_id,
        mention_key="key-dz-u",
        char_start=32,
        char_end=40,
    )

    decisions, clusters = resolve_mentions(
        [m1, m2],
        source_names_by_surname={src_id: {"zhou": {"xin zhou"}}},
        source_profile_containers={
            src_id: {
                "h1_text": "Xin Zhou",
                "has_bio": True,
                "url": "https://untrusted.example/profile/xin",
                "source_quality_class": SourceQualityClass.CLASS_C,
            }
        },
        evidence_text_by_id={ev_id: html},
    )

    dec_map = {(d.source_mention_id, d.target_mention_id): d for d in decisions}
    d = dec_map.get(("MEN-DZ-U", "MEN-XZ-U")) or dec_map.get(("MEN-XZ-U", "MEN-DZ-U"))
    assert d.machine_relation == MachineRelation.REVIEW
    assert len(clusters) == 2


def test_single_clause_multi_subject_isolation():
    """
    P0 Regression Test:
    In a single compound clause with multiple subjects:
    "Alice Smith is Professor at Stanford University while Bob Jones is Dean at Massachusetts Institute of Technology."
    Claims must be partitioned strictly to their respective subjects and predicate spans without cross-talk.
    """
    from datetime import datetime, timezone
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass, EntityMention

    text = "Alice Smith is Professor at Stanford University while Bob Jones is Dean at Massachusetts Institute of Technology."
    ev = Evidence(
        evidence_id="EVI-MULTI-1",
        source_id="SRC-MULTI-1",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )

    m_alice = EntityMention(
        mention_id="MEN-ALICE-1",
        raw_name_text="Alice Smith",
        source_id="SRC-MULTI-1",
        context_snippet=text,
        evidence_id="EVI-MULTI-1",
        mention_key="key-alice-1",
        char_start=0,
        char_end=11,
    )
    m_bob = EntityMention(
        mention_id="MEN-BOB-1",
        raw_name_text="Bob Jones",
        source_id="SRC-MULTI-1",
        context_snippet=text,
        evidence_id="EVI-MULTI-1",
        mention_key="key-bob-1",
        char_start=text.index("Bob Jones"),
        char_end=text.index("Bob Jones") + len("Bob Jones"),
    )

    claims = extract_claims_from_evidence(
        evidence=ev,
        candidate_entity_id=None,
        subject_mention_id=None,
        target_name=None,
        evidence_mentions=[m_alice, m_bob],
        mention_to_cand_id={"MEN-ALICE-1": "CAND-ALICE", "MEN-BOB-1": "CAND-BOB"},
    )

    alice_claims = [c for c in claims if c.candidate_entity_id == "CAND-ALICE"]
    bob_claims = [c for c in claims if c.candidate_entity_id == "CAND-BOB"]

    # Alice must have Professor and Stanford, and MUST NOT have Dean or MIT
    assert any(c.predicate == "holds_position" and "Professor" in c.object_raw for c in alice_claims)
    assert any(c.predicate == "affiliated_with" and "Stanford" in c.object_raw for c in alice_claims)
    assert not any("Dean" in c.object_raw for c in alice_claims)
    assert not any("Massachusetts" in c.object_raw or "MIT" in c.object_raw for c in alice_claims)

    # Bob must have Dean and MIT, and MUST NOT have Professor or Stanford
    assert any(c.predicate == "holds_position" and "Dean" in c.object_raw for c in bob_claims)
    assert any(c.predicate == "affiliated_with" and "Massachusetts Institute of Technology" in c.object_raw for c in bob_claims)
    assert not any("Professor" in c.object_raw for c in bob_claims)
    assert not any("Stanford" in c.object_raw for c in bob_claims)

    # Validate relation spans
    for c in claims:
        sup = c.support_clauses[0]
        assert sup.relation_span_start is not None and sup.relation_span_end is not None
        assert sup.clause_span_start <= sup.relation_span_start < sup.relation_span_end <= sup.clause_span_end
        rel_text = text[sup.relation_span_start:sup.relation_span_end].lower()
        if c.candidate_entity_id == "CAND-ALICE":
            assert sup.relation_span_start <= m_alice.char_start and m_alice.char_end <= sup.relation_span_end
            assert "stanford" in rel_text or "professor" in rel_text
            assert "bob" not in rel_text
        else:
            assert sup.relation_span_start <= m_bob.char_start and m_bob.char_end <= sup.relation_span_end
            assert "dean" in rel_text or "massachusetts" in rel_text
            assert "alice" not in rel_text


def test_pronoun_antecedent_interrupted_by_intervening_person():
    """
    P0 Regression Test:
    "Alice Smith is Professor at Stanford University. Bob Jones arrived. He is Dean at Massachusetts Institute of Technology."
    The intervening person 'Bob Jones' breaks Alice's antecedent chain; 'He is Dean...' must NOT attribute to Alice!
    """
    from datetime import datetime, timezone
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass

    text = "Alice Smith is Professor at Stanford University. Bob Jones arrived. He is Dean at Massachusetts Institute of Technology."
    ev = Evidence(
        evidence_id="EVI-INTERRUPT-1",
        source_id="SRC-INTERRUPT-1",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )

    alice_claims = extract_claims_from_evidence(
        evidence=ev,
        candidate_entity_id="CAND-ALICE",
        target_name="Alice Smith",
    )

    assert any(c.predicate == "holds_position" and "Professor" in c.object_raw for c in alice_claims)
    assert any(c.predicate == "affiliated_with" and "Stanford" in c.object_raw for c in alice_claims)
    # Dean at MIT must NOT attach to Alice!
    assert not any("Dean" in c.object_raw for c in alice_claims)
    assert not any("Massachusetts" in c.object_raw for c in alice_claims)


def test_pronoun_antecedent_interrupted_by_neutral_clause():
    """
    P0 Regression Test:
    "Alice Smith is Professor at Stanford University. The symposium concluded at five in the evening. He is Dean at Massachusetts Institute of Technology."
    A neutral non-target sentence breaks the antecedent chain; 'He is Dean...' must NOT attribute to Alice!
    """
    from datetime import datetime, timezone
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass

    text = "Alice Smith is Professor at Stanford University. The symposium concluded at five in the evening. He is Dean at Massachusetts Institute of Technology."
    ev = Evidence(
        evidence_id="EVI-NEUTRAL-1",
        source_id="SRC-NEUTRAL-1",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )

    alice_claims = extract_claims_from_evidence(
        evidence=ev,
        candidate_entity_id="CAND-ALICE",
        target_name="Alice Smith",
    )

    assert any(c.predicate == "holds_position" and "Professor" in c.object_raw for c in alice_claims)
    assert any(c.predicate == "affiliated_with" and "Stanford" in c.object_raw for c in alice_claims)
    assert not any("Dean" in c.object_raw for c in alice_claims)
    assert not any("Massachusetts" in c.object_raw for c in alice_claims)


def test_untrusted_source_quality_fail_closed_without_metadata():
    """
    P1 Regression Test:
    When source_profile_containers lacks source_quality_class, Proof A must classify from URL
    and fail closed on untrusted domains (e.g. blogspot, unknown domains) -> must NOT auto-merge!
    """
    from core.resolver import resolve_mentions
    from models.schemas import EntityMention, MachineRelation

    html = "<h1>Xin Zhou</h1><p>Biography: Dr. Zhou is a researcher.</p>"
    src_id = "SRC-NO-META"
    ev_id = "EVI-NO-META"

    m1 = EntityMention(
        mention_id="MEN-XZ-NM",
        raw_name_text="Xin Zhou",
        source_id=src_id,
        context_snippet=html,
        evidence_id=ev_id,
        mention_key="key-xz-nm",
        char_start=4,
        char_end=12,
    )
    m2 = EntityMention(
        mention_id="MEN-DZ-NM",
        raw_name_text="Dr. Zhou",
        source_id=src_id,
        context_snippet=html,
        evidence_id=ev_id,
        mention_key="key-dz-nm",
        char_start=32,
        char_end=40,
    )

    decisions, clusters = resolve_mentions(
        [m1, m2],
        source_names_by_surname={src_id: {"zhou": {"xin zhou"}}},
        source_profile_containers={
            src_id: {
                "h1_text": "Xin Zhou",
                "has_bio": True,
                "url": "http://sketchy-blog.info/profile",
                # Note: source_quality_class intentionally omitted!
            }
        },
        evidence_text_by_id={ev_id: html},
    )

    dec_map = {(d.source_mention_id, d.target_mention_id): d for d in decisions}
    d = dec_map.get(("MEN-DZ-NM", "MEN-XZ-NM")) or dec_map.get(("MEN-XZ-NM", "MEN-DZ-NM"))
    assert d.machine_relation == MachineRelation.REVIEW
    assert len(clusters) == 2


def test_validator_rejects_mismatched_relation_span_and_phantom_object(tmp_path):
    """
    P1 Regression Test:
    scripts/validate_dossier.py must reject:
    1. A claim where object key tokens are missing from verbatim_clause / relation_span.
    2. A claim where relation_span does not enclose the subject mention.
    """
    import json
    from datetime import date, datetime, timezone
    from scripts.validate_dossier import validate_bundle

    ev_text = "Alice Smith is a Professor at Stanford University."
    b_dir = tmp_path / "bundle"
    b_dir.mkdir()

    # Create valid base files
    manifest = {
        "schema_version": "1.0",
        "bundle_id": "BND-TEST",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "item_counts": {
            "sources": 1,
            "evidence": 1,
            "mentions": 1,
            "candidates": 1,
            "matches": 0,
            "clusters": 1,
            "claims": 1,
        },
        "file_hashes": {},
    }
    (b_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    src = {
        "source_id": "SRC-1",
        "url": "https://stanford.edu/profile",
        "publisher": "stanford.edu",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "content_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "http_status": 200,
        "warc_record_id": None,
    }
    (b_dir / "sources.jsonl").write_text(json.dumps(src) + "\n", encoding="utf-8")

    ev = {
        "evidence_id": "EVI-1",
        "source_id": "SRC-1",
        "verbatim_excerpt": ev_text,
        "locator": {"locator_type": "css", "selector_or_page": "body"},
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_quality_class": "class_a",
    }
    (b_dir / "evidence.jsonl").write_text(json.dumps(ev) + "\n", encoding="utf-8")

    men = {
        "mention_id": "MEN-1",
        "raw_name_text": "Alice Smith",
        "source_id": "SRC-1",
        "context_snippet": ev_text,
        "evidence_id": "EVI-1",
        "mention_key": "key-1",
        "char_start": 0,
        "char_end": 11,
    }
    (b_dir / "mentions.jsonl").write_text(json.dumps(men) + "\n", encoding="utf-8")

    cand = {
        "candidate_entity_id": "CAND-1",
        "proposed_cluster_id": "CLUST-1",
        "mention_ids": ["MEN-1"],
    }
    (b_dir / "candidates.jsonl").write_text(json.dumps(cand) + "\n", encoding="utf-8")

    clust = {
        "cluster_id": "CLUST-1",
        "mention_ids": ["MEN-1"],
        "cohesion_score": 1.0,
    }
    (b_dir / "clusters.jsonl").write_text(json.dumps(clust) + "\n", encoding="utf-8")
    (b_dir / "matches.jsonl").write_text("", encoding="utf-8")

    dossier = {
        "dossier_id": "DOS-1",
        "candidate_entity_id": "CAND-1",
        "statements": [],
        "ambiguous_candidates": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (b_dir / "dossier.json").write_text(json.dumps(dossier), encoding="utf-8")
    (b_dir / "dossier.md").write_text("# Dossier\n", encoding="utf-8")

    # Case 1: Phantom object in claim not present in verbatim text
    bad_claim_phantom = {
        "claim_id": "CLM-BAD-1",
        "candidate_entity_id": "CAND-1",
        "subject_mention_id": "MEN-1",
        "predicate": "holds_position",
        "object_raw": "Astronaut",  # NOT in text!
        "polarity": "affirmative",
        "temporal_status": "current",
        "adjudication_status": "unresolved",
        "as_of": date(2025, 1, 1).isoformat(),
        "extraction_confidence": 0.95,
        "evidence_ids": ["EVI-1"],
        "support_clauses": [{
            "evidence_id": "EVI-1",
            "subject_mention_id": "MEN-1",
            "clause_span_start": 0,
            "clause_span_end": len(ev_text),
            "verbatim_clause": ev_text,
            "relation_span_start": 0,
            "relation_span_end": len(ev_text),
        }],
    }
    (b_dir / "claims.jsonl").write_text(json.dumps(bad_claim_phantom) + "\n", encoding="utf-8")
    res1 = validate_bundle(b_dir)
    assert res1["is_valid"] is False
    assert any("has no substantive tokens" in err for err in res1["errors"])

    # Case 2: Relation span excludes subject mention
    bad_claim_exclude_subj = {
        "claim_id": "CLM-BAD-2",
        "candidate_entity_id": "CAND-1",
        "subject_mention_id": "MEN-1",
        "predicate": "holds_position",
        "object_raw": "Professor",
        "polarity": "affirmative",
        "temporal_status": "current",
        "adjudication_status": "unresolved",
        "as_of": date(2025, 1, 1).isoformat(),
        "extraction_confidence": 0.95,
        "evidence_ids": ["EVI-1"],
        "support_clauses": [{
            "evidence_id": "EVI-1",
            "subject_mention_id": "MEN-1",
            "clause_span_start": 0,
            "clause_span_end": len(ev_text),
            "verbatim_clause": ev_text,
            "relation_span_start": 15,  # Excludes Alice Smith [0, 11]!
            "relation_span_end": 35,
        }],
    }
    (b_dir / "claims.jsonl").write_text(json.dumps(bad_claim_exclude_subj) + "\n", encoding="utf-8")
    res2 = validate_bundle(b_dir)
    assert res2["is_valid"] is False
    assert any("does not fall within relation span" in err for err in res2["errors"])

    # Case 3: Relation span encloses subject mention but excludes object tokens
    bad_claim_exclude_obj = {
        "claim_id": "CLM-BAD-3",
        "candidate_entity_id": "CAND-1",
        "subject_mention_id": "MEN-1",
        "predicate": "holds_position",
        "object_raw": "Professor",
        "polarity": "affirmative",
        "temporal_status": "current",
        "adjudication_status": "unresolved",
        "as_of": date(2025, 1, 1).isoformat(),
        "extraction_confidence": 0.95,
        "evidence_ids": ["EVI-1"],
        "support_clauses": [{
            "evidence_id": "EVI-1",
            "subject_mention_id": "MEN-1",
            "clause_span_start": 0,
            "clause_span_end": len(ev_text),
            "verbatim_clause": ev_text,
            "relation_span_start": 0,  # Encloses Alice Smith [0, 11], but excludes Professor [15, 24]!
            "relation_span_end": 14,
        }],
    }
    (b_dir / "claims.jsonl").write_text(json.dumps(bad_claim_exclude_obj) + "\n", encoding="utf-8")
    res3 = validate_bundle(b_dir)
    assert res3["is_valid"] is False
    assert any("Relation span object violation" in err for err in res3["errors"])


def test_appositive_multi_subject_isolation():
    """
    P0 Counterexample Test:
    Appositive structure multi-subject isolation:
    "Alice Smith, Professor at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    Verifies:
    1. Alice Smith strictly receives holds_position: Professor and affiliated_with: Stanford University.
    2. Bob Jones strictly receives holds_position: Dean and affiliated_with: Massachusetts Institute of Technology.
    3. Neither entity receives the other's titles or institutional affiliations (zero cross-talk).
    4. Both support clause spans properly enclose their respective subject mentions.
    """
    from datetime import datetime, timezone
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass, EntityMention

    text = "Alice Smith, Professor at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    ev = Evidence(
        evidence_id="EVI-MULTI-APPOS",
        source_id="SRC-MULTI-APPOS",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    m_alice = EntityMention(
        mention_id="MEN-ALICE",
        raw_name_text="Alice Smith",
        source_id="SRC-MULTI-APPOS",
        context_snippet=text,
        evidence_id="EVI-MULTI-APPOS",
        mention_key="key-alice",
        char_start=0,
        char_end=11,
    )
    bob_start = text.index("Bob Jones")
    bob_end = bob_start + len("Bob Jones")
    m_bob = EntityMention(
        mention_id="MEN-BOB",
        raw_name_text="Bob Jones",
        source_id="SRC-MULTI-APPOS",
        context_snippet=text,
        evidence_id="EVI-MULTI-APPOS",
        mention_key="key-bob",
        char_start=bob_start,
        char_end=bob_end,
    )

    claims = extract_claims_from_evidence(
        evidence=ev,
        evidence_mentions=[m_alice, m_bob],
        mention_to_cand_id={"MEN-ALICE": "CAND-ALICE", "MEN-BOB": "CAND-BOB"},
    )

    alice_claims = [c for c in claims if c.subject_mention_id == "MEN-ALICE"]
    bob_claims = [c for c in claims if c.subject_mention_id == "MEN-BOB"]

    assert len(alice_claims) >= 2
    assert len(bob_claims) >= 2

    alice_positions = {c.object_raw.lower() for c in alice_claims if c.predicate == "holds_position"}
    alice_affiliations = {c.object_raw.lower() for c in alice_claims if c.predicate == "affiliated_with"}
    bob_positions = {c.object_raw.lower() for c in bob_claims if c.predicate == "holds_position"}
    bob_affiliations = {c.object_raw.lower() for c in bob_claims if c.predicate == "affiliated_with"}

    # Strict non-leakage assertions
    assert "professor" in alice_positions
    assert any("stanford" in a for a in alice_affiliations)
    assert not any("dean" in p for p in alice_positions)
    assert not any("technology" in a or "mit" in a for a in alice_affiliations)

    assert "dean" in bob_positions
    assert any("technology" in a or "massachusetts" in a for a in bob_affiliations)
    assert not any("professor" in p for p in bob_positions)
    assert not any("stanford" in a for a in bob_affiliations)

    # Support clause span containment checks
    for c in alice_claims:
        sup = c.support_clauses[0]
        assert sup.clause_span_start <= m_alice.char_start and m_alice.char_end <= sup.clause_span_end
    for c in bob_claims:
        sup = c.support_clauses[0]
        assert sup.clause_span_start <= m_bob.char_start and m_bob.char_end <= sup.clause_span_end


def test_validator_rejects_generic_category_word_bypass(tmp_path):
    """
    P0 Counterexample Test:
    Validator generic category word escape:
    Verifies that validate_bundle() rejects false claims when evidence only matches
    generic category words ("University", "Professor") rather than distinctive tokens:
    1. Claim: Harvard University vs Evidence: Stanford University -> REJECTED.
    2. Claim: Professor of Epidemiology vs Evidence: Professor of Chemistry -> REJECTED.
    3. Authentic claims with matching distinctive tokens -> ACCEPTED.
    """
    import json
    from tests.bundle_factory import create_valid_bundle
    from scripts.validate_dossier import validate_bundle

    b_dir = tmp_path / "generic_bypass_bundle"
    ev_text = "Alice Smith is a Professor of Chemistry at Stanford University."
    create_valid_bundle(
        b_dir,
        target_name="Alice Smith",
        excerpt=ev_text,
        claim_predicate="affiliated_with",
        claim_object="Stanford University",
    )
    # Base bundle is valid
    res_base = validate_bundle(b_dir)
    assert res_base["is_valid"] is True

    # Read base claim
    with open(b_dir / "claims.jsonl", "r", encoding="utf-8") as f:
        claim_data = json.loads(f.readline())

    # Case 1: Generic word bypass attempt: Harvard University vs Stanford University
    claim_data["predicate"] = "affiliated_with"
    claim_data["object_raw"] = "Harvard University"
    (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")
    res1 = validate_bundle(b_dir)
    assert res1["is_valid"] is False
    assert any("Object presence violation" in err for err in res1["errors"])

    # Case 2: Generic word bypass attempt: Professor of Epidemiology vs Professor of Chemistry
    claim_data["predicate"] = "holds_position"
    claim_data["object_raw"] = "Professor of Epidemiology"
    (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")
    res2 = validate_bundle(b_dir)
    assert res2["is_valid"] is False
    assert any("Object presence violation" in err for err in res2["errors"])

    # Case 3: Authentic distinctive claims: Stanford University and Professor of Chemistry
    claim_data["predicate"] = "affiliated_with"
    claim_data["object_raw"] = "Stanford University"
    (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")
    res3 = validate_bundle(b_dir)
    assert res3["is_valid"] is True


def test_single_sided_relation_span_rejected(tmp_path):
    """
    P1 Test:
    relation_span pair constraint enforcement:
    1. ClaimEvidenceSupport rejecting single-sided relation_span_start or relation_span_end at schema level.
    2. validate_bundle() detecting and blocking asymmetric relation span entries in claims.jsonl.
    """
    import json
    import pytest
    from pydantic import ValidationError
    from models.schemas import ClaimEvidenceSupport
    from tests.bundle_factory import create_valid_bundle
    from scripts.validate_dossier import validate_bundle

    # 1. Pydantic schema validation: start without end
    with pytest.raises(ValidationError) as exc1:
        ClaimEvidenceSupport(
            evidence_id="EVI-1",
            subject_mention_id="MEN-1",
            clause_span_start=0,
            clause_span_end=50,
            verbatim_clause="Alice Smith is Professor at Stanford University.",
            relation_span_start=0,
            relation_span_end=None,
        )
    assert "relation_span_start and relation_span_end must both be set or both be None" in str(exc1.value)

    # 2. Pydantic schema validation: end without start
    with pytest.raises(ValidationError) as exc2:
        ClaimEvidenceSupport(
            evidence_id="EVI-1",
            subject_mention_id="MEN-1",
            clause_span_start=0,
            clause_span_end=50,
            verbatim_clause="Alice Smith is Professor at Stanford University.",
            relation_span_start=None,
            relation_span_end=20,
        )
    assert "relation_span_start and relation_span_end must both be set or both be None" in str(exc2.value)

    # 3. validate_bundle() checks with asymmetric relation span
    b_dir = tmp_path / "asymmetric_span_bundle"
    create_valid_bundle(b_dir)
    assert validate_bundle(b_dir)["is_valid"] is True

    with open(b_dir / "claims.jsonl", "r", encoding="utf-8") as f:
        claim_data = json.loads(f.readline())

    # Set asymmetric relation span (start set, end None)
    claim_data["support_clauses"][0]["relation_span_start"] = 0
    claim_data["support_clauses"][0]["relation_span_end"] = None
    (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")
    res = validate_bundle(b_dir)
    assert res["is_valid"] is False
    assert any("validation error" in err or "relation_span" in err for err in res["errors"])


def test_validator_rejects_category_collision_and_substring_bypass(tmp_path):
    """
    P0 Regression Test:
    Validator must reject category collisions (University != Hospital)
    and substring bypasses (MIT in submitted, Dean in deanery) with word boundaries.
    """
    from scripts.validate_dossier import check_object_presence, validate_bundle
    from tests.bundle_factory import create_valid_bundle

    # 1. Pure function level checks
    assert not check_object_presence("Yale University", "Alice works at Yale-New Haven Hospital.")
    assert not check_object_presence("Stanford University", "Stanford Hospital announced today.")
    assert not check_object_presence("MIT", "He submitted his homework yesterday.")
    assert not check_object_presence("Dean", "He visited the local deanery.")
    assert check_object_presence("Yale University", "Alice works at Yale University.")
    assert check_object_presence("Stanford Hospital", "Stanford Hospital announced today.")
    assert check_object_presence("MIT", "He graduated from MIT in 2020.")
    assert check_object_presence("Dean", "He is the Dean of Engineering.")

    # 2. Bundle level verification: Yale University in Yale-New Haven Hospital bundle
    b_yale = tmp_path / "bundle_yale_hospital"
    create_valid_bundle(
        b_yale,
        target_name="Alice Smith",
        excerpt="<html><body>Alice Smith works at Yale-New Haven Hospital.</body></html>",
        claim_predicate="affiliated_with",
        claim_object="Yale University",
    )
    res_yale = validate_bundle(b_yale)
    assert res_yale["is_valid"] is False
    assert any("Object presence violation" in err or "Relation span object violation" in err for err in res_yale["errors"])

    # 3. Bundle level verification: MIT in submitted bundle
    b_mit = tmp_path / "bundle_mit_submitted"
    create_valid_bundle(
        b_mit,
        target_name="Bob Jones",
        excerpt="<html><body>Bob Jones submitted the research grant.</body></html>",
        claim_predicate="affiliated_with",
        claim_object="MIT",
    )
    res_mit = validate_bundle(b_mit)
    assert res_mit["is_valid"] is False
    assert any("Object presence violation" in err or "Relation span object violation" in err for err in res_mit["errors"])


def test_mandatory_relation_span_for_factual_claims(tmp_path):
    """
    P1 Regression Test:
    Double-None relation span cannot bypass Rule 5. Factual claims must provide
    relation-level provenance to pass validate_bundle().
    """
    from pydantic import ValidationError
    from models.schemas import ClaimEvidenceSupport
    from scripts.validate_dossier import validate_bundle
    from tests.bundle_factory import create_valid_bundle

    # 1. Pydantic schema validation: provenance_level='relation' with double None raises ValueError
    with pytest.raises(ValidationError) as exc:
        ClaimEvidenceSupport(
            evidence_id="EVI-1",
            subject_mention_id="MEN-1",
            clause_span_start=0,
            clause_span_end=50,
            verbatim_clause="Alice Smith is Professor at Stanford University.",
            relation_span_start=None,
            relation_span_end=None,
            provenance_level="relation",
        )
    assert "relation_span_start and relation_span_end must both be set when provenance_level is 'relation'" in str(exc.value)

    # 2. validate_bundle(): factual claim with clause-level provenance is rejected
    b_dir = tmp_path / "clause_level_factual_bundle"
    create_valid_bundle(b_dir)
    with open(b_dir / "claims.jsonl", "r", encoding="utf-8") as f:
        claim_data = json.loads(f.readline())

    claim_data["support_clauses"][0]["relation_span_start"] = None
    claim_data["support_clauses"][0]["relation_span_end"] = None
    claim_data["support_clauses"][0]["provenance_level"] = "clause"
    (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")

    res = validate_bundle(b_dir)
    assert res["is_valid"] is False
    assert any("Missing relation span! Factual claim" in err for err in res["errors"])
    assert res["layers"]["relation_precision_enforced"] is False
    assert res["audit_details"]["clause_level_claim_count"] == 1


def test_appositive_natural_variations():
    """
    P1 Regression Test:
    Appositive boundary detection and role/org extraction must handle:
    1. Leading adjective modifiers: 'an award-winning Professor at Stanford University'
    2. Compound roles: 'Professor and Director at Stanford University'
    3. Multi-word disciplines: 'Professor of Molecular Biology at Stanford University'
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import EntityMention, Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    def run_multi(text: str, ev_id: str):
        ev = Evidence(
            evidence_id=ev_id,
            source_id="SRC-VAR",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )
        bob_start = text.index("Bob Jones")
        m_alice = EntityMention(
            mention_id="MEN-ALICE",
            raw_name_text="Alice Smith",
            source_id="SRC-VAR",
            context_snippet=text,
            evidence_id=ev_id,
            mention_key="key-alice",
            char_start=0,
            char_end=11,
        )
        m_bob = EntityMention(
            mention_id="MEN-BOB",
            raw_name_text="Bob Jones",
            source_id="SRC-VAR",
            context_snippet=text,
            evidence_id=ev_id,
            mention_key="key-bob",
            char_start=bob_start,
            char_end=bob_start + len("Bob Jones"),
        )
        claims = extract_claims_from_evidence(
            evidence=ev,
            evidence_mentions=[m_alice, m_bob],
            mention_to_cand_id={"MEN-ALICE": "CAND-ALICE", "MEN-BOB": "CAND-BOB"},
        )
        return [c for c in claims if c.subject_mention_id == "MEN-ALICE"], [c for c in claims if c.subject_mention_id == "MEN-BOB"]

    # Variation 1: Leading modifier
    t1 = "Alice Smith, an award-winning Professor at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    alice_claims1, bob_claims1 = run_multi(t1, "EV-APPOS-VAR1")
    roles1 = [c.object_raw for c in alice_claims1 if c.predicate == "holds_position"]
    affils1 = [c.object_raw for c in alice_claims1 if c.predicate == "affiliated_with"]
    bob_roles1 = [c.object_raw for c in bob_claims1 if c.predicate == "holds_position"]
    bob_affils1 = [c.object_raw for c in bob_claims1 if c.predicate == "affiliated_with"]

    assert "Professor" in roles1
    assert "Stanford University" in affils1
    assert "Dean" in bob_roles1
    assert any("technology" in a.lower() or "mit" in a.lower() or "massachusetts" in a.lower() for a in bob_affils1)
    assert not any("dean" in r.lower() for r in roles1)
    assert not any("massachusetts" in a.lower() or "mit" in a.lower() for a in affils1)

    # Variation 2: Compound roles
    t2 = "Alice Smith, Professor and Director at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    alice_claims2, bob_claims2 = run_multi(t2, "EV-APPOS-VAR2")
    roles2 = [c.object_raw for c in alice_claims2 if c.predicate == "holds_position"]
    affils2 = [c.object_raw for c in alice_claims2 if c.predicate == "affiliated_with"]
    bob_roles2 = [c.object_raw for c in bob_claims2 if c.predicate == "holds_position"]
    bob_affils2 = [c.object_raw for c in bob_claims2 if c.predicate == "affiliated_with"]

    assert "Professor" in roles2
    assert "Director" in roles2
    assert "Stanford University" in affils2
    assert "Dean" in bob_roles2
    assert any("technology" in a.lower() or "mit" in a.lower() or "massachusetts" in a.lower() for a in bob_affils2)
    assert not any("dean" in r.lower() for r in roles2)
    assert not any("massachusetts" in a.lower() for a in affils2)

    # Variation 3: Multi-word disciplines
    t3 = "Alice Smith, Professor of Molecular Biology at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    alice_claims3, bob_claims3 = run_multi(t3, "EV-APPOS-VAR3")
    roles3 = [c.object_raw for c in alice_claims3 if c.predicate == "holds_position"]
    affils3 = [c.object_raw for c in alice_claims3 if c.predicate == "affiliated_with"]
    bob_roles3 = [c.object_raw for c in bob_claims3 if c.predicate == "holds_position"]
    bob_affils3 = [c.object_raw for c in bob_claims3 if c.predicate == "affiliated_with"]

    assert "Professor of Molecular Biology" in roles3
    assert "Stanford University" in affils3
    assert "Dean" in bob_roles3
    assert any("technology" in a.lower() or "mit" in a.lower() or "massachusetts" in a.lower() for a in bob_affils3)
    assert not any("dean" in r.lower() for r in roles3)
    assert not any("massachusetts" in a.lower() for a in affils3)


def test_validator_rejects_cross_entity_and_cross_sentence_proximity_bypasses(tmp_path):
    """
    P0 Regression Test:
    60-char distance fallback must be removed. Cross-entity and cross-sentence
    multi-token stitching (e.g. Harvard ... Stanford University, Yale University Hospital)
    must be strictly rejected.
    """
    from scripts.validate_dossier import check_object_presence, validate_bundle
    from tests.bundle_factory import create_valid_bundle

    # 1. Pure function level checks
    # Counterexample 1: Cross-entity stitching
    assert not check_object_presence("Harvard University", "Harvard Medical School partnered with Stanford University.")
    # Counterexample 2: Cross-sentence stitching
    assert not check_object_presence("Stanford University", "Stanford researchers published results. Yale University responded.")
    # Counterexample 3: Cross-phrase stitching
    assert not check_object_presence("Yale University", "Yale researchers visited New Haven University Hospital.")
    # Counterexample 4: Hospital category collision on trailing head noun
    assert not check_object_presence("Yale University", "Alice works at Yale University Hospital.")

    # Positive controls
    assert check_object_presence("Harvard University", "Alice is at Harvard University.")
    assert check_object_presence("Stanford University", "Alice is at Stanford University.")
    assert check_object_presence("Yale University", "Alice is at Yale University.")
    assert check_object_presence("Yale-New Haven Hospital", "Alice is at Yale-New Haven Hospital.")

    # 2. Bundle level verification: Harvard Medical School partnered with Stanford University
    b_harvard = tmp_path / "bundle_harvard_partnered_stanford"
    create_valid_bundle(
        b_harvard,
        target_name="Alice Smith",
        excerpt="<html><body>Alice Smith says Harvard Medical School partnered with Stanford University.</body></html>",
        claim_predicate="affiliated_with",
        claim_object="Harvard University",
    )
    res_harvard = validate_bundle(b_harvard)
    assert res_harvard["is_valid"] is False
    assert any("Object presence violation" in err or "Relation span object violation" in err for err in res_harvard["errors"])


def test_all_factual_predicates_enforce_relation_spans(tmp_path):
    """
    P0 Regression Test:
    All predicates in RELATION_REQUIRED_PREDICATES (including employed_by, member_of,
    authored_publication, awarded_honor, based_in) must require relation-level provenance.
    Clause-level provenance must be rejected by validate_bundle() and trip relation_precision_gate.
    """
    from scripts.validate_dossier import validate_bundle
    from scripts.score_candidates import evaluate_dossier_bundle
    from tests.bundle_factory import create_valid_bundle

    test_predicates = [
        "employed_by",
        "member_of",
        "authored_publication",
        "awarded_honor",
        "based_in",
    ]

    for pred in test_predicates:
        b_dir = tmp_path / f"bundle_{pred}"
        create_valid_bundle(b_dir, claim_predicate=pred, claim_object="Stanford University" if pred in ("employed_by", "member_of") else "TestObject")

        # Strip relation spans to simulate clause-only bypass
        with open(b_dir / "claims.jsonl", "r", encoding="utf-8") as f:
            claim_data = json.loads(f.readline())

        claim_data["support_clauses"][0]["relation_span_start"] = None
        claim_data["support_clauses"][0]["relation_span_end"] = None
        claim_data["support_clauses"][0]["provenance_level"] = "clause"
        (b_dir / "claims.jsonl").write_text(json.dumps(claim_data) + "\n", encoding="utf-8")

        # 1. Structural validation must fail
        val_res = validate_bundle(b_dir)
        assert val_res["is_valid"] is False, f"Predicate {pred} bypassed validate_bundle without relation span!"
        assert any("Missing relation span! Factual claim" in err for err in val_res["errors"])
        assert val_res["layers"]["relation_precision_enforced"] is False
        assert val_res["audit_details"]["clause_level_claim_count"] == 1

        # 2. Score candidates must trip relation_precision_gate and fail all_gates_passed
        dummy_gold = tmp_path / f"gold_{pred}.json"
        dummy_gold.write_text(json.dumps({
            "case_id": f"case_{pred}",
            "target_name": "Alice Smith",
            "gold_claims": [],
            "gold_clusters": [],
        }), encoding="utf-8")

        score_res = evaluate_dossier_bundle(b_dir, dummy_gold)
        assert score_res["all_gates_passed"] is False, f"Predicate {pred} bypassed all_gates_passed!"
        assert score_res["gates"]["relation_precision_gate"] is False


def test_extended_appositive_and_conjoined_variants():
    """
    P1 Regression Test:
    Verify natural appositive and conjoined variations:
    1. internationally award-winning Professor and Center Director
    2. Professor of Molecular and Cellular Biology (conjoined field with 'and')
    3. Alice Smith and Bob Jones are Professors at Stanford University (plural role, conjoined subjects)
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import EntityMention, Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    def run_multi(text: str, ev_id: str):
        ev = Evidence(
            evidence_id=ev_id,
            source_id="SRC-VAR",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )
        bob_start = text.find("Bob Jones")
        m_alice = EntityMention(
            mention_id="MEN-ALICE",
            raw_name_text="Alice Smith",
            source_id="SRC-VAR",
            context_snippet=text,
            evidence_id=ev_id,
            mention_key="key-alice",
            char_start=0,
            char_end=11,
        )
        m_list = [m_alice]
        mention_map = {"MEN-ALICE": "CAND-ALICE"}
        if bob_start >= 0:
            m_bob = EntityMention(
                mention_id="MEN-BOB",
                raw_name_text="Bob Jones",
                source_id="SRC-VAR",
                context_snippet=text,
                evidence_id=ev_id,
                mention_key="key-bob",
                char_start=bob_start,
                char_end=bob_start + len("Bob Jones"),
            )
            m_list.append(m_bob)
            mention_map["MEN-BOB"] = "CAND-BOB"

        claims = extract_claims_from_evidence(
            evidence=ev,
            evidence_mentions=m_list,
            mention_to_cand_id=mention_map,
        )
        alice_claims = [c for c in claims if c.subject_mention_id == "MEN-ALICE"]
        bob_claims = [c for c in claims if c.subject_mention_id == "MEN-BOB"]
        return alice_claims, bob_claims

    # Variant A: Adverb modifier + Center Director
    t_a = "Alice Smith, internationally award-winning Professor and Center Director at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    alice_a, bob_a = run_multi(t_a, "EV-VAR-A")
    roles_a = [c.object_raw for c in alice_a if c.predicate == "holds_position"]
    affils_a = [c.object_raw for c in alice_a if c.predicate == "affiliated_with"]
    bob_roles_a = [c.object_raw for c in bob_a if c.predicate == "holds_position"]

    assert "Professor" in roles_a
    assert "Center Director" in roles_a
    assert "Stanford University" in affils_a
    assert "Dean" in bob_roles_a

    # Variant B: Conjoined discipline (Molecular and Cellular Biology)
    t_b = "Alice Smith, Professor of Molecular and Cellular Biology at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    alice_b, bob_b = run_multi(t_b, "EV-VAR-B")
    roles_b = [c.object_raw for c in alice_b if c.predicate == "holds_position"]
    assert "Professor of Molecular and Cellular Biology" in roles_b

    # Variant C: Conjoined subjects sharing plural role (Alice Smith and Bob Jones are Professors at Stanford University)
    t_c = "Alice Smith and Bob Jones are Professors at Stanford University."
    alice_c, bob_c = run_multi(t_c, "EV-VAR-C")
    roles_c_alice = [c.object_raw for c in alice_c if c.predicate == "holds_position"]
    affils_c_alice = [c.object_raw for c in alice_c if c.predicate == "affiliated_with"]
    roles_c_bob = [c.object_raw for c in bob_c if c.predicate == "holds_position"]
    affils_c_bob = [c.object_raw for c in bob_c if c.predicate == "affiliated_with"]

    assert "Professor" in roles_c_alice
    assert "Stanford University" in affils_c_alice
    assert "Professor" in roles_c_bob
    assert "Stanford University" in affils_c_bob


def test_cross_sentence_period_not_spliced(tmp_path):
    """
    P0 Regression Test:
    A period cannot act as a token separator connecting cross-sentence objects.
    e.g. 'Alice discussed the surname Harvard. University officials at Stanford responded.'
    must NOT match 'Harvard University'.
    """
    from scripts.validate_dossier import check_object_presence, validate_bundle
    from tests.bundle_factory import create_valid_bundle

    text_cross = "Alice discussed the surname Harvard. University officials at Stanford responded."
    assert not check_object_presence("Harvard University", text_cross)

    # Positive controls: abbreviations with internal periods
    text_phd = "Dr. Alice received her Ph.D. in Biostatistics from Harvard University."
    assert check_object_presence("Ph.D.", text_phd)
    assert check_object_presence("Ph.D. in Biostatistics", text_phd)
    assert check_object_presence("Harvard University", text_phd)

    # Bundle level: cross-sentence object should be rejected
    b_cross = tmp_path / "bundle_cross_sentence"
    create_valid_bundle(
        b_cross,
        target_name="Alice Smith",
        excerpt=f"<html><body>{text_cross}</body></html>",
        claim_predicate="affiliated_with",
        claim_object="Harvard University",
    )
    res_cross = validate_bundle(b_cross)
    assert res_cross["is_valid"] is False
    assert any("Object presence violation" in err or "Relation span object violation" in err for err in res_cross["errors"])


def test_chinese_cross_entity_not_spliced(tmp_path):
    """
    P0 Regression Test:
    Chinese objects must match as a contiguous entity phrase or explicit alias.
    Scattered substrings after removing generic words (e.g. '北京专家' + '清华大学' -> '北京大学')
    must be strictly rejected.
    """
    from scripts.validate_dossier import check_object_presence, validate_bundle
    from tests.bundle_factory import create_valid_bundle

    # Counterexamples
    text_bj = "北京专家与清华大学开展合作"
    assert not check_object_presence("北京大学", text_bj)

    text_fd = "复旦教授访问了清华大学"
    assert not check_object_presence("复旦大学", text_fd)

    # Positive controls
    text_pku = "周昕就读于北京大学生命科学学院。"
    assert check_object_presence("北京大学", text_pku)

    text_101 = "周昕就读于北京一零一中。"
    assert check_object_presence("北京一零一中", text_101)

    assert check_object_presence("清华大学", text_bj)

    # Bundle level: fake bundle must be rejected
    b_pku = tmp_path / "bundle_chinese_cross_entity"
    create_valid_bundle(
        b_pku,
        target_name="周昕",
        excerpt=f"<html><body>{text_bj}</body></html>",
        claim_predicate="affiliated_with",
        claim_object="北京大学",
    )
    res_pku = validate_bundle(b_pku)
    assert res_pku["is_valid"] is False
    assert any("Object presence violation" in err or "Relation span object violation" in err for err in res_pku["errors"])


def test_override_relation_span_and_all_predicates_gate(tmp_path):
    """
    P1 Regression Test:
    1. Invariant test: RELATION_REQUIRED_PREDICATES == PREDICATE_ALLOWLIST.
    2. Parameterized mutation test over all 9 predicates: missing relation span fails validation and trips gate.
    3. Explicit override mode in extract_claims_from_evidence must produce relation-level provenance
       when uniquely resolvable in same sentence, or return [] if unresolvable.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass, PREDICATE_ALLOWLIST, RELATION_REQUIRED_PREDICATES
    from scripts.validate_dossier import validate_bundle
    from tests.bundle_factory import create_valid_bundle
    from datetime import datetime, timezone
    import json

    # 1. Invariant test
    assert RELATION_REQUIRED_PREDICATES == set(PREDICATE_ALLOWLIST), "All allowed factual predicates must require relation spans"

    # 2. Parameterized test over all 9 predicates
    for pred in sorted(PREDICATE_ALLOWLIST):
        b_dir = tmp_path / f"bundle_all_pred_{pred}"
        obj_val = "Stanford University" if pred in ("employed_by", "member_of", "affiliated_with", "graduated_from") else "SampleValue"
        create_valid_bundle(b_dir, claim_predicate=pred, claim_object=obj_val)

        # Mutate to clause-level without relation span
        claims_file = b_dir / "claims.jsonl"
        claim_data = json.loads(claims_file.read_text(encoding="utf-8").strip().splitlines()[0])
        claim_data["support_clauses"][0]["relation_span_start"] = None
        claim_data["support_clauses"][0]["relation_span_end"] = None
        claim_data["support_clauses"][0]["provenance_level"] = "clause"
        claims_file.write_text(json.dumps(claim_data) + "\n", encoding="utf-8")

        val_res = validate_bundle(b_dir)
        assert val_res["is_valid"] is False, f"Predicate {pred} bypassed validation without relation span!"
        assert any("Missing relation span! Factual claim" in err for err in val_res["errors"])
        assert val_res["layers"]["relation_precision_enforced"] is False

    # 3. Formal relation-level extraction test
    ev = Evidence(
        evidence_id="EV-FORMAL-1",
        source_id="SRC-1",
        verbatim_excerpt="Alice Smith is Professor at Stanford University.",
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    mentions = extract_mentions_and_aliases("SRC-1", ev.verbatim_excerpt, "Alice Smith", evidence_id="EV-FORMAL-1")
    claims = extract_claims_from_evidence(
        ev,
        candidate_entity_id="CAND-ALICE",
        target_name="Alice Smith",
        evidence_mentions=mentions,
    )
    assert len(claims) >= 2
    for c in claims:
        assert c.support_clauses[0].provenance_level == "relation"
        assert c.support_clauses[0].relation_span_start is not None
        assert c.support_clauses[0].relation_span_end is not None



def test_conjoined_discipline_vs_role_disambiguation():
    """
    P1 Regression Test:
    'and' after a discipline must look ahead for role headwords:
    - If followed by a role (e.g. Director, Dean, Chair, Center Director), end the discipline and split into second role.
    - If followed by a discipline (e.g. Cellular Biology), treat 'and' as internal to the discipline.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    def run_case(text: str, ev_id: str, t_name: str = "Alice Smith"):
        ev = Evidence(
            evidence_id=ev_id,
            source_id=f"SRC-{ev_id}",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )
        mentions = extract_mentions_and_aliases(ev.source_id, text, t_name, evidence_id=ev.evidence_id)
        return extract_claims_from_evidence(ev, "CAND-1", target_name=t_name, evidence_mentions=mentions)

    # Case A: Molecular Biology and Director
    t_a = "Alice Smith, Professor of Molecular Biology and Director at Stanford University, introduced Bob Jones."
    claims_a = run_case(t_a, "EV-DIS-A")
    roles_a = [c.object_raw for c in claims_a if c.predicate == "holds_position"]
    assert "Professor of Molecular Biology" in roles_a
    assert "Director" in roles_a
    assert "Professor of Molecular Biology and Director" not in roles_a

    # Case B: Biology and Director of the Center
    t_b = "Alice Smith, Professor of Biology and Director of the Center at Stanford University, introduced Bob Jones."
    claims_b = run_case(t_b, "EV-DIS-B")
    roles_b = [c.object_raw for c in claims_b if c.predicate == "holds_position"]
    assert "Professor of Biology" in roles_b
    assert "Director of the Center" in roles_b
    assert not any("director of" == r.lower() or "director of at" in r.lower() for r in roles_b)

    # Case C: Molecular and Cellular Biology (internal conjoined discipline)
    t_c = "Alice Smith, Professor of Molecular and Cellular Biology at Stanford University, introduced Bob Jones."
    claims_c = run_case(t_c, "EV-DIS-C")
    roles_c = [c.object_raw for c in claims_c if c.predicate == "holds_position"]
    assert "Professor of Molecular and Cellular Biology" in roles_c
    assert len(roles_c) == 1


def test_multi_subject_coordinated_role_sharing_and_isolation():
    """
    P1 Regression Test:
    1. Three or more coordinated subjects (e.g. 'Alice, Bob, and Charlie are Professors...')
       must all independently receive the shared role and affiliation with their own relation spans.
    2. Roles from separate clauses (e.g. while clauses) or appositives (e.g. introduced clauses)
       must NOT be cross-copied between subjects.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    def run_multi(text: str, ev_id: str, names: list):
        ev = Evidence(
            evidence_id=ev_id,
            source_id=f"SRC-{ev_id}",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )
        all_mentions = []
        for name in names:
            m_list = extract_mentions_and_aliases(ev.source_id, text, name, evidence_id=ev.evidence_id)
            all_mentions.extend(m_list)

        results = {}
        for name in names:
            results[name] = extract_claims_from_evidence(
                ev,
                f"CAND-{name}",
                target_name=name,
                evidence_mentions=all_mentions,
            )
        return results

    # 1. Three subjects sharing plural role and affiliation
    t_shared = "Alice Smith, Bob Jones, and Charlie Brown are Professors at Stanford University."
    res_shared = run_multi(t_shared, "EV-3SUBJ", ["Alice Smith", "Bob Jones", "Charlie Brown"])
    for name in ["Alice Smith", "Bob Jones", "Charlie Brown"]:
        c_list = res_shared[name]
        roles = [c.object_raw for c in c_list if c.predicate == "holds_position"]
        affils = [c.object_raw for c in c_list if c.predicate == "affiliated_with"]
        assert "Professor" in roles, f"{name} failed to extract Professor from 3-subject coordination"
        assert "Stanford University" in affils, f"{name} failed to extract Stanford University"
        # Verify relation span exists and is non-empty
        prof_claims = [c for c in c_list if c.predicate == "holds_position"]
        assert prof_claims[0].support_clauses[0].provenance_level == "relation"
        assert prof_claims[0].support_clauses[0].relation_span_start is not None

    # 2. Separate clauses (while) isolation
    t_while = "Alice Smith is Professor at Stanford University while Bob Jones is Dean at Massachusetts Institute of Technology."
    res_while = run_multi(t_while, "EV-WHILE", ["Alice Smith", "Bob Jones"])
    alice_roles = [c.object_raw for c in res_while["Alice Smith"] if c.predicate == "holds_position"]
    bob_roles = [c.object_raw for c in res_while["Bob Jones"] if c.predicate == "holds_position"]
    assert "Professor" in alice_roles and "Dean" not in alice_roles
    assert "Dean" in bob_roles and "Professor" not in bob_roles

    # 3. Appositive cross-subject isolation
    t_appos = "Alice Smith, Professor at Stanford University, introduced Bob Jones, Dean at Massachusetts Institute of Technology."
    res_appos = run_multi(t_appos, "EV-APPOS", ["Alice Smith", "Bob Jones"])
    alice_a_roles = [c.object_raw for c in res_appos["Alice Smith"] if c.predicate == "holds_position"]
    bob_a_roles = [c.object_raw for c in res_appos["Bob Jones"] if c.predicate == "holds_position"]
    assert "Professor" in alice_a_roles and "Dean" not in alice_a_roles
    assert "Dean" in bob_a_roles and "Professor" not in bob_a_roles


def test_chinese_short_alias_compound_blocking(tmp_path):
    """
    P0 Red Test:
    Chinese short aliases (e.g. '北大' for '北京大学') must not match longer compounds
    such as '北大荒集团' or '北大西洋公约组织'.
    Matches must enforce token/word boundaries, compound blocking, and academic/employment context.
    """
    from scripts.validate_dossier import check_object_presence, validate_bundle
    import json

    # 1. Direct unit checks for compound blocking
    text_beidahuang = "周昕报道北大荒集团发布年报"
    assert not check_object_presence("北京大学", text_beidahuang), "北大 must not match inside 北大荒集团"

    text_nato = "周昕参加北大西洋公约组织会议"
    assert not check_object_presence("北京大学", text_nato), "北大 must not match inside 北大西洋公约组织"

    # 2. Positive checks: short alias with genuine educational/employment context
    text_positive_grad = "周昕毕业于北大。"
    assert check_object_presence("北京大学", text_positive_grad), "北大 with 毕业于 must match"

    text_positive_prof = "周昕为北大教授。"
    assert check_object_presence("北京大学", text_positive_prof), "北大 with 教授 must match"

    # 3. Full bundle validation gate check:
    # A bundle that falsely attempts to claim 北京大学 based on 北大荒集团 must be rejected
    b_dir = tmp_path / "bundle_chinese_short_alias_fail"
    b_dir.mkdir()

    from tests.bundle_factory import create_valid_bundle
    create_valid_bundle(
        b_dir,
        target_name="周昕",
        excerpt=text_beidahuang,
        claim_predicate="affiliated_with",
        claim_object="北京大学",
    )

    val_res = validate_bundle(b_dir)
    assert not val_res["is_valid"], "Bundle with fake 北京大学 claim matching 北大荒 must fail validation!"


def test_unentailed_actions_do_not_produce_affirmative_claims():
    """
    P1 Red Test:
    1. Sentences with unentailed actions must NOT generate affirmative claims:
       - 'Alice Smith criticized the Nobel Prize.' -> no awarded_honor
       - 'Alice Smith visited Stanford University.' -> no affiliated_with
       - 'Alice Smith wrote about Example Paper.' -> no authored_publication
    2. extract_claims_from_evidence must not expose arbitrary predicate injection override.
    """
    import inspect
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    # 1. Verify signature does NOT have target_predicate or extracted_object
    sig = inspect.signature(extract_claims_from_evidence)
    assert "target_predicate" not in sig.parameters, "target_predicate parameter must be removed"
    assert "extracted_object" not in sig.parameters, "extracted_object parameter must be removed"

    def run_case(text: str, ev_id: str):
        ev = Evidence(
            evidence_id=ev_id,
            source_id=f"SRC-{ev_id}",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )
        mentions = extract_mentions_and_aliases(ev.source_id, text, "Alice Smith", evidence_id=ev.evidence_id)
        return extract_claims_from_evidence(ev, "CAND-ALICE", target_name="Alice Smith", evidence_mentions=mentions)

    # Criticized Nobel Prize -> should NOT extract awarded_honor
    claims_nobel = run_case("Alice Smith criticized the Nobel Prize.", "EV-CRIT-NOBEL")
    assert not any(c.predicate == "awarded_honor" for c in claims_nobel)

    # Visited Stanford -> should NOT extract affiliated_with
    claims_visit = run_case("Alice Smith visited Stanford University.", "EV-VISIT-SU")
    assert not any(c.predicate == "affiliated_with" for c in claims_visit)

    # Wrote about paper -> should NOT extract authored_publication
    claims_wrote = run_case("Alice Smith wrote about Example Paper.", "EV-WROTE-EP")
    assert not any(c.predicate == "authored_publication" for c in claims_wrote)


def test_hyphenated_and_accented_names_in_coordinated_subjects():
    """
    P1 Red Test:
    Coordinated subjects with hyphens (Anne-Marie Smith) and accents (José Lee)
    must ALL be recognized, and ALL receive the shared position and affiliation,
    with independent relation spans.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    text = "Anne-Marie Smith, Bob Jones, and José Lee are Professors at Stanford University."
    ev = Evidence(
        evidence_id="EV-COORD-UNICODE",
        source_id="SRC-COORD",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    names = ["Anne-Marie Smith", "Bob Jones", "José Lee"]
    all_mentions = []
    for name in names:
        m_list = extract_mentions_and_aliases(ev.source_id, text, name, evidence_id=ev.evidence_id)
        all_mentions.extend(m_list)

    assert len(all_mentions) >= 3, f"Mentions for all 3 subjects must be extracted, got: {all_mentions}"

    for name in names:
        claims = extract_claims_from_evidence(
            ev,
            f"CAND-{name}",
            target_name=name,
            evidence_mentions=all_mentions,
        )
        roles = [c.object_raw for c in claims if c.predicate == "holds_position"]
        affils = [c.object_raw for c in claims if c.predicate == "affiliated_with"]

        assert "Professor" in roles, f"Subject '{name}' failed to extract Professor! Extracted roles: {roles}"
        assert "Stanford University" in affils, f"Subject '{name}' failed to extract Stanford University! Extracted affils: {affils}"

        prof_claim = [c for c in claims if c.predicate == "holds_position"][0]
        sup = prof_claim.support_clauses[0]
        assert sup.provenance_level == "relation"
        assert sup.relation_span_start is not None
        assert sup.relation_span_end is not None


def test_chinese_short_alias_unregistered_compound_blocking():
    """
    P0 Red Test:
    Ensures Chinese short alias '北大' is NOT matched when followed by unregistered compound words
    (e.g., 北大资源集团, 北大青鸟, 北大方正, 北大公学国际部, 北大博雅学院) or when not in a relation local object span.
    Generatively tests combinations of brand words and suffixes.
    """
    from scripts.validate_dossier import find_object_in_text

    # 1. Unregistered commercial / brand compounds must NOT match 北京大学
    assert find_object_in_text("北京大学", "周昕毕业于北大资源集团。") is None
    assert find_object_in_text("北京大学", "北大青鸟学员毕业于清华大学。") is None
    assert find_object_in_text("北京大学", "北大方正员工在该公司任职。") is None
    assert find_object_in_text("北京大学", "周昕毕业于北大公学国际部。") is None
    assert find_object_in_text("北京大学", "周昕任职于北大博雅学院。") is None

    # 2. Generative deformation testing: all unregistered brand + suffix combinations must be rejected
    brands = ["公学", "博雅", "青鸟", "方正", "资源", "科技", "药业", "集团", "公司", "国际", "荒", "仓", "西洋", "星空", "创新", "投资"]
    suffixes = ["学院", "系", "部", "中心", "所", "国际部", "研究院", "学校", "班", "学员", "员工"]
    for b in brands:
        for s in suffixes:
            res = find_object_in_text("北京大学", f"周昕毕业于北大{b}{s}。")
            assert res is None, f"Expected None for '北大{b}{s}', but got {res}"

    # 3. Legitimate relation local object spans must still match
    assert find_object_in_text("北京大学", "周昕毕业于北大。") is not None
    assert find_object_in_text("北京大学", "周昕为北大计算机系教授。") is not None
    assert find_object_in_text("北京大学", "周昕为北大教授。") is not None


def test_benchmark_4_non_zero_exit_code_on_failure():
    """
    P0/P1 Test:
    Tests Benchmark 4 release gating via pure decision function check_benchmark_release_decision
    and portable non-zero exit code in isolated temporary environment without touching repo fixture permissions.
    """
    import subprocess
    import sys
    import tempfile
    from benchmarks.eval_end2end import check_benchmark_release_decision

    # 1. Pure decision function testing across all gating criteria
    passing_summary = {
        "all_gates_pass_rate": 1.0,
        "total_false_merges_across_suite": 0,
        "bundle_immutability_verified_all": True,
        "isolation_gate": True,
        "gold_access_blocked": True,
        "dac_sentinel_gate": True,
    }
    assert check_benchmark_release_decision(passing_summary) is True

    assert check_benchmark_release_decision(dict(passing_summary, all_gates_pass_rate=0.9)) is False
    assert check_benchmark_release_decision(dict(passing_summary, total_false_merges_across_suite=1)) is False
    assert check_benchmark_release_decision(dict(passing_summary, bundle_immutability_verified_all=False)) is False
    assert check_benchmark_release_decision(dict(passing_summary, isolation_gate=False)) is False
    assert check_benchmark_release_decision(dict(passing_summary, gold_access_blocked=False)) is False
    assert check_benchmark_release_decision(dict(passing_summary, dac_sentinel_gate=False)) is False

    # 2. Subprocess exit code testing without modifying repository file permissions
    test_snippet = """
import sys
from benchmarks.eval_end2end import check_benchmark_release_decision
failing_summary = {
    'all_gates_pass_rate': 0.9,
    'total_false_merges_across_suite': 0,
    'bundle_immutability_verified_all': True,
    'isolation_gate': True,
    'gold_access_blocked': True,
    'dac_sentinel_gate': True,
}
if not check_benchmark_release_decision(failing_summary):
    sys.exit(1)
sys.exit(0)
"""
    res = subprocess.run([sys.executable, "-c", test_snippet], capture_output=True, text=True)
    assert res.returncode == 1, f"Expected returncode 1, got {res.returncode}"


def test_pro_drop_subject_chain_resolution():
    """
    P0/P1 Test:
    Verifies independent verification of antecedent mention chains:
    1. Legitimate pro-drop with verified mention_map and candidate_map passes.
    2. Fake antecedent_mention_id='MEN-deadbeef' is REJECTED.
    3. Missing antecedent metadata without explicit mention is REJECTED.
    4. Intervening competing subject breaks anaphoric attribution.
    5. Schema enforces conditional constraints on antecedent fields.
    """
    import pytest
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from models.schemas import ClaimEvidenceSupport, Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from scripts.score_candidates import check_5d_entailment

    text = "<html><body>李嘉文毕业于北京一零一中，现为耶鲁大学游泳队，荣获 CSCAA Individual Scholar All-America Team 荣誉"
    ev = Evidence(
        evidence_id="EVI-TEST-LJ",
        source_id="SRC-TEST-LJ",
        verbatim_excerpt=text,
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    mentions = extract_mentions_and_aliases(ev.source_id, text, "李嘉文", evidence_id=ev.evidence_id)
    claims = extract_claims_from_evidence(ev, "CAND-LJ", target_name="李嘉文", evidence_mentions=mentions)

    assert len(claims) == 3, f"Expected 3 claims, got {len(claims)}"

    affil_claim = [c for c in claims if c.predicate == "affiliated_with"][0]
    sup = affil_claim.support_clauses[0]
    assert hasattr(sup, "subject_resolution") and sup.subject_resolution in ("pro_drop_anaphora", "pronoun_anaphora")
    assert hasattr(sup, "antecedent_mention_id") and sup.antecedent_mention_id is not None

    evidence_map = {ev.evidence_id: ev.model_dump()}
    mention_map = {m.mention_id: m.model_dump() for m in mentions}
    candidate_map = {"CAND-LJ": {"candidate_entity_id": "CAND-LJ", "mention_ids": [m.mention_id for m in mentions]}}
    gold_affil = {
        "predicate": "affiliated_with",
        "object_raw": "Yale University Men's Swimming and Diving",
        "equivalence_set": ["耶鲁大学游泳队", "Yale Bulldogs"],
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "subject": "李嘉文",
    }

    # (A) Legitimate independent verification: must succeed
    is_ent, is_attr, is_temp = check_5d_entailment(
        affil_claim.model_dump(), gold_affil, evidence_map, {"李嘉文"},
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr is True, "Pro-drop clause must be correctly attributed to antecedent subject 李嘉文"
    assert is_ent is True, "Affiliation claim must be fully entailed"

    # (B) Fake antecedent_mention_id: must FAIL attribution
    claim_fake = affil_claim.model_dump()
    claim_fake["support_clauses"][0]["antecedent_mention_id"] = "MEN-deadbeef"
    _, is_attr_fake, _ = check_5d_entailment(
        claim_fake, gold_affil, evidence_map, {"李嘉文"},
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_fake is False, "Fake antecedent_mention_id must NOT be attributed"

    # (C) Missing antecedent metadata: must FAIL attribution
    claim_no_ante = affil_claim.model_dump()
    claim_no_ante["support_clauses"][0]["antecedent_mention_id"] = None
    claim_no_ante["support_clauses"][0]["subject_resolution"] = "explicit_mention"
    _, is_attr_none, _ = check_5d_entailment(
        claim_no_ante, gold_affil, evidence_map, {"李嘉文"},
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_none is False, "Clause without target name or verified antecedent must NOT be attributed"

    # (D) Intervening competing subject: must break antecedent chain
    intervening_mention = {
        "mention_id": "MEN-COMPETING",
        "raw_name_text": "张伟",
        "source_id": ev.source_id,
        "evidence_id": ev.evidence_id,
        "char_start": 20,
        "char_end": 22,
    }
    intervening_mention_map = dict(mention_map)
    intervening_mention_map["MEN-COMPETING"] = intervening_mention
    _, is_attr_intervene, _ = check_5d_entailment(
        affil_claim.model_dump(), gold_affil, evidence_map, {"李嘉文"},
        mention_map=intervening_mention_map, candidate_map=candidate_map,
    )
    assert is_attr_intervene is False, "Intervening competing subject must break anaphoric attribution"

    # (E) Schema conditional constraints validation
    with pytest.raises(ValueError, match="antecedent_mention_id must be provided"):
        ClaimEvidenceSupport(
            evidence_id="EVI-1",
            subject_mention_id="MEN-1",
            clause_span_start=10,
            clause_span_end=20,
            verbatim_clause="test",
            subject_resolution="pro_drop_anaphora",
            antecedent_mention_id=None,
            antecedent_clause_span=(0, 10),
        )

    with pytest.raises(ValueError, match="antecedent_mention_id must be None"):
        ClaimEvidenceSupport(
            evidence_id="EVI-1",
            subject_mention_id="MEN-1",
            clause_span_start=10,
            clause_span_end=20,
            verbatim_clause="test",
            subject_resolution="explicit_mention",
            antecedent_mention_id="MEN-1",
        )


def test_warc_player_enforces_query_budget():
    """
    P1 Red Test:
    Verifies that WarcPlayerCollector enforces query_budget and stops queries once budget is exhausted.
    """
    from core.collectors.warc_player import WarcPlayerCollector
    from pathlib import Path

    warc_path = Path("benchmarks/test_cases/dev_regression/frozen_corpus.warc")
    collector = WarcPlayerCollector(warc_path, query_budget=2)
    assert collector.query_budget == 2

    # Query 1
    collector.search("Yale")
    assert collector.queries_executed == 1

    # Query 2
    collector.search("Harvard")
    assert collector.queries_executed == 2

    # Query 3 should be blocked
    res = collector.search("Stanford")
    assert res == []
    assert collector.queries_executed == 2
    assert any("exhausted" in err.lower() for err in collector.errors)


def test_5d_strict_object_match_rejects_substring_counterexample():
    """
    P0 Unit Test:
    Verifies that 5D object matching does NOT allow substring inclusion.
    System object 'submitted' must NOT match Gold object 'MIT' on 'Alice Smith submitted a university application.'
    """
    from scripts.score_candidates import check_5d_entailment

    gold_claim = {
        "predicate": "graduated_from",
        "object_raw": "MIT",
        "equivalence_set": ["Massachusetts Institute of Technology"],
        "polarity": "affirmative",
        "temporal_status": "unknown",
    }
    evidence_map = {
        "EVI-1": {
            "evidence_id": "EVI-1",
            "source_id": "SRC-1",
            "verbatim_excerpt": "Alice Smith submitted a university application.",
        }
    }
    valid_subjects = {"alice smith"}

    # Counterexample: system object is 'submitted'
    sc_bad = {
        "claim_id": "CLM-BAD",
        "candidate_entity_id": "CAND-1",
        "predicate": "graduated_from",
        "object_raw": "submitted",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-1"],
        "support_clauses": [
            {
                "evidence_id": "EVI-1",
                "subject_mention_id": "MEN-1",
                "clause_span_start": 0,
                "clause_span_end": 44,
                "verbatim_clause": "Alice Smith submitted a university application.",
                "subject_resolution": "explicit_mention",
            }
        ],
    }
    is_ent, is_attr, is_temp = check_5d_entailment(sc_bad, gold_claim, evidence_map, valid_subjects)
    assert (is_ent, is_attr, is_temp) == (False, False, False), "Substring match 'submitted' for 'MIT' must be rejected"

    # Valid exact match
    ev_good = {
        "evidence_id": "EVI-GOOD",
        "source_id": "SRC-GOOD",
        "verbatim_excerpt": "Alice Smith graduated from MIT with honors.",
    }
    sc_good_exact = {
        "claim_id": "CLM-GOOD",
        "candidate_entity_id": "CAND-1",
        "predicate": "graduated_from",
        "object_raw": "MIT",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-GOOD"],
        "support_clauses": [
            {
                "evidence_id": "EVI-GOOD",
                "subject_mention_id": "MEN-1",
                "clause_span_start": 0,
                "clause_span_end": 42,
                "verbatim_clause": "Alice Smith graduated from MIT with honors.",
                "subject_resolution": "explicit_mention",
            }
        ],
    }
    is_ent_g, is_attr_g, is_temp_g = check_5d_entailment(sc_good_exact, gold_claim, {"EVI-GOOD": ev_good}, valid_subjects)
    assert is_ent_g is True and is_attr_g is True

    # Valid equivalence set match
    ev_equiv = {
        "evidence_id": "EVI-EQUIV",
        "source_id": "SRC-EQUIV",
        "verbatim_excerpt": "Alice Smith graduated from Massachusetts Institute of Technology.",
    }
    sc_good_equiv = {
        "claim_id": "CLM-EQUIV",
        "candidate_entity_id": "CAND-1",
        "predicate": "graduated_from",
        "object_raw": "Massachusetts Institute of Technology",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-EQUIV"],
        "support_clauses": [
            {
                "evidence_id": "EVI-EQUIV",
                "subject_mention_id": "MEN-1",
                "clause_span_start": 0,
                "clause_span_end": 64,
                "verbatim_clause": "Alice Smith graduated from Massachusetts Institute of Technology.",
                "subject_resolution": "explicit_mention",
            }
        ],
    }
    is_ent_eq, is_attr_eq, is_temp_eq = check_5d_entailment(sc_good_equiv, gold_claim, {"EVI-EQUIV": ev_equiv}, valid_subjects)
    assert is_ent_eq is True and is_attr_eq is True


def test_pro_drop_and_pronoun_syntactic_and_adjacency_gating():
    """
    P0 Unit Test:
    Verifies that:
    1. Distant antecedent (80 sentences away / >15 char gap with sentence boundaries) is rejected for pro-drop.
    2. Pro-drop clause without allowed syntactic predicate connector is rejected.
    3. Pronoun anaphora clause without pronoun is rejected.
    4. Intervening unextracted Chinese competing person (e.g. '张伟') is detected in raw text and rejected.
    """
    from scripts.score_candidates import check_5d_entailment

    gold_claim = {
        "predicate": "affiliated_with",
        "object_raw": "耶鲁大学游泳队",
        "polarity": "affirmative",
        "temporal_status": "unknown",
    }
    mention_map = {
        "MEN-LI": {
            "mention_id": "MEN-LI",
            "raw_name_text": "李嘉文",
            "source_id": "SRC-TEST",
            "evidence_id": "EVI-TEST",
            "candidate_entity_id": "CAND-LI",
            "char_start": 0,
            "char_end": 3,
        }
    }
    candidate_map = {"CAND-LI": {"candidate_entity_id": "CAND-LI", "mention_ids": ["MEN-LI"]}}
    valid_subjects = {"李嘉文"}

    # 1. Distant gap with sentence boundaries
    distant_excerpt = "李嘉文毕业于北京一零一中。" + ("这是一句填充内容。" * 40) + "现为耶鲁大学游泳队。"
    ante_end = 12
    c_start = len(distant_excerpt) - len("现为耶鲁大学游泳队。")
    c_end = len(distant_excerpt)
    ev_distant = {
        "evidence_id": "EVI-DISTANT",
        "source_id": "SRC-TEST",
        "verbatim_excerpt": distant_excerpt,
    }
    sc_distant = {
        "claim_id": "CLM-DISTANT",
        "candidate_entity_id": "CAND-LI",
        "predicate": "affiliated_with",
        "object_raw": "耶鲁大学游泳队",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-DISTANT"],
        "support_clauses": [
            {
                "evidence_id": "EVI-DISTANT",
                "subject_mention_id": "MEN-LI",
                "clause_span_start": c_start,
                "clause_span_end": c_end,
                "verbatim_clause": "现为耶鲁大学游泳队。",
                "subject_resolution": "pro_drop_anaphora",
                "antecedent_mention_id": "MEN-LI",
                "antecedent_clause_span": [0, ante_end],
            }
        ],
    }
    _, is_attr_dist, _ = check_5d_entailment(
        sc_distant, gold_claim, {"EVI-DISTANT": ev_distant}, valid_subjects,
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_dist is False, "Distant pro-drop across sentences must NOT be attributed"

    # 2. Missing predicate connector at clause start
    ev_short = {
        "evidence_id": "EVI-SHORT",
        "source_id": "SRC-TEST",
        "verbatim_excerpt": "李嘉文毕业于北京一零一中，耶鲁大学游泳队核心成员。",
    }
    sc_no_conn = {
        "claim_id": "CLM-NO-CONN",
        "candidate_entity_id": "CAND-LI",
        "predicate": "affiliated_with",
        "object_raw": "耶鲁大学游泳队",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-SHORT"],
        "support_clauses": [
            {
                "evidence_id": "EVI-SHORT",
                "subject_mention_id": "MEN-LI",
                "clause_span_start": 13,
                "clause_span_end": 26,
                "verbatim_clause": "耶鲁大学游泳队核心成员。",
                "subject_resolution": "pro_drop_anaphora",
                "antecedent_mention_id": "MEN-LI",
                "antecedent_clause_span": [0, 12],
            }
        ],
    }
    _, is_attr_noconn, _ = check_5d_entailment(
        sc_no_conn, gold_claim, {"EVI-SHORT": ev_short}, valid_subjects,
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_noconn is False, "Pro-drop clause without allowed predicate connector must NOT be attributed"

    # 3. Pronoun anaphora without pronoun
    sc_no_pronoun = {
        "claim_id": "CLM-NO-PRONOUN",
        "candidate_entity_id": "CAND-LI",
        "predicate": "affiliated_with",
        "object_raw": "耶鲁大学游泳队",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-SHORT"],
        "support_clauses": [
            {
                "evidence_id": "EVI-SHORT",
                "subject_mention_id": "MEN-LI",
                "clause_span_start": 13,
                "clause_span_end": 26,
                "verbatim_clause": "耶鲁大学游泳队核心成员。",
                "subject_resolution": "pronoun_anaphora",
                "antecedent_mention_id": "MEN-LI",
                "antecedent_clause_span": [0, 12],
            }
        ],
    }
    _, is_attr_nopron, _ = check_5d_entailment(
        sc_no_pronoun, gold_claim, {"EVI-SHORT": ev_short}, valid_subjects,
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_nopron is False, "Pronoun anaphora clause without pronoun must NOT be attributed"

    # 4. Intervening unextracted Chinese competing person ('张伟在北京大学任教')
    ev_competing = {
        "evidence_id": "EVI-COMPETING",
        "source_id": "SRC-TEST",
        "verbatim_excerpt": "李嘉文毕业于北京一零一中，张伟在北京大学任教，现为耶鲁大学游泳队。",
    }
    # Notice: mention_map ONLY has 李嘉文 (MEN-LI). '张伟' is completely unextracted in mention_map.
    c_start_comp = ev_competing["verbatim_excerpt"].find("现为耶鲁大学游泳队。")
    sc_intervene = {
        "claim_id": "CLM-INTERVENE",
        "candidate_entity_id": "CAND-LI",
        "predicate": "affiliated_with",
        "object_raw": "耶鲁大学游泳队",
        "polarity": "affirmative",
        "temporal_status": "unknown",
        "evidence_ids": ["EVI-COMPETING"],
        "support_clauses": [
            {
                "evidence_id": "EVI-COMPETING",
                "subject_mention_id": "MEN-LI",
                "clause_span_start": c_start_comp,
                "clause_span_end": c_start_comp + len("现为耶鲁大学游泳队。"),
                "verbatim_clause": "现为耶鲁大学游泳队。",
                "subject_resolution": "pro_drop_anaphora",
                "antecedent_mention_id": "MEN-LI",
                "antecedent_clause_span": [0, 12],
            }
        ],
    }
    _, is_attr_inter, _ = check_5d_entailment(
        sc_intervene, gold_claim, {"EVI-COMPETING": ev_competing}, valid_subjects,
        mention_map=mention_map, candidate_map=candidate_map,
    )
    assert is_attr_inter is False, "Intervening unextracted competing person ('张伟') must break pro-drop attribution"


def test_benchmark_4_isolation_gate_fail_closed_decision(tmp_path):
    """
    P0 Unit Test:
    Verifies that Benchmark 4 check_benchmark_release_decision strictly fails closed
    if isolation_gate or gold_access_blocked is False.
    Also tests pure tempfile permission blocking without mutating repo fixtures.
    """
    import os
    from benchmarks.eval_end2end import check_benchmark_release_decision

    base_summary = {
        "all_gates_pass_rate": 1.0,
        "total_false_merges_across_suite": 0,
        "bundle_immutability_verified_all": True,
        "dac_sentinel_gate": True,
        "isolation_gate": True,
        "gold_access_blocked": True,
    }
    assert check_benchmark_release_decision(base_summary) is True

    # 1. dac_sentinel_gate = False -> FAIL
    s1 = dict(base_summary, dac_sentinel_gate=False)
    assert check_benchmark_release_decision(s1) is False

    # 2. Legacy isolation_gate only (missing dac_sentinel_gate) -> MUST FAIL CLOSED
    s_legacy_only = {k: v for k, v in base_summary.items() if k != "dac_sentinel_gate"}
    assert check_benchmark_release_decision(s_legacy_only) is False

    # 3. gold_access_blocked = False -> FAIL
    s2 = dict(base_summary, gold_access_blocked=False)
    assert check_benchmark_release_decision(s2) is False

    # 4. Missing sentinel fields -> FAIL
    s3 = {k: v for k, v in base_summary.items() if k not in ("dac_sentinel_gate", "gold_access_blocked")}
    assert check_benchmark_release_decision(s3) is False

    # 4. Pure tempfile file permission access blocking verification
    test_file = tmp_path / "test_gold.json"
    test_file.write_text('{"secret": "gold"}', encoding="utf-8")
    orig_mode = test_file.stat().st_mode & 0o777

    try:
        os.chmod(test_file, 0o000)
        # Kernel must raise PermissionError on reading
        with pytest.raises(PermissionError):
            with open(test_file, "r", encoding="utf-8") as f:
                f.read()
    finally:
        os.chmod(test_file, orig_mode)

    # Permission restored
    assert test_file.read_text(encoding="utf-8") == '{"secret": "gold"}'


def test_chinese_name_boundary_rejects_longer_names_counterexamples():
    """
    P0 Unit Test:
    Verifies that Chinese name matching enforces maximal span and left/right context boundaries.
    Prevents target '周昕' from matching '周昕怡', and '李嘉文' from matching '李嘉文博'.
    Verifies that legitimate titles, predicates, and punctuation allow correct matches.
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases
    from core.extractors.claim_extractor import extract_claims_from_evidence

    # 1. Negative Counterexample 1: 周昕 in 周昕怡现任北京大学教授
    text_zx_longer = "周昕怡现任北京大学教授"
    ev1 = make_evidence(text_zx_longer, ev_id="EV-ZX-1")
    m1 = extract_mentions_and_aliases(ev1.source_id, text_zx_longer, target_name="周昕", evidence_id=ev1.evidence_id)
    assert len(m1) == 0, f"Expected 0 mentions for 周昕 in 周昕怡, got {len(m1)}"
    c1 = extract_claims_from_evidence(ev1, "CAND-ZX", subject_mention_id="MEN-ZX", target_name="周昕", evidence_mentions=m1)
    assert len(c1) == 0, f"Expected 0 claims for 周昕 in 周昕怡, got {len(c1)}"

    # 2. Negative Counterexample 2: 李嘉文 in 李嘉文博荣获 Nobel Prize
    text_ljw_longer = "李嘉文博荣获 Nobel Prize"
    ev2 = make_evidence(text_ljw_longer, ev_id="EV-LJW-2")
    m2 = extract_mentions_and_aliases(ev2.source_id, text_ljw_longer, target_name="李嘉文", evidence_id=ev2.evidence_id)
    assert len(m2) == 0, f"Expected 0 mentions for 李嘉文 in 李嘉文博, got {len(m2)}"
    c2 = extract_claims_from_evidence(ev2, "CAND-LJW", subject_mention_id="MEN-LJW", target_name="李嘉文", evidence_mentions=m2)
    assert len(c2) == 0, f"Expected 0 claims for 李嘉文 in 李嘉文博, got {len(c2)}"

    # 3. Positive Example 1: 周昕现任北京大学教授
    text_pos1 = "周昕现任北京大学教授"
    ev3 = make_evidence(text_pos1, ev_id="EV-POS-1")
    m3 = extract_mentions_and_aliases(ev3.source_id, text_pos1, target_name="周昕", evidence_id=ev3.evidence_id)
    assert len(m3) == 1 and m3[0].raw_name_text == "周昕"
    c3 = extract_claims_from_evidence(ev3, "CAND-ZX", subject_mention_id=m3[0].mention_id, target_name="周昕", evidence_mentions=m3)
    preds = {c.predicate: c.object_raw for c in c3}
    assert preds.get("holds_position") == "教授"
    assert preds.get("affiliated_with") == "北京大学"

    # 4. Positive Example 2: 周昕，现任北京大学教授 (comma boundary)
    text_pos2 = "周昕，现任北京大学教授"
    ev4 = make_evidence(text_pos2, ev_id="EV-POS-2")
    m4 = extract_mentions_and_aliases(ev4.source_id, text_pos2, target_name="周昕", evidence_id=ev4.evidence_id)
    assert len(m4) == 1 and m4[0].raw_name_text == "周昕"


def test_clause_internal_competing_subject_rejects_pro_drop():
    """
    P0 Unit Test:
    Verifies that a clause with an explicit third-party person subject
    (e.g. '随后张伟荣获 Nobel Prize') cannot be attributed via pro-drop anaphora
    to an antecedent target person (e.g. 李嘉文).
    """
    from scripts.score_candidates import check_5d_entailment

    # Counterexample: Zhang Wei wins Nobel Prize in the second clause
    ev_text = "李嘉文毕业于北京一零一中，随后张伟荣获 Nobel Prize。"
    sc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-1"],
        "support_clauses": [{
            "evidence_id": "EVI-1",
            "clause_span_start": 13,
            "clause_span_end": 32,
            "verbatim_clause": "随后张伟荣获 Nobel Prize",
            "subject_resolution": "pro_drop_anaphora",
            "antecedent_mention_id": "MEN-LJ",
            "antecedent_clause_span": [0, 12],
        }],
    }
    gc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "equivalence_set": ["Nobel Prize"],
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    evidence_map = {"EVI-1": {"evidence_id": "EVI-1", "source_id": "SRC-1", "verbatim_excerpt": ev_text, "char_start": 0, "char_end": len(ev_text)}}
    mention_map = {"MEN-LJ": {"mention_id": "MEN-LJ", "raw_name_text": "李嘉文", "evidence_id": "EVI-1", "char_start": 0, "char_end": 3}}
    valid_subjects = {"李嘉文"}

    is_entailed, is_attributed, is_temp = check_5d_entailment(sc, gc, evidence_map, valid_subjects, mention_map=mention_map)
    assert is_attributed is False, "Clause with explicit third-party subject '张伟' must NOT be attributed to 李嘉文"
    assert is_entailed is False

    # Valid positive: Pro-drop directly following without competing subject
    sc_valid = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-1"],
        "support_clauses": [{
            "evidence_id": "EVI-1",
            "clause_span_start": 13,
            "clause_span_end": 30,
            "verbatim_clause": "随后荣获 Nobel Prize",
            "subject_resolution": "pro_drop_anaphora",
            "antecedent_mention_id": "MEN-LJ",
            "antecedent_clause_span": [0, 12],
        }],
    }
    ev_map_valid = {"EVI-1": {"evidence_id": "EVI-1", "source_id": "SRC-1", "verbatim_excerpt": "李嘉文毕业于北京一零一中，随后荣获 Nobel Prize。", "char_start": 0, "char_end": 31}}
    is_ent, is_attr, is_t = check_5d_entailment(sc_valid, gc, ev_map_valid, valid_subjects, mention_map=mention_map)
    assert is_attr is True
    assert is_ent is True


def test_pronoun_anaphora_distance_and_paragraph_boundary():
    """
    P0/P1 Unit Test:
    Verifies that pronoun anaphora enforces paragraph boundaries (no \n\n or HTML block tags),
    sentence limits (at most 1 sentence boundary), and maximum character distance (<= 50 chars).
    """
    from scripts.score_candidates import check_5d_entailment

    gc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "equivalence_set": ["Nobel Prize"],
        "polarity": "affirmative",
        "temporal_status": "current",
    }

    # 1. Distant pronoun after 80 sentences -> BLOCKED
    ev_text_distant = "Alice graduated from MIT. " + "Sentence. " * 80 + "She received the Nobel Prize."
    ante_end = len("Alice graduated from MIT.")
    clause_start = ev_text_distant.find("She received the Nobel Prize.")
    sc_distant = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-D"],
        "support_clauses": [{
            "evidence_id": "EVI-D",
            "clause_span_start": clause_start,
            "clause_span_end": len(ev_text_distant),
            "verbatim_clause": "She received the Nobel Prize.",
            "subject_resolution": "pronoun_anaphora",
            "antecedent_mention_id": "MEN-A",
            "antecedent_clause_span": [0, ante_end],
        }],
    }
    ev_map_distant = {"EVI-D": {"evidence_id": "EVI-D", "source_id": "SRC-D", "verbatim_excerpt": ev_text_distant, "char_start": 0, "char_end": len(ev_text_distant)}}
    m_map_distant = {"MEN-A": {"mention_id": "MEN-A", "raw_name_text": "Alice", "evidence_id": "EVI-D", "char_start": 0, "char_end": 5}}
    is_ent, is_attr, _ = check_5d_entailment(sc_distant, gc, ev_map_distant, {"Alice"}, mention_map=m_map_distant)
    assert is_attr is False, "Pronoun 80 sentences away must be rejected"
    assert is_ent is False

    # 2. Pronoun across paragraph boundary (\n\n) -> BLOCKED
    ev_text_para = "Alice graduated from MIT.\n\nShe received the Nobel Prize."
    ante_end_p = len("Alice graduated from MIT.")
    clause_start_p = ev_text_para.find("She received the Nobel Prize.")
    sc_para = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-P"],
        "support_clauses": [{
            "evidence_id": "EVI-P",
            "clause_span_start": clause_start_p,
            "clause_span_end": len(ev_text_para),
            "verbatim_clause": "She received the Nobel Prize.",
            "subject_resolution": "pronoun_anaphora",
            "antecedent_mention_id": "MEN-A",
            "antecedent_clause_span": [0, ante_end_p],
        }],
    }
    ev_map_para = {"EVI-P": {"evidence_id": "EVI-P", "source_id": "SRC-P", "verbatim_excerpt": ev_text_para, "char_start": 0, "char_end": len(ev_text_para)}}
    m_map_para = {"MEN-A": {"mention_id": "MEN-A", "raw_name_text": "Alice", "evidence_id": "EVI-P", "char_start": 0, "char_end": 5}}
    is_ent_p, is_attr_p, _ = check_5d_entailment(sc_para, gc, ev_map_para, {"Alice"}, mention_map=m_map_para)
    assert is_attr_p is False, "Pronoun across paragraph boundary must be rejected"
    assert is_ent_p is False

    # 3. Valid adjacent sentence pronoun -> ALLOWED
    ev_text_valid = "Alice graduated from MIT. She received the Nobel Prize."
    ante_end_v = len("Alice graduated from MIT.")
    clause_start_v = ev_text_valid.find("She received the Nobel Prize.")
    sc_valid = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-V"],
        "support_clauses": [{
            "evidence_id": "EVI-V",
            "clause_span_start": clause_start_v,
            "clause_span_end": len(ev_text_valid),
            "verbatim_clause": "She received the Nobel Prize.",
            "subject_resolution": "pronoun_anaphora",
            "antecedent_mention_id": "MEN-A",
            "antecedent_clause_span": [0, ante_end_v],
        }],
    }
    ev_map_valid = {"EVI-V": {"evidence_id": "EVI-V", "source_id": "SRC-V", "verbatim_excerpt": ev_text_valid, "char_start": 0, "char_end": len(ev_text_valid)}}
    m_map_valid = {"MEN-A": {"mention_id": "MEN-A", "raw_name_text": "Alice", "evidence_id": "EVI-V", "char_start": 0, "char_end": 5}}
    is_ent_v, is_attr_v, _ = check_5d_entailment(sc_valid, gc, ev_map_valid, {"Alice"}, mention_map=m_map_valid)
    assert is_attr_v is True
    assert is_ent_v is True


def test_pronoun_nearest_compatible_antecedent_rejects_distractor_object():
    """
    P0 Red Test:
    In 'Alice Smith met Bob Jones. He was awarded Nobel Prize.',
    the pronoun 'He' must NOT bind to Alice Smith because:
    1) Gender incompatibility ('He' is masculine, 'Alice Smith' is female).
    2) Nearest antecedent is 'Bob Jones' (in object position of preceding sentence).
    Extractor must not generate awarded_honor: Nobel Prize for Alice.
    Scorer 5D entailment must reject attribution to Alice.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from scripts.score_candidates import check_5d_entailment

    text = "Alice Smith met Bob Jones. He was awarded Nobel Prize."
    ev = make_evidence(text, ev_id="EV-ALICE-BOB")

    # 1. Extractor test: target is Alice Smith
    claims = extract_claims_from_evidence(
        ev,
        candidate_entity_id="CAND-ALICE",
        target_name="Alice Smith",
    )
    alice_nobel = [c for c in claims if c.predicate == "awarded_honor" and "Nobel" in c.object_raw]
    assert len(alice_nobel) == 0, f"Extractor erroneously attributed Nobel Prize to Alice Smith: {alice_nobel}"

    # 2. Scorer test: Claim for Alice pointing to 'He was awarded Nobel Prize.'
    clause_start = text.find("He was awarded Nobel Prize.")
    sc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EV-ALICE-BOB"],
        "support_clauses": [{
            "evidence_id": "EV-ALICE-BOB",
            "clause_span_start": clause_start,
            "clause_span_end": len(text),
            "verbatim_clause": "He was awarded Nobel Prize.",
            "subject_resolution": "pronoun_anaphora",
            "antecedent_mention_id": "MEN-ALICE",
            "antecedent_clause_span": [0, text.find(".")],
        }],
    }
    gc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "equivalence_set": ["Nobel Prize"],
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    ev_map = {"EV-ALICE-BOB": {"evidence_id": "EV-ALICE-BOB", "source_id": "SRC-1", "verbatim_excerpt": text, "char_start": 0, "char_end": len(text)}}
    m_map = {"MEN-ALICE": {"mention_id": "MEN-ALICE", "raw_name_text": "Alice Smith", "evidence_id": "EV-ALICE-BOB", "char_start": 0, "char_end": 11}}
    valid_subjects = {"Alice Smith"}

    is_ent, is_attr, _ = check_5d_entailment(sc, gc, ev_map, valid_subjects, mention_map=m_map)
    assert is_attr is False, "Scorer erroneously attributed 'He was awarded Nobel Prize.' to Alice Smith when Bob Jones intervened"
    assert is_ent is False


def test_chinese_cleft_post_predicate_subject_rejects_target_attribution():
    """
    P0 Red Test:
    In '李嘉文毕业于北京一零一中，随后荣获 Nobel Prize 的是张伟。',
    the cleft / post-predicate structure '的是张伟' makes Zhang Wei the subject of the Nobel Prize.
    Extractor must not generate awarded_honor: Nobel Prize for 李嘉文.
    Scorer 5D entailment must reject attribution to 李嘉文.
    """
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from scripts.score_candidates import check_5d_entailment

    text = "李嘉文毕业于北京一零一中，随后荣获 Nobel Prize 的是张伟。"
    ev = make_evidence(text, ev_id="EV-LJ-ZW")

    # 1. Extractor test: target is 李嘉文
    claims = extract_claims_from_evidence(
        ev,
        candidate_entity_id="CAND-LJ",
        target_name="李嘉文",
    )
    lj_nobel = [c for c in claims if c.predicate == "awarded_honor" and "Nobel" in c.object_raw]
    assert len(lj_nobel) == 0, f"Extractor erroneously attributed Nobel Prize to 李嘉文 in cleft sentence: {lj_nobel}"

    # 2. Scorer test
    clause_start = text.find("随后荣获")
    sc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EV-LJ-ZW"],
        "support_clauses": [{
            "evidence_id": "EV-LJ-ZW",
            "clause_span_start": clause_start,
            "clause_span_end": len(text) - 1,
            "verbatim_clause": "随后荣获 Nobel Prize 的是张伟",
            "subject_resolution": "pro_drop_anaphora",
            "antecedent_mention_id": "MEN-LJ",
            "antecedent_clause_span": [0, 12],
        }],
    }
    gc = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "equivalence_set": ["Nobel Prize"],
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    ev_map = {"EV-LJ-ZW": {"evidence_id": "EV-LJ-ZW", "source_id": "SRC-1", "verbatim_excerpt": text, "char_start": 0, "char_end": len(text)}}
    m_map = {"MEN-LJ": {"mention_id": "MEN-LJ", "raw_name_text": "李嘉文", "evidence_id": "EV-LJ-ZW", "char_start": 0, "char_end": 3}}
    valid_subjects = {"李嘉文"}

    is_ent, is_attr, _ = check_5d_entailment(sc, gc, ev_map, valid_subjects, mention_map=m_map)
    assert is_attr is False, "Scorer erroneously attributed Nobel Prize to 李嘉文 when post-predicate subject is 张伟"
    assert is_ent is False


def test_chinese_name_recall_on_varied_predicates():
    """
    P1 Red Test:
    Verifies that Chinese person name mention extraction does NOT drop recall on varied predicates:
    - 周昕接受采访。 -> 1 mention
    - 周昕参与研究。 -> 1 mention
    - 周昕领导团队。 -> 1 mention
    - 周昕发表论文。 -> 1 mention
    And still correctly rejects counterexamples:
    - 周昕怡现任北京大学教授。 -> 0 mentions for 周昕
    - 李嘉文博荣获 Nobel Prize。 -> 0 mentions for 李嘉文
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases

    cases = [
        ("周昕接受采访。", "周昕", 1),
        ("周昕参与研究。", "周昕", 1),
        ("周昕领导团队。", "周昕", 1),
        ("周昕发表论文。", "周昕", 1),
        ("周昕怡现任北京大学教授。", "周昕", 0),
        ("李嘉文博荣获 Nobel Prize。", "李嘉文", 0),
    ]
    for text, target, expected_count in cases:
        mentions = extract_mentions_and_aliases("SRC-TEST", text, target_name=target, evidence_id="EV-TEST")
        matching = [m for m in mentions if m.raw_name_text == target]
        assert len(matching) == expected_count, (
            f"Expected {expected_count} mentions of '{target}' in '{text}', got {len(matching)}: {mentions}"
        )


def test_target_name_prefix_collision_rejects_longer_surname():
    """
    P0 Red Test:
    Verifies that target name prefix collision (e.g. Alice Smith vs Alice Smithson)
    does NOT attribute facts of Alice Smithson to Alice Smith.
    Text: 'Alice Smith met Alice Smithson. She was awarded Nobel Prize.'
    Extractor must NOT attribute 'awarded_honor: Nobel Prize' to Alice Smith.
    Scorer 5D entailment must return is_entailed=False, is_attributed=False.
    """
    from models.schemas import Evidence
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from scripts.score_candidates import check_5d_entailment

    text = "Alice Smith met Alice Smithson. She was awarded Nobel Prize."
    evi = Evidence(
        evidence_id="EV-COLLISION-01",
        source_id="SRC-COLLISION-01",
        verbatim_excerpt=text,
        locator={"locator_type": "css", "selector_or_page": "body"},
        retrieved_at="2026-09-17T00:00:00Z",
        source_quality_class="class_a",
        raw_payload_sha256="c" * 64,
    )

    claims = extract_claims_from_evidence(evi, target_name="Alice Smith")
    nobel_claims = [c for c in claims if c.predicate == "awarded_honor"]
    assert len(nobel_claims) == 0, f"Expected 0 Nobel Prize claims for Alice Smith, got: {nobel_claims}"

    # Verify 5D entailment checker also rejects attribution to Alice Smith
    mock_system_claim = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EV-COLLISION-01"],
        "support_clauses": [
            {
                "evidence_id": "EV-COLLISION-01",
                "clause_span_start": 32,
                "clause_span_end": 59,
                "verbatim_clause": "She was awarded Nobel Prize",
                "relation_span_start": 4,
                "relation_span_end": 27,
                "provenance_level": "relation",
                "subject_resolution": "pronoun_anaphora",
                "antecedent_mention_id": "MEN-ALICE-01",
                "antecedent_clause_span": [0, 31],
            }
        ],
    }
    gold_claim = {
        "predicate": "awarded_honor",
        "object_raw": "Nobel Prize",
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    ev_map = {
        "EV-COLLISION-01": {
            "evidence_id": "EV-COLLISION-01",
            "source_id": "SRC-COLLISION-01",
            "verbatim_excerpt": text,
            "char_start": 0,
            "char_end": len(text),
        }
    }
    mention_map = {
        "MEN-ALICE-01": {
            "mention_id": "MEN-ALICE-01",
            "raw_name_text": "Alice Smith",
            "evidence_id": "EV-COLLISION-01",
            "char_start": 0,
            "char_end": 11,
        }
    }

    is_ent, is_attr, is_temp = check_5d_entailment(
        mock_system_claim, gold_claim, ev_map, valid_subjects={"Alice Smith"}, mention_map=mention_map
    )
    assert is_attr is False, "5D entailment must reject attribution of Nobel Prize to Alice Smith when nearest antecedent is Alice Smithson"
    assert is_ent is False


def test_gpe_and_award_capitalized_phrases_not_competing_antecedents():
    """
    P1 Red Test:
    Verifies that capitalized place names (New Haven, North Carolina) or awards (Nobel Prize)
    are recognized as GPE/AWARD and do NOT compete as person antecedents.
    Text: 'Alice Smith moved to New Haven. She was awarded Nobel Prize.'
    Extractor MUST attribute 'awarded_honor: Nobel Prize' to Alice Smith.
    """
    from models.schemas import Evidence
    from core.extractors.claim_extractor import extract_claims_from_evidence

    t1 = "Alice Smith moved to New Haven. She was awarded Nobel Prize."
    ev1 = Evidence(
        evidence_id="EV-GPE-01",
        source_id="SRC-GPE-01",
        verbatim_excerpt=t1,
        locator={"locator_type": "css", "selector_or_page": "body"},
        retrieved_at="2026-09-17T00:00:00Z",
        source_quality_class="class_a",
        raw_payload_sha256="d" * 64,
    )
    claims1 = extract_claims_from_evidence(ev1, target_name="Alice Smith")
    nobel1 = [c for c in claims1 if c.predicate == "awarded_honor" and "nobel" in c.object_raw.lower()]
    assert len(nobel1) == 1, f"Expected 1 Nobel Prize claim for Alice Smith, got: {claims1}"

    t2 = "Alice Smith moved to North Carolina. She was awarded Nobel Prize."
    ev2 = Evidence(
        evidence_id="EV-GPE-02",
        source_id="SRC-GPE-02",
        verbatim_excerpt=t2,
        locator={"locator_type": "css", "selector_or_page": "body"},
        retrieved_at="2026-09-17T00:00:00Z",
        source_quality_class="class_a",
        raw_payload_sha256="e" * 64,
    )
    claims2 = extract_claims_from_evidence(ev2, target_name="Alice Smith")
    nobel2 = [c for c in claims2 if c.predicate == "awarded_honor" and "nobel" in c.object_raw.lower()]
    assert len(nobel2) == 1, f"Expected 1 Nobel Prize claim for Alice Smith, got: {claims2}"


def test_chinese_open_predicates_unlisted_verbs_extracted():
    """
    P1 Red Test:
    Verifies that Chinese person names are extracted on unlisted open predicates:
    - 周昕倡导改革。 -> 1 mention
    - 周昕创建实验室。 -> 1 mention
    - 周昕完成研究。 -> 1 mention
    - 周昕研制新型芯片。 -> 1 mention
    And still rejects longer name prefixes:
    - 周昕怡现任北京大学教授。 -> 0 mentions for 周昕
    - 李嘉文博荣获 Nobel Prize。 -> 0 mentions for 李嘉文
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases

    cases = [
        ("周昕倡导改革。", "周昕", 1),
        ("周昕创建实验室。", "周昕", 1),
        ("周昕完成研究。", "周昕", 1),
        ("周昕研制新型芯片。", "周昕", 1),
        ("周昕怡现任北京大学教授。", "周昕", 0),
        ("李嘉文博荣获 Nobel Prize。", "李嘉文", 0),
    ]
    for text, target, expected_count in cases:
        mentions = extract_mentions_and_aliases("SRC-TEST", text, target_name=target, evidence_id="EV-TEST")
        matching = [m for m in mentions if m.raw_name_text == target]
        assert len(matching) == expected_count, (
            f"Expected {expected_count} mentions of '{target}' in '{text}', got {len(matching)}: {mentions}"
        )


def test_cross_cultural_name_unknown_veto_blocker():
    """
    P0 Regression Test:
    Verifies that:
    1. Cross-cultural / pinyin names (e.g. 'Xin Zhou') are recognized as persons and block earlier targets.
    2. Unknown capitalized person-like entities ('Adewale Akintola') act as veto-only blockers:
       they prevent binding an earlier target ('David Jones'), but if the unknown entity is the target itself,
       it can be bound.
    """
    from core.extractors.subject_attribution import build_person_mention_universe, resolve_pronoun_antecedent

    # 1. 'David Jones met Xin Zhou. He was awarded Nobel Prize.'
    t1 = "David Jones met Xin Zhou. He was awarded Nobel Prize."
    m1 = build_person_mention_universe(t1, known_persons=["David Jones"])
    is_bound1, resolved1 = resolve_pronoun_antecedent("He", t1.find("He"), t1, {"David Jones"}, m1)
    assert not is_bound1, f"David Jones must NOT be bound across Xin Zhou! Resolved: {resolved1}"
    assert resolved1 == "Xin Zhou"

    # 2. Intervening UNKNOWN person-like entity acts as veto blocker
    t2 = "David Jones met Adewale Akintola. He was awarded Nobel Prize."
    m2 = build_person_mention_universe(t2, known_persons=["David Jones"])
    is_bound2, resolved2 = resolve_pronoun_antecedent("He", t2.find("He"), t2, {"David Jones"}, m2)
    assert not is_bound2, f"David Jones must NOT be bound across intervening unknown person entity! Resolved: {resolved2}"
    assert resolved2 == "Adewale Akintola"

    # 3. If Adewale Akintola is the target himself, pronoun binds correctly
    t3 = "Adewale Akintola was educated at Oxford. He was awarded Nobel Prize."
    m3 = build_person_mention_universe(t3, known_persons=["Adewale Akintola"])
    is_bound3, resolved3 = resolve_pronoun_antecedent("He", t3.find("He"), t3, {"Adewale Akintola"}, m3)
    assert is_bound3, "Adewale Akintola as target must be bound to He"
    assert resolved3 == "Adewale Akintola"


def test_gpe_and_award_priority_does_not_override_person():
    """
    P0 Regression Test:
    Verifies that intrinsic person evidence takes precedence over fuzzy GPE and AWARD rules:
    - 'Barbara Jones' preceded by 'visited' is classified as PERSON, not GPE.
    - 'Grant Hill' is classified as PERSON, not AWARD.
    - 'New Haven' remains GPE and does not block person coreference.
    """
    from core.extractors.subject_attribution import build_person_mention_universe, resolve_pronoun_antecedent

    # 1. Barbara Jones preceded by 'visited'
    t1 = "Alice Smith visited Barbara Jones. She was awarded Nobel Prize."
    m1 = build_person_mention_universe(t1, known_persons=["Alice Smith"])
    barbara_entry = next((m for m in m1 if m["name"] == "Barbara Jones"), None)
    assert barbara_entry is not None, "Barbara Jones must be detected in mention universe"
    assert barbara_entry["entity_type"] == "PERSON", f"Barbara Jones must be PERSON, got {barbara_entry['entity_type']}"
    is_bound1, resolved1 = resolve_pronoun_antecedent("She", t1.find("She"), t1, {"Alice Smith"}, m1)
    assert not is_bound1, "Alice Smith must NOT be bound across intervening Barbara Jones"
    assert resolved1 == "Barbara Jones"

    # 2. Grant Hill contains 'grant'
    t2 = "David Jones met Grant Hill. He was awarded Nobel Prize."
    m2 = build_person_mention_universe(t2, known_persons=["David Jones"])
    grant_entry = next((m for m in m2 if m["name"] == "Grant Hill"), None)
    assert grant_entry is not None, "Grant Hill must be detected in mention universe"
    assert grant_entry["entity_type"] == "PERSON", f"Grant Hill must be PERSON, got {grant_entry['entity_type']}"
    is_bound2, resolved2 = resolve_pronoun_antecedent("He", t2.find("He"), t2, {"David Jones"}, m2)
    assert not is_bound2, "David Jones must NOT be bound across intervening Grant Hill"
    assert resolved2 == "Grant Hill"

    # 3. New Haven is GPE and does not block
    t3 = "Alice Smith moved to New Haven. She was awarded Nobel Prize."
    m3 = build_person_mention_universe(t3, known_persons=["Alice Smith"])
    is_bound3, resolved3 = resolve_pronoun_antecedent("She", t3.find("She"), t3, {"Alice Smith"}, m3)
    assert is_bound3, "Alice Smith must be bound across non-person GPE New Haven"
    assert resolved3 == "Alice Smith"


def test_honorific_surname_not_auto_alias_without_verification():
    """
    P0 Regression Test:
    Verifies that 'Dr. Zhou' is NOT automatically treated as an alias for 'Xin Zhou':
    - 'Xin Zhou met Ming Zhou. Dr. Zhou was awarded Nobel Prize.'
    Without verified aliases, Dr. Zhou does not match Xin Zhou.
    With explicit verified alias ['Dr. Zhou'], it matches.
    """
    from core.extractors.subject_attribution import is_exact_or_verified_alias_match
    from core.extractors.mention_extractor import extract_mentions_and_aliases

    # 1. Matching function rejects bare honorific surname without explicit verification
    assert not is_exact_or_verified_alias_match("Dr. Zhou", {"Xin Zhou"}), (
        "Dr. Zhou must NOT match Xin Zhou without explicit alias"
    )
    assert is_exact_or_verified_alias_match("Dr. Zhou", {"Xin Zhou"}, known_aliases=["Dr. Zhou"]), (
        "Dr. Zhou must match Xin Zhou when explicitly verified in known_aliases"
    )

    # 2. Claim extractor does not automatically attribute Dr. Zhou to Xin Zhou
    from core.extractors.claim_extractor import extract_claims_from_evidence
    from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass
    from datetime import datetime, timezone

    ev = Evidence(
        evidence_id="EV-1",
        source_id="SRC-1",
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="p"),
        exact_text="Xin Zhou met Ming Zhou. Dr. Zhou was awarded Nobel Prize.",
        verbatim_excerpt="Xin Zhou met Ming Zhou. Dr. Zhou was awarded Nobel Prize.",
        char_offset_start=0,
        char_offset_end=56,
        quality_class=SourceQualityClass.CLASS_A,
        retrieved_at=datetime.now(timezone.utc),
    )
    claims = extract_claims_from_evidence(ev, target_name="Xin Zhou")
    # Xin Zhou must NOT receive Nobel Prize claim from Dr. Zhou clause
    nobel_claims = [c for c in claims if "nobel" in c.object_raw.lower()]
    assert len(nobel_claims) == 0, f"Dr. Zhou clause must not attribute Nobel Prize to Xin Zhou! Got: {nobel_claims}"


def test_chinese_maximal_span_and_predicate_counterexamples():
    """
    P0/P1 Regression Test:
    Verifies Chinese maximal candidate span and predicate morpheme boundaries:
    - 周昕批评政策。 -> 1 mention for 周昕
    - 周昕怡批评政策。 -> 0 mentions for 周昕 (周昕怡 is a longer name)
    - 李嘉文博批评政策。 -> 0 mentions for 李嘉文 (李嘉文博 is a longer name)
    - 周昕批评。 -> 1 mention for 周昕
    """
    from core.extractors.mention_extractor import extract_mentions_and_aliases

    cases = [
        ("周昕批评政策。", "周昕", 1),
        ("周昕怡批评政策。", "周昕", 0),
        ("李嘉文博批评政策。", "李嘉文", 0),
        ("周昕批评。", "周昕", 1),
    ]
    for text, target, expected_count in cases:
        mentions = extract_mentions_and_aliases("SRC-TEST", text, target_name=target, evidence_id="EV-TEST")
        matching = [m for m in mentions if m.raw_name_text == target]
        assert len(matching) == expected_count, (
            f"Expected {expected_count} mentions of '{target}' in '{text}', got {len(matching)}: {mentions}"
        )









