"""
Regression test for documentation rigor, terminology compliance, and absence of hyperbole.
Ensures that no agent or developer can introduce banned promotional phrasing,
phantom field names, or ungrounded claims into documentation and reports.
"""

import os
from pathlib import Path
from scripts.lint_wording import lint_files


def test_documentation_and_reports_terminology_compliance():
    skill_dir = Path(__file__).resolve().parent.parent

    # Required repository documentation files (must exist)
    required_targets = [
        skill_dir / "SKILL.md",
    ]
    reports_dir = skill_dir / "benchmarks" / "reports"
    report_files = list(reports_dir.glob("*.md")) if reports_dir.exists() else []
    assert len(report_files) > 0, "At least one benchmark report must exist for terminology validation"
    required_targets.extend(report_files)

    # Optional environment brain directory targets
    env_brain = os.environ.get("ANTIGRAVITY_BRAIN_DIR")
    if env_brain:
        bdir = Path(env_brain)
        # If ANTIGRAVITY_BRAIN_DIR is provided, both artifact docs become required
        required_targets.extend([
            bdir / "walkthrough.md",
            bdir / "implementation_plan.md",
        ])

    success, scanned_count, errors = lint_files(required_targets)
    assert success is True, f"Terminology compliance failed ({scanned_count} scanned, errors: {errors})"
    assert scanned_count >= 3, f"Expected at least 3 files scanned, got {scanned_count}"
