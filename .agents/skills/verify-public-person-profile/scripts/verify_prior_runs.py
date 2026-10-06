#!/usr/bin/env python3
"""Mechanical verifier and auditor for historical blind suites in benchmarks/registry/prior_runs.json."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_prior_runs(
    registry_path: Path,
    prior_runs_root: Path,
) -> tuple[bool, list[dict[str, str]], list[str]]:
    if not registry_path.is_file():
        return False, [], [f"Registry file not found: {registry_path}"]

    if not prior_runs_root.is_dir():
        return False, [], [f"Prior runs root directory not found: {prior_runs_root}"]

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    runs = data.get("runs", [])
    records: list[dict[str, str]] = []
    errors: list[str] = []

    for run in runs:
        suite_id = run.get("suite_id", "unknown")
        rel_dir = run.get("curation_rel_path", "")
        run_dir = prior_runs_root / rel_dir

        if not run_dir.is_dir():
            errors.append(f"Suite {suite_id}: directory missing at {run_dir}")
            continue

        # 1. Case Manifest
        cm_rel = run.get("case_manifest_rel_path")
        if cm_rel:
            cm_path = run_dir / cm_rel
            if not cm_path.is_file():
                errors.append(f"Suite {suite_id}: case manifest missing at {cm_path}")
            else:
                actual_sha = file_sha256(cm_path)
                expected_sha = run.get("case_manifest_sha256")
                if expected_sha and actual_sha != expected_sha:
                    errors.append(
                        f"Suite {suite_id} case_manifest_sha256 mismatch: "
                        f"expected {expected_sha}, got {actual_sha}"
                    )
                records.append({
                    "suite_id": suite_id,
                    "rel_dir": rel_dir,
                    "item": f"case_manifest ({cm_rel})",
                    "sha256": actual_sha,
                    "exclusion_reason": run.get("exclusion_reason", "prior_suite"),
                    "sealed": str(run.get("sealed", False)),
                })

        # 2. Asset Manifest
        am_rel = run.get("asset_manifest_rel_path")
        if am_rel:
            am_path = run_dir / am_rel
            if not am_path.is_file():
                errors.append(f"Suite {suite_id}: asset manifest missing at {am_path}")
            else:
                actual_sha = file_sha256(am_path)
                expected_sha = run.get("curation_asset_manifest_sha256")
                if expected_sha and actual_sha != expected_sha:
                    errors.append(
                        f"Suite {suite_id} curation_asset_manifest_sha256 mismatch: "
                        f"expected {expected_sha}, got {actual_sha}"
                    )
                records.append({
                    "suite_id": suite_id,
                    "rel_dir": rel_dir,
                    "item": f"asset_manifest ({am_rel})",
                    "sha256": actual_sha,
                    "exclusion_reason": run.get("exclusion_reason", "prior_suite"),
                    "sealed": str(run.get("sealed", False)),
                })

        # 3. Seal Receipt
        if run.get("sealed", False):
            seal_rel = run.get("seal_rel_path") or "receipts/seal.json"
            seal_path = run_dir / seal_rel
            if not seal_path.is_file():
                errors.append(f"Suite {suite_id}: seal receipt missing at {seal_path}")
            else:
                actual_sha = file_sha256(seal_path)
                expected_sha = run.get("seal_sha256")
                if expected_sha and actual_sha != expected_sha:
                    errors.append(
                        f"Suite {suite_id} seal_sha256 mismatch: "
                        f"expected {expected_sha}, got {actual_sha}"
                    )
                records.append({
                    "suite_id": suite_id,
                    "rel_dir": rel_dir,
                    "item": f"seal_receipt ({seal_rel})",
                    "sha256": actual_sha,
                    "exclusion_reason": run.get("exclusion_reason", "prior_suite"),
                    "sealed": str(run.get("sealed", False)),
                })

        # 4. Evaluation Result
        eval_rel = run.get("evaluation_result_rel_path")
        if eval_rel:
            eval_path = run_dir / eval_rel
            if not eval_path.is_file():
                errors.append(f"Suite {suite_id}: evaluation result missing at {eval_path}")
            else:
                actual_sha = file_sha256(eval_path)
                expected_sha = run.get("evaluation_result_sha256")
                if expected_sha and actual_sha != expected_sha:
                    errors.append(
                        f"Suite {suite_id} evaluation_result_sha256 mismatch: "
                        f"expected {expected_sha}, got {actual_sha}"
                    )
                records.append({
                    "suite_id": suite_id,
                    "rel_dir": rel_dir,
                    "item": f"evaluation_result ({eval_rel})",
                    "sha256": actual_sha,
                    "exclusion_reason": run.get("exclusion_reason", "prior_suite"),
                    "sealed": str(run.get("sealed", False)),
                })

    return len(errors) == 0, records, errors


def main() -> int:
    skill_root = Path(__file__).resolve().parent.parent
    registry_path = skill_root / "benchmarks" / "registry" / "prior_runs.json"
    prior_runs_root = Path(os.environ.get("PRIOR_RUNS_ROOT", "/Users/xiang-yu/Desktop/ABCD"))

    reg_sha = file_sha256(registry_path) if registry_path.is_file() else "MISSING"
    print(f"Registry File: {registry_path}")
    print(f"Registry File SHA-256: {reg_sha}")
    print(f"Prior Runs Root: {prior_runs_root}")
    print("-" * 80)

    ok, records, errors = verify_prior_runs(registry_path, prior_runs_root)

    print(f"{'Suite ID':<16} | {'Item':<32} | {'Sealed':<6} | {'Exclusion Reason':<32} | {'SHA-256'}")
    print("-" * 150)
    for r in records:
        print(f"{r['suite_id']:<16} | {r['item']:<32} | {r['sealed']:<6} | {r['exclusion_reason']:<32} | {r['sha256']}")
    print("-" * 150)

    if ok:
        print(f"PASS: All {len(records)} historical artifacts verified against physical disk.")
        return 0
    else:
        print(f"FAIL: {len(errors)} error(s) detected during verification:")
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
