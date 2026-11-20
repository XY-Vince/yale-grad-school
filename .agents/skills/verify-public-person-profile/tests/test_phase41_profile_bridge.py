"""Phase 4.1 red tests for conservative cross-source profile bridging."""

from core.resolver import extract_domains, resolve_mentions
from models.schemas import EntityMention, MachineRelation, SourceQualityClass


def _mention(
    mention_id: str,
    name: str,
    source_id: str,
    evidence_id: str,
    context: str,
    affiliations: list[str] | None = None,
) -> EntityMention:
    start = context.index(name)
    return EntityMention(
        mention_id=mention_id,
        raw_name_text=name,
        source_id=source_id,
        context_snippet=context,
        evidence_id=evidence_id,
        mention_key=f"key-{mention_id}",
        char_start=start,
        char_end=start + len(name),
        inferred_affiliations=affiliations or [],
    )


def _relation(decisions):
    assert len(decisions) == 1
    return decisions[0].machine_relation


def test_exact_name_trusted_profile_bridge_uses_shared_normalized_org():
    """Rohini-style exact names bridge when a trusted profile and independent bio share an organization."""
    bio = _mention(
        "MEN-BIO",
        "Nadine Moore",
        "SRC-BIO",
        "EVI-BIO",
        "Nadine Moore is an MPH candidate at Harvard T.H Chan School of Public Health.",
        ["harvard t.h chan school of public health"],
    )
    profile = _mention(
        "MEN-PROFILE",
        "Nadine Moore",
        "SRC-PROFILE",
        "EVI-PROFILE",
        '"name":"Nadine Moore","alumniOf":"Harvard T.H. Chan School of Public Health"',
        ["harvard t.h. chan school of public health"],
    )

    decisions, clusters = resolve_mentions(
        [bio, profile],
        source_profile_containers={
            "SRC-BIO": {
                "h1_text": "40 Under 40: Nadine Moore",
                "has_bio": True,
                "jsonld_person_names": [],
                "url": "https://awards.example/nadine-moore",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
            "SRC-PROFILE": {
                "h1_text": "Nadine Moore",
                "has_bio": True,
                "jsonld_person_names": ["Nadine Moore"],
                "url": "https://medicine.yale.edu/profile/nadine-moore/",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
        },
    )

    assert _relation(decisions) == MachineRelation.MATCH
    assert len(clusters) == 1, [
        (d.source_mention_id, d.target_mention_id, d.machine_relation, d.explanation)
        for d in decisions
    ]


def test_exact_name_trusted_profile_bridge_uses_host_to_org_anchor():
    """Sarah-style official profile host can corroborate an explicit organization on an independent bio."""
    profile = _mention(
        "MEN-YALE",
        "Mara Lanehart",
        "SRC-YALE",
        "EVI-YALE",
        '"name":"Mara Lanehart","jobTitle":"Business Systems Analyst 2"',
    )
    bio = _mention(
        "MEN-RESNET",
        "Mara Lanehart",
        "SRC-RESNET",
        "EVI-RESNET",
        "Mara Lanehart started as a Student Technician at Yale University.",
        ["yale university"],
    )

    decisions, clusters = resolve_mentions(
        [profile, bio],
        source_profile_containers={
            "SRC-YALE": {
                "h1_text": "Mara Lanehart",
                "has_bio": True,
                "jsonld_person_names": ["Mara Lanehart"],
                "url": "https://medicine.yale.edu/profile/mara-lanehart/",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
            "SRC-RESNET": {
                "h1_text": "Board of Directors",
                "has_bio": False,
                "jsonld_person_names": [],
                "url": "https://resnetinc.org/board/",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
        },
    )

    assert _relation(decisions) == MachineRelation.MATCH
    assert len(clusters) == 1


def test_exact_name_without_shared_anchor_stays_review():
    """Exact names across unrelated sources remain separate even when one page is a trusted profile."""
    stanford = _mention(
        "MEN-STANFORD",
        "Alex Kim",
        "SRC-STANFORD",
        "EVI-STANFORD",
        "Alex Kim is Professor at Stanford University.",
        ["stanford university"],
    )
    mit = _mention(
        "MEN-MIT",
        "Alex Kim",
        "SRC-MIT",
        "EVI-MIT",
        "Alex Kim is Dean at Massachusetts Institute of Technology.",
        ["massachusetts institute of technology"],
    )

    decisions, clusters = resolve_mentions(
        [stanford, mit],
        source_profile_containers={
            "SRC-STANFORD": {
                "h1_text": "Alex Kim",
                "has_bio": True,
                "jsonld_person_names": ["Alex Kim"],
                "url": "https://profiles.stanford.edu/alex-kim",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
            "SRC-MIT": {
                "h1_text": "Alex Kim",
                "has_bio": True,
                "jsonld_person_names": ["Alex Kim"],
                "url": "https://mit.edu/people/alex-kim",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
        },
    )

    assert _relation(decisions) in {MachineRelation.REVIEW, MachineRelation.NONMATCH}
    assert len(clusters) == 2


def test_untrusted_lookalike_host_cannot_bridge_to_org():
    """A Class C lookalike domain cannot use a hostname token as identity corroboration."""
    fake_profile = _mention(
        "MEN-FAKE",
        "Mara Lanehart",
        "SRC-FAKE",
        "EVI-FAKE",
        "Mara Lanehart biography",
    )
    bio = _mention(
        "MEN-BIO",
        "Mara Lanehart",
        "SRC-BIO",
        "EVI-BIO",
        "Mara Lanehart worked at Yale University.",
        ["yale university"],
    )

    decisions, clusters = resolve_mentions(
        [fake_profile, bio],
        source_profile_containers={
            "SRC-FAKE": {
                "h1_text": "Mara Lanehart",
                "has_bio": True,
                "jsonld_person_names": ["Mara Lanehart"],
                "url": "https://yale.edu.evil.example/profile/mara-lanehart",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
            "SRC-BIO": {
                "h1_text": "Board",
                "has_bio": False,
                "jsonld_person_names": [],
                "url": "https://resnetinc.org/board/",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
        },
    )

    assert _relation(decisions) == MachineRelation.REVIEW
    assert len(clusters) == 2


def test_source_level_profile_bridge_prevents_local_affiliation_poison_edge():
    """A current-role snippet must not split a profile already bridged by shared history."""
    yale_history = _mention(
        "MEN-YALE-HISTORY",
        "Nadine Moore",
        "SRC-YALE",
        "EVI-YALE-HISTORY",
        '"name":"Nadine Moore","alumniOf":"Harvard T.H. Chan School of Public Health"',
        ["harvard t.h. chan school of public health"],
    )
    yale_current = _mention(
        "MEN-YALE-CURRENT",
        "Nadine Moore",
        "SRC-YALE",
        "EVI-YALE-CURRENT",
        "Nadine Moore is a Hospital Resident at Yale School of Medicine.",
        ["yale school of medicine"],
    )
    independent_bio = _mention(
        "MEN-BIO",
        "Nadine Moore",
        "SRC-BIO",
        "EVI-BIO",
        "Nadine Moore earned an MPH at Harvard T.H Chan School of Public Health.",
        ["harvard t.h chan school of public health"],
    )
    independent_honorific = _mention(
        "MEN-BIO-HONORIFIC",
        "Dr. Moore",
        "SRC-BIO",
        "EVI-BIO-HONORIFIC",
        "Dr. Moore is pursuing research in global women's health.",
        ["harvard t.h chan school of public health"],
    )

    decisions, clusters = resolve_mentions(
        [yale_history, yale_current, independent_bio, independent_honorific],
        source_profile_containers={
            "SRC-YALE": {
                "h1_text": "Nadine Moore",
                "has_bio": True,
                "jsonld_person_names": ["Nadine Moore"],
                "url": "https://medicine.yale.edu/profile/nadine-moore/",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
            "SRC-BIO": {
                "h1_text": "40 Under 40: Nadine Moore",
                "has_bio": True,
                "jsonld_person_names": [],
                "url": "https://bcph.org/awards/nadine-moore/",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
        },
    )

    assert len(clusters) == 1, [
        (d.source_mention_id, d.target_mention_id, d.machine_relation, d.explanation)
        for d in decisions
    ]
    assert all(d.machine_relation != MachineRelation.NONMATCH for d in decisions)


def test_html_meta_property_is_not_a_real_estate_domain_signal():
    domains = extract_domains(
        '<meta property="og:description" content="Nadine Moore is a Hospital Resident">'
    )

    assert "biomedical" in domains
    assert "real_estate" not in domains


def test_host_only_profile_bridge_does_not_override_domain_conflict():
    biostat = _mention(
        "MEN-BIOSTAT",
        "Lin Zhou",
        "SRC-BIOSTAT",
        "EVI-BIOSTAT",
        "Lin Zhou is Professor of Biostatistics at Yale School of Public Health.",
        ["yale school of public health"],
    )
    mhealth = _mention(
        "MEN-MHEALTH",
        "Lin Zhou",
        "SRC-MHEALTH",
        "EVI-MHEALTH",
        "Lin Zhou develops mHealth communication tools at Yale University.",
        ["yale university"],
    )

    decisions, clusters = resolve_mentions(
        [biostat, mhealth],
        source_profile_containers={
            "SRC-BIOSTAT": {
                "h1_text": "Lin Zhou",
                "has_bio": True,
                "jsonld_person_names": ["Lin Zhou"],
                "url": "https://medicine.yale.edu/profile/lin-zhou/",
                "source_quality_class": SourceQualityClass.CLASS_A,
            },
            "SRC-MHEALTH": {
                "h1_text": "Research Team",
                "has_bio": False,
                "jsonld_person_names": [],
                "url": "https://example.org/team/lin-zhou",
                "source_quality_class": SourceQualityClass.CLASS_C,
            },
        },
    )

    assert _relation(decisions) == MachineRelation.NONMATCH
    assert len(clusters) == 2
