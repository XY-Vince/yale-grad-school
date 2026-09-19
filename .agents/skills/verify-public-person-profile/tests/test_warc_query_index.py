"""Deterministic query-index tests for offline WARC replay."""

import json
from pathlib import Path

import pytest

from core.collectors.warc_player import WarcPlayerCollector


def _warc_response(uri: str, body: str, record_id: str) -> bytes:
    payload = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        f"{body}"
    ).encode("utf-8")
    headers = (
        "WARC/1.0\r\n"
        "WARC-Type: response\r\n"
        f"WARC-Record-ID: <urn:uuid:{record_id}>\r\n"
        f"WARC-Target-URI: {uri}\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "\r\n"
    ).encode("ascii")
    return headers + payload + b"\r\n\r\n"


def _write_fixture(tmp_path: Path) -> Path:
    warc_path = tmp_path / "corpus.warc"
    warc_path.write_bytes(
        _warc_response(
            "https://example.edu/target",
            "<html>Alex Kim target profile shared token</html>",
            "00000000-0000-0000-0000-000000000001",
        )
        + _warc_response(
            "https://example.org/distractor",
            "<html>Alex Kim distractor profile shared token</html>",
            "00000000-0000-0000-0000-000000000002",
        )
    )
    return warc_path


def test_sidecar_query_index_controls_offline_search(tmp_path: Path):
    warc_path = _write_fixture(tmp_path)
    (tmp_path / "query_index.jsonl").write_text(
        json.dumps(
            {
                "query": "Alex Kim",
                "urls": ["https://example.edu/target"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    collector = WarcPlayerCollector(warc_path)

    assert [result["url"] for result in collector.search("  alex   KIM  ")] == [
        "https://example.edu/target"
    ]
    assert collector.search("unregistered query") == []


def test_query_index_rejects_url_absent_from_warc(tmp_path: Path):
    warc_path = _write_fixture(tmp_path)
    (tmp_path / "query_index.jsonl").write_text(
        json.dumps(
            {
                "query": "Alex Kim",
                "urls": ["https://missing.example/person"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="absent from WARC"):
        WarcPlayerCollector(warc_path)


def test_warc_without_query_index_retains_content_search(tmp_path: Path):
    warc_path = _write_fixture(tmp_path)

    collector = WarcPlayerCollector(warc_path)

    assert len(collector.search("Alex Kim")) == 2
