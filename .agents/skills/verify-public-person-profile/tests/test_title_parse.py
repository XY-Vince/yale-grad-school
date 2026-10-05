"""Unit and regression tests for HTML title affiliation parsing (Workstream A)."""

from core.text.title_parse import extract_institution_from_title
from scripts.validate_dossier import check_object_presence


def test_title_parse_v10_reproduction_clean():
    """Verify that multi-pipe titles with section filler extract clean institution without delimiters."""
    title = "<title>\n\t\t\t\n\n    Emily Clark | Faculty  | University of the Incarnate Word \n\t\t</title>"
    person, inst, span = extract_institution_from_title(title, "Emily Clark")
    assert person == "Emily Clark"
    assert inst == "University of the Incarnate Word"
    assert inst in title
    assert span is not None
    assert title[span[0]:span[1]] == inst
    # Dossier object presence validator check
    assert check_object_presence(inst, title) is True


def test_title_parse_campus_hyphen_preservation():
    """R4: Multi-campus hyphenated institutions must not be truncated."""
    title1 = "Jane Doe | University of Illinois - Chicago"
    p1, inst1, s1 = extract_institution_from_title(title1, "Jane Doe")
    assert inst1 == "University of Illinois - Chicago"
    assert inst1 in title1
    assert check_object_presence(inst1, title1) is True

    title2 = "Texas A&M - Commerce | Bob Smith"
    p2, inst2, s2 = extract_institution_from_title(title2, "Bob Smith")
    assert inst2 == "Texas A&M - Commerce"
    assert inst2 in title2
    assert check_object_presence(inst2, title2) is True


def test_title_parse_fallback_spaced_hyphen():
    """Fallback to spaced hyphen when primary delimiters are absent."""
    title = "Target Person - Sample College of Medicine - Faculty Profile"
    p, inst, s = extract_institution_from_title(title, "Target Person")
    assert p == "Target Person"
    assert inst == "Sample College of Medicine"
    assert inst in title
    assert check_object_presence(inst, title) is True


def test_title_parse_cjk_transliterated_name_protection():
    """Unspaced middle dots in CJK transliterated names must not be split as title delimiters."""
    title = "约翰·史密斯 | 北京大学"
    p, inst, s = extract_institution_from_title(title, "约翰·史密斯")
    assert p == "约翰·史密斯"
    assert inst == "北京大学"
    assert inst in title
    assert check_object_presence(inst, title) is True


def test_title_parse_parent_university_precedence():
    """Parent University takes precedence over School/Department subdivision."""
    title = "Carol White :: School of Engineering :: Columbia University"
    p, inst, s = extract_institution_from_title(title, "Carol White")
    assert p == "Carol White"
    assert inst == "Columbia University"
    assert inst in title


def test_title_parse_delimiters_variety():
    """Primary delimiters: em-dash, en-dash, fullwidth pipe, spaced middle dot."""
    t_em = "Alice Brown — Department of Physics — Stanford University"
    assert extract_institution_from_title(t_em, "Alice Brown")[1] == "Stanford University"

    t_en = "David Lee – Department of Chemistry – MIT"
    assert extract_institution_from_title(t_en, "David Lee")[1] == "MIT"

    t_full = "Target Person ｜ Department ｜ Harvard University"
    assert extract_institution_from_title(t_full, "Target Person")[1] == "Harvard University"

    t_dot = "Dr. Smith  ·  Division of Humanities  ·  Oxford University"
    assert extract_institution_from_title(t_dot, "Dr. Smith")[1] == "Oxford University"


def test_title_parse_negatives():
    """Negative tests: no institution, naked discipline, prepositional phrase, ambiguous names."""
    # No institution in title
    assert extract_institution_from_title("Just a Normal Webpage Header", "Normal Person") == (None, None, None)
    
    # Target name not found
    assert extract_institution_from_title("John Doe | Harvard University", "Jane Smith") == (None, None, None)
    
    # Naked discipline without institutional head noun
    assert extract_institution_from_title("Jane Doe | Medicine", "Jane Doe") == (None, None, None)
    
    # Prepositional title without delimiters (handled by sentence/SVO extractor)
    assert extract_institution_from_title("Jane Doe, Professor at Harvard University", "Jane Doe") == (None, None, None)
    
    # Empty inputs
    assert extract_institution_from_title("", "Target") == (None, None, None)
    assert extract_institution_from_title("<title>   </title>", "Target") == (None, None, None)


def test_title_parse_determinism():
    """Two successive invocations must yield byte-identical outputs."""
    title = "Jane Doe | Faculty | Yale University"
    r1 = extract_institution_from_title(title, "Jane Doe")
    r2 = extract_institution_from_title(title, "Jane Doe")
    assert r1 == r2
    assert r1[1] == "Yale University"


def test_validator_check_object_presence_empirical_sweep():
    """S-A & R4: Empirical sweep of complex institution names through validator check_object_presence."""
    sweep = [
        ("Texas A&M University", "He attended Texas A&M University in 2020."),
        ("O'Reilly Media", "She works at O'Reilly Media."),
        ("U.S. Department of Energy", "He joined the U.S. Department of Energy."),
        ("北京大学", "他毕业于北京大学经济学院。"),
        ("Universität Heidelberg", "She studied at Universität Heidelberg."),
        ("University of Illinois - Chicago", "She graduated from University of Illinois - Chicago in 2021."),
        ("Texas A&M - Commerce", "He is affiliated with Texas A&M - Commerce."),
    ]
    for obj, text in sweep:
        assert check_object_presence(obj, text) is True, f"Failed object presence on {obj}"
