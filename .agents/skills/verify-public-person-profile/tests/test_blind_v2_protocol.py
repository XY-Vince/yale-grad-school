import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from benchmarks.tools.blind_v2_protocol import (
    build_commitment,
    claim_one_shot_attempt,
    select_candidate_ids,
    validate_curator_attestation,
    validate_hidden_gold_alignment,
    validate_revealed_assets,
    verify_hidden_asset_manifest,
    verify_toolchain_hashes,
    verify_commitment,
)
from models.blind_protocol import (
    BlindCandidatePool,
    BlindHiddenAssetManifest,
    BlindPersonaManifest,
    BlindPreregistration,
    CuratorAttestation,
    ExcludedPersonaRegistry,
)


HEX = "a" * 64


def prereg_payload() -> dict:
    return {
        "protocol_version": "2.0",
        "suite_id": "blind_release_v2",
        "evaluation_role": "blind_release",
        "candidate_git_commit": "1" * 40,
        "evaluator_sha256": "2" * 64,
        "gold_schema_sha256": "3" * 64,
        "expected_case_count": 30,
        "candidate_pool_minimum": 90,
        "selection_method": "stratified_seeded_without_replacement",
        "permitted_attempts": 1,
        "track_name": "hinted",
        "paired_control_required": True,
        "independent_curator_required": True,
        "hidden_gold_required": True,
        "gold_annotation_policy": "two_curators_independent_then_adjudicated",
        "minimum_independent_curators": 2,
        "adjudicator_separate_from_implementation": True,
        "selection_seed_commitment_sha256": "4" * 64,
        "candidate_pool_commitment_sha256": "5" * 64,
        "selection_manifest_commitment_sha256": "6" * 64,
        "exclusion_registry_commitment_sha256": "7" * 64,
        "curator_attestation_sha256": "8" * 64,
        "hidden_asset_manifest_commitment_sha256": "9" * 64,
        "excluded_suite_ids": ["real_web_dev_v2", "blind_release_v1"],
        "strata": [
            {
                "stratum_id": "fact_bearing",
                "case_count": 24,
                "fact_bearing": True,
                "description": "New fact-bearing personas across heterogeneous public sources.",
            },
            {
                "stratum_id": "safe_abstention",
                "case_count": 6,
                "fact_bearing": False,
                "description": "Sparse or non-disambiguable personas expected to abstain.",
            },
        ],
        "thresholds": {
            "target_entity_case_recall": 1.0,
            "entity_source_recall": 0.95,
            "max_false_merges": 0,
            "max_false_splits": 0,
            "max_unmatched_released_claims": 0,
            "macro_claim_precision": 0.95,
            "macro_claim_recall": 0.80,
            "subject_attribution_accuracy": 0.95,
            "outcome_accuracy": 0.90,
            "abstention_accuracy": 1.0,
            "paired_input_identity_required": True,
        },
    }


def candidate_pool() -> BlindCandidatePool:
    entries = []
    for stratum, count in (("fact_bearing", 60), ("safe_abstention", 30)):
        for idx in range(count):
            entries.append(
                {
                    "candidate_id": f"{stratum}-{idx:03d}",
                    "target_name": f"Person {stratum} {idx:03d}",
                    "primary_stratum": stratum,
                    "aliases": [],
                    "hints": [f"Institution {idx:03d}"],
                }
            )
    return BlindCandidatePool(suite_id="blind_release_v2", entries=entries)


def test_public_preregistration_rejects_personas_and_quota_mismatch():
    valid = BlindPreregistration.model_validate(prereg_payload())
    assert valid.expected_case_count == 30

    exposed = prereg_payload()
    exposed["personas"] = [{"target_name": "Leaked Person"}]
    with pytest.raises(ValidationError):
        BlindPreregistration.model_validate(exposed)

    bad_quota = prereg_payload()
    bad_quota["strata"][0]["case_count"] = 23
    with pytest.raises(ValidationError, match="strata case_count total"):
        BlindPreregistration.model_validate(bad_quota)


def test_commitments_are_canonical_and_tamper_evident():
    payload = {"b": 2, "a": [1, 3]}
    digest = build_commitment(payload, "nonce-1")
    assert verify_commitment(payload, "nonce-1", digest)
    assert verify_commitment({"a": [1, 3], "b": 2}, "nonce-1", digest)
    assert not verify_commitment({"a": [1, 4], "b": 2}, "nonce-1", digest)
    assert not verify_commitment(payload, "nonce-2", digest)


def test_stratified_selection_and_reveal_validation():
    prereg = BlindPreregistration.model_validate(prereg_payload())
    pool = candidate_pool()
    exclusions = ExcludedPersonaRegistry(
        suite_id="blind_release_v2",
        names=["Previously Seen Person"],
    )
    selected = select_candidate_ids(prereg, pool, "secret-seed")
    assert len(selected) == 30

    by_id = {entry.candidate_id: entry for entry in pool.entries}
    manifest = BlindPersonaManifest(
        suite_id="blind_release_v2",
        entries=[
            {
                "case_id": f"BLIND2-{idx:03d}",
                **by_id[candidate_id].model_dump(),
            }
            for idx, candidate_id in enumerate(selected, start=1)
        ],
    )
    summary = validate_revealed_assets(prereg, pool, manifest, exclusions, "secret-seed")
    assert summary["selected_case_count"] == 30
    assert summary["strata_counts"] == {"fact_bearing": 24, "safe_abstention": 6}

    tampered = manifest.model_copy(deep=True)
    tampered.entries[0].candidate_id = "fact_bearing-059"
    with pytest.raises(ValueError, match="deterministic selection"):
        validate_revealed_assets(prereg, pool, tampered, exclusions, "secret-seed")


def test_reveal_rejects_prior_exposure_in_candidate_pool():
    prereg = BlindPreregistration.model_validate(prereg_payload())
    pool = candidate_pool()
    pool.entries[0].target_name = "Xin Zhou"
    exclusions = ExcludedPersonaRegistry(
        suite_id="blind_release_v2",
        names=["Xin Zhou", "Sarah Luckart"],
    )
    selected = select_candidate_ids(prereg, pool, "secret-seed")
    by_id = {entry.candidate_id: entry for entry in pool.entries}
    manifest = BlindPersonaManifest(
        suite_id="blind_release_v2",
        entries=[
            {"case_id": f"BLIND2-{idx:03d}", **by_id[cid].model_dump()}
            for idx, cid in enumerate(selected, start=1)
        ],
    )

    with pytest.raises(ValueError, match="prior-exposure registry"):
        validate_revealed_assets(prereg, pool, manifest, exclusions, "secret-seed")


def test_one_shot_attempt_is_claimed_atomically(tmp_path: Path):
    receipt = claim_one_shot_attempt(
        ledger_dir=tmp_path,
        suite_id="blind_release_v2",
        preregistration_sha256=HEX,
        candidate_git_commit="1" * 40,
    )
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["status"] == "claimed"

    with pytest.raises(FileExistsError, match="already been consumed"):
        claim_one_shot_attempt(
            ledger_dir=tmp_path,
            suite_id="blind_release_v2",
            preregistration_sha256=HEX,
            candidate_git_commit="1" * 40,
        )


def test_hidden_asset_manifest_requires_exact_files_and_detects_tampering(tmp_path: Path):
    required_names = [
        "capture_failures.jsonl",
        "capture_manifest.jsonl",
        "case_manifest.json",
        "corpus.warc",
        "gold.json",
        "query_index.jsonl",
    ]
    entries = {}
    for name in required_names:
        path = tmp_path / name
        path.write_text(f"payload for {name}", encoding="utf-8")
        entries[name] = {
            "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    manifest = BlindHiddenAssetManifest(suite_id="blind_release_v2", assets=entries)
    assert verify_hidden_asset_manifest(manifest, tmp_path) == []

    (tmp_path / "gold.json").write_text("tampered", encoding="utf-8")
    errors = verify_hidden_asset_manifest(manifest, tmp_path)
    assert any("gold.json" in error and "mismatch" in error for error in errors)

    (tmp_path / "undeclared.tmp").write_text("not allowed", encoding="utf-8")
    errors = verify_hidden_asset_manifest(manifest, tmp_path)
    assert any("undeclared hidden asset" in error for error in errors)

    incomplete = dict(entries)
    incomplete.pop("query_index.jsonl")
    with pytest.raises(ValidationError, match="required asset set"):
        BlindHiddenAssetManifest(suite_id="blind_release_v2", assets=incomplete)


def test_hidden_gold_must_align_with_selection_and_be_independently_adjudicated():
    prereg = BlindPreregistration.model_validate(prereg_payload())
    pool = candidate_pool()
    selected = select_candidate_ids(prereg, pool, "secret-seed")
    by_id = {entry.candidate_id: entry for entry in pool.entries}
    manifest = BlindPersonaManifest(
        suite_id="blind_release_v2",
        entries=[
            {"case_id": f"BLIND2-{idx:03d}", **by_id[cid].model_dump()}
            for idx, cid in enumerate(selected, start=1)
        ],
    )
    gold_payload = []
    for entry in manifest.entries:
        fact_bearing = entry.primary_stratum == "fact_bearing"
        entity_id = f"ENT-{entry.case_id}"
        gold_payload.append(
            {
                "case_id": entry.case_id,
                "target_name": entry.target_name,
                "target_gold_entity_id": entity_id,
                "expected_outcome": "completed" if fact_bearing else "insufficient_evidence",
                "is_fact_bearing": fact_bearing,
                "annotation_type": "double_blind_adjudicated",
                "gold_entities": [{"gold_entity_id": entity_id, "canonical_name": entry.target_name}],
                "gold_mentions": [],
                "gold_clusters": [],
                "gold_claims": (
                    [
                        {
                            "claim_id": f"GCLM-{entry.case_id}",
                            "subject_gold_entity_id": entity_id,
                            "predicate": "holds_position",
                            "object_raw": "Professor",
                            "polarity": "affirmative",
                            "temporal_status": "current",
                            "supports": [
                                {
                                    "source_url": "https://example.edu/profile",
                                    "source_content_sha256": "f" * 64,
                                    "char_start": 0,
                                    "char_end": 9,
                                    "verbatim_text": "Professor",
                                }
                            ],
                        }
                    ]
                    if fact_bearing
                    else []
                ),
            }
        )
    summary = validate_hidden_gold_alignment(prereg, manifest, gold_payload)
    assert summary == {"gold_case_count": 30, "independently_adjudicated_case_count": 30}

    gold_payload[0]["annotation_type"] = "curator_annotation"
    with pytest.raises(ValueError, match="double_blind_adjudicated"):
        validate_hidden_gold_alignment(prereg, manifest, gold_payload)


def test_curator_attestation_and_toolchain_hashes_are_enforced(tmp_path: Path):
    payload = prereg_payload()
    payload["minimum_independent_curators"] = 3
    evaluator = tmp_path / "evaluator.py"
    gold_schema = tmp_path / "gold_schema.py"
    evaluator.write_text("evaluator", encoding="utf-8")
    gold_schema.write_text("schema", encoding="utf-8")
    payload["evaluator_sha256"] = __import__("hashlib").sha256(evaluator.read_bytes()).hexdigest()
    payload["gold_schema_sha256"] = __import__("hashlib").sha256(gold_schema.read_bytes()).hexdigest()
    prereg = BlindPreregistration.model_validate(payload)

    insufficient = CuratorAttestation(
        suite_id="blind_release_v2",
        curator_id="curation-team",
        independent_of_implementation=True,
        prior_exposure_registry_reviewed=True,
        candidate_pool_frozen_before_selection=True,
        independent_curator_count=2,
        adjudication_completed=True,
    )
    with pytest.raises(ValueError, match="independent curator count"):
        validate_curator_attestation(prereg, insufficient)

    sufficient = insufficient.model_copy(update={"independent_curator_count": 3})
    assert validate_curator_attestation(prereg, sufficient)["independent_curator_count"] == 3
    assert verify_toolchain_hashes(prereg, evaluator, gold_schema)["evaluator_sha256"] == payload["evaluator_sha256"]

    evaluator.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="evaluator SHA-256"):
        verify_toolchain_hashes(prereg, evaluator, gold_schema)


def test_committed_public_schema_matches_model():
    schema_path = (
        Path(__file__).resolve().parent.parent
        / "benchmarks"
        / "protocols"
        / "blind_release_v2"
        / "preregistration.schema.json"
    )
    assert json.loads(schema_path.read_text(encoding="utf-8")) == BlindPreregistration.model_json_schema()
