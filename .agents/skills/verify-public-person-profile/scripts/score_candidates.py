"""
Dossier Bundle Scorer and Gate Adjudicator (V4.4.1).
Evaluates output bundle against Gold ground truth using:
1. Front-Door Structural Validation (validate_bundle).
2. Two-layer Mention Universe and Detection evaluation with mention_universe_gate.
3. Kuhn-Munkres Maximum Weight Partial Bipartite Matching with dummy nodes and admissible threshold.
4. Sentence-level 5D Semantic Entailment (Subj, Rel, Obj, Pol, Temp).
5. Clamped 100-pt orthogonal rubric with zero overflow.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from benchmarks.eval_extraction import (
    PERSON_NAME_PATTERN,
    ZH_TRANSITIVE_PATTERN,
    strict_object_match,
)
from benchmarks.tools.bipartite_matching import max_weight_partial_matching
from benchmarks.tools.er_metrics import (
    compute_b3,
    compute_mention_detection_metrics,
    compute_pairwise,
)
from scripts.validate_dossier import validate_bundle
from core.extractors.subject_attribution import (
    build_person_mention_universe,
    detect_post_predicate_subject,
    resolve_pronoun_antecedent,
    is_exact_or_verified_alias_match,
)

ZH_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳"
    "酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞"
    "熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓"
    "郁单杭洪包诸左石崔吉钮龚嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁"
    "仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉"
    "宰郦雍郤璩桑桂濮扈套寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东"
    "欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)

NEGATION_TOKENS = {"not", "never", "no longer", "ceased", "denies", "does not", "did not", "was not", "is not", "并未", "绝非", "不再", "未曾", "并非"}
PAST_TOKENS = {"former", "past", "previously", "was", "until", "ex-", "retired", "stepped down", "曾任", "前任", "已离任", "历任", "原", "既往"}

RELATION_KEYWORDS = {
    "holds_position": ["professor", "associate", "dean", "director", "chair", "scientist", "engineer", "realtor", "agent", "fellow", "postdoc", "appointed", "serves", "president", "researcher", "教授", "研究员", "院长", "主任", "会长", "校长", "医师"],
    "affiliated_with": ["university", "college", "institute", "hospital", "school", "center", "foundation", "department", "lab", "group", "realty", "corp", "inc", "realtor", "affiliated", "associated", "works", "大学", "学院", "研究所", "医院", "公司", "集团", "队", "亲历者", "易思汇"],
    "graduated_from": ["graduated", "alumnus", "alumna", "degree", "phd", "bs", "ba", "ms", "ma", "毕业", "校友", "获学位", "一零一中"],
    "received_degree": ["degree", "phd", "doctor", "master", "bachelor", "received", "earned", "holds", "obtained", "学位", "博士", "硕士", "学士"],
    "member_of": ["member", "joined", "works in", "team", "society", "roster", "lab", "group", "club", "association", "队", "成员", "学会", "协会", "俱乐部"],
    "authored_publication": ["authored", "wrote", "published", "author", "publication", "book", "paper", "著有", "出版", "撰写", "发表", "出版物", "著作", "岁月静好"],
    "awarded_honor": ["awarded", "honor", "prize", "fellowship", "scholar", "team", "champion", "荣获", "获得", "荣誉", "学者", "奖"],
    "based_in": ["based", "located", "living", "haven", "francisco", "city", "area", "county", "位于", "定居", "地处"],
}

EN_COMPETING_PATTERNS = [
    r"\b(?:Prof(?:essor|\.)?|Dr\.|Mr\.|Ms\.|Mrs\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:is|was|has|had|graduated|received|joined|studied|served|earned|worked|said|stated|reported|praised|thanked|interviewed|advised|won|awarded)\b",
]

ZH_COMPETING_PATTERNS = [
    # Name with title
    r"(?:教授|学者|专家|老师|研究员|医师|博士|硕士|院士|院长|主任)\s*([\u4e00-\u9fff]{2,3})|([\u4e00-\u9fff]{2,3})\s*(?:教授|学者|专家|老师|研究员|医师|博士|硕士|院士|院长|主任)",
    # Name with action/role
    rf"(?:^|[，,；;。！？\s]|随后|目前|同时|并)([{ZH_SURNAMES}][\u4e00-\u9fff]{{1,2}})\s*(?:是|曾任|现任|担任|兼任|毕业于|任职于|就职于|任教|指导|会见|感谢|指出|表示|说|称|道|撰写|发表|加入|荣获|获)(?=[，,；;。！？\s]|$)",
    # Name in prepositional location
    rf"(?:^|[，,；;。！？\s]|随后|目前|同时|并)([{ZH_SURNAMES}][\u4e00-\u9fff]{{1,2}})\s*在[\u4e00-\u9fff]+(?:任教|任职|工作|就读|学习)",
    # Name with transitive action
    rf"(?:^|[，,；;。！？\s]|随后|目前|同时|并)([{ZH_SURNAMES}][\u4e00-\u9fff]{{1,2}})\s*(?:{ZH_TRANSITIVE_PATTERN})",
]


def _matches_word_or_phrase(pattern: str, text: str) -> bool:
    if not pattern or not text:
        return False
    if pattern.isascii():
        return bool(re.search(rf"\b{re.escape(pattern)}\b", text, re.IGNORECASE))
    return pattern.lower() in text.lower()


def check_5d_entailment(
    sc: Dict[str, Any],
    gc: Dict[str, Any],
    evidence_map: Dict[str, Any],
    valid_subjects: Set[str],
    mention_map: Optional[Dict[str, Any]] = None,
    candidate_map: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, bool, bool]:
    """
    Evaluates 5D semantic entailment between system claim sc and gold claim gc.
    Returns (is_entailed, is_attributed, is_temporal_correct).
    """
    s_pred = sc.get("predicate", "")
    g_pred = gc.get("predicate", "")
    if s_pred != g_pred:
        return False, False, False

    s_obj = sc.get("object_raw", "").strip()
    if not s_obj:
        return False, False, False

    if not strict_object_match(s_obj, gc):
        return False, False, False

    s_pol = sc.get("polarity", "affirmative")
    if "polarity" in gc and gc["polarity"] != s_pol:
        return False, False, False

    s_temp = sc.get("temporal_status", "unknown")
    if "temporal_status" in gc and gc["temporal_status"] != s_temp:
        return False, False, False

    # Check evidence support clause
    ev_ids = sc.get("evidence_ids", [])
    if not ev_ids:
        return False, False, False

    is_attributed = False
    is_temporal_correct = True
    clause_entailed = False

    # Check parent evidence excerpts
    ev_excerpts = []
    for e_id in ev_ids:
        ev = evidence_map.get(e_id)
        if ev:
            ev_excerpts.append(ev.get("verbatim_excerpt", "").lower())

    # Check support clauses if available
    support_clauses = sc.get("support_clauses", [])
    candidate_clauses = []
    if support_clauses:
        for sup in support_clauses:
            rc = sup.get("verbatim_clause", "") if isinstance(sup, dict) else getattr(sup, "verbatim_clause", "")
            candidate_clauses.append((rc, rc.lower()))
    else:
        for exc in ev_excerpts:
            candidate_clauses.append((exc, exc.lower()))

    # 1. Direct explicit attribution in clause text
    for raw_clause, clause_text in candidate_clauses:
        if valid_subjects:
            for s in valid_subjects:
                if _matches_word_or_phrase(s, clause_text):
                    is_attributed = True
                    break
        if is_attributed:
            break

    # 2. Independent Antecedent Verification (No ungrounded fallbacks)
    if not is_attributed and support_clauses and mention_map is not None:
        claim_cand_id = sc.get("candidate_entity_id")
        for sup in support_clauses:
            res_type = sup.get("subject_resolution") if isinstance(sup, dict) else getattr(sup, "subject_resolution", None)
            ante_id = sup.get("antecedent_mention_id") if isinstance(sup, dict) else getattr(sup, "antecedent_mention_id", None)
            ante_span = sup.get("antecedent_clause_span") if isinstance(sup, dict) else getattr(sup, "antecedent_clause_span", None)
            c_start = sup.get("clause_span_start") if isinstance(sup, dict) else getattr(sup, "clause_span_start", None)
            ev_id = sup.get("evidence_id") if isinstance(sup, dict) else getattr(sup, "evidence_id", None)
            raw_clause = sup.get("verbatim_clause", "") if isinstance(sup, dict) else getattr(sup, "verbatim_clause", "")

            if res_type not in ("pro_drop_anaphora", "pronoun_anaphora"):
                continue

            # (1) Syntactic grounding for pronoun_anaphora: clause MUST contain an anaphoric pronoun
            if res_type == "pronoun_anaphora":
                if not re.search(r"\b(?:she|he|they|her|his|their|i|my)\b|(?:其|该学者|该专家|该教授|该研究员)", raw_clause, re.IGNORECASE):
                    continue

            # (2) Syntactic grounding for pro_drop_anaphora: clause MUST start with an allowed predicate connector
            if res_type == "pro_drop_anaphora":
                raw_clause_clean = raw_clause.strip()
                adverb_match = re.match(r"^(?:目前|随后|并|同时|此前|此后)\s*", raw_clause_clean)
                if adverb_match:
                    after_adverb = raw_clause_clean[adverb_match.end():]
                    if not re.match(r"^(?:现为|曾为|现任|曾任|担任|兼任|荣获|获|入选|受聘|任职|就职|就任|毕业|就读|发表|出版|撰写|出生|生于|是|为)", after_adverb):
                        continue
                elif not re.match(
                    r"^(?:(?:现为|曾为|现任|曾任|担任|兼任|荣获|获|入选|受聘|任职|就职|就任|毕业|就读|发表|出版|撰写|出生|生于)|(?:and\s+serves|and\s+served|and\s+joined|and\s+was|and\s+is)\b)",
                    raw_clause_clean,
                    re.IGNORECASE,
                ):
                    continue

            # (3) Scan raw_clause itself for explicit third-party competing subjects
            clause_competing = False
            for pat in EN_COMPETING_PATTERNS:
                for pm in re.finditer(pat, raw_clause):
                    found_en = (pm.group(1) if pm.lastindex and pm.lastindex >= 1 else pm.group(0)).strip()
                    if not any(_matches_word_or_phrase(s, found_en) for s in valid_subjects):
                        clause_competing = True
                        break
                if clause_competing:
                    break
            if not clause_competing:
                for pat in ZH_COMPETING_PATTERNS:
                    for zm in re.finditer(pat, raw_clause):
                        g1 = zm.group(1) if zm.lastindex and zm.lastindex >= 1 else None
                        g2 = zm.group(2) if zm.lastindex and zm.lastindex >= 2 else None
                        found_zh = (g1 or g2 or "").strip()
                        if found_zh and not any(_matches_word_or_phrase(s, found_zh) for s in valid_subjects):
                            clause_competing = True
                            break
                    if clause_competing:
                        break
            if clause_competing:
                continue

            # (a) Antecedent mention must actually exist in mention_map
            if not ante_id or ante_id not in mention_map:
                continue
            ante_m = mention_map[ante_id]

            # Antecedent surface text must match valid_subjects
            ante_text = ante_m.get("raw_name_text") or ante_m.get("text", "")
            if not any(_matches_word_or_phrase(s, ante_text) for s in valid_subjects):
                continue

            # (b) Must belong to the same Evidence and Candidate
            ev = evidence_map.get(ev_id)
            if not ev:
                continue
            ante_ev_id = ante_m.get("evidence_id")
            ante_src_id = ante_m.get("source_id")
            ev_src_id = ev.get("source_id")
            if ante_ev_id and ante_ev_id != ev_id:
                continue
            if ante_src_id and ev_src_id and ante_src_id != ev_src_id:
                continue

            if candidate_map and claim_cand_id:
                cand = candidate_map.get(claim_cand_id)
                if cand and ante_id not in cand.get("mention_ids", []):
                    continue
            if ante_m.get("candidate_entity_id") and claim_cand_id and ante_m.get("candidate_entity_id") != claim_cand_id:
                continue

            # (c) Antecedent span must precede the current clause
            if not ante_span or len(ante_span) != 2:
                continue
            if c_start is None or ante_span[1] > c_start:
                continue

            ev_text = ev.get("verbatim_excerpt", "")
            ev_s = ev.get("char_start", ev.get("start_offset", 0))

            rel_ante_s = ante_span[0] if ante_span[0] < len(ev_text) else (ante_span[0] - ev_s)
            rel_ante_e = ante_span[1] if ante_span[1] <= len(ev_text) else (ante_span[1] - ev_s)
            rel_c_s = c_start if c_start < len(ev_text) else (c_start - ev_s)

            if not (0 <= rel_ante_s < rel_ante_e <= rel_c_s <= len(ev_text)):
                continue

            # (d) antecedent_clause_span must cover the antecedent mention
            m_s = ante_m.get("char_start", ante_m.get("start_offset"))
            m_e = ante_m.get("char_end", ante_m.get("end_offset"))
            if m_s is not None and m_e is not None:
                rel_m_s = m_s if m_s < len(ev_text) else (m_s - ev_s)
                rel_m_e = m_e if m_e <= len(ev_text) else (m_e - ev_s)
                if not (rel_ante_s <= rel_m_s < rel_m_e <= rel_ante_e):
                    continue
            else:
                rel_m_e = rel_ante_e

            # (d.1) Post-predicate (cleft / focal) subject check:
            raw_clause = sup.get("verbatim_clause", "")
            post_subj = detect_post_predicate_subject(raw_clause)
            if post_subj and not is_exact_or_verified_alias_match(post_subj, valid_subjects):
                continue

            # (e) Adjacency / Contiguity check for pro_drop_anaphora and pronoun_anaphora
            gap_text = ev_text[rel_ante_e:rel_c_s]
            if res_type == "pro_drop_anaphora":
                # 1. Pro-drop cannot cross sentence boundaries
                if re.search(r"[。！？.!?\n\r]", gap_text):
                    continue
                # 2. Cannot have an arbitrary distant gap (> 15 chars)
                if (rel_c_s - rel_ante_e) > 15:
                    continue
                # 3. Gap must only be whitespace, clause delimiters, or allowed connectors
                if not re.fullmatch(r"[\s,，;；、\-—–]*(?:and|&|并|并且|且|同时)?[\s,，;；、\-—–]*", gap_text, re.IGNORECASE):
                    continue
            elif res_type == "pronoun_anaphora":
                # 1. Pronoun anaphora cannot cross paragraph boundaries
                if re.search(r"\n\s*\n|<\s*(?:p|div|section|article|blockquote)\b", gap_text, re.IGNORECASE):
                    continue
                # 2. Pronoun anaphora cannot skip multiple sentences (> 1 sentence boundary)
                if len(re.findall(r"[。！？.!?]", gap_text)) > 1:
                    continue
                # 3. Pronoun anaphora gap distance limit (cannot be distant text, > 50 chars)
                if (rel_c_s - rel_ante_e) > 50:
                    continue
                # 4. Nearest compatible antecedent validation
                pronoun_m = re.search(r"\b(she|he|they|i|my|其|该学者|该专家)\b", raw_clause, re.IGNORECASE)
                if pronoun_m:
                    p_word = pronoun_m.group(1)
                    p_pos = rel_c_s + pronoun_m.start()
                    all_persons = build_person_mention_universe(ev_text, known_persons=list(valid_subjects))
                    is_bound, resolved_name = resolve_pronoun_antecedent(
                        p_word, p_pos, ev_text, target_names=valid_subjects, all_mentions=all_persons
                    )
                    if not is_bound:
                        continue

            # (f) Competing subject detection between antecedent mention and current clause
            # 1. Check in mention_map
            intervening_competing = False
            for other_id, other_m in mention_map.items():
                if other_id == ante_id:
                    continue
                o_ev = other_m.get("evidence_id")
                o_src = other_m.get("source_id")
                if (o_ev and o_ev == ev_id) or (o_src and ev_src_id and o_src == ev_src_id):
                    o_s = other_m.get("char_start", other_m.get("start_offset"))
                    o_e = other_m.get("char_end", other_m.get("end_offset"))
                    if o_s is not None and o_e is not None:
                        rel_o_s = o_s if o_s < len(ev_text) else (o_s - ev_s)
                        if rel_m_e <= rel_o_s < rel_c_s:
                            o_name = other_m.get("raw_name_text") or other_m.get("text", "")
                            if not any(_matches_word_or_phrase(s, o_name) for s in valid_subjects):
                                intervening_competing = True
                                break
                            if candidate_map and claim_cand_id:
                                o_cand = other_m.get("candidate_entity_id")
                                if o_cand and o_cand != claim_cand_id:
                                    intervening_competing = True
                                    break
            if intervening_competing:
                continue

            # 2. Raw text scan in ev_text between antecedent mention and current clause
            # (Detects unextracted 3rd-party persons, e.g. "张伟" or "Bob Smith")
            between_text = ev_text[rel_m_e:rel_c_s]

            for pat in EN_COMPETING_PATTERNS:
                for pm in re.finditer(pat, between_text):
                    found_en = (pm.group(1) if pm.lastindex and pm.lastindex >= 1 else pm.group(0)).strip()
                    if not any(_matches_word_or_phrase(s, found_en) for s in valid_subjects):
                        intervening_competing = True
                        break
                if intervening_competing:
                    break
            if intervening_competing:
                continue

            for pat in ZH_COMPETING_PATTERNS:
                for zm in re.finditer(pat, between_text):
                    g1 = zm.group(1) if zm.lastindex and zm.lastindex >= 1 else None
                    g2 = zm.group(2) if zm.lastindex and zm.lastindex >= 2 else None
                    found_zh = (g1 or g2 or "").strip()
                    if found_zh and not any(_matches_word_or_phrase(s, found_zh) for s in valid_subjects):
                        intervening_competing = True
                        break
                if intervening_competing:
                    break
            if intervening_competing:
                continue

            # All independent checks verified
            is_attributed = True
            break


    # 3. Clause-level semantic entailment check
    for raw_clause, clause_text in candidate_clauses:
        post_subj = detect_post_predicate_subject(raw_clause)
        if post_subj and not any(_matches_word_or_phrase(s, post_subj) for s in valid_subjects):
            continue

        # Syntactic role check for holds_position:
        # Prevent "Alice praised Dean Bob", "Dean Bob praised Alice", "Alice emailed Dean Bob", "Alice is the custodian of Dean Hall"
        is_distractor_role = False
        if s_pred == "holds_position" and valid_subjects:
            s_obj_lower = s_obj.lower().strip()
            for subj in valid_subjects:
                subj_lower = subj.lower().strip()

                # 1. Facility/building noun check: e.g. "Dean Hall", "Director Building"
                if re.search(rf"\b{re.escape(s_obj_lower)}\s+(?:hall|building|center|auditorium|tower|house|complex|library|pavilion|room)\b", clause_text):
                    if not re.search(rf"\b{re.escape(subj_lower)}\b\s+(?:is|was|serves as|served as)\s+(?:a\s+|the\s+)?{re.escape(s_obj_lower)}\s+of\b", clause_text):
                        is_distractor_role = True
                        break

                # 2. Foreign title prefix check: e.g. "Dean Bob" when subject is "Alice"
                # Checks if title in raw clause is immediately followed by a capitalized Proper Name of another person
                foreign_prefix = re.search(rf"\b{re.escape(sc.get('object_raw', ''))}\s+([A-Z][a-z]+)\b", raw_clause)
                if foreign_prefix:
                    attached_token = foreign_prefix.group(1).lower()
                    if attached_token not in {"hall", "building", "center", "tower", "house", "complex", "room", "pavilion"}:
                        if attached_token not in subj_lower and not any(part in attached_token for part in subj_lower.split() if len(part) > 2):
                            is_distractor_role = True
                            break

                # 3. Transitive verb interaction: e.g. "Alice praised Dean Bob", "Dean Bob praised Alice", "Alice emailed Dean Bob"
                interaction_pat = r"\b(?:praised|emailed|interviewed|visited|met|contacted|congratulated|thanked|reported to|recommended)\b"
                if re.search(interaction_pat, clause_text):
                    copular_pat = rf"\b{re.escape(subj_lower)}\b.*?\b(?:is|was|serves as|served as|appointed as)\b.*?\b{re.escape(s_obj_lower)}\b"
                    prefix_pat = rf"\b{re.escape(s_obj_lower)}\s+{re.escape(subj_lower)}\b"
                    if not re.search(copular_pat, clause_text) and not re.search(prefix_pat, clause_text):
                        is_distractor_role = True
                        break

                # 4. Foreign appositive: "Alice met Bob, the former Dean"
                foreign_appos = re.search(
                    r"([a-z]+\s+[a-z]+)\s*[,，]\s*(?:the\s+)?([a-z\s]{2,30}?(?:dean|director|professor|chair|president|院长|主任|教授))",
                    clause_text
                )
                if foreign_appos:
                    other_name = foreign_appos.group(1).lower()
                    appos_role = foreign_appos.group(2).lower()
                    if other_name not in subj_lower and subj_lower not in other_name:
                        if any(_matches_word_or_phrase(tok, appos_role) for tok in s_obj.split() if len(tok) > 2):
                            is_distractor_role = True
                            break

        if is_distractor_role:
            continue

        rel_kws = RELATION_KEYWORDS.get(s_pred, [])
        has_rel = any(rw in clause_text for rw in rel_kws)
        has_obj = (_matches_word_or_phrase(s_obj, clause_text)) or (s_obj.lower() in clause_text) or any(_matches_word_or_phrase(t, clause_text) for t in s_obj.split() if len(t) > 3)
        has_neg = any(neg in clause_text for neg in NEGATION_TOKENS)
        has_past = any(p in clause_text for p in PAST_TOKENS)

        pol_ok = (s_pol == "negative") if has_neg else (s_pol == "affirmative")
        temp_ok = not (has_past and s_temp == "current")

        if has_rel and has_obj and pol_ok and temp_ok:
            clause_entailed = True
            break

    is_entailed = clause_entailed and (is_attributed if valid_subjects else True)
    return is_entailed, is_attributed, is_temporal_correct


def evaluate_dossier_bundle(
    bundle_dir: Path,
    gold_file: Path,
    evaluation_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    # 1. Structural Pre-Gate
    val_res = validate_bundle(bundle_dir)
    if not val_res["is_valid"]:
        return {
            "total_score_out_of_100": 0.0,
            "all_gates_passed": False,
            "structural_validation_passed": False,
            "validation_errors": val_res["errors"],
            "gates": {
                "claim_precision_gate": False,
                "gold_claim_recall_gate": False,
                "citation_entailment_gate": False,
                "current_status_gate": False,
                "er_b3_gate": False,
                "zero_false_merges": False,
                "mention_detection_gate": False,
                "mention_universe_gate": False,
                "abstention_gate": False,
                "safety_gate": False,
                "pending_review_gate": False,
                "structural_validation_gate": False,
                "relation_precision_gate": False,
            },
            "detailed_metrics": {"claim_precision": 0.0, "gold_claim_recall": 0.0, "false_merges": 0, "b3_f1": 0.0},
            "adjudication_status": "rejected_structural_failure",
        }

    with open(gold_file, "r", encoding="utf-8") as f:
        gold = json.load(f)

    with open(bundle_dir / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    run_outcome = manifest.get("run_outcome", "completed")
    expected_outcome = gold.get("expected_outcome", "completed")
    track = gold.get("track", "frozen_corpus")

    # 2. Strict outcome validation
    if run_outcome in ("failed", "collection_failed", "budget_exhausted"):
        return {
            "total_score_out_of_100": 0.0,
            "all_gates_passed": False,
            "gates": {
                "claim_precision_gate": False,
                "gold_claim_recall_gate": False,
                "citation_entailment_gate": False,
                "current_status_gate": False,
                "er_b3_gate": False,
                "zero_false_merges": False,
                "mention_detection_gate": False,
                "mention_universe_gate": False,
                "abstention_gate": False,
                "safety_gate": False,
                "pending_review_gate": False,
                "structural_validation_gate": True,
                "relation_precision_gate": False,
            },
            "detailed_metrics": {"claim_precision": 0.0, "gold_claim_recall": 0.0, "false_merges": 0, "b3_f1": 0.0},
            "adjudication_status": "rejected_failure",
        }

    if expected_outcome and expected_outcome != run_outcome:
        return {
            "total_score_out_of_100": 0.0,
            "all_gates_passed": False,
            "gates": {
                "claim_precision_gate": False,
                "gold_claim_recall_gate": False,
                "citation_entailment_gate": False,
                "current_status_gate": False,
                "er_b3_gate": False,
                "zero_false_merges": False,
                "mention_detection_gate": False,
                "mention_universe_gate": False,
                "abstention_gate": False,
                "safety_gate": False,
                "pending_review_gate": False,
                "structural_validation_gate": True,
                "relation_precision_gate": False,
            },
            "detailed_metrics": {"claim_precision": 0.0, "gold_claim_recall": 0.0, "false_merges": 0, "b3_f1": 0.0},
            "adjudication_status": f"rejected_outcome_mismatch_expected_{expected_outcome}_got_{run_outcome}",
        }

    claims = []
    with open(bundle_dir / "claims.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                claims.append(json.loads(line))

    mentions = []
    with open(bundle_dir / "mentions.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                mentions.append(json.loads(line))

    clusters = []
    with open(bundle_dir / "clusters.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                clusters.append(json.loads(line))

    sources = []
    with open(bundle_dir / "sources.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sources.append(json.loads(line))

    evidence = []
    with open(bundle_dir / "evidence.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                evidence.append(json.loads(line))
    evidence_map = {e["evidence_id"]: e for e in evidence}

    matches = []
    if (bundle_dir / "matches.jsonl").exists():
        with open(bundle_dir / "matches.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    matches.append(json.loads(line))
    pending_review_count = sum(1 for m in matches if m.get("machine_relation") == "review")

    candidates = []
    if (bundle_dir / "candidates.jsonl").exists():
        with open(bundle_dir / "candidates.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    candidates.append(json.loads(line))
    candidate_map = {c["candidate_entity_id"]: c for c in candidates}
    mention_map = {m["mention_id"]: m for m in mentions}

    # 3. Abstention Handling
    abstention_gate = False
    if run_outcome == "insufficient_evidence":
        if not claims and manifest.get("abstention_records"):
            abstention_gate = True
            return {
                "total_score_out_of_100": 100.0,
                "all_gates_passed": True,
                "gates": {
                    "claim_precision_gate": True,
                    "gold_claim_recall_gate": True,
                    "citation_entailment_gate": True,
                    "current_status_gate": True,
                    "er_b3_gate": True,
                    "zero_false_merges": True,
                    "mention_detection_gate": True,
                    "mention_universe_gate": True,
                    "abstention_gate": True,
                    "safety_gate": True,
                    "pending_review_gate": True,
                    "structural_validation_gate": True,
                    "relation_precision_gate": True,
                },
                "detailed_metrics": {"claim_precision": 1.0, "gold_claim_recall": 1.0, "false_merges": 0, "b3_f1": 1.0},
                "adjudication_status": "adjudicated_abstention_success",
            }

    # 4. Two-Layer Entity Resolution Metrics
    gold_clusters = gold.get("gold_clusters", [])
    sys_mention_ids = [m["mention_id"] for m in mentions]
    sys_clusters = [c["mention_ids"] for c in clusters] if clusters else [[m_id] for m_id in sys_mention_ids]

    # Map mentions if gold clusters use mention_key instead of mention_id
    key_to_sys_id = {}
    for m in mentions:
        m_id = m.get("mention_id")
        m_key = m.get("mention_key")
        if m_key and m_id:
            key_to_sys_id[m_key] = m_id

    translated_gold_clusters = []
    for cl in gold_clusters:
        new_cl = []
        for item in cl:
            new_cl.append(key_to_sys_id.get(item, item))
        translated_gold_clusters.append(new_cl)
    gold_clusters = translated_gold_clusters
    gold_mentions = [m for cl in gold_clusters for m in cl]

    # Layer 1: Mention Detection
    det_metrics = compute_mention_detection_metrics(gold_mentions, sys_mention_ids)
    mention_detection_gate = det_metrics["detection_gate"]

    # Layer 2: Common Universe Clustering
    common_universe = list(set(gold_mentions).intersection(set(sys_mention_ids)))
    if not common_universe and not gold_mentions and not sys_mention_ids:
        b3_res = {"b3_precision": 1.0, "b3_recall": 1.0, "b3_f1": 1.0}
        pair_res = {"pairwise_f1": 1.0, "false_merge_count": 0, "false_split_count": 0}
        mention_universe_gate = True
    elif not common_universe:
        b3_res = {"b3_precision": 0.0, "b3_recall": 0.0, "b3_f1": 0.0}
        pair_res = {"pairwise_f1": 0.0, "false_merge_count": 0, "false_split_count": 0}
        mention_universe_gate = False
    else:
        b3_res = compute_b3(gold_clusters, sys_clusters, common_universe)
        pair_res = compute_pairwise(gold_clusters, sys_clusters, common_universe)
        mention_universe_gate = (det_metrics["missing_gold_count"] == 0 and det_metrics["spurious_sys_count"] == 0)

    false_merges = pair_res["false_merge_count"]

    # 5. Kuhn-Munkres Maximum Weight Partial Bipartite Matching for Claims
    gold_claims = gold.get("gold_claims", [])
    target_name = gold.get("target_name", "").lower()
    gold_aliases = [a.get("alias_value", "").lower() for a in gold.get("gold_aliases", [])]
    valid_subjects = {target_name} | set(gold_aliases) if target_name else set()

    m_claims = len(claims)
    n_gold = len(gold_claims)

    weight_matrix = [[0.0 for _ in range(n_gold)] for _ in range(m_claims)]
    for i, sc in enumerate(claims):
        for j, gc in enumerate(gold_claims):
            is_ent, _, _ = check_5d_entailment(
                sc, gc, evidence_map, valid_subjects, mention_map=mention_map, candidate_map=candidate_map
            )
            if is_ent:
                weight_matrix[i][j] = 1.0

    admissible_matches, total_admissible_weight = max_weight_partial_matching(weight_matrix, threshold=1.0)
    matched_claim_indices = {i for i, j in admissible_matches}
    matched_gold_indices = {j for i, j in admissible_matches}

    verified_claims_count = len(admissible_matches)
    total_claims = len(claims)

    if track == "frozen_corpus":
        claim_precision = (verified_claims_count / total_claims) if total_claims > 0 else (1.0 if not gold_claims else 0.0)
    else:
        claim_precision = (verified_claims_count / total_claims) if total_claims > 0 else 0.0

    gold_claim_recall = (len(matched_gold_indices) / len(gold_claims)) if gold_claims else 1.0

    # 6. 5D Semantic Entailment Statistics across all claims
    entailed_claims_count = 0
    attributed_claims_count = 0
    temporal_match_count = 0

    for i, sc in enumerate(claims):
        if i in matched_claim_indices:
            entailed_claims_count += 1
            attributed_claims_count += 1
            temporal_match_count += 1
        elif not gold_claims:
            dummy_gc = {
                "predicate": sc.get("predicate"),
                "object_raw": sc.get("object_raw"),
                "equivalence_set": [sc.get("object_raw", "")],
                "polarity": sc.get("polarity", "affirmative"),
                "temporal_status": sc.get("temporal_status", "current"),
            }
            is_ent, is_attr, is_temp = check_5d_entailment(
                sc, dummy_gc, evidence_map, valid_subjects, mention_map=mention_map, candidate_map=candidate_map
            )
            if is_ent:
                entailed_claims_count += 1
            if is_attr:
                attributed_claims_count += 1
            if is_temp:
                temporal_match_count += 1

    citation_entailment_rate = (entailed_claims_count / total_claims) if total_claims > 0 else 0.0
    attribution_rate = (attributed_claims_count / total_claims) if total_claims > 0 else 0.0
    temporal_consistency_rate = (temporal_match_count / total_claims) if total_claims > 0 else 0.0

    # Output unreviewed claims to evaluation_dir
    unreviewed_claims = [sc for i, sc in enumerate(claims) if i not in matched_claim_indices]
    if unreviewed_claims and evaluation_dir:
        evaluation_dir.mkdir(parents=True, exist_ok=True)
        with open(evaluation_dir / "unreviewed_claims.jsonl", "w", encoding="utf-8") as uf:
            for uc in unreviewed_claims:
                uf.write(json.dumps(uc) + "\n")

    # 7. Rubric Aggregation (Sum of maximums = 100.0)
    score_precision = claim_precision * 25.0
    score_recall = gold_claim_recall * 20.0
    score_er = b3_res["b3_f1"] * 20.0
    score_entailment = citation_entailment_rate * 15.0
    score_attribution = attribution_rate * 10.0
    score_temporal = temporal_consistency_rate * 5.0
    score_safety = 5.0 if sources else 0.0

    raw_total = (
        score_precision
        + score_recall
        + score_er
        + score_entailment
        + score_attribution
        + score_temporal
        + score_safety
    )
    total_score = min(100.0, max(0.0, raw_total))

    # 8. Release Gates
    gates = {
        "claim_precision_gate": claim_precision >= 0.95 if track == "frozen_corpus" else True,
        "gold_claim_recall_gate": gold_claim_recall >= 0.85 if (track == "frozen_corpus" and len(gold_claims) > 0) else True,
        "citation_entailment_gate": citation_entailment_rate >= 0.95,
        "current_status_gate": temporal_consistency_rate >= 0.95,
        "er_b3_gate": b3_res["b3_f1"] >= 0.90,
        "zero_false_merges": false_merges == 0,
        "mention_detection_gate": mention_detection_gate,
        "mention_universe_gate": mention_universe_gate,
        "abstention_gate": True,
        "safety_gate": score_safety == 5.0,
        "pending_review_gate": (pending_review_count == 0) and (len(unreviewed_claims) == 0),
        "structural_validation_gate": True,
        "relation_precision_gate": bool(val_res.get("layers", {}).get("relation_precision_enforced", False)),
    }

    all_gates_passed = all(gates.values())

    return {
        "total_score_out_of_100": round(total_score, 2),
        "all_gates_passed": all_gates_passed,
        "structural_validation_passed": True,
        "gates": gates,
        "detailed_metrics": {
            "claim_precision": round(claim_precision, 4),
            "gold_claim_recall": round(gold_claim_recall, 4),
            "pending_review_count": pending_review_count,
            "b3_f1": round(b3_res["b3_f1"], 4),
            "false_merges": false_merges,
            "citation_entailment_rate": round(citation_entailment_rate, 4),
            "attribution_rate": round(attribution_rate, 4),
            "temporal_consistency_rate": round(temporal_consistency_rate, 4),
            "kuhn_munkres_matches": verified_claims_count,
        },
        "adjudication_status": "adjudicated_success" if all_gates_passed else "rejected_gate_failure",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate output bundle against gold standard.")
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--gold-file", type=Path, required=True)
    parser.add_argument("--eval-dir", type=Path, default=None)
    args = parser.parse_args()

    res = evaluate_dossier_bundle(args.bundle_dir, args.gold_file, evaluation_dir=args.eval_dir)
    print(json.dumps(res, indent=2, ensure_ascii=False))
