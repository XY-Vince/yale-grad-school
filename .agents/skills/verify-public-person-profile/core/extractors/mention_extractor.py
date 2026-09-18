"""
Mention and Alias Extractor (V4.4.1).
Extracts entity mentions from source text and generates orthogonal alias hypotheses.
Binds mentions to evidence_id, records character spans, and generates deterministic IDs.
"""

import hashlib
import re
import unicodedata
from typing import List, Optional
from models.schemas import EntityMention, AliasRecord, OriginType, VerificationStatus


ZH_COMMON_VERBS = {
    "接受", "参与", "领导", "发表", "出版", "撰写", "研究", "工作", "访问", "学习",
    "创立", "负责", "担任", "现任", "曾任", "兼任", "毕业", "荣获", "指导", "考察",
    "前往", "出生", "就读", "任教", "演讲", "汇报", "主持", "组织", "策划", "讲授",
    "出席", "参加", "合作", "获得", "提出", "指出", "表示", "强调", "认为", "宣布",
    "介绍", "受聘", "聘任", "当选", "入选", "荣膺", "就任", "任职", "就职", "求学",
    "代表", "回应", "坦言", "致辞", "调研", "讨论", "创立", "开发", "设计", "建立",
    "创办", "讲座", "谈到", "提到", "写道", "获评", "荣休", "离任", "退休", "加盟",
    "加入", "执教", "投身", "从事", "主导", "推进", "深耕", "生于", "签约",
    "倡导", "创建", "完成", "设立", "筹建", "组建", "开展", "研发", "探索", "实施",
    "牵头", "研制", "规划", "统筹", "主编", "承办", "协办", "主办",
    "批评", "表扬", "赞赏", "抨击", "谴责", "反对", "支持", "呼吁", "强调", "指出",
    "当选为", "被评为", "被任命为", "被选为", "被聘为", "被授予", "荣膺", "当选",
}

ZH_PARTICLES_AND_PREPS = {
    "在", "于", "和", "与", "及", "同", "等", "的", "被", "把", "将", "为", "是", "系",
    "对", "向", "自", "从", "赴", "到", "已", "曾", "正", "获", "任", "读", "写", "做",
    "说", "称", "道", "看", "听", "去", "来", "问", "答", "请", "让", "给", "替", "帮",
}

ZH_TITLES = {
    "教授", "副教授", "助理教授", "讲师", "研究员", "副研究员", "助理研究员", "院士",
    "学者", "专家", "博士", "硕士", "学士", "主任", "副主任", "院长", "副院长",
    "所长", "副所长", "校长", "副校长", "书记", "处长", "部长", "局长", "省长", "市长",
    "老师", "同志", "先生", "女士", "医生", "医师", "工程师", "总监", "经理", "顾问",
    "队员", "队长", "教练", "会长", "主席", "理事长", "委员", "代表", "作家", "记者",
}

_all_right_tokens = sorted(list(ZH_COMMON_VERBS | ZH_TITLES | ZH_PARTICLES_AND_PREPS), key=len, reverse=True)
ZH_NAME_RIGHT_ALLOWED = re.compile(
    r"^(?:" + "|".join(re.escape(tok) for tok in _all_right_tokens) + r")"
)

ZH_NAME_LEFT_ALLOWED = re.compile(
    r"(?:由|向|对|与|和|同|给|替|帮|关于|专访|采访|记者|学者|专家|教授|副教授|研究员|院士|博士|主任|校长|院长|老师|同志|先生|女士|主席|总理|部长|司长|局长|处长|科长|组长|代表|委员|队员|运动员|教练|裁判|作家|律师|医生|工程师|随后|此前|此后|目前|同时|然后|接着|近日|日前)$"
)


def is_valid_chinese_name_boundary(cand: str, start_pos: int, end_pos: int, text: str) -> bool:
    """
    Maximal candidate span and context confirmation for Chinese person names.
    Enforces maximum span conflict detection and morpheme boundaries:
    - Rejects cand if extending by 1 or 2 characters forms a longer person candidate that is followed
      by a legitimate predicate, particle, or boundary (e.g. 周昕 inside 周昕怡现任 / 周昕怡批评, 李嘉文 inside 李嘉文博荣获 / 李嘉文博批评).
    - Allows cand if immediately followed by non-Han punctuation, functional particles, or a valid verb/title.
    - Fails closed if followed by Han characters that do not form a recognizable word boundary.
    """
    # 1. Left boundary validation
    if start_pos > 0:
        prev_char = text[start_pos - 1]
        if "\u4e00" <= prev_char <= "\u9fff":
            if not ZH_NAME_LEFT_ALLOWED.search(text[:start_pos]):
                return False
        elif prev_char.isalnum() or prev_char == "_":
            return False

    # 2. Right boundary validation
    if end_pos < len(text):
        next_char = text[end_pos]
        if "\u4e00" <= next_char <= "\u9fff":
            # (a) Check if next_char starts an approved particle / preposition
            if next_char in ZH_PARTICLES_AND_PREPS:
                return True

            # (b) Check if next 2-3 chars match a known verb or title directly
            two_chars = text[end_pos : end_pos + 2]
            if two_chars in ZH_COMMON_VERBS or two_chars in ZH_TITLES:
                return True
            three_chars = text[end_pos : end_pos + 3]
            if three_chars in ZH_COMMON_VERBS or three_chars in ZH_TITLES:
                return True

            # (c) Maximal span conflict test:
            # Does extending cand by 1 character form a longer person name candidate ending at a predicate/boundary?
            rem1 = text[end_pos + 1 :]
            if rem1:
                c1 = rem1[0]
                t1_2 = rem1[:2]
                t1_3 = rem1[:3]
                if (
                    (not ("\u4e00" <= c1 <= "\u9fff"))
                    or (c1 in ZH_PARTICLES_AND_PREPS)
                    or (t1_2 in ZH_COMMON_VERBS or t1_2 in ZH_TITLES)
                    or (t1_3 in ZH_COMMON_VERBS or t1_3 in ZH_TITLES)
                ):
                    # Longer candidate exists and terminates at a legitimate boundary/predicate -> conflict!
                    return False
            else:
                # Extending reaches EOF -> longer candidate ends at EOF
                return False

            # Does extending cand by 2 characters form a longer 4-character person candidate ending at a boundary/predicate?
            if len(cand) == 2:
                rem2 = text[end_pos + 2 :]
                if rem2:
                    c2 = rem2[0]
                    t2_2 = rem2[:2]
                    t2_3 = rem2[:3]
                    if (
                        (not ("\u4e00" <= c2 <= "\u9fff"))
                        or (c2 in ZH_PARTICLES_AND_PREPS)
                        or (t2_2 in ZH_COMMON_VERBS or t2_2 in ZH_TITLES)
                        or (t2_3 in ZH_COMMON_VERBS or t2_3 in ZH_TITLES)
                    ):
                        return False
                else:
                    return False

            # If it did not match any known particle, verb/title, or longer span conflict,
            # fail closed on an unresolved Han character sequence.
            return False
        elif next_char.isalnum() or next_char == "_":
            return False

    return True


def extract_mentions_and_aliases(
    source_id: str,
    raw_text: str,
    target_name: str,
    known_aliases: Optional[List[str]] = None,
    evidence_id: Optional[str] = None,
    base_char_offset: int = 0,
) -> List[EntityMention]:
    """
    Extracts mentions of the target person and derives candidate alias hypotheses.
    Fails closed: Returns empty list if target name or recognized alias is not present in raw_text.
    """
    mentions: List[EntityMention] = []

    norm_target = unicodedata.normalize("NFC", target_name.strip())
    norm_text = unicodedata.normalize("NFC", raw_text)

    if not norm_target or not norm_text:
        return mentions

    candidates_to_search = [norm_target]
    if known_aliases:
        for a in known_aliases:
            cand = unicodedata.normalize("NFC", a.strip())
            if cand and cand not in candidates_to_search:
                candidates_to_search.append(cand)


    # Derive natural honorific forms for multi-token names (e.g. Xin Zhou -> Dr. Zhou)
    t_tokens = norm_target.split()
    if len(t_tokens) >= 2 and t_tokens[-1].isalpha():
        last_name = t_tokens[-1]
        for prefix in ["Dr.", "Prof.", "Professor"]:
            h_cand = f"{prefix} {last_name}"
            if h_cand not in candidates_to_search:
                candidates_to_search.append(h_cand)

    seen_spans = set()

    for cand in candidates_to_search:
        is_cand_zh = any("\u4e00" <= c <= "\u9fff" for c in cand)
        # Case-insensitive search using regex word boundaries for ASCII names
        if cand.isascii() and " " not in cand:
            pattern = rf"\b{re.escape(cand)}\b"
        elif cand.isascii():
            tokens = [re.escape(t) for t in cand.split()]
            pattern = rf"\b" + r"\s+".join(tokens) + rf"\b"
        else:
            pattern = re.escape(cand)

        for match in re.finditer(pattern, norm_text, re.IGNORECASE):
            start_pos, end_pos = match.start(), match.end()
            span_key = (start_pos, end_pos)
            if span_key in seen_spans:
                continue

            # Boundary validation for Chinese candidate names:
            if is_cand_zh and not is_valid_chinese_name_boundary(cand, start_pos, end_pos, norm_text):
                continue

            # Reject matches that fall inside an HTML tag / markup (<...>)
            last_open = norm_text.rfind("<", 0, start_pos)
            last_close = norm_text.rfind(">", 0, start_pos)
            if last_open > last_close:
                next_close = norm_text.find(">", start_pos)
                if next_close != -1:
                    continue

            # Reject matches that fall inside dialog / modal / overlay containers or UI action prompts
            start_ctx = max(0, start_pos - 150)
            end_ctx = min(len(norm_text), end_pos + 150)
            context_snippet = norm_text[start_ctx:end_ctx].strip()
            if re.search(r'\b(?:block\s+or\s+report|report\s+or\s+block|overlay-title|close-dialog)\b', context_snippet, re.IGNORECASE):
                continue

            seen_spans.add(span_key)

            matched_text = norm_text[start_pos:end_pos]


            abs_start = base_char_offset + start_pos
            abs_end = base_char_offset + end_pos

            mention_key = hashlib.sha256(
                f"{source_id}:{abs_start}:{abs_end}".encode("utf-8")
            ).hexdigest()[:16]

            raw_id_seed = f"{source_id}:{matched_text}:{abs_start}:{abs_end}"
            mention_id = f"MEN-{hashlib.sha256(raw_id_seed.encode('utf-8')).hexdigest()[:12]}"

            alias_hypotheses: List[AliasRecord] = [
                AliasRecord(
                    alias_value=matched_text,
                    origin_type=OriginType.SOURCE_STATED,
                    verification_status=VerificationStatus.VERIFIED,
                    verification_source_id=source_id,
                )
            ]
            norm_target_spaces = " ".join(norm_target.split())
            norm_matched_spaces = " ".join(matched_text.split())
            if norm_target and norm_target_spaces == norm_matched_spaces and norm_target != matched_text:
                alias_hypotheses.append(
                    AliasRecord(
                        alias_value=norm_target,
                        origin_type=OriginType.SOURCE_STATED,
                        verification_status=VerificationStatus.VERIFIED,
                        verification_source_id=source_id,
                    )
                )
            elif norm_target and norm_target_spaces != norm_matched_spaces:
                alias_hypotheses.append(
                    AliasRecord(
                        alias_value=norm_target,
                        origin_type=OriginType.GENERATED_HYPOTHESIS,
                        verification_status=VerificationStatus.UNVERIFIED,
                        verification_source_id=source_id,
                    )
                )

            mentions.append(
                EntityMention(
                    mention_id=mention_id,
                    raw_name_text=matched_text,
                    source_id=source_id,
                    evidence_id=evidence_id,
                    mention_key=mention_key,
                    char_start=abs_start,
                    char_end=abs_end,
                    context_snippet=context_snippet,
                    alias_hypotheses=alias_hypotheses,
                )
            )

    return mentions
