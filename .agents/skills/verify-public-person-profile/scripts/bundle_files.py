#!/usr/bin/env python3
"""Capture public responses and maintain bundle file manifests.

These operations record bytes and metadata. They do not verify who a person is
or whether a source supports a claim.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.collectors.base import SSRFSecurityError, safe_fetch


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path, item):
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(item, ensure_ascii=False) + "\n")


def bundle_path(bundle, relative):
    root = bundle.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root or path.relative_to(root).as_posix() != relative:
        raise ValueError(f"Path is outside the bundle or is not canonical: {relative}")
    return path


def audit_registered_sources(bundle):
    paths = set()
    ids = set()
    for item in read_jsonl(bundle / "source_inventory.jsonl"):
        if item.get("source_id") in ids:
            raise ValueError(f"Duplicate source ID: {item.get('source_id')}")
        ids.add(item.get("source_id"))
        path = bundle_path(bundle, item["local_path"])
        paths.add(path)
        data = path.read_bytes()
        expected = item.get("raw_bytes_sha256") or item.get("sha256")
        if not expected or sha256(data) != expected.lower():
            raise ValueError(f"Source bytes do not match inventory: {item.get('source_id')}")
        if item.get("byte_size") is not None and len(data) != item["byte_size"]:
            raise ValueError(f"Source size does not match inventory: {item.get('source_id')}")
    raw_dir = bundle / "raw_sources"
    if raw_dir.exists():
        for path in raw_dir.rglob("*"):
            if path.is_file() and not path.name.startswith(".") and path.resolve() not in paths:
                raise ValueError(f"Raw source is not registered: {path.relative_to(bundle)}")


def capture(bundle, source_id, url, extension=".html", timeout=15.0):
    if not re.fullmatch(r"SRC-[A-Za-z0-9_-]+", source_id):
        raise ValueError("source_id must begin with SRC- and contain letters, digits, _ or -")
    if not re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", extension):
        raise ValueError("extension must look like .html, .json or .pdf")
    bundle = bundle.resolve()
    bundle.mkdir(parents=True, exist_ok=True)
    raw_dir = bundle / "raw_sources"
    raw_dir.mkdir(exist_ok=True)
    inventory = bundle / "source_inventory.jsonl"
    log_path = bundle / "query_logs.jsonl"
    records = read_jsonl(inventory)
    if any(item.get("source_id") == source_id for item in records):
        raise ValueError(f"Source ID already exists: {source_id}")
    raw_path = bundle_path(bundle, f"raw_sources/{source_id}{extension}")
    if raw_path.exists():
        raise ValueError(f"Refusing to overwrite raw response: {raw_path}")

    timestamp = datetime.now(timezone.utc).isoformat()
    log = {"query_text": url, "executed_at": timestamp, "backend": "safe_fetch"}
    try:
        response = safe_fetch(url, timeout=timeout)
    except (requests.RequestException, SSRFSecurityError, OSError, ValueError) as exc:
        status = "BLOCKED" if isinstance(exc, SSRFSecurityError) else "FAILED"
        log.update(status=status, http_status=None, error=f"{type(exc).__name__}: {exc}")
        append_jsonl(log_path, log)
        return {"status": status, "error": log["error"]}

    data = response.content
    digest = sha256(data)
    duplicate = None
    for item in records:
        if item.get("raw_bytes_sha256") == digest:
            prior = bundle_path(bundle, item["local_path"])
            if prior.is_file() and sha256(prior.read_bytes()) == digest:
                duplicate = item["local_path"]
                break
    if duplicate is None:
        with raw_path.open("xb") as output:
            output.write(data)
        relative_path = str(raw_path.relative_to(bundle))
    else:
        relative_path = duplicate
    status = response.status_code
    evidence_status = "unverified" if status == 200 else "blocked" if status in (401, 403, 429) else "failed"
    query_status = "EXECUTED" if status == 200 else "BLOCKED" if status in (401, 403, 429) else "FAILED"
    record = {
        "source_id": source_id,
        "url": url,
        "final_url": response.url,
        "fetched_at": timestamp,
        "http_status": status,
        "raw_bytes_sha256": digest,
        "byte_size": len(data),
        "local_path": relative_path,
        "source_class": "UNCLASSIFIED",
        "evidence_status": evidence_status,
        "evidence_use": "PENDING_REVIEW",
    }
    append_jsonl(inventory, record)
    log.update(
        status=query_status,
        http_status=status,
        final_url=response.url,
        source_id=source_id,
        result_count=None,
    )
    append_jsonl(log_path, log)
    return {
        "status": query_status,
        "source_id": source_id,
        "http_status": status,
        "local_path": relative_path,
        "reused_identical_bytes": duplicate is not None,
        "evidence_status": evidence_status,
        "manifest_files_to_update": [relative_path, "source_inventory.jsonl", "query_logs.jsonl"],
    }


def refresh_manifest(bundle, includes, initialize=False, target_name=None, outcome=None):
    bundle = bundle.resolve()
    manifest_path = bundle / "manifest.json"
    if initialize:
        if manifest_path.exists():
            raise ValueError("Refusing to replace an existing manifest.")
        if not target_name or not outcome:
            raise ValueError("--target-name and --outcome are required when initializing.")
        manifest = {
            "bundle_version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "target_name": target_name,
            "run_outcome": outcome,
            "provenance": "agent_synthesized",
            "files": {},
        }
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    audit_registered_sources(bundle)
    files = manifest.setdefault("files", {})
    selected = set(includes)
    for relative in selected:
        path = bundle_path(bundle, relative)
        if relative == "manifest.json" or not path.is_file():
            raise ValueError(f"Selected path is not an eligible file: {relative}")

    disk_files = {
        str(path.relative_to(bundle))
        for path in bundle.rglob("*")
        if path.is_file() and path.name != "manifest.json" and not path.name.startswith(".")
        and not path.name.endswith(".pyc") and "__pycache__" not in path.parts
    }
    if initialize:
        selected = disk_files
    else:
        unexpected = disk_files - set(files) - selected
        if unexpected:
            raise ValueError(f"Unregistered files must be explicitly included: {sorted(unexpected)}")
        for relative, metadata in files.items():
            path = bundle_path(bundle, relative)
            if not path.is_file():
                raise ValueError(f"Previously registered file missing: {relative}")
            data = path.read_bytes()
            changed = sha256(data) != metadata.get("sha256") or len(data) != metadata.get("byte_size")
            if changed and (relative not in selected or relative.startswith("raw_sources/")):
                raise ValueError(f"Unexpected change to registered file: {relative}")

    for relative in sorted(selected):
        data = bundle_path(bundle, relative).read_bytes()
        files[relative] = {"byte_size": len(data), "sha256": sha256(data)}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"manifest": str(manifest_path), "updated_files": sorted(selected)}


def align_statement_metadata(bundle, apply=False):
    """Copy unambiguous claim metadata into statements; prose still needs review."""
    bundle = bundle.resolve()
    claims = {}
    for claim in read_jsonl(bundle / "verified_claims.jsonl"):
        claim_id = claim.get("claim_id")
        if not claim_id or claim_id in claims:
            raise ValueError(f"Missing or duplicate claim ID: {claim_id}")
        claims[claim_id] = claim
    dossier_path = bundle / "dossier.json"
    dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    changed, skipped = [], []
    for statement in dossier.get("statements", []):
        statement_id = statement.get("statement_id", "<unnamed>")
        refs = statement.get("backed_claim_ids")
        if not isinstance(refs, list) or not refs or any(ref not in claims for ref in refs):
            raise ValueError(f"Statement {statement_id} has missing or unknown claim references")
        entries = [
            (claims[ref].get("candidate_id"), claims[ref].get("predicate"),
             claims[ref].get("object") or claims[ref].get("object_raw"))
            for ref in refs
        ]
        if any(not all(isinstance(value, str) and value.strip() for value in entry) for entry in entries):
            skipped.append({"statement_id": statement_id, "reason": "claim metadata incomplete"})
            continue
        if len(set(entries)) != 1:
            skipped.append({"statement_id": statement_id, "reason": "claims have different metadata"})
            continue
        values = dict(zip(("candidate_id", "predicate", "object"), entries[0]))
        for field, value in values.items():
            if statement.get(field) and statement[field] != value:
                raise ValueError(f"Statement {statement_id} {field} conflicts with its claim")
        missing = {field: value for field, value in values.items() if not statement.get(field)}
        if missing:
            statement.update(missing)
            changed.append({"statement_id": statement_id, "fields": sorted(missing)})
    if apply and changed:
        dossier_path.write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "applied": bool(apply and changed),
        "statements_to_update": changed,
        "skipped": skipped,
        "manifest_files_to_update": ["dossier.json"] if apply and changed else [],
        "note": "Copied metadata is not semantic verification of rendered text.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cap = sub.add_parser("capture", help="Record one HTTP response and its query log.")
    cap.add_argument("--bundle-dir", type=Path, required=True)
    cap.add_argument("--source-id", required=True)
    cap.add_argument("--url", required=True)
    cap.add_argument("--extension", default=".html")
    cap.add_argument("--timeout", type=float, default=15.0)
    manifest = sub.add_parser("manifest", help="Initialize or update explicitly selected bundle files.")
    manifest.add_argument("--bundle-dir", type=Path, required=True)
    manifest.add_argument("--include", action="append", default=[])
    manifest.add_argument("--initialize", action="store_true")
    manifest.add_argument("--target-name")
    manifest.add_argument("--outcome")
    align = sub.add_parser("align-statements", help="Preview claim metadata for dossier statements.")
    align.add_argument("--bundle-dir", type=Path, required=True)
    align.add_argument("--apply", action="store_true", help="Write unambiguous missing metadata.")
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture(args.bundle_dir, args.source_id, args.url, args.extension, args.timeout)
            exit_code = 0 if result.get("status") == "EXECUTED" else 1
        elif args.command == "manifest":
            result = refresh_manifest(args.bundle_dir, args.include, args.initialize, args.target_name, args.outcome)
            exit_code = 0
        else:
            result = align_statement_metadata(args.bundle_dir, apply=args.apply)
            exit_code = 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
