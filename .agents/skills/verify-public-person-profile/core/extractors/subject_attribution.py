"""
Unified Subject Attribution and Coreference Resolution Module.

Provides:
1. Full Person Mention Universe scanning across clauses/sentences
   (including object positions, titles, and unregistered third-party persons).
2. Post-predicate (cleft / focal) subject detection (e.g. '的是张伟', '获奖者为张伟').
3. Strict nearest compatible antecedent binding for pronouns with gender/number validation.
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Set, Tuple


ZH_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳"
    "酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞"
    "熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓"
    "郁单杭洪包诸左石崔吉钮龚嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁"
    "仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉"
    "宰郦雍郤璩桑桂濮扈套寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东"
    "欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
)
ZH_COMPOUND_SURNAMES = [
    "欧阳", "司马", "诸葛", "上官", "令狐", "皇甫", "南宫", "东方", "尉迟", "公孙", "长孙", "夏侯",
]

COMMON_MALE_FIRST_NAMES = {
    "bob", "david", "john", "liam", "michael", "james", "robert", "william", "richard",
    "thomas", "charles", "daniel", "matthew", "anthony", "donald", "paul", "mark", "george",
    "kenneth", "steven", "edward", "brian", "ronald", "timothy", "jason", "jeffrey", "ryan",
    "jacob", "gary", "nicholas", "eric", "stephen", "jonathan", "larry", "justin", "scott",
    "brandon", "frank", "benjamin", "gregory", "samuel", "raymond", "patrick", "alexander",
    "jack", "dennis", "jerry", "tyler", "aaron", "jose", "henry", "douglas", "peter", "adam",
    "nathan", "zachary", "walter", "kyle", "harold", "carl", "jeremy", "keith", "roger",
    "gerald", "ethan", "arthur", "terry", "christian", "sean", "lawrence", "austin", "joe",
    "noah", "jesse", "albert", "billy", "bruce", "willie", "jordan", "dylan", "alan", "ralph",
    "gabriel", "roy", "juan", "wayne", "eugene", "logan", "randy", "louis", "russell",
    "vincent", "philip", "bobby", "johnny", "bradley", "martin", "andrew", "ian",
    "grant", "xin", "ming", "rahul", "amit", "raj", "sina",
}

COMMON_FEMALE_FIRST_NAMES = {
    "alice", "mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan", "jessica",
    "sarah", "karen", "nancy", "lisa", "betty", "margaret", "sandra", "ashley", "kimberly",
    "emily", "donna", "michelle", "dorothy", "carol", "amanda", "melissa", "deborah", "stephanie",
    "rebecca", "sharon", "laura", "cynthia", "kathleen", "amy", "shirley", "angela", "helen",
    "anna", "brenda", "pamela", "nicole", "samantha", "katherine", "christine", "debra", "rachel",
    "carolyn", "janet", "catherine", "maria", "heather", "diane", "ruth", "julie", "olivia",
    "joyce", "virginia", "victoria", "kelly", "lauren", "christina", "joan", "evelyn", "judith",
    "megan", "cheryl", "andrea", "hannah", "martha", "jacqueline", "frances", "gloria", "ann",
    "teresa", "kathryn", "sara", "janice", "jean", "madison", "doris", "abigail", "julia",
    "judy", "grace", "denise", "amber", "marilyn", "beverly", "danielle", "theresa", "sophia",
    "marie", "diana", "brittany", "natalie", "isabella", "charlotte", "rose", "kayla", "alexis",
    "katniss", "vaishali",
}

ALL_COMMON_FIRST_NAMES = COMMON_MALE_FIRST_NAMES | COMMON_FEMALE_FIRST_NAMES

PINYIN_SURNAMES = {
    "zhou", "chen", "wang", "li", "zhang", "liu", "yang", "huang", "wu", "zhao",
    "xu", "sun", "ma", "zhu", "hu", "guo", "he", "gao", "lin", "zheng", "xie",
    "song", "tang", "han", "feng", "deng", "cao", "peng", "zeng", "xiao", "tian",
    "dong", "pan", "yuan", "cai", "jiang", "yu", "du", "ye", "cheng", "wei", "su",
    "lu", "ding", "ren", "shen", "yao", "luo", "fan", "jin", "fang", "shi", "cui",
    "jia", "liao", "bai", "meng", "qin", "qiu", "yin", "xue", "yan", "duan", "lei",
    "hou", "long", "tao", "mao", "shao", "wan", "qian", "dai", "mo", "kong", "xiang",
}

GPE_TOKENS = {
    "haven", "carolina", "dakota", "hampshire", "jersey", "mexico", "york", "angeles", "diego",
    "antonio", "francisco", "jose", "seattle", "boston", "chicago", "london", "paris", "beijing",
    "shanghai", "tokyo", "singapore", "island", "islands", "valley", "beach", "city", "county",
    "state", "republic", "kingdom", "village", "town", "district", "province", "country",
    "england", "scotland", "wales", "ireland", "america", "canada", "australia", "europe", "asia",
    "africa", "china", "japan", "germany", "france", "russia", "india", "brazil", "texas",
    "california", "florida", "ohio", "michigan", "illinois", "pennsylvania", "georgia", "virginia",
    "washington", "massachusetts", "connecticut", "maryland", "colorado", "tennessee", "indiana",
    "missouri", "wisconsin", "minnesota", "alabama", "louisiana", "kentucky", "oregon", "oklahoma",
    "rhode", "delaware", "vermont", "maine", "hawaii", "alaska", "nevada", "utah",
    "kansas", "arkansas", "mississippi", "iowa", "idaho", "nebraska", "montana", "wyoming",
}

DIRECTIONAL_OR_GEOGRAPHIC_MODIFIERS = {
    "new", "old", "north", "south", "east", "west", "northern", "southern", "eastern", "western",
    "upper", "lower", "central", "grand", "great", "little", "big", "mount", "lake", "fort",
    "saint", "san", "santa", "los", "las", "el", "la",
}

AWARD_AND_WORK_TOKENS = {
    "prize", "award", "medal", "fellowship", "scholarship", "grant", "honor", "cup", "trophy",
    "project", "initiative", "system", "model", "protocol", "theory", "theorem", "law", "equation",
    "framework", "program", "database", "format", "paper", "journal", "magazine", "review", "press",
    "times", "post", "news", "gazette", "herald", "tribune", "chronicle", "quarterly", "report",
}

LOCATION_PREPOSITIONS_PATTERN = re.compile(
    r"\b(?:moved\s+to|relocated\s+to|traveled\s+to|travelled\s+to|travelling\s+to|traveling\s+to|"
    r"lives?\s+in|living\s+in|located\s+in|headquartered\s+in|based\s+in|born\s+in|"
    r"arrived\s+in|trip\s+to|fled\s+to|flight\s+to|settled\s+in|stayed\s+in|in\s+downtown)\s+$",
    re.IGNORECASE,
)


def normalize_for_name_comparison(name: str) -> str:
    """
    Normalize person name for strict identity comparison.
    Strips English honorifics (Dr., Prof., Mr., Ms., etc.) and Chinese titles (教授, 博士, 院士, etc.).
    """
    norm = unicodedata.normalize("NFKC", name or "").strip().lower()
    norm = re.sub(r"^(?:prof(?:essor|\.)?|dr\.|mr\.|ms\.|mrs\.)\s+", "", norm)
    norm = re.sub(r"^(?:教授|博士|院士|主任|老师|学者|会长|校长|院长)", "", norm)
    norm = re.sub(r"(?:教授|博士|院士|主任|老师|学者|会长|校长|院长|先生|女士)$", "", norm)
    return norm.strip()


def is_exact_or_verified_alias_match(
    name: str,
    target_names: Set[str],
    known_aliases: Optional[List[str]] = None,
) -> bool:
    """
    Strict matching: Only exact equality of normalized full names or verified alias entries.
    Strictly forbids substring inclusion (e.g. 'Alice Smith' in 'Alice Smithson' is REJECTED).
    Does NOT automatically treat honorific surnames (e.g. 'Dr. Zhou') as aliases without explicit verification.
    """
    norm_name = normalize_for_name_comparison(name)
    if not norm_name:
        return False

    all_targets = set(target_names or set())
    if known_aliases:
        all_targets.update(known_aliases)

    for t in all_targets:
        if not t:
            continue
        norm_t = normalize_for_name_comparison(t)
        if norm_name == norm_t:
            return True
    return False


def infer_gender(name: str) -> str:
    """Infer grammatical gender ('male', 'female', 'unknown') from person name."""
    norm = name.strip()
    if not norm:
        return "unknown"

    # Check explicit titles/honorifics
    if re.search(r"\b(?:Mr\.|Sir|Lord|King)\b|先生", norm):
        return "male"
    if re.search(r"\b(?:Ms\.|Mrs\.|Miss|Lady|Queen)\b|女士", norm):
        return "female"

    tokens = [t.strip(".,;:?!") for t in norm.split() if t.strip(".,;:?!")]
    while tokens and tokens[0].lower() in {"dr", "prof", "professor", "rev", "pastor", "officer", "col", "gen"}:
        tokens.pop(0)

    if tokens:
        first_token = tokens[0].lower()
        if first_token in COMMON_MALE_FIRST_NAMES:
            return "male"
        if first_token in COMMON_FEMALE_FIRST_NAMES:
            return "female"

    return "unknown"


def build_person_mention_universe(
    text: str,
    known_persons: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Scans text to detect all person mentions (English & Chinese),
    including third-party figures in subject or object positions.
    Returns sorted list of mention dicts:
    [{"name": str, "start": int, "end": int, "gender": str}]
    """
    mentions: List[Dict[str, Any]] = []
    seen_spans = set()

    from core.extractors.mention_extractor import is_valid_chinese_name_boundary

    # 1. Known target persons & aliases
    if known_persons:
        for kp in known_persons:
            kp_clean = kp.strip()
            if not kp_clean:
                continue
            kp_esc = re.escape(kp_clean)
            pat = rf"\b{kp_esc}\b" if kp_clean.isascii() else kp_esc
            for m in re.finditer(pat, text, re.IGNORECASE):
                if not kp_clean.isascii():
                    if not is_valid_chinese_name_boundary(kp_clean, m.start(), m.end(), text):
                        continue
                span = (m.start(), m.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    mentions.append({
                        "name": m.group(0),
                        "start": m.start(),
                        "end": m.end(),
                        "gender": infer_gender(kp_clean),
                        "entity_type": "PERSON",
                        "confidence": 1.0,
                    })

    # 2. English Person Name Patterns
    # (a) Honorific + Name: e.g. Dr. Bob Jones, Prof. Alice Smith, Mr. Jones
    en_hon_pat = re.compile(
        r"\b(?:Prof(?:essor|\.)?|Dr\.|Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
    )
    for m in en_hon_pat.finditer(text):
        span = (m.start(), m.end())
        if span not in seen_spans:
            seen_spans.add(span)
            mentions.append({
                "name": m.group(0),
                "start": m.start(),
                "end": m.end(),
                "gender": infer_gender(m.group(0)),
                "entity_type": "PERSON",
                "confidence": 0.98,
            })

    # (b) Standard Capitalized Full Names: e.g. "Bob Jones", "Alice Smith", "New Haven"
    # Exclude capitalized entities containing organizational, role, award, academic discipline, or location tokens
    NON_PERSON_TOKENS = {
        "university", "college", "school", "institute", "hospital", "center", "centre", "department", "dept",
        "lab", "laboratory", "foundation", "society", "association", "group", "company",
        "corp", "inc", "ltd", "board", "committee", "council", "academy", "faculty", "division", "office",
        "professor", "scientist", "dean", "director", "chair", "president", "fellow",
        "assistant", "associate", "lecturer", "instructor", "researcher", "engineer",
        "physician", "doctor", "specialist", "officer", "manager", "student", "candidate",
        "hall", "building", "house", "street", "road", "avenue", "park",
        "medicine", "health", "sciences", "arts", "studies", "affairs", "service", "services",
        "communication", "journalism", "education", "united", "states",
        # Academic disciplines & fields
        "biology", "chemistry", "physics", "microbiology", "immunology", "neuroscience", "pathology",
        "oncology", "genetics", "cardiology", "surgery", "psychiatry", "philosophy", "economics",
        "sociology", "anthropology", "engineering", "mathematics", "microbial", "molecular", "cellular",
        "biomedical", "clinical", "computational", "applied", "theoretical", "environmental", "global",
        "public", "policy", "business", "law", "history", "literature", "linguistics", "pathogenesis",
        "infectious", "diseases", "disease", "genomics", "biochemistry", "biophysics", "ecology",
        "evolution", "astronomy", "astrophysics", "geology", "geophysics", "humanities", "social",
        "management", "finance", "marketing", "accounting", "operations", "administration", "technology",
        "information", "systems", "artificial", "intelligence", "data", "science", "statistics",
    }
    en_name_pat = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
    for m in en_name_pat.finditer(text):
        cand_name = m.group(1).strip()
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        tokens_lower = [t.lower() for t in cand_name.split()]
        prefix = text[:m.start()]
        suffix = text[m.end():]

        if any(t in NON_PERSON_TOKENS for t in tokens_lower):
            continue

        first_token = tokens_lower[0]
        has_person_first_name = first_token in ALL_COMMON_FIRST_NAMES

        # Check if matched entity is a GPE / location or modified by directional prefix
        # Intrinsic person name evidence takes precedence unless explicit location modifier
        is_gpe = False
        if not has_person_first_name:
            is_gpe = (
                any(t in GPE_TOKENS for t in tokens_lower)
                or (tokens_lower[0] in DIRECTIONAL_OR_GEOGRAPHIC_MODIFIERS)
                or bool(LOCATION_PREPOSITIONS_PATTERN.search(prefix))
            )
        elif tokens_lower[0] in DIRECTIONAL_OR_GEOGRAPHIC_MODIFIERS:
            is_gpe = True

        if is_gpe:
            seen_spans.add(span)
            mentions.append({
                "name": cand_name,
                "start": m.start(),
                "end": m.end(),
                "gender": "unknown",
                "entity_type": "GPE",
                "confidence": 0.95,
            })
            continue

        # Check if matched entity is an Award, Publication, or Project
        is_award = False
        if not has_person_first_name:
            if any(t in AWARD_AND_WORK_TOKENS for t in tokens_lower):
                is_award = True
        else:
            if tokens_lower[-1] in {"award", "prize", "medal", "fellowship", "scholarship"}:
                is_award = True

        if is_award:
            seen_spans.add(span)
            mentions.append({
                "name": cand_name,
                "start": m.start(),
                "end": m.end(),
                "gender": "unknown",
                "entity_type": "AWARD",
                "confidence": 0.95,
            })
            continue

        # Preceding institutional context check: e.g. "Department of ...", "School of ..."
        if re.search(r"\b(?:Department|Dept\.?|School|Faculty|Institute|Center|Centre|Division|College|University|Office|Program|Laboratory|Lab)\s+(?:of|for|in)\s+$", prefix, re.IGNORECASE):
            seen_spans.add(span)
            mentions.append({
                "name": cand_name,
                "start": m.start(),
                "end": m.end(),
                "gender": "unknown",
                "entity_type": "ORG",
                "confidence": 0.95,
            })
            continue

        # Following institutional context check: e.g. "... Lab", "... Center"
        if re.match(r"^\s+(?:Lab|Laboratory|Group|Institute|Center|Centre|Department|Office|Foundation|Hospital|Clinic|School|University|Press)\b", suffix, re.IGNORECASE):
            seen_spans.add(span)
            mentions.append({
                "name": cand_name,
                "start": m.start(),
                "end": m.end(),
                "gender": "unknown",
                "entity_type": "ORG",
                "confidence": 0.95,
            })
            continue

        # Positive Person Name validation
        is_known_person_first_name = first_token in ALL_COMMON_FIRST_NAMES
        is_pinyin_person = False
        if len(tokens_lower) == 2:
            if tokens_lower[0] in PINYIN_SURNAMES or tokens_lower[-1] in PINYIN_SURNAMES:
                is_pinyin_person = True

        if is_known_person_first_name:
            entity_type = "PERSON"
            confidence = 0.95
        elif is_pinyin_person:
            entity_type = "PERSON"
            confidence = 0.85
        else:
            entity_type = "UNKNOWN"
            confidence = 0.50

        seen_spans.add(span)
        mentions.append({
            "name": cand_name,
            "start": m.start(),
            "end": m.end(),
            "gender": infer_gender(cand_name),
            "entity_type": entity_type,
            "confidence": confidence,
        })

    # 3. Chinese Person Name Patterns
    surnames_regex = "[" + "".join(ZH_SURNAMES) + "]"
    compound_regex = "(?:" + "|".join(ZH_COMPOUND_SURNAMES) + ")"
    zh_person_pat = re.compile(
        rf"(?:{compound_regex}[\u4e00-\u9fff]{{1,2}}|{surnames_regex}[\u4e00-\u9fff]{{1,2}})"
    )
    ZH_NON_PERSONS = {
        "北京", "清华", "北大", "复旦", "浙江", "中国", "美国", "英国", "法国", "德国", "日本",
        "一零一", "海淀", "朝阳", "西城", "东城", "学院", "大学", "公司", "集团", "医院", "学者",
        "教授", "博士", "硕士", "目前", "随后", "此前", "此后", "同时", "并且", "以及", "岁月静好",
    }

    for m in zh_person_pat.finditer(text):
        zh_cand = m.group(0)
        if zh_cand in ZH_NON_PERSONS:
            continue
        if not is_valid_chinese_name_boundary(zh_cand, m.start(), m.end(), text):
            continue
        span = (m.start(), m.end())
        if span not in seen_spans:
            seen_spans.add(span)
            mentions.append({
                "name": zh_cand,
                "start": m.start(),
                "end": m.end(),
                "gender": infer_gender(zh_cand),
                "entity_type": "PERSON",
                "confidence": 0.95,
            })

    mentions.sort(key=lambda x: x["start"])
    return mentions


def detect_post_predicate_subject(clause: str) -> Optional[str]:
    """
    Detects cleft / post-predicate focus structures attributing action to a named person:
    - Chinese: '随后荣获 Nobel Prize 的是张伟' -> '张伟'
               '获得者为李四' -> '李四'
               '获奖者系王五' -> '王五'
    - English: 'The recipient was Bob Jones' -> 'Bob Jones'
               'It was Bob Jones who was awarded...' -> 'Bob Jones'
    Returns the detected post-predicate subject person name, or None.
    """
    c_strip = clause.strip()
    if not c_strip:
        return None

    # 1. Chinese cleft / post-predicate patterns
    surnames_regex = "[" + "".join(ZH_SURNAMES) + "]"
    compound_regex = "(?:" + "|".join(ZH_COMPOUND_SURNAMES) + ")"
    zh_name_expr = rf"(?:{compound_regex}[\u4e00-\u9fff]{{1,2}}|{surnames_regex}[\u4e00-\u9fff]{{1,2}}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"

    zh_cleft_pat = re.compile(
        rf"(?:的是|者为|获奖者为|获得者是|获得者为|任职者为|任职者是|当选者为|当选者是|作者为|作者是|的为|的系)\s*({zh_name_expr})\s*(?:[。！？.!?\s]|$)"
    )
    m_zh = zh_cleft_pat.search(c_strip)
    if m_zh:
        post_subj = m_zh.group(1).strip()
        if post_subj not in {"北京", "清华", "北大", "中国", "美国", "大学", "公司", "医院", "学院"}:
            return post_subj

    # 2. English cleft / post-predicate patterns
    en_cleft_pat = re.compile(
        r"(?:(?:the\s+)?(?:winner|recipient|awardee|author|person|one)\s+(?:is|was)|it\s+(?:is|was))\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+who\b|\s*[。！？.!?\s]|$)",
        re.IGNORECASE,
    )
    m_en = en_cleft_pat.search(c_strip)
    if m_en:
        cand = m_en.group(1).strip()
        if cand.lower() not in {"nobel prize", "yale university", "harvard university", "associate dean", "research scientist"}:
            return cand

    return None


def resolve_pronoun_antecedent(
    pronoun: str,
    pronoun_start: int,
    text: str,
    target_names: Set[str],
    all_mentions: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """
    Resolves pronoun to nearest compatible antecedent.
    Enforces:
    1. Recency: candidate must precede pronoun_start (within 250 chars, at most 1 sentence boundary, no paragraph breaks).
    2. Entity Type: candidate must be an actual PERSON entity (GPE, ORG, AWARD do not compete).
    3. Gender compatibility:
       - 'he/him/his': Incompatible with female names.
       - 'she/her/hers': Incompatible with male names.
    4. Nearest compatible antecedent:
       Must be the closest compatible person before pronoun_start.
       If the nearest compatible antecedent is NOT in target_names (e.g. it is 'Bob Jones' or 'Alice Smithson' when target is 'Alice Smith'),
       binding to target_names is REJECTED.

    Returns:
    (is_target_bound: bool, resolved_name: Optional[str])
    """
    p_lower = pronoun.lower().strip()

    req_gender = "any"
    if p_lower in {"he", "him", "his"}:
        req_gender = "male"
    elif p_lower in {"she", "her", "hers"}:
        req_gender = "female"

    prior_mentions = [m for m in all_mentions if m["end"] <= pronoun_start]
    if not prior_mentions:
        return False, None

    valid_prior = []
    for m in prior_mentions:
        ent_type = m.get("entity_type", "PERSON")
        # Strictly exclude non-person entities (GPE, ORG, AWARD) from pronoun competition
        if ent_type not in {"PERSON", "UNKNOWN"}:
            continue

        gap = text[m["end"]:pronoun_start]
        if re.search(r"\n\s*\n|<\s*(?:p|div|section|article|blockquote)\b", gap, re.IGNORECASE):
            continue
        if len(re.findall(r"[。！？.!?]", gap)) > 1:
            continue
        if (pronoun_start - m["end"]) > 250:
            continue
        valid_prior.append(m)

    if not valid_prior:
        return False, None

    compatible = []
    for m in valid_prior:
        g = m.get("gender", "unknown")
        if req_gender == "male" and g == "female":
            continue
        if req_gender == "female" and g == "male":
            continue
        compatible.append(m)

    if not compatible:
        return False, None

    nearest_m = max(compatible, key=lambda x: x["end"])
    nearest_name = nearest_m["name"].strip()

    # If the nearest compatible entity is UNKNOWN, it acts as a veto-only blocker:
    # it cannot establish positive identity for target, and blocks jumping over it to an earlier target.
    if nearest_m.get("entity_type") == "UNKNOWN":
        return False, nearest_name

    # Strict target identity match: normalized full name exact equality or verified alias (NO substring inclusion!)
    is_target = is_exact_or_verified_alias_match(nearest_name, target_names)

    if is_target:
        return True, nearest_name
    else:
        return False, nearest_name
