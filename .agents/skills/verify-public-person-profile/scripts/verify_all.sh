#!/usr/bin/env bash
set -euo pipefail

CANDIDATE_DIR="/Users/xiang-yu/Desktop/GradQuest"
HARNESS_DIR="/Users/xiang-yu/Desktop/ABCD/GradQuest-agent-eval-harness"
SKILL_REL=".agents/skills/verify-public-person-profile"

echo "============================================================"
echo "POST-V10 VERIFY ALL: UNIFIED AUDIT & REGRESSION SUITE"
echo "============================================================"

echo ""
echo "[1/8] Verifying repository synchronization across shared files..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/verify_repo_sync.py"

echo ""
echo "[2/8] Running candidate repository pytest suite..."
(cd "$CANDIDATE_DIR" && python3 -m pytest -q "$SKILL_REL/tests")

echo ""
echo "[3/8] Running harness repository pytest suite..."
(cd "$HARNESS_DIR" && python3 -m pytest -q "$SKILL_REL/tests")

echo ""
echo "[4/8] Running quick structure & contract validation..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/quick_validate.py"
python3 "$HARNESS_DIR/$SKILL_REL/scripts/quick_validate.py"

echo ""
echo "[5/8] Running terminology & wording integrity linters..."
python3 "$CANDIDATE_DIR/$SKILL_REL/scripts/lint_wording.py"
python3 "$HARNESS_DIR/$SKILL_REL/scripts/lint_wording.py"

echo ""
echo "[6/8] Verifying Python bytecode compilation..."
python3 -m compileall -q "$CANDIDATE_DIR/$SKILL_REL"
python3 -m compileall -q "$HARNESS_DIR/$SKILL_REL"

echo ""
echo "[7/9] Verifying physical prior runs registry against disk..."
python3 "$HARNESS_DIR/$SKILL_REL/scripts/verify_prior_runs.py"

echo ""
echo "[8/9] Verifying git repository roots & cleanliness..."
echo "Candidate repo root: $(cd "$CANDIDATE_DIR" && git rev-parse --show-toplevel)"
CAND_PORCELAIN=$(cd "$CANDIDATE_DIR" && git status --porcelain)
if [ -n "$CAND_PORCELAIN" ]; then
    echo "ERROR: Candidate repository working tree is dirty:" >&2
    echo "$CAND_PORCELAIN" >&2
    exit 1
fi
echo "Candidate working tree: CLEAN"

echo "Harness repo root: $(cd "$HARNESS_DIR" && git rev-parse --show-toplevel)"
HARN_PORCELAIN=$(cd "$HARNESS_DIR" && git status --porcelain)
if [ -n "$HARN_PORCELAIN" ]; then
    echo "ERROR: Harness repository working tree is dirty:" >&2
    echo "$HARN_PORCELAIN" >&2
    exit 1
fi
echo "Harness working tree: CLEAN"

CAND_HEAD=$(cd "$CANDIDATE_DIR" && git rev-parse HEAD)
HARN_HEAD=$(cd "$HARNESS_DIR" && git rev-parse HEAD)
echo "Candidate HEAD: $CAND_HEAD"
echo "Harness HEAD:   $HARN_HEAD"

echo ""
echo "[9/9] Verifying runtime exposure registry integrity & monotonicity..."
python3 "$HARNESS_DIR/$SKILL_REL/scripts/verify_prior_runs.py" --check-runtime

echo ""
echo "============================================================"
echo "ALL 9 VERIFICATION CHECKS PASSED SUCCESSFULLY!"
echo "============================================================"
