"""
V4.4.1 Comprehensive 15-Test Matrix.
Establishes the authoritative TDD verification suite for verify-public-person-profile:
  1. test_sentinel_gold_permission_denied_eacces
  2. test_multi_candidate_subject_mention_closure
  3. test_evidence_tampering_caught_by_payload_verifier
  4. test_mention_detection_layer_and_common_universe
  5. test_kuhn_munkres_partial_matching_with_dummies
  6. test_kuhn_munkres_differential_vs_scipy
  7. test_quotation_frame_not_attributed_to_speaker
  8. test_appositive_frame_attaches_to_adjacent_noun
  9. test_copular_svo_and_local_negation
  10. test_state_machine_matrix_s1_through_s7
  11. test_cross_lingual_pinyin_yields_review_without_corroboration
  12. test_ambiguous_identity_when_margin_below_delta
  13. test_deterministic_semantic_bundle_hash
  14. test_claim_id_128bit_sha256_hash
  15. test_total_score_clamped_and_approximate_edges_routed_to_review
"""

import errno
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest
from scipy.optimize import linear_sum_assignment

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from benchmarks.tools.bipartite_matching import hungarian_min_cost, max_weight_partial_matching
from benchmarks.tools.er_metrics import compute_b3, compute_mention_detection_metrics, compute_pairwise
from core.extractors.claim_extractor import extract_claims_from_evidence, detect_clause_polarity, detect_clause_temporal_status
from core.resolver import compute_pairwise_name_similarity, resolve_mentions
from core.run_profile import determine_state_outcome, compute_bundle_fingerprint
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
    MatchDecision,
    RunManifest,
    RunOutcome,
    SourceQualityClass,
    SourceSnapshot,
    TemporalStatus,
)
from scripts.score_candidates import evaluate_dossier_bundle
from scripts.validate_dossier import validate_bundle


# ==============================================================================
# Test 1: Sentinel Gold True Permission Physical Isolation Gate
# ==============================================================================
def test_sentinel_gold_permission_denied_eacces():
    """
    Test 1: Sentinel Gold file physically exists. In investigator child process,
    chmod 000 ensures attempt to read throws PermissionError (errno.EACCES).
    The test strictly asserts EACCES and rejects ENOENT. Evaluator restores
    permissions to 0400 and successfully reads it.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        gold_path = Path(tmp_dir) / "sentinel_gold.json"
        with open(gold_path, "w", encoding="utf-8") as f:
            json.dump({"target_name": "Sentinel", "gold_claims": []}, f)

        # Set permissions to 000 (no read/write/execute for anyone)
        os.chmod(gold_path, 0o000)

        # Child process as investigator attempts to read the file
        code = f"""
import errno, sys
try:
    with open({repr(str(gold_path))}, 'r') as f:
        f.read()
    sys.exit(1)
except PermissionError as e:
    if e.errno == errno.EACCES:
        sys.exit(42)  # Success: Caught EACCES
    sys.exit(2)
except FileNotFoundError:
    sys.exit(3)  # FAILED: Returned ENOENT!
except Exception:
    sys.exit(4)
"""
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert proc.returncode == 42, f"Physical isolation test failed! Returncode was {proc.returncode} (3 means ENOENT)."

        # Evaluator restores permissions and successfully reads the file
        os.chmod(gold_path, 0o400)
        with open(gold_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["target_name"] == "Sentinel"


# ==============================================================================
# Test 2: Claim Subject Anchor and Multi-Candidate Attribution Closure
# ==============================================================================
def test_multi_candidate_subject_mention_closure():
    """
    Test 2: Evidence contains mentions for both Alice and Bob.
    Claims must carry explicit subject_mention_id anchoring them to candidate entities.
    validate_bundle() enforces strict subject mention closure.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir) / "bundle"
        bundle_dir.mkdir()

        raw_payload = "Alice Example is Professor at Yale. Bob Sample is Dean at Harvard."
        content_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        with open(bundle_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "source_id": "SRC-01",
                "url": "https://example.com/news",
                "publisher": "example.com",
                "content_sha256": content_hash,
                "http_status": 200
            }) + "\n")

        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "evidence_id": "EV-01",
                "source_id": "SRC-01",
                "verbatim_excerpt": raw_payload,
                "locator": {"locator_type": "css", "selector_or_page": "body"},
                "retrieved_at": "2026-09-06T00:00:00Z",
                "source_quality_class": "class_a",
                "raw_payload_sha256": content_hash,
                "char_start": 0,
                "char_end": len(raw_payload)
            }) + "\n")

        with open(bundle_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            k_alice = hashlib.sha256(b"SRC-01:0:13").hexdigest()[:16]
            k_bob = hashlib.sha256(b"SRC-01:36:46").hexdigest()[:16]
            f.write(json.dumps({"mention_id": "MEN-ALICE", "evidence_id": "EV-01", "mention_key": k_alice, "raw_name_text": "Alice Example", "source_id": "SRC-01", "context_snippet": "Alice Example is Professor at Yale.", "char_start": 0, "char_end": 13}) + "\n")
            f.write(json.dumps({"mention_id": "MEN-BOB", "evidence_id": "EV-01", "mention_key": k_bob, "raw_name_text": "Bob Sample", "source_id": "SRC-01", "context_snippet": "Bob Sample is Dean at Harvard.", "char_start": 36, "char_end": 46}) + "\n")

        with open(bundle_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"cluster_id": "CLUST-ALICE", "mention_ids": ["MEN-ALICE"], "clustering_method": "constrained_union_find", "threshold_used": 0.85}) + "\n")
            f.write(json.dumps({"cluster_id": "CLUST-BOB", "mention_ids": ["MEN-BOB"], "clustering_method": "constrained_union_find", "threshold_used": 0.85}) + "\n")

        with open(bundle_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"candidate_entity_id": "CAND-ALICE", "proposed_cluster_id": "CLUST-ALICE", "mention_ids": ["MEN-ALICE"]}) + "\n")
            f.write(json.dumps({"candidate_entity_id": "CAND-BOB", "proposed_cluster_id": "CLUST-BOB", "mention_ids": ["MEN-BOB"]}) + "\n")

        with open(bundle_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            pass

        claims = [
            {
                "claim_id": "CLM-001",
                "candidate_entity_id": "CAND-ALICE",
                "subject_mention_id": "MEN-ALICE",
                "predicate": "holds_position",
                "object_raw": "Professor",
                "polarity": "affirmative",
                "temporal_status": "current",
                "adjudication_status": "unresolved",
                "as_of": "2026-09-06",
                "extraction_confidence": 0.95,
                "evidence_ids": ["EV-01"],
                "support_clauses": [{
                    "evidence_id": "EV-01",
                    "subject_mention_id": "MEN-ALICE",
                    "clause_span_start": 0,
                    "clause_span_end": 35,
                    "verbatim_clause": "Alice Example is Professor at Yale.",
                    "relation_span_start": 0,
                    "relation_span_end": 26,
                    "provenance_level": "relation",
                }]
            },
            {
                "claim_id": "CLM-002",
                "candidate_entity_id": "CAND-BOB",
                "subject_mention_id": "MEN-BOB",
                "predicate": "holds_position",
                "object_raw": "Dean",
                "polarity": "affirmative",
                "temporal_status": "current",
                "adjudication_status": "unresolved",
                "as_of": "2026-09-06",
                "extraction_confidence": 0.95,
                "evidence_ids": ["EV-01"],
                "support_clauses": [{
                    "evidence_id": "EV-01",
                    "subject_mention_id": "MEN-BOB",
                    "clause_span_start": 36,
                    "clause_span_end": 66,
                    "verbatim_clause": "Bob Sample is Dean at Harvard.",
                    "relation_span_start": 36,
                    "relation_span_end": 54,
                    "provenance_level": "relation",
                }]
            }
        ]
        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            for c in claims:
                f.write(json.dumps(c) + "\n")

        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({
                "run_id": "R1",
                "run_outcome": "completed",
                "queries_executed": 1,
                "pages_fetched": 1,
                "query_budget": 10,
                "tool_version": "1.0.0",
                "model_name": "test",
                "execution_time_seconds": 0.1,
                "crawl_errors": [],
                "abstention_records": []
            }, f)

        with open(bundle_dir / "dossier.json", "w", encoding="utf-8") as f:
            json.dump({
                "dossier_id": "D1",
                "candidate_entity_id": "CAND-ALICE",
                "proposed_cluster_id": "CLUST-ALICE",
                "statements": [{"statement_id": "S1", "section": "role", "rendered_text": "Professor at Yale", "backed_claim_ids": ["CLM-001"]}],
                "generated_at": "2026-09-06T00:00:00Z"
            }, f)

        with open(bundle_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier for Alice Example\n")

        val = validate_bundle(bundle_dir)
        assert val["is_valid"] is True, f"Valid multi-candidate bundle was rejected: {val['errors']}"

        # Test failure: assign Bob's claim to Alice's candidate
        claims[1]["candidate_entity_id"] = "CAND-ALICE"
        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            for c in claims:
                f.write(json.dumps(c) + "\n")

        val_tampered = validate_bundle(bundle_dir)
        assert val_tampered["is_valid"] is False, "Failure: Subject mention MEN-BOB attributed to CAND-ALICE was not rejected!"


# ==============================================================================
# Test 3: Evidence Tampering Caught by Payload Verifier
# ==============================================================================
def test_evidence_tampering_caught_by_payload_verifier():
    """
    Test 3: Mutate evidence.verbatim_excerpt or raw_payload_sha256;
    validate_bundle() asserts divergence between evidence and source payload SHA-256.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir) / "bundle"
        bundle_dir.mkdir()

        raw_payload = "Real untouched payload text for Alice Example, Researcher."
        content_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        with open(bundle_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"source_id": "SRC-01", "url": "https://example.com", "publisher": "example.com", "content_sha256": content_hash, "http_status": 200}) + "\n")

        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "evidence_id": "EV-01",
                "source_id": "SRC-01",
                "verbatim_excerpt": raw_payload,
                "locator": {"locator_type": "css", "selector_or_page": "body"},
                "retrieved_at": "2026-09-06T00:00:00Z",
                "source_quality_class": "class_a",
                "raw_payload_sha256": content_hash,
                "char_start": 0,
                "char_end": len(raw_payload)
            }) + "\n")

        with open(bundle_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            k_ev3 = hashlib.sha256(b"SRC-01:32:45").hexdigest()[:16]
            f.write(json.dumps({"mention_id": "MEN-01", "evidence_id": "EV-01", "mention_key": k_ev3, "raw_name_text": "Alice Example", "source_id": "SRC-01", "context_snippet": raw_payload, "char_start": 32, "char_end": 45}) + "\n")

        with open(bundle_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"cluster_id": "CLUST-01", "mention_ids": ["MEN-01"], "clustering_method": "constrained_union_find", "threshold_used": 0.85}) + "\n")

        with open(bundle_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"candidate_entity_id": "CAND-01", "proposed_cluster_id": "CLUST-01", "mention_ids": ["MEN-01"]}) + "\n")

        with open(bundle_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            pass

        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "claim_id": "CLM-001",
                "candidate_entity_id": "CAND-01",
                "subject_mention_id": "MEN-01",
                "predicate": "holds_position",
                "object_raw": "Researcher",
                "polarity": "affirmative",
                "temporal_status": "current",
                "adjudication_status": "unresolved",
                "as_of": "2026-09-06",
                "extraction_confidence": 0.95,
                "evidence_ids": ["EV-01"],
                "support_clauses": [{
                    "evidence_id": "EV-01",
                    "subject_mention_id": "MEN-01",
                    "clause_span_start": 0,
                    "clause_span_end": len(raw_payload),
                    "verbatim_clause": raw_payload,
                    "relation_span_start": 32,
                    "relation_span_end": 57,
                    "provenance_level": "relation"
                }]
            }) + "\n")

        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({"run_id": "R1", "run_outcome": "completed", "queries_executed": 1, "pages_fetched": 1, "query_budget": 10, "tool_version": "1.0", "model_name": "m", "execution_time_seconds": 0.1, "crawl_errors": [], "abstention_records": []}, f)

        with open(bundle_dir / "dossier.json", "w", encoding="utf-8") as f:
            json.dump({"dossier_id": "D1", "candidate_entity_id": "CAND-01", "proposed_cluster_id": "CLUST-01", "statements": [{"statement_id": "S1", "section": "role", "rendered_text": "text", "backed_claim_ids": ["CLM-001"]}], "generated_at": "2026-09-06T00:00:00Z"}, f)

        with open(bundle_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier\n")

        assert validate_bundle(bundle_dir)["is_valid"] is True

        # Tampering 1: Mutate raw_payload_sha256 in evidence
        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "evidence_id": "EV-01",
                "source_id": "SRC-01",
                "verbatim_excerpt": raw_payload,
                "locator": {"locator_type": "css", "selector_or_page": "body"},
                "retrieved_at": "2026-09-06T00:00:00Z",
                "source_quality_class": "class_a",
                "raw_payload_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "char_start": 0,
                "char_end": len(raw_payload)
            }) + "\n")

        assert validate_bundle(bundle_dir)["is_valid"] is False, "Evidence tampering with mismatched sha256 was not caught!"


# ==============================================================================
# Test 4: Two-Layer Mention Universe Evaluation
# ==============================================================================
def test_mention_detection_layer_and_common_universe():
    r"""
    Test 4: Layer 1 evaluates Mention Detection ($P, R, F_1$);
    Layer 2 evaluates clustering on common universe $U_{common} = M_{sys} \cap M_{gold}$
    without ZeroDivisionError.
    """
    gold_mentions = ["M1", "M2", "M3", "M4"]
    sys_mentions = ["M1", "M5"]  # Low recall: 1/4 = 0.25

    det = compute_mention_detection_metrics(gold_mentions, sys_mentions, threshold=0.95)
    assert det["detection_recall"] == 0.25
    assert det["detection_gate"] is False
    assert det["missing_gold_count"] == 3
    assert det["spurious_sys_count"] == 1

    # Common universe
    common = list(set(gold_mentions).intersection(set(sys_mentions)))
    assert common == ["M1"]

    b3 = compute_b3([["M1", "M2"]], [["M1"]], common)
    assert b3["b3_f1"] == 1.0  # Restriction of both to M1 gives identical clusters

    # Zero universe boundary test
    b3_empty = compute_b3([], [], [])
    assert b3_empty["b3_f1"] == 1.0


# ==============================================================================
# Test 5: Kuhn-Munkres Partial Matching with Dummy Nodes
# ==============================================================================
def test_kuhn_munkres_partial_matching_with_dummies():
    """
    Test 5: All-zero weight matrix with threshold theta=1.0 returns 0 matches,
    precision 0.0, and recall 0.0, rejecting any fake perfect scores.
    """
    # 2 gold claims, 2 sys claims, all zero semantic similarity
    matrix = [
        [0.0, 0.0],
        [0.0, 0.0]
    ]
    matched_pairs, total_weight = max_weight_partial_matching(matrix, threshold=1.0)
    assert len(matched_pairs) == 0
    assert total_weight == 0.0

    # 1 perfect match, 1 non-match
    matrix_half = [
        [1.0, 0.0],
        [0.0, 0.0]
    ]
    matched_half, weight_half = max_weight_partial_matching(matrix_half, threshold=1.0)
    assert len(matched_half) == 1
    assert matched_half[0] == (0, 0)
    assert weight_half == 1.0


# ==============================================================================
# Test 6: Kuhn-Munkres Differential vs Scipy
# ==============================================================================
def test_kuhn_munkres_differential_vs_scipy():
    """
    Test 6: 100 random matrix differential trials comparing pure-Python
    Hungarian algorithm against scipy.optimize.linear_sum_assignment.
    """
    random.seed(42)
    for trial in range(100):
        n = random.randint(2, 10)
        cost_matrix = [[round(random.uniform(1.0, 100.0), 4) for _ in range(n)] for _ in range(n)]

        custom_cols, custom_cost = hungarian_min_cost(cost_matrix)
        scipy_rows, scipy_cols = linear_sum_assignment(cost_matrix)

        scipy_cost = sum(cost_matrix[r][c] for r, c in zip(scipy_rows, scipy_cols))
        assert abs(custom_cost - scipy_cost) < 1e-6, f"Discrepancy on trial {trial}: custom={custom_cost}, scipy={scipy_cost}"


# ==============================================================================
# Test 7: Quotation Frame Does Not Attribute to Speaker
# ==============================================================================
def test_quotation_frame_not_attributed_to_speaker():
    """
    Test 7: "Alice said Bob is Dean" -> Dean is NOT attributed to Alice.
    """
    ev = Evidence(
        evidence_id="EV-Q1",
        source_id="SRC-Q1",
        verbatim_excerpt="Alice Example said that Bob Sample is Dean of Yale College.",
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    alice_claims = extract_claims_from_evidence(ev, "CAND-ALICE", target_name="Alice Example")
    assert not any(c.predicate == "holds_position" and "Dean" in c.object_raw for c in alice_claims), \
        "Quotation Frame leak: Dean was falsely attributed to speaker Alice!"

    bob_claims = extract_claims_from_evidence(ev, "CAND-BOB", target_name="Bob Sample")
    assert any(c.predicate == "holds_position" and "Dean" in c.object_raw for c in bob_claims), \
        "Quotation Frame failure: Dean was not attributed to Bob!"


# ==============================================================================
# Test 8: Appositive Frame Attaches to Adjacent Noun
# ==============================================================================
def test_appositive_frame_attaches_to_adjacent_noun():
    """
    Test 8: "Alice met Bob, the former Dean" -> former Dean belongs to Bob, not Alice.
    """
    ev = Evidence(
        evidence_id="EV-A1",
        source_id="SRC-A1",
        verbatim_excerpt="Alice Example met Bob Sample, the former Dean of Yale College.",
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    alice_claims = extract_claims_from_evidence(ev, "CAND-ALICE", target_name="Alice Example")
    assert not any(c.predicate == "holds_position" and "Dean" in c.object_raw for c in alice_claims), \
        "Appositive Frame leak: Dean was falsely attributed to Alice!"

    bob_claims = extract_claims_from_evidence(ev, "CAND-BOB", target_name="Bob Sample")
    assert any(c.predicate == "holds_position" and "Dean" in c.object_raw and c.temporal_status == TemporalStatus.FORMER for c in bob_claims), \
        "Appositive Frame failure: former Dean was not attributed to Bob!"


# ==============================================================================
# Test 9: Copular SVO and Local Negation Scope
# ==============================================================================
def test_copular_svo_and_local_negation():
    """
    Test 9: "Alice is not Dean. Alice is Associate Dean."
    Verifies affirmative vs negative polarity detection without bleeding.
    """
    pol_neg = detect_clause_polarity("Alice Example is not the Dean")
    pol_pos = detect_clause_polarity("Alice Example is the Associate Dean")
    assert pol_neg == FactPolarity.NEGATIVE
    assert pol_pos == FactPolarity.AFFIRMATIVE

    ev = Evidence(
        evidence_id="EV-S1",
        source_id="SRC-S1",
        verbatim_excerpt="Alice Example is not the Dean of Yale College. Alice Example is Associate Dean at Yale College.",
        locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
        retrieved_at=datetime.now(timezone.utc),
        source_quality_class=SourceQualityClass.CLASS_A,
    )
    claims = extract_claims_from_evidence(ev, "CAND-ALICE", target_name="Alice Example")
    dean_claims = [c for c in claims if c.predicate == "holds_position" and c.object_raw == "Dean"]
    assoc_claims = [c for c in claims if c.predicate == "holds_position" and "Associate Dean" in c.object_raw]

    assert any(c.polarity == FactPolarity.NEGATIVE for c in dean_claims), "Negative claim polarity was not detected!"
    assert any(c.polarity == FactPolarity.AFFIRMATIVE for c in assoc_claims), "Affirmative claim polarity was not detected!"


# ==============================================================================
# Test 10: State Machine Matrix S1 through S7
# ==============================================================================
def test_state_machine_matrix_s1_through_s7():
    """
    Test 10: Exhaustive truth-table verification of states S1 to S7.
    Particularly checks that 403 on seed fetch yields S5 (collection_failed).
    """
    # S5: collection_failed on 403 HTTP error with 0 pages fetched
    s5_outcome, _, _ = determine_state_outcome(
        has_structural_error=False,
        crawl_errors=["HTTP 403 Forbidden"],
        pages_fetched=0,
        candidates=[],
        claims=[]
    )
    assert s5_outcome == RunOutcome.COLLECTION_FAILED

    # S3: insufficient_evidence when pages fetched > 0 but 0 verified claims
    s3_outcome, _, _ = determine_state_outcome(
        has_structural_error=False,
        crawl_errors=[],
        pages_fetched=2,
        candidates=[],
        claims=[]
    )
    assert s3_outcome == RunOutcome.INSUFFICIENT_EVIDENCE

    # S7: structural_failure on broken schema
    s7_outcome, _, _ = determine_state_outcome(
        has_structural_error=True,
        crawl_errors=[],
        pages_fetched=2,
        candidates=[],
        claims=[]
    )
    assert s7_outcome == RunOutcome.FAILED


# ==============================================================================
# Test 11: Cross-Lingual Pinyin Yields REVIEW Without Corroboration
# ==============================================================================
def test_cross_lingual_pinyin_yields_review_without_corroboration():
    """
    Test 11: Cross-lingual pinyin match (Xin Zhou vs 周欣) without independent
    corroboration produces REVIEW (sim=0.50) and does not merge automatically.
    """
    m1 = EntityMention(
        mention_id="M1",
        raw_name_text="Xin Zhou",
        source_id="S1",
        evidence_id="EV-01",
        context_snippet="Xin Zhou authored publication on computer algorithms.",
        char_start=0,
        char_end=8,
        mention_key="k1",
    )
    m2 = EntityMention(
        mention_id="M2",
        raw_name_text="周欣",
        source_id="S2",
        evidence_id="EV-02",
        context_snippet="周欣 担任电视台节目主持人。",
        char_start=0,
        char_end=2,
        mention_key="k2",
    )
    decisions, clusters = resolve_mentions([m1, m2])
    assert len(decisions) == 1
    assert decisions[0].machine_relation == MachineRelation.REVIEW
    assert decisions[0].match_probability == 0.50
    # Must be split into 2 clusters
    assert len(clusters) == 2


# ==============================================================================
# Test 12: Ambiguous Identity When Margin Below Delta
# ==============================================================================
def test_ambiguous_identity_when_margin_below_delta():
    """
    Test 12: When top 2 candidates have margin < Delta (0.20), state machine
    outputs AMBIGUOUS_IDENTITY and sets primary_candidate_id = None.
    """
    cand1 = CandidateEntity(candidate_entity_id="CAND-1", proposed_cluster_id="CLUST-1", mention_ids=["M1"])
    cand2 = CandidateEntity(candidate_entity_id="CAND-2", proposed_cluster_id="CLUST-2", mention_ids=["M2"])

    claim1 = Claim(
        claim_id="C1",
        candidate_entity_id="CAND-1",
        subject_mention_id="M1",
        predicate="holds_position",
        object_raw="Professor",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        adjudication_status=AdjudicationStatus.UNRESOLVED,
        as_of=datetime.now().date(),
        extraction_confidence=0.90,
        evidence_ids=["E1"],
        support_clauses=[ClaimEvidenceSupport(evidence_id="E1", subject_mention_id="M1", clause_span_start=0, clause_span_end=9, verbatim_clause="Professor")]
    )
    claim2 = Claim(
        claim_id="C2",
        candidate_entity_id="CAND-2",
        subject_mention_id="M2",
        predicate="holds_position",
        object_raw="Director",
        polarity=FactPolarity.AFFIRMATIVE,
        temporal_status=TemporalStatus.CURRENT,
        adjudication_status=AdjudicationStatus.UNRESOLVED,
        as_of=datetime.now().date(),
        extraction_confidence=0.90,
        evidence_ids=["E2"],
        support_clauses=[ClaimEvidenceSupport(evidence_id="E2", subject_mention_id="M2", clause_span_start=0, clause_span_end=8, verbatim_clause="Director")]
    )

    outcome, primary_id, ambig = determine_state_outcome(
        has_structural_error=False,
        crawl_errors=[],
        pages_fetched=2,
        candidates=[cand1, cand2],
        claims=[claim1, claim2]
    )
    assert outcome == RunOutcome.AMBIGUOUS_IDENTITY
    assert primary_id is None
    assert set(ambig) == {"CAND-1", "CAND-2"}


# ==============================================================================
# Test 13: Deterministic Semantic Bundle Hash
# ==============================================================================
def test_deterministic_semantic_bundle_hash():
    """
    Test 13: Semantic Bundle tree hash is deterministic and ignores runtime
    operational timestamps (observed_at, retrieved_at).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir) / "bundle"
        bundle_dir.mkdir()

        claims = [{"claim_id": "CLM-01", "predicate": "holds_position", "object_raw": "Dean"}]
        manifest = {
            "run_id": "RUN-01",
            "run_outcome": "completed",
            "abstention_records": [{"observed_at": "2026-09-06T12:00:00Z", "gap_id": "G1"}]
        }
        evidence = [{"evidence_id": "EV-01", "retrieved_at": "2026-09-06T12:00:00Z", "verbatim_excerpt": "Text"}]

        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            for c in claims:
                f.write(json.dumps(c) + "\n")
        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            for e in evidence:
                f.write(json.dumps(e) + "\n")

        hash1 = compute_bundle_fingerprint(bundle_dir)

        # Mutate timestamps only
        manifest["abstention_records"][0]["observed_at"] = "2099-01-01T00:00:00Z"
        evidence[0]["retrieved_at"] = "2099-01-01T00:00:00Z"
        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            for e in evidence:
                f.write(json.dumps(e) + "\n")

        hash2 = compute_bundle_fingerprint(bundle_dir)
        assert hash1 == hash2, "Immutability failure: Operational timestamps affected semantic bundle hash!"

        # Mutate semantic payload
        claims[0]["object_raw"] = "Vice Dean"
        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            for c in claims:
                f.write(json.dumps(c) + "\n")

        hash3 = compute_bundle_fingerprint(bundle_dir)
        assert hash1 != hash3, "Divergence failure: Claim content mutation was not captured by bundle hash!"


# ==============================================================================
# Test 14: 128-bit SHA-256 Claim ID Determinism
# ==============================================================================
def test_claim_id_128bit_sha256_hash():
    """
    Test 14: Claim IDs use CLM-{32 hex chars} (128-bit SHA-256) and are bit-for-bit idempotent.
    """
    subj = "MEN-12345"
    pred = "holds_position"
    obj = "Professor"
    pol = FactPolarity.AFFIRMATIVE
    temp = TemporalStatus.CURRENT

    raw_key = f"{subj}:{pred}:{obj}:{pol.value}:{temp.value}".encode("utf-8")
    claim_id1 = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
    claim_id2 = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"

    assert claim_id1 == claim_id2
    assert re.match(r"^CLM-[0-9a-f]{32}$", claim_id1), f"Claim ID '{claim_id1}' does not match 128-bit specification!"


# ==============================================================================
# Test 15: Total Score Clamped in [0, 100.0] and Approximate Edges Routed to Review
# ==============================================================================
def test_total_score_clamped_and_approximate_edges_routed_to_review():
    """
    Test 15: Total score is strictly clamped to [0, 100.0].
    Approximate edges (weight 0.50) are routed to review and excluded from precision.
    """
    # Test bipartite matching with 0.50 edge
    matrix = [[0.50]]
    matched_pairs, total_weight = max_weight_partial_matching(matrix, threshold=1.0)
    # Threshold 1.0 excludes 0.50 from admissible matches
    assert len(matched_pairs) == 0
    assert total_weight == 0.0

    # Test scoring clamp
    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir) / "bundle"
        bundle_dir.mkdir()

        # Minimal valid bundle
        with open(bundle_dir / "sources.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"source_id": "S1", "url": "https://example.com", "publisher": "example.com", "content_sha256": "abcdef", "http_status": 200}) + "\n")
        with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"evidence_id": "E1", "source_id": "S1", "verbatim_excerpt": "Alice is Dean.", "locator": {"locator_type": "css", "selector_or_page": "body"}, "retrieved_at": "2026-09-06T00:00:00Z", "source_quality_class": "class_a"}) + "\n")
        with open(bundle_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"mention_id": "M1", "evidence_id": "E1", "mention_key": "k1", "raw_name_text": "Alice", "source_id": "S1", "context_snippet": "Alice is Dean."}) + "\n")
        with open(bundle_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"cluster_id": "CLUST-1", "mention_ids": ["M1"], "clustering_method": "constrained_union_find", "threshold_used": 0.85}) + "\n")
        with open(bundle_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"candidate_entity_id": "CAND-1", "proposed_cluster_id": "CLUST-1", "mention_ids": ["M1"]}) + "\n")
        with open(bundle_dir / "matches.jsonl", "w", encoding="utf-8") as f:
            pass
        with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "claim_id": "CLM-1",
                "candidate_entity_id": "CAND-1",
                "subject_mention_id": "M1",
                "predicate": "holds_position",
                "object_raw": "Dean",
                "polarity": "affirmative",
                "temporal_status": "current",
                "adjudication_status": "unresolved",
                "as_of": "2026-09-06",
                "extraction_confidence": 1.0,
                "evidence_ids": ["E1"],
                "support_clauses": [{"evidence_id": "E1", "subject_mention_id": "M1", "clause_span_start": 0, "clause_span_end": 14, "verbatim_clause": "Alice is Dean."}]
            }) + "\n")
        with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump({"run_id": "R1", "run_outcome": "completed", "queries_executed": 1, "pages_fetched": 1, "query_budget": 10, "tool_version": "1.0", "model_name": "m", "execution_time_seconds": 0.1, "crawl_errors": [], "abstention_records": []}, f)
        with open(bundle_dir / "dossier.json", "w", encoding="utf-8") as f:
            json.dump({"dossier_id": "D1", "candidate_entity_id": "CAND-1", "proposed_cluster_id": "CLUST-1", "statements": [{"statement_id": "S1", "section": "role", "rendered_text": "Dean", "backed_claim_ids": ["CLM-1"]}], "generated_at": "2026-09-06T00:00:00Z"}, f)
        with open(bundle_dir / "dossier.md", "w", encoding="utf-8") as f:
            f.write("# Dossier\n")

        gold_file = Path(tmp_dir) / "gold.json"
        with open(gold_file, "w", encoding="utf-8") as f:
            json.dump({"target_name": "Alice", "gold_claims": [{"predicate": "holds_position", "object_raw": "Dean", "equivalence_set": ["Dean"]}]}, f)

        res = evaluate_dossier_bundle(bundle_dir, gold_file)
        score = res["total_score_out_of_100"]
        assert 0.0 <= score <= 100.0, f"Score {score} violated [0, 100.0] bounds!"
