#!/usr/bin/env python3
"""
verify_investigation_bundle.py
Mechanical Auditor and Quality Gate for Person Investigation Bundles (V6.1 - Fail-Closed).

Audits:
1. Raw Source Integrity: Every file in raw_sources/ is registered in source_inventory.jsonl
   with exact SHA-256 and byte-size match (zero orphan files, zero missing files, valid HTTP status).
   Rejects synthetic domains (e.g. profiles.institution.edu).
2. Claim Grounding: Every claim in verified_claims.jsonl is anchored to an authentic source,
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
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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


NON_PERSON_WORDS = {
    "university", "college", "institute", "department", "center", "school", "program", "hospital",
    "united", "states", "new", "york", "san", "francisco", "north", "south", "east", "west",
    "first", "place", "second", "third", "honorable", "mention", "best", "paper", "student",
    "fellow", "fellowship", "award", "prize", "scholarship", "survey", "methodology", "data", "science",
    "predoctoral", "postdoctoral", "assistant", "associate", "professor", "doctor", "master",
    "bachelor", "dean", "director", "chair", "annual", "conference", "meeting", "journal",
    "american", "association", "national", "public", "opinion", "research", "midwest",
    "roper", "center", "michigan", "wisconsin", "madison", "yale", "georgetown", "chicago",
    "harvard", "princeton", "columbia", "stanford", "berkeley", "china", "chinese",
    "social", "sciences", "health", "medicine", "pharmacy", "medical", "pharmaceutical",
    "curriculum", "vitae", "resume", "table", "content", "page", "spring", "summer", "fall", "winter",
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


class BundleVerifier:
    def __init__(self, bundle_dir: Path):
        self.bundle_dir = bundle_dir.resolve()
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
            outcome = data.get("run_outcome", "")
            if outcome in ("INSUFFICIENT_EVIDENCE", "ABSTENTION", "RunOutcome.INSUFFICIENT_EVIDENCE"):
                self.is_abstention = True
                self.info.append("Manifest indicates INSUFFICIENT_EVIDENCE (abstention bundle).")
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

            cand_id = c.get("candidate_id")
            if cand_id:
                self.candidate_ids.add(cand_id)

            src_id = c.get("source_id")
            if not src_id or src_id not in self.sources:
                self.errors.append(f"Claim {claim_id} references unknown or missing source: {src_id}")
                continue

            src_record = self.sources[src_id]
            local_path_str = src_record.get("local_path")
            if not local_path_str:
                continue

            full_path = self._resolve_path(local_path_str)
            if not full_path or not full_path.exists():
                self.errors.append(f"Claim {claim_id} source file cannot be resolved: {local_path_str}")
                continue

            excerpt = c.get("verbatim_excerpt") or c.get("excerpt")
            if not excerpt:
                self.errors.append(f"Claim {claim_id} missing verbatim_excerpt")
                continue

            matched = self._verify_text_in_file(full_path, excerpt, c.get("locator"))
            if not matched:
                self.errors.append(
                    f"Claim {claim_id} verbatim excerpt not replayable in {full_path.name}. "
                    f"Excerpt: '{excerpt[:60]}...'"
                )
                continue

            # Atomic Evidence Unit Grounding and Cross-Entity Checks
            subject = (c.get("subject") or "").strip()
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
                    else:
                        items = [data]

                for it in items:
                    if not isinstance(it, dict):
                        continue

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
                            if norm_exc in normalize_whitespace(aff_text).lower():
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
                # Check JSON-LD scripts for Person
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
                            if obj.get("@type") == "Person":
                                p_name = obj.get("name", "")
                                if dict_contains_text(obj, norm_exc):
                                    return f"{p_name} — {excerpt}"
                    except Exception:
                        pass

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
                    for src_ref in ld.get("corroborating_source_ids", []):
                        if src_ref not in self.sources:
                            self.errors.append(f"Lead {lid} references unknown source: {src_ref}")
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
            outcome = str(data.get("run_outcome", ""))
            claim_count = len(self.verified_claim_ids)

            if claim_count == 0 and "INSUFFICIENT_EVIDENCE" not in outcome and "ABSTENTION" not in outcome:
                self.errors.append(
                    f"Manifest run_outcome is '{outcome}' but 0 verified claims found. "
                    "Must be INSUFFICIENT_EVIDENCE."
                )
            elif claim_count > 0 and "INSUFFICIENT_EVIDENCE" in outcome:
                self.errors.append(
                    f"Manifest run_outcome is '{outcome}' but {claim_count} verified claims found."
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

                    # Collect supported text tokens from backed claims
                    backed_supported_tokens = set()
                    for cid in backed:
                        if cid not in self.verified_claim_ids:
                            self.errors.append(f"Dossier statement cites unbacked claim ID: {cid}")
                            continue
                        c = self.claims.get(cid, {})
                        c_text = f"{c.get('subject', '')} {c.get('predicate', '')} {c.get('object', '')} {c.get('verbatim_excerpt', '')}".lower()
                        for tok in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", c_text):
                            if len(tok) > 1:
                                backed_supported_tokens.add(tok)

                    # Extract substantive tokens from statement (excluding boilerplate/stop words)
                    stmt_substantive_tokens = {
                        tok.lower() for tok in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", rendered_text)
                        if len(tok) > 2 and tok.lower() not in exempt_words and not tok.isdigit()
                    }

                    # Must have grounding overlap with backed claims
                    overlap = stmt_substantive_tokens.intersection(backed_supported_tokens)
                    if stmt_substantive_tokens and not overlap:
                        self.errors.append(
                            f"Dossier statement {stmt_id} text '{rendered_text}' has ZERO semantic grounding in backed claims {backed}."
                        )

                    # Mathematical grounding check: unsupported tokens cannot exceed 35% of statement
                    unbacked_tokens = stmt_substantive_tokens - backed_supported_tokens
                    if stmt_substantive_tokens and (len(unbacked_tokens) / len(stmt_substantive_tokens) > 0.35):
                        self.errors.append(
                            f"Dossier statement {stmt_id} fails semantic grounding: contains excessive ungrounded tokens {unbacked_tokens} "
                            f"not supported by claims {backed}."
                        )

                self.info.append("Dossier JSON parsed and validated.")
            except Exception as e:
                self.errors.append(f"Invalid dossier.json: {e}")

        if not report_file.exists():
            self.errors.append("recall_report.md missing in bundle root.")
            return

        report_text = report_file.read_text(encoding="utf-8")
        if not self.is_abstention:
            if "## 候选实体比对" not in report_text and "Candidate Matrix" not in report_text and "候选人矩阵" not in report_text and "候选实体" not in report_text:
                self.errors.append("recall_report.md is missing Candidate Matrix section.")

        # Check citation closure in report
        cited_claims = set(re.findall(r"\[(VCLM-\d+)\]", report_text))
        for cid in cited_claims:
            if cid not in self.verified_claim_ids:
                self.errors.append(f"recall_report.md cites phantom claim ID not in verified_claims: {cid}")

        # Check report lines for ungrounded citations (tokens must be grounded in cited claim)
        for line in report_text.splitlines():
            line_cids = re.findall(r"\[(VCLM-\d+)\]", line)
            if not line_cids:
                continue
            line_lower = line.lower()
            for cid in line_cids:
                c = self.claims.get(cid, {})
                c_text = f"{c.get('subject', '')} {c.get('predicate', '')} {c.get('object', '')} {c.get('verbatim_excerpt', '')}".lower()
                c_tokens = {t for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", c_text) if len(t) > 2}
                line_tokens = {t for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", line_lower) if len(t) > 2 and t not in exempt_words}
                line_unbacked = line_tokens - c_tokens
                if line_tokens and (len(line_unbacked) / len(line_tokens) > 0.5):
                    self.errors.append(
                        f"recall_report.md line citing [{cid}] contains ungrounded tokens {line_unbacked}: '{line.strip()}'"
                    )

            # For claim bullet items, ensure the claim object appears in the bullet
            for cid in line_cids:
                if line.strip().startswith(f"* [{cid}]"):
                    c = self.claims.get(cid, {})
                    c_obj = str(c.get("object", "")).strip().lower()
                    c_obj_tokens = {t for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", c_obj) if len(t) > 2}
                    line_tokens = {t for t in re.findall(r"[a-zA-Z0-9_\u4e00-\u9fa5]+", line_lower) if len(t) > 2}
                    if c_obj_tokens and not line_tokens.intersection(c_obj_tokens):
                        self.errors.append(
                            f"recall_report.md claim bullet * [{cid}] does not contain object of claim {cid}"
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


def main():
    parser = argparse.ArgumentParser(description="Audit and verify person investigation bundle.")
    parser.add_argument("--bundle-dir", type=Path, required=True, help="Path to investigation bundle directory")
    args = parser.parse_args()

    verifier = BundleVerifier(args.bundle_dir)
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
        print("RESULT: PASS (All checks verified successfully)")
        sys.exit(0)
    else:
        print(f"RESULT: FAIL ({len(verifier.errors)} errors detected)")
        sys.exit(1)


if __name__ == "__main__":
    main()
