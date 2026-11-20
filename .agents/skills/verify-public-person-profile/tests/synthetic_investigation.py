"""Small, explicitly synthetic investigation bundle for offline unit tests."""

import hashlib
import json
from pathlib import Path


def make_synthetic_warc(path: Path) -> Path:
    """Write fabricated offline pages; no response was fetched from the network."""
    pages = [
        (
            "https://example.edu/faculty/alice",
            "<html><body><h1>Alice Example</h1>"
            "<p>Alice Example is a Professor at Stanford University. "
            "Alice Example studies precision medicine.</p>"
            "<p>Bob Example joined the seminar. Dr. Example spoke later.</p>"
            '<div role="dialog" class="overlay"><h2 class="overlay-title">'
            "Block or report Alice Example</h2></div></body></html>",
        ),
        (
            "https://example.edu/other/alice",
            "<html><body><h1>Alice Example</h1>"
            "<p>Alice Example is a Dean at Massachusetts Institute of Technology.</p>"
            "</body></html>",
        ),
    ]
    records = []
    for number, (url, html) in enumerate(pages, 1):
        payload = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n{html}".encode()
        header = (
            "WARC/1.0\r\n"
            "WARC-Type: response\r\n"
            f"WARC-Target-URI: {url}\r\n"
            f"WARC-Record-ID: <urn:uuid:00000000-0000-0000-0000-{number:012d}>\r\n"
            "WARC-Date: 2026-01-01T00:00:00Z\r\n"
            "Content-Type: application/http; msgtype=response\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n"
        ).encode()
        records.append(header + payload + b"\r\n\r\n")
    path.write_bytes(b"".join(records))
    return path


def make_synthetic_bundle(root: Path, *, extended: bool = False) -> Path:
    root.mkdir(parents=True)
    raw = root / "raw_sources"
    raw.mkdir()
    facts = [
        ("CAND-01", "holds_position", "Professor", "CURRENT", "Alice Example is a Professor."),
        ("CAND-02", "holds_position", "Dentist", "CURRENT", "Alice Example is a Dentist."),
    ]
    if extended:
        facts.extend([
            ("CAND-01", "graduated_from", "Example University", "HISTORICAL",
             "Alice Example graduated from Example University."),
            ("CAND-01", "received_degree", "M.S.", "HISTORICAL",
             "Alice Example received an M.S."),
            ("CAND-01", "expressed_interest_in", "Example Research Seminar", "STATED_FUTURE",
             "Alice Example expressed interest in the Example Research Seminar."),
            ("CAND-01", "acknowledged_research_resource", "Example Imaging Program", "HISTORICAL",
             "Alice Example acknowledged the Example Imaging Program."),
            ("CAND-02", "awarded_honor", "Example Prize", "HISTORICAL",
             "Alice Example received the Example Prize."),
        ])
    sources, claims, statements = [], [], []
    for number, (candidate_id, predicate, obj, temporal_status, excerpt) in enumerate(facts, 1):
        source_id = f"SRC-{number:02d}"
        relative = f"raw_sources/source-{number}.html"
        content = f"<html><body><p>{excerpt}</p></body></html>"
        (root / relative).write_text(content, encoding="utf-8")
        payload = (root / relative).read_bytes()
        sources.append({
            "source_id": source_id, "url": f"https://test.invalid/person/{number}",
            "final_url": f"https://test.invalid/person/{number}", "http_status": 200,
            "raw_bytes_sha256": hashlib.sha256(payload).hexdigest(),
            "byte_size": len(payload), "local_path": relative,
            "source_class": "CLASS_C", "evidence_status": "usable",
        })
        claim_id = f"VCLM-{number:02d}"
        claims.append({
            "claim_id": claim_id, "candidate_id": candidate_id,
            "subject": "Alice Example", "predicate": predicate, "object": obj,
            "source_id": source_id, "source_file": relative, "verbatim_excerpt": excerpt,
            "temporal_status": temporal_status, "evidence_strength": "S1",
        })
        statements.append({
            "statement_id": f"STMT-{number:02d}", "candidate_id": candidate_id,
            "rendered_text": f"Alice Example {predicate} {obj}",
            "backed_claim_ids": [claim_id],
        })

    def write_jsonl(name, rows):
        (root / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    write_jsonl("source_inventory.jsonl", sources)
    write_jsonl("verified_claims.jsonl", claims)
    write_jsonl("corroborated_leads.jsonl", [{
        "lead_id": "LEAD-01", "candidate_id": "CAND-01",
        "description": "Further identification is pending.", "status": "UNRESOLVED",
        "context_source_ids": ["SRC-01"],
    }])
    write_jsonl("open_questions.jsonl", [{
        "question_id": "OQ-01", "question": "Are the two records the same person?",
    }])
    write_jsonl("query_logs.jsonl", [{
        "query_text": "synthetic fixture query", "executed_at": "2026-01-01T00:00:00Z",
        "status": "EXECUTED",
    }])
    (root / "dossier.json").write_text(json.dumps({
        "target_name": "Alice Example", "primary_candidate_id": "CAND-01",
        "statements": statements,
    }, indent=2), encoding="utf-8")
    (root / "evidence_index.md").write_text(
        "".join(f"## {claim['claim_id']}\n\n" for claim in claims)
        + "## LEAD-01\n\n## OQ-01\n", encoding="utf-8",
    )
    (root / "recall_report.md").write_text(
        "## Candidate Matrix\n\n"
        + "".join(
            f"* [{claim['claim_id']}](evidence_index.md#{claim['claim_id'].lower()}) "
            f"Alice Example {claim['predicate']} {claim['object']}.\n"
            for claim in claims
        )
        + "* [LEAD-01](evidence_index.md#lead-01) Further identification is pending.\n"
        "* [OQ-01](evidence_index.md#oq-01) Are the two records the same person?\n",
        encoding="utf-8",
    )
    files = {}
    for path in root.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            files[str(path.relative_to(root))] = {
                "byte_size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            }
    (root / "manifest.json").write_text(json.dumps({
        "target_name": "Alice Example", "run_outcome": "COMPLETED",
        "fixture_type": "synthetic", "files": files,
    }, indent=2), encoding="utf-8")
    return root
