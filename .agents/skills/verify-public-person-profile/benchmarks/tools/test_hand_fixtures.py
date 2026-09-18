"""
Unit test verifying er_metrics against the 10 hand-calculated fixtures.
"""

import json
import math
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

try:
    from er_metrics import compute_b3, compute_pairwise
except ImportError:
    from .er_metrics import compute_b3, compute_pairwise


def test_hand_fixtures():
    fixtures_file = Path(__file__).resolve().parent.parent / "test_cases" / "hand_fixtures" / "fixtures.json"
    with open(fixtures_file, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    for fix in fixtures:
        f_id = fix["fixture_id"]
        mentions = fix["mentions"]
        gold_c = fix["gold_clusters"]
        sys_c = fix["system_clusters"]
        exp = fix["expected_metrics"]

        b3_res = compute_b3(gold_c, sys_c, mentions)
        pair_res = compute_pairwise(gold_c, sys_c, mentions)

        # Check B3
        assert math.isclose(b3_res["b3_precision"], exp["b3_precision"], abs_tol=1e-5), \
            f"[{f_id}] B3 Prec mismatch: got {b3_res['b3_precision']}, expected {exp['b3_precision']}"
        assert math.isclose(b3_res["b3_recall"], exp["b3_recall"], abs_tol=1e-5), \
            f"[{f_id}] B3 Rec mismatch: got {b3_res['b3_recall']}, expected {exp['b3_recall']}"
        assert math.isclose(b3_res["b3_f1"], exp["b3_f1"], abs_tol=1e-5), \
            f"[{f_id}] B3 F1 mismatch: got {b3_res['b3_f1']}, expected {exp['b3_f1']}"

        # Check Pairwise
        assert math.isclose(pair_res["pairwise_precision"], exp["pairwise_precision"], abs_tol=1e-5), \
            f"[{f_id}] Pair Prec mismatch: got {pair_res['pairwise_precision']}, expected {exp['pairwise_precision']}"
        assert math.isclose(pair_res["pairwise_recall"], exp["pairwise_recall"], abs_tol=1e-5), \
            f"[{f_id}] Pair Rec mismatch: got {pair_res['pairwise_recall']}, expected {exp['pairwise_recall']}"
        assert math.isclose(pair_res["pairwise_f1"], exp["pairwise_f1"], abs_tol=1e-5), \
            f"[{f_id}] Pair F1 mismatch: got {pair_res['pairwise_f1']}, expected {exp['pairwise_f1']}"

        assert pair_res["false_merge_count"] == exp["false_merge_count"], \
            f"[{f_id}] False merge count mismatch: got {pair_res['false_merge_count']}, expected {exp['false_merge_count']}"
        assert pair_res["false_split_count"] == exp["false_split_count"], \
            f"[{f_id}] False split count mismatch: got {pair_res['false_split_count']}, expected {exp['false_split_count']}"

        print(f"PASS: {f_id} (B3 F1: {b3_res['b3_f1']:.4f}, Pair F1: {pair_res['pairwise_f1']:.4f})")

    print(f"\nAll {len(fixtures)} hand-calculated fixtures PASSED with 100% precision!")


if __name__ == "__main__":
    test_hand_fixtures()
