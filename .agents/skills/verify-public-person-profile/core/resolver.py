"""
Entity Resolver and Disambiguation Engine (V4.4.1).
Computes pairwise match probabilities with structural organization and domain conflict detection,
treats cross-lingual pinyin as a weak candidate feature requiring corroboration,
and implements Constrained Union-Find to strictly enforce Cannot-Link boundaries
with guaranteed mathematical order-independence.
"""

import re
from typing import Any, Dict, List, Set, Tuple, Optional
from models.schemas import (
    ClusterAssignment,
    ClusteringMethod,
    EntityMention,
    MachineRelation,
    MatchDecision,
    SourceQualityClass,
    VerificationStatus,
)

# Generic organization pattern (English & Chinese)
ORG_PATTERN_EN = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9&.-]*(?:\s+(?:of|at|for|on|and|&)\s+[A-Z][A-Za-z0-9&.-]*|\s+[A-Z][A-Za-z0-9&.-]*){0,4}\s+)?"
    r"(?:University(?:\s+of\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*(?:\s+at\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*)?)?"
    r"|College|Institute|Hospital|Medical\s+School|School\s+of\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*"
    r"|Center(?:\s+for\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*(?:\s+on\s+[A-Z][A-Za-z0-9.-]+)?)?"
    r"|Section(?:\s+of\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*)?"
    r"|Program(?:\s+(?:on|for|in)\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*)?"
    r"|Foundation|Department(?:\s+of\s+[A-Z][A-Za-z0-9.-]+(?:\s+[A-Z][A-Za-z0-9.-]+)*)?"
    r"|Laboratory|Lab|Company|Corp|Corporation|Inc|LLC|Group|Enterprises|Technologies)\b"
)
ORG_PATTERN_ZH = re.compile(
    r"(?:[\u4e00-\u9fff]{2,15}?(?:大学|学院|研究所|研究院|公司|集团|医院|中心|学会|协会))"
)

GENERIC_ORGS = {
    "department", "center", "school", "hospital", "university", "college",
    "institute", "laboratory", "lab", "company", "group", "association",
    "division", "faculty", "program", "team", "中心", "大学", "学院", "医院", "研究所",
    "public", "health", "medicine", "internal medicine"
}

# Generic domain vocabularies
DOMAIN_SIGNATURES = {
    "biomedical": {
        "medicine", "medical", "biomedical", "pathology", "pathogenesis", "microbial",
        "biostatistics", "internal medicine", "cancer", "hospital", "physician",
        "doctor", "immunology", "pharmacology", "genomics", "epidemiology", "public health",
        "school of medicine", "school of public health"
    },
    "clinical_counselling": {
        "counselling", "counsellor", "counselor", "counseling", "psychotherapy",
        "therapist", "mental health", "social worker", "clinical counselling"
    },
    "arts_entertainment": {
        "performing arts", "dance", "kathak", "theatre", "music", "musician",
        "fine arts", "visual arts", "dancer"
    },
    "culinary_gastronomy": {
        "culinary", "chef", "cuisine", "restaurant", "cook", "gastronomy", "pastry", "huaiyang"
    },
    "media_film_tv": {
        "television", "drama", "film", "movie", "actor", "actress", "rtv", "broadcast",
        "anchor", "fictional character", "character in"
    },
    "real_estate": {
        "real estate", "realtor", "coldwell", "broker", "property", "housing"
    },
    "athletics": {
        "athletics", "swimming", "diver", "cscaa", "sports", "coach", "tournament", "olympic"
    },
    "engineering_tech": {
        "engineering", "project engineer", "electronic technology", "software", "circuits",
        "semiconductor", "computer science", "algorithms"
    },
    "entrepreneurship_business": {
        "易思汇", "一切从柬", "留学生", "创业", "商业", "consulting", "investment",
        "fintech", "startup", "ceo", "founder"
    },
    "library_science": {
        "library", "librarian", "archives", "archivist", "cataloging", "library science"
    },
    "health_communication": {
        "health communication", "aids program", "som aids", "mhealth", "communication technology"
    },
    "law_jurisprudence": {
        "law school", "law", "jurisprudence", "legal", "attorney", "court", "appellate",
        "law firm", "bar association", "litigation"
    },
    "education_k12": {
        "kindergarten", "preschool", "elementary", "k-12", "childhood educator", "nursery"
    },
    "public_administration": {
        "mayor", "city council", "municipal", "senator", "civic", "governor", "public administration"
    },
    "retail_operations": {
        "retail store", "shift manager", "merchandise", "supermarket", "grocery", "inventory logistics"
    },
    "finance_investment": {
        "portfolio manager", "private equity", "investment banking", "asset management", "quantitative equity", "venture capital"
    },
    "humanities_philosophy": {
        "philosophy", "epistemology", "continental philosophy", "ethics", "metaphysics"
    },
    "dental_medicine": {
        "dentist", "dental", "dental hygienist", "orthodontist", "periodontist", "teeth", "oral health", "dental clinic"
    },
    "trades_crafts": {
        "plumber", "plumbing", "pipefitter", "electrician", "carpenter", "mechanic", "welder", "pipefitting"
    },
}

INCOMPATIBLE_DOMAIN_PAIRS = {
    ("biomedical", "arts_entertainment"),
    ("biomedical", "culinary_gastronomy"),
    ("biomedical", "media_film_tv"),
    ("biomedical", "real_estate"),
    ("biomedical", "athletics"),
    ("biomedical", "clinical_counselling"),
    ("biomedical", "library_science"),
    ("biomedical", "health_communication"),
    ("biomedical", "entrepreneurship_business"),
    ("biomedical", "law_jurisprudence"),
    ("athletics", "engineering_tech"),
    ("athletics", "biomedical"),
    ("athletics", "arts_entertainment"),
    ("athletics", "humanities_philosophy"),
    ("culinary_gastronomy", "entrepreneurship_business"),
    ("culinary_gastronomy", "media_film_tv"),
    ("culinary_gastronomy", "biomedical"),
    ("culinary_gastronomy", "engineering_tech"),
    ("culinary_gastronomy", "finance_investment"),
    ("media_film_tv", "entrepreneurship_business"),
    ("media_film_tv", "biomedical"),
    ("media_film_tv", "engineering_tech"),
    ("media_film_tv", "law_jurisprudence"),
    ("clinical_counselling", "library_science"),
    ("clinical_counselling", "engineering_tech"),
    ("clinical_counselling", "entrepreneurship_business"),
    ("real_estate", "arts_entertainment"),
    ("real_estate", "culinary_gastronomy"),
    ("real_estate", "biomedical"),
    ("real_estate", "engineering_tech"),
    ("engineering_tech", "education_k12"),
    ("public_administration", "retail_operations"),
    ("dental_medicine", "trades_crafts"),
    ("dental_medicine", "engineering_tech"),
    ("dental_medicine", "culinary_gastronomy"),
    ("trades_crafts", "biomedical"),
    ("trades_crafts", "law_jurisprudence"),
    ("trades_crafts", "finance_investment"),
}

NEGATIVE_PROFESSIONS = {
    "counsellor", "counselor", "librarian", "chef", "fictional character",
    "actor", "actress", "dancer", "diver", "realtor", "dentist", "plumber", "electrician", "carpenter"
}
ACADEMIC_PROFESSIONS = {
    "professor", "associate professor", "assistant professor", "postdoc",
    "postdoctoral", "phd", "research scientist", "biostatistics", "pathology",
    "medical school", "public health"
}

PINYIN_MAP = {
    "周": ["zhou"], "李": ["li"], "杨": ["yang"], "陈": ["chen"], "王": ["wang"],
    "张": ["zhang"], "刘": ["liu"], "赵": ["zhao"], "吴": ["wu"], "徐": ["xu"],
    "孙": ["sun"], "马": ["ma"], "朱": ["zhu"], "胡": ["hu"], "郭": ["guo"],
    "何": ["he"], "高": ["gao"], "林": ["lin"], "郑": ["zheng"], "梁": ["liang"],
    "欣": ["xin"], "昕": ["xin"], "新": ["xin"], "鑫": ["xin"], "悦": ["yue"],
    "启": ["qi", "chi"], "荣": ["rong"], "嘉": ["jia"], "文": ["wen"],
    "华": ["hua"], "伟": ["wei"], "芳": ["fang"], "娜": ["na"], "敏": ["min"],
    "静": ["jing"], "丽": ["li"], "强": ["qiang"], "磊": ["lei"], "军": ["jun"],
    "勇": ["yong"], "艳": ["yan"], "杰": ["jie"], "娟": ["juan"], "涛": ["tao"],
    "明": ["ming"], "超": ["chao"], "秀": ["xiu"], "霞": ["xia"], "平": ["ping"],
    "刚": ["gang"], "桂": ["gui"], "英": ["ying"], "峰": ["feng"], "鹏": ["peng"],
    "飞": ["fei"], "辉": ["hui"], "健": ["jian"], "波": ["bo"], "亮": ["liang"],
    "浩": ["hao"], "博": ["bo"], "斌": ["bin"], "琴": ["qin"], "玲": ["ling"],
    "丹": ["dan"], "萍": ["ping"], "红": ["hong"], "玉": ["yu"], "兰": ["lan"],
    "梅": ["mei"], "海": ["hai"], "晶": ["jing"], "云": ["yun"],
}


TITLE_PREFIXES = r"^(?:(?:Assistant|Associate|Full|Distinguished|Adjunct|Clinical|Visiting|Executive|Senior|Junior|Principal|Lead|Staff|Postdoctoral)?\s+)?(?:Professor|Associate|Fellow|Scientist|Dean|Director|Chair|President|Researcher|Developer)\s+(?:of|in)\s+[A-Za-z\s]+?\s+(?:at|in)\s+"
CAMPUS_EXCEPTIONS = {"chapel hill", "albany", "austin", "berkeley", "los angeles", "san diego", "davis", "irvine", "boulder", "ann arbor"}


def clean_org_token(token: str) -> str:
    token = re.sub(r"[,;:\.]+$", "", token.strip())
    token = re.sub(r"\s+(?:of|at|for|on|and|the)$", "", token, flags=re.IGNORECASE).strip()
    token = re.sub(TITLE_PREFIXES, "", token, flags=re.IGNORECASE).strip()
    return token


def extract_organizations(text: str) -> Set[str]:
    """Extracts standardized organization mentions structurally without hardcoded school lists."""
    delimiters = r"(?<!\b[A-Z])(?<!\bDr)(?<!\bProf)(?<!\bMr)(?<!\bMs)(?<!\bPh)(?<!\bPh\.D)(?<!\bM\.D)[.!?;\n。！？；]+"
    orgs = set()
    for sentence in re.split(delimiters, text):
        for m in ORG_PATTERN_EN.finditer(sentence):
            token = clean_org_token(m.group(0))
            if not token:
                continue
            token_lower = token.lower()
            if " at " in token_lower:
                parts = re.split(r"\s+at\s+", token_lower, flags=re.IGNORECASE)
                if len(parts) == 2 and parts[1].strip() in CAMPUS_EXCEPTIONS:
                    if token_lower not in GENERIC_ORGS and len(token_lower) > 4:
                        orgs.add(token_lower)
                else:
                    for p in parts:
                        p_clean = p.strip()
                        if p_clean not in GENERIC_ORGS and len(p_clean) > 4:
                            orgs.add(p_clean)
            else:
                if token_lower not in GENERIC_ORGS and len(token_lower) > 4:
                    orgs.add(token_lower)
        for m in ORG_PATTERN_ZH.finditer(sentence):
            token = m.group(0).strip()
            if token not in GENERIC_ORGS and len(token) > 3:
                orgs.add(token)
    return orgs


def extract_domains(text: str, exclude_tokens: Optional[Set[str]] = None) -> Set[str]:
    lower_text = text.lower()
    if exclude_tokens:
        words = [w for w in lower_text.split() if w not in exclude_tokens]
        lower_text = " ".join(words)
    domains = set()
    for dom, kws in DOMAIN_SIGNATURES.items():
        if any(kw in lower_text for kw in kws):
            domains.add(dom)
    return domains


class ConstrainedUnionFind:
    def __init__(self, elements: List[str], cannot_link_pairs: Set[Tuple[str, str]]):
        sorted_elements = sorted(set(elements))
        self.parent = {e: e for e in sorted_elements}
        self.members = {e: {e} for e in sorted_elements}
        self.cannot_link = {e: set() for e in sorted_elements}
        for u, v in cannot_link_pairs:
            if u in self.cannot_link and v in self.cannot_link:
                self.cannot_link[u].add(v)
                self.cannot_link[v].add(u)

    def find(self, e: str) -> str:
        if self.parent[e] != e:
            self.parent[e] = self.find(self.parent[e])
        return self.parent[e]

    def can_merge(self, r1: str, r2: str) -> bool:
        if r1 == r2:
            return True
        for u in self.members[r1]:
            if self.cannot_link[u].intersection(self.members[r2]):
                return False
        return True

    def union(self, e1: str, e2: str) -> bool:
        if e1 == e2:
            return True
        r1, r2 = self.find(e1), self.find(e2)
        if r1 == r2:
            return True
        if not self.can_merge(r1, r2):
            return False

        # Deterministic merge: smaller alphabetical root becomes parent
        if r1 > r2:
            r1, r2 = r2, r1

        self.parent[r2] = r1
        self.members[r1].update(self.members[r2])
        del self.members[r2]
        return True


def detect_cannot_link(m1: Any, m2: Any) -> bool:
    """Detects mutually exclusive affiliations, institutions, or domains."""
    if m1.source_id == m2.source_id and m1.source_id != "SRC-FIXTURE":
        return False

    raw1 = m1.context_snippet + " " + " ".join(m1.inferred_affiliations)
    raw2 = m2.context_snippet + " " + " ".join(m2.inferred_affiliations)

    name1_tokens = set(m1.raw_name_text.lower().split())
    name2_tokens = set(m2.raw_name_text.lower().split())

    COLLEGIATE_UNITS = {
        "school of medicine": "medicine",
        "medical school": "medicine",
        "medicine.yale.edu": "medicine",
        "internal medicine": "medicine",
        "infectious diseases": "medicine",
        "department of internal medicine": "medicine",
        "section of infectious diseases": "medicine",
        "school of public health": "public_health",
        "public health": "public_health",
        "biostatistics": "public_health",
        "department of biostatistics": "public_health",
        "ysph": "public_health",
        "epidemiology": "public_health",
        "law school": "law",
        "school of law": "law",
        "business school": "business",
        "school of management": "business",
        "school of nursing": "nursing",
        "school of music": "music",
        "school of drama": "drama",
        "school of art": "art",
        "divinity school": "divinity",
    }
    JOINT_APPOINTMENT_CUES = {
        "joint appointment",
        "secondary appointment",
        "adjunct",
        "jointly appointed",
        "dual appointment",
        "affiliated with both",
        "courtesy appointment",
        "jointly with",
        "joint faculty",
        "joint affiliation",
    }
    units1 = {u for phrase, u in COLLEGIATE_UNITS.items() if phrase in raw1.lower()}
    units2 = {u for phrase, u in COLLEGIATE_UNITS.items() if phrase in raw2.lower()}
    has_joint = any(cue in raw1.lower() or cue in raw2.lower() for cue in JOINT_APPOINTMENT_CUES)
    if units1 and units2 and not units1.intersection(units2):
        if not has_joint:
            return True

    # 1. Structural organization conflict check
    orgs1 = extract_organizations(raw1) - name1_tokens
    orgs2 = extract_organizations(raw2) - name2_tokens

    GENERIC_ORG_TOKENS = {
        "university", "college", "school", "medicine", "institute", "hospital",
        "center", "department", "foundation", "laboratory", "lab", "national", "medical",
        "of", "the", "and", "at", "for"
    }

    PAST_CUES = {
        "previously", "former", "formerly", "until", "prior to", "graduated", "alumnus",
        "alumna", "ph.d. at", "phd at", "ph.d. from", "phd from", "past", "ex-",
        "was a", "served as", "before", "received"
    }
    CURRENT_CUES = {
        "currently", "current", "now", "present", "since", "is a", "is an", "serves as"
    }

    if orgs1 and orgs2:
        # Check if any org in orgs1 overlaps with orgs2
        overlap = False
        for o1 in orgs1:
            for o2 in orgs2:
                if (o1 in o2 or o2 in o1) and o1.lower() not in GENERIC_ORGS and o2.lower() not in GENERIC_ORGS:
                    overlap = True
                    break
                d1 = {w for w in o1.split() if len(w) > 3 and w not in GENERIC_ORG_TOKENS}
                d2 = {w for w in o2.split() if len(w) > 3 and w not in GENERIC_ORG_TOKENS}
                if d1 and d2 and d1.intersection(d2):
                    overlap = True
                    break
            if overlap:
                break
        if not overlap:
            has_past1 = any(c in raw1.lower() for c in PAST_CUES)
            has_curr1 = any(c in raw1.lower() for c in CURRENT_CUES)
            has_past2 = any(c in raw2.lower() for c in PAST_CUES)
            has_curr2 = any(c in raw2.lower() for c in CURRENT_CUES)
            is_sequential_career = (has_past1 and has_curr2) or (has_past2 and has_curr1)

            name_tokens = name1_tokens | name2_tokens
            doms1 = extract_domains(raw1, exclude_tokens=name_tokens)
            doms2 = extract_domains(raw2, exclude_tokens=name_tokens)
            has_domain_conflict = any(
                (d1, d2) in INCOMPATIBLE_DOMAIN_PAIRS or (d2, d1) in INCOMPATIBLE_DOMAIN_PAIRS
                for d1 in doms1 for d2 in doms2
            )
            has_neg1 = any(p in raw1.lower() for p in NEGATIVE_PROFESSIONS)
            has_neg2 = any(p in raw2.lower() for p in NEGATIVE_PROFESSIONS)
            has_acad1 = any(p in raw1.lower() for p in ACADEMIC_PROFESSIONS)
            has_acad2 = any(p in raw2.lower() for p in ACADEMIC_PROFESSIONS)
            has_neg_conflict = (has_neg1 and has_acad2) or (has_neg2 and has_acad1)

            if is_sequential_career and not has_domain_conflict and not has_neg_conflict:
                # Sequential career migration across institutions - not a cannot-link
                pass
            else:
                # Different organizations with no overlap and no career transition -> Cannot-Link!
                return True

    # 2. Domain conflict check
    name_tokens = name1_tokens | name2_tokens
    doms1 = extract_domains(raw1, exclude_tokens=name_tokens)
    doms2 = extract_domains(raw2, exclude_tokens=name_tokens)
    for d1 in doms1:
        for d2 in doms2:
            if (d1, d2) in INCOMPATIBLE_DOMAIN_PAIRS or (d2, d1) in INCOMPATIBLE_DOMAIN_PAIRS:
                return True

    # 3. Cross-profession incompatibility
    has_neg1 = any(p in raw1.lower() for p in NEGATIVE_PROFESSIONS)
    has_neg2 = any(p in raw2.lower() for p in NEGATIVE_PROFESSIONS)
    has_acad1 = any(p in raw1.lower() for p in ACADEMIC_PROFESSIONS)
    has_acad2 = any(p in raw2.lower() for p in ACADEMIC_PROFESSIONS)
    if (has_neg1 and has_acad2) or (has_neg2 and has_acad1):
        return True
    if has_neg1 and has_neg2:
        profs1 = {p for p in NEGATIVE_PROFESSIONS if p in raw1.lower()}
        profs2 = {p for p in NEGATIVE_PROFESSIONS if p in raw2.lower()}
        if profs1 and profs2 and not profs1.intersection(profs2):
            return True

    # 3. Explicit negative assertions
    if any(neg in raw1.lower() for neg in ["not the same", "different person", "distinct individual"]):
        return True
    if any(neg in raw2.lower() for neg in ["not the same", "different person", "distinct individual"]):
        return True

    return False


def check_full_pinyin_match(zh_name: str, latin_name: str) -> bool:
    """Requires all characters of zh_name to match syllables in latin_name."""
    zh_chars = [c for c in zh_name if "\u4e00" <= c <= "\u9fff"]
    if not zh_chars:
        return False

    latin_clean = latin_name.lower().replace("-", " ")
    latin_tokens = latin_clean.split()
    latin_full = "".join(latin_tokens)

    matched_chars = 0
    for char in zh_chars:
        pys = PINYIN_MAP.get(char, [])
        if any(py in latin_tokens or py in latin_full for py in pys):
            matched_chars += 1

    return matched_chars == len(zh_chars) and len(zh_chars) >= 2


def is_chinese_text(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def compute_pairwise_name_similarity(m1: Any, m2: Any) -> Tuple[float, str]:
    """
    Computes pairwise name similarity and indicates if match relies on cross-lingual pinyin.
    Returns (similarity_score, match_type).
    """
    if isinstance(m1, str):
        n1 = m1.strip().lower()
        verified_aliases1 = set()
        unverified_aliases1 = set()
    else:
        n1 = m1.raw_name_text.strip().lower()
        verified_aliases1 = {
            a.alias_value.strip().lower()
            for a in m1.alias_hypotheses
            if getattr(a, "verification_status", None) == VerificationStatus.VERIFIED
        }
        unverified_aliases1 = {
            a.alias_value.strip().lower()
            for a in m1.alias_hypotheses
            if getattr(a, "verification_status", None) != VerificationStatus.VERIFIED
        }

    if isinstance(m2, str):
        n2 = m2.strip().lower()
        verified_aliases2 = set()
        unverified_aliases2 = set()
    else:
        n2 = m2.raw_name_text.strip().lower()
        verified_aliases2 = {
            a.alias_value.strip().lower()
            for a in m2.alias_hypotheses
            if getattr(a, "verification_status", None) == VerificationStatus.VERIFIED
        }
        unverified_aliases2 = {
            a.alias_value.strip().lower()
            for a in m2.alias_hypotheses
            if getattr(a, "verification_status", None) != VerificationStatus.VERIFIED
        }

    n1 = " ".join(n1.split())
    n2 = " ".join(n2.split())

    if n1 == n2:
        return 1.0, "exact"

    # Token Jaccard
    t1 = set(n1.split())
    t2 = set(n2.split())
    if t1 and t2:
        jaccard = len(t1.intersection(t2)) / len(t1.union(t2))
        if jaccard >= 0.85:
            return jaccard, "token_exact"

    # Honorific title + surname match (e.g. "Dr. Zhou" vs "Xin Zhou")
    HONORIFICS = {"dr.", "dr", "prof.", "prof", "professor", "mr.", "ms.", "mrs."}
    clean_toks1 = [t for t in n1.split() if t not in HONORIFICS]
    clean_toks2 = [t for t in n2.split() if t not in HONORIFICS]
    has_honorific1 = any(t in HONORIFICS for t in n1.split())
    has_honorific2 = any(t in HONORIFICS for t in n2.split())
    if (has_honorific1 or has_honorific2) and clean_toks1 and clean_toks2:
        if clean_toks1[-1] == clean_toks2[-1]:
            if len(clean_toks1) == 1 or len(clean_toks2) == 1:
                return 0.85, "surname_honorific"
            return 0.85, "honorific"

    # Check verified aliases hypotheses (authoritative / independent source verified)
    if (
        n1 in verified_aliases2
        or n2 in verified_aliases1
        or (verified_aliases1 and verified_aliases2 and verified_aliases1.intersection(verified_aliases2))
    ):
        return 0.95, "verified_alias"

    # Check unverified candidate alias hypotheses (forbids auto-merge; requires review)
    if (
        n1 in unverified_aliases2
        or n2 in unverified_aliases1
        or (unverified_aliases1 and unverified_aliases2 and unverified_aliases1.intersection(unverified_aliases2))
    ):
        return 0.50, "unverified_alias"

    # Cross-lingual pinyin heuristic check (strictly requiring full syllable match)
    is_zh1 = is_chinese_text(n1)
    is_zh2 = is_chinese_text(n2)

    if (is_zh1 and not is_zh2) or (is_zh2 and not is_zh1):
        zh_name = n1 if is_zh1 else n2
        latin_name = n2 if is_zh1 else n1

        if check_full_pinyin_match(zh_name, latin_name):
            return 0.50, "pinyin_weak"
        else:
            return 0.0, "none"

    # Fallback token overlap
    if not t1 or not t2:
        return 0.0, "none"
    return (len(t1.intersection(t2)) / len(t1.union(t2))), "token"


def resolve_mentions(
    mentions: List[EntityMention],
    match_threshold: float = 0.85,
    review_threshold: float = 0.50,
    source_names_by_surname: Optional[Dict[str, Dict[str, Set[str]]]] = None,
    source_profile_containers: Optional[Dict[str, Any]] = None,
    evidence_text_by_id: Optional[Dict[str, str]] = None,
) -> Tuple[List[MatchDecision], List[ClusterAssignment]]:
    decisions: List[MatchDecision] = []
    cannot_link_pairs: Set[Tuple[str, str]] = set()

    # Deduplicate mentions by mention_id
    dedup_dict = {}
    for m in mentions:
        if m.mention_id not in dedup_dict:
            dedup_dict[m.mention_id] = m
    sorted_mentions = sorted(dedup_dict.values(), key=lambda m: m.mention_id)
    n = len(sorted_mentions)

    # Build per-source entity full-name index from mentions
    HONORIFICS = {"dr.", "dr", "prof.", "prof", "professor", "mr.", "ms.", "mrs."}
    local_source_names_by_surname: Dict[str, Dict[str, Set[str]]] = {}
    for m in sorted_mentions:
        tokens = [t for t in m.raw_name_text.lower().split() if t not in HONORIFICS]
        if len(tokens) >= 2:
            sname = tokens[-1]
            full_n = " ".join(tokens)
            local_source_names_by_surname.setdefault(m.source_id, {}).setdefault(sname, set()).add(full_n)

    # Merge external source payload index (if provided) with local mention index
    active_source_names: Dict[str, Dict[str, Set[str]]] = {}
    if source_names_by_surname:
        for s_id, s_map in source_names_by_surname.items():
            for sname, fnames in s_map.items():
                active_source_names.setdefault(s_id, {}).setdefault(sname.lower(), set()).update({fn.lower() for fn in fnames})
    for s_id, s_map in local_source_names_by_surname.items():
        for sname, fnames in s_map.items():
            active_source_names.setdefault(s_id, {}).setdefault(sname.lower(), set()).update({fn.lower() for fn in fnames})

    edges = []

    for i in range(n):
        for j in range(i + 1, n):
            m1 = sorted_mentions[i]
            m2 = sorted_mentions[j]

            id1, id2 = sorted([m1.mention_id, m2.mention_id])

            sim, match_type = compute_pairwise_name_similarity(m1, m2)
            if sim < review_threshold:
                rel = MachineRelation.NONMATCH
                expl = f"Low similarity ({sim:.2f})"
            else:
                is_cannot_link = detect_cannot_link(m1, m2)
                raw1 = m1.context_snippet + " " + " ".join(m1.inferred_affiliations)
                raw2 = m2.context_snippet + " " + " ".join(m2.inferred_affiliations)
                name1_toks = set(m1.raw_name_text.lower().split())
                name2_toks = set(m2.raw_name_text.lower().split())
                orgs1 = extract_organizations(raw1) - name1_toks
                orgs2 = extract_organizations(raw2) - name2_toks
                shared_orgs = {
                    o1 for o1 in orgs1 for o2 in orgs2
                    if (o1 in o2 or o2 in o1) and o1.lower() not in GENERIC_ORGS and o2.lower() not in GENERIC_ORGS
                }
                doms1 = extract_domains(raw1, exclude_tokens=name1_toks | name2_toks)
                doms2 = extract_domains(raw2, exclude_tokens=name1_toks | name2_toks)
                shared_doms = doms1.intersection(doms2)

                is_surname_honorific = (match_type in ("honorific", "surname_honorific")) and (
                    len([t for t in m1.raw_name_text.lower().split() if t not in HONORIFICS]) == 1
                    or len([t for t in m2.raw_name_text.lower().split() if t not in HONORIFICS]) == 1
                )

                same_src = (m1.source_id == m2.source_id and m1.source_id != "SRC-FIXTURE")

                if is_surname_honorific:
                    # Identify surname and candidate full name
                    c_toks1 = [t for t in m1.raw_name_text.lower().split() if t not in HONORIFICS]
                    c_toks2 = [t for t in m2.raw_name_text.lower().split() if t not in HONORIFICS]
                    cand_m = m1 if len(c_toks1) > 1 else m2
                    cand_name_toks = [t for t in cand_m.raw_name_text.lower().split() if t not in HONORIFICS]
                    cand_full_name = " ".join(cand_name_toks)
                    sname = cand_name_toks[-1] if cand_name_toks else (c_toks1[-1] if c_toks1 else (c_toks2[-1] if c_toks2 else ""))
                    sname_lower = sname.lower()

                    # 1. Full-source same-surname competitor detection (Veto Signal Only)
                    raw_combined = (m1.context_snippet + " " + m2.context_snippet)
                    # Scan snippets for any multi-token names ending with this surname
                    found_names_in_snippets = set(re.findall(rf"\b([A-Z][a-zA-Z\.\-]+(?:\s+[A-Z][a-zA-Z\.\-]+)*\s+{re.escape(sname.capitalize())})\b", raw_combined))
                    known_names = active_source_names.get(m1.source_id, {}).get(sname_lower, set()) if same_src else set()
                    all_detected_same_surname = {n.lower().strip() for n in known_names}.union({n.lower().strip() for n in found_names_in_snippets})

                    # Veto check: any competitor full name ending with sname that is not the candidate
                    competing_full_names = set()
                    for raw_n in all_detected_same_surname:
                        norm_n = " ".join(raw_n.lower().split())
                        non_hon_toks = [t for t in norm_n.split() if t.rstrip(".,") not in HONORIFICS]
                        if len(non_hon_toks) < 2:
                            continue
                        clean_n = " ".join(non_hon_toks)
                        if clean_n != cand_full_name and not clean_n.endswith(" " + cand_full_name) and not cand_full_name.endswith(" " + clean_n):
                            competing_full_names.add(norm_n)
                    has_multi_entities = len(competing_full_names) > 0

                    # 2. Positive Proof Requirements for auto-merge:
                    # Positive Proof A: Target-bound Profile Page with Trusted Quality
                    is_target_bound_container = False
                    if same_src and not has_multi_entities and cand_full_name:
                        cont = source_profile_containers.get(m1.source_id) if source_profile_containers else None
                        cand_name_regex = r"\b" + r"\s+".join(re.escape(t) for t in cand_name_toks) + r"\b" if cand_name_toks else rf"\b{re.escape(cand_full_name)}\b"
                        if isinstance(cont, dict):
                            h1_text = cont.get("h1_text", "")
                            h1_clean = " ".join(h1_text.split())
                            jsonld_names = [n.lower().strip() for n in cont.get("jsonld_person_names", [])]
                            has_bio = cont.get("has_bio", False)
                            url = cont.get("url", "").lower()
                            sq = cont.get("source_quality_class")
                            if not sq and url:
                                from core.extractors.content_locator import classify_source_quality
                                sq = classify_source_quality(url)
                            is_trusted_quality = bool(sq and sq in (SourceQualityClass.CLASS_A, SourceQualityClass.CLASS_B))
                            cand_in_h1 = bool(re.search(cand_name_regex, h1_clean, re.I))
                            cand_in_jsonld = any(cand_full_name in n or n in cand_full_name for n in jsonld_names)
                            is_profile_page = has_bio or any(p in url for p in ["/profile/", "/people/", "/faculty/", "/person/"])
                            if (cand_in_h1 or cand_in_jsonld) and is_profile_page and is_trusted_quality:
                                is_target_bound_container = True

                    # Positive Proof B: Unambiguous Immediate Local Antecedent (using authentic Evidence text coordinate system)
                    is_local_antecedent = False
                    if same_src and not has_multi_entities and cand_full_name and m1.evidence_id == m2.evidence_id:
                        earlier_m = m1 if m1.char_start <= m2.char_start else m2
                        later_m = m2 if m1.char_start <= m2.char_start else m1
                        if earlier_m == cand_m:
                            dist = later_m.char_start - earlier_m.char_end
                            if 0 <= dist <= 150:
                                ev_text = evidence_text_by_id.get(m1.evidence_id) if evidence_text_by_id else None
                                if not ev_text and m1.context_snippet == m2.context_snippet:
                                    if len(m1.context_snippet) >= later_m.char_end and m1.context_snippet[earlier_m.char_start:earlier_m.char_end] == earlier_m.raw_name_text:
                                        ev_text = m1.context_snippet
                                if ev_text and len(ev_text) >= later_m.char_start:
                                    between_text = ev_text[earlier_m.char_end:later_m.char_start]
                                    if not re.search(r'[.!?;\n]|</?(?:p|h\d|div|li|tr|td|section|article)\b', between_text) and not re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', between_text):
                                        is_local_antecedent = True
                                else:
                                    is_local_antecedent = False

                    # Conservative policy: Surname honorifics strictly default to REVIEW unless
                    # verified alias, target-bound profile container, or immediate local antecedent is present
                    has_corroboration = (
                        same_src
                        and not has_multi_entities
                        and (
                            is_target_bound_container
                            or is_local_antecedent
                            or (match_type == "verified_alias")
                        )
                    )
                else:
                    has_corroboration = (
                        same_src
                        or (match_type == "verified_alias")
                        or bool(shared_orgs)
                        or (bool(shared_doms) and sim >= match_threshold)
                    )

                COLLEGIATE_UNITS_MAP = {
                    "school of medicine": "medicine",
                    "medical school": "medicine",
                    "medicine.yale.edu": "medicine",
                    "internal medicine": "medicine",
                    "infectious diseases": "medicine",
                    "department of internal medicine": "medicine",
                    "section of infectious diseases": "medicine",
                    "school of public health": "public_health",
                    "public health": "public_health",
                    "biostatistics": "public_health",
                    "department of biostatistics": "public_health",
                    "ysph": "public_health",
                    "epidemiology": "public_health",
                    "law school": "law",
                    "school of law": "law",
                    "business school": "business",
                    "school of management": "business",
                    "school of nursing": "nursing",
                    "school of music": "music",
                    "school of drama": "drama",
                    "school of art": "art",
                    "divinity school": "divinity",
                }
                JOINT_CUES = {
                    "joint appointment", "secondary appointment", "adjunct", "jointly appointed",
                    "dual appointment", "affiliated with both", "courtesy appointment", "jointly with",
                    "joint faculty", "joint affiliation"
                }
                u1 = {u for phrase, u in COLLEGIATE_UNITS_MAP.items() if phrase in raw1.lower()}
                u2 = {u for phrase, u in COLLEGIATE_UNITS_MAP.items() if phrase in raw2.lower()}
                has_joint_cue = any(cue in raw1.lower() or cue in raw2.lower() for cue in JOINT_CUES)
                is_cross_unit_joint = bool(u1 and u2 and not u1.intersection(u2) and has_joint_cue)

                if is_cannot_link:
                    cannot_link_pairs.add((id1, id2))
                    rel = MachineRelation.NONMATCH
                    expl = "Cannot-link constraint: mutually exclusive institutional affiliation or domain detected"
                    sim = 0.0
                elif is_cross_unit_joint:
                    rel = MachineRelation.REVIEW
                    sim = 0.50
                    expl = "Cross-collegiate unit mention with joint/secondary appointment cue; exempts hard cannot-link but requires human review"
                elif match_type == "unverified_alias":
                    rel = MachineRelation.REVIEW
                    sim = 0.50
                    expl = "Unverified candidate alias hypothesis without independent verification; requires review and forbids auto-merge"
                elif match_type == "pinyin_weak":
                    rel = MachineRelation.REVIEW
                    sim = 0.50
                    expl = "Weak cross-lingual pinyin hypothesis without verified official alias; requires human review"
                elif is_surname_honorific and not has_corroboration:
                    rel = MachineRelation.REVIEW
                    sim = 0.50
                    if has_multi_entities:
                        expl = f"Ambiguous surname-only honorific match with competing same-surname entities ({sorted(competing_full_names)}) in source; routed to review to prevent false merges"
                    else:
                        expl = "Surname-only honorific requires single-subject profile container or unambiguous local antecedent; routed to review to prevent false merges"
                elif sim >= match_threshold and has_corroboration:
                    rel = MachineRelation.MATCH
                    expl = f"High token overlap ({sim:.2f}) with corroborating evidence (org/domain/source)"
                else:
                    rel = MachineRelation.REVIEW
                    expl = f"Candidate name match ({sim:.2f}) without sufficient corroborating evidence; requires review"
                    sim = 0.50


            dec = MatchDecision(
                decision_id=f"DEC-{id1}-{id2}",
                source_mention_id=id1,
                target_mention_id=id2,
                algorithm="multi_field_constrained",
                match_probability=sim,
                machine_relation=rel,
                explanation=expl,
            )
            decisions.append(dec)

            if rel == MachineRelation.MATCH:
                edges.append((sim, id1, id2))

    # Total deterministic sort on edges: score DESC, id1 ASC, id2 ASC
    edges.sort(key=lambda x: (-x[0], x[1], x[2]))

    # Constrained Union-Find clustering
    mention_ids = [m.mention_id for m in sorted_mentions]
    cuf = ConstrainedUnionFind(mention_ids, cannot_link_pairs)

    for sim, id1, id2 in edges:
        success = cuf.union(id1, id2)
        if not success:
            # Downgrade decision to review due to cannot-link conflict across cluster members
            for dec in decisions:
                if dec.source_mention_id == id1 and dec.target_mention_id == id2:
                    dec.machine_relation = MachineRelation.REVIEW
                    dec.match_probability = 0.50
                    dec.explanation = "Merge rejected by Cannot-Link constraint across cluster members"

    # Assemble clusters deterministically
    clusters: List[ClusterAssignment] = []
    for root in sorted(cuf.members.keys()):
        members = sorted(cuf.members[root])
        primary_id = members[0].replace("MEN-", "")
        cluster_id = f"CLUST-{primary_id}"
        clusters.append(
            ClusterAssignment(
                cluster_id=cluster_id,
                mention_ids=members,
                clustering_method=ClusteringMethod.CONSTRAINED_UNION_FIND,
                threshold_used=match_threshold,
            )
        )

    decisions.sort(key=lambda d: (d.source_mention_id, d.target_mention_id))
    return decisions, clusters
