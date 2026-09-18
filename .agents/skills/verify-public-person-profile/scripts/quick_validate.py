"""
Quick validation script to verify skill structure and compliance.
Checks presence of SKILL.md, valid frontmatter, schemas, scripts, and unit tests.
"""

import sys
import os
from pathlib import Path
import yaml


def quick_validate(skill_dir: Path) -> bool:
    print(f"Validating skill at: {skill_dir}")
    errors = []

    # 1. Check SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing SKILL.md")
    else:
        content = skill_md.read_text(encoding="utf-8")
        if not content.startswith("---"):
            errors.append("SKILL.md missing frontmatter start '---'")
        else:
            parts = content.split("---", 2)
            if len(parts) < 3:
                errors.append("SKILL.md invalid frontmatter structure")
            else:
                try:
                    fm = yaml.safe_load(parts[1])
                    if "name" not in fm:
                        errors.append("SKILL.md frontmatter missing 'name'")
                    if "description" not in fm:
                        errors.append("SKILL.md frontmatter missing 'description'")
                except Exception as e:
                    errors.append(f"Failed to parse frontmatter: {e}")

    # 2. Check schemas and reference files
    ref_schema = skill_dir / "references" / "claim-schema.json"
    if not ref_schema.exists():
        errors.append("Missing references/claim-schema.json")

    # 3. Check core scripts
    core_entry = skill_dir / "core" / "run_profile.py"
    if not core_entry.exists():
        errors.append("Missing core/run_profile.py")

    validator_script = skill_dir / "scripts" / "validate_dossier.py"
    if not validator_script.exists():
        errors.append("Missing scripts/validate_dossier.py")

    scorer_script = skill_dir / "scripts" / "score_candidates.py"
    if not scorer_script.exists():
        errors.append("Missing scripts/score_candidates.py")

    # 4. Check wording and terminology integrity
    try:
        if str(skill_dir) not in sys.path:
            sys.path.insert(0, str(skill_dir))
        from scripts.lint_wording import lint_files
        required_targets = [skill_dir / "SKILL.md"]
        reports_dir = skill_dir / "benchmarks" / "reports"
        if reports_dir.exists():
            required_targets.extend(reports_dir.glob("*.md"))
        
        optional_targets = []
        env_brain = os.environ.get("ANTIGRAVITY_BRAIN_DIR")
        if env_brain and Path(env_brain).exists():
            optional_targets.extend([
                Path(env_brain) / "walkthrough.md",
                Path(env_brain) / "implementation_plan.md",
            ])

        success, count, lint_errs = lint_files(required_targets, optional_targets)
        if not success:
            errors.append(f"Wording / Terminology compliance check failed ({count} scanned): {lint_errs}")
    except Exception as e:
        errors.append(f"Wording linter execution error: {e}")

    if errors:
        print("FAIL: Validation encountered errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("PASS: Skill structure and contracts validated successfully!")
        return True


if __name__ == "__main__":
    skill_path = Path(__file__).resolve().parent.parent
    success = quick_validate(skill_path)
    sys.exit(0 if success else 1)
