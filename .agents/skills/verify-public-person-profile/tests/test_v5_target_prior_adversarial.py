"""
V5 TargetPrior Vertical Disambiguation Adversarial Test Suite.
Tests:
1. Ray Liu Ambiguity vs Resolution (UC Berkeley / Google AI vs UMD Professor):
   - Name-Only Track: cleanly returns AMBIGUOUS_IDENTITY with 0 false merges.
   - Hinted Track (Berkeley): cleanly resolves to Berkeley candidate with 0 UMD claims.
   - Hinted Track (UMD): cleanly resolves to UMD candidate with 0 Berkeley claims.
2. Cannot-Link Preservation Invariant:
   - Conflicting cross-institution hints NEVER force-merge distinct candidate clusters.
3. Zero-Hallucination Invariant:
   - Fictitious prior hints NEVER fabricate ungrounded claims into claims.jsonl or dossier.json.
4. TargetPrior parsing unit tests.
"""

import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import pytest

from models.schemas import (
    FactPolarity,
    MachineRelation,
    RunOutcome,
    TargetPrior,
    TemporalStatus,
)
from core.run_profile import (
    compute_candidate_prior_affinity,
    determine_state_outcome,
    run_pipeline,
)


def make_warc_record(uri: str, html: str, warc_id: str) -> bytes:
    date_str = "2026-09-18T20:00:00Z"
    http_payload = (
        f"HTTP/1.1 200 OK\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Server: Apache\r\n"
        f"Content-Length: {len(html.encode('utf-8'))}\r\n"
        f"\r\n"
        f"{html}"
    ).encode("utf-8")

    warc_header = (
        f"WARC/1.0\r\n"
        f"WARC-Type: response\r\n"
        f"WARC-Record-ID: <{warc_id}>\r\n"
        f"WARC-Date: {date_str}\r\n"
        f"WARC-Target-URI: {uri}\r\n"
        f"Content-Length: {len(http_payload)}\r\n"
        f"\r\n"
    ).encode("latin-1")

    return warc_header + http_payload + b"\r\n\r\n"


@pytest.fixture
def ray_liu_warc(tmp_path):
    warc_file = tmp_path / "ray_liu_corpus.warc"
    p1 = (
        "<html><body><h1>Ray Liu</h1><p>Ray Liu earned his BS in Electrical Engineering & Computer Sciences "
        "from UC Berkeley in 2020. Ray Liu is a Software Engineer at Google.</p></body></html>"
    )
    p2 = (
        "<html><body><h1>Dr. Ray Liu</h1><p>Dr. Ray Liu is a Professor of Electrical Engineering "
        "at the University of Maryland. Dr. Ray Liu served as IEEE President.</p></body></html>"
    )
    rec1 = make_warc_record("https://eecs.berkeley.edu/alumni/ray-liu", p1, "urn:uuid:11111111-1111-1111-1111-111111111111")
    rec2 = make_warc_record("https://ece.umd.edu/faculty/ray-liu", p2, "urn:uuid:22222222-2222-2222-2222-222222222222")
    warc_file.write_bytes(rec1 + rec2)
    return warc_file


def test_target_prior_parsing_units():
    """Unit test: TargetPrior correctly extracts structured fields from text hints and aliases."""
    prior = TargetPrior.from_hints_and_aliases(
        target_name="Albert Zhao",
        hints=["Fall 2026 incoming Yale BME MS"],
        aliases=["Al Zhao"],
    )
    assert prior.target_name == "Albert Zhao"
    assert "Yale" in prior.known_affiliations
    assert "MS" in prior.known_education
    assert any("BME" in d for d in prior.known_domains)
    assert "Fall 2026" in prior.temporal_anchors
    assert "Al Zhao" in prior.known_aliases
    assert not prior.is_empty()

    empty_prior = TargetPrior.from_hints_and_aliases(target_name="Empty Person", hints=[], aliases=[])
    assert empty_prior.is_empty()


def test_ray_liu_name_only_track_ambiguous(ray_liu_warc, tmp_path):
    """Test 1A: In Name-Only track (no hints), Ray Liu must cleanly return AMBIGUOUS_IDENTITY with 0 false merges."""
    out_dir = tmp_path / "run_name_only"
    run_pipeline(
        target_name="Ray Liu",
        hints=[],
        output_dir=out_dir,
        offline_corpus=ray_liu_warc,
        query_budget=5,
    )

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == RunOutcome.AMBIGUOUS_IDENTITY.value

    # Check candidates
    cands = [json.loads(line) for line in (out_dir / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert len(cands) == 2, "Must produce exactly 2 distinct candidate clusters (Berkeley and UMD)"

    # Check dossier
    dossier = json.loads((out_dir / "dossier.json").read_text(encoding="utf-8"))
    assert dossier["candidate_entity_id"] is None
    assert len(dossier["statements"]) == 0
    assert len(dossier["ambiguous_candidates"]) == 2


def test_ray_liu_hinted_track_resolves_berkeley(ray_liu_warc, tmp_path):
    """Test 1B: In Hinted track with Berkeley hint, cleanly resolves to Berkeley candidate with 0 UMD claims."""
    out_dir = tmp_path / "run_hinted_berkeley"
    run_pipeline(
        target_name="Ray Liu",
        hints=["BS from UC Berkeley"],
        output_dir=out_dir,
        offline_corpus=ray_liu_warc,
        query_budget=5,
    )

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == RunOutcome.COMPLETED.value

    dossier = json.loads((out_dir / "dossier.json").read_text(encoding="utf-8"))
    assert dossier["candidate_entity_id"] is not None

    # Check that released claims belong strictly to the Berkeley candidate
    claims = [json.loads(line) for line in (out_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line]
    primary_claims = [c for c in claims if c["candidate_entity_id"] == dossier["candidate_entity_id"]]
    assert len(primary_claims) >= 1

    objects = [c["object_raw"] for c in primary_claims]
    assert any("Berkeley" in o or "Google" in o or "Electrical Engineering" in o for o in objects)
    assert not any("Maryland" in o or "IEEE" in o for o in objects), "Must not leak UMD claims into Berkeley dossier!"


def test_ray_liu_hinted_track_resolves_umd(ray_liu_warc, tmp_path):
    """Test 1C: In Hinted track with UMD hint, cleanly resolves to UMD candidate with 0 Berkeley claims."""
    out_dir = tmp_path / "run_hinted_umd"
    run_pipeline(
        target_name="Ray Liu",
        hints=["Professor at University of Maryland"],
        output_dir=out_dir,
        offline_corpus=ray_liu_warc,
        query_budget=5,
    )

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_outcome"] == RunOutcome.COMPLETED.value

    dossier = json.loads((out_dir / "dossier.json").read_text(encoding="utf-8"))
    assert dossier["candidate_entity_id"] is not None

    claims = [json.loads(line) for line in (out_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line]
    primary_claims = [c for c in claims if c["candidate_entity_id"] == dossier["candidate_entity_id"]]
    assert len(primary_claims) >= 1

    objects = [c["object_raw"] for c in primary_claims]
    assert any("Maryland" in o or "Professor" in o or "IEEE" in o for o in objects)
    assert not any("Google" in o for o in objects), "Must not leak Berkeley/Google claims into UMD dossier!"


def test_cannot_link_invariant_under_adversarial_prior(ray_liu_warc, tmp_path):
    """Test 2: A contradictory hint claiming both UMD and Berkeley must NOT force-merge the candidates."""
    out_dir = tmp_path / "run_adversarial_prior"
    run_pipeline(
        target_name="Ray Liu",
        hints=["Professor at University of Maryland and BS from UC Berkeley"],
        output_dir=out_dir,
        offline_corpus=ray_liu_warc,
        query_budget=5,
    )

    # Crucial invariant: ConstrainedUnionFind clusters must still be 2!
    cands = [json.loads(line) for line in (out_dir / "candidates.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert len(cands) == 2, "Cannot-Link must prevent merging distinct real entities regardless of prior hint!"


def test_zero_hallucination_invariant(ray_liu_warc, tmp_path):
    """Test 3: Fictitious prior hint must never fabricate an ungrounded claim."""
    out_dir = tmp_path / "run_fictitious_hint"
    run_pipeline(
        target_name="Ray Liu",
        hints=["Nobel Laureate in Physics 2024 at MIT"],
        output_dir=out_dir,
        offline_corpus=ray_liu_warc,
        query_budget=5,
    )

    claims = [json.loads(line) for line in (out_dir / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for c in claims:
        assert "Nobel" not in c["object_raw"], "Fictitious hint must not be fabricated into claims!"
        assert "MIT" not in c["object_raw"], "Fictitious hint must not be fabricated into claims!"
