"""
Structural, Relational, and Referential Validator (V4.4.1 Strict Fail-Closed).
Enforces:
1. Pydantic instantiation and uniqueness for all 9 bundle files + dossier.md.
2. CandidateEntity mention set equivalence: set(cand.mention_ids) == set(cluster.mention_ids).
3. Strict Claim subject anchor closure: claim.subject_mention_id in cand.mention_ids.
4. Dossier statement purity: claims[c_id].candidate_entity_id == dossier.candidate_entity_id.
5. Evidence authenticity & payload tamper-detection.
6. Ambiguous identity consistency.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError
from models.schemas import (
    AdjudicationStatus,
    CandidateEntity,
    Claim,
    ClusterAssignment,
    Dossier,
    EntityMention,
    Evidence,
    MachineRelation,
    MatchDecision,
    RunManifest,
    SourceSnapshot,
    PREDICATE_ALLOWLIST,
    RELATION_REQUIRED_PREDICATES,
)
from models.entity_registry import (
    CANONICAL_OBJECT_REGISTRY,
    OBJECT_ALIASES,
    lookup_registry_object,
)

REQUIRED_FILES = [
    "sources.jsonl",
    "evidence.jsonl",
    "mentions.jsonl",
    "candidates.jsonl",
    "matches.jsonl",
    "clusters.jsonl",
    "claims.jsonl",
    "dossier.json",
    "manifest.json",
]

GENERIC_OBJECT_CATEGORY_WORDS = {
    # Organizations
    "university", "college", "school", "institute", "institution", "hospital",
    "center", "centre", "department", "division", "section", "program", "programme",
    "laboratory", "lab", "labs", "foundation", "association", "society", "council",
    "committee", "agency", "firm", "company", "group", "corporation", "corp", "inc", "ltd", "llc",
    # Roles / Titles
    "professor", "prof", "assistant", "associate", "full", "adjunct", "clinical",
    "visiting", "executive", "distinguished", "senior", "junior", "principal", "lead",
    "chief", "staff", "postdoc", "postdoctoral", "fellow", "researcher", "scientist",
    "engineer", "dean", "director", "chair", "president", "vice", "chancellor", "head",
    "officer", "member", "doctor", "dr", "realtor", "agent", "scholar",
    # Stopwords & Connectives
    "the", "of", "at", "in", "for", "on", "and", "to", "from", "with", "by", "a", "an",
}

ZH_GENERIC_WORDS = [
    "大学", "学院", "研究所", "研究院", "医院", "中心", "系", "部", "所", "实验室", "公司", "集团", "协会", "学会", "委员会",
    "教授", "副教授", "助理教授", "研究员", "副研究员", "博士后", "院长", "副院长", "主任", "副主任", "科学家", "首席科学家",
    "工程师", "会长", "校长", "医师", "队长", "队员", "顾问", "总监", "经理", "成员",
]

ACADEMIC_CATEGORIES = {"university", "college", "school", "academy", "univ"}
HEALTH_CATEGORIES = {"hospital", "clinic", "infirmary", "health", "medicine", "medical"}
RESEARCH_CATEGORIES = {"institute", "institution", "laboratory", "lab", "center"}
COMPANY_CATEGORIES = {"company", "corporation", "corp", "inc", "ltd", "firm", "group"}
DEPT_CATEGORIES = {"department", "dept", "division", "section"}

CATEGORY_MAP = {}
for cat, words in [
    ("academic", ACADEMIC_CATEGORIES),
    ("health", HEALTH_CATEGORIES),
    ("research", RESEARCH_CATEGORIES),
    ("company", COMPANY_CATEGORIES),
    ("dept", DEPT_CATEGORIES),
]:
    for w in words:
        CATEGORY_MAP[w] = cat

CATEGORY_MAP_ZH = {}
for cat, words in [
    ("academic", {"大学", "学院", "一零一中", "中学", "小学"}),
    ("health", {"医院", "门诊", "诊所"}),
    ("research", {"研究所", "研究院", "实验室", "中心"}),
    ("company", {"公司", "集团", "企业"}),
    ("dept", {"系", "部", "室"}),
]:
    for w in words:
        CATEGORY_MAP_ZH[w] = cat

STOPWORDS = {
    "the", "of", "at", "in", "for", "on", "and", "to", "from", "with", "by", "a", "an"
}


def normalize_object(raw_obj: str) -> Tuple[str, str, Optional[str]]:
    """
    Normalizes an object string into canonical name, canonical entity ID, and semantic category.
    """
    rec = lookup_registry_object(raw_obj)
    if rec:
        return rec["canonical_name"], rec["canonical_id"], rec["category"]
    clean = raw_obj.strip()
    can_id = f"OBJ-{hashlib.sha256(clean.lower().encode('utf-8')).hexdigest()[:12]}"
    cat = None
    is_zh = any("\u4e00" <= ch <= "\u9fff" for ch in clean)
    if is_zh:
        for w, c in CATEGORY_MAP_ZH.items():
            if w in clean:
                cat = c
                break
    else:
        for tok in re.split(r"[\s/]+", clean.lower()):
            norm = re.sub(r"^[^\w.]+|[^\w.]+$", "", tok)
            if norm in CATEGORY_MAP:
                cat = CATEGORY_MAP[norm]
                break
    return clean, can_id, cat


def resolve_object_aliases(raw_obj: str) -> List[Dict[str, Any]]:
    """
    Resolves an object string into search surface candidate specs along with canonical ID,
    semantic category, match_mode, min_length, blocked_compounds, and required_contexts.
    """
    rec = lookup_registry_object(raw_obj)
    if rec:
        results = []
        for a in rec["aliases"]:
            results.append({
                "surface": a["surface"],
                "canonical_id": rec["canonical_id"],
                "category": a.get("category") or rec.get("category"),
                "match_mode": a.get("match_mode", "canonical"),
                "min_length": a.get("min_length", len(a["surface"])),
                "authorized_subunits": rec.get("authorized_subunits", []),
            })
        return results
    norm_name, can_id, cat = normalize_object(raw_obj)
    return [{
        "surface": norm_name,
        "canonical_id": can_id,
        "category": cat,
        "match_mode": "canonical",
        "min_length": len(norm_name),
        "authorized_subunits": [],
    }]


def split_sentences(text: str) -> List[Tuple[int, int, str]]:
    """
    Splits text into sentences/clauses using punctuation boundaries while protecting
    standard abbreviations (Ph.D., M.D., Dr., Prof., etc.).
    """
    delimiters = (
        r"(?<!\b[A-Za-z])(?<!\bDr)(?<!\bProf)(?<!\bMr)(?<!\bMs)(?<!\bPh)(?<!\bPh\.D)(?<!\bM\.D)[.!?;\n。！？；]+"
    )
    results = []
    last_end = 0
    for match in re.finditer(delimiters, text):
        clause = text[last_end:match.start()].strip()
        if clause:
            results.append((last_end, match.start(), text[last_end:match.start()]))
        last_end = match.end()
    trailing = text[last_end:].strip()
    if trailing:
        results.append((last_end, len(text), text[last_end:]))
    return results


def tokenize_with_abbreviations(text: str) -> List[Tuple[str, int, int]]:
    """
    Tokenizes text while treating recognized abbreviations (e.g. Ph.D., M.D., U.S.) as single tokens.
    Returns list of (token_str, start_char, end_char).
    """
    abbrev_pat = r"\b[A-Za-z]\.(?:[A-Za-z]\.)+"
    word_pat = r"\b[A-Za-z0-9]+(?:'[a-z]+)?\b"
    token_pat = rf"({abbrev_pat}|{word_pat})"
    tokens = []
    for m in re.finditer(token_pat, text, re.IGNORECASE):
        tokens.append((m.group(1), m.start(), m.end()))
    return tokens


def find_object_in_text(raw_obj: str, text: str) -> Optional[Tuple[int, int, str, Optional[str]]]:
    """
    Locates raw_obj or its registered aliases in text.
    Enforces:
    - English: Strictly within a single sentence (period cannot connect tokens across sentences),
      utilizing tokenize_with_abbreviations for atomic tokens and abbreviation protection.
    - Chinese: Strictly as a contiguous entity phrase or explicit alias (no scattered subtoken stitching).
      Short aliases (e.g. '北大') must strictly respect word boundaries, blocked compounds (e.g. '北大荒'),
      and require verified educational/employment context or academic subunits.
    - Category compatibility: Rejects matches immediately followed by conflicting institutional head words
      (e.g. academic entity followed by hospital).
    Returns (start_char, end_char, canonical_id, category) if found, else None.
    """
    raw_obj_clean = raw_obj.strip()
    if not raw_obj_clean or not text:
        return None
    candidates = resolve_object_aliases(raw_obj_clean)
    is_zh_obj = any("\u4e00" <= ch <= "\u9fff" for ch in raw_obj_clean)

    if is_zh_obj:
        academic_subunits = [
            "生科院", "微电子", "光华", "医学部", "法学院", "数学系", "物理学院", "化学学院",
            "计算机系", "信科", "中文系", "哲学系", "历史学系", "外语学院", "经济学院",
            "工学院", "软件学院", "环境学院", "社会学系", "新闻传播学院", "系", "学院", "所", "实验室",
        ]
        for spec in candidates:
            cand_clean = spec["surface"].strip()
            can_id = spec["canonical_id"]
            cat = spec["category"]
            match_mode = spec["match_mode"]
            auth_subunits = spec.get("authorized_subunits", [])

            idx = 0
            while True:
                pos = text.find(cand_clean, idx)
                if pos == -1:
                    break
                m_start = pos
                m_end = pos + len(cand_clean)

                # 1. Chinese short alias: Relation Local Object Span and Strict Boundary Check
                if match_mode == "short_alias":
                    # Preceding character check: cannot be attached to a preceding Han character unless an allowed relational preposition
                    if m_start > 0:
                        prev_char = text[m_start - 1]
                        if "\u4e00" <= prev_char <= "\u9fff":
                            allowed_prev_chars = set("于在为是到入访任聘属及和与同兼从")
                            if prev_char not in allowed_prev_chars:
                                idx = m_end
                                continue

                    # Trailing character check: cannot be attached to unauthorized compounds
                    trailing_text = text[m_end:]
                    academic_roles_pat = r"^(?:(?:终身|讲席|特聘|长聘|助理|副)?(?:教授|研究员|讲师|学者|校长|院长|系主任|院士|教师)|(?:获|获得|攻读|取得|修读)?(?:博士后|博士|硕士|学士|研究生|本科生|学生|校友|学位)|(?:团队|课题组))"
                    particles_pat = r"^(?:的|期间|时)"

                    matched_auth_sub = None
                    if trailing_text and "\u4e00" <= trailing_text[0] <= "\u9fff":
                        for sub in auth_subunits:
                            if trailing_text.startswith(sub):
                                matched_auth_sub = sub
                                break

                        if matched_auth_sub:
                            after_sub = trailing_text[len(matched_auth_sub):]
                            if after_sub and "\u4e00" <= after_sub[0] <= "\u9fff":
                                if not (re.match(academic_roles_pat, after_sub) or re.match(particles_pat, after_sub)):
                                    idx = m_end
                                    continue
                        elif re.match(academic_roles_pat, trailing_text) or re.match(particles_pat, trailing_text):
                            pass
                        else:
                            # Any unregistered compound word (e.g. 公学, 博雅, 青鸟, 方正, 资源, 科技, 荒...) FAIL-CLOSED!
                            idx = m_end
                            continue

                    # Local preceding context within the same clause
                    punct_chars = "。！？；\n，,"
                    prev_splits = [text.rfind(p, 0, m_start) for p in punct_chars if text.rfind(p, 0, m_start) != -1]
                    clause_start = max(prev_splits) + 1 if prev_splits else 0
                    preceding_clause_slice = text[clause_start:m_start].strip()

                    rel_trigger_pat = r"(?:毕业于|就读于|求学于|就读|毕业|考入|求学|在|任职于|任教于|执教于|受聘于|就职于|加盟|进入|来自|现为|曾为|担任|现任|曾任|是|为)\s*$"
                    has_rel_prefix = bool(re.search(rel_trigger_pat, preceding_clause_slice))
                    trailing_has_role = bool(re.match(academic_roles_pat, trailing_text))
                    trailing_has_auth_sub = bool(matched_auth_sub is not None)

                    if not (has_rel_prefix or trailing_has_role or trailing_has_auth_sub):
                        idx = m_end
                        continue

                # 3. Category conflict check
                trailing = text[m_end : m_end + 15]
                trail_punct = re.split(r"[。！？；，,\n]", trailing)[0]
                conflict = False
                if cat == "academic":
                    if any(hw in trail_punct for hw in ["医院", "门诊", "诊所"]):
                        conflict = True
                elif cat == "health":
                    if any(aw in trail_punct for aw in ["大学", "学院"]):
                        conflict = True
                if not conflict:
                    return (m_start, m_end, can_id, cat)
                idx = m_end
        return None
    else:
        sentences = split_sentences(text)
        for s_start, s_end, sent_text in sentences:
            sent_lower = sent_text.lower()
            sent_tokens = tokenize_with_abbreviations(sent_text)

            for spec in candidates:
                cand_surface = spec["surface"]
                can_id = spec["canonical_id"]
                cat = spec["category"]
                cand_lower = cand_surface.lower().strip()
                clean_tokens = [tok for tok in re.split(r"[\s/]+", cand_lower) if tok]
                if not clean_tokens:
                    continue
                substantive = [
                    re.sub(r"^[^\w.]+|[^\w.]+$", "", tok)
                    for tok in clean_tokens
                    if re.sub(r"^[^\w.]+|[^\w.]+$", "", tok) not in STOPWORDS
                ]
                substantive = [tok for tok in substantive if tok]
                if not substantive:
                    substantive = [re.sub(r"^[^\w.]+|[^\w.]+$", "", tok) for tok in clean_tokens if tok]
                    substantive = [tok for tok in substantive if tok]

                ROLE_WORDS = {"resident", "fellow", "professor", "scientist", "director", "dean", "chair", "student", "doctor", "physician", "intern", "engineer", "researcher", "scholar", "clerk", "member"}
                def _is_conflict(match_end_rel: int) -> bool:
                    if not cat or any(rw in raw_obj.lower() for rw in ROLE_WORDS):
                        return False
                    after_text = sent_lower[match_end_rel : match_end_rel + 35]
                    punct_split = re.split(r"[.;:!?\n]", after_text)
                    after_entity = punct_split[0] if punct_split else ""
                    trailing_words = [
                        re.sub(r"^[^\w]+|[^\w]+$", "", tok)
                        for tok in re.split(r"[\s-]+", after_entity)
                        if re.sub(r"^[^\w]+|[^\w]+$", "", tok) and re.sub(r"^[^\w]+|[^\w]+$", "", tok) not in STOPWORDS
                    ]
                    trailing_cats = set(CATEGORY_MAP[w] for w in trailing_words if w in CATEGORY_MAP)
                    if cat == "academic" and "health" in trailing_cats:
                        return True
                    if cat == "health" and "academic" in trailing_cats and "health" not in trailing_cats:
                        return True
                    return False

                if len(substantive) >= 2:
                    # Contiguous noun phrase match strictly within same sentence
                    # sep_pat prohibits periods
                    sep_pat = r"[\s,&-]+(?:(?:the|of|at|in|for|on|and|&|to|from|with|by|a|an)\b[\s,&-]*)*"
                    phrase_tokens = [re.escape(tok) for tok in substantive]
                    if substantive[-1] in ROLE_WORDS:
                        phrase_tokens[-1] = rf"{re.escape(substantive[-1])}s?"
                    phrase_pat = sep_pat.join(phrase_tokens)
                    for m in re.finditer(rf"(?<!\w){phrase_pat}(?!\w)", sent_lower):
                        if not _is_conflict(m.end()):
                            return (s_start + m.start(), s_start + m.end(), can_id, cat)
                elif len(substantive) == 1:
                    tok = substantive[0]
                    if not tok:
                        continue
                    # Check against atomic tokens from tokenize_with_abbreviations
                    found_tok = False
                    for tok_str, t_start, t_end in sent_tokens:
                        role_forms = {tok.lower()}
                        if tok.lower() in ROLE_WORDS:
                            role_forms.add(f"{tok.lower()}s")
                        if tok_str.lower() == cand_lower or tok_str.lower() in role_forms:
                            if not _is_conflict(t_end):
                                return (s_start + t_start, s_start + t_end, can_id, cat)
                    # Fallback to word-boundary regex if token split differed
                    tok_esc = re.escape(tok)
                    pat = rf"(?<!\w){tok_esc}" if tok.endswith(".") else rf"(?<!\w){tok_esc}(?!\w)"
                    for m in re.finditer(pat, sent_lower):
                        if not _is_conflict(m.end()):
                            return (s_start + m.start(), s_start + m.end(), can_id, cat)
        return None


def check_object_presence(raw_obj: str, text: str) -> bool:
    """
    Checks if raw_obj or an alias is validly and contiguously present in text.
    """
    return find_object_in_text(raw_obj, text) is not None


def validate_bundle(bundle_dir: Path, warc_path: Optional[Path] = None) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Strict existence of all 9 files + dossier.md
    for fname in REQUIRED_FILES:
        p = bundle_dir / fname
        if not p.exists():
            errors.append(f"Missing required bundle file: {fname}")

    dossier_md_path = bundle_dir / "dossier.md"
    if not dossier_md_path.exists():
        errors.append("Missing required bundle file: dossier.md")

    if errors:
        return {"is_valid": False, "errors": errors, "warnings": warnings}

    # 2. Pydantic instantiation and uniqueness checks
    manifest_obj = None
    try:
        with open(bundle_dir / "manifest.json", "r", encoding="utf-8") as f:
            manifest_raw = json.load(f)
        manifest_obj = RunManifest(**manifest_raw)
    except Exception as e:
        errors.append(f"manifest.json schema validation error: {e}")

    # Load and validate Sources
    sources: Dict[str, SourceSnapshot] = {}
    with open(bundle_dir / "sources.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                s = SourceSnapshot(**raw)
                if s.source_id in sources:
                    errors.append(f"sources.jsonl: Duplicate source_id '{s.source_id}' at line {line_no}")
                sources[s.source_id] = s
                if not re.match(r"^[a-f0-9]{64}$", s.content_sha256):
                    errors.append(f"sources.jsonl: Source {s.source_id} content_sha256 is not 64-char hex")
                if s.content_sha256 == "0" * 64:
                    errors.append(f"sources.jsonl: Source {s.source_id} uses fake all-zero content_sha256")
            except Exception as e:
                errors.append(f"sources.jsonl: line {line_no} validation error: {e}")

    # Load and validate Evidence
    evidence: Dict[str, Evidence] = {}
    with open(bundle_dir / "evidence.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                ev = Evidence(**raw)
                if ev.evidence_id in evidence:
                    errors.append(f"evidence.jsonl: Duplicate evidence_id '{ev.evidence_id}' at line {line_no}")
                evidence[ev.evidence_id] = ev
                if ev.source_id not in sources:
                    errors.append(f"evidence.jsonl: Evidence {ev.evidence_id} references non-existent source_id '{ev.source_id}'")

                # Payload authenticity verification
                if ev.raw_payload_sha256 == "0" * 64:
                    errors.append(f"evidence.jsonl: Evidence {ev.evidence_id} uses fake all-zero raw_payload_sha256")
                elif ev.raw_payload_sha256 and ev.source_id in sources:
                    src = sources[ev.source_id]
                    if ev.raw_payload_sha256 != src.content_sha256:
                        errors.append(
                            f"evidence.jsonl: Evidence {ev.evidence_id} payload sha256 ({ev.raw_payload_sha256}) "
                            f"mismatches source {src.source_id} content_sha256 ({src.content_sha256})"
                        )
            except Exception as e:
                errors.append(f"evidence.jsonl: line {line_no} validation error: {e}")

    # Load and validate Mentions
    mentions: Dict[str, EntityMention] = {}
    with open(bundle_dir / "mentions.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                m = EntityMention(**raw)
                if m.mention_id in mentions:
                    errors.append(f"mentions.jsonl: Duplicate mention_id '{m.mention_id}' at line {line_no}")
                mentions[m.mention_id] = m
                if m.source_id not in sources:
                    errors.append(f"mentions.jsonl: Mention {m.mention_id} references non-existent source_id '{m.source_id}'")
                if not m.evidence_id:
                    errors.append(f"mentions.jsonl: Mention {m.mention_id} has empty evidence_id")
                elif m.evidence_id not in evidence:
                    errors.append(f"mentions.jsonl: Mention {m.mention_id} references non-existent evidence_id '{m.evidence_id}'")
                else:
                    ev = evidence[m.evidence_id]
                    # Enforce strict mention_key recomputation
                    expected_key = hashlib.sha256(
                        f"{m.source_id}:{m.char_start}:{m.char_end}".encode("utf-8")
                    ).hexdigest()[:16]
                    if m.mention_key != expected_key:
                        errors.append(
                            f"mentions.jsonl: Mention {m.mention_id} mention_key '{m.mention_key}' "
                            f"does not match recomputed key '{expected_key}'"
                        )
                    # Enforce text slice verification
                    if m.char_start < 0 or m.char_end > len(ev.verbatim_excerpt):
                        errors.append(
                            f"mentions.jsonl: Mention {m.mention_id} span [{m.char_start}:{m.char_end}] "
                            f"out of range for evidence {ev.evidence_id} (length {len(ev.verbatim_excerpt)})"
                        )
                    else:
                        sliced_name = ev.verbatim_excerpt[m.char_start:m.char_end]
                        if m.raw_name_text != sliced_name:
                            errors.append(
                                f"mentions.jsonl: Mention {m.mention_id} raw_name_text '{m.raw_name_text}' "
                                f"does not match excerpt slice '{sliced_name}' at [{m.char_start}:{m.char_end}]"
                            )
                    if m.raw_name_text not in m.context_snippet:
                        errors.append(
                            f"mentions.jsonl: Mention {m.mention_id} raw_name_text '{m.raw_name_text}' "
                            f"not found in context_snippet"
                        )
                    if m.context_snippet not in ev.verbatim_excerpt:
                        errors.append(
                            f"mentions.jsonl: Mention {m.mention_id} context_snippet is not a substring of evidence {ev.evidence_id}"
                        )
            except Exception as e:
                errors.append(f"mentions.jsonl: Parse error at line {line_no}: {str(e)}")

    # Load and validate Clusters
    clusters: Dict[str, ClusterAssignment] = {}
    partition_mentions: Set[str] = set()
    with open(bundle_dir / "clusters.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                cl = ClusterAssignment(**raw)
                if cl.cluster_id in clusters:
                    errors.append(f"clusters.jsonl: Duplicate cluster_id '{cl.cluster_id}' at line {line_no}")
                clusters[cl.cluster_id] = cl
                for m_id in cl.mention_ids:
                    if m_id not in mentions:
                        errors.append(f"clusters.jsonl: Cluster {cl.cluster_id} references non-existent mention_id '{m_id}'")
                    if m_id in partition_mentions:
                        errors.append(f"clusters.jsonl: Partition violation! Mention '{m_id}' appears in multiple clusters")
                    partition_mentions.add(m_id)
            except Exception as e:
                errors.append(f"clusters.jsonl: line {line_no} validation error: {e}")

    if mentions and partition_mentions != set(mentions.keys()):
        missing = set(mentions.keys()) - partition_mentions
        errors.append(f"clusters.jsonl: Partition completeness error: mentions not assigned to any cluster: {missing}")

    # Load and validate Candidates
    candidates: Dict[str, CandidateEntity] = {}
    with open(bundle_dir / "candidates.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                cand = CandidateEntity(**raw)
                if cand.candidate_entity_id in candidates:
                    errors.append(f"candidates.jsonl: Duplicate candidate_entity_id '{cand.candidate_entity_id}' at line {line_no}")
                candidates[cand.candidate_entity_id] = cand
                if cand.human_confirmed_entity_id is not None:
                    errors.append(f"candidates.jsonl: Candidate {cand.candidate_entity_id} machine record has human_confirmed_entity_id set!")
                if cand.proposed_cluster_id not in clusters:
                    errors.append(f"candidates.jsonl: Candidate {cand.candidate_entity_id} references non-existent cluster '{cand.proposed_cluster_id}'")
                else:
                    # MANDATORY EQUIVALENCE: cand.mention_ids == cluster.mention_ids
                    cl_m_set = set(clusters[cand.proposed_cluster_id].mention_ids)
                    cd_m_set = set(cand.mention_ids)
                    if cd_m_set != cl_m_set:
                        errors.append(
                            f"candidates.jsonl: Candidate {cand.candidate_entity_id} mention_ids {cd_m_set} "
                            f"does not match cluster {cand.proposed_cluster_id} mention_ids {cl_m_set}"
                        )
            except Exception as e:
                errors.append(f"candidates.jsonl: line {line_no} validation error: {e}")

    # Load and validate Matches
    decisions_seen: Set[str] = set()
    review_edges_count = 0
    with open(bundle_dir / "matches.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                match = MatchDecision(**raw)
                if match.machine_relation == MachineRelation.REVIEW:
                    review_edges_count += 1
                if match.decision_id in decisions_seen:
                    errors.append(f"matches.jsonl: Duplicate decision_id '{match.decision_id}' at line {line_no}")
                decisions_seen.add(match.decision_id)
                if match.source_mention_id == match.target_mention_id:
                    errors.append(f"matches.jsonl: Self-match violation! source == target '{match.source_mention_id}'")
                if match.source_mention_id not in mentions:
                    errors.append(f"matches.jsonl: source_mention_id '{match.source_mention_id}' not in mentions")
                if match.target_mention_id not in mentions:
                    errors.append(f"matches.jsonl: target_mention_id '{match.target_mention_id}' not in mentions")
            except Exception as e:
                errors.append(f"matches.jsonl: line {line_no} validation error: {e}")

    # Load and validate Claims
    claims: Dict[str, Claim] = {}
    unadjudicated_claims_count = 0
    clause_level_claims_count = 0
    with open(bundle_dir / "claims.jsonl", "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                c = Claim(**raw)
                if c.adjudication_status == AdjudicationStatus.UNRESOLVED:
                    unadjudicated_claims_count += 1
                if c.claim_id in claims:
                    errors.append(f"claims.jsonl: Duplicate claim_id '{c.claim_id}' at line {line_no}")
                claims[c.claim_id] = c
                if c.predicate not in PREDICATE_ALLOWLIST:
                    errors.append(f"claims.jsonl: Claim {c.claim_id} uses illegal predicate '{c.predicate}'")
                if c.candidate_entity_id not in candidates:
                    errors.append(f"claims.jsonl: Claim {c.claim_id} references non-existent candidate '{c.candidate_entity_id}'")
                if not c.evidence_ids:
                    errors.append(f"claims.jsonl: Claim {c.claim_id} has empty evidence_ids")
                for e_id in c.evidence_ids:
                    if e_id not in evidence:
                        errors.append(f"claims.jsonl: Claim {c.claim_id} references non-existent evidence '{e_id}'")

                # MANDATORY SUBJECT ANCHOR CLOSURE:
                # claim.subject_mention_id must exist in mentions
                if c.subject_mention_id not in mentions:
                    errors.append(f"claims.jsonl: Claim {c.claim_id} subject_mention_id '{c.subject_mention_id}' not in mentions")
                elif c.candidate_entity_id in candidates:
                    cand = candidates[c.candidate_entity_id]
                    if c.subject_mention_id not in cand.mention_ids:
                        errors.append(
                            f"claims.jsonl: Cross-candidate claim contamination! Claim {c.claim_id} subject mention "
                            f"'{c.subject_mention_id}' does not belong to candidate '{c.candidate_entity_id}' "
                            f"(mention_ids: {cand.mention_ids})"
                        )
                # MANDATORY SUPPORT CLAUSES VALIDATION:
                if not c.support_clauses:
                    errors.append(f"claims.jsonl: Claim {c.claim_id} has empty support_clauses")
                for sup in c.support_clauses:
                    if sup.evidence_id not in evidence:
                        errors.append(f"claims.jsonl: Claim {c.claim_id} support_clause references non-existent evidence '{sup.evidence_id}'")
                    else:
                        ev_excerpt = evidence[sup.evidence_id].verbatim_excerpt
                        if not sup.verbatim_clause:
                            errors.append(f"claims.jsonl: Claim {c.claim_id} support_clause verbatim_clause cannot be empty")
                        elif sup.verbatim_clause not in ev_excerpt:
                            errors.append(
                                f"claims.jsonl: Claim {c.claim_id} support_clause verbatim_clause is not a substring of evidence {sup.evidence_id}"
                            )
                        # Check span offsets: MUST be strictly positive, non-zero span!
                        if sup.clause_span_start < 0 or sup.clause_span_end <= sup.clause_span_start or sup.clause_span_end > len(ev_excerpt):
                            errors.append(
                                f"claims.jsonl: Claim {c.claim_id} support_clause span [{sup.clause_span_start}:{sup.clause_span_end}] "
                                f"is invalid (must be positive non-zero range within excerpt length {len(ev_excerpt)})"
                            )
                        else:
                            slice_text = ev_excerpt[sup.clause_span_start:sup.clause_span_end]
                            if sup.verbatim_clause != slice_text:
                                errors.append(
                                    f"claims.jsonl: Claim {c.claim_id} support_clause span [{sup.clause_span_start}:{sup.clause_span_end}] "
                                    f"does not match verbatim_clause in evidence {sup.evidence_id}"
                                )

                    if sup.subject_mention_id not in mentions:
                        errors.append(
                            f"claims.jsonl: Claim {c.claim_id} support_clause references non-existent subject_mention_id '{sup.subject_mention_id}'"
                        )
                    else:
                        # Cross-evidence & subject anchor check:
                        # 1. support_clause must anchor to the claim's subject mention
                        if sup.subject_mention_id != c.subject_mention_id:
                            errors.append(
                                f"claims.jsonl: Support clause subject mention '{sup.subject_mention_id}' does not match "
                                f"claim subject_mention_id '{c.subject_mention_id}'!"
                            )
                        # 2. The subject normally originates from the supported evidence.
                        # A document-context support may point to another exact slice from
                        # the same source page, but never to a different source.
                        subj_m = mentions[c.subject_mention_id]
                        if subj_m.evidence_id != sup.evidence_id:
                            subject_ev = evidence.get(subj_m.evidence_id)
                            support_ev = evidence.get(sup.evidence_id)
                            selector = (
                                support_ev.locator.selector_or_page
                                if support_ev is not None
                                else ""
                            )
                            same_source = bool(
                                subject_ev is not None
                                and support_ev is not None
                                and subject_ev.source_id == support_ev.source_id
                            )
                            if (
                                sup.subject_resolution != "document_context"
                                or not same_source
                                or not selector.startswith("document-context:")
                            ):
                                errors.append(
                                    f"claims.jsonl: Cross-evidence contamination! Subject mention '{c.subject_mention_id}' "
                                    f"originates from evidence '{subj_m.evidence_id}', but support clause attaches "
                                    f"evidence '{sup.evidence_id}' without a valid same-source document-context contract!"
                                )
                        # 3. Subject span containment: if the subject's name is explicitly present in the support clause,
                        # the subject mention's span [char_start, char_end] MUST fall within [clause_span_start, clause_span_end]
                        elif subj_m.raw_name_text.lower() in sup.verbatim_clause.lower():
                            if not (sup.clause_span_start <= subj_m.char_start and subj_m.char_end <= sup.clause_span_end):
                                errors.append(
                                    f"claims.jsonl: Subject mention anchor span violation! Claim {c.claim_id} subject mention "
                                    f"'{c.subject_mention_id}' ({subj_m.raw_name_text}) span [{subj_m.char_start}:{subj_m.char_end}] "
                                    f"does not fall within support clause span [{sup.clause_span_start}:{sup.clause_span_end}]!"
                                )

                        # 4. Object presence check: substantive / discriminative tokens of c.object_raw must be present in sup.verbatim_clause
                        if not check_object_presence(c.object_raw, sup.verbatim_clause):
                            errors.append(
                                f"claims.jsonl: Object presence violation! Claim {c.claim_id} object '{c.object_raw}' "
                                f"has no substantive tokens in support clause '{sup.verbatim_clause}'!"
                            )

                        # 5. Relation span containment check (mandatory for all factual claims in RELATION_REQUIRED_PREDICATES)
                        is_factual_predicate = c.predicate in RELATION_REQUIRED_PREDICATES
                        if (sup.relation_span_start is None) != (sup.relation_span_end is None):
                            errors.append(
                                f"claims.jsonl: Incomplete relation span! Claim {c.claim_id} has asymmetric relation span "
                                f"[{sup.relation_span_start}:{sup.relation_span_end}]! Both must be set or both None."
                            )
                        elif sup.relation_span_start is None and sup.relation_span_end is None:
                            clause_level_claims_count += 1
                            if is_factual_predicate:
                                errors.append(
                                    f"claims.jsonl: Missing relation span! Factual claim {c.claim_id} ({c.predicate}) "
                                    f"has clause-level support without mandatory relation-level span (relation_span_start/end cannot be None)!"
                                )
                        elif sup.relation_span_start is not None and sup.relation_span_end is not None:
                            if not (sup.clause_span_start <= sup.relation_span_start < sup.relation_span_end <= sup.clause_span_end):
                                errors.append(
                                    f"claims.jsonl: Relation span boundary violation! Claim {c.claim_id} relation span "
                                    f"[{sup.relation_span_start}:{sup.relation_span_end}] is not contained within clause span [{sup.clause_span_start}:{sup.clause_span_end}]!"
                                )
                            if (
                                subj_m.evidence_id == sup.evidence_id
                                and subj_m.raw_name_text.lower() in sup.verbatim_clause.lower()
                            ):
                                if not (sup.relation_span_start <= subj_m.char_start and subj_m.char_end <= sup.relation_span_end):
                                    errors.append(
                                        f"claims.jsonl: Relation span subject violation! Claim {c.claim_id} subject mention "
                                        f"'{c.subject_mention_id}' [{subj_m.char_start}:{subj_m.char_end}] does not fall within relation span [{sup.relation_span_start}:{sup.relation_span_end}]!"
                                    )
                            ev_rel_slice = evidence[sup.evidence_id].verbatim_excerpt[sup.relation_span_start:sup.relation_span_end] if sup.evidence_id in evidence else ""
                            if ev_rel_slice:
                                if not check_object_presence(c.object_raw, ev_rel_slice):
                                    errors.append(
                                        f"claims.jsonl: Relation span object violation! Claim {c.claim_id} object '{c.object_raw}' "
                                        f"has no substantive tokens in relation span [{sup.relation_span_start}:{sup.relation_span_end}] ('{ev_rel_slice}')!"
                                    )
            except Exception as e:
                errors.append(f"claims.jsonl: line {line_no} validation error: {e}")

    # Load and validate Dossier
    dossier_obj = None
    try:
        with open(bundle_dir / "dossier.json", "r", encoding="utf-8") as f:
            dossier_raw = json.load(f)
        dossier_obj = Dossier(**dossier_raw)

        if dossier_obj.candidate_entity_id is not None:
            if dossier_obj.candidate_entity_id not in candidates:
                errors.append(f"dossier.json: candidate_entity_id '{dossier_obj.candidate_entity_id}' not found in candidates.jsonl")
            if dossier_obj.proposed_cluster_id not in clusters:
                errors.append(f"dossier.json: proposed_cluster_id '{dossier_obj.proposed_cluster_id}' not found in clusters.jsonl")
            if dossier_obj.candidate_entity_id in candidates:
                expected_clust = candidates[dossier_obj.candidate_entity_id].proposed_cluster_id
                if dossier_obj.proposed_cluster_id != expected_clust:
                    errors.append(f"dossier.json: Cluster mismatch: dossier has '{dossier_obj.proposed_cluster_id}' but candidate entity has '{expected_clust}'")

            stmt_ids: Set[str] = set()
            for stmt in dossier_obj.statements:
                if stmt.statement_id in stmt_ids:
                    errors.append(f"dossier.json: Duplicate statement_id '{stmt.statement_id}'")
                stmt_ids.add(stmt.statement_id)
                if not stmt.backed_claim_ids:
                    errors.append(f"dossier.json: Statement {stmt.statement_id} has no backed_claim_ids")
                for c_id in stmt.backed_claim_ids:
                    if c_id not in claims:
                        errors.append(f"dossier.json: Statement {stmt.statement_id} references non-existent claim '{c_id}'")
                    else:
                        # MANDATORY CLAIM PURITY: claim must belong to dossier.candidate_entity_id
                        if claims[c_id].candidate_entity_id != dossier_obj.candidate_entity_id:
                            errors.append(
                                f"dossier.json: Statement {stmt.statement_id} references claim '{c_id}' belonging to "
                                f"candidate '{claims[c_id].candidate_entity_id}', contaminating dossier of '{dossier_obj.candidate_entity_id}'!"
                            )
        else:
            # Null candidate_entity_id (ambiguous identity or insufficient evidence / abstention)
            outcome_val = manifest_obj.run_outcome.value if manifest_obj else "ambiguous_identity"
            if outcome_val == "ambiguous_identity":
                if not dossier_obj.ambiguous_candidates or len(dossier_obj.ambiguous_candidates) < 2:
                    errors.append("dossier.json: Ambiguous dossier must list at least 2 ambiguous_candidates")
            if dossier_obj.statements:
                errors.append("dossier.json: Ambiguous or abstention dossier must have empty statements")
    except Exception as e:
        errors.append(f"dossier.json validation error: {e}")

    # 3. State Machine Consistency with Manifest
    if manifest_obj:
        outcome = manifest_obj.run_outcome.value
        if outcome in ("failed", "collection_failed", "budget_exhausted"):
            errors.append(f"Bundle invalid: run_outcome is '{outcome}'")
        elif outcome == "ambiguous_identity":
            if dossier_obj and dossier_obj.candidate_entity_id is not None:
                errors.append("run_outcome is 'ambiguous_identity' but dossier candidate_entity_id is not null")
        elif outcome == "insufficient_evidence":
            if not manifest_obj.abstention_records:
                errors.append("run_outcome is 'insufficient_evidence' but abstention_records is empty")
            if claims:
                errors.append(f"run_outcome is 'insufficient_evidence' but claims.jsonl contains {len(claims)} claims")
        elif outcome == "completed":
            if not claims:
                errors.append("run_outcome is 'completed' but claims.jsonl has zero claims")
            if dossier_obj and not dossier_obj.statements:
                errors.append("run_outcome is 'completed' but dossier statements are empty")

    # 4. Dossier Markdown and Outcome Cross-Validation
    dossier_md_path = bundle_dir / "dossier.md"
    if not dossier_md_path.exists():
        errors.append("Missing required bundle file: dossier.md")
    else:
        try:
            with open(dossier_md_path, "r", encoding="utf-8") as f:
                md_text = f.read().strip()
            if not md_text:
                errors.append("dossier.md is empty")
            elif manifest_obj:
                outcome = manifest_obj.run_outcome.value
                if outcome == "insufficient_evidence":
                    if "INSUFFICIENT_EVIDENCE" not in md_text:
                        errors.append("dossier.md must mention INSUFFICIENT_EVIDENCE when run_outcome is insufficient_evidence")
                    if "AMBIGUOUS_IDENTITY" in md_text:
                        errors.append("dossier.md must NOT mention AMBIGUOUS_IDENTITY when run_outcome is insufficient_evidence")
                elif outcome == "ambiguous_identity":
                    if "AMBIGUOUS_IDENTITY" not in md_text:
                        errors.append("dossier.md must mention AMBIGUOUS_IDENTITY when run_outcome is ambiguous_identity")
                elif outcome == "completed":
                    if dossier_obj and dossier_obj.candidate_entity_id:
                        if dossier_obj.candidate_entity_id not in md_text and dossier_obj.proposed_cluster_id not in md_text:
                            warnings.append("dossier.md does not reference candidate_entity_id or proposed_cluster_id")
        except Exception as e:
            errors.append(f"Failed to read dossier.md: {e}")

    structural_errors = list(errors)
    structural_valid = len(structural_errors) == 0
    has_warc_ids = all(bool(s.warc_record_id) for s in sources.values())
    
    provenance_replay_valid = None
    replay_errors: List[str] = []
    if warc_path is not None:
        replay_res = verify_warc_replay(bundle_dir, warc_path)
        if not replay_res["valid"]:
            provenance_replay_valid = False
            replay_errors.extend(replay_res["errors"])
        else:
            provenance_replay_valid = bool(has_warc_ids and replay_res["valid"])

    all_errors = structural_errors + replay_errors
    is_valid = bool(structural_valid and (provenance_replay_valid is not False))
    semantic_review_passed = bool(structural_valid and review_edges_count == 0 and unadjudicated_claims_count == 0)

    return {
        "is_valid": is_valid,
        "error_count": len(all_errors),
        "warning_count": len(warnings),
        "layers": {
            "structural_valid": structural_valid,
            "warc_record_ids_present": has_warc_ids,
            "provenance_replay_valid": provenance_replay_valid,
            "semantic_review_passed": semantic_review_passed,
            "relation_precision_enforced": bool(structural_valid and clause_level_claims_count == 0),
        },
        "audit_details": {
            "all_sources_have_warc_record_id": has_warc_ids,
            "warc_replay_verified": bool(provenance_replay_valid is True),
            "unadjudicated_claim_count": unadjudicated_claims_count,
            "review_edge_count": review_edges_count,
            "clause_level_claim_count": clause_level_claims_count,
        },
        "errors": all_errors,
        "warnings": warnings,
    }


def verify_warc_replay(bundle_dir: Path, warc_path: Path) -> Dict[str, Any]:
    """
    Substantive WARC provenance replay verifier.
    Parses the target WARC, locates records by warc_record_id, verifies target URI and HTTP status,
    recalculates payload SHA-256, and verifies that every Evidence verbatim_excerpt and locator
    is directly sourced from the corresponding WARC record payload (Claim-level provenance closure).
    """
    replay_errors: List[str] = []
    if not warc_path.exists():
        return {"valid": False, "errors": [f"WARC archive not found at: {warc_path}"], "verified_count": 0}

    try:
        from core.collectors.warc_player import WarcPlayerCollector
        player = WarcPlayerCollector(warc_path)
    except Exception as e:
        return {"valid": False, "errors": [f"Failed to load WARC player for {warc_path}: {e}"], "verified_count": 0}

    sources_path = bundle_dir / "sources.jsonl"
    if not sources_path.exists():
        return {"valid": False, "errors": ["sources.jsonl missing from bundle"], "verified_count": 0}

    sources: List[SourceSnapshot] = []
    with open(sources_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                sources.append(SourceSnapshot(**json.loads(line)))
            except Exception as e:
                replay_errors.append(f"sources.jsonl: line {line_no} parse error: {e}")

    warc_payloads: Dict[str, str] = {}
    verified_sources = 0
    for s in sources:
        if not s.warc_record_id:
            replay_errors.append(f"Source {s.source_id} ({s.url}) has missing or empty warc_record_id")
            continue

        warc_rec = None
        if hasattr(player, "records_by_id"):
            warc_rec = player.records_by_id.get(s.warc_record_id) or player.records_by_id.get(s.warc_record_id.strip("<>"))

        if not warc_rec:
            replay_errors.append(
                f"Source {s.source_id} ({s.url}) warc_record_id '{s.warc_record_id}' not found in WARC {warc_path.name}"
            )
            continue

        if warc_rec.warc_record_id:
            clean_warc_id = warc_rec.warc_record_id.strip("<>")
            clean_src_id = s.warc_record_id.strip("<>")
            if clean_warc_id != clean_src_id:
                replay_errors.append(
                    f"Source {s.source_id} warc_record_id '{s.warc_record_id}' does not match WARC record ID '{warc_rec.warc_record_id}'"
                )
                continue

        norm_warc_uri = warc_rec.target_uri.rstrip("/")
        norm_src_url = s.url.rstrip("/")
        if norm_warc_uri != norm_src_url:
            replay_errors.append(
                f"Source {s.source_id} URL '{s.url}' does not match WARC target URI '{warc_rec.target_uri}'"
            )

        if warc_rec.http_status != s.http_status:
            replay_errors.append(
                f"Source {s.source_id} HTTP status {s.http_status} does not match WARC status {warc_rec.http_status}"
            )

        recomputed_sha = hashlib.sha256(warc_rec.payload.encode("utf-8")).hexdigest()
        if recomputed_sha != s.content_sha256:
            replay_errors.append(
                f"Source {s.source_id} content_sha256 '{s.content_sha256}' does not match recomputed WARC payload SHA-256 '{recomputed_sha}'"
            )
        else:
            warc_payloads[s.source_id] = warc_rec.payload

        verified_sources += 1

    # Evidence-to-WARC substantive verification
    evidence_path = bundle_dir / "evidence.jsonl"
    verified_evidence = 0
    if evidence_path.exists():
        with open(evidence_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    ev_dict = json.loads(line)
                    ev = Evidence(**ev_dict)
                except Exception as e:
                    replay_errors.append(f"evidence.jsonl: line {line_no} parse error: {e}")
                    continue

                if ev.source_id not in warc_payloads:
                    replay_errors.append(
                        f"Evidence {ev.evidence_id}: associated source {ev.source_id} payload not available from WARC"
                    )
                    continue

                w_payload = warc_payloads[ev.source_id]
                expected_sha = hashlib.sha256(w_payload.encode("utf-8")).hexdigest()
                if ev.raw_payload_sha256 and ev.raw_payload_sha256 != expected_sha:
                    replay_errors.append(
                        f"Evidence {ev.evidence_id} raw_payload_sha256 '{ev.raw_payload_sha256}' does not match WARC payload SHA-256 '{expected_sha}'"
                    )

                if ev.verbatim_excerpt not in w_payload:
                    replay_errors.append(
                        f"Evidence {ev.evidence_id}: verbatim_excerpt is not found in the WARC record payload for source {ev.source_id}"
                    )
                else:
                    if ev.char_start is not None and ev.char_end is not None:
                        if 0 <= ev.char_start < ev.char_end <= len(w_payload):
                            sliced = w_payload[ev.char_start:ev.char_end]
                            if sliced != ev.verbatim_excerpt:
                                replay_errors.append(
                                    f"Evidence {ev.evidence_id}: char span [{ev.char_start}:{ev.char_end}] in WARC payload does not match verbatim_excerpt"
                                )
                        else:
                            replay_errors.append(
                                f"Evidence {ev.evidence_id}: char span [{ev.char_start}:{ev.char_end}] is out of bounds for WARC payload (length {len(w_payload)})"
                            )

                verified_evidence += 1

    if len(sources) == 0:
        is_replay_ok = (len(replay_errors) == 0)
    else:
        is_replay_ok = (len(replay_errors) == 0 and verified_sources > 0)
    return {
        "valid": is_replay_ok,
        "errors": replay_errors,
        "verified_count": verified_sources,
        "verified_evidence_count": verified_evidence,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate output bundle structure and referential integrity.")
    parser.add_argument("--bundle-dir", type=Path, required=True, help="Path to bundle directory.")
    parser.add_argument("--warc-path", type=Path, default=None, help="Optional path to WARC archive for strict provenance verification.")
    args = parser.parse_args()

    res = validate_bundle(args.bundle_dir, warc_path=args.warc_path)
    print(json.dumps(res, indent=2, ensure_ascii=False))
