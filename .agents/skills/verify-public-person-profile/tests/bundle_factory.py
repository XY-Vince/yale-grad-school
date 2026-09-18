"""
Legitimate Bundle Factory for V4.6 Testing.
Constructs 100% schema-compliant, structurally valid dossier bundles that pass validate_bundle,
ensuring adversarial tests evaluate core algorithmic mechanisms without pre-gate short-circuiting.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def create_valid_bundle(
    bundle_dir: Path,
    target_name: str = "Alice Smith",
    excerpt: Optional[str] = None,
    claim_predicate: str = "holds_position",
    claim_object: str = "Professor",
    claim_temporal: str = "current",
    claim_polarity: str = "affirmative",
    custom_clause: Optional[str] = None,
    adjudication_status: str = "unresolved",
    raw_name_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a structurally sound, 100% valid bundle passing all validate_bundle checks.
    Allows customizing excerpt, claims, and mentions for behavioral adversarial testing.
    """
    bundle_dir.mkdir(parents=True, exist_ok=True)

    name_in_text = raw_name_text if raw_name_text is not None else target_name
    if excerpt is None:
        excerpt = f"<html><body>{name_in_text} is a {claim_object} at Stanford University.</body></html>"

    source_id = "SRC-01"
    evidence_id = "EV-01"
    mention_id = "MEN-01"
    cluster_id = "CL-01"
    candidate_id = "CAND-01"
    claim_id = "CLM-01"
    dossier_id = "DOS-01"

    # Find character coordinates of name_in_text inside excerpt
    c_start = excerpt.find(name_in_text)
    if c_start < 0:
        c_start = 0
        name_in_text = excerpt[:min(len(name_in_text), len(excerpt))]
    c_end = c_start + len(name_in_text)
    if c_end <= c_start:
        c_end = c_start + 1

    mention_key = hashlib.sha256(f"{source_id}:{c_start}:{c_end}".encode("utf-8")).hexdigest()[:16]
    excerpt_sha256 = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()

    # Context snippet
    context_snippet = excerpt[max(0, c_start - 10) : min(len(excerpt), c_end + 30)]
    if name_in_text not in context_snippet:
        context_snippet = name_in_text

    # 1. sources.jsonl
    src_sha = excerpt_sha256
    sources = [
        {
            "source_id": source_id,
            "url": "https://example.org/profile",
            "publisher": "example.org",
            "content_sha256": src_sha,
            "http_status": 200,
        }
    ]
    with open(bundle_dir / "sources.jsonl", "w", encoding="utf-8") as f:
        for s in sources:
            f.write(json.dumps(s) + "\n")

    # 2. evidence.jsonl
    evidence = [
        {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "verbatim_excerpt": excerpt,
            "locator": {"locator_type": "css", "selector_or_page": "body"},
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "source_quality_class": "class_a",
            "raw_payload_sha256": excerpt_sha256,
            "char_start": 0,
            "char_end": len(excerpt),
        }
    ]
    with open(bundle_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
        for e in evidence:
            f.write(json.dumps(e) + "\n")

    # 3. mentions.jsonl
    mentions = [
        {
            "mention_id": mention_id,
            "raw_name_text": name_in_text,
            "source_id": source_id,
            "evidence_id": evidence_id,
            "context_snippet": context_snippet,
            "char_start": c_start,
            "char_end": c_end,
            "mention_key": mention_key,
            "inferred_affiliations": ["stanford university"],
            "alias_hypotheses": [
                {
                    "alias_value": name_in_text,
                    "origin_type": "source_stated",
                    "verification_status": "verified",
                    "verification_source_id": source_id,
                }
            ],
        }
    ]
    with open(bundle_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
        for m in mentions:
            f.write(json.dumps(m) + "\n")

    # 4. clusters.jsonl
    clusters = [
        {
            "cluster_id": cluster_id,
            "mention_ids": [mention_id],
            "clustering_method": "constrained_union_find",
            "threshold_used": 0.85,
        }
    ]
    with open(bundle_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
        for c in clusters:
            f.write(json.dumps(c) + "\n")

    # 5. candidates.jsonl
    candidates = [
        {
            "candidate_entity_id": candidate_id,
            "proposed_cluster_id": cluster_id,
            "mention_ids": [mention_id],
        }
    ]
    with open(bundle_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
        for cd in candidates:
            f.write(json.dumps(cd) + "\n")

    # 6. matches.jsonl
    with open(bundle_dir / "matches.jsonl", "w", encoding="utf-8") as f:
        f.write("")

    # 7. claims.jsonl
    verbatim_clause = custom_clause if custom_clause is not None else excerpt
    if verbatim_clause not in excerpt:
        clause_span_start = 0
        clause_span_end = len(excerpt)
        verbatim_clause = excerpt
    else:
        clause_span_start = excerpt.find(verbatim_clause)
        clause_span_end = clause_span_start + len(verbatim_clause)

    obj_idx = verbatim_clause.find(claim_object)
    if obj_idx >= 0:
        obj_abs_start = clause_span_start + obj_idx
        obj_abs_end = obj_abs_start + len(claim_object)
        rel_s = min(c_start, obj_abs_start)
        rel_e = max(c_end, obj_abs_end)
    else:
        rel_s = clause_span_start
        rel_e = clause_span_end

    claims = [
        {
            "claim_id": claim_id,
            "candidate_entity_id": candidate_id,
            "subject_mention_id": mention_id,
            "predicate": claim_predicate,
            "object_raw": claim_object,
            "polarity": claim_polarity,
            "temporal_status": claim_temporal,
            "adjudication_status": adjudication_status,
            "valid_from": None,
            "valid_to": None,
            "as_of": "2026-09-08",
            "extraction_confidence": 0.95,
            "evidence_ids": [evidence_id],
            "support_clauses": [
                {
                    "evidence_id": evidence_id,
                    "subject_mention_id": mention_id,
                    "clause_span_start": clause_span_start,
                    "clause_span_end": clause_span_end,
                    "verbatim_clause": verbatim_clause,
                    "relation_span_start": rel_s,
                    "relation_span_end": rel_e,
                    "provenance_level": "relation",
                }
            ],
        }
    ]
    with open(bundle_dir / "claims.jsonl", "w", encoding="utf-8") as f:
        for cl in claims:
            f.write(json.dumps(cl) + "\n")

    # 8. dossier.json
    dossier = {
        "dossier_id": dossier_id,
        "candidate_entity_id": candidate_id,
        "proposed_cluster_id": cluster_id,
        "ambiguous_candidates": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "statements": [
            {
                "statement_id": "STMT-01",
                "section": "Positions",
                "rendered_text": f"{target_name} is a {claim_object}",
                "backed_claim_ids": [claim_id],
            }
        ],
    }
    with open(bundle_dir / "dossier.json", "w", encoding="utf-8") as f:
        json.dump(dossier, f, indent=2)

    # 9. dossier.md
    with open(bundle_dir / "dossier.md", "w", encoding="utf-8") as f:
        f.write(f"# Dossier: {target_name}\nCandidate: {candidate_id}\nCluster: {cluster_id}\n")

    # 10. manifest.json
    manifest = {
        "run_id": "RUN-TEST-01",
        "target_name": target_name,
        "tool_version": "4.6.0",
        "model_name": "bundle-factory",
        "query_budget": 10,
        "queries_executed": 1,
        "pages_fetched": 1,
        "execution_time_seconds": 0.5,
        "run_outcome": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(bundle_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "source_id": source_id,
        "evidence_id": evidence_id,
        "mention_id": mention_id,
        "cluster_id": cluster_id,
        "candidate_id": candidate_id,
        "claim_id": claim_id,
        "mention_key": mention_key,
    }
