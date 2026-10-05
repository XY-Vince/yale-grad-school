#!/usr/bin/env python3
"""Mechanical SHA-256 verifier for shared files between candidate and harness repos."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

SHARED_FILES = (
    "core/text/__init__.py",
    "core/text/title_parse.py",
    "core/extractors/claim_extractor.py",
    "core/extractors/content_locator.py",
    "scripts/validate_dossier.py",
    "models/gold_schema_v2.py",
    "benchmarks/registry/prior_runs.json",
)


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_sync(candidate_skill: Path, harness_skill: Path) -> tuple[bool, list[str]]:
    mismatches: list[str] = []
    for rel_path in SHARED_FILES:
        cand_file = candidate_skill / rel_path
        harn_file = harness_skill / rel_path

        if not cand_file.is_file():
            mismatches.append(f"Missing in candidate: {rel_path}")
            continue
        if not harn_file.is_file():
            mismatches.append(f"Missing in harness: {rel_path}")
            continue

        cand_sha = compute_sha256(cand_file)
        harn_sha = compute_sha256(harn_file)
        if cand_sha != harn_sha:
            mismatches.append(f"Hash mismatch {rel_path}: cand={cand_sha[:12]} harn={harn_sha[:12]}")

    return len(mismatches) == 0, mismatches


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify repo sync between candidate and harness")
    parser.add_argument("--candidate-skill", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--harness-skill", type=Path, default=Path("/Users/xiang-yu/Desktop/ABCD/GradQuest-agent-eval-harness/.agents/skills/verify-public-person-profile"))
    args = parser.parse_args()

    ok, mismatches = verify_sync(args.candidate_skill, args.harness_skill)
    if ok:
        print(f"PASS: All {len(SHARED_FILES)} shared files are 100% byte-identical between candidate and harness.")
        return 0
    else:
        print(f"FAIL: {len(mismatches)} synchronization mismatch(es) detected:")
        for m in mismatches:
            print(f"  - {m}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
