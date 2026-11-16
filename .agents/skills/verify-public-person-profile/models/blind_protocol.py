"""Strict public and hidden contracts for preregistered Blind Evaluation V2."""

from __future__ import annotations

import re
from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

BLIND_V2_REQUIRED_ASSETS = frozenset(
    {
        "capture_failures.jsonl",
        "capture_manifest.jsonl",
        "case_manifest.json",
        "corpus.warc",
        "gold.json",
        "query_index.jsonl",
    }
)


class StrictProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BlindStratumSpec(StrictProtocolModel):
    stratum_id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_\-]*$")
    case_count: int = Field(..., gt=0)
    fact_bearing: bool
    description: str = Field(..., min_length=1)


class BlindGateThresholds(StrictProtocolModel):
    target_entity_case_recall: float = Field(..., ge=1.0, le=1.0)
    entity_source_recall: float = Field(..., ge=0.95, le=1.0)
    max_false_merges: int = Field(..., ge=0, le=0)
    max_false_splits: int = Field(..., ge=0, le=0)
    max_unmatched_released_claims: int = Field(..., ge=0, le=0)
    macro_claim_precision: float = Field(..., ge=0.95, le=1.0)
    macro_claim_recall: float = Field(..., ge=0.80, le=1.0)
    subject_attribution_accuracy: float = Field(..., ge=0.95, le=1.0)
    outcome_accuracy: float = Field(..., ge=0.90, le=1.0)
    abstention_accuracy: float = Field(..., ge=1.0, le=1.0)
    paired_input_identity_required: Literal[True]


class BlindPreregistration(StrictProtocolModel):
    protocol_version: Literal["2.0"]
    suite_id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_\-]*$")
    evaluation_role: Literal["blind_release"]
    candidate_git_commit: str
    evaluator_sha256: str
    gold_schema_sha256: str
    expected_case_count: int = Field(..., ge=30)
    candidate_pool_minimum: int = Field(..., ge=90)
    selection_method: Literal["stratified_seeded_without_replacement"]
    permitted_attempts: Literal[1]
    track_name: Literal["hinted"]
    paired_control_required: Literal[True]
    query_budget_per_case: int = Field(..., ge=1, le=100)
    investigator_isolation_backend: Literal["macos_seatbelt"]
    one_shot_execution_required: Literal[True]
    independent_curator_required: Literal[True]
    hidden_gold_required: Literal[True]
    gold_annotation_policy: Literal["two_curators_independent_then_adjudicated"]
    minimum_independent_curators: int = Field(..., ge=2)
    adjudicator_separate_from_implementation: Literal[True]
    selection_seed_commitment_sha256: str
    candidate_pool_commitment_sha256: str
    selection_manifest_commitment_sha256: str
    exclusion_registry_commitment_sha256: str
    curator_attestation_sha256: str
    hidden_asset_manifest_commitment_sha256: str
    excluded_suite_ids: List[str] = Field(..., min_length=1)
    strata: List[BlindStratumSpec] = Field(..., min_length=2)
    thresholds: BlindGateThresholds

    @field_validator(
        "evaluator_sha256",
        "gold_schema_sha256",
        "selection_seed_commitment_sha256",
        "candidate_pool_commitment_sha256",
        "selection_manifest_commitment_sha256",
        "exclusion_registry_commitment_sha256",
        "curator_attestation_sha256",
        "hidden_asset_manifest_commitment_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        clean = value.strip().lower()
        if not HEX64_PATTERN.fullmatch(clean):
            raise ValueError("expected a 64-character lowercase SHA-256 digest")
        return clean

    @field_validator("candidate_git_commit")
    @classmethod
    def validate_git_commit(cls, value: str) -> str:
        clean = value.strip().lower()
        if not HEX40_PATTERN.fullmatch(clean):
            raise ValueError("candidate_git_commit must be a full 40-character Git SHA")
        return clean

    @model_validator(mode="after")
    def validate_preregistration_contract(self) -> "BlindPreregistration":
        stratum_ids = [spec.stratum_id for spec in self.strata]
        if len(stratum_ids) != len(set(stratum_ids)):
            raise ValueError("stratum_id values must be unique")
        quota_total = sum(spec.case_count for spec in self.strata)
        if quota_total != self.expected_case_count:
            raise ValueError(
                f"strata case_count total ({quota_total}) must equal expected_case_count ({self.expected_case_count})"
            )
        if self.candidate_pool_minimum < self.expected_case_count * 3:
            raise ValueError("candidate_pool_minimum must be at least 3x expected_case_count")
        if not any(spec.fact_bearing for spec in self.strata):
            raise ValueError("at least one fact-bearing stratum is required")
        if not any(not spec.fact_bearing for spec in self.strata):
            raise ValueError("at least one abstention stratum is required")
        if len(self.excluded_suite_ids) != len(set(self.excluded_suite_ids)):
            raise ValueError("excluded_suite_ids must be unique")
        return self


class BlindCandidate(StrictProtocolModel):
    candidate_id: str = Field(..., min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")
    target_name: str = Field(..., min_length=1)
    primary_stratum: str = Field(..., min_length=1)
    aliases: List[str] = Field(default_factory=list)
    hints: List[str] = Field(default_factory=list)


class BlindCandidatePool(StrictProtocolModel):
    suite_id: str = Field(..., min_length=1)
    entries: List[BlindCandidate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_candidates(self) -> "BlindCandidatePool":
        candidate_ids = [entry.candidate_id for entry in self.entries]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate_id values must be unique")
        return self


class BlindPersonaEntry(BlindCandidate):
    case_id: str = Field(..., pattern=r"^BLIND2-[0-9]{3}$")


class BlindPersonaManifest(StrictProtocolModel):
    suite_id: str = Field(..., min_length=1)
    entries: List[BlindPersonaEntry] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_selection(self) -> "BlindPersonaManifest":
        case_ids = [entry.case_id for entry in self.entries]
        candidate_ids = [entry.candidate_id for entry in self.entries]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case_id values must be unique")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("selected candidate_id values must be unique")
        return self


class ExcludedPersonaRegistry(StrictProtocolModel):
    suite_id: str = Field(..., min_length=1)
    names: List[str] = Field(..., min_length=1)

    @field_validator("names")
    @classmethod
    def validate_names(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("excluded names must be non-empty")
        return cleaned


class CuratorAttestation(StrictProtocolModel):
    suite_id: str = Field(..., min_length=1)
    curator_id: str = Field(..., min_length=1)
    independent_of_implementation: Literal[True]
    prior_exposure_registry_reviewed: Literal[True]
    candidate_pool_frozen_before_selection: Literal[True]
    independent_curator_count: int = Field(..., ge=2)
    adjudication_completed: Literal[True]
    notes: str = ""


class BlindAssetRecord(StrictProtocolModel):
    sha256: str
    bytes: int = Field(..., ge=0)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        clean = value.strip().lower()
        if not HEX64_PATTERN.fullmatch(clean):
            raise ValueError("expected a 64-character lowercase SHA-256 digest")
        return clean


class BlindHiddenAssetManifest(StrictProtocolModel):
    suite_id: str = Field(..., min_length=1)
    assets: Dict[str, BlindAssetRecord]

    @model_validator(mode="after")
    def validate_required_assets(self) -> "BlindHiddenAssetManifest":
        actual = set(self.assets)
        if actual != set(BLIND_V2_REQUIRED_ASSETS):
            missing = sorted(set(BLIND_V2_REQUIRED_ASSETS) - actual)
            extra = sorted(actual - set(BLIND_V2_REQUIRED_ASSETS))
            raise ValueError(
                f"assets must equal the Blind V2 required asset set; missing={missing}, extra={extra}"
            )
        return self
