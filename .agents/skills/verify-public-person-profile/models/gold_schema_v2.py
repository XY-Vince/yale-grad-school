"""
Blind Evaluation Protocol v1.2 - Gold Contract V2 Schema.
Strict Pydantic V2 Models for Ground Truth:
1. GoldEntity: Unique entity ID, canonical name, aliases.
2. GoldMention: Unique mention ID, bound to GoldEntity, source SHA-256, span, text.
3. GoldClaim: Unique claim ID, bound to subject_gold_entity_id, 5D predicate/object/polarity/temporal.
4. GoldCase: Strict validation of:
   - Intra-case ID uniqueness (entities, mentions, claims)
   - Foreign key closure (mention->entity, claim->entity, target_gold_entity_id->entity)
   - Mention span validity (0 <= char_start < char_end)
   - SHA-256 format (64 lowercase hex)
   - Complete partition of gold_clusters over gold_mentions
   - Consistency of is_fact_bearing == (len(gold_claims) > 0)
5. GoldSuite (RootModel[List[GoldCase]]): Global uniqueness of case_id across the suite.
"""

import re
from typing import List, Optional, Set
from pydantic import BaseModel, Field, RootModel, field_validator, model_validator

HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class GoldEntity(BaseModel):
    gold_entity_id: str = Field(..., min_length=1, description="Unique entity ID in case, e.g. ENT-01")
    canonical_name: str = Field(..., min_length=1)
    aliases: List[str] = Field(default_factory=list)

    @field_validator("gold_entity_id", "canonical_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
        return v


class GoldMention(BaseModel):
    gold_mention_id: str = Field(..., min_length=1, description="Unique mention ID, e.g. GMEN-01")
    gold_entity_id: str = Field(..., min_length=1, description="Target entity this mention refers to")
    source_content_sha256: str = Field(..., description="64-char lowercase hex SHA256 of source HTML payload")
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., gt=0)
    verbatim_text: str = Field(..., min_length=1)

    @field_validator("source_content_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        v = v.strip().lower()
        if not HEX64_PATTERN.match(v):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v

    @model_validator(mode="after")
    def validate_spans(self) -> "GoldMention":
        if self.char_end <= self.char_start:
            raise ValueError(
                f"Mention {self.gold_mention_id}: char_end ({self.char_end}) must be strictly greater than char_start ({self.char_start})"
            )
        return self


class GoldClaim(BaseModel):
    claim_id: str = Field(..., min_length=1, description="Unique claim ID, e.g. GCLM-01")
    subject_gold_entity_id: str = Field(..., min_length=1, description="Entity ID this fact belongs to")
    predicate: str = Field(..., min_length=1)
    object_raw: str = Field(..., min_length=1)
    equivalence_set: List[str] = Field(default_factory=list)
    polarity: str = Field(..., description="'affirmative' or 'negative'")
    temporal_status: str = Field(..., description="'current', 'former', or 'unknown'")

    @field_validator("polarity")
    @classmethod
    def validate_polarity(cls, v: str) -> str:
        clean = v.strip().lower().replace("factpolarity.", "")
        if clean not in {"affirmative", "negative"}:
            raise ValueError(f"Invalid polarity '{v}', must be 'affirmative' or 'negative'")
        return clean

    @field_validator("temporal_status")
    @classmethod
    def validate_temporal(cls, v: str) -> str:
        clean = v.strip().lower().replace("temporalstatus.", "")
        if clean not in {"current", "former", "unknown"}:
            raise ValueError(f"Invalid temporal_status '{v}', must be 'current', 'former', or 'unknown'")
        return clean


class GoldCase(BaseModel):
    case_id: str = Field(..., min_length=1)
    target_name: str = Field(..., min_length=1)
    target_gold_entity_id: Optional[str] = None
    expected_outcome: str = "completed"
    expected_outcome_name_only: Optional[str] = None
    expected_outcome_hinted: Optional[str] = None
    is_fact_bearing: bool = True
    gold_entities: List[GoldEntity] = Field(default_factory=list)
    gold_mentions: List[GoldMention] = Field(default_factory=list)
    gold_clusters: List[List[str]] = Field(default_factory=list, description="Clusters of gold_mention_ids")
    gold_claims: List[GoldClaim] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_case_integrity(self) -> "GoldCase":
        # 1. Intra-case uniqueness
        ent_ids = [e.gold_entity_id for e in self.gold_entities]
        if len(ent_ids) != len(set(ent_ids)):
            raise ValueError(f"Case {self.case_id}: Duplicate gold_entity_id found in entities: {ent_ids}")
        ent_set = set(ent_ids)

        men_ids = [m.gold_mention_id for m in self.gold_mentions]
        if len(men_ids) != len(set(men_ids)):
            raise ValueError(f"Case {self.case_id}: Duplicate gold_mention_id found in mentions: {men_ids}")
        men_set = set(men_ids)

        clm_ids = [c.claim_id for c in self.gold_claims]
        if len(clm_ids) != len(set(clm_ids)):
            raise ValueError(f"Case {self.case_id}: Duplicate claim_id found in claims: {clm_ids}")

        # 2. Foreign key closure
        if self.target_gold_entity_id and self.target_gold_entity_id not in ent_set:
            raise ValueError(
                f"Case {self.case_id}: target_gold_entity_id '{self.target_gold_entity_id}' not found in gold_entities"
            )

        for m in self.gold_mentions:
            if m.gold_entity_id not in ent_set:
                raise ValueError(
                    f"Case {self.case_id}: Mention {m.gold_mention_id} references unknown gold_entity_id '{m.gold_entity_id}'"
                )

        for c in self.gold_claims:
            if c.subject_gold_entity_id not in ent_set:
                raise ValueError(
                    f"Case {self.case_id}: Claim {c.claim_id} references unknown subject_gold_entity_id '{c.subject_gold_entity_id}'"
                )

        # 3. Gold clusters partition check
        cluster_mentions: List[str] = []
        for cluster in self.gold_clusters:
            for mid in cluster:
                if mid not in men_set:
                    raise ValueError(f"Case {self.case_id}: Cluster contains unknown mention_id '{mid}'")
                cluster_mentions.append(mid)

        if len(cluster_mentions) != len(set(cluster_mentions)):
            raise ValueError(f"Case {self.case_id}: Gold clusters are not disjoint! Mentions duplicated across clusters.")

        if self.gold_mentions and set(cluster_mentions) != men_set:
            missing_mids = men_set - set(cluster_mentions)
            raise ValueError(f"Case {self.case_id}: Gold clusters do not fully partition mentions. Missing: {missing_mids}")

        # 4. is_fact_bearing consistency
        expected_fact_bearing = (len(self.gold_claims) > 0)
        if self.is_fact_bearing != expected_fact_bearing:
            raise ValueError(
                f"Case {self.case_id}: Inconsistent is_fact_bearing={self.is_fact_bearing} with len(gold_claims)={len(self.gold_claims)}"
            )

        return self


class GoldSuite(RootModel[List[GoldCase]]):
    """Container for entire suite of GoldCases enforcing global uniqueness of case_id."""

    @model_validator(mode="after")
    def validate_global_suite_integrity(self) -> "GoldSuite":
        cids = [c.case_id for c in self.root]
        if len(cids) != len(set(cids)):
            from collections import Counter
            dupes = [cid for cid, cnt in Counter(cids).items() if cnt > 1]
            raise ValueError(f"Duplicate case_id found across Gold suite: {dupes}")
        return self

    def __iter__(self):
        return iter(self.root)

    def __len__(self):
        return len(self.root)

    def __getitem__(self, item):
        return self.root[item]
