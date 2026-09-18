"""
Entity Resolution and Mention Detection Metrics (V4.4.1).
Implements two-layer evaluation:
Layer 1: Mention Detection Precision, Recall, F1 with mention_detection_gate.
Layer 2: B³ and Pairwise clustering metrics on common mention universe U_common,
strictly aligned with ER-Evaluation inner join semantics, and guarded by mention_universe_gate.
"""

import math
from typing import Any, Dict, List, Set, Tuple


def compute_mention_detection_metrics(
    gold_mentions: List[str],
    sys_mentions: List[str],
    threshold: float = 0.95,
) -> Dict[str, Any]:
    """
    Layer 1: Evaluates pure mention extraction performance against gold truth mentions.
    """
    gold_set = set(gold_mentions)
    sys_set = set(sys_mentions)

    if not gold_set and not sys_set:
        return {
            "detection_precision": 1.0,
            "detection_recall": 1.0,
            "detection_f1": 1.0,
            "detection_gate": True,
            "missing_gold_count": 0,
            "spurious_sys_count": 0,
        }

    intersection = gold_set.intersection(sys_set)
    prec = len(intersection) / len(sys_set) if sys_set else 0.0
    rec = len(intersection) / len(gold_set) if gold_set else 1.0
    f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    missing_count = len(gold_set - sys_set)
    spurious_count = len(sys_set - gold_set)

    return {
        "detection_precision": prec,
        "detection_recall": rec,
        "detection_f1": f1,
        "detection_gate": (rec >= threshold and prec >= threshold),
        "missing_gold_count": missing_count,
        "spurious_sys_count": spurious_count,
    }


def compute_b3(
    gold_clusters: List[List[str]],
    system_clusters: List[List[str]],
    mentions: List[str],
) -> Dict[str, float]:
    """
    Computes B-cubed Precision, Recall, and F1 on the evaluated mention universe.
    For each mention i in mentions:
      Prec(i) = |(G(i) ∩ S(i)) ∩ U| / |S(i) ∩ U|
      Rec(i)  = |(G(i) ∩ S(i)) ∩ U| / |G(i) ∩ U|
    """
    u_set = set(mentions)
    if not u_set:
        return {"b3_precision": 1.0, "b3_recall": 1.0, "b3_f1": 1.0}

    # Map each mention to its gold cluster restricted to u_set
    gold_map: Dict[str, Set[str]] = {}
    for cluster in gold_clusters:
        c_set = set(cluster).intersection(u_set)
        for m in c_set:
            gold_map[m] = c_set

    # Map each mention to its system cluster restricted to u_set
    system_map: Dict[str, Set[str]] = {}
    for cluster in system_clusters:
        c_set = set(cluster).intersection(u_set)
        for m in c_set:
            system_map[m] = c_set

    precisions = []
    recalls = []

    for m in sorted(u_set):
        g_set = gold_map.get(m, {m})
        s_set = system_map.get(m, {m})
        intersection_len = len(g_set.intersection(s_set))

        prec_i = intersection_len / len(s_set) if len(s_set) > 0 else 0.0
        rec_i = intersection_len / len(g_set) if len(g_set) > 0 else 0.0

        precisions.append(prec_i)
        recalls.append(rec_i)

    avg_prec = sum(precisions) / len(u_set)
    avg_rec = sum(recalls) / len(u_set)

    f1 = (2.0 * avg_prec * avg_rec / (avg_prec + avg_rec)) if (avg_prec + avg_rec) > 0 else 0.0

    return {
        "b3_precision": avg_prec,
        "b3_recall": avg_rec,
        "b3_f1": f1,
    }


def compute_pairwise(
    gold_clusters: List[List[str]],
    system_clusters: List[List[str]],
    mentions: List[str],
) -> Dict[str, Any]:
    """
    Computes Pairwise Precision, Recall, F1, false merge count, and false split count
    on the evaluated mention universe.
    """
    sorted_mentions = sorted(set(mentions))
    n = len(sorted_mentions)
    if n < 2:
        return {
            "pairwise_precision": 1.0,
            "pairwise_recall": 1.0,
            "pairwise_f1": 1.0,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "false_merge_count": 0,
            "false_split_count": 0,
        }

    gold_map: Dict[str, int] = {}
    for idx, cluster in enumerate(gold_clusters):
        for m in cluster:
            if m in sorted_mentions:
                gold_map[m] = idx

    system_map: Dict[str, int] = {}
    for idx, cluster in enumerate(system_clusters):
        for m in cluster:
            if m in sorted_mentions:
                system_map[m] = idx

    tp = 0
    fp = 0  # false merge
    fn = 0  # false split

    for i in range(n):
        for j in range(i + 1, n):
            m_i = sorted_mentions[i]
            m_j = sorted_mentions[j]

            gold_same = (gold_map.get(m_i) is not None and gold_map.get(m_i) == gold_map.get(m_j))
            sys_same = (system_map.get(m_i) is not None and system_map.get(m_i) == system_map.get(m_j))

            if gold_same and sys_same:
                tp += 1
            elif not gold_same and sys_same:
                fp += 1
            elif gold_same and not sys_same:
                fn += 1

    prec = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if (tp + fn) == 0 else 0.0)
    rec = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
    f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    return {
        "pairwise_precision": prec,
        "pairwise_recall": rec,
        "pairwise_f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "false_merge_count": fp,
        "false_split_count": fn,
    }
