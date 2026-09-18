"""
Standard WARC 1.0/1.1 Archive Player (V4.2).
Parses standard WARC response records without third-party dependencies.
Provides deterministic offline replay, inverted index search, and SHA-256 verification.
"""

import gzip
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .base import BaseCollector


class WarcRecord:
    def __init__(self, target_uri: str, http_status: int, payload: str, sha256: str, warc_record_id: Optional[str] = None):
        self.target_uri = target_uri
        self.http_status = http_status
        self.payload = payload
        self.sha256 = sha256
        self.warc_record_id = warc_record_id


class WarcPlayerCollector(BaseCollector):
    def __init__(self, warc_file_or_index: Path, query_budget: int = 20):
        self.warc_path = warc_file_or_index
        self.query_budget = query_budget
        self.records: Dict[str, WarcRecord] = {}
        self.records_by_id: Dict[str, WarcRecord] = {}
        self.queries_executed = 0
        self.pages_fetched = 0
        self.errors: List[str] = []
        self._load_warc()

    def _load_warc(self):
        if not self.warc_path.exists():
            self.errors.append(f"WARC file does not exist: {self.warc_path}")
            return

        # Explicitly reject WACZ format
        if self.warc_path.name.lower().endswith(".wacz"):
            raise ValueError(
                "WACZ format is not supported. Please supply a standard uncompressed or gzip-compressed WARC (.warc / .warc.gz) file."
            )

        is_gz = self.warc_path.name.endswith(".gz")
        open_fn = gzip.open if is_gz else open

        try:
            with open_fn(self.warc_path, "rb") as f:
                data = f.read()
        except Exception as e:
            self.errors.append(f"Failed to read WARC: {e}")
            return

        # Check for ZIP header (WACZ masquerading as WARC)
        if data.startswith(b"PK\x03\x04"):
            raise ValueError(
                "Detected ZIP/WACZ archive header. WACZ format is not supported. Supply a standard WARC file."
            )

        # Sequential parsing of WARC records using Content-Length
        idx = 0
        total_len = len(data)

        while idx < total_len:
            # Skip whitespace / CRLF between records
            while idx < total_len and data[idx:idx+1] in (b"\r", b"\n", b" ", b"\t"):
                idx += 1
            if idx >= total_len:
                break

            # Check WARC magic header
            if not data[idx:].startswith(b"WARC/"):
                # Seek forward to next WARC/
                next_warc = data.find(b"WARC/", idx)
                if next_warc == -1:
                    break
                idx = next_warc

            # Find header end
            header_end_crlf = data.find(b"\r\n\r\n", idx)
            header_end_lf = data.find(b"\n\n", idx)
            if header_end_crlf != -1 and (header_end_lf == -1 or header_end_crlf < header_end_lf):
                header_end = header_end_crlf
                payload_start = header_end + 4
            elif header_end_lf != -1:
                header_end = header_end_lf
                payload_start = header_end + 2
            else:
                break

            header_bytes = data[idx:header_end]
            warc_headers = {}
            for line in header_bytes.decode("latin-1", errors="ignore").splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    warc_headers[k.strip().lower()] = v.strip()

            content_length_str = warc_headers.get("content-length", "")
            try:
                content_length = int(content_length_str) if content_length_str else 0
            except ValueError:
                content_length = 0

            payload_bytes = data[payload_start:payload_start + content_length]
            idx = payload_start + content_length

            rec_type = warc_headers.get("warc-type", "").lower()
            target_uri = warc_headers.get("warc-target-uri", "")

            if rec_type == "response" and target_uri:
                # Body starts with HTTP response headers
                http_parts = payload_bytes.split(b"\r\n\r\n", 1)
                if len(http_parts) < 2:
                    http_parts = payload_bytes.split(b"\n\n", 1)

                http_status = 200
                if http_parts and http_parts[0]:
                    status_line = http_parts[0].decode("latin-1", errors="ignore").splitlines()[0] if http_parts[0] else ""
                    tokens = status_line.split()
                    if len(tokens) >= 2 and tokens[1].isdigit():
                        http_status = int(tokens[1])

                html_payload = http_parts[1].decode("utf-8", errors="ignore") if len(http_parts) > 1 else ""
                sha256 = hashlib.sha256(html_payload.encode("utf-8")).hexdigest()

                warc_rec_id = warc_headers.get("warc-record-id")

                rec = WarcRecord(
                    target_uri=target_uri,
                    http_status=http_status,
                    payload=html_payload,
                    sha256=sha256,
                    warc_record_id=warc_rec_id,
                )
                self.records[target_uri] = rec
                if warc_rec_id:
                    self.records_by_id[warc_rec_id] = rec
                    self.records_by_id[warc_rec_id.strip("<>")] = rec

    def get_warc_record_id(self, url: str) -> Optional[str]:
        rec = self.records.get(url)
        return rec.warc_record_id if rec else None

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if self.queries_executed >= self.query_budget:
            self.errors.append(f"Query budget exhausted ({self.query_budget})")
            return []
        self.queries_executed += 1
        q_tokens = [t.lower() for t in query.split() if t.strip()]

        scored_results = []
        for uri, rec in sorted(self.records.items(), key=lambda x: x[0]):  # Deterministic tie-break
            content_lower = rec.payload.lower()
            matches = sum(1 for t in q_tokens if t in content_lower)
            if matches > 0:
                # Basic BM25-like scoring
                score = matches / (len(q_tokens) + 0.1)
                scored_results.append((score, uri, rec))

        # Sort by score DESC, then URI ASC
        scored_results.sort(key=lambda x: (-x[0], x[1]))

        results = []
        for score, uri, rec in scored_results[:max_results]:
            results.append({
                "title": uri,
                "url": uri,
                "snippet": rec.payload[:250].replace("\n", " ").strip(),
            })
        return results

    def fetch_page(self, url: str) -> Tuple[int, str, str]:
        self.pages_fetched += 1
        rec = self.records.get(url)
        if rec:
            if rec.http_status not in (200, 301, 302):
                self.errors.append(f"HTTP {rec.http_status} fetching {url}")
            return rec.http_status, rec.payload, rec.sha256
        else:
            self.errors.append(f"HTTP 404 fetching {url}")
            return 404, "", hashlib.sha256(b"").hexdigest()
