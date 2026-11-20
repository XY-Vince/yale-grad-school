#!/usr/bin/env python3
"""
verify_investigation_bundle.py
Mechanical auditor for person investigation bundles.

PASS establishes local consistency, not source authenticity or semantic accuracy.
Uncited prose warnings require human review; token overlap is only a heuristic.

Audits:
1. Raw Source Integrity: Every file in raw_sources/ is registered in source_inventory.jsonl
   with exact SHA-256 and byte-size match (zero orphan files, zero missing files, valid HTTP status).
   Rejects synthetic domains (e.g. profiles.institution.edu).
2. Claim Grounding: Every claim in verified_claims.jsonl is anchored to a registered source,
   with verbatim_excerpt found via substring or normalized matching in the raw payload.
3. PDF/HTML Locators: Verified against actual content.
4. Tri-tier Consistency & Closure:
   - corroborated_leads.jsonl source citations exist in source_inventory.jsonl.
   - open_questions.jsonl formatted and valid.
5. Query Logs Execution: query_logs.jsonl exists and contains executed queries with real HTTP status.
   For non-abstention bundles, at least one query MUST have status="EXECUTED".
6. Manifest Integrity: manifest.json exists, valid JSON, run_outcome consistent with claims count,
   and any registered file hashes/sizes strictly match disk bytes. Complete bidirectional closure.
7. Ledger-to-Report Closure:
   - Every claim in verified_claims.jsonl MUST be cited in recall_report.md [VCLM-xx].
   - recall_report.md must cite at least one lead [LEAD-xx] and at least one question [OQ-xx].
   - Zero phantom citations allowed.
   - Every dossier statement MUST have non-empty backed_claim_ids backed by verified claims.
   - Candidate Matrix must exist with candidate IDs and differentiation rationale.
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlsplit

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

SYNTHETIC_DOMAIN_PATTERNS = [
    r"profiles\.institution\.edu",
    r"example\.com",
    r"localhost",
    r"127\.0\.0\.1",
    r"mock\.university",
]


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


ABSTENTION_OUTCOMES = {"INSUFFICIENT_EVIDENCE", "ABSTENTION", "COLLECTION_FAILED"}


def normalized_outcome(value) -> str:
    return str(value).removeprefix("RunOutcome.")


def evidence_ineligibility(source: dict, allow_legacy_missing_status: bool = False) -> Optional[str]:
    """Positive support needs an explicit eligible status and HTTP 200."""
    status = source.get("evidence_status")
    if status is None and not allow_legacy_missing_status:
        return "source missing evidence_status"
    if status is not None and str(status).lower() not in {"usable", "verified"}:
        return f"{status} source"
    if type(source.get("http_status")) is not int or source["http_status"] != 200:
        return "source without HTTP 200"
    for field in ("intended_use", "evidence_use"):
        use = str(source.get(field, "")).casefold()
        if any(marker in use for marker in (
            "authwall", "login", "captcha", "restricted", "fetch_failure",
            "retrieval_noise", "search_noise", "unlinked_account", "pending_review",
            "disambiguation_only",
        )):
            return f"source with excluded {field}={use}"
    return None


def has_degree_candidacy(text: str) -> bool:
    if re.search(r"\bdegree candidates?\b|\bcandidates? for (?:the )?degrees?\b|学位候选人",
                 text, flags=re.IGNORECASE):
        return True
    # Some PDF headings extract as "CANDIDATES FO R D EG R E E S".
    letters = re.sub(r"[^a-z]", "", text.casefold())
    return "candidatesfordegrees" in letters or "degreecandidates" in letters


def markdown_visible_text(text: str) -> str:
    """Ignore fenced code and HTML comments when inspecting prose and anchors."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append("")
        else:
            lines.append(line if fence is None else "")
    return "\n".join(lines)


def markdown_anchors(text: str) -> Set[str]:
    """Collect explicit HTML IDs and GitHub-style ATX/setext heading anchors."""
    text = markdown_visible_text(text)
    anchors = set(re.findall(r"""<(?:a|h[1-6])\b[^>]*\b(?:id|name)=["']([^"']+)["']""",
                             text, flags=re.IGNORECASE))
    used = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"^\s{0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$", line)
        if heading:
            title = heading.group(1)
        elif index + 1 < len(lines) and line.strip() and re.fullmatch(r"\s{0,3}(?:=+|-+)\s*", lines[index + 1]):
            title = line.strip()
        else:
            continue
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title)
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).lower()
        slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
        unique = slug
        suffix = 0
        while unique in used:
            suffix += 1
            unique = f"{slug}-{suffix}"
        used.add(unique)
        anchors.add(unique)
    return anchors


def claim_grounding_text(claim: dict) -> str:
    """Use the atomic auditor's raw-subject fallback, never display qualifiers."""
    subject = (claim.get("subject_raw") or claim.get("subject") or "").strip()
    return (
        f"{subject} {claim.get('predicate', '')} {claim.get('object', '')} "
        f"{claim.get('verbatim_excerpt', '')}"
    ).lower()


def lexical_review_tokens(text: str, excluded: Set[str]) -> Set[str]:
    """Offer English-word review hints without treating Chinese translation as unsupported."""
    return {
        token.casefold() for token in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)
        if token.casefold() not in excluded
    }


NON_PERSON_WORDS = {
    "university", "college", "institute", "department", "center", "school", "program", "hospital",
    "united", "states", "new", "york", "san", "francisco", "north", "south", "east", "west",
    "first", "place", "second", "third", "honorable", "mention", "best", "paper", "student",
    "fellow", "fellowship", "award", "prize", "scholarship", "survey", "methodology", "data", "science",
    "predoctoral", "postdoctoral", "assistant", "associate", "professor", "doctor", "master",
    "bachelor", "dean", "director", "chair", "annual", "conference", "meeting", "journal",
    "american", "association", "national", "public", "opinion", "research", "midwest",
    "center", "michigan", "wisconsin", "madison", "yale", "georgetown", "chicago",
    "harvard", "princeton", "columbia", "stanford", "berkeley", "china", "chinese",
    "social", "sciences", "health", "medicine", "pharmacy", "medical", "pharmaceutical",
    "policy", "studies", "management", "international", "affairs", "services", "curriculum",
    "eye", "disease", "clinical", "optometry", "technology", "biology",
    "vitae", "resume", "table", "content", "page", "spring", "summer", "fall", "winter",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
}


def find_person_names_in_text(text: str, subject_name: str) -> List[Tuple[str, int, int]]:
    matches = []
    for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\b', text):
        candidate = m.group(1)
        tokens = [t.lower().replace(".", "") for t in candidate.split()]
        if any(t in NON_PERSON_WORDS for t in tokens):
            continue
        matches.append((candidate, m.start(), m.end()))
    return matches


def match_author_name(target_name: str, author_full: str) -> bool:
    t_parts = [p.lower() for p in target_name.strip().split() if p]
    a_parts = [p.lower() for p in author_full.strip().split() if p]
    if not t_parts or not a_parts:
        return False
    if len(t_parts) == 1 or len(a_parts) == 1:
        return " ".join(t_parts) == " ".join(a_parts)
    t_last = t_parts[-1]
    a_last = a_parts[-1]
    if t_last != a_last:
        return False
    t_first = t_parts[0]
    a_first = a_parts[0]
    return (
        t_first == a_first
        or (len(t_first) == 1 and a_first.startswith(t_first))
        or (len(a_first) == 1 and t_first.startswith(a_first))
    )


def orcid_owned_unit(data: dict, excerpt: str, subject: Optional[str]) -> Optional[str]:
    """Resolve a JSON fragment inside selected owner fields of one ORCID record.

    Works, coauthors, depositor identities and arbitrary strings are not owner
    attributes. Matching is structural and exact, never whole-record overlap.
    """
    identifier = data.get("orcid-identifier", {})
    path = identifier.get("path", "")
    if (not subject or identifier.get("host") != "orcid.org"
            or not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", path)
            or identifier.get("uri") != f"https://orcid.org/{path}"):
        return None
    person = data.get("person") or {}
    name = person.get("name") or {}
    full_name = " ".join(
        (name.get(key) or {}).get("value", "") for key in ("given-names", "family-name")
    ).strip()
    others = (person.get("other-names") or {}).get("other-name", [])
    names = [full_name, (name.get("credit-name") or {}).get("value", "")]
    names.extend(item.get("content", "") for item in others)
    if normalize_whitespace(subject).casefold() not in {
        normalize_whitespace(n).casefold() for n in names if n
    }:
        return None
    try:
        fragment = json.loads(excerpt if excerpt.lstrip().startswith("{") else "{" + excerpt + "}")
    except (ValueError, TypeError):
        return None
    if not isinstance(fragment, dict) or not fragment:
        return None

    def subset(small, large):
        if isinstance(small, dict):
            return isinstance(large, dict) and all(
                key in large and subset(value, large[key]) for key, value in small.items()
            )
        return type(small) is type(large) and small == large

    nodes = [identifier, {k: name[k] for k in ("given-names", "family-name", "credit-name") if k in name}]
    nodes.extend({"content": item["content"]} for item in others if "content" in item)
    nodes.extend(
        {k: item[k] for k in ("url-name", "url") if k in item}
        for item in (person.get("researcher-urls") or {}).get("researcher-url", [])
    )
    activities = data.get("activities-summary") or {}
    for group in (activities.get("employments") or {}).get("affiliation-group", []):
        for summary in group.get("summaries", []):
            employment = summary.get("employment-summary") or {}
            nodes.append({k: employment[k] for k in (
                "department-name", "role-title", "start-date", "end-date", "organization"
            ) if k in employment})
    for group in (activities.get("peer-reviews") or {}).get("group", []):
        for review_group in group.get("peer-review-group", []):
            for review in review_group.get("peer-review-summary", []):
                nodes.append({k: review[k] for k in (
                    "reviewer-role", "review-type", "completion-date", "review-group-id",
                    "convening-organization"
                ) if k in review})
    if any(subset(fragment, node) for node in nodes):
        return f"{subject} — {excerpt}"
    return None


class BundleVerifier:
    def __init__(self, bundle_dir: Path, allow_legacy_missing_status: bool = False):
        self.bundle_dir = bundle_dir.resolve()
        self.allow_legacy_missing_status = allow_legacy_missing_status
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.sources: Dict[str, dict] = {}
        self.claims: Dict[str, dict] = {}
        self.leads: Dict[str, dict] = {}
        self.verified_claim_ids: Set[str] = set()
        self.lead_ids: Set[str] = set()
        self.question_ids: Set[str] = set()
        self.candidate_ids: Set[str] = set()
        self.is_abstention: bool = False
        self._legacy_status_warnings: Set[str] = set()

    def _evidence_ineligibility(self, source: dict, source_id: str) -> Optional[str]:
        if source.get("evidence_status") is None and self.allow_legacy_missing_status:
            if source_id not in self._legacy_status_warnings:
                self.warnings.append(
                    f"Legacy source {source_id} has no evidence_status; eligibility requires manual review."
                )
                self._legacy_status_warnings.add(source_id)
        return evidence_ineligibility(source, self.allow_legacy_missing_status)

    def _resolve_path(self, local_path_str: str) -> Optional[Path]:
        p = Path(local_path_str)
        candidates = [
            p if p.is_absolute() else None,
            self.bundle_dir / p.name,
            self.bundle_dir / "raw_sources" / p.name,
            self.bundle_dir / p,
            self.bundle_dir.parent / p,
            self.bundle_dir.parent.parent / p,
        ]
        for c in candidates:
            if c and c.resolve().exists():
                return c.resolve()
        return None

    def audit_all(self) -> bool:
        if not self.bundle_dir.exists():
            self.errors.append(f"Bundle directory does not exist: {self.bundle_dir}")
            return False

        self.audit_manifest_preliminary()
        self.audit_sources()
        self.audit_claims()
        self.audit_leads_and_questions()
        self.audit_query_logs()
        self.audit_manifest_full()
        self.audit_dossier_and_report_closure()

        return len(self.errors) == 0

    def audit_manifest_preliminary(self):
        man_file = self.bundle_dir / "manifest.json"
        if not man_file.exists():
            self.errors.append("manifest.json missing in bundle root.")
            return

        try:
            data = json.loads(man_file.read_text(encoding="utf-8"))
            outcome = normalized_outcome(data.get("run_outcome", ""))
            claims_file = self.bundle_dir / "verified_claims.jsonl"
            has_claims = claims_file.exists() and bool(claims_file.read_text(encoding="utf-8").strip())
            if outcome in ABSTENTION_OUTCOMES and not has_claims:
                self.is_abstention = True
                self.info.append(f"Manifest indicates {outcome} (abstention/collection-failed bundle).")
        except Exception as e:
            self.errors.append(f"manifest.json is not valid JSON: {e}")

    def audit_sources(self):
        inv_file = self.bundle_dir / "source_inventory.jsonl"
        raw_dir = self.bundle_dir / "raw_sources"

        if not inv_file.exists() and not raw_dir.exists():
            if self.is_abstention:
                self.info.append("Abstention bundle: source_inventory and raw_sources empty as expected.")
                return
            self.errors.append("Missing source_inventory.jsonl and raw_sources/ directory.")
            return

        registered_paths: Set[Path] = set()

        if inv_file.exists():
            lines = [l.strip() for l in inv_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines and self.is_abstention:
                self.info.append("Abstention bundle: 0 sources registered in inventory.")
            elif not lines and not self.is_abstention:
                self.errors.append("source_inventory.jsonl is empty for non-abstention bundle.")

            for line_idx, line in enumerate(lines, 1):
                try:
                    record = json.loads(line)
                except Exception as e:
                    self.errors.append(f"Invalid JSON in source_inventory.jsonl:{line_idx}: {e}")
                    continue

                src_id = record.get("source_id") or record.get("id")
                if not src_id:
                    self.errors.append(f"source_inventory.jsonl:{line_idx} missing source_id")
                    continue
                self.sources[src_id] = record

                url = record.get("url", "")
                final_url = record.get("final_url", "")
                for pattern in SYNTHETIC_DOMAIN_PATTERNS:
                    if re.search(pattern, url) or re.search(pattern, final_url):
                        self.errors.append(
                            f"Source {src_id} contains prohibited synthetic domain marker '{pattern}': url={url}"
                        )

                http_status = record.get("http_status")
                if http_status is None:
                    self.errors.append(f"Source {src_id} missing http_status")

                local_path_str = record.get("local_path")
                if local_path_str:
                    full_path = self._resolve_path(local_path_str)
                    if not full_path or not full_path.exists():
                        self.errors.append(f"Registered source {src_id} missing on disk: {local_path_str}")
                        continue

                    registered_paths.add(full_path)

                    expected_size = record.get("byte_size")
                    actual_size = os.path.getsize(full_path)
                    if expected_size is not None and expected_size != actual_size:
                        self.errors.append(
                            f"Byte size mismatch for {src_id} ({full_path.name}): "
                            f"expected {expected_size}, got {actual_size}"
                        )

                    expected_sha = record.get("raw_bytes_sha256") or record.get("sha256")
                    if expected_sha:
                        actual_sha = compute_sha256(full_path)
                        if expected_sha.lower() != actual_sha.lower():
                            self.errors.append(
                                f"SHA-256 mismatch for {src_id} ({full_path.name}): "
                                f"expected {expected_sha}, got {actual_sha}"
                            )

        if raw_dir.exists():
            for root, _, files in os.walk(raw_dir):
                for f in files:
                    if f.startswith("."):
                        continue
                    p = (Path(root) / f).resolve()
                    if p not in registered_paths:
                        self.errors.append(f"Orphan file in raw_sources (not in source_inventory): {p}")

        self.info.append(f"Audited {len(self.sources)} sources in inventory.")

    def audit_claims(self):
        claims_file = self.bundle_dir / "verified_claims.jsonl"
        if not claims_file.exists():
            if self.is_abstention:
                self.info.append("Abstention bundle: verified_claims.jsonl omitted or empty.")
                return
            self.errors.append("verified_claims.jsonl missing in bundle.")
            return

        lines = [l.strip() for l in claims_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines and not self.is_abstention:
            self.errors.append("verified_claims.jsonl is empty for non-abstention bundle.")

        claim_count = 0
        for line_idx, line in enumerate(lines, 1):
            claim_count += 1
            try:
                c = json.loads(line)
            except Exception as e:
                self.errors.append(f"Invalid JSON in verified_claims.jsonl:{line_idx}: {e}")
                continue

            claim_id = c.get("claim_id") or f"line-{line_idx}"
            self.verified_claim_ids.add(claim_id)
            self.claims[claim_id] = c
            if c.get("evidence_strength") == "S4":
                self.errors.append(
                    f"Claim {claim_id} has S4 evidence strength; unresolved evidence belongs in the lead ledger."
                )

            cand_id = c.get("candidate_id")
            if cand_id:
                self.candidate_ids.add(cand_id)

            src_id = c.get("source_id")
            if not src_id or src_id not in self.sources:
                self.errors.append(f"Claim {claim_id} references unknown or missing source: {src_id}")
                continue

            src_record = self.sources[src_id]
            ineligible = self._evidence_ineligibility(src_record, src_id)
            if ineligible:
                self.errors.append(
                    f"Claim {claim_id} cites {ineligible} {src_id}; "
                    "this capture cannot support verified claims."
                )
                continue
            local_path_str = src_record.get("local_path")
            if not local_path_str:
                self.errors.append(f"Claim {claim_id} supporting source {src_id} has no local_path.")
                continue

            full_path = self._resolve_path(local_path_str)
            if not full_path or not full_path.exists():
                self.errors.append(f"Claim {claim_id} source file cannot be resolved: {local_path_str}")
                continue

            excerpt = c.get("verbatim_excerpt") or c.get("excerpt")
            if not excerpt:
                self.errors.append(f"Claim {claim_id} missing verbatim_excerpt")
                continue

            # Narrow regression guards, not general semantic entailment checks.
            if c.get("predicate") in {"graduated_from", "received_degree"} and self._degree_candidacy_context(
                full_path, excerpt, c.get("locator")
            ):
                self.errors.append(
                    f"Claim {claim_id} promotes degree candidacy to degree completion; "
                    "use separate evidence explicitly establishing graduation or award."
                )
            if c.get("predicate") == "employed_by" and re.search(
                r"\bshareholders?\b|股东", excerpt, flags=re.IGNORECASE
            ) and not re.search(r"\bemploy(?:ed|ee|ment)\b|受雇|雇员|任职", excerpt, flags=re.IGNORECASE):
                self.errors.append(f"Claim {claim_id} promotes shareholding to employment.")

            matched = self._verify_text_in_file(full_path, excerpt, c.get("locator"))
            if not matched:
                self.errors.append(
                    f"Claim {claim_id} verbatim excerpt not replayable in {full_path.name}. "
                    f"Excerpt: '{excerpt[:60]}...'"
                )
                continue

            # Atomic Evidence Unit Grounding and Cross-Entity Checks
            display_subject = (c.get("subject") or "").strip()
            subject = (c.get("subject_raw") or display_subject).strip()
            # Qualified ledger labels are not words quoted from the source.
            if subject != display_subject and (
                not cand_id or not (
                    display_subject == f"{subject} ({cand_id})"
                    or display_subject.startswith(f"{subject} ({cand_id},")
                )
            ):
                self.errors.append(
                    f"Claim {claim_id} qualified subject does not match subject_raw and candidate_id."
                )
                continue
            obj = (c.get("object") or c.get("object_raw") or "").strip()
            if not subject:
                self.errors.append(f"Claim {claim_id} missing subject.")
                continue
            if not obj:
                self.errors.append(f"Claim {claim_id} missing object.")
                continue

            norm_excerpt = normalize_whitespace(excerpt).lower()
            norm_obj = normalize_whitespace(obj).lower()
            obj_tokens = [tok for tok in re.findall(r'[a-zA-Z0-9_\u4e00-\u9fa5]+', norm_obj) if len(tok) >= 3]
            obj_grounded = (norm_obj in norm_excerpt) or any(tok in norm_excerpt for tok in obj_tokens)
            if not obj_grounded:
                self.errors.append(
                    f"Claim {claim_id} object '{obj}' not grounded in verbatim_excerpt: '{excerpt[:60]}...'"
                )
                continue

            norm_subject = normalize_whitespace(subject).lower()
            sub_grounded = norm_subject in norm_excerpt
            enclosing_unit = None
            if not sub_grounded:
                enclosing_unit = self._find_enclosing_atomic_unit(full_path, excerpt, target_subject=subject)
                if enclosing_unit:
                    norm_unit = normalize_whitespace(enclosing_unit).lower()
                    if norm_subject in norm_unit or match_author_name(subject, enclosing_unit):
                        sub_grounded = True

            if not sub_grounded:
                self.errors.append(
                    f"Claim {claim_id} subject '{subject}' not grounded in atomic evidence unit for object '{obj}'. Excerpt: '{excerpt[:60]}...'"
                )
                continue

            unit_to_check = enclosing_unit if enclosing_unit else excerpt
            if c.get("predicate") != "authored_work":
                contam_name = self._detect_cross_entity_contamination(unit_to_check, subject, obj)
                if contam_name:
                    self.errors.append(
                        f"Claim {claim_id} cross-entity attribution violation: object '{obj}' belongs to another entity '{contam_name}' in evidence unit: '{unit_to_check[:80]}...'"
                    )

        self.info.append(f"Audited {claim_count} verified claims.")

    def _degree_candidacy_context(self, filepath: Path, excerpt: str, locator: Optional[str]) -> bool:
        """Guard short degree claims against preceding HTML/PDF candidacy headings.

        This is conservative, not a general PDF section parser. A later explicit
        conferral statement may support an award; a bare Name, BA row cannot.
        """
        if has_degree_candidacy(excerpt):
            return True
        if filepath.suffix.lower() in {".html", ".htm"}:
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(filepath.read_text(encoding="utf-8", errors="replace"), "html.parser")
                page_context = " ".join(
                    node.get_text(" ", strip=True) for node in [soup.title, soup.find("h1")] if node
                )
                def normalized_html_text(value):
                    return re.sub(r"\s+([,.;:])", r"\1", normalize_whitespace(value)).casefold()

                plain_excerpt = normalized_html_text(
                    BeautifulSoup(excerpt, "html.parser").get_text(" ", strip=True)
                )
                container_names = {"p", "li", "tr", "td", "div", "section", "article"}
                containers = [
                    node for node in soup.find_all(container_names)
                    if plain_excerpt and plain_excerpt in normalized_html_text(node.get_text(" ", strip=True))
                ]
                container_ids = {id(node) for node in containers}
                smallest = [
                    node for node in containers
                    if not any(id(child) in container_ids for child in node.find_all(container_names))
                ]
                if not smallest and plain_excerpt:
                    smallest = [
                        node.parent for node in soup.find_all(string=True)
                        if plain_excerpt in normalized_html_text(str(node))
                    ]
                nearest_headings = []
                def is_heading(tag):
                    return (tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "legend"}
                            or tag.get("role") == "heading"
                            or "view-grouping-header" in tag.get("class", []))

                for node in smallest:
                    heading = node.find_previous(is_heading)
                    if heading:
                        nearest_headings.append(heading.get_text(" ", strip=True))
                    # Follow the enclosing HTML heading hierarchy without inheriting
                    # a previous sibling section at the same heading level.
                    last_level = 7
                    for previous in node.find_all_previous(
                            lambda tag: tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"}):
                        level = int(previous.name[1])
                        if level < last_level:
                            nearest_headings.append(previous.get_text(" ", strip=True))
                            last_level = level
                            if level == 1:
                                break
                    group = node.find_parent(class_="view-grouping")
                    if group:
                        group_heading = group.find(class_="view-grouping-header", recursive=False)
                        if group_heading and any(previous is group_heading for previous in node.find_all_previous()):
                            nearest_headings.append(group_heading.get_text(" ", strip=True))
                explicit_award = re.search(
                    r"\b(?:received|earned|awarded|conferred|graduated)\b|获得.{0,8}学位|授予.{0,8}学位",
                    excerpt, flags=re.IGNORECASE,
                )
                prospective = re.search(
                    r"\b(?:will|expected|anticipated|candidate|eligible|to be)\b|预计|候选|拟获",
                    excerpt, flags=re.IGNORECASE,
                )
                return bool(has_degree_candidacy(" ".join([page_context] + nearest_headings))
                            and (not explicit_award or prospective))
            except Exception as exc:
                self.errors.append(f"Cannot inspect degree context in {filepath.name}: {exc}")
                return False
        if filepath.suffix.lower() != ".pdf":
            return False
        if not fitz:
            self.errors.append("Degree claim requires PDF context review, but PyMuPDF is unavailable.")
            return False
        try:
            with fitz.open(filepath) as doc:
                texts = [normalize_whitespace(page.get_text()) for page in doc]
            matching = [i for i, text in enumerate(texts) if normalize_whitespace(excerpt) in text]
            page_match = re.search(r"\bPage\s+(\d+)\b", locator or "", re.IGNORECASE)
            if page_match and int(page_match.group(1)) - 1 in matching:
                matching = [int(page_match.group(1)) - 1]
            candidate_context = any(
                has_degree_candidacy(texts[i][:650])
                for end in matching for i in range(end + 1)
            )
            explicit_award = re.search(
                r"\b(?:received|earned|awarded|conferred|graduated)\b|获得.{0,8}学位|授予.{0,8}学位",
                excerpt, flags=re.IGNORECASE,
            )
            return bool(candidate_context and not explicit_award)
        except Exception as exc:
            self.errors.append(f"Cannot inspect degree context in {filepath.name}: {exc}")
            return False

    def _verify_text_in_file(self, filepath: Path, excerpt: str, locator: Optional[str]) -> bool:
        norm_excerpt = normalize_whitespace(excerpt)
        if filepath.suffix.lower() == ".pdf":
            if not fitz:
                self.warnings.append(f"PyMuPDF not installed, skipping strict PDF verification for {filepath.name}")
                return True
            try:
                doc = fitz.open(filepath)
                target_page = None
                if locator:
                    m = re.search(r"Page\s+(\d+)", locator, re.IGNORECASE)
                    if m:
                        target_page = int(m.group(1)) - 1  # 0-indexed

                if target_page is not None and 0 <= target_page < len(doc):
                    page_text = normalize_whitespace(doc[target_page].get_text())
                    if norm_excerpt in page_text:
                        return True

                for page in doc:
                    if norm_excerpt in normalize_whitespace(page.get_text()):
                        return True
                return False
            except Exception as e:
                self.errors.append(f"PDF extraction error on {filepath.name}: {e}")
                return False
        else:
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
                # 1. Direct normalized match
                if norm_excerpt in normalize_whitespace(content):
                    return True
                # 2. Tag-stripped match for HTML / XML
                if filepath.suffix.lower() in (".html", ".htm", ".xml"):
                    import html
                    stripped = re.sub(r"<[^>]+>", " ", content)
                    if norm_excerpt in normalize_whitespace(stripped) or norm_excerpt in normalize_whitespace(html.unescape(stripped)):
                        return True
                    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE):
                        raw_ld = m.group(1).strip()
                        if norm_excerpt in normalize_whitespace(raw_ld) or norm_excerpt in normalize_whitespace(raw_ld.replace(r'\"', '"').replace(r'\/', '/')):
                            return True
                        try:
                            parsed = json.loads(raw_ld)
                            if norm_excerpt in normalize_whitespace(json.dumps(parsed)):
                                return True
                        except Exception:
                            pass
                # 3. JSON unescaped match
                if filepath.suffix.lower() == ".json":
                    unescaped = content.replace(chr(92) + chr(34), chr(34))
                    if norm_excerpt in normalize_whitespace(unescaped):
                        return True
                    try:
                        parsed = json.loads(content)
                        parsed_str = json.dumps(parsed)
                        if norm_excerpt in normalize_whitespace(parsed_str):
                            return True
                    except Exception:
                        pass
                return False
            except Exception as e:
                self.errors.append(f"File read error on {filepath.name}: {e}")
                return False

    def _find_enclosing_atomic_unit(self, filepath: Path, excerpt: str, target_subject: Optional[str] = None) -> Optional[str]:
        norm_exc = normalize_whitespace(excerpt).lower()
        suffix = filepath.suffix.lower()

        # 1. PDF Documents
        if suffix == ".pdf":
            if not fitz:
                return None
            try:
                doc = fitz.open(filepath)
                for page in doc:
                    ptext = page.get_text()
                    for line in ptext.splitlines():
                        if norm_exc in normalize_whitespace(line).lower():
                            return line.strip()
                return None
            except Exception:
                return None

        # 2. JSON Files (CrossRef, OpenAlex, etc.)
        elif suffix == ".json":
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
                data = json.loads(content)
                if isinstance(data, dict) and "orcid-identifier" in data:
                    # Do not fall through to line matching: compact ORCID JSON
                    # also contains coauthors and unrelated work metadata.
                    return orcid_owned_unit(data, excerpt, target_subject)
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if "message" in data and isinstance(data["message"], dict) and "items" in data["message"]:
                        items = data["message"]["items"]
                    elif "items" in data and isinstance(data["items"], list):
                        items = data["items"]
                    elif "results" in data and isinstance(data["results"], list):
                        items = data["results"]
                    elif "hits" in data and isinstance(data["hits"], dict) and "hits" in data["hits"]:
                        items = data["hits"]["hits"]
                    else:
                        items = [data]

                for it in items:
                    if not isinstance(it, dict):
                        continue

                    # Nested content string (e.g. FINRA BrokerCheck)
                    raw_content = ""
                    if "_source" in it and isinstance(it["_source"], dict) and "content" in it["_source"]:
                        raw_content = it["_source"]["content"]
                    elif "content" in it and isinstance(it["content"], str):
                        raw_content = it["content"]

                    if raw_content and isinstance(raw_content, str):
                        try:
                            inner_data = json.loads(raw_content)
                            basic = inner_data.get("basicInformation", {})
                            if basic:
                                b_first = basic.get("firstName", "")
                                b_mid = basic.get("middleName", "")
                                b_last = basic.get("lastName", "")
                                b_name = " ".join([p for p in (b_first, b_mid, b_last) if p]).strip()
                                if b_name and (norm_exc in normalize_whitespace(raw_content).lower() or norm_exc in normalize_whitespace(json.dumps(inner_data)).lower()):
                                    return f"{b_name} — {excerpt}"
                        except Exception:
                            pass

                    # OpenAlex author records, distinct from work authorships.
                    # Inspect the named author object, not synthetic summary fields.
                    author_name = it.get("display_name", "")
                    if re.fullmatch(r"https://openalex\.org/A\d+", str(it.get("id", ""))):
                        if target_subject and normalize_whitespace(author_name).casefold() == target_subject.casefold():
                            for institution in it.get("last_known_institutions", []):
                                institution_name = institution.get("display_name", "")
                                if norm_exc == normalize_whitespace(institution_name).lower():
                                    return f"{author_name} — {institution_name}"

                    # Author-level affiliations (CrossRef)
                    authors = it.get("author", [])
                    if isinstance(authors, list):
                        matching_authors = []
                        for a in authors:
                            if not isinstance(a, dict):
                                continue
                            a_name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                            affs = a.get("affiliation", [])
                            if isinstance(affs, list):
                                for aff in affs:
                                    aff_name = aff.get("name", "") if isinstance(aff, dict) else str(aff)
                                    if norm_exc in normalize_whitespace(aff_name).lower():
                                        matching_authors.append((a_name, aff_name))
                        if matching_authors:
                            if target_subject:
                                for a_name, aff_name in matching_authors:
                                    if match_author_name(target_subject, a_name) or target_subject.lower() in a_name.lower():
                                        return f"{a_name} — {aff_name}"
                            return f"{matching_authors[0][0]} — {matching_authors[0][1]}"

                    # Authorship-level institutions (OpenAlex)
                    authorships = it.get("authorships", [])
                    if isinstance(authorships, list):
                        matching_authors = []
                        for ash in authorships:
                            if not isinstance(ash, dict):
                                continue
                            a_name = ash.get("author", {}).get("display_name", "")
                            insts = ash.get("institutions", [])
                            if isinstance(insts, list):
                                for inst in insts:
                                    inst_name = inst.get("display_name", "") if isinstance(inst, dict) else str(inst)
                                    if norm_exc in normalize_whitespace(inst_name).lower():
                                        matching_authors.append((a_name, inst_name))
                        if matching_authors:
                            if target_subject:
                                for a_name, inst_name in matching_authors:
                                    if match_author_name(target_subject, a_name) or target_subject.lower() in a_name.lower():
                                        return f"{a_name} — {inst_name}"
                            return f"{matching_authors[0][0]} — {matching_authors[0][1]}"

                    # Work title match (CrossRef / OpenAlex)
                    title = ""
                    if isinstance(it.get("title"), list) and it["title"]:
                        title = str(it["title"][0])
                    elif isinstance(it.get("title"), str):
                        title = it["title"]

                    if title and norm_exc in normalize_whitespace(title).lower():
                        all_auths = []
                        if isinstance(authors, list):
                            for a in authors:
                                if isinstance(a, dict):
                                    name_str = f"{a.get('given', '')} {a.get('family', '')}".strip()
                                    if name_str:
                                        all_auths.append(name_str)
                        if isinstance(authorships, list):
                            for ash in authorships:
                                if isinstance(ash, dict):
                                    name_str = ash.get("author", {}).get("display_name", "").strip()
                                    if name_str:
                                        all_auths.append(name_str)
                        return f"Title: {title} | Authors: {', '.join(all_auths)}"

                # Fallback: line-by-line
                for line in content.splitlines():
                    if norm_exc in normalize_whitespace(line).lower():
                        return line.strip()
                return None
            except Exception:
                return None

        # 3. XML Files (PubMed EFetch, etc.)
        elif suffix == ".xml":
            try:
                import xml.etree.ElementTree as ET
                content = filepath.read_text(encoding="utf-8", errors="replace")
                root = ET.fromstring(content)
                articles = root.findall(".//PubmedArticle") or [root]
                for art in articles:
                    # Check author affiliation
                    matching_authors = []
                    for auth in art.findall(".//Author"):
                        last = auth.findtext("LastName") or ""
                        fore = auth.findtext("ForeName") or ""
                        a_name = f"{fore} {last}".strip()
                        for aff in auth.findall(".//Affiliation"):
                            aff_text = aff.text or ""
                            norm_aff = normalize_whitespace(aff_text).lower()
                            if norm_exc in norm_aff or norm_aff in norm_exc:
                                matching_authors.append((a_name, aff_text))
                            elif target_subject and (match_author_name(target_subject, a_name) or target_subject.lower() in a_name.lower()):
                                if any(tok in norm_exc for tok in norm_aff.split() if len(tok) >= 4):
                                    matching_authors.append((a_name, aff_text))
                    if matching_authors:
                        if target_subject:
                            for a_name, aff_text in matching_authors:
                                if match_author_name(target_subject, a_name) or target_subject.lower() in a_name.lower():
                                    return f"{a_name} — {aff_text}"
                        return f"{matching_authors[0][0]} — {matching_authors[0][1]}"

                    # Check article title
                    title = art.findtext(".//ArticleTitle") or ""
                    if title and norm_exc in normalize_whitespace(title).lower():
                        authors = []
                        for auth in art.findall(".//Author"):
                            last = auth.findtext("LastName") or ""
                            fore = auth.findtext("ForeName") or ""
                            full = f"{fore} {last}".strip()
                            if full:
                                authors.append(full)
                        return f"Title: {title} | Authors: {', '.join(authors)}"

                lines = [re.sub(r'<[^>]+>', ' ', l).strip() for l in content.splitlines()]
                for line in lines:
                    if norm_exc in normalize_whitespace(line).lower():
                        return line.strip()
                return None
            except Exception:
                return None

        # 4. HTML Files
        elif suffix in (".html", ".htm"):
            try:
                import html
                content = filepath.read_text(encoding="utf-8", errors="replace")
                # Check JSON-LD scripts for Person / Postings
                def dict_contains_text(d, target):
                    if isinstance(d, str):
                        cleaned = normalize_whitespace(re.sub(r'<[^>]+>', ' ', d)).lower()
                        return target in cleaned
                    elif isinstance(d, dict):
                        return any(dict_contains_text(v, target) for v in d.values())
                    elif isinstance(d, list):
                        return any(dict_contains_text(item, target) for item in d)
                    return False

                for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE):
                    raw_ld = m.group(1).strip()
                    try:
                        p = json.loads(raw_ld)
                        objs = []
                        if isinstance(p, dict):
                            if "@graph" in p and isinstance(p["@graph"], list):
                                objs.extend([x for x in p["@graph"] if isinstance(x, dict)])
                            else:
                                objs.append(p)
                        elif isinstance(p, list):
                            objs.extend([x for x in p if isinstance(x, dict)])

                        for obj in objs:
                            p_name = ""
                            if obj.get("@type") == "Person":
                                p_name = obj.get("name", "")
                            elif obj.get("@type") in ("DiscussionForumPosting", "SocialMediaPosting", "BlogPosting"):
                                author = obj.get("author", {})
                                p_name = author.get("name", "") if isinstance(author, dict) else ""
                            elif "author" in obj and isinstance(obj["author"], dict):
                                p_name = obj["author"].get("name", "")
                            elif "creator" in obj and isinstance(obj["creator"], dict):
                                p_name = obj["creator"].get("name", "")

                            if p_name and dict_contains_text(obj, norm_exc):
                                return f"{p_name} — {excerpt}"
                    except Exception:
                        pass

                # A first-person biography can be grounded in a single, named
                # microdata Person plus an explicitly titled "About me" article.
                # Do not extend this to rosters, multiple profiles or news pages.
                if target_subject:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "html.parser")
                    interviews = soup.select("article.interview")
                    if interviews:
                        # A named, single-subject interview owns only its body
                        # paragraphs, not sidebars, comments or other articles.
                        if len(soup.select("article")) == 1 and len(interviews) == 1:
                            interview = interviews[0]
                            headings = interview.select("h1")
                            title = headings[0].get_text(" ", strip=True) if len(headings) == 1 else ""
                            if re.fullmatch(
                                rf"Meet {re.escape(target_subject)}(?: of [^\n]+)?",
                                title, flags=re.IGNORECASE
                            ):
                                for paragraph in interview.select("p"):
                                    if paragraph.find_parent(["aside", "blockquote"]) or paragraph.find_parent(
                                        class_=re.compile(r"(?:comment|sidebar)")
                                    ):
                                        continue
                                    unit = normalize_whitespace(paragraph.get_text(" ", strip=True))
                                    if norm_exc in unit.lower():
                                        return f"{target_subject} — {unit}"
                        return None

                    # Pure research portals identify one Person in JSON-LD and
                    # delimit that person's biography in profileinformation.
                    # Never use this association for publications/people lists.
                    profile_sections = soup.select("section.person-profileinformation")
                    if profile_sections:
                        person_records = []
                        for script in soup.select('script[type="application/ld+json"]'):
                            try:
                                record = json.loads(script.get_text())
                            except ValueError:
                                continue
                            if isinstance(record, dict) and record.get("@type") == "Person":
                                person_records.append(record)
                        if (len(person_records) == 1 and len(profile_sections) == 1
                                and person_records[0].get("name", "").casefold() == target_subject.casefold()
                                and any(h.get_text(" ", strip=True).casefold() == target_subject.casefold()
                                        for h in soup.select("h1"))):
                            for paragraph in profile_sections[0].select("p"):
                                unit = normalize_whitespace(paragraph.get_text(" ", strip=True))
                                if norm_exc in unit.lower():
                                    return f"{target_subject} — {unit}"

                    people = soup.select('[itemtype="http://schema.org/Person"], [itemtype="https://schema.org/Person"]')
                    article = soup.select_one('article[itemtype="http://schema.org/CreativeWork"], article[itemtype="https://schema.org/CreativeWork"]')
                    heading = article.select_one("h1") if article else None
                    if len(people) == 1 and heading and heading.get_text(" ", strip=True).casefold() == "about me":
                        name_element = people[0].select_one('[itemprop="name"], .author__name')
                        person_name = name_element.get_text(" ", strip=True) if name_element else ""
                        person_name = re.sub(r"^(?:Dr\.?|Prof\.?)\s+", "", person_name, flags=re.IGNORECASE)
                        if person_name.casefold() == target_subject.casefold():
                            for element in article.select('[itemprop="text"] p, [itemprop="text"] li'):
                                unit = normalize_whitespace(element.get_text(" ", strip=True))
                                if norm_exc in unit.lower():
                                    return f"{person_name} — {unit}"

                # Microdata Person profile check (e.g. UCSF profiles)
                if 'itemtype="http://schema.org/Person"' in content or 'itemtype="https://schema.org/Person"' in content or 'itemscope' in content:
                    m_name = re.search(r'<div[^>]*class=[\"\x27]pageTitle[\"\x27][^>]*>\s*<h[1-3][^>]*>(.*?)</h[1-3]>', content, re.IGNORECASE)
                    if not m_name:
                        m_name = re.search(r'alt=[\"\x27]Photo of (.*?)[\"\x27]', content, re.IGNORECASE)
                    if not m_name:
                        m_name = re.search(r'itemprop=[\"\x27]name[\"\x27][^>]*>(.*?)</', content, re.IGNORECASE)
                    if not m_name:
                        m_name = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', content, re.IGNORECASE)
                    if m_name:
                        person_header = normalize_whitespace(html.unescape(re.sub(r'<[^>]+>', ' ', m_name.group(1))))
                        clean_pname = re.sub(r',.*$', '', person_header).strip()
                        if target_subject and (target_subject.lower() in clean_pname.lower() or clean_pname.lower() in target_subject.lower()):
                            clean_exc = normalize_whitespace(re.sub(r'<[^>]+>', ' ', norm_exc)).lower()
                            for m_row in re.finditer(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE):
                                row_html = m_row.group(1)
                                clean_row = normalize_whitespace(html.unescape(re.sub(r'<[^>]+>', ' ', row_html)))
                                if norm_exc in row_html.lower() or (clean_exc and clean_exc in clean_row.lower()):
                                    return f"{clean_pname} — {clean_row}"

                for m in re.finditer(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL | re.IGNORECASE):
                    row_html = m.group(1)
                    clean_row = normalize_whitespace(html.unescape(re.sub(r'<[^>]+>', ' ', row_html)))
                    if norm_exc in clean_row.lower():
                        return clean_row
                for m in re.finditer(r'<li[^>]*>(.*?)</li>', content, re.DOTALL | re.IGNORECASE):
                    li_html = m.group(1)
                    clean_li = normalize_whitespace(html.unescape(re.sub(r'<[^>]+>', ' ', li_html)))
                    if norm_exc in clean_li.lower():
                        return clean_li
                for m in re.finditer(r'<(?:p|blockquote)[^>]*>(.*?)</(?:p|blockquote)>', content, re.DOTALL | re.IGNORECASE):
                    p_html = m.group(1)
                    clean_p = normalize_whitespace(html.unescape(re.sub(r'<[^>]+>', ' ', p_html)))
                    if norm_exc in clean_p.lower():
                        return clean_p
                block_tags = r'</?(?:p|div|h[1-6]|tr|li|ul|ol|table|br|hr|blockquote|section|article)[^>]*>'
                text_with_newlines = re.sub(block_tags, '\n', content, flags=re.IGNORECASE)
                lines = [re.sub(r'<[^>]+>', ' ', l).strip() for l in text_with_newlines.split('\n')]
                for line in lines:
                    norm_line = normalize_whitespace(line).lower()
                    if norm_exc in norm_line:
                        return line.strip()
                return None
            except Exception:
                return None

        # 5. Generic Files
        else:
            try:
                content = filepath.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    if norm_exc in normalize_whitespace(line).lower():
                        return line.strip()
                return None
            except Exception:
                return None

    def _detect_cross_entity_contamination(self, unit_text: str, subject: str, obj: str) -> Optional[str]:
        person_matches = find_person_names_in_text(unit_text, subject)
        sub_lower = subject.lower()
        other_names = [p for p in person_matches if p[0].lower() != sub_lower]
        if not other_names:
            return None

        norm_unit = unit_text.lower()
        norm_obj = obj.lower()
        obj_pos = norm_unit.find(norm_obj)
        if obj_pos == -1:
            for tok in re.findall(r'[a-zA-Z0-9_\u4e00-\u9fa5]+', norm_obj):
                if len(tok) >= 3 and tok in norm_unit:
                    obj_pos = norm_unit.find(tok)
                    break

        if obj_pos == -1:
            return None

        sub_pos = norm_unit.find(sub_lower)
        if sub_pos == -1:
            return other_names[0][0]

        for other_name, o_start, o_end in other_names:
            dist_other = abs(o_start - obj_pos)
            dist_sub = abs(sub_pos - obj_pos)
            span_sub_obj = unit_text[min(sub_pos, obj_pos):max(sub_pos, obj_pos)]
            has_delimiter = any(d in span_sub_obj for d in (';', '\n', '|', '•'))
            if dist_other < dist_sub and has_delimiter:
                return other_name

        return None

    def audit_leads_and_questions(self):
        leads_file = self.bundle_dir / "corroborated_leads.jsonl"
        if leads_file.exists():
            lead_count = 0
            for line_idx, line in enumerate(leads_file.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                lead_count += 1
                try:
                    ld = json.loads(line)
                    lid = ld.get("lead_id") or f"LEAD-{lead_count:02d}"
                    self.lead_ids.add(lid)
                    self.leads[lid] = ld
                    cand_id = ld.get("candidate_id")
                    if cand_id:
                        self.candidate_ids.add(cand_id)
                    self.audit_lead_support(lid, ld)
                except Exception as e:
                    self.errors.append(f"Invalid JSON in corroborated_leads.jsonl:{line_idx}: {e}")
            self.info.append(f"Audited {lead_count} corroborated leads.")

        q_file = self.bundle_dir / "open_questions.jsonl"
        if q_file.exists():
            q_count = 0
            for line_idx, line in enumerate(q_file.read_text(encoding="utf-8").splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                q_count += 1
                try:
                    qd = json.loads(line)
                    qid = qd.get("question_id") or f"OQ-{q_count:02d}"
                    self.question_ids.add(qid)
                except Exception as e:
                    self.errors.append(f"Invalid JSON in open_questions.jsonl:{line_idx}: {e}")
            self.info.append(f"Audited {q_count} open questions.")

    def audit_lead_support(self, lid: str, lead: dict):
        """Separate supporting evidence from discovery and withdrawn history."""
        supporting = []
        is_corroborated = str(lead.get("status", "")).upper() == "CORROBORATED"
        legacy_context = self.allow_legacy_missing_status and not is_corroborated
        for field in ("corroborating_source_ids", "source_refs", "context_source_ids", "withdrawn_source_ids"):
            refs = lead.get(field, [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                self.errors.append(f"Lead {lid} {field} must be a list of source IDs.")
                continue
            for ref in refs:
                source = self.sources.get(ref)
                if source is None:
                    self.errors.append(f"Lead {lid} references unknown source: {ref}")
                    continue
                if field in {"corroborating_source_ids", "source_refs"}:
                    supporting.append(ref)
                    if not legacy_context:
                        reason = self._evidence_ineligibility(source, ref)
                        if reason:
                            self.errors.append(f"Lead {lid} cites {reason} {ref} as support; use context_source_ids or withdrawn_source_ids for history.")
                elif field == "withdrawn_source_ids" and source.get("evidence_status") != "withdrawn":
                    self.errors.append(f"Lead {lid} withdrawn_source_ids includes non-withdrawn source {ref}.")
                elif field == "context_source_ids" and source.get("evidence_status") == "withdrawn":
                    self.errors.append(f"Lead {lid} must put withdrawn source {ref} in withdrawn_source_ids.")
        if not is_corroborated:
            if supporting:
                message = (f"Lead {lid} is not CORROBORATED but lists positive sources; "
                           "use context_source_ids until the support is reviewed.")
                if legacy_context:
                    self.warnings.append(
                        f"Legacy review: {message} These references are context only, not corroboration."
                    )
                else:
                    self.errors.append(message)
            return
        evidence = lead.get("supporting_evidence", [])
        if not supporting or not isinstance(evidence, list) or not evidence:
            self.errors.append(f"Lead {lid} CORROBORATED requires eligible sources and supporting_evidence with subject, object and replayable excerpt.")
            return
        covered = set()
        for unit in evidence:
            if not isinstance(unit, dict):
                self.errors.append(f"Lead {lid} has invalid supporting_evidence entry.")
                continue
            ref = unit.get("source_id")
            subject = unit.get("subject_raw")
            obj = unit.get("object")
            excerpt = unit.get("verbatim_excerpt")
            if ref not in supporting or not all(isinstance(v, str) and v.strip() for v in (subject, obj, excerpt)):
                self.errors.append(f"Lead {lid} evidence requires a supporting source_id, subject_raw, object and verbatim_excerpt.")
                continue
            source = self.sources[ref]
            if self._evidence_ineligibility(source, ref):
                continue
            path = self._resolve_path(source.get("local_path") or "")
            if not path or not path.is_file() or not self._verify_text_in_file(path, excerpt, unit.get("locator")):
                self.errors.append(f"Lead {lid} supporting excerpt not replayable in {ref}.")
                continue
            enclosing = self._find_enclosing_atomic_unit(path, excerpt, subject)
            text = normalize_whitespace(enclosing or excerpt).casefold()
            owned = re.search(rf"(?<!\w){re.escape(normalize_whitespace(subject).casefold())}(?!\w)", text)
            grounded = normalize_whitespace(obj).casefold() in normalize_whitespace(excerpt).casefold()
            contamination = self._detect_cross_entity_contamination(enclosing or excerpt, subject, obj)
            if not owned or not grounded or contamination:
                self.errors.append(f"Lead {lid} supporting evidence lacks subject/object grounding in {ref}.")
                continue
            covered.add(ref)
        if set(supporting) - covered:
            self.errors.append(f"Lead {lid} CORROBORATED has sources without grounded evidence: {sorted(set(supporting) - covered)}")

    def audit_query_logs(self):
        qlog_file = self.bundle_dir / "query_logs.jsonl"
        if not qlog_file.exists():
            self.errors.append("query_logs.jsonl missing in bundle root.")
            return

        lines = [l.strip() for l in qlog_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            self.errors.append("query_logs.jsonl is empty (no queries executed).")
            return

        has_executed_query = False
        for idx, line in enumerate(lines, 1):
            try:
                rec = json.loads(line)
                if not (rec.get("query_text") or rec.get("query")):
                    self.errors.append(f"query_logs.jsonl:{idx} missing query_text or query")
                if not (rec.get("executed_at") or rec.get("timestamp")):
                    self.errors.append(f"query_logs.jsonl:{idx} missing executed_at or timestamp")
                st = str(rec.get("status", "")).upper()
                if st in ("EXECUTED", "COMPLETED"):
                    has_executed_query = True
            except Exception as e:
                self.errors.append(f"query_logs.jsonl:{idx} invalid JSON: {e}")

        if not self.is_abstention and not has_executed_query:
            self.errors.append("query_logs.jsonl must contain at least one query with status EXECUTED or COMPLETED.")

        self.info.append(f"Audited {len(lines)} query log entries.")

    def audit_manifest_full(self):
        man_file = self.bundle_dir / "manifest.json"
        if not man_file.exists():
            return

        try:
            data = json.loads(man_file.read_text(encoding="utf-8"))
            outcome = normalized_outcome(data.get("run_outcome", ""))
            claim_count = len(self.verified_claim_ids)
            dossier_file = self.bundle_dir / "dossier.json"
            dossier = json.loads(dossier_file.read_text(encoding="utf-8")) if dossier_file.exists() else {}
            primary = dossier.get("primary_candidate_id")
            target_count = sum(c.get("candidate_id") == primary for c in self.claims.values()) if primary else None

            if claim_count == 0 and outcome not in ABSTENTION_OUTCOMES:
                self.errors.append(
                    f"Manifest run_outcome is '{outcome}' but 0 verified claims found. "
                    "Must be INSUFFICIENT_EVIDENCE or COLLECTION_FAILED."
                )
            elif claim_count > 0 and outcome in ABSTENTION_OUTCOMES and not (
                outcome in {"INSUFFICIENT_EVIDENCE", "ABSTENTION"} and primary
                and target_count == 0 and all(c.get("candidate_id") for c in self.claims.values())
            ):
                self.errors.append(
                    f"Manifest run_outcome is '{outcome}' but {claim_count} verified claims found."
                )
            if primary and target_count == 0 and outcome not in ABSTENTION_OUTCOMES:
                self.errors.append(
                    f"Primary candidate {primary} has 0 verified claims; "
                    "manifest must declare INSUFFICIENT_EVIDENCE (alternate-candidate claims do not establish the target)."
                )

            # Audit registered files in manifest (bidirectional closure)
            files_dict = data.get("files")
            if isinstance(files_dict, dict):
                manifest_registered_paths = set()
                for rel_path, meta in files_dict.items():
                    fpath = self.bundle_dir / rel_path
                    if not fpath.exists():
                        self.errors.append(f"Manifest registered file missing on disk: {rel_path}")
                        continue
                    manifest_registered_paths.add(fpath.resolve())
                    exp_size = meta.get("byte_size")
                    if exp_size is not None and fpath.stat().st_size != exp_size:
                        self.errors.append(
                            f"Manifest byte_size mismatch for {rel_path}: expected {exp_size}, got {fpath.stat().st_size}"
                        )
                    exp_sha = meta.get("sha256")
                    if exp_sha:
                        actual_sha = compute_sha256(fpath)
                        if exp_sha.lower() != actual_sha.lower():
                            self.errors.append(
                                f"Manifest SHA-256 mismatch for {rel_path}: expected {exp_sha}, got {actual_sha}"
                            )

                # Check if disk files are registered in manifest
                for root, _, fnames in os.walk(self.bundle_dir):
                    if "__pycache__" in root:
                        continue
                    for fn in fnames:
                        if fn.startswith(".") or fn == "manifest.json" or fn.endswith(".pyc"):
                            continue
                        disk_p = (Path(root) / fn).resolve()
                        if disk_p not in manifest_registered_paths:
                            self.errors.append(f"File on disk not registered in manifest.json: {disk_p.relative_to(self.bundle_dir)}")

            self.info.append("Manifest integrity, file closure, and run_outcome verified.")
        except Exception as e:
            self.errors.append(f"Error auditing manifest: {e}")

    def audit_dossier_and_report_closure(self):
        dossier_file = self.bundle_dir / "dossier.json"
        report_file = self.bundle_dir / "recall_report.md"

        exempt_words = {
            "cand", "stmt", "vclm", "src", "status", "状态", "as_of_publication", "historical", "current",
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "was", "with",
            "by", "from", "as", "affiliated_with", "authored_work", "holds_position", "graduated_from",
            "mentioned_in", "received_degree", "employed_by", "published", "fellow", "author", "work",
            "researcher", "institution", "候选人", "时间语义", "来源", "依据", "候选实体", "匹配结论",
            "消歧依据", "引用", "标识", "关联机构", "角色"
        }

        dossier = None
        if not dossier_file.exists():
            self.errors.append("dossier.json missing in bundle root.")
        else:
            try:
                dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
                primary_id = dossier.get("primary_candidate_id")

                # Clue gating check: If primary_candidate_id is null/None, no clue-correlation leads allowed
                if primary_id is None and not self.is_abstention:
                    for lid, ld in self.leads.items():
                        desc = ld.get("description", "").lower()
                        if "correlate with clues" in desc or "signals correlate" in desc:
                            self.errors.append(
                                f"Lead {lid} asserts clue correlation when primary_candidate_id is null: {ld.get('description')}"
                            )

                # Semantic alignment check on each dossier statement
                for stmt in dossier.get("statements", []):
                    stmt_id = stmt.get("statement_id", "")
                    rendered_text = stmt.get("rendered_text", "")
                    backed = stmt.get("backed_claim_ids", [])
                    if not backed:
                        self.errors.append(f"Dossier statement {stmt_id} has empty backed_claim_ids.")
                        continue

                    # Structured values can be checked exactly; prose still needs
                    # human review even when it shares words with its source.
                    backed_supported_tokens = set()
                    for cid in backed:
                        if cid not in self.verified_claim_ids:
                            self.errors.append(f"Dossier statement cites unbacked claim ID: {cid}")
                            continue
                        c = self.claims.get(cid, {})
                        if stmt.get("candidate_id") and c.get("candidate_id") != stmt["candidate_id"]:
                            self.errors.append(
                                f"Dossier statement {stmt_id} candidate differs from backed claim {cid}."
                            )
                        for field in ("predicate", "object"):
                            claim_value = c.get(field) or (c.get("object_raw") if field == "object" else "")
                            if stmt.get(field) and normalize_whitespace(str(stmt[field])).casefold() != (
                                normalize_whitespace(str(claim_value or "")).casefold()
                            ):
                                self.errors.append(
                                    f"Dossier statement {stmt_id} {field} differs from backed claim {cid}."
                                )
                        c_text = claim_grounding_text(c)
                        backed_supported_tokens.update(lexical_review_tokens(c_text, exempt_words))

                    # Extract substantive tokens from statement (excluding boilerplate/stop words)
                    stmt_substantive_tokens = lexical_review_tokens(rendered_text, exempt_words)

                    # Must have grounding overlap with backed claims
                    overlap = stmt_substantive_tokens.intersection(backed_supported_tokens)
                    if stmt_substantive_tokens and not overlap:
                        self.warnings.append(
                            f"Dossier statement {stmt_id} has no lexical overlap with backed claims {backed}; review meaning."
                        )

                    unbacked_tokens = stmt_substantive_tokens - backed_supported_tokens
                    if stmt_substantive_tokens and (len(unbacked_tokens) / len(stmt_substantive_tokens) > 0.35):
                        self.warnings.append(
                            f"Dossier statement {stmt_id} has token-overlap review hints {unbacked_tokens}; "
                            f"review against claims {backed}."
                        )

                self.info.append("Dossier JSON parsed and validated.")
            except Exception as e:
                self.errors.append(f"Invalid dossier.json: {e}")

        if not report_file.exists():
            self.errors.append("recall_report.md missing in bundle root.")
            return

        report_text = report_file.read_text(encoding="utf-8")
        self.audit_evidence_links(report_file, report_text)
        index_file = self.bundle_dir / "evidence_index.md"
        if index_file.exists():
            self.audit_evidence_links(index_file, index_file.read_text(encoding="utf-8"))
        self.warn_uncited_report_prose(report_text)
        if not self.is_abstention:
            if "## 候选实体比对" not in report_text and "Candidate Matrix" not in report_text and "候选人矩阵" not in report_text and "候选实体" not in report_text:
                self.errors.append("recall_report.md is missing Candidate Matrix section.")

        # Check citation closure in report
        cited_claims = set(re.findall(r"\[(VCLM-\d+)\]", report_text))
        for cid in cited_claims:
            if cid not in self.verified_claim_ids:
                self.errors.append(f"recall_report.md cites phantom claim ID not in verified_claims: {cid}")

        # Token overlap is an imperfect review hint, not semantic entailment.
        for line in report_text.splitlines():
            line_cids = re.findall(r"\[(VCLM-\d+)\]", line)
            if not line_cids:
                continue
            # Link destinations locate evidence; they are not factual prose.
            line_lower = re.sub(r"\]\([^)]*\)", "]", line).lower()
            line_lower = re.sub(r"\[(?:lead|oq)-\d+\]", "", line_lower)
            # An aggregate row may cite several facts. Compare with their union,
            # not each fact in isolation; phantom IDs are still rejected above.
            c_text = " ".join(claim_grounding_text(self.claims.get(cid, {})) for cid in line_cids)
            c_tokens = lexical_review_tokens(c_text, exempt_words)
            line_tokens = lexical_review_tokens(line_lower, exempt_words)
            line_unbacked = line_tokens - c_tokens
            if line_tokens and (len(line_unbacked) / len(line_tokens) > 0.5):
                self.warnings.append(
                    f"recall_report.md line citing [{'], ['.join(line_cids)}] has token-overlap review hints {line_unbacked}: '{line.strip()}'"
                )

            # For claim bullet items, ensure the claim object appears in the bullet
            for cid in line_cids:
                if re.match(rf"^[*-]\s+\[{re.escape(cid)}\]", line.strip()):
                    c = self.claims.get(cid, {})
                    c_obj = str(c.get("object", "")).strip().lower()
                    c_obj_tokens = lexical_review_tokens(c_obj, exempt_words)
                    c_obj_cjk = re.findall(r"[\u4e00-\u9fff]{2,}", c_obj)
                    visible_tokens = lexical_review_tokens(line_lower, exempt_words)
                    if ((c_obj_tokens or c_obj_cjk)
                            and not visible_tokens.intersection(c_obj_tokens)
                            and not any(token in line_lower for token in c_obj_cjk)):
                        self.warnings.append(
                            f"recall_report.md claim bullet [{cid}] does not literally contain object of claim {cid}; review meaning"
                        )

        cited_leads = set(re.findall(r"\[(LEAD-\d+)\]", report_text))
        for lid in cited_leads:
            if lid not in self.lead_ids:
                self.errors.append(f"recall_report.md cites phantom lead ID not in corroborated_leads: {lid}")

        cited_oqs = set(re.findall(r"\[(OQ-\d+)\]", report_text))
        for qid in cited_oqs:
            if qid not in self.question_ids:
                self.errors.append(f"recall_report.md cites phantom question ID not in open_questions: {qid}")

        # Complete coverage: for non-abstention bundles, every verified claim MUST be cited in report
        if not self.is_abstention and len(self.verified_claim_ids) > 0:
            uncited_claims = self.verified_claim_ids - cited_claims
            if uncited_claims:
                self.errors.append(f"recall_report.md fails to cite all verified claims: {uncited_claims}")
            if not cited_leads and len(self.lead_ids) > 0:
                self.errors.append("recall_report.md must cite corroborated leads.")
            if not cited_oqs and len(self.question_ids) > 0:
                self.errors.append("recall_report.md must cite open questions.")

        self.info.append(
            f"Citation closure verified: {len(cited_claims)} claims, {len(cited_leads)} leads, {len(cited_oqs)} questions cited."
        )

    def audit_evidence_links(self, report_file: Path, report_text: str):
        """Validate destinations as well as citation IDs; never fetch remote links."""
        visible = markdown_visible_text(report_text)
        references = {
            label.strip().casefold(): dest.strip("<>")
            for label, dest in re.findall(r"^\s{0,3}\[([^]]+)\]:\s*(<[^>]+>|\S+)", visible, re.MULTILINE)
        }
        # Ordinary links also need portable paths, even when their labels are
        # not VCLM/LEAD/OQ IDs. Remote URLs are unaffected; nothing is fetched.
        destinations = re.findall(r"\[[^]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)", visible)
        destinations.extend(references.values())
        for destination in sorted(set(destinations)):
            raw = unquote(destination.strip("<>"))
            try:
                url = urlsplit(raw)
                if (url.scheme.casefold() == "file" or re.match(r"^[A-Za-z]:[\\/]", raw)
                        or (not url.scheme and not url.netloc and url.path.startswith("/"))):
                    self.errors.append(f"Report link uses an absolute local path; use a relative path: {destination}")
                elif not url.scheme and not url.netloc and url.path:
                    target = (report_file.parent / url.path).resolve()
                    if not target.is_relative_to(self.bundle_dir) or not target.exists():
                        self.errors.append(f"Local link target missing or outside bundle: {destination}")
            except ValueError:
                # The citation-specific checks below report malformed links.
                self.errors.append(f"Report link has an invalid destination: {destination}")
        links = re.findall(
            r"\[((?:VCLM|LEAD|OQ)-\d+)\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)",
            visible,
        )
        for cid, label in re.findall(r"\[((?:VCLM|LEAD|OQ)-\d+)\]\[([^]]*)\]", visible):
            key = (label or cid).strip().casefold()
            if key not in references:
                self.errors.append(f"Evidence link [{cid}] has undefined reference [{label or cid}].")
            else:
                links.append((cid, references[key]))
        no_inline_code = re.sub(r"`+[^`\n]*`+", "", visible)
        for cid in re.findall(
            r"(?<!\\)\[((?:VCLM|LEAD|OQ)-\d+)\](?!\s*(?:\(|\[|:))",
            no_inline_code,
        ):
            if cid.casefold() in references:
                links.append((cid, references[cid.casefold()]))
            else:
                self.errors.append(f"Evidence citation [{cid}] must link to its local evidence anchor.")
        for cid, destination in sorted(set(links)):
            try:
                url = urlsplit(destination.strip("<>"))
                if url.scheme or url.netloc:
                    self.errors.append(f"Evidence link [{cid}] must target a local evidence anchor: {destination}")
                    continue
                target = (report_file.parent / unquote(url.path)).resolve() if url.path else report_file
                if not target.is_relative_to(self.bundle_dir) or not target.is_file():
                    self.errors.append(f"Evidence link [{cid}] target missing or outside bundle: {destination}")
                    continue
                anchor = unquote(url.fragment)
                if not anchor or anchor not in markdown_anchors(target.read_text(encoding="utf-8")):
                    self.errors.append(f"Evidence link [{cid}] missing anchor in target: {destination}")
                elif anchor.casefold() != cid.casefold():
                    self.errors.append(f"Evidence link [{cid}] points to another entry: {destination}")
            except (ValueError, OSError, UnicodeError) as exc:
                self.errors.append(f"Evidence link [{cid}] cannot be read: {destination}: {exc}")

    def warn_uncited_report_prose(self, report_text: str):
        """Surface review candidates without claiming to classify factual language."""
        uncited = []
        for line_number, line in enumerate(markdown_visible_text(report_text).splitlines(), 1):
            text = line.strip()
            if not text or text.startswith("#") or re.fullmatch(r"[-|: *]+", text):
                continue
            if re.match(r"^\[[^]]+\]:", text) or re.search(r"\[(?:VCLM|LEAD|OQ)-\d+\]", text):
                continue
            if len(re.findall(r"\w", text)) < 20:
                continue
            uncited.append((line_number, text))
        if len(uncited) == 1:
            line_number, text = uncited[0]
            self.warnings.append(
                f"recall_report.md:{line_number}: uncited prose requires human review "
                f"(may be context or an unsupported assertion): {text[:100]}"
            )
        elif uncited:
            line_numbers = ", ".join(str(number) for number, _ in uncited)
            self.warnings.append(
                f"recall_report.md: {len(uncited)} uncited prose lines require human review "
                f"(may be context or unsupported assertions); inspect lines {line_numbers}."
            )


def main():
    parser = argparse.ArgumentParser(description="Audit and verify person investigation bundle.")
    parser.add_argument("--bundle-dir", type=Path, required=True, help="Path to investigation bundle directory")
    parser.add_argument(
        "--allow-legacy-missing-evidence-status",
        action="store_true",
        help=("Review missing source status and unresolved legacy lead references with warnings; "
              "legacy references are context, not corroboration."),
    )
    args = parser.parse_args()

    verifier = BundleVerifier(args.bundle_dir, args.allow_legacy_missing_evidence_status)
    ok = verifier.audit_all()

    print("=" * 70)
    print(f"INVESTIGATION BUNDLE AUDIT: {args.bundle_dir}")
    print("=" * 70)
    for info in verifier.info:
        print(f"  [INFO] {info}")
    for warn in verifier.warnings:
        print(f"  [WARN] {warn}")
    for err in verifier.errors:
        print(f"  [ERROR] {err}")
    print("-" * 70)

    if ok:
        print("RESULT: PASS (mechanical checks only; source authenticity and meaning require human review)")
        sys.exit(0)
    else:
        print(f"RESULT: FAIL ({len(verifier.errors)} errors detected)")
        sys.exit(1)


if __name__ == "__main__":
    main()
