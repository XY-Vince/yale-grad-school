"""Single shared parser for extracting verified person-institution affiliations from HTML <title> elements."""

from __future__ import annotations

import html
import re
from typing import Callable, Optional, Tuple


import unicodedata


def normalize_person_title_name(name: str) -> str:
    """Normalize person name for strict identity comparison matching core attribution rules."""
    norm = unicodedata.normalize("NFKC", html.unescape(name or "")).strip().casefold()
    norm = re.sub(r"^(?:prof(?:essor|\.)?|dr\.|mr\.|ms\.|mrs\.)\s+", "", norm)
    norm = re.sub(r"^(?:教授|博士|院士|主任|老师|学者|会长|校长|院长)\s*", "", norm)
    norm = re.sub(r"\s*(?:教授|博士|院士|主任|老师|学者|会长|校长|院长|先生|女士)$", "", norm)
    return " ".join(norm.split())


def default_person_matcher(segment: str, target_name: str) -> bool:
    """Strict equality of normalized full names; rejects partial token overlap or substrings."""
    norm_seg = normalize_person_title_name(segment)
    norm_target = normalize_person_title_name(target_name)
    return bool(norm_seg and norm_target and norm_seg == norm_target)


# Tier 1: Canonical institution head nouns (English and CJK)
TIER1_PARENT = re.compile(
    r"\b(?:University|State University|Institute of Technology|Polytechnic|A&M|MIT|CMU|NYU|Caltech)\b|大学",
    re.IGNORECASE,
)

TIER1_ALL = re.compile(
    r"\b(?:University|State University|Institute of Technology|Polytechnic|A&M|MIT|CMU|NYU|Caltech|College|School|Institute|Academy|Hospital|Conservatory|Laboratory|Foundation|Center|Centre)\b|"
    r"(?:School of Medicine|College of Medicine|Faculty of Medicine|Medical Center|Medical Centre)|"
    r"(?:大学|学院|研究所|研究院|医院|科学院|工程院|高等专科学校)",
    re.IGNORECASE,
)

# Reject naked disciplines that lack an institutional head noun
NAKED_DISCIPLINE_PATTERN = re.compile(
    r"^(?:\s*|\b)(?:Medicine|English|Physics|Chemistry|Biology|Mathematics|History|Economics|Law|Art|Music)(?:\s*|\b)$",
    re.IGNORECASE,
)

# Section filler / non-institution labels (Tier 2)
TIER2_SECTION_FILLER = re.compile(
    r"^(?:\s*|\b)(?:Faculty|Staff|People|Directory|Profile|Biography|About Us|Contact|Faculty Directory|Staff Directory|Overview|Home|News|Events|Department of [^|｜—–•·:]+|Division of [^|｜—–•·:]+)(?:\s*|\b)$",
    re.IGNORECASE,
)

# Multi-campus patterns with hyphens that must NOT be split
CAMPUS_HYPHEN_PATTERN = re.compile(
    r"\b(?:University of [A-Za-z\s]+-\s*[A-Za-z\s]+|[A-Za-z\s]+A&M\s*-\s*[A-Za-z\s]+|[A-Za-z\s]+State University\s*-\s*[A-Za-z\s]+)\b",
    re.IGNORECASE,
)

# Primary delimiters:
# 1. Pipe: | or fullwidth ｜
# 2. Double colon: :: (grouped as (?:::|...) to avoid splitting on single colon)
# 3. Em-dash: — or En-dash: –
# 4. Spaced middle dots: \s[•·]\s (requires surrounding spaces to preserve unspaced CJK names like 约翰·史密斯)
PRIMARY_DELIMITER_PATTERN = re.compile(
    r"\s*(?:(?:::|[|｜—–])|\s[•·]\s)\s*"
)

# Fallback delimiter:
# Spaced hyphen \s+-\s+ (only when primary delimiters are absent and campus pattern is preserved)
FALLBACK_HYPHEN_PATTERN = re.compile(r"\s+-\s+")


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def extract_institution_from_title(
    title_raw: str,
    target_name: str,
    matcher: Optional[Callable[[str, str], bool]] = None,
) -> Tuple[Optional[str], Optional[str], Optional[Tuple[int, int]]]:
    """
    Parses an HTML title string to extract (matched_person_name, object_raw, span_in_title_raw).
    
    Invariants:
    1. If matched, object_raw is a VERBATIM contiguous substring of title_raw.
    2. object_raw contains NO delimiters (| :: — – • ·).
    3. Normalization is applied ONLY to internal candidate segments for scoring/matching,
       never to mutate object_raw in place.
    4. If no valid person-institution pair exists, returns (None, None, None).
    """
    if not title_raw or not target_name:
        return None, None, None

    # Strip inner HTML tags if full <title>...</title> snippet is passed
    inner_match = re.search(r"<title\b[^>]*>(?P<inner>.*?)</title>", title_raw, re.IGNORECASE | re.DOTALL)
    search_context = inner_match.group("inner") if inner_match else title_raw
    search_offset = inner_match.start("inner") if inner_match else 0

    clean_context = _clean_whitespace(_strip_html_tags(search_context))
    if not clean_context:
        return None, None, None

    # Step 1: Split on delimiters
    has_primary = bool(PRIMARY_DELIMITER_PATTERN.search(clean_context))
    if has_primary:
        segments = [s.strip() for s in PRIMARY_DELIMITER_PATTERN.split(clean_context) if s.strip()]
    else:
        # Fallback to spaced hyphen if present and not purely inside a campus pattern
        if FALLBACK_HYPHEN_PATTERN.search(clean_context) and not CAMPUS_HYPHEN_PATTERN.fullmatch(clean_context):
            segments = [s.strip() for s in FALLBACK_HYPHEN_PATTERN.split(clean_context) if s.strip()]
        else:
            segments = [clean_context]

    if len(segments) < 2:
        return None, None, None

    # Step 2: Identify target person segment
    matched_person_segments: list[str] = []
    other_segments: list[str] = []
    match_fn = matcher or default_person_matcher

    for seg in segments:
        seg_norm = html.unescape(seg)
        if match_fn(seg_norm, target_name) or match_fn(seg, target_name):
            matched_person_segments.append(seg)
        else:
            other_segments.append(seg)

    # Exactly one segment must match target name; zero or ambiguous multiple matches reject
    if len(matched_person_segments) != 1:
        return None, None, None

    matched_person = matched_person_segments[0]

    # Step 3: Filter and tier candidate institution segments
    valid_institutions: list[str] = []
    for seg in other_segments:
        # Reject section filler
        if TIER2_SECTION_FILLER.match(seg):
            continue
        # Reject naked discipline
        if NAKED_DISCIPLINE_PATTERN.match(seg):
            continue
        # Must match Tier 1 institution head nouns
        if TIER1_ALL.search(seg):
            valid_institutions.append(seg)

    if not valid_institutions:
        return None, None, None

    # Step 4: Precedence: prefer parent University / Institute over subdivision
    chosen_segment = valid_institutions[0]
    parent_matches = [inst for inst in valid_institutions if TIER1_PARENT.search(inst)]
    if parent_matches:
        chosen_segment = parent_matches[0]

    # Step 5: Locate verbatim span in title_raw (M1 Invariant: assert object_raw in title_raw)
    # The chosen_segment was derived by splitting clean_context. Find its exact verbatim match in search_context
    raw_pos = search_context.find(chosen_segment)
    if raw_pos == -1:
        # Try unescaped form if HTML entities differed
        unescaped_seg = html.unescape(chosen_segment)
        raw_pos = search_context.find(unescaped_seg)
        if raw_pos != -1:
            chosen_segment = unescaped_seg
        else:
            # Token-slice fallback in search_context
            tokens = chosen_segment.split()
            if tokens and tokens[0] in search_context and tokens[-1] in search_context:
                tok_start = search_context.find(tokens[0])
                tok_end = search_context.find(tokens[-1], tok_start) + len(tokens[-1])
                candidate_slice = search_context[tok_start:tok_end]
                if _clean_whitespace(candidate_slice) == _clean_whitespace(chosen_segment):
                    chosen_segment = candidate_slice
                    raw_pos = tok_start

    if raw_pos == -1 or chosen_segment not in title_raw:
        return None, None, None

    abs_start = search_offset + raw_pos
    abs_end = abs_start + len(chosen_segment)
    object_raw = title_raw[abs_start:abs_end]

    # Invariants verification
    if not (object_raw in title_raw):
        return None, None, None
    if any(delim in object_raw for delim in ("|", "｜", "::", "—", "–")):
        return None, None, None

    return matched_person, object_raw, (abs_start, abs_end)
