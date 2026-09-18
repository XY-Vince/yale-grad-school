"""
Static linter for engineering rigor, terminology compliance, and wording integrity.
Scans documentation, implementation plans, and reports to prevent hyperbole,
phantom field names, status/tense desync, and false isolation claims.

Fail-Closed Design:
- Required files that do not exist trigger an immediate failure.
- Scanning 0 files triggers an immediate failure.
- Portable: uses relative paths and CLI arguments, avoiding hardcoded personal paths.
"""

import sys
import re
import argparse
import os
from pathlib import Path

BANNED_TERMS = [
    ("彻底根治", "Use '在当前用例中已修复/阻断' or '所列测试均通过' instead of '彻底根治'"),
    ("彻底消除", "Use '所列测试均通过' or '在当前回归集内未复现' instead of '彻底消除'"),
    ("彻底解决", "Use '已落实修复' instead of '彻底解决'"),
    ("物理隔离", "Same-UID chmod 0o000 is '文件权限访问阻断', not '物理隔离'"),
    ("内核级防窥探", "Same-UID chmod 0o000 is '文件权限访问阻断', not '内核级防窥探'"),
    (r"真实测试率\s*100%", "Avoid absolute claims; state '所列反例测试均在前置通过结构校验的前提下完成业务分支验证'"),
    (r"100%\s*客观规范", "Avoid absolute claims; state '遵循限定范围与规范'"),
    ("绝无漏洞", "Scientific integrity: avoid unfalsifiable absolute claims"),
    (r"\burl_sha256\b", "Phantom field: actual implementation uses mention_key = sha256(f'{source_id}:{start}:{end}')[:16]"),
    (r"\bevidence\.payload_sha256\b", "Phantom field: actual implementation uses Evidence.raw_payload_sha256"),
    ("拟整改", "Tense mismatch: completed work must be documented as '实施记录' with past tense, not '拟整改'"),
    ("一劳永逸", "Avoid absolute claims; use '持续性检查' instead"),
    ("永久注入", "Avoid absolute claims; use '工作区规则' instead"),
    (r"任何\s*Agent", "Avoid universal quantification; use '已接入该规则的 Agent' instead"),
    ("彻底杜绝", "Avoid absolute claims; use '降低复发概率' instead"),
    ("彻底切断", "Avoid absolute claims; use '在当前扫描范围内阻断' instead"),
    ("完全隔离", "Avoid absolute claims; use '保持独立聚类' instead of '完全隔离'"),
    ("完全清除", "Avoid absolute claims; use '已过滤/已排除' instead of '完全清除'"),
    ("彻底清除", "Avoid absolute claims; use '在当前用例中已过滤' instead of '彻底清除'"),
    ("弹窗噪音已清除", "Avoid absolute claims; use '弹窗人物提及已过滤/已拦截' instead of '弹窗噪音已清除'"),
]

# Patterns that indicate a legitimate disclaimer or boundary explanation
DISCLAIMER_PREFIXES = [
    "不能称为",
    "严禁称为",
    "不属于",
    "非物理隔离",
    "而非",
    "拦截",
    "禁用词",
]


def lint_text(text: str, file_path: str = "") -> list[str]:
    violations = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        clean_line = line.strip()
        for pattern, msg in BANNED_TERMS:
            if re.search(pattern, clean_line):
                # Allow if the occurrence is part of an explicit boundary explanation or negative example
                is_disclaimer = any(prefix in clean_line for prefix in DISCLAIMER_PREFIXES)
                if not is_disclaimer:
                    violations.append(f"{file_path}:{line_idx} [VIOLATION] Found '{pattern}': {msg}\n  Line: {clean_line}")
    return violations


def lint_files(required_paths: list[Path], optional_paths: list[Path] | None = None) -> tuple[bool, int, list[str]]:
    """
    Fail-closed file linter.
    Returns (success: bool, scanned_count: int, all_errors: list[str]).
    """
    all_errors = []
    scanned_count = 0

    # 1. Required paths must exist
    for path in required_paths:
        if not path.exists():
            all_errors.append(f"[ERROR] Required file not found: {path}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
            violations = lint_text(content, str(path))
            all_errors.extend(violations)
            scanned_count += 1
        except Exception as e:
            all_errors.append(f"[ERROR] Failed to read required file {path}: {e}")

    # 2. Optional paths
    if optional_paths:
        for path in optional_paths:
            if path and path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    violations = lint_text(content, str(path))
                    all_errors.extend(violations)
                    scanned_count += 1
                except Exception as e:
                    all_errors.append(f"[ERROR] Failed to read optional file {path}: {e}")

    # 3. Fail-closed: Must have scanned at least one file
    if scanned_count == 0:
        all_errors.append("[ERROR] Fail-Closed: No files were scanned.")

    success = (len(all_errors) == 0) and (scanned_count > 0)
    return success, scanned_count, all_errors


def main():
    parser = argparse.ArgumentParser(description="Lint documentation and reports for wording rigor.")
    parser.add_argument("paths", nargs="*", type=Path, help="Explicit file paths to scan (required).")
    parser.add_argument("--optional", nargs="*", type=Path, default=[], help="Optional file paths to scan if present.")
    parser.add_argument("--brain-dir", type=Path, default=None, help="Agent artifact/brain directory.")
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parent.parent

    if args.paths:
        required = list(args.paths)
        optional = list(args.optional)
    else:
        # Default portable suite
        required = [
            skill_root / "SKILL.md",
        ]
        reports_dir = skill_root / "benchmarks" / "reports"
        if reports_dir.exists():
            report_files = list(reports_dir.glob("*.md"))
            if report_files:
                required.extend(report_files)
            else:
                required.append(reports_dir / "extraction_benchmark_report.md")
        else:
            required.append(reports_dir / "extraction_benchmark_report.md")

        optional = []
        # Check environment or CLI brain dir
        brain_dir = args.brain_dir or os.environ.get("ANTIGRAVITY_BRAIN_DIR")
        if brain_dir:
            bp = Path(brain_dir)
            # Fail-closed: if brain_dir is explicitly specified, artifact files are required
            required.append(bp / "walkthrough.md")
            required.append(bp / "implementation_plan.md")

    success, scanned_count, errors = lint_files(required, optional)
    if not success:
        print(f"FAIL: Wording / Terminology linter failed ({scanned_count} files scanned, {len(errors)} issues):")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print(f"PASS: Terminology and wording integrity verified across {scanned_count} files!")
        sys.exit(0)


if __name__ == "__main__":
    main()
