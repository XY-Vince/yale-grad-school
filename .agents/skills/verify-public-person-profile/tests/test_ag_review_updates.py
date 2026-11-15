"""Focused regressions for capture boundaries and investigation-bundle review."""
import json
import socket

import pytest
import requests

from core.collectors import base
from scripts import bundle_files
from scripts.lint_wording import lint_text
from scripts.run_recall_profile import UniversalEvidenceRetriever
from scripts.verify_investigation_bundle import BundleVerifier, evidence_ineligibility


def dns_answer(*addresses):
    return [(socket.AF_INET6 if ":" in addr else socket.AF_INET,
             socket.SOCK_STREAM, 6, "", (addr, 443)) for addr in addresses]


class FakeResponse:
    def __init__(self, status=200, chunks=(b"hello",), headers=None):
        self.status_code = status
        self.headers = headers or {}
        self.chunks = chunks
        self.closed = False
        self.url = None

    def iter_content(self, chunk_size):
        yield from self.chunks

    def close(self):
        self.closed = True


def fake_sessions(monkeypatch, responses):
    calls = []

    class FakeSession:
        def __init__(self):
            self.trust_env = True
            self.mounts = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def mount(self, prefix, adapter):
            self.mounts[prefix] = adapter

        def get(self, url, **kwargs):
            calls.append((url, kwargs, self.trust_env, self.mounts))
            return responses[len(calls) - 1]

    monkeypatch.setattr(base.requests, "Session", FakeSession)
    return calls


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "100.64.0.1", "::1", "ff02::1"])
def test_disallows_all_nonpublic_and_multicast_dns_answers(monkeypatch, address):
    monkeypatch.setattr(base.socket, "getaddrinfo", lambda *a, **k: dns_answer(address))
    assert not base.validate_safe_url("https://research.test/")[0]


def test_mixed_public_and_private_dns_answers_are_rejected(monkeypatch):
    monkeypatch.setattr(base.socket, "getaddrinfo", lambda *a, **k: dns_answer("8.8.8.8", "10.0.0.1"))
    assert not base.validate_safe_url("https://research.test/")[0]


def test_dns_failure_is_not_reported_as_ssrf(monkeypatch, tmp_path):
    def failed(*args, **kwargs):
        raise socket.gaierror("no DNS")

    monkeypatch.setattr(base.socket, "getaddrinfo", failed)
    with pytest.raises(requests.ConnectionError, match="DNS resolution failed"):
        base.safe_fetch("https://research.test/")
    result = bundle_files.capture(tmp_path, "SRC-01", "https://research.test/")
    assert result["status"] == "FAILED"
    assert "ConnectionError" in result["error"]


def test_pins_public_address_preserves_host_and_tls_identity_and_disables_proxies(monkeypatch):
    answers = []

    def resolve(host, *args, **kwargs):
        answers.append(host)
        return dns_answer("8.8.8.8")

    monkeypatch.setattr(base.socket, "getaddrinfo", resolve)
    response = FakeResponse(chunks=(b"first", b"second"))
    calls = fake_sessions(monkeypatch, [response])
    captured = base.safe_fetch("https://research.test:8443/article?q=1")
    url, options, trust_env, mounts = calls[0]
    assert answers == ["research.test"]
    assert url == "https://8.8.8.8:8443/article?q=1"
    assert options["headers"]["Host"] == "research.test:8443"
    assert options["stream"] is True and trust_env is False
    assert mounts["https://"].poolmanager.connection_pool_kw["assert_hostname"] == "research.test"
    assert mounts["https://"].poolmanager.connection_pool_kw["server_hostname"] == "research.test"
    assert captured.url == "https://research.test:8443/article?q=1"
    assert captured._content == b"firstsecond" and response.closed


def test_redirect_to_private_address_is_checked_before_connecting(monkeypatch):
    def resolve(host, *args, **kwargs):
        return dns_answer("8.8.8.8" if host == "public.test" else "127.0.0.1")

    monkeypatch.setattr(base.socket, "getaddrinfo", resolve)
    first = FakeResponse(302, headers={"Location": "http://internal.test/admin"})
    calls = fake_sessions(monkeypatch, [first])
    with pytest.raises(base.SSRFSecurityError):
        base.safe_fetch("https://public.test/")
    assert len(calls) == 1 and first.closed


@pytest.mark.parametrize("headers,chunks", [
    ({"Content-Length": "6"}, (b"x",)),
    ({}, (b"abc", b"def")),
])
def test_response_limit_applies_to_declared_and_streamed_bytes(monkeypatch, headers, chunks):
    monkeypatch.setattr(base.socket, "getaddrinfo", lambda *a, **k: dns_answer("8.8.8.8"))
    response = FakeResponse(headers=headers, chunks=chunks)
    fake_sessions(monkeypatch, [response])
    with pytest.raises(base.ResponseTooLargeError):
        base.safe_fetch("https://public.test/", max_response_bytes=5)
    assert response.closed


def test_legacy_retriever_uses_shared_safe_fetch_and_records_security_separately(monkeypatch):
    from scripts import run_recall_profile

    retriever = UniversalEvidenceRetriever()

    def blocked(*args, **kwargs):
        raise base.SSRFSecurityError("private")

    monkeypatch.setattr(run_recall_profile, "safe_fetch", blocked)
    assert retriever._execute_request("WEB", "http://private.test/")[0] == 0
    assert retriever.query_logs[-1]["http_status"] == 0
    assert retriever.query_logs[-1]["status"] == "BLOCKED_SSRF"

    def dns_failure(*args, **kwargs):
        raise requests.ConnectionError("DNS failure")

    monkeypatch.setattr(run_recall_profile, "safe_fetch", dns_failure)
    assert retriever._execute_request("WEB", "https://unavailable.test/")[0] == 0
    assert retriever.query_logs[-1]["status"] == "FAILED"


@pytest.mark.parametrize("source", [
    {"http_status": 200}, {"http_status": 200, "evidence_status": "usable", "evidence_use": "PENDING_REVIEW"},
    {"http_status": 200, "evidence_status": "verified", "evidence_use": "DISAMBIGUATION_ONLY"},
])
def test_unreviewed_source_cannot_silently_become_positive_evidence(source):
    assert evidence_ineligibility(source)


def test_legacy_missing_status_requires_explicit_opt_in_and_warning(tmp_path):
    verifier = BundleVerifier(tmp_path, allow_legacy_missing_status=True)
    assert verifier._evidence_ineligibility({"http_status": 200}, "SRC-01") is None
    assert any("manual review" in message for message in verifier.warnings)


def test_unresolved_lead_must_not_label_sources_as_positive_support(tmp_path):
    verifier = BundleVerifier(tmp_path)
    verifier.sources = {"SRC-01": {"http_status": 200, "evidence_status": "usable"}}
    verifier.audit_lead_support("LEAD-01", {
        "status": "UNRESOLVED", "corroborating_source_ids": ["SRC-01"],
    })
    assert any("not CORROBORATED" in message for message in verifier.errors)


@pytest.mark.parametrize("excerpt,expected", [
    ("Alice Wang, BA", True),
    ("Alice Wang received a Bachelor of Arts degree.", False),
])
def test_html_degree_row_inherits_candidate_page_title(tmp_path, excerpt, expected):
    path = tmp_path / "commencement.html"
    path.write_text(
        "<html><head><title>Candidates for Degrees</title></head>"
        f"<body><h1>Class of 2024</h1><section><p>{excerpt}</p></section></body></html>"
    )
    assert BundleVerifier(tmp_path)._degree_candidacy_context(path, excerpt, None) is expected


def test_html_later_candidate_section_does_not_retroactively_apply(tmp_path):
    path = tmp_path / "report.html"
    path.write_text(
        "<title>University news</title><h1>Graduates</h1><p>Alice Wang, BA</p>"
        "<h2>Candidates for Degrees</h2><p>Bob Smith, BA</p>"
    )
    assert not BundleVerifier(tmp_path)._degree_candidacy_context(path, "Alice Wang, BA", None)


def test_html_degree_row_inherits_accessible_section_heading(tmp_path):
    path = tmp_path / "report.html"
    path.write_text(
        "<title>University program</title><h1>Commencement</h1>"
        '<section><div role="heading">Candidates for Degrees</div><p>Alice Wang, BA</p></section>'
    )
    assert BundleVerifier(tmp_path)._degree_candidacy_context(path, "Alice Wang, BA", None)


def test_evidence_link_rules_include_bare_labels_index_paths_and_case(tmp_path):
    index = tmp_path / "evidence_index.md"
    index.write_text('<a id="VCLM-01"></a>\n[raw](missing.html)\n')
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(index, index.read_text())
    assert any("missing or outside" in error for error in verifier.errors)
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", "[VCLM-01]")
    assert any("must link" in error for error in verifier.errors)
    verifier = BundleVerifier(tmp_path)
    verifier.audit_evidence_links(tmp_path / "recall_report.md", "[VCLM-01](evidence_index.md#VCLM-01)")
    assert not verifier.errors


def test_linter_flags_overstated_disproof():
    assert lint_text("该页彻底证伪所有同名者")


def test_dossier_natural_language_is_review_hint_but_structured_mismatch_is_error(tmp_path):
    verifier = BundleVerifier(tmp_path)
    verifier.claims = {"VCLM-01": {
        "subject": "Alice Wang", "candidate_id": "CAND-01",
        "predicate": "affiliated_with", "object": "Yale University",
        "verbatim_excerpt": "Alice Wang works at Yale University.",
    }}
    verifier.verified_claim_ids = {"VCLM-01"}
    dossier = {"primary_candidate_id": "CAND-01", "statements": [{
        "statement_id": "STMT-01", "candidate_id": "CAND-01",
        "rendered_text": "Alice Wang reportedly works at Yale University.",
        "backed_claim_ids": ["VCLM-01"],
    }]}
    (tmp_path / "dossier.json").write_text(json.dumps(dossier))
    (tmp_path / "evidence_index.md").write_text("## VCLM-01\n")
    (tmp_path / "recall_report.md").write_text(
        "## Candidate Matrix\n[Alice](https://example.org) [VCLM-01](evidence_index.md#vclm-01)"
    )
    verifier.audit_dossier_and_report_closure()
    assert not verifier.errors
    dossier["statements"][0]["object"] = "Harvard University"
    (tmp_path / "dossier.json").write_text(json.dumps(dossier))
    verifier = BundleVerifier(tmp_path)
    verifier.claims = {"VCLM-01": {
        "subject": "Alice Wang", "candidate_id": "CAND-01",
        "predicate": "affiliated_with", "object": "Yale University",
    }}
    verifier.verified_claim_ids = {"VCLM-01"}
    verifier.audit_dossier_and_report_closure()
    assert any("object differs" in error for error in verifier.errors)
