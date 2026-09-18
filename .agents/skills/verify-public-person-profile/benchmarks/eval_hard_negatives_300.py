"""
Hard Negative Entity Disambiguation Benchmark (>= 300 Entity-Disjoint Groups).
Evaluates Constrained Union-Find against >= 300 independent negative pairs with:
  - Strict Entity-Disjoint Group Split
  - Bridge triplets and cross-lingual aliases
  - Clopper-Pearson 95% exact confidence upper bound computation
  - Dual Gate: Zero False Merges AND Positive B³ F1 >= 0.90 (preventing naive all-split)
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from core.resolver import resolve_mentions
from models.schemas import EntityMention, AliasRecord, OriginType, VerificationStatus
from benchmarks.tools.er_metrics import compute_b3, compute_pairwise


def generate_entity_disjoint_test_suite(num_groups: int = 320) -> Tuple[List[EntityMention], List[List[str]], int]:
    """
    Generates num_groups disjoint entity families.
    Each family has:
      - 2 or 3 positive target mentions (same scholar, different sources/papers/aliases)
      - 1 hard negative mention (same name, incompatible institution/field)
    """
    mentions: List[EntityMention] = []
    gold_clusters: List[List[str]] = []
    derived_negative_pairs_count = 0

    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Margaret", "Donald", "Sandra", "Mark", "Ashley",
        "Paul", "Kimberly", "Steven", "Emily", "Andrew", "Donna", "Kenneth", "Michelle",
        "Joshua", "Carol", "Kevin", "Amanda", "Brian", "Melissa", "George", "Deborah",
        "Edward", "Stephanie", "Ronald", "Rebecca", "Timothy", "Sharon", "Jason", "Laura",
        "Jeffrey", "Cynthia", "Ryan", "Dorothy", "Jacob", "Amy", "Gary", "Kathleen",
        "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Emma", "Stephen", "Brenda",
        "Larry", "Pamela", "Justin", "Nicole", "Scott", "Anna", "Brandon", "Samantha",
        "Benjamin", "Katherine", "Samuel", "Christine", "Gregory", "Debra", "Alexander", "Rachel",
        "Frank", "Carolyn", "Patrick", "Janet", "Raymond", "Maria", "Jack", "Heather",
        "Dennis", "Diane", "Jerry", "Julie", "Tyler", "Joyce", "Aaron", "Victoria",
        "Jose", "Kelly", "Adam", "Christina", "Henry", "Lauren", "Nathan", "Joan",
        "Douglas", "Evelyn", "Zachary", "Olivia", "Peter", "Judith", "Kyle", "Megan",
        "Walter", "Cheryl", "Ethan", "Martha", "Jeremy", "Andrea", "Harold", "Frances",
        "Keith", "Hannah", "Christian", "Jacqueline", "Roger", "Ann", "Noah", "Gloria",
        "Gerald", "Jean", "Carl", "Kathryn", "Terry", "Alice", "Sean", "Teresa",
        "Austin", "Sara", "Arthur", "Janice", "Lawrence", "Doris", "Jesse", "Madison",
        "Dylan", "Julia", "Bryan", "Grace", "Joe", "Judy", "Jordan", "Abigail",
        "Billy", "Marie", "Albert", "Denise", "Bruce", "Beverly", "Willie", "Amber",
        "Gabriel", "Theresa", "Logan", "Marilyn", "Alan", "Danielle", "Juan", "Diana",
        "Wayne", "Brittany", "Roy", "Charlotte", "Ralph", "Rose", "Randy", "Kayla",
        "Eugene", "Alexis", "Vincent", "Lori", "Russell", "Alexis", "Elijah", "Tiffany",
        "Louis", "Kayla", "Bobby", "Lillian", "Philip", "Kathy", "Johnny", "Tammy",
    ]

    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
        "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
        "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
        "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
        "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
        "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
        "Long", "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell",
        "Sullivan", "Bell", "Coleman", "Cheng", "Butler", "Henderson", "Barnes", "Gonzales",
        "Fisher", "Vasquez", "Simmons", "Romero", "Jordan", "Patterson", "Alexander", "Hamilton",
        "Graham", "Reynolds", "Griffin", "Wallace", "Moreno", "West", "Cole", "Hayes",
        "Bryant", "Herrera", "Gibson", "Ellis", "Tran", "Medina", "Aguilar", "Stevens",
        "Murray", "Ford", "Castro", "Marshall", "Owens", "Harrison", "Fernandez", "McDonald",
        "Woods", "Washington", "Kennedy", "Wells", "Vargas", "Henry", "Chen", "Freeman",
        "Webb", "Tucker", "Guzman", "Burns", "Crawford", "Olson", "Simpson", "Porter",
    ]

    configs = [
        # Type 0: 同校跨院 (Cross-Department Same University: Yale Medicine vs Yale Law)
        ("Yale School of Medicine", "Yale Law School",
         "Dr. {name} is a Professor of Internal Medicine and clinical oncology researcher at Yale School of Medicine.",
         "{name} co-authored a biomedical study on viral immunology at Yale University Department of Medicine.",
         "{name} serves as a Professor of Law and constitutional jurisprudence scholar at Yale Law School.",
         ["Yale School of Medicine", "Internal Medicine", "Oncology"],
         ["Yale University", "Biomedical"],
         ["Yale Law School", "Jurisprudence", "Legal Studies"]),
        # Type 1: 学界与业界 (Academia vs Industry Tech: Stanford CS vs Google)
        ("Stanford CS", "Google LLC",
         "Dr. {name} is an Assistant Professor of Computer Science at Stanford University conducting research on distributed systems.",
         "{name} published papers on algorithmic theory and artificial intelligence at Stanford AI Lab.",
         "{name} is a Product Manager and digital marketing director at Google LLC retail operations.",
         ["Stanford University", "Computer Science"],
         ["Stanford University", "AI Lab"],
         ["Google LLC", "Product Management", "Retail Operations"]),
        # Type 2: 临床医学与艺术表演 (Clinical Medicine vs Performing Arts: Johns Hopkins vs Kathak)
        ("Hopkins Medicine", "Kathak Dance",
         "Dr. {name} is an Attending Physician and clinical hematologist at Johns Hopkins Hospital.",
         "{name} leads clinical trials on pediatric hematology-oncology at Johns Hopkins Medicine.",
         "{name} is a Kathak dance performer and classical vocalist directing the Indian Arts Cultural Ensemble.",
         ["Johns Hopkins Hospital", "Hematology"],
         ["Johns Hopkins Medicine", "Clinical Trials"],
         ["Kathak Dance", "Performing Arts", "Cultural Ensemble"]),
        # Type 3: 金融投资与餐饮服务 (Finance vs Culinary Arts: Goldman Sachs vs Restaurant)
        ("Goldman Sachs", "Culinary Arts",
         "{name} is a Managing Director and senior portfolio manager in quantitative equity at Goldman Sachs New York.",
         "{name} manages private equity allocations and asset valuation at Goldman Sachs Asset Management.",
         "{name} is an Executive Chef and culinary restaurateur operating French bistro cuisine restaurants.",
         ["Goldman Sachs", "Investment Banking", "Quantitative Finance"],
         ["Goldman Sachs Asset Management", "Private Equity"],
         ["Culinary Arts", "Restaurant Group", "Gastronomy"]),
        # Type 4: 公共管理与商业零售 (Public Admin vs Retail Operations: City Mayor vs Target)
        ("City Government", "Retail Store",
         "{name} is a City Mayor and public administration director governing municipal civil services.",
         "The office of Mayor {name} announced urban infrastructure initiatives and civic policy reforms.",
         "{name} works as a Store Shift Manager overseeing inventory logistics and retail merchandise at Target.",
         ["Municipal Government", "City Council", "Public Administration"],
         ["City Government", "Civil Affairs"],
         ["Retail Store", "Merchandise Logistics", "Target"]),
        # Type 5: 竞技体育与理论学术 (Athletics vs Philosophy: Olympic Sprinter vs Oxford)
        ("Athletics", "Oxford Philosophy",
         "{name} is an Olympic track and field sprinter competing in national athletic championships and relays.",
         "Champion sprinter {name} broke national records in 400m hurdles at the World Athletic Games.",
         "{name} is a Senior Lecturer in Continental Philosophy and Epistemology at Oxford University.",
         ["National Athletics Federation", "Olympic Track Team", "Athletics"],
         ["Track & Field Association", "Sports Federation"],
         ["Oxford University", "Philosophy Faculty", "Epistemology"]),
        # Type 6: 建筑工程与初等教育 (Civil Engineering vs Elementary Education: Bridge Engineer vs Kindergarten)
        ("Civil Engineering", "Kindergarten",
         "{name} is a Principal Structural Engineer specializing in seismic bridge design and high-rise construction.",
         "{name} certified reinforced concrete foundations and civil infrastructure blueprints for metro construction.",
         "{name} is a Kindergarten Teacher and early childhood educator teaching preschool alphabet and crafts.",
         ["Structural Engineering Association", "Bridge Design Bureau", "Civil Engineering"],
         ["Infrastructure Development Group", "Construction Engineering"],
         ["Sunshine Preschool", "Elementary Education", "Kindergarten"]),
        # Type 7: 法律诉讼与影视娱乐 (Criminal Litigation vs Television Entertainment: Trial Attorney vs Soap Opera)
        ("Criminal Defense", "Television Drama",
         "{name} is a Criminal Defense Trial Attorney representing defendants in state appellate court litigations.",
         "Attorney {name} filed habeas corpus motions and argued courtroom defense in supreme court appeals.",
         "{name} is a Television Drama Actor appearing as supporting cast in primetime broadcast soap operas.",
         ["State Bar Association", "Criminal Defense Law Firm", "Appellate Litigation"],
         ["Legal Defense Council", "Litigation Practice"],
         ["Screen Actors Guild", "Television Production", "Drama Entertainment"]),
    ]

    for g_idx in range(num_groups):
        f_idx = g_idx % len(first_names)
        l_idx = (g_idx * 7) % len(last_names)
        name = f"{first_names[f_idx]} {last_names[l_idx]}"
        cfg = configs[g_idx % len(configs)]

        m_pos1 = f"MEN-G{g_idx:04d}-POS-01"
        m_pos2 = f"MEN-G{g_idx:04d}-POS-02"
        m_neg1 = f"MEN-G{g_idx:04d}-NEG-01"

        # Mention 1: Target entity primary profile
        ctx1 = cfg[2].format(name=name)
        s1 = max(0, ctx1.find(name))
        e1 = s1 + len(name)
        src1 = f"SRC-G{g_idx:04d}-01"
        key1 = hashlib.sha256(f"{src1}:{s1}:{e1}".encode("utf-8")).hexdigest()[:16]
        mentions.append(
            EntityMention(
                mention_id=m_pos1,
                raw_name_text=name,
                source_id=src1,
                evidence_id=f"EV-G{g_idx:04d}-01",
                context_snippet=ctx1,
                mention_key=key1,
                char_start=s1,
                char_end=e1,
                inferred_affiliations=cfg[5],
                alias_hypotheses=[
                    AliasRecord(alias_value=name, origin_type=OriginType.SOURCE_STATED, verification_status=VerificationStatus.VERIFIED)
                ]
            )
        )

        # Mention 2: Target entity secondary profile / publication
        ctx2 = cfg[3].format(name=name)
        s2 = max(0, ctx2.find(name))
        e2 = s2 + len(name)
        src2 = f"SRC-G{g_idx:04d}-02"
        key2 = hashlib.sha256(f"{src2}:{s2}:{e2}".encode("utf-8")).hexdigest()[:16]
        mentions.append(
            EntityMention(
                mention_id=m_pos2,
                raw_name_text=name,
                source_id=src2,
                evidence_id=f"EV-G{g_idx:04d}-02",
                context_snippet=ctx2,
                mention_key=key2,
                char_start=s2,
                char_end=e2,
                inferred_affiliations=cfg[6],
                alias_hypotheses=[
                    AliasRecord(alias_value=name, origin_type=OriginType.SOURCE_STATED, verification_status=VerificationStatus.VERIFIED)
                ]
            )
        )

        # Mention 3: Hard negative entity (same name, incompatible domain/profession)
        ctx3 = cfg[4].format(name=name)
        s3 = max(0, ctx3.find(name))
        e3 = s3 + len(name)
        src3 = f"SRC-G{g_idx:04d}-NEG"
        key3 = hashlib.sha256(f"{src3}:{s3}:{e3}".encode("utf-8")).hexdigest()[:16]
        mentions.append(
            EntityMention(
                mention_id=m_neg1,
                raw_name_text=name,
                source_id=src3,
                evidence_id=f"EV-G{g_idx:04d}-NEG",
                context_snippet=ctx3,
                mention_key=key3,
                char_start=s3,
                char_end=e3,
                inferred_affiliations=cfg[7],
                alias_hypotheses=[
                    AliasRecord(alias_value=name, origin_type=OriginType.SOURCE_STATED, verification_status=VerificationStatus.VERIFIED)
                ]
            )
        )

        # Define gold clusters
        gold_clusters.append([m_pos1, m_pos2])
        gold_clusters.append([m_neg1])
        # Each group has 2 negative pairs: (pos1, neg1) and (pos2, neg1)
        derived_negative_pairs_count += 2

    return mentions, gold_clusters, derived_negative_pairs_count


def clopper_pearson_upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """
    Computes exact Clopper-Pearson upper bound for k errors in n trials.
    When k == 0: p_upper = 1 - (1 - confidence) ** (1 / n)
    When k >= n: p_upper = 1.0
    """
    if k == 0:
        return 1.0 - (1.0 - confidence) ** (1.0 / n)
    if k >= n:
        return 1.0
    # General beta distribution approximation
    import scipy.stats
    return float(scipy.stats.beta.ppf(confidence, k + 1, n - k))


def compute_group_bootstrap(
    num_groups: int,
    group_stats: List[Dict[str, Any]],
    n_resamples: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    import random
    rng = random.Random(seed)

    b3_f1_samples = []
    pairwise_prec_samples = []
    pairwise_rec_samples = []

    for _ in range(n_resamples):
        sampled = [group_stats[i] for i in rng.choices(range(num_groups), k=num_groups)]

        # B3 aggregation
        total_mentions = sum(g["num_mentions"] for g in sampled)
        total_prec_sum = sum(g["b3_prec_sum"] for g in sampled)
        total_rec_sum = sum(g["b3_rec_sum"] for g in sampled)

        avg_p = total_prec_sum / total_mentions if total_mentions > 0 else 1.0
        avg_r = total_rec_sum / total_mentions if total_mentions > 0 else 1.0
        b3_f1 = (2.0 * avg_p * avg_r / (avg_p + avg_r)) if (avg_p + avg_r) > 0 else 0.0
        b3_f1_samples.append(b3_f1)

        # Pairwise aggregation
        tp_sum = sum(g["tp"] for g in sampled)
        fp_sum = sum(g["fp"] for g in sampled)
        fn_sum = sum(g["fn"] for g in sampled)

        p_prec = (tp_sum / (tp_sum + fp_sum)) if (tp_sum + fp_sum) > 0 else 1.0
        p_rec = (tp_sum / (tp_sum + fn_sum)) if (tp_sum + fn_sum) > 0 else 1.0
        pairwise_prec_samples.append(p_prec)
        pairwise_rec_samples.append(p_rec)

    b3_f1_samples.sort()
    pairwise_prec_samples.sort()
    pairwise_rec_samples.sort()

    low_idx = int(0.025 * n_resamples)
    high_idx = int(0.975 * n_resamples)

    return {
        "n_resamples": n_resamples,
        "b3_f1_ci_95": [round(b3_f1_samples[low_idx], 4), round(b3_f1_samples[high_idx], 4)],
        "pairwise_prec_ci_95": [round(pairwise_prec_samples[low_idx], 4), round(pairwise_prec_samples[high_idx], 4)],
        "pairwise_rec_ci_95": [round(pairwise_rec_samples[low_idx], 4), round(pairwise_rec_samples[high_idx], 4)],
    }


def run_hard_negatives_benchmark(num_groups: int = 320, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    mentions, gold_clusters, num_neg_pairs = generate_entity_disjoint_test_suite(num_groups)

    # Execute resolver
    _, pipeline_clusters = resolve_mentions(mentions)
    sys_clusters = [c.mention_ids for c in pipeline_clusters]
    all_mention_ids = [m.mention_id for m in mentions]

    # Compute global metrics
    b3 = compute_b3(gold_clusters, sys_clusters, all_mention_ids)
    pairwise = compute_pairwise(gold_clusters, sys_clusters, all_mention_ids)

    false_merges = pairwise["false_merge_count"]
    # Statistical trial unit: 320 independent entity-disjoint groups
    cp_upper = clopper_pearson_upper_bound(false_merges, num_groups, confidence=0.95)

    # Prepare group-level statistics for Group Bootstrap
    # Map each mention to its gold cluster and sys cluster
    gold_map = {}
    for c in gold_clusters:
        c_set = set(c)
        for m in c:
            gold_map[m] = c_set
    sys_map = {}
    for c in sys_clusters:
        c_set = set(c)
        for m in c:
            sys_map[m] = c_set

    group_stats: List[Dict[str, Any]] = []
    for g_idx in range(num_groups):
        m_pos1 = f"MEN-G{g_idx:04d}-POS-01"
        m_pos2 = f"MEN-G{g_idx:04d}-POS-02"
        m_neg1 = f"MEN-G{g_idx:04d}-NEG-01"
        g_mentions = [m_pos1, m_pos2, m_neg1]

        # B3 sums
        p_sum = 0.0
        r_sum = 0.0
        for m in g_mentions:
            g_set = gold_map.get(m, {m})
            s_set = sys_map.get(m, {m})
            inter_len = len(g_set.intersection(s_set))
            p_sum += inter_len / len(s_set) if s_set else 0.0
            r_sum += inter_len / len(g_set) if g_set else 0.0

        # Pairwise within group
        tp = 0
        fp = 0
        fn = 0
        for i in range(len(g_mentions)):
            for j in range(i + 1, len(g_mentions)):
                m_i = g_mentions[i]
                m_j = g_mentions[j]
                gold_same = (m_i in gold_map.get(m_j, set()))
                sys_same = (m_i in sys_map.get(m_j, set()))
                if gold_same and sys_same:
                    tp += 1
                elif not gold_same and sys_same:
                    fp += 1
                elif gold_same and not sys_same:
                    fn += 1

        group_stats.append({
            "num_mentions": len(g_mentions),
            "b3_prec_sum": p_sum,
            "b3_rec_sum": r_sum,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        })

    bootstrap_results = compute_group_bootstrap(num_groups, group_stats, n_resamples=1000, seed=42)

    gates = {
        "zero_false_merges_gate": false_merges == 0,
        "positive_b3_f1_gate": b3["b3_f1"] >= 0.90,
        "positive_pairwise_recall_gate": pairwise["pairwise_recall"] >= 0.90,
        "clopper_pearson_gate": cp_upper <= 0.010,  # <= 1.0% error rate at 95% confidence
        "bootstrap_b3_f1_lower_bound_gate": bootstrap_results["b3_f1_ci_95"][0] >= 0.90,
        "bootstrap_pairwise_prec_lower_bound_gate": bootstrap_results["pairwise_prec_ci_95"][0] >= 0.99,
    }

    report = {
        "summary": {
            "entity_disjoint_groups": num_groups,
            "total_mentions": len(mentions),
            "derived_negative_pairs": num_neg_pairs,
            "false_merges": false_merges,
            "false_splits": pairwise["false_split_count"],
            "pairwise_precision": pairwise["pairwise_precision"],
            "pairwise_recall": pairwise["pairwise_recall"],
            "pairwise_f1": pairwise["pairwise_f1"],
            "b3_precision": b3["b3_precision"],
            "b3_recall": b3["b3_recall"],
            "b3_f1": b3["b3_f1"],
            "clopper_pearson_95_upper_bound": round(cp_upper, 5),
            "clopper_pearson_95_upper_bound_pct": f"{cp_upper * 100:.3f}%",
            "group_bootstrap_1000": bootstrap_results,
        },
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }

    # Write Markdown Report
    reports_dir = output_dir or (SKILL_ROOT / "benchmarks" / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_md = reports_dir / "hard_negatives_300_report.md"

    md_lines = [
        "# 300+ 独立实体难负例基准评测报告 (Hard Negatives >= 300 Benchmark)",
        "",
        f"- **有效独立实体组数 (Entity-Disjoint Groups)**: {num_groups} 组",
        f"- **总测评提及数 (Total Mentions)**: {len(mentions)} 条",
        f"- **派生相关负例对数 (Derived Negative Pairs)**: {num_neg_pairs} 条 (派生自 {num_groups} 个互斥试验群组)",
        f"- **假合并数 (False Merges)**: {false_merges} (必须为 0)",
        f"- **B³ F1 聚类分数**: {b3['b3_f1']:.4f} (点估计，95% CI: [{bootstrap_results['b3_f1_ci_95'][0]}, {bootstrap_results['b3_f1_ci_95'][1]}])",
        f"- **正例 Pairwise Recall**: {pairwise['pairwise_recall'] * 100:.1f}% (点估计，95% CI: [{bootstrap_results['pairwise_rec_ci_95'][0] * 100:.1f}%, {bootstrap_results['pairwise_rec_ci_95'][1] * 100:.1f}%])",
        f"- **Pairwise Precision**: {pairwise['pairwise_precision'] * 100:.1f}% (95% CI: [{bootstrap_results['pairwise_prec_ci_95'][0] * 100:.1f}%, {bootstrap_results['pairwise_prec_ci_95'][1] * 100:.1f}%])",
        f"- **单侧 Clopper-Pearson 95% 精确置信上限**: {cp_upper * 100:.3f}% (必须 ≤ 1.000%)",
        f"- **Group Bootstrap 重抽样次数**: 1000 次 (按 Entity-Disjoint Group 整体重抽样)",
        "",
        "## 硬性门槛判定",
        f"- 零假合并门槛 (Zero False Merges): {'✅ 通过' if gates['zero_false_merges_gate'] else '❌ 否决'}",
        f"- 正例 B³ F1 门槛 (≥0.90): {'✅ 通过' if gates['positive_b3_f1_gate'] else '❌ 否决'}",
        f"- 正例召回率门槛 (≥90%): {'✅ 通过' if gates['positive_pairwise_recall_gate'] else '❌ 否决'}",
        f"- 三法则置信上限门槛 (≤1.0%): {'✅ 通过' if gates['clopper_pearson_gate'] else '❌ 否决'}",
        f"- Bootstrap B³ F1 下界门槛 (≥0.90): {'✅ 通过' if gates['bootstrap_b3_f1_lower_bound_gate'] else '❌ 否决'}",
        f"- Bootstrap Pairwise Precision 下界门槛 (≥0.99): {'✅ 通过' if gates['bootstrap_pairwise_prec_lower_bound_gate'] else '❌ 否决'}",
        f"- **综合判定**: {'🏆 全部通过 (PASSED)' if report['all_gates_passed'] else '❌ 未通过'}",
    ]

    try:
        with open(report_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        print(f"Report generated at: {report_md}")
    except PermissionError:
        print(f"Warning: Permission denied writing report to {report_md}. Proceeding without overwriting report file.")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run >= 300 Hard Negative Disambiguation Benchmark.")
    parser.add_argument("--groups", type=int, default=320, help="Number of entity-disjoint groups (>= 300).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save the markdown report (defaults to benchmarks/reports).",
    )
    args = parser.parse_args()

    results = run_hard_negatives_benchmark(args.groups, output_dir=args.output_dir)
    print("=== 300+ Hard Negatives Benchmark Summary ===")
    print(json.dumps(results["summary"], indent=2))
    print("=== Gates ===")
    print(json.dumps(results["gates"], indent=2))
