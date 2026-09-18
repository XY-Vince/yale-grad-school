"""
Versioned Entity and Object Registry (V1.1.0).
Provides canonical entity identifiers, categories, match modes, and alias mappings for
evidence verification, strict object matching, and provenance enforcement.
"""

from typing import Any, Dict, List, Optional

OBJECT_REGISTRY_VERSION = "1.1.0"

CANONICAL_OBJECT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ENT-MIT": {
        "canonical_id": "ENT-MIT",
        "canonical_name": "Massachusetts Institute of Technology",
        "category": "academic",
        "aliases": [
            {
                "surface": "Massachusetts Institute of Technology",
                "match_mode": "canonical",
                "min_length": 10,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "MIT",
                "match_mode": "short_alias",
                "min_length": 3,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-CMU": {
        "canonical_id": "ENT-CMU",
        "canonical_name": "Carnegie Mellon University",
        "category": "academic",
        "aliases": [
            {
                "surface": "Carnegie Mellon University",
                "match_mode": "canonical",
                "min_length": 10,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "CMU",
                "match_mode": "short_alias",
                "min_length": 3,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-NYU": {
        "canonical_id": "ENT-NYU",
        "canonical_name": "New York University",
        "category": "academic",
        "aliases": [
            {
                "surface": "New York University",
                "match_mode": "canonical",
                "min_length": 10,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "NYU",
                "match_mode": "short_alias",
                "min_length": 3,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-UCLA": {
        "canonical_id": "ENT-UCLA",
        "canonical_name": "University of California, Los Angeles",
        "category": "academic",
        "aliases": [
            {
                "surface": "University of California, Los Angeles",
                "match_mode": "canonical",
                "min_length": 15,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "UCLA",
                "match_mode": "short_alias",
                "min_length": 4,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-UCB": {
        "canonical_id": "ENT-UCB",
        "canonical_name": "University of California, Berkeley",
        "category": "academic",
        "aliases": [
            {
                "surface": "University of California, Berkeley",
                "match_mode": "canonical",
                "min_length": 15,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "UC Berkeley",
                "match_mode": "short_alias",
                "min_length": 5,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-DEG-PHD": {
        "canonical_id": "ENT-DEG-PHD",
        "canonical_name": "Ph.D.",
        "category": "degree",
        "aliases": [
            {
                "surface": "Ph.D.",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "degree",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "PhD",
                "match_mode": "canonical",
                "min_length": 3,
                "category": "degree",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "Doctor of Philosophy",
                "match_mode": "canonical",
                "min_length": 10,
                "category": "degree",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "Doctorate",
                "match_mode": "canonical",
                "min_length": 5,
                "category": "degree",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-PKU": {
        "canonical_id": "ENT-PKU",
        "canonical_name": "北京大学",
        "category": "academic",
        "authorized_subunits": [
            "计算机系", "计算机学院", "生命科学学院", "生科院", "医学部", "哲学系", "历史学系", "历史系",
            "数学科学学院", "数学系", "物理学院", "化学与分子工程学院", "外国语学院", "外院", "法学院",
            "经济学院", "光华管理学院", "社会学系", "信息科学技术学院", "信科", "中文系", "工学院",
            "软件与微电子学院", "软件学院", "环境科学与工程学院", "新闻与传播学院", "政府管理学院",
            "国际关系学院", "城市与环境学院", "地球与空间科学学院", "心理与认知科学学院"
        ],
        "aliases": [
            {
                "surface": "北京大学",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "academic",
            },
            {
                "surface": "北大",
                "match_mode": "short_alias",
                "min_length": 2,
                "category": "academic",
            },
        ],
    },
    "ENT-THU": {
        "canonical_id": "ENT-THU",
        "canonical_name": "清华大学",
        "category": "academic",
        "aliases": [
            {
                "surface": "清华大学",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-FUDAN": {
        "canonical_id": "ENT-FUDAN",
        "canonical_name": "复旦大学",
        "category": "academic",
        "aliases": [
            {
                "surface": "复旦大学",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
    "ENT-BJ101": {
        "canonical_id": "ENT-BJ101",
        "canonical_name": "北京一零一中",
        "category": "academic",
        "aliases": [
            {
                "surface": "北京一零一中",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "北京101中学",
                "match_mode": "canonical",
                "min_length": 4,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
            {
                "surface": "北京一零一中学",
                "match_mode": "canonical",
                "min_length": 5,
                "category": "academic",
                "blocked_compounds": [],
                "required_contexts": [],
            },
        ],
    },
}

_SURFACE_TO_CANONICAL: Dict[str, Dict[str, Any]] = {}
OBJECT_ALIASES: Dict[str, List[str]] = {}

for ent_id, rec in CANONICAL_OBJECT_REGISTRY.items():
    alias_surfaces = [a["surface"].lower().strip() for a in rec["aliases"]]
    for alias_spec in rec["aliases"]:
        key = alias_spec["surface"].lower().strip()
        _SURFACE_TO_CANONICAL[key] = rec
        OBJECT_ALIASES[key] = alias_surfaces


def lookup_registry_object(surface: str) -> Optional[Dict[str, Any]]:
    """Look up a canonical entity record by surface form or known alias."""
    if not surface:
        return None
    key = surface.lower().strip()
    return _SURFACE_TO_CANONICAL.get(key)

