"""Regression tests for Plan A extraction and benchmark governance."""

import hashlib
import json
from pathlib import Path

import pytest

from benchmarks.eval_end2end import DEFAULT_GOLD_FILE, resolve_gold_file
from benchmarks.eval_extraction import (
    build_extraction_gates,
    clause_has_target_subject,
    strict_object_match,
)


SKILL_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = SKILL_ROOT / "benchmarks" / "test_cases" / "dev_regression"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_strict_5d_release_requires_precision_recall_and_f1():
    gates = build_extraction_gates(
        polarity_accuracy=1.0,
        temporal_accuracy=1.0,
        subject_attribution_accuracy=1.0,
        noise_false_positive_rate=0.0,
        relation_precision=1.0,
        relation_recall=1.0,
        relation_f1=1.0,
        joint_5d_precision=0.91,
        joint_5d_recall=1.0,
        joint_5d_f1=0.953,
    )

    assert gates["joint_5d_precision_gate"] is False
    assert gates["joint_5d_recall_gate"] is True
    assert gates["joint_5d_f1_gate"] is True
    assert gates["strict_5d_release_gate"] is False


def test_strict_object_match_rejects_partial_overlap():
    gold = {
        "object_raw": "Yale School of Medicine",
        "equivalence_set": ["Yale University School of Medicine"],
    }

    assert strict_object_match("Yale University School of Medicine", gold)
    assert not strict_object_match("Yale School of Medicine AIDS Program", gold)


def test_subject_attribution_uses_full_name_boundaries():
    assert clause_has_target_subject("Li Jiawen graduated from Beijing 101 Middle School.", "Li Jiawen")
    ctx = "Jacqueline Mann joined the team. She graduated from the University of Michigan."
    assert clause_has_target_subject("She graduated from the University of Michigan.", "Jacqueline Mann", full_context=ctx)
    # Standalone pronoun without antecedent must be rejected
    assert not clause_has_target_subject("She graduated from the University of Michigan.", "Jacqueline Mann")
    assert not clause_has_target_subject("The clinical program expanded.", "Li")


def test_subject_attribution_rejects_cross_entity_pronouns_and_other_subjects():
    """
    TDD / Governance Test:
    clause_has_target_subject must not accept anaphoric pronouns (he/she/they) blindly
    when the antecedent or clause subject is a different named person, or when target is an object.
    """
    # 1. Explicit conflicting person name as subject in clause
    assert not clause_has_target_subject(
        "Bob Smith graduated from MIT.", "Alice Wang"
    )

    # 2. Contextual cross-entity antecedent: pronoun binds to nearest preceding entity (Bob, not Alice)
    ctx = "Alice Wang joined Yale. Bob Smith presented the work. He won the best paper award."
    assert not clause_has_target_subject(
        "He won the best paper award.", "Alice Wang", full_context=ctx
    )
    assert clause_has_target_subject(
        "He won the best paper award.", "Bob Smith", full_context=ctx
    )

    # 3. Intra-clause cross-entity antecedent
    assert not clause_has_target_subject(
        "Bob Smith delivered the keynote. He received an honorary degree.", "Alice Wang"
    )

    # 4. Target appearing as an OBJECT of another subject's action must be rejected
    assert not clause_has_target_subject(
        "Bob Smith hired Alice Wang as a researcher.", "Alice Wang"
    )
    assert not clause_has_target_subject(
        "Prof. Davis advised Alice Wang during her doctoral studies.", "Alice Wang"
    )
    assert not clause_has_target_subject(
        "李四聘请了张三作为特聘研究员。", "张三"
    )

    # 5. Standalone pronoun with zero antecedent must be rejected
    assert not clause_has_target_subject(
        "She graduated from MIT.", "Alice Wang"
    )
    assert not clause_has_target_subject(
        "He served as department chair.", "Bob Smith"
    )

    # 6. Invalid subject_mention_id must be rejected
    assert not clause_has_target_subject(
        "Alice Wang graduated from MIT.", "Alice Wang", subject_mention_id="INVALID_ID"
    )
    assert clause_has_target_subject(
        "Alice Wang graduated from MIT.", "Alice Wang", subject_mention_id="MEN-a1b2c3d4e5f6"
    )

    # 7. Additional transitive object exclusion (e.g. thanked, emailed)
    assert not clause_has_target_subject(
        "Bob Smith thanked Alice Wang for her valuable contribution.", "Alice Wang"
    )
    assert not clause_has_target_subject(
        "She received her degree from MIT.",
        "Alice Wang",
        full_context="Bob Smith emailed Alice Wang. She received her degree from MIT.",
    )
    assert clause_has_target_subject(
        "She received her degree from MIT.",
        "Alice Wang",
        full_context="Alice Wang joined the lab. She received her degree from MIT.",
    )


def test_gold_versions_are_manifested_and_unversioned_alias_is_rejected():
    manifest_path = GOLD_DIR / "gold_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert DEFAULT_GOLD_FILE.name == "cases_gold_v2.json"
    assert manifest["active_version"] == "v2"
    assert _sha256(GOLD_DIR / "cases_gold_v1.json") == manifest["versions"]["v1"]["sha256"]
    assert _sha256(GOLD_DIR / "cases_gold_v2.json") == manifest["versions"]["v2"]["sha256"]
    assert manifest["versions"]["v1"]["historical_all_gates_pass_rate"] == 0.8

    v1 = {item["case_id"]: item for item in json.loads((GOLD_DIR / "cases_gold_v1.json").read_text(encoding="utf-8"))}
    v2 = {item["case_id"]: item for item in json.loads((GOLD_DIR / "cases_gold_v2.json").read_text(encoding="utf-8"))}
    assert set(v1) == set(v2)
    changed_cases = [case_id for case_id in v1 if v1[case_id] != v2[case_id]]
    assert changed_cases == ["jacqueline_mann"]
    added_claims = [
        claim
        for claim in v2["jacqueline_mann"]["gold_claims"]
        if claim not in v1["jacqueline_mann"]["gold_claims"]
    ]
    assert added_claims == [
        {
            "predicate": "graduated_from",
            "object_raw": "University of Michigan",
            "equivalence_set": ["University of Michigan", "UMich", "University of Michigan, Ann Arbor"],
            "polarity": "affirmative",
            "temporal_status": "unknown",
            "subject": "Jacqueline Mann",
        }
    ]

    with pytest.raises(ValueError, match="versioned Gold"):
        resolve_gold_file(GOLD_DIR / "cases_gold.json")
