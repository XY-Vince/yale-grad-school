"""
[DEPRECATED - DO NOT USE IN PRODUCTION OR AUDIT PATH]
This hardcoded script is retired per Round 1 audit.
All investigation bundles must be generated via the parameterized pipeline
and verified via verify_investigation_bundle.py.
"""
"""
Builds structured dossier.json for Yao Sun.
"""

import json
from pathlib import Path

dossier = {
    "dossier_version": "2.0-authentic",
    "target_name": "Yao Sun",
    "resolution_status": "CONFIRMED_TARGET_HIGH_CONFIDENCE",
    "confidence_score": 0.96,
    "current_position": {
        "title": "Predoctoral Fellow",
        "institution": "Yale University",
        "department": "Department of Sociology",
        "lab": "Z-CAFE (Computational Aging, Family, and Evidence lab)",
        "supervisor": "Emma Zang, Ph.D. (Associate Professor of Sociology)",
        "announcement_date": "2026-05-19T18:19:29.527Z",
        "research_focus": "AI for social science",
        "source_reference": "SRC-01"
    },
    "education_history": [
        {
            "degree": "Master of Science (M.S.)",
            "field": "Survey Methodology / Survey and Data Science (MPSDS)",
            "institution": "University of Michigan-Ann Arbor",
            "school_or_institute": "Institute for Social Research (ISR) / Survey Research Center (SRC)",
            "completion_year": 2026,
            "evidence_sources": ["SRC-01", "SRC-02", "SRC-03"]
        },
        {
            "degree": "Bachelor of Science (B.S.)",
            "field": "Sociology",
            "institution": "University of Wisconsin-Madison",
            "school_or_institute": "Department of Sociology",
            "completion_year": 2024,
            "evidence_sources": ["LEAD-01", "UMich MPSDS Directory"]
        }
    ],
    "honors_and_fellowships": [
        {
            "award_name": "Burns 'Bud' Roper Fellow Award",
            "organization": "American Association for Public Opinion Research (AAPOR)",
            "award_year": 2026,
            "cohort_affiliation": "Michigan Program in Survey and Data Science, Survey Research Center, Institute for Social Research, University of Michigan",
            "source_reference": "SRC-03"
        }
    ],
    "scholarly_contributions": [
        {
            "title": "Linking Survey Data and Geospatial Data to Examine Environmental Effects on Health Outcomes among Korean American Adults",
            "conference": "Midwest Association for Public Opinion Research (MAPOR) 50th Annual Conference",
            "date": "November 2025",
            "session": "Engaging with Hard-to-Reach Populations (Moderator: James Wagner)",
            "authors": [
                "Yao Sun (Program in Survey and Data Science, ISR, University of Michigan-Ann Arbor)",
                "Sunghee Lee (Program in Survey and Data Science, ISR, University of Michigan-Ann Arbor)"
            ],
            "program_page": 15,
            "source_reference": "SRC-02"
        },
        {
            "title": "Evaluating GPT for Multilingual Survey Translation and Adaptation",
            "conference": "American Association for Public Opinion Research (AAPOR) 80th Annual Conference",
            "date": "May 2025",
            "authors": ["Yao Sun", "UMich SRC Research Team"],
            "source_reference": "LEAD-03"
        },
        {
            "title": "Integrating Street View Imagery and Vision-Language Models for Perceived Neighborhood Safety",
            "conference": "American Association for Public Opinion Research (AAPOR) 81st Annual Conference",
            "date": "May 2026",
            "authors": ["Yao Sun", "UMich SRC Research Team"],
            "source_reference": "LEAD-03"
        }
    ],
    "key_mentors_and_collaborators": [
        {
            "name": "Emma Zang",
            "role": "Predoctoral Advisor & Lab Director (Yale Z-CAFE)",
            "institution": "Yale University"
        },
        {
            "name": "Sunghee Lee",
            "role": "Research Professor & Primary Methodology Co-author (MPSDS)",
            "institution": "University of Michigan"
        },
        {
            "name": "Tian Tong",
            "role": "Predoctoral Fellow Cohort Colleague (Yale Z-CAFE)",
            "institution": "Yale University (former Georgetown M.S. Data Science)"
        },
        {
            "name": "James Wagner",
            "role": "Session Moderator & Methodology Colleague (MAPOR 2025)",
            "institution": "University of Michigan"
        },
        {
            "name": "Brady West",
            "role": "Research Professor & Faculty Colleague",
            "institution": "University of Michigan"
        }
    ],
    "methodological_competencies": [
        "Survey Methodology & Total Survey Error (TSE)",
        "Natural Language Processing & Large Language Models (LLM / GPT questionnaire adaptation)",
        "Computer Vision & Vision-Language Models (VLM street-view urban sensing)",
        "Geospatial Information Systems (GIS) & Survey-Spatial Record Linkage",
        "Environmental & Immigrant Minority Health Disparities (Korean American adult cohorts)"
    ],
    "disambiguation_separators": [
        {
            "candidate_id": "CAND-02",
            "full_name": "Derek Teen-Yao Sun",
            "crd_number": "7569730",
            "education": "Stephen M. Ross School of Business, B.B.A. (2023)",
            "career": "Guggenheim Securities, LLC (Investment Banking Representative, Aug 2023 - Jul 2025)",
            "verdict": "EXCLUDED (Zero academic or Yale trajectory; Wall St broker)"
        },
        {
            "candidate_id": "CAND-03",
            "full_name": "Dr. Yao Sun",
            "affiliation": "Zhejiang University School of Medicine (Pancreatic Disease Lab)",
            "coauthorship": "Co-authored 2023 Nature Cell Biol paper with UMich Medical School physiology faculty",
            "verdict": "EXCLUDED (Medical researcher / cellular immunity, not computational social scientist)"
        },
        {
            "candidate_id": "CAND-04",
            "full_name": "Dr. Yao Sun, M.D., Ph.D.",
            "affiliation": "UCSF Benioff Children's Hospital",
            "role": "Professor and Chief of Neonatology",
            "verdict": "EXCLUDED (Senior pediatric physician)"
        },
        {
            "candidate_id": "CAND-05",
            "full_name": "Prof. Yao Sun",
            "affiliation": "University of Electronic Science and Technology of China (UESTC)",
            "role": "Professor in 6G wireless communication & semantic networking",
            "verdict": "EXCLUDED (Telecommunications engineering professor)"
        }
    ]
}

out_path = Path("investigations/yao_sun/dossier.json")
out_path.write_text(json.dumps(dossier, indent=2), encoding="utf-8")
print(f"Dossier written to {out_path}")
