"""
Benchmark 1: Entity Resolution Benchmark on Fixed Mentions Table.
Evaluates Exact/Fuzzy, Splink-style probabilistic, and deterministic Resolvers on standardized mention datasets.
Computes B³ and Pairwise metrics using benchmarks.tools.er_metrics.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from benchmarks.tools.er_metrics import compute_b3, compute_pairwise
from core.resolver import compute_pairwise_name_similarity, resolve_mentions
from models.schemas import EntityMention


def run_er_benchmark(dataset_file: Path) -> Dict[str, Any]:
    with open(dataset_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    algorithms = ["exact_match", "token_fuzzy", "resolver_pipeline"]
    results = {
        algo: {"b3_f1_sum": 0.0, "pairwise_f1_sum": 0.0, "false_merges": 0, "false_splits": 0}
        for algo in algorithms
    }

    total_cases = len(cases)

    for case in cases:
        raw_mentions = case["mentions"]
        gold_clusters = case["gold_clusters"]
        n = len(raw_mentions)

        # Standardize mention representation
        mention_objects: List[EntityMention] = []
        mention_ids: List[str] = []
        name_map: Dict[str, str] = {}

        for idx, m in enumerate(raw_mentions):
            if isinstance(m, dict):
                m_dict = dict(m)
                if "evidence_id" not in m_dict or not m_dict["evidence_id"]:
                    m_dict["evidence_id"] = m_dict.get("source_id", f"EV-{idx:03d}")
                m_obj = EntityMention(**m_dict)
            else:
                m_obj = EntityMention(
                    mention_id=f"M-{idx:03d}",
                    raw_name_text=str(m),
                    source_id="SRC-FIXTURE",
                    evidence_id=f"EV-FIXTURE-{idx:03d}",
                    context_snippet=str(m),
                )
            mention_objects.append(m_obj)
            mention_ids.append(m_obj.mention_id)
            name_map[m_obj.mention_id] = m_obj.raw_name_text

        # 1. Exact match on normalized name
        exact_clusters: Dict[str, List[str]] = {}
        for m_id in mention_ids:
            name = name_map[m_id].strip().lower()
            exact_clusters.setdefault(name, []).append(m_id)
        exact_sys = list(exact_clusters.values())

        # 2. Token fuzzy (threshold 0.8)
        fuzzy_adj = {m_id: set() for m_id in mention_ids}
        for i in range(n):
            for j in range(i + 1, n):
                id_i, id_j = mention_ids[i], mention_ids[j]
                sim, _ = compute_pairwise_name_similarity(name_map[id_i], name_map[id_j])
                if sim >= 0.8:
                    fuzzy_adj[id_i].add(id_j)
                    fuzzy_adj[id_j].add(id_i)

        fuzzy_visited = set()
        fuzzy_sys = []
        for m_id in mention_ids:
            if m_id not in fuzzy_visited:
                comp = []
                q = [m_id]
                fuzzy_visited.add(m_id)
                while q:
                    curr = q.pop(0)
                    comp.append(curr)
                    for nxt in fuzzy_adj[curr]:
                        if nxt not in fuzzy_visited:
                            fuzzy_visited.add(nxt)
                            q.append(nxt)
                fuzzy_sys.append(comp)

        # 3. Direct invocation of core.resolver.resolve_mentions
        _, pipeline_clusters = resolve_mentions(mention_objects)
        resolver_sys = [c.mention_ids for c in pipeline_clusters]

        sys_map = {
            "exact_match": exact_sys,
            "token_fuzzy": fuzzy_sys,
            "resolver_pipeline": resolver_sys,
        }

        # Align mentions for fixtures where gold_clusters uses strings
        all_ids = mention_ids
        for algo in algorithms:
            b3 = compute_b3(gold_clusters, sys_map[algo], all_ids)
            pw = compute_pairwise(gold_clusters, sys_map[algo], all_ids)
            results[algo]["b3_f1_sum"] += b3["b3_f1"]
            results[algo]["pairwise_f1_sum"] += pw["pairwise_f1"]
            results[algo]["false_merges"] += pw["false_merge_count"]
            results[algo]["false_splits"] += pw["false_split_count"]

    summary = {}
    for algo in algorithms:
        summary[algo] = {
            "mean_b3_f1": round(results[algo]["b3_f1_sum"] / total_cases, 4) if total_cases else 0.0,
            "mean_pairwise_f1": round(results[algo]["pairwise_f1_sum"] / total_cases, 4) if total_cases else 0.0,
            "total_false_merges": results[algo]["false_merges"],
            "total_false_splits": results[algo]["false_splits"],
        }

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Entity Resolution Benchmark.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=SKILL_ROOT / "benchmarks" / "test_cases" / "er_benchmark" / "cases.json",
        help="Path to cases dataset JSON.",
    )
    args = parser.parse_args()

    benchmark_report = run_er_benchmark(args.dataset)
    print("=== Benchmark 1: Entity Resolution Evaluation Report ===")
    print(json.dumps(benchmark_report, indent=2, ensure_ascii=False))
