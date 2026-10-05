#!/usr/bin/env python3
"""Mechanical SHA-256 verifier and directional synchronizer for shared files between candidate and harness repos."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

# Single source of truth authority mapping.
# Authority is the repository where changes originate; Mirror is the downstream destination.
# Reverse copying (Mirror -> Authority) is strictly prohibited by protocol.
AUTHORITATIVE_SOURCES: dict[str, str] = {
    # Candidate Authority (extraction & parsing logic owned by candidate agent)
    "core/text/__init__.py": "candidate",
    "core/text/title_parse.py": "candidate",
    "core/extractors/claim_extractor.py": "candidate",
    "core/extractors/content_locator.py": "candidate",
    "scripts/validate_dossier.py": "candidate",
    # Harness Authority (benchmark evaluation schemas & historical run registry owned by harness)
    "models/gold_schema_v2.py": "harness",
    "benchmarks/registry/prior_runs.json": "harness",
}

SHARED_FILES: tuple[str, ...] = tuple(AUTHORITATIVE_SOURCES.keys())


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
            auth = AUTHORITATIVE_SOURCES[rel_path]
            mismatches.append(
                f"Hash mismatch {rel_path} (Authority: {auth}): "
                f"cand={cand_sha[:12]} harn={harn_sha[:12]}"
            )

    return len(mismatches) == 0, mismatches


def apply_directional_sync(candidate_skill: Path, harness_skill: Path) -> None:
    """Sync shared files strictly in the authoritative direction (Authority -> Mirror)."""
    for rel_path, auth in AUTHORITATIVE_SOURCES.items():
        cand_file = candidate_skill / rel_path
        harn_file = harness_skill / rel_path

        if auth == "candidate":
            src, dst = cand_file, harn_file
            src_repo, dst_repo = "candidate", "harness"
        elif auth == "harness":
            src, dst = harn_file, cand_file
            src_repo, dst_repo = "harness", "candidate"
        else:
            raise ValueError(f"Unknown authority '{auth}' for {rel_path}")

        if not src.is_file():
            raise FileNotFoundError(f"Authoritative source file missing: {src} ({src_repo})")

        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file() or compute_sha256(src) != compute_sha256(dst):
            shutil.copy2(src, dst)
            print(f"SYNC: {rel_path} copied from {src_repo} (Authority) to {dst_repo} (Mirror)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify and directionally sync shared files between candidate and harness")
    parser.add_argument("--candidate-skill", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--harness-skill",
        type=Path,
        default=Path("/Users/xiang-yu/Desktop/ABCD/GradQuest-agent-eval-harness/.agents/skills/verify-public-person-profile"),
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Directionally synchronize files from Authority to Mirror (strictly prohibited in reverse)",
    )
    args = parser.parse_args()

    if args.sync:
        print("Applying directional sync from authoritative repositories...")
        apply_directional_sync(args.candidate_skill, args.harness_skill)

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
