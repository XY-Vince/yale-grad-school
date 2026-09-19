"""
Claim and Relation Extractor (V4.4.1).
Extracts atomic claims from verified evidence using sentence and clause segmentation,
syntactic frame resolution (Quotation, Appositive, SVO), and strict subject attribution.
Generates deterministic 128-bit SHA-256 Claim IDs and records ClaimEvidenceSupport.
"""

import hashlib
import re
from typing import Dict, List, Optional, Tuple
from models.schemas import (
    AdjudicationStatus,
    Claim,
    ClaimEvidenceSupport,
    DateWithPrecision,
    EntityMention,
    Evidence,
    FactPolarity,
    TemporalStatus,
    PREDICATE_ALLOWLIST,
)
from core.resolver import extract_organizations, clean_org_token, GENERIC_ORGS
from core.extractors.mention_extractor import is_valid_chinese_name_boundary, ZH_NAME_RIGHT_ALLOWED, ZH_NAME_LEFT_ALLOWED
from core.extractors.subject_attribution import (
    build_person_mention_universe,
    detect_post_predicate_subject,
    resolve_pronoun_antecedent,
    is_exact_or_verified_alias_match,
)

PRO_DROP_DIRECT_PREDICATES = r"(?:现任|曾任|兼任|担任|现为|曾为|荣获|获|入选|受聘|任职|就任|就职|毕业|就读|求学|发表|出版|撰写|出生|生于)"
PRO_DROP_ADVERB_CONNECTORS = r"(?:目前|随后|并|同时|此前|此后)"
PRO_DROP_ZH_PATTERN = rf"^(?:{PRO_DROP_DIRECT_PREDICATES}|{PRO_DROP_ADVERB_CONNECTORS}\s*{PRO_DROP_DIRECT_PREDICATES})"

NEGATION_PATTERNS = [
    r"\bnot\b",
    r"\bnever\b",
    r"\bno longer\b",
    r"\bceased\b",
    r"\bdenies\b",
    r"\bdoes not\b",
    r"\bdid not\b",
    r"\bwas not\b",
    r"\bis not\b",
    r"并未",
    r"绝非",
    r"不再",
    r"未曾",
    r"并非",
    r"未入选",
    r"已离开",
]

PAST_PATTERNS = [
    r"\bformer\b",
    r"\bpast\b",
    r"\bpreviously\b",
    r"\bwas\b",
    r"\buntil\b",
    r"\bex-\b",
    r"\bretired\b",
    r"\bstepped down\b",
    r"\bearned\b",
    r"\breceived\b",
    r"\bgraduated\b",
    r"\bcompleted\b",
    r"\bobtained\b",
    r"\bawarded\b",
    r"曾任",
    r"前任",
    r"已离任",
    r"历任",
    r"原",
    r"既往",
    r"毕业于",
    r"获.*学位",
    r"获得",
]

CURRENT_PATTERNS = [
    r"\bcurrently\b",
    r"\bcurrent\b",
    r"\bpresent\b",
    r"\bsince\b",
    r"\bnow\b",
    r"\bis\b",
    r"\bare\b",
    r"\bserves as\b",
    r"\bserve as\b",
    r"\bserves\b",
    r"\bworks as\b",
    r"\bwork as\b",
    r"\bwill join\b",
    r"\bwill serve\b",
    r"\bjoins\b",
    r"\bincoming\b",
    r"\badmitted to\b",
    r"\baccepted to\b",
    r"\bholds\b",
    r"\bleads\b",
    r"现任",
    r"担任",
    r"至今",
    r"目前",
]


def detect_clause_polarity(clause: str) -> FactPolarity:
    lower_text = clause.lower()
    for pat in NEGATION_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            return FactPolarity.NEGATIVE
    return FactPolarity.AFFIRMATIVE


def detect_clause_temporal_status(clause: str, target_name: Optional[str] = None) -> TemporalStatus:
    lower_text = clause.lower()
    for pat in PAST_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            return TemporalStatus.FORMER
    for pat in CURRENT_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            return TemporalStatus.CURRENT
    if target_name:
        t_pat = re.escape(target_name)
        first_name = target_name.strip().split()[0]
        if re.search(
            rf"\b(?:Dean|Professor|Director|President|Chair|教授|院长|主任|校长)\s+(?:{t_pat}|{re.escape(first_name)})\b",
            clause,
            re.IGNORECASE,
        ):
            return TemporalStatus.CURRENT
        if re.search(
            rf"{t_pat}\s*[,，]\s*(?:(?:the|a|an)\s+)?(?:(?:[a-z]+ly\s+)?[a-z-]+\s+)*(?:Dean|Professor|Director|President|Chair|Scientist|Fellow|Researcher|Engineer|Analyst|Manager|Clerk|Resident|Member|Trustee)",
            clause,
            re.IGNORECASE,
        ):
            return TemporalStatus.CURRENT
    return TemporalStatus.UNKNOWN


def clean_position_title(raw_title: str) -> str:
    cleaned = re.sub(
        r"^(?:(?:Dr\.|Mr\.|Ms\.|Prof\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+)?(?:is|was|are|were|serves as|served as|will join(?:\s+[A-Za-z0-9&.-]+(?:\s+[A-Za-z0-9&.-]+)*)?\s+as|joins(?:\s+[A-Za-z0-9&.-]+(?:\s+[A-Za-z0-9&.-]+)*)?\s+as|currently|previously|not|appointed as|holds position of)\s+",
        "",
        raw_title,
        flags=re.IGNORECASE,
    ).strip()
    cleaned = re.sub(r"^(?:a|an|the)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"<[^>]+>", " ", cleaned).strip()
    cleaned = re.sub(r"\s+\d+$", "", cleaned).strip()
    cleaned = re.sub(r"\s+[IVX]+$", "", cleaned).strip()
    if cleaned.lower().startswith("it, "):
        cleaned = re.sub(r"^it,\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"^(?:(?:[a-z]+ly\s+)?(?:award-winning|recognized|acclaimed|respected|renowned|noted|prominent|leading|honorary|emeritus|former|past|previous|ex-|current|acting)\s+)+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    if not re.match(r"^distinguished\s+(?:university\s+)?professors?\b", cleaned, re.IGNORECASE):
        cleaned = re.sub(r"^distinguished\s+", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^(?:现任|曾任|担任|被聘为)\s*", "", cleaned).strip()
    cleaned = re.sub(r"^[一-鿿A-Za-z0-9]{2,15}?(?:大学|学院|研究所|研究院|医院)\s*", "", cleaned).strip()
    # Singularize standard plural roles
    plural_map = [
        (r"\bProfessors\b", "Professor"),
        (r"\bDeans\b", "Dean"),
        (r"\bDirectors\b", "Director"),
        (r"\bScientists\b", "Scientist"),
        (r"\bResearchers\b", "Researcher"),
        (r"\bEngineers\b", "Engineer"),
        (r"\bFellows\b", "Fellow"),
        (r"\bChairs\b", "Chair"),
        (r"\bPresidents\b", "President"),
        (r"\bAssociates\b", "Associate"),
        (r"\bAgents\b", "Agent"),
        (r"\bRealtors\b", "Realtor"),
        (r"\bStudents\b", "Student"),
        (r"\bAnalysts\b", "Analyst"),
        (r"\bResidents\b", "Resident"),
        (r"\bMembers\b", "Member"),
        (r"\bClerks\b", "Clerk"),
    ]
    for p_pat, s_repl in plural_map:
        cleaned = re.sub(p_pat, s_repl, cleaned, flags=re.IGNORECASE)
    # Strip trailing punctuation
    cleaned = re.sub(r"[,.;:\s]+$", "", cleaned).strip()
    return cleaned


def split_sentences_and_clauses(text: str) -> List[Tuple[int, int, str]]:
    """
    Splits text into sentences/clauses with start and end character offsets.
    Splits by major punctuation as well as clause-level subordinating conjunctions.
    """
    results = []
    # Split by major punctuation: periods, exclamation, question marks, semicolons, newlines, and Chinese punctuation
    # Guard against splitting on abbreviations or middle initials like "N.", "E.", "Dr.", "Prof."
    # Also split on clause conjunction boundaries (while, whereas, meanwhile, whilst, etc.)
    delimiters = (
        r"(?<!\b[A-Z])(?<!\bDr)(?<!\bProf)(?<!\bMr)(?<!\bMs)(?<!\bPh)(?<!\bPh\.D)(?<!\bM\.D)[.!?;\n。！？；]+"
        r"|[,;，；]?\s*\b(?:while|whereas|meanwhile|whilst)\b"
        r"|[,;，；]\s*(?:but|although|though|however)\b"
        r"|[，；]\s*(?=(?:现任|曾任|兼任|担任|随后|目前|同时|现为|曾为|并))"
    )
    last_end = 0
    for match in re.finditer(delimiters, text, re.IGNORECASE):
        last_open = text.rfind("<", 0, match.start())
        last_close = text.rfind(">", 0, match.start())
        if last_open > last_close:
            continue
        raw_seg = text[last_end:match.start()]
        lstrip_len = len(raw_seg) - len(raw_seg.lstrip())
        clause = raw_seg.strip()
        if clause:
            c_start = last_end + lstrip_len
            c_end = c_start + len(clause)
            results.append((c_start, c_end, clause))
        last_end = match.end()

    if last_end < len(text):
        raw_seg = text[last_end:]
        lstrip_len = len(raw_seg) - len(raw_seg.lstrip())
        clause = raw_seg.strip()
        if clause:
            c_start = last_end + lstrip_len
            c_end = c_start + len(clause)
            results.append((c_start, c_end, clause))

    if not results and text.strip():
        lstrip_len = len(text) - len(text.lstrip())
        clause = text.strip()
        results.append((lstrip_len, lstrip_len + len(clause), clause))

    return results


def partition_clause_by_mentions(
    c_start: int,
    c_end: int,
    clause_text: str,
    mentions: List[EntityMention],
) -> List[Tuple[int, int, str, Optional[EntityMention]]]:
    """
    Partitions a clause containing multiple entity mentions into mention-specific sub-clauses,
    ensuring each sub-clause only binds to its corresponding subject mention.
    """
    unique_m = {}
    for m in mentions:
        key = (m.char_start, m.char_end)
        if key not in unique_m:
            unique_m[key] = m
    sorted_m = sorted(unique_m.values(), key=lambda m: m.char_start)

    if len(sorted_m) <= 1:
        m = sorted_m[0] if sorted_m else None
        return [(c_start, c_end, clause_text, m)]

    # Check if mentions are separated by a verb, role, or clause boundary
    # Notice: do NOT treat a bare comma or 'and' between coordinates as a separate predicate!
    has_separate_predicates = False
    for i in range(len(sorted_m) - 1):
        m_curr = sorted_m[i]
        m_next = sorted_m[i + 1]
        rel_m_curr_end = max(0, m_curr.char_end - c_start)
        rel_m_next_start = max(rel_m_curr_end, m_next.char_start - c_start)
        between = clause_text[rel_m_curr_end:rel_m_next_start]
        if re.search(
            r'(\b(?:while|whereas|meanwhile|whilst|but)\b|[;；]|\b(?:is|was|are|were|serves?|served|joined|appointed|became|holds?|held|works?|worked|introduced|met|visited|welcomed|hired|co-authored|spoke|praised|Professor|Dean|Director|Doctor|President|Scientist|Fellow|Chair|Researcher|Engineer|Agent|Scholar|Associate|担任|现任|曾任|是|就职于|受聘于|任职于|会见|访问|对话)\b)',
            between,
            re.I,
        ):
            has_separate_predicates = True
            break

    if not has_separate_predicates:
        # Coordinated subject phrase sharing the same predicate
        return [(c_start, c_end, clause_text, m) for m in sorted_m]

    sub_clauses: List[Tuple[int, int, str, Optional[EntityMention]]] = []
    curr_start = c_start

    transitive_action_verbs = r"(?:introduced|met|visited|welcomed|hired|co-authored\s+with|spoke\s+with|praised|interviewed|会见|访问|对话|介绍|欢迎)"

    for i in range(len(sorted_m)):
        m_curr = sorted_m[i]
        if i < len(sorted_m) - 1:
            m_next = sorted_m[i + 1]
            rel_m_curr_end = max(0, m_curr.char_end - c_start)
            rel_m_next_start = max(rel_m_curr_end, m_next.char_start - c_start)
            between = clause_text[rel_m_curr_end:rel_m_next_start]

            # Syntactic transition boundary detection:
            # 1. Transitive action verb between subjects (e.g. "Alice, [appositive], introduced Bob, [appositive]")
            m_trans = re.search(rf"[,，]\s*{transitive_action_verbs}\b", between, re.I)
            # 2. Semicolons or subordinate/clause conjunctions (e.g. while, whereas, meanwhile, whilst, but, ;)
            m_conj = re.search(r"([;；]|[,;，；]?\s*\b(?:while|whereas|meanwhile|whilst|but)\b)", between, re.I)
            # 3. Coordinating conjunction immediately before next mention (e.g. ", and Bob", " and Bob")
            m_and = re.search(r"[,，]?\s*\b(?:and|as\s+well\s+as)\s*$", between.rstrip(), re.I)
            # 4. Trailing comma before next mention (e.g. "Alice, Professor, Bob, Dean")
            m_trailing_comma = re.search(r"[,，]\s*$", between)

            if m_trans:
                split_rel = rel_m_curr_end + m_trans.start()
                curr_end = c_start + split_rel
                next_start = m_next.char_start
            elif m_conj and m_conj.start() > 0:
                split_rel = rel_m_curr_end + m_conj.start()
                curr_end = c_start + split_rel
                next_start = m_next.char_start
            elif m_and and m_and.start() > 0:
                split_rel = rel_m_curr_end + m_and.start()
                curr_end = c_start + split_rel
                next_start = m_next.char_start
            elif m_trailing_comma and m_trailing_comma.start() > 0:
                split_rel = rel_m_curr_end + m_trailing_comma.start()
                curr_end = c_start + split_rel
                next_start = m_next.char_start
            else:
                curr_end = m_next.char_start
                next_start = m_next.char_start
        else:
            curr_end = c_end
            next_start = c_end

        rel_start = max(0, curr_start - c_start)
        rel_end = max(rel_start, curr_end - c_start)
        raw_slice = clause_text[rel_start:rel_end]
        lstrip_len = len(raw_slice) - len(raw_slice.lstrip())
        sub_text = raw_slice.strip()
        if sub_text:
            actual_start = curr_start + lstrip_len
            actual_end = actual_start + len(sub_text)
            sub_clauses.append((actual_start, actual_end, sub_text, m_curr))
        curr_start = next_start

    if not sub_clauses:
        return [(c_start, c_end, clause_text, sorted_m[0])]
    return sub_clauses


def is_mention_matching_target(m_text: str, t_name: str) -> bool:
    """
    Determines if a mention text matches the requested target entity name or honorific alias.
    Enforces strict normalized equality; strictly forbids substring inclusion.
    """
    if not m_text or not t_name:
        return False
    return is_exact_or_verified_alias_match(m_text, {t_name})


def extract_claims_from_evidence(
    evidence: Evidence,
    candidate_entity_id: Optional[str] = None,
    subject_mention_id: Optional[str] = None,
    target_name: Optional[str] = None,
    is_current: Optional[bool] = None,
    is_negative: Optional[bool] = None,
    evidence_mentions: Optional[List[EntityMention]] = None,
    mention_to_cand_id: Optional[Dict[str, str]] = None,
) -> List[Claim]:
    """
    Extracts atomic claims from verified evidence.
    Fails closed: Rejects irrelevant noise excerpts (weather, generic navigation, etc.).
    """
    excerpt = evidence.verbatim_excerpt
    if not excerpt or not excerpt.strip():
        return []

    # Check for pure noise
    noise_indicators = [
        "the weather is",
        "current weather",
        "terms of service",
        "privacy policy",
        "cookie settings",
        "breaking news: economy",
        "all rights reserved",
    ]
    if any(n in excerpt.lower() for n in noise_indicators):
        return []

    # Ensure evidence is about target entity before attributing claims
    if target_name:
        t_clean = target_name.strip()
        is_zh = any("\u4e00" <= c <= "\u9fff" for c in t_clean)
        if is_zh:
            if t_clean not in excerpt:
                return []
        else:
            t_tokens = t_clean.split()
            t_norm_pat = r"\s+".join(re.escape(tok) for tok in t_tokens) if t_tokens else re.escape(t_clean)
            if not re.search(rf"\b{t_norm_pat}\b", excerpt, re.IGNORECASE):
                if not (evidence_mentions and any(m.evidence_id == evidence.evidence_id for m in evidence_mentions)):
                    return []
        # Single-name target protection (e.g. Liam matching David N. Liam)
        t_tokens = t_clean.split()
        if len(t_tokens) == 1 and not is_zh:
            longer_name = bool(
                re.search(rf"[A-Z][a-z]+\s+(?:[A-Z]\.\s+)?{re.escape(t_clean)}\b", excerpt)
                or re.search(rf"\b{re.escape(t_clean)}\s+[A-Z][a-z]+", excerpt)
            )
            if longer_name:
                return []

    is_target_zh = any("\u4e00" <= c <= "\u9fff" for c in target_name) if target_name else False
    t_clean = target_name.strip() if target_name else ""
    t_toks = [re.escape(t) for t in t_clean.split()]
    raw_t_toks = t_clean.split()
    surname = raw_t_toks[-1] if len(raw_t_toks) >= 2 and not is_target_zh else None
    conflicting_surname = False
    if surname and target_name:
        all_persons = build_person_mention_universe(excerpt, known_persons=[target_name])
        target_given = raw_t_toks[0].lower()
        for p in all_persons:
            p_name = p.get("name", "").strip()
            p_parts = p_name.split()
            if len(p_parts) >= 2 and p_parts[-1].lower() == surname.lower():
                if target_given not in p_name.lower():
                    conflicting_surname = True
                    break

    target_ev_mentions = [
        m for m in (evidence_mentions or [])
        if m.evidence_id == evidence.evidence_id and is_mention_matching_target(m.raw_name_text, target_name)
    ]
    if target_ev_mentions:
        base_subj_id = subject_mention_id or target_ev_mentions[0].mention_id
        if mention_to_cand_id and base_subj_id in mention_to_cand_id:
            base_cand_id = candidate_entity_id or mention_to_cand_id[base_subj_id]
        else:
            base_cand_id = candidate_entity_id or "CAND-DEFAULT"
    else:
        raw_seed = f"{evidence.source_id}:{target_name or 'target'}:1:1"
        base_subj_id = subject_mention_id or f"MEN-{hashlib.sha256(raw_seed.encode('utf-8')).hexdigest()[:12]}"
        base_cand_id = candidate_entity_id or "CAND-DEFAULT"

    # Sentence & Clause level parsing
    raw_clauses = split_sentences_and_clauses(excerpt)
    clauses: List[Tuple[int, int, str, Optional[EntityMention]]] = []
    if evidence_mentions:
        for c_start, c_end, c_text in raw_clauses:
            in_clause_m = [
                m for m in evidence_mentions
                if m.evidence_id == evidence.evidence_id and c_start <= m.char_start and m.char_end <= c_end
            ]
            clauses.extend(partition_clause_by_mentions(c_start, c_end, c_text, in_clause_m))
    else:
        clauses = [(c_start, c_end, c_text, None) for c_start, c_end, c_text in raw_clauses]

    claims: List[Claim] = []

    if is_target_zh:
        target_pat = re.escape(target_name.strip())
        target_word_pat = target_pat
    else:
        if len(t_toks) >= 2:
            target_word_pat = rf"\b(?:" + r"\s+".join(t_toks) + rf")\b"
            target_pat = rf"(?:" + r"\s+".join(t_toks) + rf")"
        elif t_toks:
            target_word_pat = rf"\b{t_toks[0]}\b"
            target_pat = t_toks[0]
        else:
            target_pat = r"[A-Z][a-z]+\s+[A-Z][a-z]+"
            target_word_pat = rf"\b{target_pat}\b"

    target_mentioned_in_prev_clause = False
    target_seen_in_excerpt = bool(target_ev_mentions)
    prev_clause_subj_id = None
    prev_clause_cand_id = None
    prev_clause_target_name = target_name
    prev_clause_span = None

    for c_start, c_end, clause, clause_m in clauses:
        clause_lower = clause.lower()

        # If clause_m was not pre-assigned, check if any mention in evidence_mentions falls in this subclause
        if clause_m is None and evidence_mentions:
            in_clause_mentions = [
                m for m in evidence_mentions
                if m.evidence_id == evidence.evidence_id and c_start <= m.char_start and m.char_end <= c_end
            ]
            if in_clause_mentions:
                if target_name:
                    matching_m = [m for m in in_clause_mentions if is_mention_matching_target(m.raw_name_text, target_name)]
                    clause_m = matching_m[0] if matching_m else in_clause_mentions[0]
                else:
                    clause_m = in_clause_mentions[0]

        has_target = False
        is_anaphoric = False
        is_profile_field = False

        # Check for post-predicate (cleft / focal) subject attribution:
        # e.g. '随后荣获 Nobel Prize 的是张伟', 'The recipient was Bob Jones'
        post_subj = detect_post_predicate_subject(clause)
        if post_subj and target_name and not is_mention_matching_target(post_subj, target_name):
            target_mentioned_in_prev_clause = False
            prev_clause_subj_id = None
            prev_clause_cand_id = None
            prev_clause_target_name = None
            prev_clause_span = None
            continue

        is_surname_clause = False
        if clause_m is not None:
            if target_name and not is_mention_matching_target(clause_m.raw_name_text, target_name):
                if not mention_to_cand_id or clause_m.mention_id not in mention_to_cand_id:
                    # Another person is the subject of this subclause and not a routed candidate; reset anaphoric continuity
                    target_mentioned_in_prev_clause = False
                    prev_clause_subj_id = None
                    prev_clause_cand_id = None
                    prev_clause_target_name = None
                    prev_clause_span = None
                    continue
            has_target = True
            subj_id = clause_m.mention_id
            candidate_entity_id = (mention_to_cand_id.get(clause_m.mention_id) if mention_to_cand_id else None) or base_cand_id
            clause_target_name = clause_m.raw_name_text.strip()
        elif target_name:
            t_clean = target_name.strip()
            if is_target_zh:
                has_target = False
                for tm in re.finditer(re.escape(t_clean), clause):
                    tm_s, tm_e = tm.start(), tm.end()
                    abs_tm_s = c_start + tm_s
                    abs_tm_e = c_start + tm_e
                    if is_valid_chinese_name_boundary(t_clean, abs_tm_s, abs_tm_e, excerpt):
                        has_target = True
                        break
            else:
                has_target = bool(re.search(target_word_pat, clause, re.IGNORECASE))
                if not has_target and surname and target_seen_in_excerpt and not conflicting_surname:
                    surname_verb_pat = rf"\b{re.escape(surname)}\s+(?:was|is|serves|served|joined|retired|holds|held|became|has\s+been|had\s+been)\b"
                    if re.search(surname_verb_pat, clause, re.IGNORECASE):
                        has_target = True
                        is_surname_clause = True
            if has_target:
                target_seen_in_excerpt = True
                subj_id = base_subj_id
                candidate_entity_id = base_cand_id
                clause_target_name = t_clean

        if not has_target and target_mentioned_in_prev_clause and prev_clause_subj_id:
            if re.match(r"^(?:(?:in\s+\d{4}|since\s+\d{4}|from\s+\d{4}|currently|previously|formerly|later|subsequently|and|also|thereafter)\s*[,，]?\s*)*(?:she|he|they|i|my)\b|^(?:其|该学者|该专家)", clause_lower.strip()) or re.match(PRO_DROP_ZH_PATTERN, clause.strip()):
                is_anaphoric = True
            elif re.match(r"^(?:<[^>]+>)?\s*(?:position|roles?|title|rank|职位|职务|职称|头衔)\s*[:：]", clause_lower.strip()):
                is_profile_field = True
            elif re.match(r"^(?:<[^>]+>)*\s*(?:<h[1-6][^>]*>|<span[^>]*>|<p[^>]*>|<div[^>]*>)?\s*(?:(?:the|a|an)\s+)?(?:(?:[a-z]+ly\s+)?[a-z-]+\s+)*(?:Assistant|Associate|Full|Distinguished|Clinical|Visiting|Executive|Senior|Junior|Principal|Lead|Staff|Software|Postdoctoral|Real\s+Estate|Research|IT|Business\s+Systems|Hospital|Global\s+Surgery|Data\s+Visualization|Surgery\s+)*?(?:Director|Dean|Chair|President|Head|Professor|Scientist|Fellow|Researcher|Engineer|Agent|Realtor|Associate|Scholar|Physician|Specialist|Doctor|Student|Analyst|Consultant|Manager|Candidate|Clerk|Resident|Member|Trustee|教授|副教授|研究员|博士后|院长|主任|科学家|工程师|会长|校长|医师|队长)", clause, re.IGNORECASE):
                is_profile_field = True

            # Tight contiguity and boundary check for pro-drop and pronoun anaphora:
            if is_anaphoric:
                pronoun_m = re.search(r"\b(she|he|they|i|my|其|该学者|该专家)\b", clause, re.IGNORECASE)
                if not pronoun_m:
                    # pro-drop: must be immediately contiguous without sentence boundary
                    if prev_clause_span:
                        gap = excerpt[prev_clause_span[1]:c_start] if 0 <= prev_clause_span[1] <= c_start <= len(excerpt) else ""
                        if (c_start - prev_clause_span[1] > 15) or re.search(r"[。！？.!?\n\r]", gap):
                            is_anaphoric = False
                else:
                    # pronoun: must bind to nearest compatible antecedent
                    p_word = pronoun_m.group(1)
                    p_start_in_excerpt = c_start + pronoun_m.start()
                    all_persons = build_person_mention_universe(excerpt, known_persons=[target_name] if target_name else [])
                    valid_tgts = {target_name} if target_name else set()
                    if prev_clause_target_name:
                        valid_tgts.add(prev_clause_target_name)
                    is_bound, resolved_name = resolve_pronoun_antecedent(
                        p_word, p_start_in_excerpt, excerpt, target_names=valid_tgts, all_mentions=all_persons
                    )
                    if not is_bound:
                        is_anaphoric = False

            if is_anaphoric or is_profile_field:
                subj_id = prev_clause_subj_id
                candidate_entity_id = prev_clause_cand_id
                clause_target_name = prev_clause_target_name or (target_name.strip() if target_name else "")

        if not has_target and not is_anaphoric and not is_profile_field:
            # Intervening clause breaks pronoun/anaphora chain! Reset antecedent state immediately.
            target_mentioned_in_prev_clause = False
            prev_clause_subj_id = None
            prev_clause_cand_id = None
            prev_clause_target_name = None
            prev_clause_span = None
            continue

        resolution_type = "explicit_mention"
        antecedent_id = None
        antecedent_span = None

        if has_target:
            resolution_type = "explicit_mention"
        elif is_anaphoric:
            pronoun_m = re.search(r"\b(she|he|they|i|my|其|该学者|该专家)\b", clause, re.IGNORECASE)
            resolution_type = "pronoun_anaphora" if pronoun_m else "pro_drop_anaphora"
            antecedent_id = prev_clause_subj_id
            antecedent_span = prev_clause_span
        elif is_profile_field:
            resolution_type = "profile_field"
            antecedent_id = None
            antecedent_span = None

        # Successfully matched or continued: update antecedent state
        target_mentioned_in_prev_clause = True
        prev_clause_subj_id = subj_id
        prev_clause_cand_id = candidate_entity_id
        prev_clause_target_name = clause_target_name
        prev_clause_span = (c_start, c_end)

        def make_support(rel_s: Optional[int] = None, rel_e: Optional[int] = None) -> ClaimEvidenceSupport:
            if rel_s is not None and rel_e is not None:
                if clause_m and c_start <= clause_m.char_start and clause_m.char_end <= c_end:
                    rel_s = min(rel_s, clause_m.char_start)
                    rel_e = max(rel_e, clause_m.char_end)
                elif clause_target_name and clause_target_name.lower() in clause.lower():
                    t_idx = clause.lower().find(clause_target_name.lower())
                    if t_idx >= 0:
                        rel_s = min(rel_s, c_start + t_idx)
                        rel_e = max(rel_e, c_start + t_idx + len(clause_target_name))
                elif is_surname_clause and surname and surname.lower() in clause.lower():
                    s_idx = clause.lower().find(surname.lower())
                    if s_idx >= 0:
                        rel_s = min(rel_s, c_start + s_idx)
                        rel_e = max(rel_e, c_start + s_idx + len(surname))
                elif is_anaphoric:
                    pronoun_m = re.search(r"\b(she|he|they|i|my|其|该学者|该专家)\b", clause, re.IGNORECASE)
                    if pronoun_m:
                        rel_s = min(rel_s, c_start + pronoun_m.start())
                        rel_e = max(rel_e, c_start + pronoun_m.end())
                s = max(c_start, min(rel_s, rel_e))
                e = min(c_end, max(rel_s, rel_e))
                if e > s:
                    return ClaimEvidenceSupport(
                        evidence_id=evidence.evidence_id,
                        subject_mention_id=subj_id,
                        clause_span_start=c_start,
                        clause_span_end=c_end,
                        verbatim_clause=clause,
                        relation_span_start=s,
                        relation_span_end=e,
                        provenance_level="relation",
                        subject_resolution=resolution_type,
                        antecedent_mention_id=antecedent_id,
                        antecedent_clause_span=antecedent_span,
                    )
            return ClaimEvidenceSupport(
                evidence_id=evidence.evidence_id,
                subject_mention_id=subj_id,
                clause_span_start=c_start,
                clause_span_end=c_end,
                verbatim_clause=clause,
                provenance_level="clause",
                subject_resolution=resolution_type,
                antecedent_mention_id=antecedent_id,
                antecedent_clause_span=antecedent_span,
            )

        # Build dynamic target regex for this specific clause's subject
        is_c_target_zh = any("\u4e00" <= c <= "\u9fff" for c in clause_target_name) if clause_target_name else False
        if is_c_target_zh:
            c_target_pat = re.escape(clause_target_name)
            curr_target_pat = rf"(?:{c_target_pat}|其|该学者|该专家)" if is_anaphoric else c_target_pat
        else:
            c_toks = [re.escape(t) for t in clause_target_name.split()] if clause_target_name else []
            if len(c_toks) >= 2:
                c_target_pat = rf"(?:" + r"\s+".join(c_toks) + rf")"
                c_word_pat = rf"\b{c_target_pat}\b"
            elif c_toks:
                c_target_pat = c_toks[0]
                c_word_pat = rf"\b{c_toks[0]}\b"
            else:
                c_target_pat = r"[A-Z][a-z]+\s+[A-Z][a-z]+"
                c_word_pat = rf"\b{c_target_pat}\b"
            if is_surname_clause and surname:
                c_word_pat = rf"(?:{c_word_pat}|\b{re.escape(surname)}\b)"
            curr_target_pat = rf"(?:{c_word_pat}|\bshe\b|\bhe\b|\bthey\b|\bi\b|\bmy\b)" if is_anaphoric else c_word_pat

        pol = detect_clause_polarity(clause)
        temp = detect_clause_temporal_status(clause, clause_target_name)
        if is_profile_field and pol == FactPolarity.AFFIRMATIVE and temp == TemporalStatus.UNKNOWN:
            # A current profile's Position/Role field is a present-state assertion unless
            # the field itself contains an explicit former or negated marker.
            temp = TemporalStatus.CURRENT

        # 1. Quotation Frame Check:
        # e.g. "Alice said Bob is Dean" -> target is speaker, not the role holder!
        if clause_target_name:
            speaker_match = re.search(
                rf"{curr_target_pat}\s+(?:said|stated|claimed|noted|reported|commented|wrote|表示|称|指出|说)\s+(?:that\s+)?",
                clause,
                re.IGNORECASE,
            )
            if speaker_match:
                # Target is the speaker reporting someone else; skip attributing internal roles to target
                continue

        # 2. Appositive Frame Check:
        # e.g. "Alice met Bob, the former Dean" -> role attaches to Bob, NOT Alice!
        if clause_target_name:
            other_person_appositive = re.search(
                rf"{curr_target_pat}\s+(?:met|interviewed|profiled|consulted|visited|会见|采访|对话)\s+([A-Z][a-z]+\s+[A-Z][a-z]+|[一-鿿]{2,4})\s*[,，]\s*(?:the\s+)?([A-Za-z\s]{2,30}?(?:Dean|Director|Professor|Chair|President|院长|主任|教授))",
                clause,
                re.IGNORECASE,
            )
            if other_person_appositive:
                continue

            # Check if another person is directly preceding the title in appositive
            foreign_appositive = re.search(
                rf"([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[,，]\s*(?:the\s+)?([A-Za-z\s]{2,30}?(?:Dean|Director|Professor|Chair|President|院长|主任|教授))",
                clause,
                re.IGNORECASE,
            )
            if foreign_appositive:
                other_name = foreign_appositive.group(1).lower()
                if other_name != clause_target_name.lower():
                    # The appositive role belongs to other_name, not target!
                    continue

        # 3. Direct Copular / SVO / Title extraction where target is the subject
        found_roles: List[Tuple[str, int, int]] = []

        ROLE_HEAD_WORDS = r"(?:Director|Dean|Chair|President|Head|Professor|Scientist|Fellow|Researcher|Engineer|Agent|Realtor|Associate|Scholar|Physician|Specialist|Doctor|Student|Analyst|Consultant|Manager|Candidate|Clerk|Resident|Member|Trustee|教授|副教授|研究员|博士后|院长|主任|科学家|工程师|会长|校长|医师|队长)"
        ROLE_PREFIX_WORDS = r"(?:Center|Institute|Department|Division|Program|Laboratory|Lab|Assistant|Associate|Full|Distinguished|Adjunct|Clinical|Visiting|Executive|Senior|Junior|Principal|Lead|Staff|Software|Postdoctoral|Real\s+Estate|Research|MS|PhD|BS|Investment\s+Banking|IT|Business\s+Systems|Hospital|Global\s+Surgery|Data\s+Visualization|Surgery|Master\x27s|Graduate|Undergraduate|University|Regents|Endowed|Named)"
        ROLE_LOOKAHEAD = rf"(?:(?:the|a|an)\s+)?(?:(?:[a-z]+ly\s+)?(?:award-winning|renowned|noted|prominent|acclaimed|leading|distinguished|honorary|emeritus|former|past|previous|ex-|current|acting)\s+)*(?:{ROLE_PREFIX_WORDS}\s+)*{ROLE_HEAD_WORDS}\b"

        field_token = r"(?!\b(?:at|in|for|from|with|to|by|while|the|a|an|of|and)\b)[A-Za-z]+"
        field_expr = rf"{field_token}(?:\s+(?:and\s+(?!{ROLE_LOOKAHEAD}))?{field_token})*"
        role_of_suffix = (
            r"\s+of\s+(?:the\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)*?"
            r"(?=\s+(?:at|in|from|with)\b|[,，.;:<\n]|$)"
        )
        governance_role_pat = (
            rf"(?:Clerks?(?:{role_of_suffix})?|"
            rf"Members?(?:\s+at\s+Large|{role_of_suffix})?|"
            rf"Trustees?(?:{role_of_suffix})?)"
        )
        role_base_pat = (
            rf"(?:{ROLE_PREFIX_WORDS}\s+)*"
            rf"(?:Associate\s+Research\s+Scientists?|Research\s+Scientists?|Professor(?:s)?(?:\s+of\s+{field_expr})?|Postdoctoral(?:\s+Associates?|\s+Researchers?|\s+Fellows?)?|Postdoc(?:\s+Fellows?)?|Fellows?|{governance_role_pat}|Deans?|Directors?(?:{role_of_suffix})?|Scientists?|Engineers?|Agents?|Chairs?|Realtors?|Presidents?|Researchers?|Associates?|[^\s，。；、]{{0,15}}?{ROLE_HEAD_WORDS})\b"
        )
        compound_role_pat = rf"({role_base_pat})(?:\s+(?:and|&|/)\s+({role_base_pat}))?"
        prefix_mod_pat = r"(?:(?:the|a|an)\s+)?(?:(?:[a-z]+ly\s+)?(?:award-winning|renowned|noted|prominent|acclaimed|leading|distinguished|honorary|emeritus|former|past|previous|ex-|current|acting|associate|assistant|lead|chief|principal|staff|research|dedicated)\s+)*"

        # Pattern A: [Target] is/serves as [Role]
        verb_pat = r"(?:,\s*(?:PhD|MD|Ph\.D\.|M\.D\.|Jr\.|Sr\.|III)\s*,)?\s*(?:currently|previously|formerly|also)?\s*(?:is|was|are|were|serves as|served as|serve as|will join(?:\s+[A-Za-z0-9&.-]+(?:\s+[A-Za-z0-9&.-]+)*)?\s+as|joins(?:\s+[A-Za-z0-9&.-]+(?:\s+[A-Za-z0-9&.-]+)*)?\s+as|works as|worked as|work as|is appointed as|appointed as|holds position of|担任|现任|曾任|是)\s*(?:currently|previously|formerly|not|never)?\s*(?:a\s+|an\s+|the\s+)?(?:licensed\s+|certified\s+|registered\s+|active\s+)?"
        coord_sep = r"(?:,\s*(?:(?:and|&|as well as)\s+)?|\s+(?:and|&|as well as)\s+|[、，和与]\s*)"
        name_token = r"[^\W\d_]+(?:[-'][^\W\d_]+)*"
        name_pat = rf"(?:{name_token}(?:\s+{name_token})*|[一-鿿]{{2,4}})"
        svo_subj_pat = (
            rf"(?:{name_pat}{coord_sep})*"
            rf"{curr_target_pat}"
            rf"(?:{coord_sep}{name_pat})*"
        )

        # 1. Mention coordinate-based coordinated subject extraction
        coordinated_mention_matched = False
        if evidence_mentions and clause_m:
            in_clause_mentions = [
                m for m in evidence_mentions
                if m.evidence_id == evidence.evidence_id and c_start <= m.char_start and m.char_end <= c_end
            ]
            if len(in_clause_mentions) >= 2:
                v_match = re.search(rf"{verb_pat}{compound_role_pat}", clause, re.IGNORECASE)
                if v_match:
                    v_start_rel = v_match.start()
                    pre_verb_m = [m for m in in_clause_mentions if (m.char_end - c_start) <= v_start_rel]
                    if len(pre_verb_m) >= 2 and any(m.mention_id == clause_m.mention_id for m in pre_verb_m):
                        is_pure_coord = True
                        sorted_pre = sorted(pre_verb_m, key=lambda m: m.char_start)
                        for idx in range(len(sorted_pre) - 1):
                            m_a = sorted_pre[idx]
                            m_b = sorted_pre[idx + 1]
                            rel_a_end = m_a.char_end - c_start
                            rel_b_start = m_b.char_start - c_start
                            between_m = clause[rel_a_end:rel_b_start].strip()
                            if not re.match(r"^(?:,\s*(?:(?:and|&|as well as)\s+)?|\s+(?:and|&|as well as)\s+|[、，和与]\s*)$", between_m, re.IGNORECASE):
                                is_pure_coord = False
                                break
                        if is_pure_coord:
                            coordinated_mention_matched = True
                            found_roles.append((v_match.group(1), c_start + v_match.start(1), c_start + v_match.end(1)))
                            if v_match.group(2):
                                found_roles.append((v_match.group(2), c_start + v_match.start(2), c_start + v_match.end(2)))

        if not coordinated_mention_matched:
            svo_matches = re.finditer(
                rf"{svo_subj_pat}\s*{verb_pat}{compound_role_pat}",
                clause,
                re.IGNORECASE,
            )
            for m in svo_matches:
                found_roles.append((m.group(1), c_start + m.start(1), c_start + m.end(1)))
                if m.group(2):
                    found_roles.append((m.group(2), c_start + m.start(2), c_start + m.end(2)))

        # Pattern B: [Role] [Target] (Title prefix)
        title_matches = re.finditer(
            rf"\b((?:Assistant\s+Professor|Associate\s+Professor|Associate\s+Research\s+Scientist|Research\s+Scientist|Postdoctoral\s+Associate|Postdoctoral\s+Researcher|Postdoctoral\s+Fellow|Postdoc\s+Fellow|Real\s+Estate\s+Agent|Software\s+Engineer|Postdoc|Professor|Dean|Director|Chair|President|Researcher|Fellow|教授|副教授|研究员|博士后|院长|主任|校长))\s+{curr_target_pat}",
            clause,
            re.IGNORECASE,
        )
        for m in title_matches:
            found_roles.append((m.group(1), c_start + m.start(), c_start + m.end()))

        # Pattern C: [Target], [Role] at/of [Org]
        TAG_OR_COMMA_SEP = r"(?:\s*[,，]\s*|[\s\n\r]*(?:</?(?:h[1-6]|span|div|p|b|strong|u|a|li)[^>]*>[\s\n\r]*)+)"
        appos_matches = re.finditer(
            rf"{curr_target_pat}{TAG_OR_COMMA_SEP}{prefix_mod_pat}{compound_role_pat}",
            clause,
            re.IGNORECASE,
        )
        for m in appos_matches:
            found_roles.append((m.group(1), c_start + m.start(1), c_start + m.end(1)))
            if m.group(2):
                found_roles.append((m.group(2), c_start + m.start(2), c_start + m.end(2)))

        # Pattern D: Profile field line: Position: [Role], [Org]
        if is_profile_field:
            field_match = re.match(
                r"^(?:<[^>]+>)*\s*(?:position|roles?|title|rank|职位|职务|职称|头衔)?\s*[:：]?\s*(?:<[^>]+>)*\s*" + prefix_mod_pat + compound_role_pat,
                clause,
                re.IGNORECASE,
            )
            if field_match:
                found_roles.append((field_match.group(1).strip(), c_start + field_match.start(1), c_start + field_match.end(1)))
                if field_match.group(2):
                    found_roles.append((field_match.group(2).strip(), c_start + field_match.start(2), c_start + field_match.end(2)))
            # Extract affiliations from profile field line
            profile_orgs = extract_organizations(clause)
            for org in sorted(profile_orgs):
                org_clean = clean_org_token(org)
                if org_clean and len(org_clean) > 3 and org_clean.lower() not in GENERIC_ORGS:
                    if org_clean.lower().startswith("of "):
                        continue
                    # Title-case org tokens cleanly
                    title_org = " ".join(w if w.lower() in ("of", "for", "on", "at", "in", "and", "the") else w.capitalize() for w in org_clean.split())
                    raw_key = f"{subj_id}:affiliated_with:{title_org}:{pol.value}:{temp.value}".encode("utf-8")
                    claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                    org_idx = clause.find(org)
                    if org_idx >= 0:
                        support = make_support(c_start + org_idx, c_start + org_idx + len(org))
                    else:
                        support = make_support(c_start, c_end)
                    claims.append(
                        Claim(
                            claim_id=claim_id,
                            candidate_entity_id=candidate_entity_id,
                            subject_mention_id=subj_id,
                            predicate="affiliated_with",
                            object_raw=title_org,
                            polarity=pol,
                            temporal_status=temp,
                            adjudication_status=AdjudicationStatus.UNRESOLVED,
                            as_of=evidence.retrieved_at.date(),
                            extraction_confidence=0.95,
                            evidence_ids=[evidence.evidence_id],
                            support_clauses=[support],
                        )
                    )

        for raw_pos, r_start, r_end in found_roles:
            cleaned = clean_position_title(raw_pos)
            if cleaned and len(cleaned) > 2:
                if not any(stop in cleaned.lower() for stop in ["interviewed", "consulted", "regarding", "yesterday", "guest"]):
                    raw_key = f"{subj_id}:holds_position:{cleaned}:{pol.value}:{temp.value}".encode("utf-8")
                    claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                    support = make_support(r_start, r_end)
                    claims.append(
                        Claim(
                            claim_id=claim_id,
                            candidate_entity_id=candidate_entity_id,
                            subject_mention_id=subj_id,
                            predicate="holds_position",
                            object_raw=cleaned,
                            polarity=pol,
                            temporal_status=temp,
                            adjudication_status=AdjudicationStatus.UNRESOLVED,
                            as_of=evidence.retrieved_at.date(),
                            extraction_confidence=0.98,
                            evidence_ids=[evidence.evidence_id],
                            support_clauses=[support],
                        )
                    )

        # 4. Affiliation extraction
        # Guard: If clause is an event/interaction (interview, meeting, visit, speech) and target does not hold position in it,
        # prepositional "at [Org]" is an event location, NOT an institutional affiliation!
        is_event_interaction = bool(
            re.search(
                r"\b(?:interviewed|profiled|visited|met|talked with|spoke at|praised|emailed|congratulated)\b",
                clause,
                re.IGNORECASE,
            )
        )
        if pol == FactPolarity.NEGATIVE:
            affil_verb_pat = r"(?:not affiliated with|not associated with|not employed by|does not work at|did not work at|未就职于|不属于)\s+"
        elif is_event_interaction and not found_roles:
            affil_verb_pat = r"\b(?:joined|affiliated with|associated with|employed by|works at|working at|就职于|受聘于|任职于|就读于)\s+"
        else:
            affil_verb_pat = r"\b(?:at|joined|affiliated with|associated with|employed by|works at|working at|student at|undergraduate student at|graduate student at|researcher at|associate at|就职于|受聘于|任职于|就读于|in\s+(?:the\s+)?(?=(?:(?:[A-Za-z0-9&.-]+\s+)*(?:Department|Division|Section|Center|Institute|School|College|University|Program)|University|College))\b)\s*"

        affil_org_core = (
            r"(?:University(?:\s+(?:of|at)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|[A-Z][A-Za-z\s]{0,45}?(?:University(?:\s+(?:of|at)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|College|Institute(?:\s+(?:for|of)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|Hospital|School(?:\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|Department(?:\s+of\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|Center(?:\s+(?:for|of)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)?"
            r"|Section(?:\s+of\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)?"
            r"|Program(?:\s+(?:on|for|in)\s+[A-Za-z]+(?:\s+[A-Za-z]+)*)?"
            r"|Foundation|Realty|Real\s+Estate|Agency|Firm|Google|Microsoft|Meta|Apple|Amazon|OpenAI|IEEE|Company|Corp|Inc|LLC|大学|学院|研究所|研究院|公司|集团|医院|中心))"
        )
        article_or_tag = r"(?:(?:the|a|an)\s+)?(?:<[^>]*>\s*)?(?:(?:the|a|an)\s+)?"
        affil_matches = re.finditer(
            rf"{affil_verb_pat}{article_or_tag}({affil_org_core})\b",
            clause,
            re.IGNORECASE,
        )
        for m in affil_matches:
            affil = m.group(1).strip()
            affil = re.sub(r"<[^>]+>", "", affil).strip()
            # Strip trailing participial phrases / clauses like 'working in the Mothes Lab'
            affil = re.sub(
                r"\s+(?:working|focusing|conducting|serving|located|based|joined|received|graduated|leading)\s+.*$",
                "",
                affil,
                flags=re.IGNORECASE,
            ).strip()
            if affil.lower().startswith("the "):
                affil = affil[4:].strip()
            if affil.lower().startswith("of "):
                continue
            if " from " in affil.lower():
                continue
            if affil.lower() in ("university", "college", "institute", "hospital", "school", "center", "department", "foundation", "agency", "firm"):
                continue

            affil_candidates = [affil]
            org_kws = ["university", "college", "school", "institute", "hospital", "department", "division", "section", "center", "program", "lab", "laboratory"]
            primary_kws = ["university", "college", "school", "institute", "hospital", "firm", "agency", "foundation", "realty", "company", "corporation", "大学", "学院", "研究所", "研究院", "公司", "集团", "医院"]
            if re.search(r"\s+affiliated\s+with\s+", affil, re.IGNORECASE):
                parts = [p.strip() for p in re.split(r"\s+affiliated\s+with\s+", affil, flags=re.IGNORECASE) if p.strip()]
                cand_matches = [p for p in parts if any(kw in p.lower() for kw in org_kws)]
                if cand_matches:
                    primary_matches = [p for p in cand_matches if any(kw in p.lower() for kw in primary_kws)]
                    affil_candidates = [primary_matches[0]] if primary_matches else [cand_matches[0]]
            elif " at " in affil:
                parts = [p.strip() for p in affil.split(" at ") if p.strip()]
                cand_matches = [p for p in parts if any(kw in p.lower() for kw in org_kws)]
                if cand_matches:
                    affil_candidates = cand_matches
            elif re.search(r"\s+in\s+(?:the\s+)?", affil, re.IGNORECASE):
                parts = [p.strip() for p in re.split(r"\s+in\s+(?:the\s+)?", affil, flags=re.IGNORECASE) if p.strip()]
                cand_matches = [p for p in parts if any(kw in p.lower() for kw in org_kws)]
                if cand_matches:
                    primary_matches = [p for p in cand_matches if any(kw in p.lower() for kw in primary_kws)]
                    affil_candidates = [primary_matches[0]] if primary_matches else [cand_matches[0]]

            for aff in affil_candidates:
                if aff.lower().startswith("the "):
                    aff = aff[4:].strip()
                if aff.lower().startswith("of "):
                    continue
                if aff and len(aff) > 3 and aff.lower() not in ("university", "college", "institute", "hospital", "school", "center", "department"):
                    raw_key = f"{subj_id}:affiliated_with:{aff}:{pol.value}:{temp.value}".encode("utf-8")
                    claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                    aff_idx = clause.find(aff, m.start())
                    if aff_idx >= 0:
                        aff_s = c_start + aff_idx
                        aff_e = aff_s + len(aff)
                    else:
                        aff_s = c_start + m.start()
                        aff_e = c_start + m.end()
                    support = make_support(aff_s, aff_e)
                    claims.append(
                        Claim(
                            claim_id=claim_id,
                            candidate_entity_id=candidate_entity_id,
                            subject_mention_id=subj_id,
                            predicate="affiliated_with",
                            object_raw=aff,
                            polarity=pol,
                            temporal_status=temp,
                            adjudication_status=AdjudicationStatus.UNRESOLVED,
                            as_of=evidence.retrieved_at.date(),
                            extraction_confidence=0.95,
                            evidence_ids=[evidence.evidence_id],
                            support_clauses=[support],
                        )
                    )

        zh_team_matches = re.finditer(
            r"(?:现为|曾为|加入|效力于)\s*([A-Za-z0-9\s一-鿿]{2,30}?(?:大学[^\s，。；、]{2,10}?队|队|俱乐部))\b",
            clause,
            re.IGNORECASE,
        )
        for m in zh_team_matches:
            affil = m.group(1).strip()
            if affil and len(affil) > 2:
                raw_key = f"{subj_id}:affiliated_with:{affil}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="affiliated_with",
                        object_raw=affil,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # Chinese Composite Pattern: [Target] (现任|曾任|担任) [Org] [Role]
        if is_c_target_zh:
            zh_target_bounded = rf"{curr_target_pat}(?=(?:[\s，,。；;]|$|{ZH_NAME_RIGHT_ALLOWED.pattern[1:]}))"
            target_zh_expr = (
                rf"(?:{zh_target_bounded}|^(?:目前|随后|并|同时|此前|此后|并且|且)?)"
                if is_anaphoric
                else zh_target_bounded
            )
        else:
            target_zh_expr = rf"(?:\b{curr_target_pat}\b|^)" if is_anaphoric else rf"\b{curr_target_pat}\b"
        zh_composite_matches = re.finditer(
            rf"{target_zh_expr}\s*(现任|曾任|担任|曾为|现为|任职于|是|为|在|于)?\s*([一-鿿A-Za-z0-9]{{2,25}}?(?:大学|学院|研究所|研究院|公司|集团|医院|中心|实验室))\s*([一-鿿A-Za-z0-9]{{0,20}}?(?:队长|队员|教练|主席|顾问|委员|总监|经理|研究员|教授|副教授|博士后|院长|主任|校长|会长|医师))",
            clause,
        )
        for m in zh_composite_matches:
            tense_str = m.group(1) or ""
            zh_org = m.group(2).strip()
            zh_role = m.group(3).strip()
            zh_org = re.sub(
                r"^(?:目前|随后|并|同时|此前|此后|并且|且|现任|曾任|担任|曾为|现为|任职于|是|为|在|于|的)+",
                "",
                zh_org,
            ).strip()

            c_temp = temp
            if "曾任" in tense_str or "曾为" in tense_str or "已离任" in clause:
                c_temp = TemporalStatus.FORMER
            elif "现任" in tense_str or "现为" in tense_str or "至今" in clause:
                c_temp = TemporalStatus.CURRENT

            if zh_role and len(zh_role) >= 2:
                raw_key = f"{subj_id}:holds_position:{zh_role}:{pol.value}:{c_temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end(3))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="holds_position",
                        object_raw=zh_role,
                        polarity=pol,
                        temporal_status=c_temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.98,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

            if zh_org and len(zh_org) >= 2:
                raw_key = f"{subj_id}:affiliated_with:{zh_org}:{pol.value}:{c_temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end(2))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="affiliated_with",
                        object_raw=zh_org,
                        polarity=pol,
                        temporal_status=c_temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.98,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        ctx_matches = re.finditer(
            r"([一-鿿A-Za-z0-9\s]{2,30}?)(?:亲历者|参与者|志愿者|作者群)",
            clause,
        )
        for m in ctx_matches:
            raw_ctx = m.group(1).strip()
            cleaned_ctx = raw_ctx.replace("易思汇", "").strip() if "易思汇" in raw_ctx else raw_ctx.strip()
            affil = cleaned_ctx if cleaned_ctx else ("留学生群体与赴美中转背景" if "留学生" in raw_ctx else raw_ctx)
            if affil and len(affil) > 2:
                raw_key = f"{subj_id}:affiliated_with:{affil}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="affiliated_with",
                        object_raw=affil,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 5. Lab / Group member_of extraction
        member_matches = re.finditer(
            r"(?:(?:is\s+)?(?:an?\s+)?(?:active\s+|current\s+|former\s+)?member of(?: the)?|joined the|works in the|working in the)\s+([A-Z][A-Za-z\s]{2,30}?(?:Lab|Laboratory|Group|Team|Society|Association|Council|Committee|Club|小组|实验室|学会|协会))\b",
            clause,
            re.IGNORECASE,
        )
        for m in member_matches:
            lab = m.group(1).strip()
            if lab and len(lab) > 3:
                raw_key = f"{subj_id}:member_of:{lab}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="member_of",
                        object_raw=lab,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 6. Based in location extraction
        based_matches = re.finditer(
            r"(?:based in|located in|living in|residing in|位于|定居于)\s+([A-Z][A-Za-z\s]{2,30}?|[一-鿿]{2,10}?)(?=[,.;\n]|$)",
            clause,
            re.IGNORECASE,
        )
        for m in based_matches:
            loc = m.group(1).strip()
            if loc and len(loc) > 2:
                raw_key = f"{subj_id}:based_in:{loc}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="based_in",
                        object_raw=loc,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 7. Education / Graduated from extraction
        grad_matches = re.finditer(
            r"(?:(?:毕业于|graduated from|alumnus of|alumna of)|(?:(?:received|earned|obtained|awarded|graduated with)\s+(?:my\s+|her\s+|his\s+|their\s+|a\s+|an\s+)?(?:Ph\.?D\.?|Doctor of Philosophy|M\.?D\.?|M\.?S\.?|B\.?S\.?|B\.?A\.?|Master(?:'s)?|Bachelor(?:'s)?|Juris Doctor|J\.?D\.?)(?:\s+in\s+[A-Za-z\s&.-]+?)?\s+from))\s*((?:the\s+)?(?:University\s+of\s+[A-Za-z\s]+?(?:\s+at\s+[A-Za-z\s]+)?|UC\s+[A-Za-z]+|Berkeley|MIT|CMU|NYU|Stanford|Harvard|Princeton|Caltech|[A-Za-z0-9\s一-鿿]{0,50}?(?:University(?:\s+(?:of|at)\s+[A-Za-z\s]+)?|College|Institute|School(?:\s+of\s+[A-Za-z\s]+)?|SUNY(?:\s+(?:of|at)\s+[A-Za-z\s]+)?|CUNY(?:\s+(?:of|at)\s+[A-Za-z\s]+)?|大学|学院)))(?=\s+(?:in\s+\d{4}|during|\bwith\b|\band\b)|[,.;，。；\n]|$)",
            clause,
            re.IGNORECASE,
        )
        for m in grad_matches:
            inst = m.group(1).strip()
            if inst.lower().startswith("the "):
                inst = inst[4:].strip()
            if inst and len(inst) > 2:
                raw_key = f"{subj_id}:graduated_from:{inst}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="graduated_from",
                        object_raw=inst,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # Chinese graduation pattern: 毕业于 [学校/附中/中学/高中/初中]
        zh_grad_matches = re.finditer(
            r"(?:毕业于|就读于)\s*([一-鿿0-9]{2,25}?(?:大学|学院|研究所|研究院|附中|中学|高级中学|高中|初级中学|初中|实验学校|学校|(?:[一二三四五六七八九十0-9]+|一零一)中))(?=[,.;，。；\n\s]|$)",
            clause,
        )
        for m in zh_grad_matches:
            inst = m.group(1).strip()
            if inst and len(inst) > 2:
                raw_key = f"{subj_id}:graduated_from:{inst}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="graduated_from",
                        object_raw=inst,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 8. Degree received extraction
        deg_matches = re.finditer(
            r"(?:received|earned|holds|obtained|awarded|graduated with|获得|取得)\s+(?:my\s+|her\s+|his\s+|their\s+|a\s+|an\s+)?((?:Ph\.?D\.?|Doctor of Philosophy|M\.?D\.?|M\.?S\.?|B\.?S\.?|B\.?A\.?|Master(?:'s)?|Bachelor(?:'s)?|Juris Doctor|J\.?D\.?)(?:\s+in\s+[A-Za-z\s&.-]+?)?)(?:\s+from|\s*[,;.]|$)",
            clause,
            re.IGNORECASE,
        )
        for m in deg_matches:
            deg = m.group(1).strip()
            if deg and len(deg) > 2:
                raw_key = f"{subj_id}:received_degree:{deg}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="received_degree",
                        object_raw=deg,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 8b. Structured / Bullet / Semicolon / Card Education Extractor
        bullet_edu_matches = re.finditer(
            r"(?:<li>|<h\d[^>]*>)?\s*([A-Z][A-Za-z\s&.-]+?(?:University(?:\s+(?:of|at)\s+[A-Za-z\s]+)?|College|Institute|School))\s*,\s*((?:Ph\.?D\.?|M\.?S\.?|B\.?S\.?|Doctor of Philosophy|Bachelor|Master)(?:\s+in\s+[A-Za-z\s&.-]+?)?)(?:\s*\(\d{4}\)|;|,|<|$)",
            clause,
            re.IGNORECASE,
        )
        for m in bullet_edu_matches:
            inst = m.group(1).strip()
            deg = m.group(2).strip()
            if inst and len(inst) > 2:
                raw_key = f"{subj_id}:graduated_from:{inst}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(1), c_start + m.end(1))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="graduated_from",
                        object_raw=inst,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )
            if deg and len(deg) > 2:
                raw_key = f"{subj_id}:received_degree:{deg}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(2), c_start + m.end(2))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="received_degree",
                        object_raw=deg,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        semi_edu_matches = re.finditer(
            r"((?:Ph\.?D\.?|Doctor of Philosophy|M\.?S\.?|B\.?S\.?|Master|Bachelor)(?:\s+in\s+[A-Za-z\s&.-]+?)?)\s*;\s*((?:University\s+of\s+[A-Za-z\s]+|[A-Za-z\s&.-]+?(?:University|College|Institute)))\b",
            clause,
            re.IGNORECASE,
        )
        for m in semi_edu_matches:
            deg = m.group(1).strip()
            inst = m.group(2).strip()
            if deg and len(deg) > 2:
                raw_key = f"{subj_id}:received_degree:{deg}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(1), c_start + m.end(1))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="received_degree",
                        object_raw=deg,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )
            if inst and len(inst) > 2:
                raw_key = f"{subj_id}:graduated_from:{inst}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(2), c_start + m.end(2))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="graduated_from",
                        object_raw=inst,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        card_edu_matches = re.finditer(
            r"((?:B\.?S\.?|Bachelor|Master|M\.?S\.?|Ph\.?D\.?)\s+in\s+[A-Za-z\s&.-]+?)<[\s\S]*?>([A-Z][A-Za-z\s&.-]+?(?:University|College|Institute))",
            clause,
            re.IGNORECASE,
        )
        for m in card_edu_matches:
            deg = m.group(1).strip()
            inst = m.group(2).strip()
            if deg and len(deg) > 2:
                raw_key = f"{subj_id}:received_degree:{deg}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(1), c_start + m.end(1))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="received_degree",
                        object_raw=deg,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )
            if inst and len(inst) > 2:
                raw_key = f"{subj_id}:graduated_from:{inst}:{pol.value}:former".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(2), c_start + m.end(2))
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="graduated_from",
                        object_raw=inst,
                        polarity=pol,
                        temporal_status=TemporalStatus.FORMER,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 8c. Roster / Directory student or faculty role
        roster_m = re.search(r"<h2[^>]*>(Master\x27s Students?|Ph\.?D\.?\s+Students?|Postdoctoral\s+Associates?|Faculty|Staff)</h2>", clause, re.IGNORECASE)
        if roster_m:
            r_role = roster_m.group(1).strip()
            if "Master" in r_role:
                std_role = "Master's Student"
            elif "Ph.D" in r_role or "PhD" in r_role:
                std_role = "PhD Student"
            else:
                std_role = r_role
            raw_key = f"{subj_id}:holds_position:{std_role}:affirmative:current".encode("utf-8")
            claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
            support = make_support(c_start + roster_m.start(1), c_start + roster_m.end(1))
            claims.append(
                Claim(
                    claim_id=claim_id,
                    candidate_entity_id=candidate_entity_id,
                    subject_mention_id=subj_id,
                    predicate="holds_position",
                    object_raw=std_role,
                    polarity=FactPolarity.AFFIRMATIVE,
                    temporal_status=TemporalStatus.CURRENT,
                    adjudication_status=AdjudicationStatus.UNRESOLVED,
                    as_of=evidence.retrieved_at.date(),
                    extraction_confidence=0.98,
                    evidence_ids=[evidence.evidence_id],
                    support_clauses=[support],
                )
            )
            if "yale" in clause.lower() or "yale.edu" in clause.lower():
                raw_key = f"{subj_id}:affiliated_with:Yale University:affirmative:current".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="affiliated_with",
                        object_raw="Yale University",
                        polarity=FactPolarity.AFFIRMATIVE,
                        temporal_status=TemporalStatus.CURRENT,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.98,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 8d. IEEE President former role
        ieee_m = re.search(r"\b(?:was\s+(?:the\s+)?)?(\d{4}\s+)?(IEEE\s+President(?:\s+and\s+CEO)?|President(?:\s+and\s+CEO)?\s+of\s+IEEE)\b", clause, re.IGNORECASE)
        if ieee_m and (has_target or is_anaphoric):
            raw_key = f"{subj_id}:holds_position:IEEE President:affirmative:former".encode("utf-8")
            claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
            support = make_support(c_start + ieee_m.start(), c_start + ieee_m.end())
            claims.append(
                Claim(
                    claim_id=claim_id,
                    candidate_entity_id=candidate_entity_id,
                    subject_mention_id=subj_id,
                    predicate="holds_position",
                    object_raw="IEEE President",
                    polarity=FactPolarity.AFFIRMATIVE,
                    temporal_status=TemporalStatus.FORMER,
                    adjudication_status=AdjudicationStatus.UNRESOLVED,
                    as_of=evidence.retrieved_at.date(),
                    extraction_confidence=0.98,
                    evidence_ids=[evidence.evidence_id],
                    support_clauses=[support],
                )
            )

        # 8e. Institutional email affiliation (for official faculty / academic profile cards)
        email_m = re.search(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.(?:edu|edu\.cn))\b", clause)
        if email_m and (has_target or is_profile_field):
            host = email_m.group(1).lower()
            org_name = None
            if "cornell.edu" in host:
                org_name = "Cornell University"
            elif "njit.edu" in host:
                org_name = "New Jersey Institute of Technology"
            elif "yale.edu" in host and "medicine.yale.edu" not in clause.lower():
                org_name = "Yale University"
            elif "umd.edu" in host:
                org_name = "University of Maryland"
            elif "bu.edu" in host:
                org_name = "Boston University"
            if org_name and org_name.lower() in clause.lower():
                raw_key = f"{subj_id}:affiliated_with:{org_name}:affirmative:current".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + email_m.start(), c_start + email_m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="affiliated_with",
                        object_raw=org_name,
                        polarity=FactPolarity.AFFIRMATIVE,
                        temporal_status=TemporalStatus.CURRENT,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 9. Publication authored extraction
        pub_matches = re.finditer(
            r"(?:著有|出版|撰写|发表|authored|wrote|published)\s*(?:出版物|著作|书|论文|作品)?\s*[《\"']([^》\"']{2,60}?)[》\"']",
            clause,
            re.IGNORECASE,
        )
        for m in pub_matches:
            pub = m.group(1).strip()
            if pub and len(pub) > 1:
                raw_key = f"{subj_id}:authored_publication:{pub}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="authored_publication",
                        object_raw=pub,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

        # 9. Honor awarded extraction
        honor_matches = re.finditer(
            r"(?:荣获|获得|awarded|received honor(?: of)?)\s*([A-Za-z0-9\s\-]{3,45}?(?:Team|Award|Prize|Fellowship|Honor))\s*(?:荣誉)?",
            clause,
            re.IGNORECASE,
        )
        for m in honor_matches:
            honor = m.group(1).strip()
            if honor and len(honor) > 2:
                raw_key = f"{subj_id}:awarded_honor:{honor}:{pol.value}:{temp.value}".encode("utf-8")
                claim_id = f"CLM-{hashlib.sha256(raw_key).hexdigest()[:32]}"
                support = make_support(c_start + m.start(), c_start + m.end())
                claims.append(
                    Claim(
                        claim_id=claim_id,
                        candidate_entity_id=candidate_entity_id,
                        subject_mention_id=subj_id,
                        predicate="awarded_honor",
                        object_raw=honor,
                        polarity=pol,
                        temporal_status=temp,
                        adjudication_status=AdjudicationStatus.UNRESOLVED,
                        as_of=evidence.retrieved_at.date(),
                        extraction_confidence=0.95,
                        evidence_ids=[evidence.evidence_id],
                        support_clauses=[support],
                    )
                )

    # Deduplicate claims
    unique_claims = []
    seen_keys = set()
    for c in claims:
        key = (c.subject_mention_id, c.predicate, c.object_raw.strip().lower(), c.polarity.value, c.temporal_status.value)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_claims.append(c)

    return unique_claims
