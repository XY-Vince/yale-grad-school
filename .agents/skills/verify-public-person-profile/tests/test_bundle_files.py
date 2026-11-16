import json
from types import SimpleNamespace

import pytest
import requests

from scripts import bundle_files


def response(content=b"public response", status=200, url="https://example.org/final"):
    return SimpleNamespace(content=content, status_code=status, url=url)


def test_capture_preserves_each_query_and_reuses_only_identical_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle_files, "safe_fetch", lambda url, timeout: response())
    first = bundle_files.capture(tmp_path, "SRC-01", "https://example.org/one")
    second = bundle_files.capture(tmp_path, "SRC-02", "https://example.org/two")
    assert first["evidence_status"] == second["evidence_status"] == "unverified"
    assert first["local_path"] == second["local_path"]
    assert second["reused_identical_bytes"] is True
    assert len(bundle_files.read_jsonl(tmp_path / "query_logs.jsonl")) == 2
    assert len(bundle_files.read_jsonl(tmp_path / "source_inventory.jsonl")) == 2
    bundle_files.refresh_manifest(tmp_path, [], initialize=True, target_name="Example", outcome="COMPLETED")
    assert json.loads((tmp_path / "manifest.json").read_text())["files"][first["local_path"]]


def test_failed_fetch_records_failure_without_fabricating_source(tmp_path, monkeypatch):
    def fail(url, timeout):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(bundle_files, "safe_fetch", fail)
    result = bundle_files.capture(tmp_path, "SRC-01", "https://example.org/unavailable")
    assert result["status"] == "FAILED"
    assert bundle_files.read_jsonl(tmp_path / "query_logs.jsonl")[0]["http_status"] is None
    assert not (tmp_path / "source_inventory.jsonl").exists()
    assert not list((tmp_path / "raw_sources").iterdir())


def test_blocked_response_is_preserved_and_reported_as_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle_files, "safe_fetch", lambda url, timeout: response(b"blocked", 403))
    result = bundle_files.capture(tmp_path, "SRC-01", "https://example.org/blocked")
    assert result["status"] == "BLOCKED"
    assert result["evidence_status"] == "blocked"
    assert (tmp_path / result["local_path"]).read_bytes() == b"blocked"
    assert bundle_files.read_jsonl(tmp_path / "query_logs.jsonl")[0]["status"] == "BLOCKED"
    assert bundle_files.main([
        "capture", "--bundle-dir", str(tmp_path), "--source-id", "SRC-02",
        "--url", "https://example.org/also-blocked",
    ]) == 1


def test_manifest_updates_only_declared_files_and_never_reseals_changed_raw(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle_files, "safe_fetch", lambda url, timeout: response())
    record = bundle_files.capture(tmp_path, "SRC-01", "https://example.org/one")
    report = tmp_path / "recall_report.md"
    report.write_text("First version", encoding="utf-8")
    bundle_files.refresh_manifest(tmp_path, [], initialize=True, target_name="Example", outcome="COMPLETED")
    report.write_text("Edited version", encoding="utf-8")
    with pytest.raises(ValueError, match="Unexpected change"):
        bundle_files.refresh_manifest(tmp_path, [])
    bundle_files.refresh_manifest(tmp_path, ["recall_report.md"])
    (tmp_path / record["local_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Source bytes do not match"):
        bundle_files.refresh_manifest(tmp_path, [record["local_path"]])


def test_capture_does_not_overwrite_existing_source_id(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle_files, "safe_fetch", lambda url, timeout: response())
    bundle_files.capture(tmp_path, "SRC-01", "https://example.org/one")
    with pytest.raises(ValueError, match="already exists"):
        bundle_files.capture(tmp_path, "SRC-01", "https://example.org/two")
    assert len(bundle_files.read_jsonl(tmp_path / "query_logs.jsonl")) == 1
