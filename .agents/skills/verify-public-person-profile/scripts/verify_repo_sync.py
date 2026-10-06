#!/usr/bin/env python3
"""Mechanical SHA-256 verifier and directional synchronizer for shared files between candidate and harness repos."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import shutil
import subprocess
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
    "tests/test_title_parse.py": "candidate",
    "scripts/verify_repo_sync.py": "candidate",
    "scripts/verify_all.sh": "candidate",
    # Harness Authority (benchmark evaluation schemas & historical run registry owned by harness)
    "models/gold_schema_v2.py": "harness",
    "benchmarks/registry/prior_runs.json": "harness",
    "scripts/verify_prior_runs.py": "harness",
}

SHARED_FILES: tuple[str, ...] = tuple(AUTHORITATIVE_SOURCES.keys())


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _is_git_clean(repo_path: Path) -> bool:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and not res.stdout.strip()


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


def show_diff(src: Path, dst: Path, rel_path: str) -> None:
    src_lines = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    dst_lines = dst.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if dst.is_file() else []
    diff = difflib.unified_diff(
        dst_lines,
        src_lines,
        fromfile=f"mirror:{rel_path}",
        tofile=f"authority:{rel_path}",
    )
    diff_text = "".join(diff)
    if diff_text:
        print(f"--- Diff for {rel_path} ---")
        print(diff_text)


def apply_directional_sync(
    candidate_skill: Path,
    harness_skill: Path,
    apply: bool = False,
    force: bool = False,
) -> None:
    """Sync shared files strictly in the authoritative direction (Authority -> Mirror)."""
    cand_repo = candidate_skill.parents[2]
    harn_repo = harness_skill.parents[2]

    for rel_path, auth in AUTHORITATIVE_SOURCES.items():
        cand_file = candidate_skill / rel_path
        harn_file = harness_skill / rel_path

        if auth == "candidate":
            src, dst = cand_file, harn_file
            src_repo_name, dst_repo_name = "candidate", "harness"
            dst_repo_root = harn_repo
        elif auth == "harness":
            src, dst = harn_file, cand_file
            src_repo_name, dst_repo_name = "harness", "candidate"
            dst_repo_root = cand_repo
        else:
            raise ValueError(f"Unknown authority '{auth}' for {rel_path}")

        if not src.is_file():
            raise FileNotFoundError(f"Authoritative source file missing: {src} ({src_repo_name})")

        needs_sync = not dst.is_file() or compute_sha256(src) != compute_sha256(dst)
        if needs_sync:
            show_diff(src, dst, rel_path)
            if apply:
                if force:
                    print(
                        f"WARNING: --force specified: bypassing clean destination repository check on {dst_repo_root}!",
                        file=sys.stderr,
                    )
                elif not _is_git_clean(dst_repo_root):
                    raise RuntimeError(
                        f"Refusing to sync to dirty destination repository {dst_repo_root}. "
                        "Commit or stash changes before applying sync, or specify --force."
                    )
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"SYNC APPLIED: {rel_path} copied from {src_repo_name} (Authority) to {dst_repo_name} (Mirror)")
            else:
                print(f"DRY RUN: {rel_path} differs between {src_repo_name} (Authority) and {dst_repo_name} (Mirror). Use --apply to copy.")


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
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to disk (default is dry-run mode)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing to dirty destination repository (use with caution)",
    )
    args = parser.parse_args()

    if args.sync or args.apply:
        print(f"Checking directional sync (apply={args.apply})...")
        apply_directional_sync(args.candidate_skill, args.harness_skill, apply=args.apply, force=args.force)

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
