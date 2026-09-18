"""
Benchmark 2: Snapshot and Minimal Contrast Pair Claim Extraction Benchmark (V4.7).
Evaluates strict predicate/object/subject/polarity/temporal joint matches and
noise rejection against frozen snapshots. Relaxed relation metrics are diagnostic.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from core.extractors.claim_extractor import extract_claims_from_evidence
from core.extractors.mention_extractor import extract_mentions_and_aliases
from core.extractors.subject_attribution import (
    is_exact_or_verified_alias_match,
    GPE_TOKENS,
    AWARD_AND_WORK_TOKENS,
    DIRECTIONAL_OR_GEOGRAPHIC_MODIFIERS,
    ALL_COMMON_FIRST_NAMES,
)
from models.schemas import Evidence, EvidenceLocator, LocatorType, SourceQualityClass, VerificationStatus
from datetime import datetime, timezone


def is_likely_person_name(name: str) -> bool:
    name_clean = name.strip()
    toks = [t.lower() for t in re.findall(r"[A-Za-z]+", name_clean)]
    if not toks:
        return False
    if any(t in AWARD_AND_WORK_TOKENS for t in toks) and not any(t in ALL_COMMON_FIRST_NAMES for t in toks):
        return False
    if any(t in GPE_TOKENS for t in toks) and not any(t in ALL_COMMON_FIRST_NAMES for t in toks):
        return False
    if len(toks) >= 2 and toks[0] in DIRECTIONAL_OR_GEOGRAPHIC_MODIFIERS and toks[-1] in GPE_TOKENS:
        return False
    return True


STRICT_GATE_THRESHOLD = 0.95
_NAME_TOKEN = r"[A-Z\u00C0-\u024F][^\W\d_]*(?:[-'][A-Z\u00C0-\u024F]?[^\W\d_]*)*"
PERSON_NAME_PATTERN = (
    rf"((?:(?:Prof\.|Dr\.|President|Dean|Director)\s+{_NAME_TOKEN}(?:\s+{_NAME_TOKEN})*)|(?:{_NAME_TOKEN}(?:\s+{_NAME_TOKEN})+))"
)
TRANSITIVE_VERBS_PATTERN = (
    r"(?:"
    r"thanked|emailed|called|hired|advised|supervised|employed|appointed|awarded|"
    r"directed|managed|criticized|praised|invited|visited|interviewed|met|contacted|"
    r"helped|greeted|congratulated|joined|funded|trained|mentored|nominated|elected|"
    r"told|gave|saw|taught|led|sent|bought|found|heard|chose|paid|brought|caught|"
    r"wrote|read|fed|made|kept|held|hit|left|lost|set|took|won|understood|"
    r"[a-z]{3,}ed"
    r")"
)
ZH_TRANSITIVE_PATTERN = r"(?:聘请|指导|雇佣|任命|授予|采访|会见|批评|表扬|感谢|致信|致电|帮助|祝贺|培训|告知|给予|看见|领导|教授|推荐)"




def _normalize_match_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    return " ".join(normalized.split())


def strict_object_match(extracted_object: str, gold_claim: Dict[str, Any]) -> bool:
    """Require exact normalized object identity or an explicit gold equivalence."""
    extracted = _normalize_match_text(extracted_object)
    accepted = {
        _normalize_match_text(gold_claim.get("object_raw", "")),
        *(
            _normalize_match_text(value)
            for value in gold_claim.get("equivalence_set", [])
        ),
    }
    accepted.discard("")
    return bool(extracted and extracted in accepted)


def clause_has_target_subject(
    clause: str,
    target_name: str,
    full_context: Optional[str] = None,
    subject_mention_id: Optional[str] = None,
    known_mention_ids: Optional[Set[str]] = None,
) -> bool:
    """
    Check a full target mention or a strictly corroborated anaphoric subject.
    Enforces:
    1. subject_mention_id validity if supplied (must match MEN-[a-f0-9]{12} and exist in known_mention_ids).
    2. Heuristic object exclusion: Rejects clauses where target appears in object position of another subject's transitive action.
    3. Heuristic syntactic prominence in discourse: If target was an object in the preceding sentence, target is not an eligible subject antecedent.
    4. Standalone pronoun clauses without target antecedent are strictly rejected.
    5. Enforces nearest preceding subject coreference in full_context.

    Note: Benchmark 2 metrics reflect evaluation against the curated regression fixture and minimal contrast pairs;
    they do not constitute an open-domain generic SVO parsing oracle.
    """
    if not clause or not target_name:
        return False

    # 1. Validate subject_mention_id if explicitly supplied
    if subject_mention_id is not None:
        if not isinstance(subject_mention_id, str) or not re.match(r"^MEN-[a-f0-9]{12}$", subject_mention_id):
            return False
        if known_mention_ids is not None and subject_mention_id not in known_mention_ids:
            return False

    c_clean = clause.strip()
    t_clean = target_name.strip()

    is_zh = any("\u4e00" <= char <= "\u9fff" for char in t_clean)
    if is_zh:
        name_pat = r"\s*".join(re.escape(c) for c in t_clean)
    else:
        target_tokens = [re.escape(token) for token in t_clean.split()]
        if not target_tokens:
            return False
        name_pat = r"(?<!\w)" + r"\s+".join(target_tokens) + r"(?!\w)"

    target_in_clause = bool(re.search(name_pat, c_clean, re.IGNORECASE))

    if target_in_clause:
        # 2. Object exclusion: If another named entity precedes target, check if target is in predicate/object position
        # e.g., "Bob Smith thanked Alice Wang", "Bob Smith emailed Alice Wang", "Prof. Davis advised Alice Wang"
        if not is_zh:
            other_lead = re.search(
                rf"\b{PERSON_NAME_PATTERN}\b(.*?)" + name_pat,
                c_clean,
            )
            if other_lead:
                other_name = other_lead.group(1).strip()
                intervening = other_lead.group(2).strip()
                if is_likely_person_name(other_name) and not is_exact_or_verified_alias_match(target_name, other_name) and not re.search(name_pat, other_name, re.IGNORECASE):
                    # Check if intervening indicates coordinating conjunction (compound subject)
                    is_coordination = bool(re.match(r"^(?:and|&|with|as well as|,)\b", intervening, re.IGNORECASE))
                    has_transitive_action = bool(
                        re.search(
                            rf"\b{TRANSITIVE_VERBS_PATTERN}\b",
                            intervening,
                            re.IGNORECASE,
                        )
                    )
                    if has_transitive_action and not is_coordination:
                        return False

        if is_zh:
            zh_lead = re.search(
                rf"([\u4e00-\u9fff]{{2,4}})\s*(.*?)" + name_pat,
                c_clean,
            )
            if zh_lead:
                other_zh = zh_lead.group(1).strip()
                intervening = zh_lead.group(2).strip()
                if not re.search(name_pat, other_zh):
                    is_zh_coord = bool(re.match(r"^(?:和|与|以及|同|兼|,|，)\s*", intervening))
                    has_zh_action = bool(re.search(ZH_TRANSITIVE_PATTERN, intervening))
                    if has_zh_action or not is_zh_coord:
                        return False

        # If another entity is explicitly the subject of the clause followed by a verb:
        other_person_match = re.search(
            rf"\b{PERSON_NAME_PATTERN}\s+(?:is|was|has|had|graduated|received|joined|studied|served|earned|worked|said|stated|reported)\b",
            c_clean,
        )
        if other_person_match:
            other_name = other_person_match.group(1).strip()
            if is_likely_person_name(other_name) and not is_exact_or_verified_alias_match(target_name, other_name) and not re.search(name_pat, other_name, re.IGNORECASE):
                return False

        return True

    # 3. Target not in clause: check for anaphoric pronoun or Chinese pro-drop predicate connector
    has_pronoun = bool(
        re.search(r"\b(?:she|he|they|her|his|their|i|my)\b|(?:其|该学者|该专家)", c_clean, re.IGNORECASE)
        or (is_zh and re.match(r"^(?:现任|曾任|兼任|担任|现为|曾为|目前|随后|并|同时)", c_clean))
    )
    if not has_pronoun:
        return False

    # 4. Strict Anaphoric Coreference:
    context_to_search = full_context or ""
    clause_idx = context_to_search.find(clause) if (full_context and clause in full_context) else -1
    preceding_text = context_to_search[:clause_idx] if clause_idx > 0 else ""

    if not preceding_text:
        # No preceding context: check if target appeared earlier within the same compound clause
        intra_target = [m.end() for m in re.finditer(name_pat, c_clean, re.IGNORECASE)]
        if not intra_target:
            # Standalone pronoun with zero antecedent -> strictly reject!
            return False

    target_positions = [m.end() for m in re.finditer(name_pat, preceding_text, re.IGNORECASE)] if preceding_text else []
    if not target_positions:
        # Preceding context exists, but target name never appeared -> strictly reject!
        return False

    # Discourse syntactic prominence check:
    # If in the sentence immediately preceding the clause, target appeared as an OBJECT of another subject's action
    # (e.g. "Bob Smith emailed Alice Wang."), target was syntactically subordinated and is NOT an eligible subject antecedent.
    if preceding_text and not is_zh:
        sentences = [s.strip() for s in re.split(r"[.!?]\s*", preceding_text) if s.strip()]
        if sentences:
            last_sentence = sentences[-1]
            if re.search(name_pat, last_sentence, re.IGNORECASE):
                other_subj_match = re.search(
                    rf"\b{PERSON_NAME_PATTERN}\b(.*?)" + name_pat,
                    last_sentence,
                )
                if other_subj_match:
                    other_name = other_subj_match.group(1).strip()
                    intervening = other_subj_match.group(2).strip()
                    if is_likely_person_name(other_name) and not is_exact_or_verified_alias_match(target_name, other_name) and not re.search(name_pat, other_name, re.IGNORECASE):
                        has_transitive_action = bool(
                            re.search(
                                rf"\b{TRANSITIVE_VERBS_PATTERN}\b",
                                intervening,
                                re.IGNORECASE,
                            )
                        )
                        is_coord = bool(re.match(r"^(?:and|&|with|as well as|,)\b", intervening, re.IGNORECASE))
                        if has_transitive_action and not is_coord:
                            # Target was object of other_name in the preceding sentence -> reject!
                            return False

    other_names_matches = [
        m for m in re.finditer(rf"\b{PERSON_NAME_PATTERN}\b", preceding_text)
        if is_likely_person_name(m.group(0))
        and not is_exact_or_verified_alias_match(target_name, m.group(0))
        and not re.search(name_pat, m.group(0), re.IGNORECASE)
    ]
    if other_names_matches:
        last_other_end = max(m.end() for m in other_names_matches)
        last_target_end = max(target_positions)
        if last_other_end > last_target_end:
            # Another entity intervened as the nearest subject antecedent -> reject!
            return False

    # Intra-clause cross-entity antecedent check
    if not is_zh:
        intra_other = re.search(
            rf"\b{PERSON_NAME_PATTERN}\b.*?\b(?:she|he|they|her|his|their)\b",
            c_clean,
            re.DOTALL,
        )
        if intra_other:
            other_name = intra_other.group(1).strip()
            if is_likely_person_name(other_name) and not is_exact_or_verified_alias_match(target_name, other_name) and not re.search(name_pat, other_name, re.IGNORECASE):
                return False

    return True


def build_extraction_gates(
    *,
    polarity_accuracy: float,
    temporal_accuracy: float,
    subject_attribution_accuracy: float,
    noise_false_positive_rate: float,
    relation_precision: float,
    relation_recall: float,
    relation_f1: float,
    joint_5d_precision: float,
    joint_5d_recall: float,
    joint_5d_f1: float,
) -> Dict[str, bool]:
    """Build component gates and the strict 5D release gate."""
    gates = {
        "polarity_accuracy_gate": polarity_accuracy >= STRICT_GATE_THRESHOLD,
        "temporal_accuracy_gate": temporal_accuracy >= STRICT_GATE_THRESHOLD,
        "subject_attribution_gate": subject_attribution_accuracy >= STRICT_GATE_THRESHOLD,
        "noise_rejection_gate": noise_false_positive_rate == 0.0,
        "relation_precision_gate": relation_precision >= STRICT_GATE_THRESHOLD,
        "relation_recall_gate": relation_recall >= STRICT_GATE_THRESHOLD,
        "relation_f1_gate": relation_f1 >= STRICT_GATE_THRESHOLD,
        "joint_5d_precision_gate": joint_5d_precision >= STRICT_GATE_THRESHOLD,
        "joint_5d_recall_gate": joint_5d_recall >= STRICT_GATE_THRESHOLD,
        "joint_5d_f1_gate": joint_5d_f1 >= STRICT_GATE_THRESHOLD,
    }
    gates["strict_5d_release_gate"] = all(
        gates[name]
        for name in (
            "joint_5d_precision_gate",
            "joint_5d_recall_gate",
            "joint_5d_f1_gate",
            "polarity_accuracy_gate",
            "temporal_accuracy_gate",
            "subject_attribution_gate",
            "noise_rejection_gate",
        )
    )
    return gates


def run_extraction_benchmark(fixtures_file: Path, output_dir: Optional[Path] = None) -> Dict[str, Any]:
    with open(fixtures_file, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    total_gold_claims = 0
    total_extracted_claims = 0
    correct_claims = 0
    joint_5d_correct_claims = 0

    polarity_evals = 0
    polarity_correct = 0

    temporal_evals = 0
    temporal_correct = 0

    subject_attribution_evals = 0
    subject_attribution_correct = 0

    noise_cases = 0
    noise_false_positives = 0

    case_reports = []

    for item in fixtures:
        f_id = item["fixture_id"]
        cat = item["category"]
        t_name = item["target_name"]
        text = item["text"]
        gold_claims = item.get("gold_claims", [])

        # Create mock Evidence object
        mock_ev = Evidence(
            evidence_id=f"EV-{f_id}",
            source_id=f"SRC-{f_id}",
            verbatim_excerpt=text,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page="body"),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=SourceQualityClass.CLASS_A,
        )

        # Build independent Mention Universe from upstream mention extraction layer
        fixture_mentions = extract_mentions_and_aliases(
            source_id=mock_ev.source_id,
            raw_text=text,
            target_name=t_name,
            evidence_id=mock_ev.evidence_id,
            base_char_offset=0,
        )
        independent_mention_universe = {m.mention_id for m in fixture_mentions}
        if "known_mention_ids" in item:
            independent_mention_universe.update(item["known_mention_ids"])

        # Execute extraction with clause-level mention anchoring (no blind fallback)
        extracted = extract_claims_from_evidence(
            evidence=mock_ev,
            candidate_entity_id="CAND-TEST",
            target_name=t_name,
            evidence_mentions=fixture_mentions,
        )

        total_gold_claims += len(gold_claims)
        total_extracted_claims += len(extracted)

        if cat == "noise":
            noise_cases += 1
            if len(extracted) > 0:
                noise_false_positives += len(extracted)

        # 1. Relaxed Match (Legacy rule: predicate + loose object overlap)
        matched_gold_relaxed = set()
        for ec in extracted:
            e_pred = ec.predicate
            e_obj = ec.object_raw.lower()
            e_pol = ec.polarity.value
            e_temp = ec.temporal_status.value

            best_match_idx = None
            for idx, gc in enumerate(gold_claims):
                if idx in matched_gold_relaxed:
                    continue
                g_pred = gc["predicate"]
                g_obj = gc["object_raw"].lower()

                if e_pred == g_pred and (e_obj in g_obj or g_obj in e_obj or any(w in e_obj for w in g_obj.split() if len(w) > 3)):
                    best_match_idx = idx
                    break

            if best_match_idx is not None:
                matched_gold_relaxed.add(best_match_idx)
                correct_claims += 1
                gc = gold_claims[best_match_idx]

                # Polarity check
                polarity_evals += 1
                if e_pol == gc["polarity"]:
                    polarity_correct += 1

                # Temporal check
                temporal_evals += 1
                if e_temp == gc["temporal_status"]:
                    temporal_correct += 1

                # Subject check
                subject_attribution_evals += 1
                support_texts = [sup.verbatim_clause for sup in ec.support_clauses] or [text]
                has_subject = any(
                    clause_has_target_subject(
                        value,
                        t_name,
                        full_context=text,
                        subject_mention_id=ec.subject_mention_id,
                        known_mention_ids=independent_mention_universe,
                    )
                    for value in support_texts
                )

                if has_subject:
                    subject_attribution_correct += 1

        # 2. Strict Joint 5D Match (Predicate + Object + Polarity + Temporal + Subject Attribution)
        matched_gold_joint_5d = set()
        for ec in extracted:
            e_pred = ec.predicate
            e_obj = ec.object_raw.lower().strip()
            e_pol = ec.polarity.value
            e_temp = ec.temporal_status.value

            best_joint_idx = None
            for idx, gc in enumerate(gold_claims):
                if idx in matched_gold_joint_5d:
                    continue
                # 1. Predicate
                if ec.predicate != gc["predicate"]:
                    continue
                # 2. Polarity
                if e_pol != gc["polarity"]:
                    continue
                # 3. Temporal
                if e_temp != gc["temporal_status"]:
                    continue
                # 4. Object
                if not strict_object_match(e_obj, gc):
                    continue
                # 5. Subject attribution
                expected_subject = gc.get("subject", t_name)
                support_texts = [sup.verbatim_clause for sup in ec.support_clauses] or [text]
                if not any(
                    clause_has_target_subject(
                        value,
                        expected_subject,
                        full_context=text,
                        subject_mention_id=ec.subject_mention_id,
                        known_mention_ids=independent_mention_universe,
                    )
                    for value in support_texts
                ):
                    continue

                best_joint_idx = idx
                break

            if best_joint_idx is not None:
                matched_gold_joint_5d.add(best_joint_idx)
                joint_5d_correct_claims += 1

        case_reports.append({
            "fixture_id": f_id,
            "category": cat,
            "gold_count": len(gold_claims),
            "extracted_count": len(extracted),
            "matched_relaxed_count": len(matched_gold_relaxed),
            "matched_joint_5d_count": len(matched_gold_joint_5d),
        })

    # Legacy Relaxed Metrics
    prec = (correct_claims / total_extracted_claims) if total_extracted_claims > 0 else 1.0
    rec = (correct_claims / total_gold_claims) if total_gold_claims > 0 else 1.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    # Strict Joint 5D Metrics
    joint_prec = (joint_5d_correct_claims / total_extracted_claims) if total_extracted_claims > 0 else 1.0
    joint_rec = (joint_5d_correct_claims / total_gold_claims) if total_gold_claims > 0 else 1.0
    joint_f1 = (2 * joint_prec * joint_rec / (joint_prec + joint_rec)) if (joint_prec + joint_rec) > 0 else 0.0

    pol_acc = (polarity_correct / polarity_evals) if polarity_evals > 0 else 1.0
    temp_acc = (temporal_correct / temporal_evals) if temporal_evals > 0 else 1.0
    subj_acc = (subject_attribution_correct / subject_attribution_evals) if subject_attribution_evals > 0 else 1.0
    noise_fpr = (noise_false_positives / noise_cases) if noise_cases > 0 else 0.0

    gates = build_extraction_gates(
        polarity_accuracy=pol_acc,
        temporal_accuracy=temp_acc,
        subject_attribution_accuracy=subj_acc,
        noise_false_positive_rate=noise_fpr,
        relation_precision=prec,
        relation_recall=rec,
        relation_f1=f1,
        joint_5d_precision=joint_prec,
        joint_5d_recall=joint_rec,
        joint_5d_f1=joint_f1,
    )

    report = {
        "summary": {
            "total_fixtures": len(fixtures),
            "relation_precision": round(prec, 4),
            "relation_recall": round(rec, 4),
            "relation_f1": round(f1, 4),
            "joint_5d_precision": round(joint_prec, 4),
            "joint_5d_recall": round(joint_rec, 4),
            "joint_5d_f1": round(joint_f1, 4),
            "polarity_accuracy": round(pol_acc, 4),
            "temporal_accuracy": round(temp_acc, 4),
            "subject_attribution_accuracy": round(subj_acc, 4),
            "noise_false_positive_rate": round(noise_fpr, 4),
            "noise_abstention_accuracy": round(1.0 - noise_fpr, 4),
        },
        "gates": gates,
        "case_details": case_reports,
    }

    # Generate Markdown Report
    reports_dir = output_dir or (SKILL_ROOT / "benchmarks" / "reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_md = reports_dir / "extraction_benchmark_report.md"

    md_lines = [
        "# Benchmark 2: 快照与最小对照对断言抽取基准评测报告",
        "",
        f"- **评测用例总数**: {len(fixtures)} (涵盖真实网页、最小成对变换、纯对抗噪声)",
        f"- **联合 5D 全匹配 F1 (Joint 5D Oracle F1)**: {report['summary']['joint_5d_f1']:.4f} (P: {report['summary']['joint_5d_precision']:.4f}, R: {report['summary']['joint_5d_recall']:.4f})",
        f"- **宽松规则关系抽取 F1 (Relaxed Relation F1)**: {report['summary']['relation_f1']:.4f} (P: {report['summary']['relation_precision']:.4f}, R: {report['summary']['relation_recall']:.4f})",
        f"- **极性识别准确率 (Polarity Accuracy)**: {report['summary']['polarity_accuracy'] * 100:.1f}%",
        f"- **时态状态准确率 (Temporal Accuracy)**: {report['summary']['temporal_accuracy'] * 100:.1f}%",
        f"- **主体归属准确率 (Subject Attribution)**: {report['summary']['subject_attribution_accuracy'] * 100:.1f}%",
        f"- **噪声误报率 (Noise False Positive Rate)**: {report['summary']['noise_false_positive_rate'] * 100:.1f}%",
        f"- **噪声正确弃答率 (Abstention Accuracy)**: {report['summary']['noise_abstention_accuracy'] * 100:.1f}%",
        "- **Gold 主体口径**: 每条 fixture 的 `target_name` 是主体真值；object 仅接受标准化精确值或显式 `equivalence_set`。",
        "",
        "## 硬性门槛核验表",
        f"- 严格 5D 发布门槛（P/R/F1 与四项组件均通过）: {'✅ 通过' if report['gates']['strict_5d_release_gate'] else '❌ 未通过'}",
        f"- 联合 5D 精确率门槛 (≥95%): {'✅ 通过' if report['gates']['joint_5d_precision_gate'] else '❌ 未通过'}",
        f"- 联合 5D 召回率门槛 (≥95%): {'✅ 通过' if report['gates']['joint_5d_recall_gate'] else '❌ 未通过'}",
        f"- 联合 5D F1 门槛 (≥95%): {'✅ 通过' if report['gates']['joint_5d_f1_gate'] else '❌ 未通过'}",
        f"- 主体归属识别门槛 (≥95%): {'✅ 通过' if report['gates']['subject_attribution_gate'] else '❌ 未通过'}",
        f"- 极性识别门槛 (≥95%): {'✅ 通过' if report['gates']['polarity_accuracy_gate'] else '❌ 未通过'}",
        f"- 时态识别门槛 (≥95%): {'✅ 通过' if report['gates']['temporal_accuracy_gate'] else '❌ 未通过'}",
        f"- 纯噪声零误报门槛 (0%): {'✅ 通过' if report['gates']['noise_rejection_gate'] else '❌ 未通过'}",
        f"- 关系精确率门槛 (≥95%): {'✅ 通过' if report['gates']['relation_precision_gate'] else '❌ 未通过'}",
        f"- 关系召回率门槛 (≥95%): {'✅ 通过' if report['gates']['relation_recall_gate'] else '❌ 未通过'}",
        f"- 关系抽取 F1 门槛 (≥95%): {'✅ 通过' if report['gates']['relation_f1_gate'] else '❌ 未通过'}",
        "",
        "## 用例明细",
        "| Fixture ID | Category | Gold Claims | Extracted Claims | Matched (Relaxed) | Matched (Joint 5D) |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for c in case_reports:
        md_lines.append(f"| `{c['fixture_id']}` | {c['category']} | {c['gold_count']} | {c['extracted_count']} | {c['matched_relaxed_count']} | {c['matched_joint_5d_count']} |")

    try:
        with open(report_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        print(f"Extraction benchmark report generated at: {report_md}")
    except PermissionError:
        print(f"Warning: Permission denied writing report to {report_md}. Proceeding without overwriting report file.")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Benchmark 2: Claim Extraction Benchmark.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=SKILL_ROOT / "benchmarks" / "test_cases" / "extraction_fixtures" / "fixtures.json",
        help="Path to extraction fixtures JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save the markdown report (defaults to benchmarks/reports).",
    )
    args = parser.parse_args()

    results = run_extraction_benchmark(args.fixtures, output_dir=args.output_dir)
    print("=== Benchmark 2 Summary ===")
    print(json.dumps(results["summary"], indent=2))
    print("=== Benchmark 2 Gates ===")
    print(json.dumps(results["gates"], indent=2))
    if not results["gates"]["strict_5d_release_gate"]:
        raise SystemExit(1)
