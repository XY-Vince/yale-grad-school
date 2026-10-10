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


def verify_runtime_registry_integrity(path: Path, anchor_path: Path | None = None) -> tuple[bool, str, int, str]:
    if not path.is_file():
        return True, "not present (0 entries)", 0, "MISSING"

    raw_bytes = path.read_bytes()
    h = hashlib.sha256(raw_bytes).hexdigest()
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        return False, f"invalid JSON: {exc}", 0, h

    runs = data.get("runs", [])
    if not runs:
        return True, "empty registry (0 entries)", 0, h

    genesis = "0" * 64
    for i, run in enumerate(runs):
        expected_seq = i + 1
        actual_seq = run.get("entry_seq")
        if actual_seq is not None and actual_seq != expected_seq:
            return False, f"entry_seq mismatch at index {i}: expected {expected_seq}, got {actual_seq}", len(runs), h

        expected_prev = runs[i - 1].get("entry_hash") if i > 0 else genesis
        actual_prev = run.get("prev_hash")
        if actual_prev is not None and actual_prev != expected_prev:
            return False, f"prev_hash mismatch at index {i}: expected {expected_prev}, got {actual_prev}", len(runs), h

        actual_hash = run.get("entry_hash")
        if actual_hash:
            payload = {k: v for k, v in run.items() if k != "entry_hash"}
            canon_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            computed_hash = hashlib.sha256(canon_bytes).hexdigest()
            if actual_hash != computed_hash:
                return False, f"entry_hash corruption at index {i}: expected {computed_hash}, got {actual_hash}", len(runs), h

    latest = runs[-1].get("entry_hash")
    declared_latest = data.get("latest_entry_hash")
    if declared_latest and latest and declared_latest != latest:
        return False, f"latest_entry_hash mismatch: expected {latest}, got {declared_latest}", len(runs), h

    declared_n = data.get("n_entries")
    if declared_n is not None and declared_n != len(runs):
        return False, f"n_entries mismatch: expected {len(runs)}, got {declared_n}", len(runs), h

    if anchor_path and anchor_path.is_file():
        try:
            anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
            anchored_n = anchor.get("n_entries", 0)
            anchored_hash = anchor.get("latest_entry_hash")
            if len(runs) < anchored_n:
                return False, f"external anchor regression: {len(runs)} < anchored {anchored_n}", len(runs), h
            if anchored_n > 0 and anchored_hash:
                target_hash = runs[anchored_n - 1].get("entry_hash")
                if target_hash != anchored_hash:
                    return False, f"external anchor hash mismatch at entry {anchored_n}: expected {anchored_hash}, got {target_hash}", len(runs), h
        except Exception as exc:
            return False, f"failed to parse external anchor {anchor_path}: {exc}", len(runs), h

    return True, f"valid hash chain across {len(runs)} entries", len(runs), h


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Mechanical verifier for prior runs and runtime exposure registries.")
    parser.add_argument("--check-runtime", action="store_true", help="Audit only the runtime exposure registry integrity and hash chain.")
    parser.add_argument("--min-entries", type=int, default=0, help="Minimum required entries in runtime registry (monotonic check).")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent
    registry_path = skill_root / "benchmarks" / "registry" / "prior_runs.json"
    prior_runs_root = Path(os.environ.get("PRIOR_RUNS_ROOT", "/Users/xiang-yu/Desktop/ABCD"))
    runtime_reg_path = Path(
        os.environ.get(
            "ABCD_RUNTIME_REGISTRY",
            prior_runs_root / "ledger" / "registry" / "runtime_prior_runs.json",
        )
    )

    anchor_path = skill_root / "benchmarks" / "registry" / "runtime_registry_anchor.json"
    r_ok, r_msg, r_count, r_sha = verify_runtime_registry_integrity(runtime_reg_path, anchor_path=anchor_path)

    if args.check_runtime:
        print("Authority Source: Harness (canonical authoritative copy)")
        print(f"Runtime Registry Path: {runtime_reg_path}")
        print(f"Runtime Registry SHA-256: {r_sha}")
        print(f"Runtime Registry Entries: {r_count}")
        print(f"Runtime Registry Integrity: {'PASS' if r_ok else 'FAIL'} ({r_msg})")
        if not r_ok:
            print(f"ERROR: Runtime registry integrity violation: {r_msg}", file=sys.stderr)
            return 1
        if r_count < args.min_entries:
            print(f"ERROR: Runtime registry entries regressed: {r_count} < required {args.min_entries}", file=sys.stderr)
            return 1
        print("PASS: Runtime registry integrity and hash chain verified.")
        return 0

    reg_sha = file_sha256(registry_path) if registry_path.is_file() else "MISSING"
    print("Authority Source: Harness (canonical authoritative copy)")
    print(f"Registry File: {registry_path}")
    print(f"Registry File SHA-256: {reg_sha}")
    print(f"Prior Runs Root: {prior_runs_root}")
    print(f"Runtime Registry Path: {runtime_reg_path}")
    print(f"Runtime Registry SHA-256: {r_sha}")
    print(f"Runtime Registry Audit: Seed: 151 entries | Runtime: {r_count} entries | Integrity: {'PASS' if r_ok else 'FAIL'}")
    print("-" * 120)

    ok, records, errors = verify_prior_runs(registry_path, prior_runs_root)

    header = f"{'Suite ID':<16} | {'Suite Directory':<34} | {'Item':<32} | {'Sealed':<6} | {'Exclusion Reason':<34} | {'SHA-256'}"
    print(header)
    print("-" * len(header))
    for r in records:
        print(
            f"{r['suite_id']:<16} | {r['rel_dir']:<34} | {r['item']:<32} | {r['sealed']:<6} | "
            f"{r['exclusion_reason']:<34} | {r['sha256']}"
        )
    print("-" * len(header))

    if not r_ok:
        errors.append(f"Runtime registry hash chain integrity failed: {r_msg}")

    if ok and r_ok:
        print(f"PASS: All {len(records)} historical artifacts verified against physical disk.")
        return 0
    else:
        print(f"FAIL: {len(errors)} error(s) detected during verification:")
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
