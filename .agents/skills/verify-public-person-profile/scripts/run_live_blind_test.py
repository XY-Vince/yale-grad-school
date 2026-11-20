#!/usr/bin/env python3
"""
Targeted WARC replay integration runner.
The command requires a caller-supplied target and existing WARC; it does not
embed or automatically retrieve any person's source pages.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

from models.schemas import (
    CandidateEntity,
    Claim,
    ClusterAssignment,
    Dossier,
    DossierStatement,
    EntityMention,
    Evidence,
    EvidenceLocator,
    FactPolarity,
    LocatorType,
    MatchDecision,
    RunManifest,
    RunOutcome,
    SourceQualityClass,
    SourceSnapshot,
)
from core.collectors.warc_player import WarcPlayerCollector
from core.extractors.claim_extractor import extract_claims_from_evidence
from core.extractors.mention_extractor import extract_mentions_and_aliases
from core.render_dossier import render_dossier_markdown
from core.resolver import extract_organizations, resolve_mentions
from core.run_profile import run_pipeline
from scripts.validate_dossier import validate_bundle


def fetch_live_warc(targets: List[Dict], output_warc_path: Path, crawl_errors: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Performs live HTTP retrieval with standard browser headers and
    serializes responses as normalized HTML text snapshots into standard WARC 1.0.
    """
    output_warc_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    warc_records_info = {}
    with open(output_warc_path, "wb") as warc_f:
        for target in targets:
            url = target["url"]
            print(f"[LIVE FETCH] Requesting: {url} ...")
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                status_code = resp.status_code
                if status_code != 200:
                    err_msg = f"HTTP {status_code} for {url}"
                    print(f"  WARNING: {err_msg}")
                    if crawl_errors is not None:
                        crawl_errors.append(err_msg)
                raw_text = resp.text
            except Exception as e:
                err_msg = f"Fetch error for {url}: {e}"
                print(f"  ERROR: {err_msg}")
                if crawl_errors is not None:
                    crawl_errors.append(err_msg)
                continue

            payload_bytes = raw_text.encode("utf-8")
            sha256 = hashlib.sha256(payload_bytes).hexdigest()
            rec_uuid = f"urn:uuid:{uuid.uuid4()}"
            warc_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            http_header = (
                f"HTTP/1.1 {status_code} OK\r\n"
                f"Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(payload_bytes)}\r\n\r\n"
            ).encode("latin-1")

            block = http_header + payload_bytes
            warc_header = (
                f"WARC/1.0\r\n"
                f"WARC-Type: response\r\n"
                f"WARC-Record-ID: <{rec_uuid}>\r\n"
                f"WARC-Target-URI: {url}\r\n"
                f"WARC-Date: {warc_date}\r\n"
                f"Content-Type: application/http; msgtype=response\r\n"
                f"Content-Length: {len(block)}\r\n\r\n"
            ).encode("latin-1")

            warc_f.write(warc_header + block + b"\r\n\r\n")

            warc_records_info[url] = {
                "warc_record_id": f"<{rec_uuid}>",
                "html_text": raw_text,
                "sha256": sha256,
                "status_code": status_code,
                "target_meta": target,
            }
            print(f"  -> Captured {len(raw_text)} chars, SHA256: {sha256[:16]}, RecordID: <{rec_uuid}>")

    print(f"[WARC CREATED] Total size: {output_warc_path.stat().st_size} bytes at {output_warc_path}")
    return warc_records_info


def run_targeted_warc_replay(
    target_name: str = "",
    output_dir: Optional[Path] = None,
    offline_corpus: Optional[Path] = None,
    hints: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
) -> Tuple[Path, Dict]:
    """
    Targeted offline replay runner.
    Delegates strictly to canonical run_pipeline() to eliminate production path divergence.
    """
    if not target_name.strip():
        raise ValueError("target_name is required")
    if offline_corpus is None or not offline_corpus.is_file():
        raise ValueError("an existing offline_corpus WARC is required")
    if output_dir:
        bundle_dir = output_dir if output_dir.name == "bundle" else output_dir / "bundle"
        run_dir = bundle_dir.parent
    else:
        run_dir = SKILL_DIR / "runs" / "targeted_warc_replay"
        bundle_dir = run_dir / "bundle"
    run_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    warc_path = offline_corpus
    hints = hints or []
    aliases = aliases or []

    # Canonical execution via official run_pipeline() entry point (zero pipeline divergence)
    run_pipeline(
        target_name=target_name,
        hints=hints,
        output_dir=bundle_dir,
        offline_corpus=warc_path,
        aliases=aliases,
    )

    # Validate generated bundle against WARC archive
    val_res = validate_bundle(bundle_dir, warc_path=warc_path)
    return bundle_dir, val_res


# Backwards-compatible alias maintained strictly for legacy external and test suite callers;
# maps directly to the canonical run_targeted_warc_replay implementation.
run_live_blind_test = run_targeted_warc_replay


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Targeted WARC Replay Integration Test.")
    parser.add_argument("--name", type=str, required=True, help="Target person name.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory.")
    parser.add_argument("--offline-corpus", type=Path, required=True, help="Existing WARC path.")
    args = parser.parse_args()

    bundle_path, res = run_targeted_warc_replay(
        target_name=args.name,
        output_dir=args.output_dir,
        offline_corpus=args.offline_corpus,
    )
    print("\n[VALIDATION RESULT]")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res["is_valid"]:
        sys.exit(1)
