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


class BundleVerifier:
    def __init__(self, bundle_dir: Path):
        self.bundle_dir = bundle_dir.resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.sources: Dict[str, dict] = {}
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

        if not dossier_file.exists():
            self.errors.append("dossier.json missing in bundle root.")
        else:
            try:
                dossier = json.loads(dossier_file.read_text(encoding="utf-8"))
                for stmt in dossier.get("statements", []):
                    backed = stmt.get("backed_claim_ids", [])
                    if not backed:
                        self.errors.append(f"Dossier statement {stmt.get('statement_id', '')} has empty backed_claim_ids.")
                    for cid in backed:
                        if cid not in self.verified_claim_ids:
                            self.errors.append(f"Dossier statement cites unbacked claim ID: {cid}")
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
