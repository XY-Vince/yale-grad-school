"""
Pydantic core schemas for verify-public-person-profile (V4.2).
Single source of truth for the entire public person profiling and verification pipeline.
"""

import calendar
from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, model_validator


class RunOutcome(str, Enum):
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    COLLECTION_FAILED = "collection_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    AMBIGUOUS_IDENTITY = "ambiguous_identity"
    FAILED = "failed"


class FactPolarity(str, Enum):
    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"


class TemporalStatus(str, Enum):
    CURRENT = "current"
    FORMER = "former"
    UNKNOWN = "unknown"


class AdjudicationStatus(str, Enum):
    SUPPORTED = "supported"
    VERIFIED = "verified"
    REFUTED = "refuted"
    CONTESTED = "contested"
    UNRESOLVED = "unresolved"


PREDICATE_ALLOWLIST = {
    "holds_position",
    "employed_by",
    "graduated_from",
    "received_degree",
    "member_of",
    "authored_publication",
    "awarded_honor",
    "affiliated_with",
    "based_in",
}

RELATION_REQUIRED_PREDICATES = set(PREDICATE_ALLOWLIST)


class DatePrecision(str, Enum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


class DateWithPrecision(BaseModel):
    date_value: date
    precision: DatePrecision = DatePrecision.DAY

    def to_iso_date(self) -> str:
        """Compatibility helper returning ISO format string."""
        return self.date_value.isoformat()

    def get_bounds(self) -> Tuple[date, date]:
        """Return (lower_bound, upper_bound) date tuple based on precision."""
        d = self.date_value
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if self.precision == DatePrecision.YEAR:
            return date(d.year, 1, 1), date(d.year, 12, 31)
        elif self.precision == DatePrecision.MONTH:
            last_day = calendar.monthrange(d.year, d.month)[1]
            return date(d.year, d.month, 1), date(d.year, d.month, last_day)
        return d, d


class OriginType(str, Enum):
    SOURCE_STATED = "source_stated"
    GENERATED_HYPOTHESIS = "generated_hypothesis"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class MachineRelation(str, Enum):
    MATCH = "match"
    NONMATCH = "nonmatch"
    REVIEW = "review"


class ClusteringMethod(str, Enum):
    CONSTRAINED_UNION_FIND = "constrained_union_find"
    CONNECTED_COMPONENTS = "connected_components"
    HAC = "hac"


class SourceQualityClass(str, Enum):
    CLASS_A = "class_a"  # Official government, edu institutions, certified registries
    CLASS_B = "class_b"  # Reputable media, peer-reviewed journals, verified databases
    CLASS_C = "class_c"  # User-generated content, blogs, unverified social profiles


class LocatorType(str, Enum):
    CSS = "css"
    PDF_BBOX = "pdf_bbox"
    JSONPATH = "jsonpath"
    SEARCH_SNIPPET = "search_snippet"


class EvidenceLocator(BaseModel):
    locator_type: LocatorType
    selector_or_page: str


class SourceSnapshot(BaseModel):
    source_id: str
    url: str
    canonical_url: Optional[str] = None
    publisher: str
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    current_as_of: Optional[date] = None
    content_sha256: str
    warc_record_id: Optional[str] = None
    http_status: int = 200


class Evidence(BaseModel):
    evidence_id: str
    source_id: str
    verbatim_excerpt: str
    locator: EvidenceLocator
    retrieved_at: datetime
    source_quality_class: SourceQualityClass = SourceQualityClass.CLASS_B
    raw_payload_sha256: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class AliasRecord(BaseModel):
    alias_value: str
    origin_type: OriginType
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_source_id: Optional[str] = None


class EntityMention(BaseModel):
    mention_id: str
    raw_name_text: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    context_snippet: str = Field(..., min_length=1)
    evidence_id: str = Field(..., min_length=1)
    mention_key: str = Field(..., min_length=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., gt=0)
    inferred_affiliations: List[str] = Field(default_factory=list)
    alias_hypotheses: List[AliasRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_mention_spans(self) -> "EntityMention":
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be strictly greater than char_start ({self.char_start})"
            )
        return self


class MatchDecision(BaseModel):
    decision_id: str
    source_mention_id: str
    target_mention_id: str
    algorithm: str  # e.g. "token_jaccard", "multi_field_constrained"
    match_probability: float
    machine_relation: MachineRelation
    explanation: str


class ClusterAssignment(BaseModel):
    cluster_id: str
    mention_ids: List[str]
    clustering_method: ClusteringMethod
    threshold_used: float


class CandidateEntity(BaseModel):
    candidate_entity_id: str
    proposed_cluster_id: str
    human_confirmed_entity_id: Optional[str] = None
    mention_ids: List[str]


class ClaimEvidenceSupport(BaseModel):
    evidence_id: str = Field(..., min_length=1)
    subject_mention_id: str = Field(..., min_length=1)
    clause_span_start: int = Field(..., ge=0)
    clause_span_end: int = Field(..., gt=0)
    verbatim_clause: str = Field(..., min_length=1)
    relation_span_start: Optional[int] = Field(default=None, ge=0)
    relation_span_end: Optional[int] = Field(default=None, gt=0)
    provenance_level: Optional[Literal["clause", "relation"]] = None
    subject_resolution: Optional[Literal["explicit_mention", "pronoun_anaphora", "pro_drop_anaphora", "profile_field", "coordinated_subject"]] = "explicit_mention"
    antecedent_mention_id: Optional[str] = None
    antecedent_clause_span: Optional[Tuple[int, int]] = None

    @model_validator(mode="after")
    def validate_clause_spans(self) -> "ClaimEvidenceSupport":
        if self.clause_span_end <= self.clause_span_start:
            raise ValueError(
                f"clause_span_end ({self.clause_span_end}) must be strictly greater than clause_span_start ({self.clause_span_start})"
            )
        if (self.relation_span_start is None) != (self.relation_span_end is None):
            raise ValueError(
                "relation_span_start and relation_span_end must both be set or both be None"
            )
        if self.relation_span_start is not None and self.relation_span_end is not None:
            if self.relation_span_end <= self.relation_span_start:
                raise ValueError(
                    f"relation_span_end ({self.relation_span_end}) must be strictly greater than relation_span_start ({self.relation_span_start})"
                )
            if self.provenance_level is None:
                self.provenance_level = "relation"
            elif self.provenance_level != "relation":
                raise ValueError(
                    "provenance_level must be 'relation' when relation_span_start and relation_span_end are set"
                )
        else:
            if self.provenance_level is None:
                self.provenance_level = "clause"
            elif self.provenance_level == "relation":
                raise ValueError(
                    "relation_span_start and relation_span_end must both be set when provenance_level is 'relation'"
                )

        # Conditional constraints on subject_resolution and antecedent fields
        if self.subject_resolution in ("pro_drop_anaphora", "pronoun_anaphora"):
            if not self.antecedent_mention_id or not isinstance(self.antecedent_mention_id, str) or not self.antecedent_mention_id.strip():
                raise ValueError(
                    f"antecedent_mention_id must be provided and non-empty for subject_resolution='{self.subject_resolution}'"
                )
            if not self.antecedent_clause_span:
                raise ValueError(
                    f"antecedent_clause_span must be provided for subject_resolution='{self.subject_resolution}'"
                )
            ante_s, ante_e = self.antecedent_clause_span
            if ante_e <= ante_s:
                raise ValueError(
                    f"antecedent_clause_span end ({ante_e}) must be greater than start ({ante_s})"
                )
            if ante_e > self.clause_span_start:
                raise ValueError(
                    f"antecedent_clause_span end ({ante_e}) must precede or equal current clause_span_start ({self.clause_span_start})"
                )
        else:
            if self.antecedent_mention_id is not None:
                raise ValueError(
                    f"antecedent_mention_id must be None for subject_resolution='{self.subject_resolution}'"
                )
            if self.antecedent_clause_span is not None:
                raise ValueError(
                    f"antecedent_clause_span must be None for subject_resolution='{self.subject_resolution}'"
                )

        return self


class Claim(BaseModel):
    claim_id: str
    candidate_entity_id: str
    subject_mention_id: str
    predicate: str
    object_raw: str = Field(..., min_length=1)
    object_norm_id: Optional[str] = None
    polarity: FactPolarity = FactPolarity.AFFIRMATIVE
    temporal_status: TemporalStatus = TemporalStatus.UNKNOWN
    adjudication_status: AdjudicationStatus = AdjudicationStatus.UNRESOLVED
    valid_from: Optional[DateWithPrecision] = None
    valid_to: Optional[DateWithPrecision] = None
    as_of: Optional[date] = None
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(..., min_length=1)
    support_clauses: List[ClaimEvidenceSupport] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_temporal_interval(self) -> "Claim":
        if self.valid_from and self.valid_to:
            start_bounds = self.valid_from.get_bounds()
            end_bounds = self.valid_to.get_bounds()
            if start_bounds[0] > end_bounds[1]:
                raise ValueError(
                    f"Invalid temporal interval: valid_from ({self.valid_from.date_value}) cannot be later than valid_to ({self.valid_to.date_value})"
                )
        return self


class DossierStatement(BaseModel):
    statement_id: str
    section: str
    rendered_text: str
    backed_claim_ids: List[str]


class Dossier(BaseModel):
    dossier_id: str
    candidate_entity_id: Optional[str] = None
    proposed_cluster_id: Optional[str] = None
    statements: List[DossierStatement]
    ambiguous_candidates: List[str] = Field(default_factory=list)
    generated_at: datetime


class AbstentionRecord(BaseModel):
    gap_id: str
    target_name: str
    query_executed: str
    reason: str
    observed_at: datetime = Field(default_factory=datetime.utcnow)


class RunManifest(BaseModel):
    run_id: str
    run_outcome: RunOutcome = RunOutcome.COMPLETED
    run_fingerprint: Optional[str] = None
    tool_version: str
    model_name: str
    query_budget: int
    queries_executed: int
    pages_fetched: int
    crawl_errors: List[str] = Field(default_factory=list)
    abstention_records: List[AbstentionRecord] = Field(default_factory=list)
    execution_time_seconds: float


class RootBundle(BaseModel):
    """Unified root container exporting the complete schema with native $defs."""
    sources: List[SourceSnapshot] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    mentions: List[EntityMention] = Field(default_factory=list)
    candidates: List[CandidateEntity] = Field(default_factory=list)
    matches: List[MatchDecision] = Field(default_factory=list)
    clusters: List[ClusterAssignment] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    dossier: Optional[Dossier] = None
    manifest: Optional[RunManifest] = None
