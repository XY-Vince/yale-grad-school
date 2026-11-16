"""One-shot Blind V2 G2/G3 runner with investigator/evaluator separation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


SKILL_ROOT = Path(__file__).resolve().parents[2]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from benchmarks.tools.evaluator_v2_4 import compute_bundle_tree_hash
from models.blind_protocol import BlindPersonaManifest, BlindPreregistration
from scripts.validate_dossier import validate_bundle


INVESTIGATOR_ASSETS = (
    "case_manifest.json",
    "corpus.warc",
    "query_index.jsonl",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seatbelt_escape(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def build_seatbelt_profile(hidden_assets_dir: Path) -> str:
    hidden = _seatbelt_escape(hidden_assets_dir)
    return "\n".join(
        [
            "(version 1)",
            "(allow default)",
            f'(deny file-read* (subpath "{hidden}"))',
            f'(deny file-write* (subpath "{hidden}"))',
        ]
    )


def ensure_new_workspace(workspace: Path) -> None:
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(f"execution workspace is not empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)


def stage_investigator_assets(hidden_assets_dir: Path, staging_dir: Path) -> dict[str, str]:
    if staging_dir.exists() and any(staging_dir.iterdir()):
        raise FileExistsError(f"investigator staging directory is not empty: {staging_dir}")
    staging_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for filename in INVESTIGATOR_ASSETS:
        source = hidden_assets_dir / filename
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"investigator asset must be a regular file: {filename}")
        destination = staging_dir / filename
        shutil.copyfile(source, destination)
        copied[filename] = sha256_file(destination)
    if set(path.name for path in staging_dir.iterdir()) != set(INVESTIGATOR_ASSETS):
        raise ValueError("investigator staging contains undeclared files")
    return copied


def build_pipeline_command(
    *,
    sandbox_exec: str,
    seatbelt_profile: str,
    persona: Any,
    output_dir: Path,
    corpus_path: Path,
    query_budget: int,
    enable_target_prior: bool,
) -> list[str]:
    command = [
        sandbox_exec,
        "-p",
        seatbelt_profile,
        sys.executable,
        str(SKILL_ROOT / "core" / "run_profile.py"),
        "--name",
        persona.target_name,
        "--output-dir",
        str(output_dir),
        "--offline-corpus",
        str(corpus_path),
        "--query-budget",
        str(query_budget),
    ]
    if persona.hints:
        command.extend(["--hints", *persona.hints])
    if persona.aliases:
        command.extend(["--aliases", *persona.aliases])
    if enable_target_prior:
        command.append("--enable-target-prior")
    return command


def verify_seatbelt_boundary(
    sandbox_exec: str,
    seatbelt_profile: str,
    hidden_gold: Path,
    staged_corpus: Path,
) -> None:
    probe = "from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()"
    denied = subprocess.run(
        [sandbox_exec, "-p", seatbelt_profile, sys.executable, "-c", probe, str(hidden_gold)],
        capture_output=True,
        text=True,
    )
    if denied.returncode == 0:
        raise RuntimeError("Seatbelt probe could read hidden Gold")
    allowed = subprocess.run(
        [sandbox_exec, "-p", seatbelt_profile, sys.executable, "-c", probe, str(staged_corpus)],
        capture_output=True,
        text=True,
    )
    if allowed.returncode != 0:
        raise RuntimeError("Seatbelt probe could not read staged investigator corpus")


def write_bundle_seal(bundle_dir: Path, case_id: str, track: str) -> dict[str, str]:
    seal_path = bundle_dir / "seal.json"
    if seal_path.exists():
        raise FileExistsError(f"bundle already has a seal: {seal_path}")
    tree_hash = compute_bundle_tree_hash(bundle_dir)
    payload = {
        "case_id": case_id,
        "track": track,
        "bundle_tree_hash": tree_hash,
    }
    seal_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def write_result_receipt(
    ledger_dir: Path,
    suite_id: str,
    *,
    status: str,
    evaluation_json: Path | None = None,
    error: str | None = None,
) -> Path:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = ledger_dir / f"{suite_id}.result.json"
    payload: dict[str, Any] = {
        "suite_id": suite_id,
        "status": status,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if evaluation_json and evaluation_json.is_file():
        payload["evaluation_json_sha256"] = sha256_file(evaluation_json)
        evaluation = json.loads(evaluation_json.read_text(encoding="utf-8"))
        payload["all_gates_passed"] = bool(evaluation.get("all_gates_passed"))
        payload["evaluation_decision"] = evaluation.get("evaluation_decision")
    if error:
        payload["error"] = error
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(receipt_path, flags, 0o600)
    except FileExistsError as exc:
        raise FileExistsError(f"result receipt already exists for suite {suite_id}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    return receipt_path


def _run_logged(command: Sequence[str], log_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"})
    completed = subprocess.run(
        list(command),
        cwd=SKILL_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        completed.stdout + ("\n[stderr]\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    return completed


def _nonce(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"empty nonce file: {path}")
    return value


def build_reveal_command(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(SKILL_ROOT / "benchmarks" / "tools" / "blind_v2_protocol.py"),
        "verify-reveal",
        "--preregistration",
        str(args.preregistration),
        "--seed-file",
        str(args.seed_file),
        "--seed-nonce",
        _nonce(args.seed_nonce_file),
        "--candidate-pool",
        str(args.candidate_pool),
        "--pool-nonce",
        _nonce(args.pool_nonce_file),
        "--selection-manifest",
        str(args.selection_manifest),
        "--selection-nonce",
        _nonce(args.selection_nonce_file),
        "--exclusion-registry",
        str(args.exclusion_registry),
        "--exclusion-nonce",
        _nonce(args.exclusion_nonce_file),
        "--curator-attestation",
        str(args.curator_attestation),
        "--attestation-nonce",
        _nonce(args.attestation_nonce_file),
        "--hidden-asset-manifest",
        str(args.hidden_assets_dir / "asset_manifest.json"),
        "--hidden-assets-nonce",
        _nonce(args.hidden_assets_nonce_file),
        "--hidden-assets-dir",
        str(args.hidden_assets_dir),
        "--repo-root",
        str(args.repo_root),
        "--evaluator-file",
        str(SKILL_ROOT / "benchmarks" / "tools" / "evaluator_v2_4.py"),
        "--gold-schema-file",
        str(SKILL_ROOT / "models" / "gold_schema_v2.py"),
        "--consume-ledger-dir",
        str(args.ledger_dir),
    ]


def execute(args: argparse.Namespace) -> int:
    prereg = BlindPreregistration.model_validate_json(
        args.preregistration.read_text(encoding="utf-8")
    )
    sandbox_exec = shutil.which("sandbox-exec")
    if prereg.investigator_isolation_backend == "macos_seatbelt" and not sandbox_exec:
        raise RuntimeError("sandbox-exec is required by the preregistered isolation backend")
    assert sandbox_exec is not None

    ensure_new_workspace(args.workspace)
    staging_dir = args.workspace / "investigator_input"
    stage_investigator_assets(args.hidden_assets_dir, staging_dir)
    seatbelt_profile = build_seatbelt_profile(args.hidden_assets_dir)
    verify_seatbelt_boundary(
        sandbox_exec,
        seatbelt_profile,
        args.hidden_assets_dir / "gold.json",
        staging_dir / "corpus.warc",
    )

    reveal = _run_logged(
        build_reveal_command(args),
        args.workspace / "logs" / "reveal.log",
    )
    if reveal.returncode != 0:
        raise RuntimeError("reveal verification failed before the one-shot execution claim")

    case_manifest = BlindPersonaManifest.model_validate_json(
        (staging_dir / "case_manifest.json").read_text(encoding="utf-8")
    )
    evaluation_json = args.workspace / "evaluation" / "blind_v2.json"
    try:
        for track, prior_enabled in (("g2", False), ("g3", True)):
            for persona in case_manifest.entries:
                bundle_dir = args.workspace / "runs" / track / persona.case_id
                command = build_pipeline_command(
                    sandbox_exec=sandbox_exec,
                    seatbelt_profile=seatbelt_profile,
                    persona=persona,
                    output_dir=bundle_dir,
                    corpus_path=staging_dir / "corpus.warc",
                    query_budget=prereg.query_budget_per_case,
                    enable_target_prior=prior_enabled,
                )
                result = _run_logged(
                    command,
                    args.workspace / "logs" / f"{track}-{persona.case_id}.log",
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"investigator failed for {track}/{persona.case_id}; one-shot attempt is consumed"
                    )
                validation = validate_bundle(bundle_dir, warc_path=staging_dir / "corpus.warc")
                if not validation["is_valid"]:
                    raise RuntimeError(
                        f"bundle validation failed for {track}/{persona.case_id}: {validation['errors']}"
                    )
                write_bundle_seal(bundle_dir, persona.case_id, track)

        evaluation_md = args.workspace / "evaluation" / "blind_v2.md"
        evaluator_command = [
            sys.executable,
            str(SKILL_ROOT / "benchmarks" / "tools" / "evaluator_v2_4.py"),
            "--runs-dir",
            str(args.workspace / "runs" / "g3"),
            "--gold-file",
            str(args.hidden_assets_dir / "gold.json"),
            "--case-manifest",
            str(args.hidden_assets_dir / "case_manifest.json"),
            "--expected-count",
            str(prereg.expected_case_count),
            "--warc-file",
            str(args.hidden_assets_dir / "corpus.warc"),
            "--query-index",
            str(args.hidden_assets_dir / "query_index.jsonl"),
            "--asset-manifest",
            str(args.hidden_assets_dir / "asset_manifest.json"),
            "--preregistration",
            str(args.preregistration),
            "--track-name",
            "hinted",
            "--evaluation-role",
            "blind_release",
            "--paired-runs-dir",
            str(args.workspace / "runs" / "g2"),
            "--output-json",
            str(evaluation_json),
            "--output-md",
            str(evaluation_md),
        ]
        evaluated = _run_logged(
            evaluator_command,
            args.workspace / "logs" / "evaluator.log",
        )
        if not evaluation_json.is_file():
            raise RuntimeError("Evaluator did not produce its required JSON result")
        receipt = write_result_receipt(
            args.ledger_dir,
            prereg.suite_id,
            status="completed",
            evaluation_json=evaluation_json,
        )
        print(json.dumps({
            "suite_id": prereg.suite_id,
            "evaluator_exit_code": evaluated.returncode,
            "result_receipt": str(receipt),
            "result_receipt_sha256": sha256_file(receipt),
        }, indent=2))
        return evaluated.returncode
    except Exception as exc:
        write_result_receipt(
            args.ledger_dir,
            prereg.suite_id,
            status="execution_failed",
            evaluation_json=evaluation_json if evaluation_json.exists() else None,
            error=f"{type(exc).__name__}: {exc}",
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute Blind Release V2 exactly once")
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--seed-file", type=Path, required=True)
    parser.add_argument("--seed-nonce-file", type=Path, required=True)
    parser.add_argument("--candidate-pool", type=Path, required=True)
    parser.add_argument("--pool-nonce-file", type=Path, required=True)
    parser.add_argument("--selection-manifest", type=Path, required=True)
    parser.add_argument("--selection-nonce-file", type=Path, required=True)
    parser.add_argument("--exclusion-registry", type=Path, required=True)
    parser.add_argument("--exclusion-nonce-file", type=Path, required=True)
    parser.add_argument("--curator-attestation", type=Path, required=True)
    parser.add_argument("--attestation-nonce-file", type=Path, required=True)
    parser.add_argument("--hidden-assets-dir", type=Path, required=True)
    parser.add_argument("--hidden-assets-nonce-file", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--ledger-dir", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args))


if __name__ == "__main__":
    main()
