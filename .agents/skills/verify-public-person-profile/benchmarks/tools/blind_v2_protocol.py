"""Preregistration, reveal verification, and one-shot consumption tools for Blind V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from models.blind_protocol import (
    BlindCandidatePool,
    BlindHiddenAssetManifest,
    BlindPersonaManifest,
    BlindPreregistration,
    CuratorAttestation,
    ExcludedPersonaRegistry,
)
from models.gold_schema_v2 import GoldSuite


HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _json_value(payload: Any) -> Any:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return payload


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        _json_value(payload),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def build_commitment(payload: Any, nonce: str) -> str:
    if not nonce:
        raise ValueError("commitment nonce must be non-empty")
    material = nonce.encode("utf-8") + b"\0" + canonical_json_bytes(payload)
    return hashlib.sha256(material).hexdigest()


def verify_commitment(payload: Any, nonce: str, expected_sha256: str) -> bool:
    if not HEX64_PATTERN.fullmatch(expected_sha256):
        return False
    return build_commitment(payload, nonce) == expected_sha256


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def select_candidate_ids(
    preregistration: BlindPreregistration,
    candidate_pool: BlindCandidatePool,
    selection_seed: str,
) -> list[str]:
    if preregistration.suite_id != candidate_pool.suite_id:
        raise ValueError("candidate pool suite_id does not match preregistration")
    if len(candidate_pool.entries) < preregistration.candidate_pool_minimum:
        raise ValueError(
            f"candidate pool has {len(candidate_pool.entries)} entries; "
            f"minimum is {preregistration.candidate_pool_minimum}"
        )
    if not selection_seed:
        raise ValueError("selection seed must be non-empty")

    by_stratum: dict[str, list] = {}
    valid_strata = {spec.stratum_id for spec in preregistration.strata}
    for candidate in candidate_pool.entries:
        if candidate.primary_stratum not in valid_strata:
            raise ValueError(
                f"candidate {candidate.candidate_id} uses undeclared stratum {candidate.primary_stratum}"
            )
        by_stratum.setdefault(candidate.primary_stratum, []).append(candidate)

    selected: list[str] = []
    for spec in preregistration.strata:
        available = by_stratum.get(spec.stratum_id, [])
        if len(available) < spec.case_count:
            raise ValueError(
                f"stratum {spec.stratum_id} has {len(available)} candidates; requires {spec.case_count}"
            )

        def seeded_rank(candidate: Any) -> tuple[bytes, str]:
            material = f"{selection_seed}\0{spec.stratum_id}\0{candidate.candidate_id}".encode("utf-8")
            return hashlib.sha256(material).digest(), candidate.candidate_id

        selected.extend(candidate.candidate_id for candidate in sorted(available, key=seeded_rank)[: spec.case_count])
    return selected


def _assert_no_prior_exposure(
    candidate_pool: BlindCandidatePool,
    exclusions: ExcludedPersonaRegistry,
) -> None:
    excluded = {normalize_identity(name) for name in exclusions.names}
    for candidate in candidate_pool.entries:
        identities = [candidate.target_name, *candidate.aliases]
        overlap = {normalize_identity(value) for value in identities} & excluded
        if overlap:
            raise ValueError(
                f"candidate {candidate.candidate_id} appears in the prior-exposure registry"
            )


def validate_revealed_assets(
    preregistration: BlindPreregistration,
    candidate_pool: BlindCandidatePool,
    selection_manifest: BlindPersonaManifest,
    exclusions: ExcludedPersonaRegistry,
    selection_seed: str,
) -> dict[str, Any]:
    suite_ids = {
        preregistration.suite_id,
        candidate_pool.suite_id,
        selection_manifest.suite_id,
        exclusions.suite_id,
    }
    if len(suite_ids) != 1:
        raise ValueError("revealed assets do not share one suite_id")

    _assert_no_prior_exposure(candidate_pool, exclusions)
    expected_ids = select_candidate_ids(preregistration, candidate_pool, selection_seed)
    actual_ids = [entry.candidate_id for entry in selection_manifest.entries]
    if actual_ids != expected_ids:
        raise ValueError("selection manifest does not match deterministic selection")
    if len(actual_ids) != preregistration.expected_case_count:
        raise ValueError("selection manifest case count does not match preregistration")
    expected_case_ids = [
        f"BLIND2-{index:03d}"
        for index in range(1, preregistration.expected_case_count + 1)
    ]
    actual_case_ids = [entry.case_id for entry in selection_manifest.entries]
    if actual_case_ids != expected_case_ids:
        raise ValueError("selection manifest case IDs must be contiguous and deterministic")

    pool_by_id = {entry.candidate_id: entry for entry in candidate_pool.entries}
    for selected in selection_manifest.entries:
        pool_entry = pool_by_id.get(selected.candidate_id)
        if pool_entry is None:
            raise ValueError(f"selected candidate {selected.candidate_id} is absent from candidate pool")
        expected = pool_entry.model_dump(mode="json")
        actual = selected.model_dump(mode="json", exclude={"case_id"})
        if actual != expected:
            raise ValueError(f"selected candidate {selected.candidate_id} differs from frozen pool entry")

    counts = Counter(entry.primary_stratum for entry in selection_manifest.entries)
    expected_counts = {spec.stratum_id: spec.case_count for spec in preregistration.strata}
    if dict(counts) != expected_counts:
        raise ValueError("selection manifest strata counts do not match preregistration")

    return {
        "suite_id": preregistration.suite_id,
        "candidate_pool_count": len(candidate_pool.entries),
        "selected_case_count": len(selection_manifest.entries),
        "strata_counts": dict(counts),
        "prior_exposure_overlap_count": 0,
    }


def expected_queries_for_persona(
    target_name: str,
    hints: list[str],
    aliases: list[str],
) -> list[str]:
    queries = [target_name, *[f"{target_name} {hint}" for hint in hints]]
    for alias in aliases:
        if alias != target_name:
            queries.append(alias)
            queries.extend(f"{alias} {hint}" for hint in hints)
    return queries


def validate_execution_assets(
    preregistration: BlindPreregistration,
    selection_manifest: BlindPersonaManifest,
    case_manifest_path: Path,
    query_index_path: Path,
) -> dict[str, Any]:
    case_manifest = BlindPersonaManifest.model_validate(_load_json(case_manifest_path))
    if case_manifest.model_dump(mode="json") != selection_manifest.model_dump(mode="json"):
        raise ValueError("case_manifest.json differs from the committed selection manifest")

    indexed_queries: set[str] = set()
    for line_number, raw_line in enumerate(
        query_index_path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"malformed query_index.jsonl at line {line_number}"
            ) from exc
        query = entry.get("query") if isinstance(entry, dict) else None
        urls = entry.get("urls") if isinstance(entry, dict) else None
        if not isinstance(query, str) or not query.strip() or not isinstance(urls, list):
            raise ValueError(f"invalid query index entry at line {line_number}")
        normalized = " ".join(query.casefold().split())
        if normalized in indexed_queries:
            raise ValueError(f"duplicate normalized query index key at line {line_number}")
        indexed_queries.add(normalized)

    required_queries: set[str] = set()
    for persona in case_manifest.entries:
        persona_queries = expected_queries_for_persona(
            persona.target_name,
            persona.hints,
            persona.aliases,
        )
        if len(persona_queries) > preregistration.query_budget_per_case:
            raise ValueError(
                f"case {persona.case_id} requires {len(persona_queries)} queries, "
                f"exceeding preregistered budget {preregistration.query_budget_per_case}"
            )
        required_queries.update(" ".join(query.casefold().split()) for query in persona_queries)

    missing_queries = sorted(required_queries - indexed_queries)
    if missing_queries:
        raise ValueError(
            "query_index.jsonl is missing preregistered execution queries: "
            + ", ".join(missing_queries)
        )
    return {
        "case_count": len(case_manifest.entries),
        "required_query_count": len(required_queries),
        "indexed_query_count": len(indexed_queries),
    }


def verify_hidden_asset_manifest(
    manifest: BlindHiddenAssetManifest,
    asset_dir: Path,
) -> list[str]:
    errors: list[str] = []
    declared_names = set(manifest.assets)
    actual_names = {
        path.name
        for path in asset_dir.iterdir()
        if path.is_file() and path.name != "asset_manifest.json" and not path.name.startswith(".")
    }
    for unexpected in sorted(actual_names - declared_names):
        errors.append(f"undeclared hidden asset: {unexpected}")
    for relative_name, expected in sorted(manifest.assets.items()):
        path = asset_dir / relative_name
        if path.is_symlink():
            errors.append(f"hidden asset must not be a symlink: {relative_name}")
            continue
        if not path.is_file():
            errors.append(f"missing hidden asset: {relative_name}")
            continue
        actual_bytes = path.stat().st_size
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_bytes != expected.bytes:
            errors.append(
                f"byte-size mismatch for {relative_name}: expected {expected.bytes}, got {actual_bytes}"
            )
        if actual_sha != expected.sha256:
            errors.append(
                f"SHA-256 mismatch for {relative_name}: expected {expected.sha256}, got {actual_sha}"
            )
    return errors


def validate_curator_attestation(
    preregistration: BlindPreregistration,
    attestation: CuratorAttestation,
) -> dict[str, Any]:
    if attestation.suite_id != preregistration.suite_id:
        raise ValueError("curator attestation suite_id does not match preregistration")
    if attestation.independent_curator_count < preregistration.minimum_independent_curators:
        raise ValueError(
            "independent curator count is below the preregistered minimum"
        )
    return {
        "curator_id": attestation.curator_id,
        "independent_curator_count": attestation.independent_curator_count,
        "adjudication_completed": attestation.adjudication_completed,
    }


def verify_toolchain_hashes(
    preregistration: BlindPreregistration,
    evaluator_file: Path,
    gold_schema_file: Path,
) -> dict[str, str]:
    evaluator_sha = _sha256(evaluator_file)
    gold_schema_sha = _sha256(gold_schema_file)
    if evaluator_sha != preregistration.evaluator_sha256:
        raise ValueError(
            f"evaluator SHA-256 mismatch: expected {preregistration.evaluator_sha256}, got {evaluator_sha}"
        )
    if gold_schema_sha != preregistration.gold_schema_sha256:
        raise ValueError(
            f"Gold Schema SHA-256 mismatch: expected {preregistration.gold_schema_sha256}, got {gold_schema_sha}"
        )
    return {
        "evaluator_sha256": evaluator_sha,
        "gold_schema_sha256": gold_schema_sha,
    }


def validate_hidden_gold_alignment(
    preregistration: BlindPreregistration,
    selection_manifest: BlindPersonaManifest,
    gold_payload: Any,
) -> dict[str, int]:
    gold_suite = gold_payload if isinstance(gold_payload, GoldSuite) else GoldSuite.model_validate(gold_payload)
    if len(gold_suite) != preregistration.expected_case_count:
        raise ValueError("Gold case count does not match preregistration")

    selected_by_case = {entry.case_id: entry for entry in selection_manifest.entries}
    gold_by_case = {case.case_id: case for case in gold_suite}
    if set(selected_by_case) != set(gold_by_case):
        raise ValueError("Gold case IDs do not match the deterministic selection manifest")

    fact_bearing_by_stratum = {
        spec.stratum_id: spec.fact_bearing for spec in preregistration.strata
    }
    independently_adjudicated = 0
    for case_id, selected in selected_by_case.items():
        gold_case = gold_by_case[case_id]
        if normalize_identity(gold_case.target_name) != normalize_identity(selected.target_name):
            raise ValueError(f"Gold target_name mismatch for {case_id}")
        expected_fact_bearing = fact_bearing_by_stratum[selected.primary_stratum]
        if gold_case.is_fact_bearing != expected_fact_bearing:
            raise ValueError(f"Gold fact-bearing status conflicts with stratum for {case_id}")
        if gold_case.annotation_type != "double_blind_adjudicated":
            raise ValueError(f"Gold case {case_id} is not double_blind_adjudicated")
        independently_adjudicated += 1

    return {
        "gold_case_count": len(gold_suite),
        "independently_adjudicated_case_count": independently_adjudicated,
    }


def verify_candidate_checkout(repo_root: Path, expected_commit: str) -> dict[str, Any]:
    if not HEX40_PATTERN.fullmatch(expected_commit):
        raise ValueError("expected_commit must be a full 40-character Git SHA")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != expected_commit:
        raise ValueError(f"candidate checkout is {head}, expected {expected_commit}")
    if dirty:
        raise ValueError("candidate checkout is dirty")
    return {"git_commit": head, "git_dirty": False}


def claim_one_shot_attempt(
    ledger_dir: Path,
    suite_id: str,
    preregistration_sha256: str,
    candidate_git_commit: str,
) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_\-]*", suite_id):
        raise ValueError("invalid suite_id")
    if not HEX64_PATTERN.fullmatch(preregistration_sha256):
        raise ValueError("invalid preregistration SHA-256")
    if not HEX40_PATTERN.fullmatch(candidate_git_commit):
        raise ValueError("invalid candidate Git commit")

    ledger_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = ledger_dir / f"{suite_id}.attempt.json"
    attempt_id = hashlib.sha256(
        f"{suite_id}\0{preregistration_sha256}\0{candidate_git_commit}".encode("utf-8")
    ).hexdigest()[:20]
    receipt = {
        "suite_id": suite_id,
        "attempt_id": attempt_id,
        "status": "claimed",
        "preregistration_sha256": preregistration_sha256,
        "candidate_git_commit": candidate_git_commit,
        "claimed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(receipt_path, flags, 0o600)
    except FileExistsError as exc:
        raise FileExistsError(f"suite {suite_id} has already been consumed") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return receipt_path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind V2 preregistration and reveal verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    public = subparsers.add_parser("validate-public", help="Validate a public preregistration only")
    public.add_argument("--preregistration", type=Path, required=True)

    schema = subparsers.add_parser("export-schema", help="Export the public preregistration JSON Schema")
    schema.add_argument("--output", type=Path)

    commitment = subparsers.add_parser(
        "build-commitment",
        help="Build a canonical nonce-bound commitment for one hidden protocol asset",
    )
    commitment.add_argument("--asset-type", required=True, choices=[
        "seed",
        "candidate_pool",
        "selection_manifest",
        "exclusion_registry",
        "curator_attestation",
        "hidden_asset_manifest",
    ])
    commitment.add_argument("--input", type=Path, required=True)
    commitment.add_argument("--nonce-file", type=Path, required=True)

    reveal = subparsers.add_parser("verify-reveal", help="Verify committed hidden selection assets")
    reveal.add_argument("--preregistration", type=Path, required=True)
    reveal.add_argument("--seed-file", type=Path, required=True)
    reveal.add_argument("--seed-nonce", required=True)
    reveal.add_argument("--candidate-pool", type=Path, required=True)
    reveal.add_argument("--pool-nonce", required=True)
    reveal.add_argument("--selection-manifest", type=Path, required=True)
    reveal.add_argument("--selection-nonce", required=True)
    reveal.add_argument("--exclusion-registry", type=Path, required=True)
    reveal.add_argument("--exclusion-nonce", required=True)
    reveal.add_argument("--curator-attestation", type=Path, required=True)
    reveal.add_argument("--attestation-nonce", required=True)
    reveal.add_argument("--hidden-asset-manifest", type=Path, required=True)
    reveal.add_argument("--hidden-assets-nonce", required=True)
    reveal.add_argument("--hidden-assets-dir", type=Path, required=True)
    reveal.add_argument("--repo-root", type=Path, required=True)
    reveal.add_argument("--evaluator-file", type=Path, required=True)
    reveal.add_argument("--gold-schema-file", type=Path, required=True)
    reveal.add_argument("--consume-ledger-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "export-schema":
        schema_payload = BlindPreregistration.model_json_schema()
        serialized = json.dumps(schema_payload, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        else:
            print(serialized, end="")
        return
    if args.command == "build-commitment":
        nonce = args.nonce_file.read_text(encoding="utf-8").strip()
        if args.asset_type == "seed":
            payload = args.input.read_text(encoding="utf-8").strip()
        else:
            model_by_type = {
                "candidate_pool": BlindCandidatePool,
                "selection_manifest": BlindPersonaManifest,
                "exclusion_registry": ExcludedPersonaRegistry,
                "curator_attestation": CuratorAttestation,
                "hidden_asset_manifest": BlindHiddenAssetManifest,
            }
            payload = model_by_type[args.asset_type].model_validate(_load_json(args.input))
        print(json.dumps({
            "asset_type": args.asset_type,
            "commitment_sha256": build_commitment(payload, nonce),
        }, indent=2))
        return

    prereg = BlindPreregistration.model_validate(_load_json(args.preregistration))
    if args.command == "validate-public":
        print(json.dumps({
            "is_valid": True,
            "suite_id": prereg.suite_id,
            "expected_case_count": prereg.expected_case_count,
            "candidate_pool_minimum": prereg.candidate_pool_minimum,
            "strata": {spec.stratum_id: spec.case_count for spec in prereg.strata},
        }, indent=2, ensure_ascii=False))
        return

    seed = args.seed_file.read_text(encoding="utf-8").strip()
    pool = BlindCandidatePool.model_validate(_load_json(args.candidate_pool))
    selection = BlindPersonaManifest.model_validate(_load_json(args.selection_manifest))
    exclusions = ExcludedPersonaRegistry.model_validate(_load_json(args.exclusion_registry))
    attestation = CuratorAttestation.model_validate(_load_json(args.curator_attestation))
    hidden_assets = BlindHiddenAssetManifest.model_validate(_load_json(args.hidden_asset_manifest))
    commitment_checks = {
        "selection_seed": verify_commitment(seed, args.seed_nonce, prereg.selection_seed_commitment_sha256),
        "candidate_pool": verify_commitment(pool, args.pool_nonce, prereg.candidate_pool_commitment_sha256),
        "selection_manifest": verify_commitment(
            selection, args.selection_nonce, prereg.selection_manifest_commitment_sha256
        ),
        "exclusion_registry": verify_commitment(
            exclusions, args.exclusion_nonce, prereg.exclusion_registry_commitment_sha256
        ),
        "curator_attestation": verify_commitment(
            attestation, args.attestation_nonce, prereg.curator_attestation_sha256
        ),
        "hidden_asset_manifest": verify_commitment(
            hidden_assets,
            args.hidden_assets_nonce,
            prereg.hidden_asset_manifest_commitment_sha256,
        ),
    }
    failed = [name for name, passed in commitment_checks.items() if not passed]
    if failed:
        raise ValueError(f"commitment verification failed: {', '.join(failed)}")
    attestation_summary = validate_curator_attestation(prereg, attestation)
    if hidden_assets.suite_id != prereg.suite_id:
        raise ValueError("hidden asset manifest suite_id does not match preregistration")
    hidden_asset_errors = verify_hidden_asset_manifest(hidden_assets, args.hidden_assets_dir)
    if hidden_asset_errors:
        raise ValueError("hidden asset verification failed: " + "; ".join(hidden_asset_errors))

    summary = validate_revealed_assets(prereg, pool, selection, exclusions, seed)
    summary["execution_assets"] = validate_execution_assets(
        prereg,
        selection,
        args.hidden_assets_dir / "case_manifest.json",
        args.hidden_assets_dir / "query_index.jsonl",
    )
    gold_alignment = validate_hidden_gold_alignment(
        prereg,
        selection,
        _load_json(args.hidden_assets_dir / "gold.json"),
    )
    summary["commitment_checks"] = commitment_checks
    summary["hidden_asset_count"] = len(hidden_assets.assets)
    summary["gold_alignment"] = gold_alignment
    summary["curator_attestation"] = attestation_summary
    summary["candidate_checkout"] = verify_candidate_checkout(
        args.repo_root, prereg.candidate_git_commit
    )
    summary["toolchain"] = verify_toolchain_hashes(
        prereg,
        args.evaluator_file,
        args.gold_schema_file,
    )
    prereg_sha = _sha256(args.preregistration)
    receipt = claim_one_shot_attempt(
        args.consume_ledger_dir,
        prereg.suite_id,
        prereg_sha,
        prereg.candidate_git_commit,
    )
    summary["attempt_receipt"] = str(receipt)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
