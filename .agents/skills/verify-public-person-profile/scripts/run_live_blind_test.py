#!/usr/bin/env python3
"""
Targeted Real-Web Page Ingestion & Offline Replay Integration Runner (V4.7).
Captures specific targeted public academic web pages into a standard WARC 1.0 archive
storing normalized HTML text snapshots, performs character-level Evidence slice tracing,
resolves ambiguous entities, invokes the central deterministic state machine, and generates
the closed evidence ledger bundle for validation.

Note: This runner executes a targeted integration test with pre-specified URL fixtures,
not an unconstrained open-web blind test. The 0 false merges result is an empirical
observation on these specific fixtures.
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


LIVE_TARGETS = [
    {
        "url": "https://cira.yale.edu/people/xin-zhou-phd",
        "entity_type": "biostatistics_faculty",
        "description": "Assistant Professor of Biostatistics, Yale School of Public Health; CIRA affiliate; Ph.D. UNC Chapel Hill; Postdoc Harvard T.H. Chan.",
        "locator": "div.field-field-title p",
        "locator_type": LocatorType.CSS,
        "search_anchors": [
            ('<h1 class="title" id="page-title">Xin  Zhou, Ph.D.</h1>', 'high dimensional data analysis.</p>'),
            "Dr. Zhou is an assistant professor in the Department of Biostatistics at the Yale School of Public Health. He received his Ph.D. in Biostatistics from the University of North Carolina at Chapel Hill in 2015. Prior to arriving at Yale, Dr. Zhou was a Postdoc Fellow in the Departments of Biostatistics and Epidemiology at Harvard T.H. Chan School of Public Health. His research is focused on statistical and machine learning methods in precision medicine, measurement error correction, cluster randomized trials, and high dimensional data analysis.",
        ]
    },
    {
        "url": "https://medicine.yale.edu/profile/xin-zhou19/",
        "entity_type": "mhealth_faculty",
        "description": "Associate Research Scientist, Section of Infectious Diseases, Department of Internal Medicine / AIDS Program, Yale School of Medicine; Ph.D. SUNY Albany.",
        "locator": "script[type=\"application/ld+json\"]",
        "locator_type": LocatorType.CSS,
        "search_anchors": [
            '"name":"Xin Zhou","description":"I am a junior faculty in the Yale School of Medicine’s AIDS Program. I received my Ph.D. in Communication from SUNY at Albany. My research lie in the intersection of health communication, communication technology, and public health. My work investigates the influence of technology affordances and user engagement with mHealth technologies on health behavior change, and the design and implementation of communication technology for improving individuals’ well-being."',
            '"name":"Xin Zhou","description":"I am a junior faculty in the Yale School of Medicine&#x2019;s AIDS Program. I received my Ph.D. in Communication from SUNY at Albany.',
        ]
    },
    {
        "url": "https://github.com/xinzhoubiostat",
        "entity_type": "biostatistics_software",
        "description": "Developer of biostatistics software swdpower for stepped wedge designs.",
        "locator": "div.pinned-item-list-item-content",
        "locator_type": LocatorType.CSS,
        "search_anchors": [
            "Power calculation for SWDs with binary outcomes",
        ]
    }
]


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
    target_name: str = "Xin Zhou",
    output_dir: Optional[Path] = None,
    offline_corpus: Optional[Path] = None,
    hints: Optional[List[str]] = None,
    aliases: Optional[List[str]] = None,
) -> Tuple[Path, Dict]:
    """
    Targeted Real-Web Ingestion & Offline Replay Runner.
    Delegates strictly to canonical run_pipeline() to eliminate production path divergence.
    """
    crawl_errors: List[str] = []
    if output_dir:
        bundle_dir = output_dir if output_dir.name == "bundle" else output_dir / "bundle"
        run_dir = bundle_dir.parent
    else:
        run_dir = SKILL_DIR / "runs" / "live_xin_zhou"
        bundle_dir = run_dir / "bundle"
    run_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    warc_path = offline_corpus or (run_dir / "corpus.warc")
    if not warc_path.exists() or offline_corpus is None:
        fetch_live_warc(LIVE_TARGETS, warc_path, crawl_errors=crawl_errors)

    hints = hints or ["Yale"]
    aliases = aliases or ["xinzhoubiostat"]

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
    parser.add_argument("--name", type=str, default="Xin Zhou", help="Target person name.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory.")
    parser.add_argument("--offline-corpus", type=Path, default=None, help="Existing WARC path.")
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
