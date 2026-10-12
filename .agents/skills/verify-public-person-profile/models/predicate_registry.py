"""
Versioned Predicate Registry & Canonicalization Ontology (V1.2.0).

Defines canonical allowed predicates for public person investigation dossiers,
with domain categories, descriptions, and explicit alias normalizations.
"""

from typing import Dict, Optional, Set

PREDICATE_REGISTRY_VERSION = "1.2.0"

PREDICATE_REGISTRY: Dict[str, Dict[str, str]] = {
    # 1. Career & Appointments
    "holds_position": {
        "category": "career",
        "description": "Professional position, academic title, or appointment held",
    },
    "employed_by": {
        "category": "career",
        "description": "Employing institution, company, or organization",
    },
    "based_in": {
        "category": "location",
        "description": "Primary professional work city or jurisdiction",
    },
    # 2. Education & Qualifications
    "graduated_from": {
        "category": "education",
        "description": "Educational institution graduated from (alma mater)",
    },
    "received_degree": {
        "category": "education",
        "description": "Academic degree or qualification awarded (e.g. Ph.D., M.S.)",
    },
    # 3. Affiliations & Memberships
    "affiliated_with": {
        "category": "affiliation",
        "description": "Affiliated department, lab, research center, or initiative",
    },
    "member_of": {
        "category": "affiliation",
        "description": "Membership in learned society, professional board, or committee",
    },
    # 4. Honors & Recognition
    "awarded_honor": {
        "category": "recognition",
        "description": "Honor, award, fellowship, scholarship, or distinction received",
    },
    # 5. Scholarship & Research Activities
    "authored_publication": {
        "category": "scholarship",
        "description": "Authored peer-reviewed publication, book, or article",
    },
    "presented_paper": {
        "category": "scholarship",
        "description": "Presented conference paper, invited talk, or seminar presentation",
    },
    "conducted_research": {
        "category": "research",
        "description": "Conducted research program, initiative, or field study",
    },
    "researched_topic": {
        "category": "research",
        "description": "Researched scientific theme, substantive topic, or methodology",
    },
    "participated_in": {
        "category": "activity",
        "description": "Participated in academic workshop, panel, or working group",
    },
}

# Explicit alias normalization mapping to canonical ontology predicates
CANONICAL_PREDICATE_ALIASES: Dict[str, str] = {
    "honored_with": "awarded_honor",
    "received_award": "awarded_honor",
    "received_honor": "awarded_honor",
    "authored_work": "authored_publication",
    "presented_work": "presented_paper",
    "alumnus_of": "graduated_from",
    "alumna_of": "graduated_from",
}

PREDICATE_ALLOWLIST: Set[str] = set(PREDICATE_REGISTRY.keys()).union(CANONICAL_PREDICATE_ALIASES.keys())
RELATION_REQUIRED_PREDICATES: Set[str] = set(PREDICATE_ALLOWLIST)


def canonicalize_predicate(predicate: str) -> Optional[str]:
    """Normalizes a raw predicate string to its canonical registry representation."""
    if not predicate:
        return None
    raw = predicate.strip().lower()
    if raw in PREDICATE_REGISTRY:
        return raw
    return CANONICAL_PREDICATE_ALIASES.get(raw)
