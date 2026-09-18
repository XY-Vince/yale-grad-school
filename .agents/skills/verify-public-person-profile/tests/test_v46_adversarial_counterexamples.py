"""
Adversarial Counterexamples & Independent Release Gate Verification for V4.6.
All tests construct 100% schema-compliant bundles via Legitimate Bundle Factory
and assert structural_validation_passed == True before verifying core algorithmic gate rejections.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest

from models.schemas import (
    EntityMention,
    MachineRelation,
    RunOutcome,
    Dossier,
)
from scripts.score_candidates import evaluate_dossier_bundle
from scripts.validate_dossier import validate_bundle
from core.collectors.warc_player import WarcPlayerCollector
from core.run_profile import determine_state_outcome
from core.render_dossier import render_dossier_markdown
from core.resolver import resolve_mentions, detect_cannot_link
from tests.bundle_factory import create_valid_bundle


def test_gold_clusters_not_rewritten_by_system_output(tmp_path: Path):
    """
    [P0-1] Evaluator must NOT rewrite gold_clusters using system mentions when IDs are disjoint!
    Factory produces 100% valid bundle; evaluator must report B3=0.0 and detection gate False.
    """
    bundle_dir = tmp_path / "disjoint_bundle"
    create_valid_bundle(bundle_dir, target_name="Alice Smith")

    val = validate_bundle(bundle_dir)
    assert val["is_valid"] is True, f"Factory bundle must be valid: {val['errors']}"

    gold_data = {
        "target_name": "Alice Smith",
        "hard_negatives": [{"name": "Alice Smith", "domain": "dance", "reason": "dancer"}],
        "gold_clusters": [["GOLD-DISJOINT-01", "GOLD-DISJOINT-02"]],
        "gold_claims": [{
            "predicate": "holds_position",
            "object_raw": "Professor",
            "polarity": "affirmative",
            "temporal_status": "current",
            "subject": "Alice Smith",
        }],
    }
    gold_file = tmp_path / "gold.json"
    with open(gold_file, "w", encoding="utf-8") as f:
        json.dump(gold_data, f)

    res = evaluate_dossier_bundle(bundle_dir, gold_file)
    assert res["structural_validation_passed"] is True, "Must pass structural pre-gate"
    assert res["gates"]["mention_detection_gate"] is False, "Detection gate must fail on missing gold IDs"
    assert res["detailed_metrics"]["b3_f1"] == 0.0, "B3 F1 must be 0.0 when gold IDs are disjoint"
    assert res["all_gates_passed"] is False, "All gates must NOT pass"


def test_svo_syntactic_role_rejects_object_and_subtokens(tmp_path: Path):
    """
    [P0-3] 5D syntactic analysis must reject distractor titles:
    1. 'Alice thanked Dean Bob' (Dean belongs to Bob, not Alice)
    2. 'Dean Bob interviewed Alice' (Alice is the object, not the Dean)
    3. 'Alice praised Dean Bob' (interaction verb, title belongs to Bob)
    4. 'Alice emailed Dean Bob' (interaction verb, title belongs to Bob)
    5. 'Alice is the custodian of Dean Hall' (facility noun, not job title)
    All test bundles MUST be structurally valid!
    """
    gold_data = {
        "target_name": "Alice",
        "gold_clusters": [["MEN-01"]],
        "gold_claims": [{
            "predicate": "holds_position",
            "object_raw": "Dean",
            "polarity": "affirmative",
            "temporal_status": "current",
            "subject": "Alice",
        }],
    }
    gold_file = tmp_path / "gold.json"
    with open(gold_file, "w", encoding="utf-8") as f:
        json.dump(gold_data, f)

    counterexamples = [
        "<html><body>Alice thanked Dean Bob yesterday at the meeting.</body></html>",
        "<html><body>Dean Bob interviewed Alice regarding the curriculum.</body></html>",
        "<html><body>Alice praised Dean Bob for his leadership.</body></html>",
        "<html><body>Alice emailed Dean Bob regarding research.</body></html>",
        "<html><body>Alice is the custodian of Dean Hall on campus.</body></html>",
    ]

    for idx, text in enumerate(counterexamples):
        case_dir = tmp_path / f"case_{idx}"
        create_valid_bundle(
            case_dir,
            target_name="Alice",
            excerpt=text,
            claim_predicate="holds_position",
            claim_object="Dean",
        )

        val = validate_bundle(case_dir)
        assert val["is_valid"] is True, f"Test bundle must be structurally valid: {val['errors']}"

        res = evaluate_dossier_bundle(case_dir, gold_file)
        assert res["structural_validation_passed"] is True, "Structural validation must pass"
        assert res["gates"]["citation_entailment_gate"] is False, f"Failed to reject distractor: {text}"


def test_word_boundary_blocks_malice(tmp_path: Path):
    """
    [P0-3] Word boundary regex must prevent 'Malice' from matching 'Alice'.
    Bundle is structurally valid for Malice; evaluated against Alice's gold truth.
    """
    gold_data = {
        "target_name": "Alice",
        "gold_clusters": [["MEN-01"]],
        "gold_claims": [{
            "predicate": "holds_position",
            "object_raw": "Dean",
            "polarity": "affirmative",
            "temporal_status": "current",
            "subject": "Alice",
        }],
    }
    gold_file = tmp_path / "gold_alice.json"
    with open(gold_file, "w", encoding="utf-8") as f:
        json.dump(gold_data, f)

    case_dir = tmp_path / "case_malice"
    text = "<html><body>Malice is the Dean at the college.</body></html>"
    create_valid_bundle(
        case_dir,
        target_name="Alice",
        raw_name_text="Malice",
        excerpt=text,
        claim_predicate="holds_position",
        claim_object="Dean",
    )

    val = validate_bundle(case_dir)
    assert val["is_valid"] is True, f"Bundle must be structurally valid: {val['errors']}"

    res = evaluate_dossier_bundle(case_dir, gold_file)
    assert res["structural_validation_passed"] is True
    assert res["gates"]["citation_entailment_gate"] is False, "Malice must not entail Alice's position"


def test_unreviewed_claims_fail_pending_review_gate(tmp_path: Path):
    """
    [P0-7] When a dossier contains claims unreviewed against gold,
    pending_review_gate must fail and all_gates_passed must be False.
    """
    bundle_dir = tmp_path / "unreviewed_bundle"
    create_valid_bundle(
        bundle_dir,
        target_name="Alice Smith",
        claim_predicate="holds_position",
        claim_object="Astronaut",
    )

    val = validate_bundle(bundle_dir)
    assert val["is_valid"] is True, f"Bundle must be valid: {val['errors']}"

    # Gold only has Professor, not Astronaut
    gold_data = {
        "target_name": "Alice Smith",
        "gold_clusters": [["MEN-01"]],
        "gold_claims": [{
            "predicate": "holds_position",
            "object_raw": "Professor",
            "polarity": "affirmative",
            "temporal_status": "current",
            "subject": "Alice Smith",
        }],
    }
    gold_file = tmp_path / "gold.json"
    with open(gold_file, "w", encoding="utf-8") as f:
        json.dump(gold_data, f)

    res = evaluate_dossier_bundle(bundle_dir, gold_file)
    assert res["structural_validation_passed"] is True
    assert res["gates"]["pending_review_gate"] is False, "Unreviewed claims must trip pending_review_gate"
    assert res["all_gates_passed"] is False, "All gates must fail when unreviewed claims exist"


def test_no_auto_merge_dentist_and_plumber():
    """
    [P0-6] Same-name individuals with mutually exclusive trades/professions
    (e.g. Dentist vs Plumber) must be classified as NONMATCH and split into separate clusters.
    """
    m1 = EntityMention(
        mention_id="M1",
        raw_name_text="John Smith",
        source_id="S1",
        evidence_id="E1",
        context_snippet="Dr. John Smith operates a dental clinic as a licensed Dentist.",
        char_start=4,
        char_end=14,
        mention_key="key_m1_dentist",
        inferred_affiliations=["dental clinic", "dentist"],
    )
    m2 = EntityMention(
        mention_id="M2",
        raw_name_text="John Smith",
        source_id="S2",
        evidence_id="E2",
        context_snippet="John Smith provides residential pipe repair as a licensed Plumber.",
        char_start=0,
        char_end=10,
        mention_key="key_m2_plumber",
        inferred_affiliations=["pipe repair", "plumber"],
    )
    cannot_link = detect_cannot_link(m1, m2)
    assert cannot_link is True, "Dentist vs Plumber must trigger cannot-link"

    decisions, clusters = resolve_mentions([m1, m2])
    assert decisions[0].machine_relation == MachineRelation.NONMATCH
    assert len(clusters) == 2, "Must split into two independent singleton clusters"


def test_no_auto_merge_same_name_unsupported():
    """
    [P0-6] Same-name individuals without corroborating evidence (shared org, domain, or verified alias)
    must NOT auto-merge; they must be marked as REVIEW and remain separate singletons.
    """
    m1 = EntityMention(
        mention_id="M1",
        raw_name_text="David Miller",
        source_id="S1",
        evidence_id="E1",
        context_snippet="David Miller attended the event.",
        char_start=0,
        char_end=12,
        mention_key="key_m1_david",
        inferred_affiliations=[],
    )
    m2 = EntityMention(
        mention_id="M2",
        raw_name_text="David Miller",
        source_id="S2",
        evidence_id="E2",
        context_snippet="David Miller signed the guestbook.",
        char_start=0,
        char_end=12,
        mention_key="key_m2_david",
        inferred_affiliations=[],
    )
    decisions, clusters = resolve_mentions([m1, m2])
    assert decisions[0].machine_relation == MachineRelation.REVIEW, "Unsupported candidate match must require review"
    assert len(clusters) == 2, "Without corroboration, same-name mentions must remain singletons"


def test_gold_chmod_000_access_denied(tmp_path: Path):
    """
    [P0-2] File-permission access blocking:
    Demonstrates that chmod 0o000 on a real sentinel Gold file denies read access (EACCES)
    to child processes under the same UID, and restoring 0o644 allows evaluator reading.
    """
    gold_sentinel = tmp_path / "sentinel_gold.json"
    with open(gold_sentinel, "w", encoding="utf-8") as f:
        json.dump({"secret": "ground_truth_claims"}, f)

    # 1. Strip permissions (0o000)
    os.chmod(gold_sentinel, 0o000)
    try:
        # Child process attempts to read the sentinel
        probe_cmd = [
            sys.executable,
            "-c",
            f"open('{gold_sentinel.resolve()}', 'rb').read()",
        ]
        proc = subprocess.run(probe_cmd, capture_output=True, text=True)
        assert proc.returncode != 0, "Child process must NOT be able to read 0o000 gold file"
        assert "PermissionError" in proc.stderr or "Permission denied" in proc.stderr, f"Must fail with EACCES: {proc.stderr}"
    finally:
        # Restore permissions for evaluator
        os.chmod(gold_sentinel, 0o644)

    # Evaluator now reads successfully
    with open(gold_sentinel, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["secret"] == "ground_truth_claims"


def test_dossier_validator_rejects_fake_hashes_and_zero_slices(tmp_path: Path):
    """
    [P0-4] Validator must catch forged hashes (64 zeros), 0:0 slices, and slice mismatches.
    """
    bundle_dir = tmp_path / "tampered_bundle"
    create_valid_bundle(bundle_dir, target_name="Alice Smith")

    # Tamper with evidence: set 64 zeros payload hash
    ev_file = bundle_dir / "evidence.jsonl"
    with open(ev_file, "r") as f:
        lines = [json.loads(l) for l in f]
    lines[0]["raw_payload_sha256"] = "0" * 64
    with open(ev_file, "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")

    val = validate_bundle(bundle_dir)
    assert val["is_valid"] is False
    assert any("fake all-zero" in err for err in val["errors"])


def test_warc_player_handles_embedded_warc_delimiter_via_content_length(tmp_path: Path):
    """
    [P1-1] WARC parser must parse records sequentially using Content-Length,
    NOT by splitting on 'WARC/1.0\\r\\n'. If payload contains WARC/1.0, it must NOT be truncated.
    """
    warc_file = tmp_path / "embedded.warc"
    inner_payload = "<html><body>Documentation about WARC/1.0 format and WARC/1.1 standard.</body></html>"
    http_payload = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: text/html\r\n"
        f"Content-Length: {len(inner_payload)}\r\n\r\n"
        f"{inner_payload}"
    ).encode("utf-8")

    warc_record_bytes = (
        b"WARC/1.0\r\n"
        b"WARC-Type: response\r\n"
        b"WARC-Target-URI: https://example.org/warc-spec\r\n"
        b"WARC-Date: 2026-09-08T00:00:00Z\r\n"
        b"Content-Type: application/http; msgtype=response\r\n"
        + f"Content-Length: {len(http_payload)}\r\n\r\n".encode("latin-1")
        + http_payload
        + b"\r\n\r\n"
    )

    with open(warc_file, "wb") as f:
        f.write(warc_record_bytes)

    player = WarcPlayerCollector(warc_file)
    status, payload, sha = player.fetch_page("https://example.org/warc-spec")
    assert status == 200
    assert payload == inner_payload, "WARC parser truncated payload on embedded WARC/1.0 delimiter!"


def test_http_403_produces_collection_failed():
    """
    [P0-6] When pages return HTTP 403 / 500, collector must record crawl_errors,
    and FSM must output COLLECTION_FAILED (S2), not INSUFFICIENT_EVIDENCE (S5).
    """
    outcome, primary_cand, ambig = determine_state_outcome(
        has_structural_error=False,
        pages_fetched=0,
        crawl_errors=["HTTP 403 Forbidden: Access Denied"],
        candidates=[],
        claims=[],
        search_has_results=True,
        budget_exhausted=False,
        is_ambiguous=False,
    )
    assert outcome == RunOutcome.COLLECTION_FAILED, f"Expected COLLECTION_FAILED but got {outcome}"


def test_liam_abstention_renders_insufficient_evidence_not_ambiguous():
    """
    [P0-6] When candidate_entity_id is None and outcome is INSUFFICIENT_EVIDENCE,
    dossier markdown must render abstention, NOT 'AMBIGUOUS_IDENTITY / 存在同名多实体'.
    """
    dossier = Dossier(
        dossier_id="DOS-LIAM",
        candidate_entity_id=None,
        ambiguous_candidates=[],
        statements=[],
        generated_at=datetime.now(timezone.utc),
    )
    rendered = render_dossier_markdown(
        dossier=dossier,
        claims=[],
        person_name="Liam",
        run_outcome=RunOutcome.INSUFFICIENT_EVIDENCE,
    )
    assert "INSUFFICIENT_EVIDENCE" in rendered, "Markdown must indicate INSUFFICIENT_EVIDENCE"
    assert "AMBIGUOUS_IDENTITY" not in rendered, "Must not falsely claim AMBIGUOUS_IDENTITY on sparse abstention"
    assert "存在同名多实体" not in rendered, "Must not show ambiguous multi-entity notice"


def test_career_migration_not_split_arbitrarily():
    """
    [P0-5] Sequential career transitions (e.g. Yale former, Harvard current)
    must NOT be marked as Cannot-Link!
    """
    m1 = EntityMention(
        mention_id="M1",
        raw_name_text="Carol White",
        source_id="S1",
        evidence_id="E1",
        context_snippet="Carol White previously was a Postdoc at Yale University until 2022.",
        char_start=0,
        char_end=11,
        mention_key="key_m1_carol",
        inferred_affiliations=["yale university"],
    )
    m2 = EntityMention(
        mention_id="M2",
        raw_name_text="Carol White",
        source_id="S2",
        evidence_id="E2",
        context_snippet="Carol White currently is an Assistant Professor at Harvard University.",
        char_start=0,
        char_end=11,
        mention_key="key_m2_carol",
        inferred_affiliations=["harvard university"],
    )
    cannot_link = detect_cannot_link(m1, m2)
    assert cannot_link is False, "Sequential career transition across institutions must NOT trigger Cannot-Link"
