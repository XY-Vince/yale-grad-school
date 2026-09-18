"""
Structured DOM / JSON-LD / Biographical Content Locator (V4.6.1).
Scans HTML payloads to identify structured Person/Profile metadata,
academic profile containers, headings, and biography blocks.
Extracts Evidence slices with exact character offsets strictly matching
the underlying WARC payload.
"""

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple
from urllib.parse import urlsplit

from models.schemas import (
    Evidence,
    EvidenceLocator,
    LocatorType,
    SourceQualityClass,
)


def _is_domain_or_subdomain(hostname: str, domain: str) -> bool:
    if not hostname or not domain:
        return False
    return hostname == domain or hostname.endswith("." + domain)


def classify_source_quality(url: str) -> SourceQualityClass:
    """
    Classifies source quality based on URL and domain authority:
    - CLASS_A: Official government, educational institutions (.edu, .gov, .ac.uk), official registries.
    - CLASS_B: Reputable media, peer-reviewed journals, verified research databases (pubmed, nature, etc.).
    - CLASS_C: User-generated content, code hosting (github), social profiles (linkedin, twitter/x), personal blogs, unknown.
    """
    if not url:
        return SourceQualityClass.CLASS_C

    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").lower()
    except Exception:
        return SourceQualityClass.CLASS_C

    if not hostname:
        return SourceQualityClass.CLASS_C

    # 1. User-generated / social / code hosting profiles -> CLASS_C
    class_c_domains = [
        "github.com",
        "github.io",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "medium.com",
        "blogspot.com",
        "wordpress.com",
    ]
    if any(_is_domain_or_subdomain(hostname, d) for d in class_c_domains):
        return SourceQualityClass.CLASS_C

    # 2. Peer-reviewed scientific databases / high-reputation publishers -> CLASS_B
    # Evaluated BEFORE generic .gov so that pubmed.ncbi.nlm.nih.gov is classified as CLASS_B
    class_b_domains = [
        "pubmed.ncbi.nlm.nih.gov",
        "ncbi.nlm.nih.gov",
        "nature.com",
        "sciencedirect.com",
        "doi.org",
        "springer.com",
        "wiley.com",
        "cell.com",
    ]
    if any(_is_domain_or_subdomain(hostname, d) for d in class_b_domains):
        return SourceQualityClass.CLASS_B

    # 3. Official educational / governmental / academic domains -> CLASS_A
    class_a_suffixes = [".edu", ".gov", ".ac.uk", ".gov.cn", ".edu.cn"]
    if any(hostname.endswith(sfx) for sfx in class_a_suffixes):
        return SourceQualityClass.CLASS_A

    # Unknown / unverified sources default to CLASS_C
    return SourceQualityClass.CLASS_C


def _build_name_regex(name: str) -> Optional[re.Pattern]:
    clean = name.strip()
    if not clean:
        return None
    if any("\u4e00" <= c <= "\u9fff" for c in clean):
        pat = r"\s*".join(re.escape(c) for c in clean)
    else:
        tokens = [re.escape(t) for t in clean.split()]
        if not tokens:
            return None
        pat = r"\b" + r"\s+".join(tokens) + r"\b"
    return re.compile(pat, re.IGNORECASE)


def locate_evidence_slices(
    html_text: str,
    target_name: str,
    aliases: Optional[List[str]] = None,
    source_id: str = "SRC-UNKNOWN",
    raw_payload_sha256: str = "0000",
    url: str = "",
    source_quality_class: Optional[SourceQualityClass] = None,
) -> List[Evidence]:
    """
    Extracts high-density biographical and profile evidence slices from HTML.
    Guarantees that html_text[char_start:char_end] == verbatim_excerpt.
    """
    if not html_text or not target_name:
        return []

    aliases = aliases or []
    all_names = [target_name] + [a for a in aliases if a]

    # Include honorific variants if name has first & last
    t_tokens = target_name.strip().split()
    if len(t_tokens) >= 2 and t_tokens[-1].isalpha():
        last_name = t_tokens[-1]
        for prefix in ["Dr.", "Prof.", "Professor"]:
            h_name = f"{prefix} {last_name}"
            if h_name not in all_names:
                all_names.append(h_name)

    name_patterns = [p for p in (_build_name_regex(n) for n in all_names) if p is not None]
    if not name_patterns:
        return []

    evidence_items: List[Evidence] = []
    seen_spans: List[Tuple[int, int]] = []
    seen_content_hashes: Set[str] = set()
    eff_quality = source_quality_class or classify_source_quality(url)

    def span_overlaps(s: int, e: int) -> bool:
        for os, oe in seen_spans:
            inter = max(0, min(e, oe) - max(s, os))
            if inter > 0.5 * min(e - s, oe - os):
                return True
        return False

    def add_evidence(s_off: int, e_off: int, selector: str) -> None:
        if s_off < 0 or e_off > len(html_text) or s_off >= e_off:
            return
        if span_overlaps(s_off, e_off):
            return
        excerpt = html_text[s_off:e_off]
        c_hash = hashlib.sha256(excerpt.strip().encode("utf-8")).hexdigest()
        if c_hash in seen_content_hashes:
            return
        seen_content_hashes.add(c_hash)
        seen_spans.append((s_off, e_off))
        ev_id = f"EVI-{raw_payload_sha256[:8]}-{len(evidence_items):02d}"
        ev = Evidence(
            evidence_id=ev_id,
            source_id=source_id,
            verbatim_excerpt=excerpt,
            locator=EvidenceLocator(locator_type=LocatorType.CSS, selector_or_page=selector),
            retrieved_at=datetime.now(timezone.utc),
            source_quality_class=eff_quality,
            raw_payload_sha256=raw_payload_sha256,
            char_start=s_off,
            char_end=e_off,
        )
        evidence_items.append(ev)

    # Strategy 1: JSON-LD Person / Profile metadata (handles type="application/ld+json" or "&#x2B;")
    json_ld_pat = re.compile(
        r'<script[^>]*type=["\']application/ld(?:\+|&#x2B;|%2B)json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in json_ld_pat.finditer(html_text):
        inner = m.group(1)
        if any(pat.search(inner) for pat in name_patterns):
            # Prefer targeted person description slice inside the JSON-LD
            desc_m = re.search(
                r'("name"\s*:\s*"[^"]+".*?"description"\s*:\s*"[^"]+")',
                inner,
                re.DOTALL,
            )
            if not desc_m:
                desc_m = re.search(r'("description"\s*:\s*"[^"]+")', inner, re.DOTALL)

            if desc_m:
                s_off = m.start(1) + desc_m.start(1)
                e_off = m.start(1) + desc_m.end(1)
                add_evidence(s_off, e_off, 'script[type="application/ld+json"]')
            else:
                s_off = m.start(0)
                e_off = min(m.end(0), s_off + 3000)
                add_evidence(s_off, e_off, 'script[type="application/ld+json"]')

    # Strategy 2: Academic Profile Heading & Biography Container
    # Look for <h1> containing target name followed by biography / roles section (skipping modal/dialog headings)
    heading_pat = re.compile(r'<h1([^>]*)>(.*?)</h1>', re.DOTALL | re.IGNORECASE)
    for m in heading_pat.finditer(html_text):
        h1_attrs = m.group(1)
        heading_inner = m.group(2)
        if re.search(r'\b(?:overlay-title|dialog|modal)\b', h1_attrs, re.IGNORECASE):
            continue
        if any(pat.search(heading_inner) for pat in name_patterns):
            s_idx = m.start(0)
            # Search forward up to 4000 chars for structured bio/profile text
            window = html_text[s_idx : min(len(html_text), s_idx + 4000)]
            # Truncate window strictly before any modal/dialog/overlay container starts
            overlay_m = re.search(
                r'<(?:dialog\b|(?:div|aside|section)\b[^>]*(?:class|role|id)=["\'][^"\']*(?:overlay|dialog|modal)[^"\']*["\'])',
                window,
                re.IGNORECASE,
            )
            if overlay_m:
                window = window[: overlay_m.start()]
            # Check for bio paragraph pattern
            bio_m = re.search(
                r'<p[^>]*class=["\'][^"\']*bio[^"\']*["\'][^>]*>.*?</p>\s*<p>(.*?)</p>',
                window,
                re.IGNORECASE | re.DOTALL,
            )
            if bio_m:
                e_idx = s_idx + bio_m.end()
                add_evidence(s_idx, e_idx, "div.field-field-title p")
            else:
                # Look for end of biographical block (e.g. </article>, </section>, or end of profile node)
                node_end = window.rfind("</div><!-- /page -->")
                if node_end == -1:
                    last_p = window.rfind("</p>")
                    e_idx = s_idx + last_p + 4 if last_p > 200 else s_idx + len(window)
                else:
                    e_idx = s_idx + node_end
                add_evidence(s_idx, e_idx, "h1#page-title ~ .content")

    # Strategy 3: Pinned Item / Repository / Work Descriptions (e.g. GitHub, portfolio)
    pinned_pat = re.compile(
        r'<p[^>]*class=["\'][^"\']*pinned-item-desc[^"\']*["\'][^>]*>\s*([A-Za-z0-9][^<]{5,300}?)\s*</p>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pinned_pat.finditer(html_text):
        content = m.group(1).strip()
        if content and not content.startswith("</p>"):
            s_off = m.start(1)
            e_off = m.end(1)
            add_evidence(s_off, e_off, "div.pinned-item-list-item-content")

    # Strategy 4: Fallback to target name context window in body
    if not evidence_items:
        body_m = re.search(r'<body[^>]*>(.*?)</body>', html_text, re.DOTALL | re.IGNORECASE)
        search_region = html_text if not body_m else body_m.group(1)
        base_off = 0 if not body_m else body_m.start(1)

        for pat in name_patterns:
            m = pat.search(search_region)
            if m:
                pos = base_off + m.start()
                s_off = max(0, pos - 200)
                e_off = min(len(html_text), pos + 1800)
                add_evidence(s_off, e_off, "body")
                break

    return evidence_items
