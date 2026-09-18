"""
Benchmark 4: End-to-End Dossier Evaluation Orchestrator.
Runs pipeline over development regression fixtures, performs structural bundle validation,
computes 100-pt orthogonal rubric, gating thresholds, and generates an evaluation report.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from core.run_profile import run_pipeline
from scripts.validate_dossier import validate_bundle
from scripts.score_candidates import evaluate_dossier_bundle


DEV_REGRESSION_DIR = SKILL_ROOT / "benchmarks" / "test_cases" / "dev_regression"
DEFAULT_GOLD_FILE = DEV_REGRESSION_DIR / "cases_gold_v2.json"
GOLD_MANIFEST_FILE = DEV_REGRESSION_DIR / "gold_manifest.json"
VERSIONED_GOLD_PATTERN = re.compile(r"cases_gold_(v\d+)\.json$")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_gold_file(gold_file: Path = None) -> Path:
    """Resolve an explicit versioned Gold file; reject the ambiguous legacy alias."""
    resolved = Path(gold_file) if gold_file is not None else DEFAULT_GOLD_FILE
    if resolved.name == "cases_gold.json":
        raise ValueError(
            "Use a versioned Gold file such as cases_gold_v1.json or cases_gold_v2.json; "
            "the unversioned alias is not a valid evaluator input."
        )
    if not resolved.exists():
        raise FileNotFoundError(f"Gold truth file does not exist: {resolved}")
    return resolved.resolve()


def validate_gold_manifest(gold_file: Path) -> Dict[str, str]:
    """Verify canonical Gold bytes against the version manifest before evaluation."""
    match = VERSIONED_GOLD_PATTERN.fullmatch(gold_file.name)
    digest = _file_sha256(gold_file)
    if gold_file.parent.resolve() != DEV_REGRESSION_DIR.resolve() or not match:
        return {"version": "custom", "sha256": digest}

    if not GOLD_MANIFEST_FILE.exists():
        raise FileNotFoundError(f"Gold manifest is required: {GOLD_MANIFEST_FILE}")
    manifest = json.loads(GOLD_MANIFEST_FILE.read_text(encoding="utf-8"))
    version = match.group(1)
    entry = manifest.get("versions", {}).get(version)
    if not entry:
        raise ValueError(f"Gold version {version} is not registered in {GOLD_MANIFEST_FILE.name}")
    if entry.get("file") != gold_file.name:
        raise ValueError(f"Gold manifest file mismatch for {version}: {entry.get('file')}")
    if entry.get("sha256") != digest:
        raise ValueError(
            f"Gold hash mismatch for {version}: expected {entry.get('sha256')}, got {digest}"
        )
    return {"version": version, "sha256": digest}


def default_report_path(gold_file: Path) -> Path:
    match = VERSIONED_GOLD_PATTERN.fullmatch(gold_file.name)
    suffix = match.group(1) if match else _normalize_report_suffix(gold_file.stem)
    return SKILL_ROOT / "benchmarks" / "reports" / f"dev_regression_{suffix}_report.md"


def _normalize_report_suffix(value: str) -> str:
    suffix = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return suffix or "custom"


def compute_dir_sha256_tree(directory: Path) -> str:
    """Computes deterministic SHA-256 tree hash across all files in directory."""
    hasher = hashlib.sha256()
    for p in sorted(directory.rglob("*")):
        if p.is_file():
            hasher.update(p.relative_to(directory).as_posix().encode("utf-8"))
            with open(p, "rb") as f:
                hasher.update(hashlib.sha256(f.read()).digest())
    return hasher.hexdigest()


def run_end2end_benchmark(
    cases_file: Path,
    output_base_dir: Path,
    offline_corpus: Path = None,
    gold_file: Path = None,
    report_path: Path = None,
) -> Dict[str, Any]:
    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    gold_file = resolve_gold_file(gold_file)
    gold_metadata = validate_gold_manifest(gold_file)

    with open(gold_file, "r", encoding="utf-8") as f:
        gold_data_list = json.load(f)
    gold_data_map = {g["case_id"]: g for g in gold_data_list}

    results = []
    total_score_sum = 0.0
    passed_gates_count = 0
    total_false_merges = 0

    # File permission access blocking: strip all read/write permissions from gold_file (0o000)
    # during child process execution so that any read attempt by child receives EACCES (PermissionError).
    gold_file_abs = gold_file.resolve()
    pre_hashes = {}

    original_mode = gold_file_abs.stat().st_mode & 0o777
    chmod_applied = False
    try:
        try:
            os.chmod(gold_file_abs, 0o000)
            chmod_applied = True
            # Sentinel verification: OS kernel must deny access with PermissionError
            try:
                with open(gold_file_abs, "rb") as f:
                    raise RuntimeError(f"File permission access blocking failed: {gold_file_abs} was readable under 0o000!")
            except PermissionError:
                pass
        except OSError:
            # Environment restricts chmod operations (e.g. restricted sandbox)
            chmod_applied = False

        for case in cases:
            c_id = case["case_id"]
            t_name = case["target_name"]
            hints = case.get("known_hints", [])
            aliases = case.get("aliases", [])

            bundle_dir = output_base_dir / c_id
            bundle_dir.mkdir(parents=True, exist_ok=True)
            bundle_dir_abs = bundle_dir.resolve()

            # Phase 1: Run investigator pipeline in isolated child process (Blind, No Gold)
            cmd = [
                sys.executable,
                "-m",
                "core.run_profile",
                "--name",
                t_name,
                "--output",
                str(bundle_dir_abs),
                "--query-budget",
                "10",
            ]
            if hints:
                cmd.append("--hints")
                cmd.extend(hints)
            if aliases:
                cmd.append("--aliases")
                cmd.extend(aliases)
            if offline_corpus:
                cmd.extend(["--offline-corpus", str(offline_corpus.resolve())])

            # Clear any environment variables mentioning GOLD or EVAL to enforce blind execution
            child_env = {k: v for k, v in os.environ.items() if "GOLD" not in k.upper() and "EVAL" not in k.upper()}
            child_env["PYTHONPATH"] = str(SKILL_ROOT)

            with tempfile.TemporaryDirectory() as isolated_cwd:
                proc = subprocess.run(
                    cmd,
                    cwd=isolated_cwd,
                    env=child_env,
                    capture_output=True,
                    text=True,
                )
            if proc.returncode != 0:
                raise RuntimeError(f"Investigator child process failed for case '{c_id}':\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

            # Compute Pre-Evaluation Tree Hash of Bundle
            pre_hashes[c_id] = compute_dir_sha256_tree(bundle_dir)
    finally:
        # Restore read/write permissions for evaluator if chmod was applied
        if chmod_applied:
            try:
                os.chmod(gold_file_abs, original_mode)
            except OSError:
                pass

    # Phase 2: Evaluation against gold truth (Strictly Isolated out-of-band)
    with tempfile.TemporaryDirectory() as eval_gold_tmp:
        eval_gold_dir = Path(eval_gold_tmp)

        for case in cases:
            c_id = case["case_id"]
            t_name = case["target_name"]
            bundle_dir = output_base_dir / c_id
            pre_hash = pre_hashes[c_id]

            # 1. Structural validation
            val_res = validate_bundle(bundle_dir)

            # 2. Evaluation against gold truth
            case_gold = gold_data_map.get(c_id, case)
            case_gold_file = eval_gold_dir / f"gold_{c_id}.json"
            with open(case_gold_file, "w", encoding="utf-8") as gf:
                json.dump(case_gold, gf, indent=2, ensure_ascii=False)

            eval_dir = bundle_dir.parent / "_eval_results" / c_id
            eval_res = evaluate_dossier_bundle(bundle_dir, case_gold_file, evaluation_dir=eval_dir)

            # Compute Post-Evaluation Tree Hash of Bundle
            post_hash = compute_dir_sha256_tree(bundle_dir)
            assert pre_hash == post_hash, f"Bundle Immutability Violation in case '{c_id}': Bundle was mutated during scoring!"

            # Ensure NO gold or leak files exist in bundle_dir
            for p in bundle_dir.iterdir():
                assert "gold" not in p.name.lower(), f"Isolation breach: Gold file found in bundle: {p}"

            total_score_sum += eval_res["total_score_out_of_100"]
            if eval_res["all_gates_passed"]:
                passed_gates_count += 1
            total_false_merges += eval_res["detailed_metrics"]["false_merges"]

            case_report = {
                "case_id": c_id,
                "target_name": t_name,
                "validation_passed": val_res["is_valid"],
                "bundle_immutability_verified": pre_hash == post_hash,
                "total_score": eval_res["total_score_out_of_100"],
                "all_gates_passed": eval_res["all_gates_passed"],
                "gates": eval_res["gates"],
                "b3_f1": eval_res["detailed_metrics"]["b3_f1"],
                "false_merges": eval_res["detailed_metrics"]["false_merges"],
            }
            results.append(case_report)

        n = len(cases)
        summary = {
            "total_cases_evaluated": n,
            "gold_version": gold_metadata["version"],
            "gold_sha256": gold_metadata["sha256"],
            "gold_access_blocked": bool(chmod_applied),
            "dac_sentinel_gate": bool(chmod_applied),
            "isolation_gate": bool(chmod_applied),  # retained for backward compatibility
            "mean_total_score": round(total_score_sum / n, 2) if n > 0 else 0.0,
            "all_gates_pass_rate": round(passed_gates_count / n, 2) if n > 0 else 0.0,
            "total_false_merges_across_suite": total_false_merges,
            "bundle_immutability_verified_all": all(c["bundle_immutability_verified"] for c in results),
            "case_details": results,
        }

    # Generate Markdown Report
    report_md_path = Path(report_path) if report_path is not None else default_report_path(gold_file)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)

    md_lines = [
        "# 开发回归集端到端基准评测报告 (Dev Regression Benchmark Report)",
        "",
        f"- **评测用例总数**: {n} (收录 6 个真实人物 + 4 个历史失败去标识化夹具)",
        f"- **Gold 真值文件版本**: `{gold_file.name}`",
        f"- **Gold SHA-256**: `{gold_metadata['sha256']}`",
        f"- **DAC 权限哨兵检查 (chmod 0o000)**: {'✅ 已验证生效 (PermissionError 拦截)' if summary['dac_sentinel_gate'] else '❌ 未生效 (Fail-Closed)'}",
        f"- **DAC 哨兵门禁 (DAC Sentinel Gate)**: {'✅ 通过 (同 UID 权限拦截)' if summary['dac_sentinel_gate'] else '❌ 未通过'}",
        f"- **盲测隔离性质说明**: 本地主机同 UID 运行仅构成 DAC 哨兵检查，不构成跨进程/命名空间盲测隔离证明；受限沙箱因无权限修改操作直接 Fail-Closed 判定 FAIL。",
        f"- **平均总分 (100分制)**: {summary['mean_total_score']} / 100.0",
        f"- **硬性门槛全通率 (All Gates Pass Rate)**: {summary['all_gates_pass_rate'] * 100}%",
        f"- **全集假合并错误数 (Total False Merges)**: {total_false_merges}",
        f"- **Bundle 只读不可变性核验 (Immutability)**: {'✅ 全部一致' if summary['bundle_immutability_verified_all'] else '❌ 发生篡改'}",
        "",
        "## 用例明细评测表",
        "| 用例编号 (Case ID) | 目标人名 | 结构校验通过 | 得分 (Score) | 门槛通过 (Gates Passed) | B³ F1 | 假合并数 | 不可变性 |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for c in results:
        v_str = "✅ 是" if c["validation_passed"] else "❌ 否"
        g_str = "✅ 通过" if c["all_gates_passed"] else "⚠️ 未过门槛"
        i_str = "✅ 是" if c["bundle_immutability_verified"] else "❌ 否"
        md_lines.append(
            f"| `{c['case_id']}` | {c['target_name']} | {v_str} | {c['total_score']} | {g_str} | {c['b3_f1']:.3f} | {c['false_merges']} | {i_str} |"
        )

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Benchmark run complete. Report generated at: {report_md_path}")
    return summary


def check_benchmark_release_decision(summary: Dict[str, Any]) -> bool:
    """
    Pure decision function for Benchmark 4 release gating.
    Enforces DAC sentinel gate (chmod 0o000 EACCES check), 100% all gates pass rate (10/10),
    0 false merges, and full bundle immutability.
    Fails closed if DAC sentinel gate (dac_sentinel_gate) was not explicitly enforced as True.
    Legacy 'isolation_gate' is strictly a passive serialization field and CANNOT satisfy this decision.
    Note: Under same-UID execution, this verifies file permission access blocking,
    but does NOT constitute OS container/namespace blind test isolation proof.
    """
    return bool(
        summary.get("dac_sentinel_gate") is True
        and summary.get("isolation_gate") is not False
        and summary.get("gold_access_blocked") is True
        and summary.get("all_gates_pass_rate") == 1.0
        and summary.get("total_false_merges_across_suite") == 0
        and summary.get("bundle_immutability_verified_all") is True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run End-to-End Dossier Benchmark.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=SKILL_ROOT / "benchmarks" / "test_cases" / "dev_regression" / "cases_input.json",
        help="Path to cases input JSON file (no gold).",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=DEFAULT_GOLD_FILE,
        help="Path to gold truth JSON file (evaluator only).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional report path. Defaults to a Gold-version-specific report filename.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/dev_regression"),
        help="Base output directory for bundles.",
    )
    parser.add_argument(
        "--offline-corpus",
        type=Path,
        default=SKILL_ROOT / "benchmarks" / "test_cases" / "dev_regression" / "frozen_corpus.warc",
        help="Optional offline WARC corpus path.",
    )
    args = parser.parse_args()

    summary = run_end2end_benchmark(
        args.cases,
        args.output_dir,
        args.offline_corpus,
        gold_file=args.gold,
        report_path=args.report,
    )
    print("=== Benchmark 4 Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    all_passed = check_benchmark_release_decision(summary)
    if not all_passed:
        print(
            f"FAIL: Benchmark 4 release gates not fully satisfied (isolation_gate: {summary.get('isolation_gate')}, "
            f"gold_access_blocked: {summary.get('gold_access_blocked')}, "
            f"pass_rate: {summary.get('all_gates_pass_rate')}, "
            f"false_merges: {summary.get('total_false_merges_across_suite')}, "
            f"immutability: {summary.get('bundle_immutability_verified_all')})",
            file=sys.stderr,
        )
        sys.exit(1)
