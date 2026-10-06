"""Unit and regression tests for HTML title affiliation parsing (Workstream A)."""

from core.text.title_parse import extract_institution_from_title
from scripts.validate_dossier import check_object_presence


def test_title_parse_v10_reproduction_clean():
    """Verify that multi-pipe titles with section filler extract clean institution without delimiters."""
    title = "<title>\n\t\t\t\n\n    Synthetic Scholar | Faculty  | University of Example City \n\t\t</title>"
    person, inst, span = extract_institution_from_title(title, "Synthetic Scholar")
    assert person == "Synthetic Scholar"
    assert inst == "University of Example City"
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


def test_title_parse_fixture_driven_e2e_object_presence():
    """Fixture-driven E2E: parse raw title to extract object_raw, then assert check_object_presence in evidence sentences."""
    fixtures = [
        (
            "<title>Dr. Jane Doe | Department of Computer Science | University of Illinois - Chicago</title>",
            "Jane Doe",
            "She is a faculty member at University of Illinois - Chicago since 2019.",
        ),
        (
            "<title>Bob Smith | Texas A&M - Commerce | Faculty Directory</title>",
            "Bob Smith",
            "Bob Smith teaches at Texas A&M - Commerce.",
        ),
        (
            "<title>Carol White :: School of Engineering :: Columbia University</title>",
            "Carol White",
            "Carol White joined the engineering department at Columbia University.",
        ),
        (
            "<title>张三 | 清华大学 | 教师主页</title>",
            "张三",
            "张三教授目前就职于清华大学交叉信息研究院。",
        ),
    ]
    for raw_title, person, evidence_sentence in fixtures:
        matched_person, object_raw, span = extract_institution_from_title(raw_title, person)
        assert matched_person is not None, f"Failed to match person {person} in {raw_title}"
        assert object_raw is not None, f"Failed to extract institution from {raw_title}"
        assert object_raw in raw_title, f"object_raw '{object_raw}' must be verbatim substring of '{raw_title}'"
        assert check_object_presence(object_raw, evidence_sentence) is True, (
            f"check_object_presence failed for extracted '{object_raw}' in '{evidence_sentence}'"
        )


def test_person_matcher_parity_with_attribution_rules():
    """H2: Verify parity between default_person_matcher and is_mention_matching_target."""
    from core.extractors.claim_extractor import is_mention_matching_target
    from core.text.title_parse import default_person_matcher

    test_pairs = [
        ("Dr. Jane Doe", "Jane Doe", True),
        ("Prof. Robert Smith", "Robert Smith", True),
        ("Alice Cooper", "Alice Cooper", True),
        ("Alice Cooper", "Bob Cooper", False),
        ("Alice Cooper", "Alice Cooper-Smith", False),
        ("张伟教授", "张伟", True),
        ("李明院士", "李明", True),
        ("王芳博士", "王芳", True),
        ("陈晓", "陈晓", True),
        ("陈晓", "陈晓明", False),
        ("Mr. David Miller", "David Miller", True),
        ("Ms. Sarah Connor", "Sarah Connor", True),
    ]
    for seg, target, expected in test_pairs:
        res_default = default_person_matcher(seg, target)
        res_attr = is_mention_matching_target(seg, target)
        assert res_default == expected, f"default_person_matcher mismatch on ({seg}, {target})"
        assert res_attr == expected, f"is_mention_matching_target mismatch on ({seg}, {target})"
        assert res_default == res_attr, f"Matcher parity failed on ({seg}, {target})"

