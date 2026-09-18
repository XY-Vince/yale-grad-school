"""
V4.5 Targeted Regression Test Suite.
Verifies all 11 audited defects and specifications:
  1. test_syntax_role_binding_transitive_action (prevents "Alice interviewed Dean Bob" from attributing Dean to Alice)
  2. test_pinyin_single_syllable_false_merge_rejected (prevents "Xin Zhou" and "周悦" false merge)
  3. test_pairwise_precision_zero_retrieval_convention (when tp+fp=0, precision is 0.0 if fn>0, 1.0 if fn=0)
  4. test_gold_claim_recall_gate_tripped (trips gate when gold claims are not all recalled)
  5. test_dossier_markdown_multi_candidate_isolation (prevents Candidate B claims under Candidate A)
  6. test_state_machine_s1_through_s7_outcomes (full coverage of determine_state_outcome)
  7. test_evidence_excerpt_substring_closure (support_clauses must be authentic substring of evidence)
  8. test_mention_evidence_id_anchor (EntityMention must have non-empty evidence_id matching evidence)
"""

import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from benchmarks.tools.er_metrics import compute_pairwise
from core.extractors.claim_extractor import extract_claims_from_evidence
from core.render_dossier import render_dossier_markdown
from core.resolver import check_full_pinyin_match, compute_pairwise_name_similarity, resolve_mentions
from core.run_profile import determine_state_outcome
from models.schemas import (
    AdjudicationStatus,
    CandidateEntity,
    Claim,
    ClaimEvidenceSupport,
    ClusterAssignment,
    ClusteringMethod,
    Dossier,
    DossierStatement,
    EntityMention,
    Evidence,
    EvidenceLocator,
    FactPolarity,
    LocatorType,
    MachineRelation,
    RunManifest,
    OriginType,
    RunOutcome,
    SourceQualityClass,
    SourceSnapshot,
    TemporalStatus,
    VerificationStatus,
)
from scripts.score_candidates import check_5d_entailment, evaluate_dossier_bundle
from scripts.validate_dossier import validate_bundle


def test_syntax_role_binding_transitive_action():
    """Validates that transitive distractor roles are not attributed to the subject."""
    sc_distractor = {
        "claim_id": "CLM-DISTRACTOR-01",
        "predicate": "holds_position",
        "object_raw": "Dean",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-01"],
        "support_clauses": [
            {
                "evidence_id": "EVI-01",
                "verbatim_clause": "Alice interviewed Dean Bob yesterday at the faculty center.",
            }
        ],
    }
    gc = {
        "predicate": "holds_position",
        "object_raw": "Dean",
        "equivalence_set": ["Dean", "School Dean"],
        "polarity": "affirmative",
        "temporal_status": "current",
    }
    ev_map = {
        "EVI-01": {
            "evidence_id": "EVI-01",
            "verbatim_excerpt": "Alice interviewed Dean Bob yesterday at the faculty center.",
        }
    }
    is_entailed, is_attr, is_temp = check_5d_entailment(
        sc_distractor, gc, ev_map, valid_subjects={"alice"}
    )
    assert not is_entailed, "Transitive distractor ('Alice interviewed Dean Bob') was falsely entailed to Alice!"

    # Legitimate assertion where Alice is the actual Dean
    sc_legit = {
        "claim_id": "CLM-LEGIT-01",
        "predicate": "holds_position",
        "object_raw": "Dean",
        "polarity": "affirmative",
        "temporal_status": "current",
        "evidence_ids": ["EVI-02"],
        "support_clauses": [
            {
                "evidence_id": "EVI-02",
                "verbatim_clause": "Alice is the Dean of the School of Medicine.",
            }
        ],
    }
    ev_map["EVI-02"] = {
        "evidence_id": "EVI-02",
        "verbatim_excerpt": "Alice is the Dean of the School of Medicine.",
    }
    is_entailed_legit, _, _ = check_5d_entailment(
        sc_legit, gc, ev_map, valid_subjects={"alice"}
    )
    assert is_entailed_legit, "Direct copular role ('Alice is the Dean') failed entailment check!"


def test_pinyin_single_syllable_false_merge_rejected():
    """Validates that single syllable match does not bridge distinct Chinese names."""
    m_latin = EntityMention(
        mention_id="M-LATIN-01",
        raw_name_text="Xin Zhou",
        source_id="S-01",
        evidence_id="EVI-01",
        context_snippet="Xin Zhou is a Professor at Tsinghua University.",
        char_start=0,
        char_end=8,
        mention_key="k_latin",
    )
    m_zh_diff = EntityMention(
        mention_id="M-ZH-01",
        raw_name_text="周悦",
        source_id="S-02",
        evidence_id="EVI-02",
        context_snippet="周悦 教授 清华大学",
        char_start=0,
        char_end=2,
        mention_key="k_zh",
    )
    assert not check_full_pinyin_match("周悦", "Xin Zhou"), "Single syllable 'zhou' falsely matched full name '周悦'!"

    sim, match_type = compute_pairwise_name_similarity(m_latin, m_zh_diff)
    assert sim < 0.50 or match_type != "verified_alias", f"Expected unverified/non-match, got sim={sim}, type={match_type}"


def test_pairwise_precision_zero_retrieval_convention():
    """Validates precision convention: 0.0 when tp+fp=0 and fn>0; 1.0 when tp=fp=fn=0."""
    gold_clusters_with_pairs = [["M1", "M2", "M3"]]
    sys_clusters_singletons = [["M1"], ["M2"], ["M3"]]
    all_mentions = ["M1", "M2", "M3"]

    res1 = compute_pairwise(gold_clusters_with_pairs, sys_clusters_singletons, all_mentions)
    assert res1["tp"] == 0
    assert res1["fp"] == 0
    assert res1["fn"] > 0
    assert res1["pairwise_precision"] == 0.0, f"Expected 0.0 precision on zero retrieval with positive gold pairs, got {res1['pairwise_precision']}"

    gold_clusters_singletons = [["M1"], ["M2"], ["M3"]]
    res2 = compute_pairwise(gold_clusters_singletons, sys_clusters_singletons, all_mentions)
    assert res2["tp"] == 0
    assert res2["fp"] == 0
    assert res2["fn"] == 0
    assert res2["pairwise_precision"] == 1.0, f"Expected 1.0 precision when both gold and sys have 0 pairs, got {res2['pairwise_precision']}"


def test_gold_claim_recall_gate_tripped():
    """Validates that gold_claim_recall_gate trips when system fails to recall all gold claims."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir) / "test_bundle"
        bundle_dir.mkdir()

        manifest = RunManifest(
            run_id="RUN-TEST-01",
            run_outcome=RunOutcome.COMPLETED,
            run_fingerprint="abc",
            tool_version="verify-public-person-profile/1.0.0",
            model_name="deterministic_pipeline",
            query_budget=10,
            queries_executed=2,
            pages_fetched=1,
            execution_time_seconds=0.1,
        )
        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        source = SourceSnapshot(
            source_id="SRC-01",
            url="https://example.edu/faculty/alice",
            publisher="example.edu",
            content_sha256="sha123",
            http_status=200,
        )
        with open(bundle_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(source.model_dump_json() + "\n")

        excerpt = "Dr. Alice Smith is a Professor of Computer Science at Stanford University."
        evidence = Evidence(
            evidence_id="EVI-01",
            source_id="SRC-01",
            verbatim_excerpt=excerpt,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
            raw_payload_sha256="sha123",
            char_start=0,
            char_end=len(excerpt),
        )
        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(evidence.model_dump_json() + "\n")

        mention = EntityMention(
            mention_id="MEN-01",
            raw_name_text="Alice Smith",
            source_id="SRC-01",
            evidence_id="EVI-01",
            context_snippet=excerpt,
            char_start=4,
            char_end=15,
            mention_key=hashlib.sha256(b"SRC-01:4:15").hexdigest()[:16],
        )
        with open(bundle_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            f.write(mention.model_dump_json() + "\n")

        cluster = ClusterAssignment(
            cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            clustering_method=ClusteringMethod.CONSTRAINED_UNION_FIND,
            threshold_used=0.85,
        )
        with open(bundle_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(cluster.model_dump_json() + "\n")

        candidate = CandidateEntity(
            candidate_entity_id="CAND-01",
            primary_name="Alice Smith",
            proposed_cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            evidence_ids=["EVI-01"],
        )
        with open(bundle_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(candidate.model_dump_json() + "\n")

        # System only extracts 1 claim out of 2 gold claims
        claim1 = Claim(
            claim_id="CLM-01",
            candidate_entity_id="CAND-01",
            subject_mention_id="MEN-01",
            predicate="holds_position",
            object_raw="Professor of Computer Science",
            polarity=FactPolarity.AFFIRMATIVE,
            temporal_status=TemporalStatus.CURRENT,
            adjudication_status=AdjudicationStatus.UNRESOLVED,
            as_of=datetime.now(timezone.utc).date(),
            extraction_confidence=0.98,
            evidence_ids=["EVI-01"],
            support_clauses=[
                ClaimEvidenceSupport(
                    evidence_id="EVI-01",
                    subject_mention_id="MEN-01",
                    clause_span_start=0,
                    clause_span_end=len(excerpt),
                    verbatim_clause=excerpt,
                )
            ],
        )
        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            f.write(claim1.model_dump_json() + "\n")

        dossier = Dossier(
            dossier_id="DOS-01",
            candidate_entity_id="CAND-01",
            proposed_cluster_id="CLUST-01",
            statements=[
                DossierStatement(
                    statement_id="STMT-01",
                    section="Roles",
                    rendered_text="Professor",
                    backed_claim_ids=["CLM-01"],
                )
            ],
            generated_at=datetime.now(timezone.utc),
        )
        with open(bundle_dir / "dossier.json", "w", encoding="utf-8") as f:
            f.write(dossier.model_dump_json(indent=2))

        with open(bundle_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            f.write("")
        with open(bundle_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier: Alice Smith\n")

        gold = {
            "case_id": "test_recall_trip",
            "target_name": "Alice Smith",
            "track": "frozen_corpus",
            "gold_claims": [
                {
                    "predicate": "holds_position",
                    "object_raw": "Professor of Computer Science",
                    "equivalence_set": ["Professor of Computer Science", "Professor"],
                },
                {
                    "predicate": "affiliated_with",
                    "object_raw": "Stanford University",
                    "equivalence_set": ["Stanford University"],
                },
            ],
            "gold_clusters": [["MEN-01"]],
        }
        gold_path = Path(tmp_dir) / "gold.json"
        with open(gold_path, "w", encoding="utf-8") as gf:
            json.dump(gold, gf, indent=2)

        eval_res = evaluate_dossier_bundle(bundle_dir, gold_path)
        assert not eval_res["gates"]["gold_claim_recall_gate"], "Gold claim recall gate should fail when only 1/2 gold claims recalled!"
        assert not eval_res["all_gates_passed"], "all_gates_passed must be False when recall gate fails!"


def test_dossier_markdown_multi_candidate_isolation():
    """Validates that multi-candidate dossier markdown cleanly isolates candidates."""
    cand1 = CandidateEntity(
        candidate_entity_id="CAND-A",
        primary_name="David Liam",
        proposed_cluster_id="CLUST-A",
        mention_ids=["MEN-A1"],
        evidence_ids=["EVI-A1"],
    )
    cand2 = CandidateEntity(
        candidate_entity_id="CAND-B",
        primary_name="David Liam",
        proposed_cluster_id="CLUST-B",
        mention_ids=["MEN-B1"],
        evidence_ids=["EVI-B1"],
    )

    claims = [
        Claim(
            claim_id="CLM-A1",
            candidate_entity_id="CAND-A",
            subject_mention_id="MEN-A1",
            predicate="affiliated_with",
            object_raw="Yale University",
            polarity=FactPolarity.AFFIRMATIVE,
            temporal_status=TemporalStatus.CURRENT,
            adjudication_status=AdjudicationStatus.UNRESOLVED,
            as_of=datetime.now(timezone.utc).date(),
            extraction_confidence=0.95,
            evidence_ids=["EVI-A1"],
            support_clauses=[ClaimEvidenceSupport(evidence_id="EVI-A1", subject_mention_id="MEN-A1", clause_span_start=0, clause_span_end=15, verbatim_clause="Yale University")],
        ),
        Claim(
            claim_id="CLM-B1",
            candidate_entity_id="CAND-B",
            subject_mention_id="MEN-B1",
            predicate="affiliated_with",
            object_raw="Harvard University",
            polarity=FactPolarity.AFFIRMATIVE,
            temporal_status=TemporalStatus.CURRENT,
            adjudication_status=AdjudicationStatus.UNRESOLVED,
            as_of=datetime.now(timezone.utc).date(),
            extraction_confidence=0.95,
            evidence_ids=["EVI-B1"],
            support_clauses=[ClaimEvidenceSupport(evidence_id="EVI-B1", subject_mention_id="MEN-B1", clause_span_start=0, clause_span_end=18, verbatim_clause="Harvard University")],
        ),
    ]

    dossier = Dossier(
        dossier_id="DOS-AMB-01",
        candidate_entity_id=None,
        proposed_cluster_id=None,
        statements=[],
        ambiguous_candidates=["CAND-A", "CAND-B"],
        generated_at=datetime.now(timezone.utc),
    )

    md = render_dossier_markdown(dossier, claims, person_name="David Liam", candidates=[cand1, cand2])

    assert "CAND-A" in md
    assert "CAND-B" in md
    assert "Yale University" in md
    assert "Harvard University" in md

    pos_cand_a = md.find("CAND-A")
    pos_cand_b = md.find("CAND-B")
    pos_yale = md.find("Yale University")
    pos_harvard = md.find("Harvard University")

    assert pos_cand_a < pos_yale < pos_cand_b < pos_harvard, "Claims leaked across candidate boundaries in rendered markdown!"


def test_state_machine_s1_through_s7_outcomes():
    """Validates state machine transitions across all 7 scenarios."""
    cand = CandidateEntity(
        candidate_entity_id="CAND-01",
        primary_name="Alice",
        proposed_cluster_id="CLUST-01",
        mention_ids=["MEN-01"],
        evidence_ids=["EVI-01"],
    )
    claim = Claim(
        claim_id="CLM-01",
        candidate_entity_id="CAND-01",
        subject_mention_id="MEN-01",
        predicate="holds_position",
        object_raw="Professor",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        adjudication_status=AdjudicationStatus.UNRESOLVED,
        as_of=datetime.now(timezone.utc).date(),
        extraction_confidence=0.95,
        evidence_ids=["EVI-01"],
        support_clauses=[ClaimEvidenceSupport(evidence_id="EVI-01", subject_mention_id="MEN-01", clause_span_start=0, clause_span_end=9, verbatim_clause="Professor")],
    )

    # S1: Insufficient Evidence (0 pages fetched)
    out1, _, _ = determine_state_outcome(has_structural_error=False, pages_fetched=0, claims=[])
    assert out1 == RunOutcome.INSUFFICIENT_EVIDENCE

    # S2: Collection Failed (non-200 / crawl errors on all fetched)
    out2, _, _ = determine_state_outcome(has_structural_error=False, crawl_errors=["403 Forbidden"], pages_fetched=0)
    assert out2 == RunOutcome.COLLECTION_FAILED

    # S3: Completed (Valid candidates and claims)
    out3, prim_id, _ = determine_state_outcome(has_structural_error=False, pages_fetched=2, candidates=[cand], claims=[claim])
    assert out3 == RunOutcome.COMPLETED
    assert prim_id == "CAND-01"

    # S4: Ambiguous Identity (is_ambiguous=True)
    out4, _, amb_ids = determine_state_outcome(has_structural_error=False, pages_fetched=2, candidates=[cand, CandidateEntity(candidate_entity_id="CAND-02", primary_name="Alice", proposed_cluster_id="CLUST-02", mention_ids=["MEN-02"], evidence_ids=["EVI-02"])], claims=[claim], is_ambiguous=True)
    assert out4 == RunOutcome.AMBIGUOUS_IDENTITY

    # S5: Budget Exhausted
    out5, _, _ = determine_state_outcome(has_structural_error=False, pages_fetched=2, claims=[], budget_exhausted=True)
    assert out5 == RunOutcome.BUDGET_EXHAUSTED

    # S6: Insufficient Evidence (Pages fetched but no claims)
    out6, _, _ = determine_state_outcome(has_structural_error=False, pages_fetched=2, claims=[])
    assert out6 == RunOutcome.INSUFFICIENT_EVIDENCE

    # S7: Structural Failure
    out7, _, _ = determine_state_outcome(has_structural_error=True, pages_fetched=2, candidates=[cand], claims=[claim])
    assert out7 == RunOutcome.FAILED


def test_evidence_excerpt_substring_closure():
    """Validates that validator flags error if verbatim clause is not a substring of evidence excerpt."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        b_dir = Path(tmp_dir) / "tampered_bundle"
        b_dir.mkdir()

        manifest = RunManifest(
            run_id="RUN-TAMPER-01",
            run_outcome=RunOutcome.COMPLETED,
            run_fingerprint="fp1",
            tool_version="verify-public-person-profile/1.0.0",
            model_name="deterministic_pipeline",
            query_budget=10,
            queries_executed=1,
            pages_fetched=1,
            execution_time_seconds=0.1,
        )
        with open(b_dir / "manifest.json", "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        source = SourceSnapshot(
            source_id="SRC-01",
            url="https://example.edu",
            publisher="example.edu",
            content_sha256="sha",
            http_status=200,
        )
        with open(b_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(source.model_dump_json() + "\n")

        evidence = Evidence(
            evidence_id="EVI-01",
            source_id="SRC-01",
            verbatim_excerpt="Alice is a lecturer at MIT.",
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
            raw_payload_sha256="sha",
            char_start=0,
            char_end=27,
        )
        with open(b_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(evidence.model_dump_json() + "\n")

        mention = EntityMention(
            mention_id="MEN-01",
            raw_name_text="Alice",
            source_id="SRC-01",
            evidence_id="EVI-01",
            context_snippet="Alice is a lecturer at MIT.",
            char_start=0,
            char_end=5,
            mention_key=hashlib.sha256(b"SRC-01:0:5").hexdigest()[:16],
        )
        with open(b_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            f.write(mention.model_dump_json() + "\n")

        cluster = ClusterAssignment(
            cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            clustering_method=ClusteringMethod.CONSTRAINED_UNION_FIND,
            threshold_used=0.85,
        )
        with open(b_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(cluster.model_dump_json() + "\n")

        candidate = CandidateEntity(
            candidate_entity_id="CAND-01",
            primary_name="Alice",
            proposed_cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            evidence_ids=["EVI-01"],
        )
        with open(b_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(candidate.model_dump_json() + "\n")

        fake_claim = Claim(
            claim_id="CLM-01",
            candidate_entity_id="CAND-01",
            subject_mention_id="MEN-01",
            predicate="holds_position",
            object_raw="President",
            polarity=FactPolarity.AFFIRMATIVE,
            temporal_status=TemporalStatus.CURRENT,
            adjudication_status=AdjudicationStatus.UNRESOLVED,
            as_of=datetime.now(timezone.utc).date(),
            extraction_confidence=0.98,
            evidence_ids=["EVI-01"],
            support_clauses=[
                ClaimEvidenceSupport(
                    evidence_id="EVI-01",
                    subject_mention_id="MEN-01",
                    clause_span_start=0,
                    clause_span_end=35,
                    verbatim_clause="Alice is the President of Harvard.",
                )
            ],
        )
        with open(b_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            f.write(fake_claim.model_dump_json() + "\n")

        dossier = Dossier(
            dossier_id="DOS-01",
            candidate_entity_id="CAND-01",
            proposed_cluster_id="CLUST-01",
            statements=[
                DossierStatement(
                    statement_id="STMT-01",
                    section="Roles",
                    rendered_text="President",
                    backed_claim_ids=["CLM-01"],
                )
            ],
            generated_at=datetime.now(timezone.utc),
        )
        with open(b_dir / "dossier.json", "w", encoding="utf-8") as f:
            f.write(dossier.model_dump_json(indent=2))

        with open(b_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            f.write("")
        with open(b_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier\n")

        res = validate_bundle(b_dir)
        assert not res["is_valid"]
        assert any("is not a substring of evidence" in err for err in res["errors"])


def test_mention_evidence_id_anchor():
    """Validates that EntityMention must have non-empty evidence_id matching evidence."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        b_dir = Path(tmp_dir) / "missing_anchor_bundle"
        b_dir.mkdir()

        manifest = RunManifest(
            run_id="RUN-ANCHOR-01",
            run_outcome=RunOutcome.COMPLETED,
            run_fingerprint="fp1",
            tool_version="verify-public-person-profile/1.0.0",
            model_name="deterministic_pipeline",
            query_budget=10,
            queries_executed=1,
            pages_fetched=1,
            execution_time_seconds=0.1,
        )
        with open(b_dir / "manifest.json", "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        source = SourceSnapshot(
            source_id="SRC-01",
            url="https://example.edu",
            publisher="example.edu",
            content_sha256="sha",
            http_status=200,
        )
        with open(b_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(source.model_dump_json() + "\n")

        evidence = Evidence(
            evidence_id="EVI-01",
            source_id="SRC-01",
            verbatim_excerpt="Alice is here.",
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
            raw_payload_sha256="sha",
            char_start=0,
            char_end=14,
        )
        with open(b_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(evidence.model_dump_json() + "\n")

        with open(b_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "mention_id": "MEN-01",
                "raw_name_text": "Alice",
                "source_id": "SRC-01",
                "evidence_id": "",
                "context_snippet": "Alice is here.",
            }) + "\n")

        cluster = ClusterAssignment(
            cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            clustering_method=ClusteringMethod.CONSTRAINED_UNION_FIND,
            threshold_used=0.85,
        )
        with open(b_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(cluster.model_dump_json() + "\n")

        candidate = CandidateEntity(
            candidate_entity_id="CAND-01",
            primary_name="Alice",
            proposed_cluster_id="CLUST-01",
            mention_ids=["MEN-01"],
            evidence_ids=["EVI-01"],
        )
        with open(b_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(candidate.model_dump_json() + "\n")

        with open(b_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            f.write("")

        dossier = Dossier(
            dossier_id="DOS-01",
            candidate_entity_id="CAND-01",
            proposed_cluster_id="CLUST-01",
            statements=[],
            generated_at=datetime.now(timezone.utc),
        )
        with open(b_dir / "dossier.json", "w", encoding="utf-8") as f:
            f.write(dossier.model_dump_json(indent=2))

        with open(b_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            f.write("")
        with open(b_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier\n")

        res = validate_bundle(b_dir)
        assert not res["is_valid"]
        assert any("evidence_id" in err for err in res["errors"])
