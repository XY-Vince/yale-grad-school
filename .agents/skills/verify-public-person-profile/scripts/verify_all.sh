#!/usr/bin/env bash
set -euo pipefail

CANDIDATE_DIR="/Users/xiang-yu/Desktop/GradQuest"
HARNESS_DIR="/Users/xiang-yu/Desktop/ABCD/GradQuest-agent-eval-harness"
SKILL_REL=".agents/skills/verify-public-person-profile"

echo "============================================================"
echo "POST-V10 VERIFY ALL: UNIFIED AUDIT & REGRESSION SUITE"
echo "============================================================"

echo ""
echo "[1/7] Verifying repository synchronization across shared files..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/verify_repo_sync.py"

echo ""
echo "[2/7] Running candidate repository pytest suite..."
(cd "$CANDIDATE_DIR" && python3 -m pytest -q "$SKILL_REL/tests")

echo ""
echo "[3/7] Running harness repository pytest suite..."
(cd "$HARNESS_DIR" && python3 -m pytest -q "$SKILL_REL/tests")

echo ""
echo "[4/7] Running quick structure & contract validation..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/quick_validate.py"
python3 "$HARNESS_DIR/$SKILL_REL/scripts/quick_validate.py"

echo ""
echo "[5/7] Running terminology & wording integrity linters..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/lint_wording.py"
python3 "$HARNESS_DIR/$SKILL_REL/scripts/lint_wording.py"

echo ""
echo "[6/7] Verifying Python bytecode compilation..."
python3 -m compileall -q "$CANDIDATE_DIR/$SKILL_REL"
python3 -m compileall -q "$HARNESS_DIR/$SKILL_REL"

echo ""
echo "[7/7] Verifying git repository roots & status..."
echo "Candidate repo root: $(cd "$CANDIDATE_DIR" && git rev-parse --show-toplevel)"
echo "Candidate status porcelain:"
(cd "$CANDIDATE_DIR" && git status --porcelain)
echo "Harness repo root: $(cd "$HARNESS_DIR" && git rev-parse --show-toplevel)"
echo "Harness status porcelain:"
(cd "$HARNESS_DIR" && git status --porcelain)

echo ""
echo "============================================================"
echo "ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!"
echo "============================================================"
