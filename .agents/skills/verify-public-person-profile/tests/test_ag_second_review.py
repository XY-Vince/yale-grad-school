"""Regression checks for the second investigation workflow review."""
import json
from types import SimpleNamespace

import pytest
import requests

from core.collectors import base, discovery_engine
from scripts import bundle_files
from scripts import run_recall_profile
from scripts.verify_investigation_bundle import BundleVerifier


@pytest.mark.parametrize("row,excerpt", [
    ("<p><span>Alice Wang</span>, <span>BA</span></p>", "Alice Wang, BA"),
    ("<table><tr><td>Alice Wang</td><td>BA</td></tr></table>", "Alice Wang BA"),
])
def test_degree_context_across_tags_and_group_heading(tmp_path, row, excerpt):
    path = tmp_path / "program.html"
    path.write_text(
        '<title>University program</title><h1>Class of 2024</h1>'
        '<div class="view-grouping"><div class="view-grouping-header">Candidates for Degrees</div>'
        f'<div class="view-grouping-content"><h3>2024</h3>{row}</div></div>',
        encoding="utf-8",
    )
    assert BundleVerifier(tmp_path)._degree_candidacy_context(path, excerpt, None)


def test_degree_context_does_not_inherit_a_previous_group(tmp_path):
    path = tmp_path / "program.html"
    path.write_text(
        '<title>University program</title><h1>Class of 2024</h1>'
        '<div class="view-grouping"><div class="view-grouping-header">Candidates for Degrees</div>'
        '<p>Bob Jones, BA</p></div>'
        '<div class="view-grouping"><div class="view-grouping-header">Graduates</div>'
        '<p><span>Alice Wang</span>, <span>BA</span></p></div>',
        encoding="utf-8",
    )
    assert not BundleVerifier(tmp_path)._degree_candidacy_context(path, "Alice Wang, BA", None)


@pytest.mark.parametrize("section, expected", [
    ("<h2>Candidates for Degrees</h2><h3>2024</h3>", True),
    ("<h2>Candidates for Degrees</h2><p>Bob Jones, BA</p>"
     "<h2>Graduates</h2><h3>2024</h3>", False),
])
def test_degree_context_uses_heading_hierarchy_without_crossing_siblings(tmp_path, section, expected):
    path = tmp_path / "program.html"
    path.write_text(
        '<title>University program</title><h1>Class of 2024</h1>'
        f'{section}<p><span>Alice Wang</span>, <span>BA</span></p>',
        encoding="utf-8",
    )
    assert BundleVerifier(tmp_path)._degree_candidacy_context(path, "Alice Wang, BA", None) is expected


def test_prospective_award_is_not_conferral(tmp_path):
    path = tmp_path / "program.html"
    excerpt = "Alice Wang will be awarded a BA."
    path.write_text(f"<title>Candidates for Degrees</title><p>{excerpt}</p>", encoding="utf-8")
    assert BundleVerifier(tmp_path)._degree_candidacy_context(path, excerpt, None)


def test_legacy_unresolved_references_are_context_only_and_never_hide_unknown_sources(tmp_path):
    legacy = BundleVerifier(tmp_path, allow_legacy_missing_status=True)
    legacy.sources = {"SRC-01": {"http_status": 403, "evidence_status": "blocked"}}
    legacy.audit_lead_support("LEAD-01", {"status": "UNRESOLVED", "source_refs": ["SRC-01"]})
    assert not legacy.errors
    assert any("context only" in warning for warning in legacy.warnings)
    legacy.audit_lead_support("LEAD-02", {"status": "UNRESOLVED", "source_refs": ["SRC-99"]})
    assert any("unknown source" in error for error in legacy.errors)
    legacy.audit_lead_support("LEAD-03", {"status": "CORROBORATED", "source_refs": ["SRC-01"]})
    assert any("as support" in error for error in legacy.errors)


def test_discovery_fallback_uses_safe_post_and_records_each_attempt(monkeypatch):
    calls = []

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        if "bing.com" in url:
            return SimpleNamespace(status_code=403, content=b"blocked")
        body = (b'<a class="result__snippet" href="https://result.test/profile">'
                b'Example public profile</a>')
        return SimpleNamespace(status_code=200, content=body)

    monkeypatch.setattr(discovery_engine, "safe_fetch", fake_fetch)
    engine = discovery_engine.UniversalDiscoveryEngine()
    results, status, error = engine.search_web_endpoint("Alice Wang")
    assert status == "COMPLETED" and error is None
    assert results[0]["url"] == "https://result.test/profile"
    assert calls[0][1]["method"] == "GET"
    assert calls[1][1]["method"] == "POST" and calls[1][1]["data"] == b"q=Alice+Wang"
    assert [a["http_status"] for a in engine.last_search_attempts] == [403, 200]
    assert [a["status"] for a in engine.last_search_attempts] == ["BLOCKED", "COMPLETED"]


def test_discovery_parses_duckduckgo_result_link_when_href_precedes_class(monkeypatch):
    responses = [
        SimpleNamespace(status_code=403, content=b"blocked"),
        SimpleNamespace(status_code=200, content=(
            b'<a href="https://result.test/profile" class="result__a">Public profile</a>'
        )),
    ]
    monkeypatch.setattr(discovery_engine, "safe_fetch", lambda *args, **kwargs: responses.pop(0))
    results, status, _ = discovery_engine.UniversalDiscoveryEngine().search_web_endpoint("Alice Wang")
    assert status == "COMPLETED" and results[0]["url"] == "https://result.test/profile"


@pytest.mark.parametrize("reverse", [False, True])
def test_discovery_preserves_duckduckgo_snippet_and_separates_headers(monkeypatch, reverse):
    calls = []
    title = '<a class="result__a" href="https://result.test/profile">Alice Wang</a>'
    snippet = ('<a class="result__snippet" href="https://result.test/profile">'
               'Alice Wang researches <b>public health</b> at Example University.</a>')
    result_html = (snippet + title if reverse else title + snippet).encode()

    def fake_fetch(url, **kwargs):
        calls.append((url, kwargs))
        if "bing.com" in url:
            return SimpleNamespace(status_code=403, content=b"blocked")
        return SimpleNamespace(status_code=200, content=result_html)

    monkeypatch.setattr(discovery_engine, "safe_fetch", fake_fetch)
    results, status, _ = discovery_engine.UniversalDiscoveryEngine().search_web_endpoint(
        "Alice Wang", max_results=1
    )
    assert status == "COMPLETED"
    assert results == [{"url": "https://result.test/profile", "title": "Alice Wang",
                        "snippet": "Alice Wang researches public health at Example University."}]
    assert "Referer" not in calls[0][1]["headers"]
    assert "Content-Type" not in calls[0][1]["headers"]
    assert calls[1][1]["headers"]["Referer"] == "https://html.duckduckgo.com/"
    assert calls[1][1]["headers"]["Content-Type"] == "application/x-www-form-urlencoded"


def test_discovery_associates_nested_snippet_with_redirected_result(monkeypatch):
    responses = [
        SimpleNamespace(status_code=403, content=b"blocked"),
        SimpleNamespace(status_code=200, content=(
            b'<div class="result"><a class="result__a" '
            b'href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fresult.test%2Fprofile">Title</a>'
            b'<div class="result__snippet">Detailed <b>profile</b> text.</div></div>'
            b'<a class="result__a" href="https://other.test/">Other</a>'
        )),
    ]
    monkeypatch.setattr(discovery_engine, "safe_fetch", lambda *args, **kwargs: responses.pop(0))
    results, status, _ = discovery_engine.UniversalDiscoveryEngine().search_web_endpoint(
        "Alice Wang", max_results=1
    )
    assert status == "COMPLETED"
    assert results == [{"url": "https://result.test/profile", "title": "Title",
                        "snippet": "Detailed profile text."}]


@pytest.mark.parametrize("responses,expected", [
    ([SimpleNamespace(status_code=403, content=b""), requests.Timeout("timeout")], "FAILED"),
    ([SimpleNamespace(status_code=403, content=b""), SimpleNamespace(status_code=429, content=b"")], "BLOCKED"),
    ([SimpleNamespace(status_code=200, content=b"<html>changed layout</html>"),
      requests.Timeout("timeout")], "FAILED"),
    ([SimpleNamespace(status_code=200, content=b"No results found"),
      requests.Timeout("timeout")], "COMPLETED"),
])
def test_discovery_distinguishes_no_results_from_failure(monkeypatch, responses, expected):
    def fake_fetch(*args, **kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(discovery_engine, "safe_fetch", fake_fetch)
    engine = discovery_engine.UniversalDiscoveryEngine()
    results, status, error = engine.search_web_endpoint("Alice Wang")
    assert results == [] and status == expected
    assert error


def test_post_redirect_drops_body_on_303_and_rejects_cross_origin_307(monkeypatch):
    calls = []
    answers = []

    class FakeResponse:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {"Location": location} if location else {}

        def iter_content(self, chunk_size):
            yield b"ok"

        def close(self):
            pass

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def mount(self, *args):
            pass

        def get(self, url, **kwargs):
            calls.append(("GET", url, kwargs, self.trust_env))
            return answers.pop(0)

        def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs, self.trust_env))
            return answers.pop(0)

    monkeypatch.setattr(base.requests, "Session", FakeSession)
    monkeypatch.setattr(base, "validate_safe_url", lambda url: (True, url, "8.8.8.8"))
    answers[:] = [FakeResponse(303, "/results"), FakeResponse(200)]
    response = base.safe_fetch("https://research.test/search", method="POST", data=b"q=alice",
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response._content == b"ok"
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert calls[0][2]["data"] == b"q=alice"
    assert "Content-Type" not in calls[1][2]["headers"]
    assert all(call[3] is False for call in calls)
    calls.clear()
    answers[:] = [FakeResponse(307, "https://other.test/receive")]
    with pytest.raises(base.SSRFSecurityError, match="Cross-origin"):
        base.safe_fetch("https://research.test/search", method="POST", data=b"q=alice")
    assert len(calls) == 1


def test_statement_metadata_preview_apply_and_conflict(tmp_path):
    claim = {"claim_id": "VCLM-01", "candidate_id": "CAND-01",
             "predicate": "affiliated_with", "object": "Yale University"}
    (tmp_path / "verified_claims.jsonl").write_text(json.dumps(claim) + "\n", encoding="utf-8")
    path = tmp_path / "dossier.json"
    original = {"statements": [{"statement_id": "STMT-01", "rendered_text": "自然语言说明",
                                "backed_claim_ids": ["VCLM-01"]}]}
    path.write_text(json.dumps(original), encoding="utf-8")
    preview = bundle_files.align_statement_metadata(tmp_path)
    assert not preview["applied"] and preview["statements_to_update"]
    assert json.loads(path.read_text()) == original
    applied = bundle_files.align_statement_metadata(tmp_path, apply=True)
    assert applied["manifest_files_to_update"] == ["dossier.json"]
    statement = json.loads(path.read_text())["statements"][0]
    assert (statement["candidate_id"], statement["predicate"], statement["object"]) == (
        "CAND-01", "affiliated_with", "Yale University"
    )
    statement["object"] = "Harvard University"
    path.write_text(json.dumps({"statements": [statement]}), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        bundle_files.align_statement_metadata(tmp_path, apply=True)


@pytest.mark.parametrize("bullet", ["*", "-"])
def test_claim_bullet_flags_unrelated_two_character_chinese_object(tmp_path, bullet):
    verifier = BundleVerifier(tmp_path)
    verifier.claims = {"VCLM-01": {"object": "清华", "verbatim_excerpt": "Alice Wang works at 清华."}}
    verifier.verified_claim_ids = {"VCLM-01"}
    (tmp_path / "dossier.json").write_text(json.dumps({"statements": []}), encoding="utf-8")
    (tmp_path / "evidence_index.md").write_text("## VCLM-01\n", encoding="utf-8")
    (tmp_path / "recall_report.md").write_text(
        f"## Candidate Matrix\n{bullet} [VCLM-01](evidence_index.md#vclm-01) 任职北京大学\n",
        encoding="utf-8",
    )
    verifier.audit_dossier_and_report_closure()
    assert any("claim bullet" in warning for warning in verifier.warnings)


@pytest.mark.parametrize("resume", [False, True])
def test_legacy_runner_rejects_existing_bundle_before_discovery(tmp_path, monkeypatch, resume):
    output_dir = tmp_path / "existing"
    raw_dir = output_dir / "raw_sources"
    raw_dir.mkdir(parents=True)
    original = b"An existing investigation's raw response."
    (raw_dir / "source.html").write_bytes(original)
    (output_dir / "discovery_results.jsonl").write_bytes(b"existing discovery\n")

    def unexpected_discovery(*args, **kwargs):
        pytest.fail("The runner started discovery before checking the output directory")

    monkeypatch.setattr(discovery_engine.UniversalDiscoveryEngine, "run_discovery", unexpected_discovery)
    with pytest.raises((FileExistsError, ValueError)):
        run_recall_profile.run_recall_investigation(
            name="Alice Wang", clue="", output_dir=output_dir, resume=resume,
        )
    assert (raw_dir / "source.html").read_bytes() == original
    assert (output_dir / "discovery_results.jsonl").read_bytes() == b"existing discovery\n"


def test_unsupported_resume_does_not_create_output_directory(tmp_path):
    output_dir = tmp_path / "new"
    with pytest.raises(ValueError, match="--discovery-file"):
        run_recall_profile.run_recall_investigation(
            name="Alice Wang", clue="", output_dir=output_dir, resume=True,
        )
    assert not output_dir.exists()


@pytest.mark.parametrize("input_bytes", [
    b"",
    b'{"url":"https://research.test/profile","title":"A"}\n',
])
def test_curated_discovery_keeps_exact_input_and_never_falls_back_to_web(
    tmp_path, monkeypatch, input_bytes
):
    source = tmp_path / "input.jsonl"
    source.write_bytes(input_bytes)
    output_dir = tmp_path / "output"

    def unexpected_search(*args, **kwargs):
        pytest.fail("An explicitly supplied discovery file must not trigger live discovery")

    monkeypatch.setattr(discovery_engine.UniversalDiscoveryEngine, "search_web_endpoint", unexpected_search)
    engine = discovery_engine.UniversalDiscoveryEngine()
    records = engine.run_discovery("Alice Wang", [], output_dir, preloaded_file=source)
    assert (output_dir / "discovery_results.jsonl").read_bytes() == input_bytes
    assert len(records) == (1 if input_bytes else 0)
    assert engine.query_logs[0]["status"] == "LOADED"


def test_malformed_curated_discovery_does_not_start_web_search(tmp_path, monkeypatch):
    source = tmp_path / "input.jsonl"
    source.write_text("{broken json\n", encoding="utf-8")
    monkeypatch.setattr(
        discovery_engine.UniversalDiscoveryEngine, "search_web_endpoint",
        lambda *args, **kwargs: pytest.fail("Malformed input must not trigger live discovery"),
    )
    with pytest.raises(ValueError, match="Invalid discovery record"):
        discovery_engine.UniversalDiscoveryEngine().run_discovery(
            "Alice Wang", [], tmp_path / "output", preloaded_file=source,
        )


def test_no_extracted_claims_keeps_raw_sources_and_unresolved_leads(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    raw = b"<html><p>Alice Wang and another person are mentioned.</p></html>"
    url = "https://research.test/people"

    def discover(self, *args, **kwargs):
        self.query_logs.append({
            "backend": "Search", "query_text": "Alice Wang",
            "executed_at": "2026-11-15T00:00:00Z", "status": "COMPLETED",
        })
        return [{"url": url}]

    retriever = run_recall_profile.UniversalEvidenceRetriever
    monkeypatch.setattr(discovery_engine.UniversalDiscoveryEngine, "run_discovery", discover)
    monkeypatch.setattr(retriever, "fetch_web_url", lambda self, url: (200, raw, url))
    monkeypatch.setattr(retriever, "search_openalex_authors", lambda *args: (200, None, "", []))
    monkeypatch.setattr(retriever, "search_openalex_works", lambda *args: (200, None, "", []))
    monkeypatch.setattr(retriever, "search_crossref_works", lambda *args: (200, None, "", []))
    monkeypatch.setattr(retriever, "search_pubmed", lambda *args: [])
    monkeypatch.setattr(run_recall_profile, "extract_claims_from_web_document", lambda **kwargs: (
        [], {}, 1, set(), [{
            "description": "An ambiguous co-mention needs review.",
            "corroborating_source_ids": ["SRC-01"],
        }],
    ))
    run_recall_profile.run_recall_investigation("Alice Wang", "", output_dir=output_dir)

    inventory = json.loads((output_dir / "source_inventory.jsonl").read_text(encoding="utf-8"))
    assert (output_dir / inventory["local_path"]).read_bytes() == raw
    assert inventory["evidence_status"] == "unverified"
    assert inventory["evidence_use"] == "PENDING_REVIEW"
    assert inventory["fetched_at"] is None
    lead = json.loads((output_dir / "corroborated_leads.jsonl").read_text(encoding="utf-8"))
    assert lead["status"] == "UNRESOLVED" and lead["candidate_id"] is None
    assert lead["context_source_ids"] == ["SRC-01"]
    assert not (output_dir / "verified_claims.jsonl").read_text(encoding="utf-8")
    assert json.loads((output_dir / "manifest.json").read_text())["run_outcome"] == "INSUFFICIENT_EVIDENCE"
    verifier = BundleVerifier(output_dir)
    assert verifier.audit_all(), verifier.errors


def test_blocked_response_is_retained_but_not_processed_as_person_evidence(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    url = "https://research.test/people"
    raw = b"<html>Access denied. Alice Wang is a Professor.</html>"

    def discover(self, *args, **kwargs):
        self.query_logs.append({
            "backend": "Search", "query_text": "Alice Wang",
            "executed_at": "2026-11-15T00:00:00Z", "status": "COMPLETED",
        })
        return [{"url": url}]

    retriever = run_recall_profile.UniversalEvidenceRetriever
    monkeypatch.setattr(discovery_engine.UniversalDiscoveryEngine, "run_discovery", discover)
    monkeypatch.setattr(retriever, "fetch_web_url", lambda self, url: (403, raw, url))
    monkeypatch.setattr(retriever, "search_openalex_authors", lambda *args: (0, None, "", []))
    monkeypatch.setattr(retriever, "search_openalex_works", lambda *args: (0, None, "", []))
    monkeypatch.setattr(retriever, "search_crossref_works", lambda *args: (0, None, "", []))
    monkeypatch.setattr(retriever, "search_pubmed", lambda *args: [])
    monkeypatch.setattr(
        run_recall_profile, "extract_claims_from_web_document",
        lambda **kwargs: pytest.fail("An HTTP 403 response must not enter claim extraction"),
    )
    run_recall_profile.run_recall_investigation("Alice Wang", "", output_dir=output_dir)

    inventory = json.loads((output_dir / "source_inventory.jsonl").read_text(encoding="utf-8"))
    assert (output_dir / inventory["local_path"]).read_bytes() == raw
    assert inventory["http_status"] == 403 and inventory["evidence_status"] == "blocked"
    assert not (output_dir / "verified_claims.jsonl").read_text(encoding="utf-8")
    assert json.loads((output_dir / "manifest.json").read_text())["run_outcome"] == "COLLECTION_FAILED"
    question = json.loads((output_dir / "open_questions.jsonl").read_text(encoding="utf-8"))
    assert "failed or was blocked" in question["description"]
    assert "No public records found" not in question["description"]
    verifier = BundleVerifier(output_dir)
    assert verifier.audit_all(), verifier.errors
