"""
Main Profiling Pipeline Runner (V4.4.1).
Executes blind public profile investigation with deterministic content SHA-256 IDs,
strict Evidence -> Mention -> Cluster -> Candidate -> Claim attribution closure,
primary candidate margin-based disambiguation, and mutually exclusive state machine.
"""

import argparse
import calendar
import hashlib
import json
import re
import time
import unicodedata
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.schemas import (
    AbstentionRecord,
    CandidateEntity,
    Claim,
    ClusterAssignment,
    ClusteringMethod,
    DatePrecision,
    DateWithPrecision,
    Dossier,
    DossierStatement,
    EntityMention,
    Evidence,
    EvidenceLocator,
    FactPolarity,
    LocatorType,
    MachineRelation,
    MatchDecision,
    RootBundle,
    RunManifest,
    RunOutcome,
    SourceQualityClass,
    SourceSnapshot,
    TemporalStatus,
    TargetPrior,
)


def get_date_bounds(dwp: Optional[DateWithPrecision]) -> Optional[Tuple[date, date]]:
    """Convert DateWithPrecision to (lower_bound, upper_bound) date tuple based on precision."""
    if not dwp:
        return None
    if hasattr(dwp, "get_bounds"):
        return dwp.get_bounds()
    d = dwp.date_value
    if isinstance(d, str):
        d = date.fromisoformat(d)
    prec = getattr(dwp, "precision", DatePrecision.DAY)
    if prec == DatePrecision.YEAR:
        return date(d.year, 1, 1), date(d.year, 12, 31)
    elif prec == DatePrecision.MONTH:
        last_day = calendar.monthrange(d.year, d.month)[1]
        return date(d.year, d.month, 1), date(d.year, d.month, last_day)
    return d, d


def check_temporal_overlap(c1: Claim, c2: Claim) -> bool:
    """
    Checks if two claims have overlapping validity periods.
    Priority:
    1. Explicit date bounds: If explicit date intervals are available, compare bounds.
       - Disjoint: end1 < start2 or end2 < start1 -> False (no contradiction).
       - Overlapping: If explicit date bounds overlap, return True (contradiction),
         even if one claim has temporal_status=CURRENT and the other has FORMER.
    2. Single-bounded / partially explicit dates:
       - If one claim ended in the past and the other is CURRENT without dates, return False.
    3. Missing explicit dates:
       - Fallback to coarse-grained temporal_status:
         (CURRENT vs FORMER) -> False (disjoint).
         Otherwise -> True (potential overlap).
    """
    b_from1 = get_date_bounds(c1.valid_from)
    b_to1 = get_date_bounds(c1.valid_to)
    b_from2 = get_date_bounds(c2.valid_from)
    b_to2 = get_date_bounds(c2.valid_to)

    start1 = b_from1[0] if b_from1 else None
    end1 = b_to1[1] if b_to1 else None
    start2 = b_from2[0] if b_from2 else None
    end2 = b_to2[1] if b_to2 else None

    # Validate range boundaries: start <= end (fail-closed if inverted)
    if start1 and end1 and start1 > end1:
        raise ValueError(f"Invalid temporal interval in claim 1: start ({start1}) > end ({end1})")
    if start2 and end2 and start2 > end2:
        raise ValueError(f"Invalid temporal interval in claim 2: start ({start2}) > end ({end2})")

    has_dates1 = (start1 is not None or end1 is not None)
    has_dates2 = (start2 is not None or end2 is not None)

    # 1. Both claims have explicit date information:
    if has_dates1 and has_dates2:
        # Check for explicit disjoint intervals:
        if end1 and start2 and end1 < start2:
            return False
        if end2 and start1 and end2 < start1:
            return False
        # Explicit date intervals overlap
        return True

    # 2. One claim has explicit dates, the other does not:
    if has_dates1 and not has_dates2:
        if end1 and c2.temporal_status == TemporalStatus.CURRENT and c1.temporal_status == TemporalStatus.FORMER:
            return False
    elif has_dates2 and not has_dates1:
        if end2 and c1.temporal_status == TemporalStatus.CURRENT and c2.temporal_status == TemporalStatus.FORMER:
            return False

    # 3. Fallback when explicit dates are missing:
    if (
        (c1.temporal_status == TemporalStatus.FORMER and c2.temporal_status == TemporalStatus.CURRENT)
        or (c1.temporal_status == TemporalStatus.CURRENT and c2.temporal_status == TemporalStatus.FORMER)
    ):
        return False

    return True

from core.collectors.live_search import LiveSearchCollector
from core.collectors.warc_player import WarcPlayerCollector
from core.extractors.claim_extractor import extract_claims_from_evidence
from core.extractors.content_locator import classify_source_quality, locate_evidence_slices
from core.extractors.mention_extractor import extract_mentions_and_aliases
from core.render_dossier import render_dossier_markdown
from core.resolver import extract_organizations, resolve_mentions


def compute_semantic_bundle_fingerprint(
    sources: List[SourceSnapshot],
    evidence: List[Evidence],
    mentions: List[EntityMention],
    candidates: List[CandidateEntity],
    clusters: List[ClusterAssignment],
    claims: List[Claim],
) -> str:
    hasher = hashlib.sha256()
    for s in sorted(sources, key=lambda x: x.source_id):
        hasher.update(f"{s.source_id}:{s.url}:{s.content_sha256}".encode("utf-8"))
    for e in sorted(evidence, key=lambda x: x.evidence_id):
        hasher.update(f"{e.evidence_id}:{e.source_id}:{e.verbatim_excerpt[:50]}".encode("utf-8"))
    for m in sorted(mentions, key=lambda x: x.mention_id):
        hasher.update(f"{m.mention_id}:{m.raw_name_text}:{m.evidence_id}".encode("utf-8"))
    for cl in sorted(clusters, key=lambda x: x.cluster_id):
        hasher.update(f"{cl.cluster_id}:{sorted(cl.mention_ids)}".encode("utf-8"))
    for cand in sorted(candidates, key=lambda x: x.candidate_entity_id):
        hasher.update(f"{cand.candidate_entity_id}:{cand.proposed_cluster_id}:{sorted(cand.mention_ids)}".encode("utf-8"))
    for c in sorted(claims, key=lambda x: x.claim_id):
        hasher.update(f"{c.claim_id}:{c.candidate_entity_id}:{c.subject_mention_id}:{c.predicate}:{c.object_raw}".encode("utf-8"))
    return hasher.hexdigest()


def compute_bundle_fingerprint(bundle_dir: Path) -> str:
    """Computes SHA-256 fingerprint over semantic bundle files, ignoring runtime timestamps."""
    hasher = hashlib.sha256()
    for filename in ["sources.jsonl", "evidence.jsonl", "mentions.jsonl", "clusters.jsonl", "candidates.jsonl", "claims.jsonl", "dossier.json", "manifest.json"]:
        p = bundle_dir / filename
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Strip runtime timestamps and identifiers
                        for ts_field in ["retrieved_at", "observed_at", "generated_at", "execution_time_seconds", "run_id"]:
                            record.pop(ts_field, None)
                        if "abstention_records" in record:
                            for ar in record["abstention_records"]:
                                ar.pop("observed_at", None)
                        norm_str = json.dumps(record, sort_keys=True)
                        hasher.update(norm_str.encode("utf-8"))
                    except Exception:
                        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()




def compute_candidate_prior_affinity(
    candidate: CandidateEntity,
    mentions: List[EntityMention],
    evidence_list: List[Evidence],
    candidate_claims: List[Claim],
    prior: Optional[TargetPrior],
) -> float:
    """
    Computes semantic affinity score in [0.0, 1.0] between a candidate entity cluster
    and the user-specified TargetPrior.
    Checks:
    1. Inferred affiliations & verbatim text matches against known_affiliations.
    2. Educational degree matches against known_education.
    3. Temporal anchor matches against temporal_anchors.
    4. Domain matches against known_domains.
    5. Exact/token matches against raw_hints.
    6. Alias matches against known_aliases.
    """
    if not prior or prior.is_empty():
        return 0.0

    cand_m_ids = set(candidate.mention_ids)
    cand_mentions = [m for m in mentions if m.mention_id in cand_m_ids]
    cand_ev_ids = {m.evidence_id for m in cand_mentions}
    cand_evidence = [e for e in evidence_list if e.evidence_id in cand_ev_ids]

    texts = []
    for m in cand_mentions:
        texts.append(m.raw_name_text)
        texts.append(m.context_snippet)
        texts.extend(m.inferred_affiliations)
    for ev in cand_evidence:
        texts.append(ev.verbatim_excerpt)
    for c in candidate_claims:
        texts.append(c.object_raw)
        texts.append(c.predicate)

    combined_text = " ".join(texts).lower()

    score = 0.0
    max_possible = 0.0

    # 1. Affiliation matches (Weight: 2.0)
    if prior.known_affiliations:
        max_possible += 2.0
        aff_hit = False
        AFFILIATION_SYNONYMS = {
            "umich": ["university of michigan", "michigan", "umich"],
            "uc berkeley": ["berkeley", "university of california berkeley", "uc berkeley", "cal"],
            "umd": ["university of maryland", "umd"],
            "cmu": ["carnegie mellon", "cmu"],
            "mit": ["massachusetts institute of technology", "mit"],
            "uiuc": ["university of illinois", "uiuc"],
            "upenn": ["university of pennsylvania", "upenn", "penn"],
            "nyu": ["new york university", "nyu"],
            "pku": ["peking university", "pku", "beida", "北京大学"],
        }
        for aff in prior.known_affiliations:
            aff_norm = aff.lower().strip()
            synonyms = AFFILIATION_SYNONYMS.get(aff_norm, [aff_norm])
            if any(
                syn in combined_text
                or any(syn in inf.lower() for m in cand_mentions for inf in m.inferred_affiliations)
                for syn in synonyms
            ):
                aff_hit = True
                break
        if aff_hit:
            score += 2.0

    # 2. Education matches (Weight: 1.5)
    if prior.known_education:
        max_possible += 1.5
        edu_hit = False
        for edu in prior.known_education:
            if re.search(rf"\b{re.escape(edu.lower())}\b", combined_text):
                edu_hit = True
                break
        if edu_hit:
            score += 1.5

    # 3. Temporal anchors (Weight: 1.0)
    if prior.temporal_anchors:
        max_possible += 1.0
        temp_hit = False
        for temp in prior.temporal_anchors:
            if re.search(rf"\b{re.escape(temp.lower())}\b", combined_text):
                temp_hit = True
                break
        if temp_hit:
            score += 1.0

    # 4. Domains (Weight: 1.0)
    if prior.known_domains:
        max_possible += 1.0
        dom_hit = False
        for dom in prior.known_domains:
            if dom.lower() in combined_text:
                dom_hit = True
                break
        if dom_hit:
            score += 1.0

    # 5. Raw hints tokens / phrases (Weight: 1.5)
    if prior.raw_hints:
        max_possible += 1.5
        raw_hit = False
        for h in prior.raw_hints:
            h_low = h.lower().strip()
            if h_low and h_low in combined_text:
                raw_hit = True
                break
            h_toks = [t for t in re.split(r"\W+", h_low) if len(t) >= 2 and t not in {"from", "at", "in", "and", "the"}]
            if h_toks and all(t in combined_text for t in h_toks):
                raw_hit = True
                break
        if raw_hit:
            score += 1.5

    # 6. Known aliases (Weight: 2.0)
    if prior.known_aliases:
        max_possible += 2.0
        alias_hit = False
        for alias in prior.known_aliases:
            a_low = alias.lower().strip()
            if a_low and any(a_low == m.raw_name_text.lower().strip() for m in cand_mentions):
                alias_hit = True
                break
        if alias_hit:
            score += 2.0

    if max_possible == 0.0:
        return 0.0

    return min(1.0, score / max_possible)


def determine_state_outcome(
    has_structural_error: bool = False,
    crawl_errors: Optional[List[str]] = None,
    pages_fetched: int = 0,
    candidates: Optional[List[CandidateEntity]] = None,
    claims: Optional[List[Claim]] = None,
    search_has_results: bool = True,
    budget_exhausted: bool = False,
    is_ambiguous: bool = False,
    decisions: Optional[List[MatchDecision]] = None,
    mentions: Optional[List[EntityMention]] = None,
    evidence_list: Optional[List[Evidence]] = None,
    target_prior: Optional[TargetPrior] = None,
) -> Tuple[RunOutcome, Optional[str], List[str]]:
    """
    Deterministic State Machine Decision (S1 - S7) with V5 TargetPrior Disambiguation.
    Single authoritative decision source. Enforces:
    1. Review edges across candidate clusters must NEVER accompany COMPLETED unless resolved by Prior.
    2. Cannot-Link or multiple substantiated candidates require AMBIGUOUS_IDENTITY unless resolved by Prior.
    3. Contradictions are evaluated strictly per candidate_entity_id with temporal overlap.
    4. Prior affinity selects among valid candidate clusters without hallucinating claims.
    Returns (outcome, primary_candidate_id, ambiguous_candidates).
    """
    crawl_errors = crawl_errors or []
    candidates = candidates or []
    claims = claims or []
    decisions = decisions or []

    if has_structural_error:
        return RunOutcome.FAILED, None, []

    if (crawl_errors and pages_fetched == 0) or any("403" in str(e) or "500" in str(e) for e in crawl_errors):
        return RunOutcome.COLLECTION_FAILED, None, []

    if budget_exhausted and not claims:
        return RunOutcome.BUDGET_EXHAUSTED, None, []

    # Contradictory evidence check:
    # Scoped strictly per candidate_entity_id with normalized object and temporal overlap check.
    # Cross-candidate contradictory statements must NOT be treated as entity-internal contradictions.
    claims_by_cand: Dict[str, List[Claim]] = {}
    for c in claims:
        claims_by_cand.setdefault(c.candidate_entity_id, []).append(c)

    for cand_id, cand_claims in claims_by_cand.items():
        aff_claims = [c for c in cand_claims if c.polarity == FactPolarity.AFFIRMATIVE]
        neg_claims = [c for c in cand_claims if c.polarity == FactPolarity.NEGATIVE]
        for ac in aff_claims:
            for nc in neg_claims:
                if (
                    ac.predicate == nc.predicate
                    and ac.object_raw.lower().strip() == nc.object_raw.lower().strip()
                ):
                    if check_temporal_overlap(ac, nc):
                        return RunOutcome.CONTRADICTORY_EVIDENCE, None, []

    if not claims or pages_fetched == 0:
        return RunOutcome.INSUFFICIENT_EVIDENCE, None, []

    # Map mention_id to candidate_entity_id
    m2cand: Dict[str, str] = {}
    for cand in candidates:
        for m_id in cand.mention_ids:
            m2cand[m_id] = cand.candidate_entity_id

    # Check cross-candidate decision edges
    has_review_edge = False
    has_cannot_link_edge = False
    for dec in decisions:
        c1 = m2cand.get(dec.source_mention_id)
        c2 = m2cand.get(dec.target_mention_id)
        if c1 and c2 and c1 != c2:
            if dec.machine_relation == MachineRelation.REVIEW:
                has_review_edge = True
            elif dec.machine_relation == MachineRelation.NONMATCH or "cannot-link" in dec.explanation.lower():
                has_cannot_link_edge = True

    m2source: Dict[str, str] = {}
    if mentions:
        for m in mentions:
            m2source[m.mention_id] = m.source_id

    if len(candidates) > 1:
        substantiated_cands = []
        cand_scores = []
        for cand in candidates:
            c_claims = [c for c in claims if c.candidate_entity_id == cand.candidate_entity_id]
            cand_sources = {m2source.get(m_id) for m_id in cand.mention_ids if m2source.get(m_id)}
            source_count = len(cand_sources) if cand_sources else len(cand.mention_ids)
            score = source_count * 1.0 + len(c_claims) * 2.0
            cand_scores.append((score, cand.candidate_entity_id, len(c_claims)))
            if len(c_claims) > 0 or source_count >= 2:
                substantiated_cands.append(cand.candidate_entity_id)

        # --- V5 TargetPrior Vertical Disambiguation ---
        has_active_prior = bool(target_prior and not target_prior.is_empty())
        if has_active_prior:
            prior_scores = []
            for cand in candidates:
                c_claims = [c for c in claims if c.candidate_entity_id == cand.candidate_entity_id]
                aff = compute_candidate_prior_affinity(
                    candidate=cand,
                    mentions=mentions or [],
                    evidence_list=evidence_list or [],
                    candidate_claims=c_claims,
                    prior=target_prior,
                )
                cand_sources = {m2source.get(m_id) for m_id in cand.mention_ids if m2source.get(m_id)}
                source_count = len(cand_sources) if cand_sources else len(cand.mention_ids)
                prior_scores.append((aff, len(c_claims), source_count, cand.candidate_entity_id))

            prior_scores.sort(key=lambda x: (-x[0], -x[1], -x[2]))
            top_aff, top_claims, top_sources, top_id = prior_scores[0]
            second_aff = prior_scores[1][0] if len(prior_scores) > 1 else 0.0

            # Disambiguation Criterion:
            # Solid prior affinity (>= 0.35) and clear margin over runner-up (>= 0.20)
            # Grounded in real evidence (claims or sources)
            if top_aff >= 0.35 and (top_aff - second_aff) >= 0.20 and (top_claims > 0 or top_sources >= 1):
                other_cand_ids = [c.candidate_entity_id for c in candidates if c.candidate_entity_id != top_id]
                return RunOutcome.COMPLETED, top_id, other_cand_ids

        # Invariant: Review edges must NEVER accompany COMPLETED when no prior resolves them!
        if has_review_edge:
            return RunOutcome.AMBIGUOUS_IDENTITY, None, [c.candidate_entity_id for c in candidates]

        # Invariant: Cannot-Link across distinct candidate entities requires AMBIGUOUS_IDENTITY without resolving prior
        if has_cannot_link_edge:
            return RunOutcome.AMBIGUOUS_IDENTITY, None, [c.candidate_entity_id for c in candidates]

        if is_ambiguous or len(substantiated_cands) >= 2:
            return RunOutcome.AMBIGUOUS_IDENTITY, None, [c.candidate_entity_id for c in candidates]

        cand_scores.sort(key=lambda x: -x[0])
        if len(cand_scores) >= 2:
            s1, id1, n1 = cand_scores[0]
            s2, id2, n2 = cand_scores[1]
            total = s1 + s2
            margin = (s1 - s2) / total if total > 0 else 0.0
            if margin < 0.20 or (n1 > 0 and n2 > 0):
                return RunOutcome.AMBIGUOUS_IDENTITY, None, [c.candidate_entity_id for c in candidates]
            else:
                return RunOutcome.COMPLETED, id1, []

    primary_id = candidates[0].candidate_entity_id if candidates else None
    return RunOutcome.COMPLETED, primary_id, []


def route_and_extract_claims(
    evidence_list: List[Evidence],
    mentions_list: List[EntityMention],
    candidates: List[CandidateEntity],
    default_target_name: Optional[str] = None,
) -> List[Claim]:
    """
    Phase 3 Production Claim Routing Layer:
    Groups mentions per evidence by resolved candidate entity, and invokes claim extraction
    strictly bound to the subject mention and candidate entity.
    Guarantees strict attribution closure: each Claim's candidate_entity_id and subject_mention_id
    map to the resolved cluster and evidence.
    """
    mention_to_cand: Dict[str, CandidateEntity] = {}
    for cand in candidates:
        for m_id in cand.mention_ids:
            mention_to_cand[m_id] = cand

    all_claims: List[Claim] = []
    seen_claim_keys = set()

    def semantic_claim_key(claim: Claim) -> Tuple[object, ...]:
        normalized_object = re.sub(
            r"\s+",
            " ",
            unicodedata.normalize("NFKC", claim.object_raw).casefold(),
        ).strip()

        def date_key(value: Optional[DateWithPrecision]) -> Optional[Tuple[str, str]]:
            if value is None:
                return None
            return str(value.date_value), value.precision.value

        return (
            claim.candidate_entity_id,
            claim.predicate,
            normalized_object,
            claim.object_norm_id,
            claim.polarity.value,
            claim.temporal_status.value,
            date_key(claim.valid_from),
            date_key(claim.valid_to),
        )

    for ev in evidence_list:
        ev_mentions = [m for m in mentions_list if m.evidence_id == ev.evidence_id]
        if not ev_mentions:
            continue

        cand_id_map = {
            m.mention_id: mention_to_cand[m.mention_id].candidate_entity_id
            for m in ev_mentions if m.mention_id in mention_to_cand
        }

        ev_claims = extract_claims_from_evidence(
            evidence=ev,
            candidate_entity_id=None,
            subject_mention_id=None,
            target_name=default_target_name,
            evidence_mentions=ev_mentions,
            mention_to_cand_id=cand_id_map,
        )

        for c in ev_claims:
            ck = semantic_claim_key(c)
            if ck not in seen_claim_keys:
                seen_claim_keys.add(ck)
                all_claims.append(c)

    return all_claims


def run_pipeline(
    target_name: str,
    hints: List[str],
    output_dir: Path,
    offline_corpus: Optional[Path] = None,
    query_budget: int = 20,
    aliases: Optional[List[str]] = None,
    target_prior: Optional[TargetPrior] = None,
    enable_target_prior: bool = False,
) -> Path:
    start_time = time.time()
    if enable_target_prior:
        if target_prior is None:
            target_prior = TargetPrior.from_hints_and_aliases(target_name, hints=hints, aliases=aliases)
    else:
        target_prior = None
    query_sig = f"{target_name}:{query_budget}:{sorted(hints)}:{sorted(aliases or [])}"
    run_id = f"RUN-{hashlib.sha256(query_sig.encode('utf-8')).hexdigest()[:12]}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize collector
    if offline_corpus and offline_corpus.exists():
        collector = WarcPlayerCollector(offline_corpus, query_budget=query_budget)
    else:
        collector = LiveSearchCollector(query_budget=query_budget)

    # Phase 1: Search and Ingestion
    queries = [target_name] + [f"{target_name} {h}" for h in hints]
    if aliases:
        for a in aliases:
            if a != target_name:
                queries.append(a)
                queries.extend([f"{a} {h}" for h in hints])
    raw_search_results = []
    for q in queries:
        if collector.queries_executed >= query_budget:
            break
        raw_search_results.extend(collector.search(q, max_results=3))

    seen_urls = set()
    search_results = []
    for item in raw_search_results:
        u = item.get("url")
        if u and u not in seen_urls:
            seen_urls.add(u)
            search_results.append(item)

    sources: List[SourceSnapshot] = []
    seen_src_ids = set()
    evidence_list: List[Evidence] = []
    mentions_list: List[EntityMention] = []

    pages_attempted = 0
    pages_200_count = 0
    source_names_by_surname: Dict[str, Dict[str, Set[str]]] = {}
    source_profile_containers: Dict[str, Any] = {}

    # Ingest search results
    for idx, item in enumerate(search_results):
        url = item["url"]
        pages_attempted += 1
        status_code, text, sha256 = collector.fetch_page(url)

        src_id = f"SRC-{sha256[:16]}"
        if src_id not in seen_src_ids:
            seen_src_ids.add(src_id)
            warc_rec_id = getattr(collector, "get_warc_record_id", lambda u: None)(url)
            source = SourceSnapshot(
                source_id=src_id,
                url=url,
                publisher=url.split("/")[2] if "/" in url else "unknown",
                content_sha256=sha256,
                http_status=status_code,
                warc_record_id=warc_rec_id,
            )
            sources.append(source)

        # Non-200 pages MUST NOT generate Evidence or Claims
        if status_code != 200 or not text.strip():
            continue

        pages_200_count += 1

        # Extract all capitalized full names across entire source text to build full-source same-surname index (veto signal)
        # Matches multi-token names like "Ming Hao Zhou", "Alice Smith", "M. H. Zhou", etc.
        raw_names = re.findall(r"\b([A-Z][a-zA-Z\.\-]+(?:\s+[A-Z][a-zA-Z\.\-]+)+)\b", text)
        src_map = source_names_by_surname.setdefault(src_id, {})
        for full_n in raw_names:
            toks = full_n.strip().split()
            if len(toks) >= 2:
                sname = toks[-1].lower().rstrip(".,")
                src_map.setdefault(sname, set()).add(full_n.strip().lower())

        text_lower = text.lower()
        h1_match = re.search(r'<h1\b[^>]*>(.*?)</h1\s*>', text, re.DOTALL | re.I)
        h1_text = re.sub(r'<[^>]+>', ' ', h1_match.group(1)).strip() if h1_match else ""
        has_bio = any(marker in text_lower for marker in ["biography:", "bio:", "about me", "profile-details"])
        jsonld_person_names = re.findall(r'"@type"\s*:\s*"Person"[^}]*?"name"\s*:\s*"([^"]+)"', text, re.I | re.DOTALL)
        if not jsonld_person_names:
            jsonld_person_names = re.findall(r'"name"\s*:\s*"([^"]+)"[^}]*?"@type"\s*:\s*"Person"', text, re.I | re.DOTALL)
        sq_class = classify_source_quality(url)
        source_profile_containers[src_id] = {
            "h1_text": h1_text,
            "has_bio": has_bio,
            "jsonld_person_names": jsonld_person_names,
            "url": url,
            "source_quality_class": sq_class,
        }

        # Use structured DOM locator to extract exact evidence slices from recorded crawl payload
        page_evs = locate_evidence_slices(
            html_text=text,
            target_name=target_name,
            aliases=aliases,
            source_id=src_id,
            raw_payload_sha256=sha256,
            url=url,
            source_quality_class=sq_class,
        )
        evidence_list.extend(page_evs)

        for ev in page_evs:
            mentions = extract_mentions_and_aliases(
                source_id=src_id,
                raw_text=ev.verbatim_excerpt,
                target_name=target_name,
                known_aliases=aliases,
                evidence_id=ev.evidence_id,
            )
            orgs = extract_organizations(ev.verbatim_excerpt)
            for m in mentions:
                m.inferred_affiliations = list(orgs)
                if any(existing.mention_id == m.mention_id for existing in mentions_list):
                    dup_seed = f"{m.mention_id}:{ev.evidence_id}"
                    m.mention_id = f"MEN-{hashlib.sha256(dup_seed.encode('utf-8')).hexdigest()[:12]}"
                mentions_list.append(m)

    # Phase 2: Entity Resolution and Clustering (Constrained Union-Find)
    evidence_text_by_id = {ev.evidence_id: ev.verbatim_excerpt for ev in evidence_list}
    matches, clusters = resolve_mentions(
        mentions_list,
        source_names_by_surname=source_names_by_surname,
        source_profile_containers=source_profile_containers,
        evidence_text_by_id=evidence_text_by_id,
    )

    # Create CandidateEntity records strictly 1:1 with clusters
    candidates: List[CandidateEntity] = []
    for cluster in clusters:
        cand_id_suffix = cluster.cluster_id.replace("CLUST-", "")
        cand = CandidateEntity(
            candidate_entity_id=f"CAND-{cand_id_suffix}",
            proposed_cluster_id=cluster.cluster_id,
            mention_ids=cluster.mention_ids,
        )
        candidates.append(cand)

    # Phase 3: Claim Extraction with Strict Subject Mention and Candidate Attribution
    all_claims = route_and_extract_claims(
        evidence_list=evidence_list,
        mentions_list=mentions_list,
        candidates=candidates,
        default_target_name=target_name,
    )

    # Phase 4: Central Deterministic State Machine Outcome Determination (Sole Authority)
    budget_exhausted = collector.queries_executed >= query_budget and not all_claims
    search_has_results = len(search_results) > 0
    pages_fetched = pages_200_count

    outcome, primary_candidate_id, ambiguous_cand_ids = determine_state_outcome(
        has_structural_error=False,
        pages_fetched=pages_fetched,
        crawl_errors=collector.errors,
        candidates=candidates,
        claims=all_claims,
        search_has_results=search_has_results,
        budget_exhausted=budget_exhausted,
        is_ambiguous=False,
        decisions=matches,
        mentions=mentions_list,
        evidence_list=evidence_list,
        target_prior=target_prior,
    )

    abstention_records: List[AbstentionRecord] = []
    if outcome == RunOutcome.INSUFFICIENT_EVIDENCE:
        gap_id = f"GAP-{hashlib.sha256(f'{target_name}:{queries[0]}'.encode('utf-8')).hexdigest()[:8]}"
        abstention_records.append(
            AbstentionRecord(
                gap_id=gap_id,
                target_name=target_name,
                query_executed="; ".join(queries[:3]),
                reason=f"No verified public records or substantiated claims found for target entity '{target_name}'",
                observed_at=datetime.now(timezone.utc),
            )
        )

    # Phase 6: Dossier Synthesis
    statements: List[DossierStatement] = []
    if outcome == RunOutcome.COMPLETED and primary_candidate_id:
        primary_candidate = next((c for c in candidates if c.candidate_entity_id == primary_candidate_id), None)
        primary_claims = [c for c in all_claims if c.candidate_entity_id == primary_candidate_id]
        for c in primary_claims:
            stmt_id = f"STMT-{hashlib.sha256(f'{primary_candidate_id}:{c.claim_id}'.encode('utf-8')).hexdigest()[:8]}"
            statements.append(
                DossierStatement(
                    statement_id=stmt_id,
                    section="身份与机构关联 (Affiliations & Status)",
                    rendered_text=f"公开记录显示其关联机构/经历为: {c.object_raw}",
                    backed_claim_ids=[c.claim_id],
                )
            )

        dossier_id = f"DOS-{hashlib.sha256(f'{target_name}:{primary_candidate_id}'.encode('utf-8')).hexdigest()[:8]}"
        dossier = Dossier(
            dossier_id=dossier_id,
            candidate_entity_id=primary_candidate_id,
            proposed_cluster_id=primary_candidate.proposed_cluster_id if primary_candidate else None,
            statements=statements,
            ambiguous_candidates=[c.candidate_entity_id for c in candidates],
            generated_at=datetime.now(timezone.utc),
        )
    else:
        # Ambiguous identity or insufficient evidence
        dossier_id = f"DOS-AMBIGUOUS-{hashlib.sha256(target_name.encode('utf-8')).hexdigest()[:8]}"
        dossier = Dossier(
            dossier_id=dossier_id,
            candidate_entity_id=None,
            proposed_cluster_id=None,
            statements=[],
            ambiguous_candidates=ambiguous_cand_ids if ambiguous_cand_ids else [c.candidate_entity_id for c in candidates],
            generated_at=datetime.now(timezone.utc),
        )

    dossier_md = render_dossier_markdown(
        dossier,
        all_claims,
        target_name,
        candidates=candidates,
        run_outcome=outcome,
        is_offline_replay=bool(offline_corpus is not None),
    )

    run_fingerprint = compute_semantic_bundle_fingerprint(
        sources=sources,
        evidence=evidence_list,
        mentions=mentions_list,
        candidates=candidates,
        clusters=clusters,
        claims=all_claims,
    )

    prior_scores_dict = None
    if enable_target_prior and target_prior and candidates:
        prior_scores_dict = {}
        for cand in candidates:
            c_claims = [c for c in all_claims if c.candidate_entity_id == cand.candidate_entity_id]
            aff = compute_candidate_prior_affinity(
                candidate=cand,
                mentions=mentions_list,
                evidence_list=evidence_list,
                candidate_claims=c_claims,
                prior=target_prior,
            )
            prior_scores_dict[cand.candidate_entity_id] = round(aff, 4)

    manifest = RunManifest(
        run_id=run_id,
        run_outcome=outcome,
        run_fingerprint=run_fingerprint,
        abstention_records=abstention_records,
        target_prior=target_prior,
        enable_target_prior=enable_target_prior,
        prior_affinity_scores=prior_scores_dict,
        prior_thresholds={"min_affinity": 0.35, "min_margin": 0.20} if enable_target_prior else None,
        tool_version="verify-public-person-profile/1.0.0",
        model_name="deterministic_pipeline",
        query_budget=query_budget,
        queries_executed=collector.queries_executed,
        pages_fetched=collector.pages_fetched,
        crawl_errors=collector.errors,
        execution_time_seconds=round(time.time() - start_time, 3),
    )

    # Phase 7: Write all 9 JSONL/JSON bundle files + dossier.md
    with open(output_dir / "sources.jsonl", "w", encoding="utf-8") as f:
        for s in sources:
            f.write(s.model_dump_json() + "\n")

    with open(output_dir / "evidence.jsonl", "w", encoding="utf-8") as f:
        for ev in evidence_list:
            f.write(ev.model_dump_json() + "\n")

    with open(output_dir / "mentions.jsonl", "w", encoding="utf-8") as f:
        for m in mentions_list:
            f.write(m.model_dump_json() + "\n")

    with open(output_dir / "candidates.jsonl", "w", encoding="utf-8") as f:
        for cand in candidates:
            f.write(cand.model_dump_json() + "\n")

    with open(output_dir / "matches.jsonl", "w", encoding="utf-8") as f:
        for match in matches:
            f.write(match.model_dump_json() + "\n")

    with open(output_dir / "clusters.jsonl", "w", encoding="utf-8") as f:
        for cluster in clusters:
            f.write(cluster.model_dump_json() + "\n")

    with open(output_dir / "claims.jsonl", "w", encoding="utf-8") as f:
        for c in all_claims:
            f.write(c.model_dump_json() + "\n")

    with open(output_dir / "dossier.json", "w", encoding="utf-8") as f:
        f.write(dossier.model_dump_json(indent=2))

    with open(output_dir / "dossier.md", "w", encoding="utf-8") as f:
        f.write(dossier_md)

    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Verify Public Person Profile Pipeline CLI.")
    parser.add_argument("--name", type=str, required=True, help="Full name of target person.")
    parser.add_argument("--hints", type=str, nargs="*", default=[], help="Optional search hints.")
    parser.add_argument("--aliases", type=str, nargs="*", default=[], help="Known verified aliases.")
    parser.add_argument("--output", "--output-dir", dest="output", type=Path, default=Path("runs/test_run"), help="Output directory.")
    parser.add_argument("--offline-corpus", type=Path, default=None, help="Path to offline WARC archive.")
    parser.add_argument("--query-budget", type=int, default=15, help="Maximum search query budget.")
    parser.add_argument("--enable-target-prior", action="store_true", default=False, help="Enable experimental V5-alpha TargetPrior downstream disambiguation.")
    args = parser.parse_args()

    out = run_pipeline(
        target_name=args.name,
        hints=args.hints,
        aliases=args.aliases,
        output_dir=args.output,
        offline_corpus=args.offline_corpus,
        query_budget=args.query_budget,
        enable_target_prior=args.enable_target_prior,
    )
    print(f"Profile bundle successfully generated at: {out}")


if __name__ == "__main__":
    main()
