"""Crop Intelligence request/response schemas.

Validation mirrors the engine's data rules: a requirement is either a numeric
band (pH, temperature, rainfall, duration) or a categorical set (texture, water
need, season, region) - never both - and categorical values must come from the
documented vocabularies.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field as PydanticField,
    model_validator,
)

from app.decision_engine.constants import (
    ALL_FACTORS,
    FACTOR_LABELS,
    SEASONS,
    STATUS_LABELS,
)
from app.models.crop import CROP_CATEGORIES
from app.services.soil_limits import TEXTURE_CLASSES

NUMERIC_FACTORS = ("ph", "temperature", "rainfall", "duration")
CATEGORICAL_FACTORS = ("texture", "water", "season", "region")
WATER_NEEDS = ("low", "medium", "high")

Factor = Literal[tuple(ALL_FACTORS)]  # type: ignore
Category = Literal[tuple(CROP_CATEGORIES)]  # type: ignore


# --- Crop knowledge base ----------------------------------------------------


class CropRequirementRead(BaseModel):
    id: int
    crop_id: int
    factor: str
    factor_label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[list[str]] = None
    is_essential: bool
    explanation: Optional[str] = None
    source: str
    source_url: Optional[str] = None
    sequence: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CropRead(BaseModel):
    id: int
    name: str
    display_name: str
    category: str
    description: Optional[str] = None
    is_active: bool
    source: str
    source_url: Optional[str] = None
    date_reviewed: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class CropDetailRead(CropRead):
    requirements: list[CropRequirementRead] = []


class CropCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = PydanticField(min_length=1, max_length=60)
    display_name: str = PydanticField(min_length=1, max_length=120)
    category: Category
    description: Optional[str] = PydanticField(default=None, max_length=500)
    is_active: bool = True
    source: str = PydanticField(min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    date_reviewed: Optional[date] = None


class CropUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: Optional[str] = PydanticField(default=None, min_length=1, max_length=120)
    category: Optional[Category] = None
    description: Optional[str] = PydanticField(default=None, max_length=500)
    is_active: Optional[bool] = None
    source: Optional[str] = PydanticField(default=None, min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    date_reviewed: Optional[date] = None


def validate_requirement(
    factor: str,
    min_value: Optional[float],
    max_value: Optional[float],
    allowed_values: Optional[list[str]],
) -> None:
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError("min_value must be <= max_value")

    if factor in NUMERIC_FACTORS:
        if allowed_values:
            raise ValueError(f"{factor} is a numeric factor; use min_value/max_value, not allowed_values")
        if min_value is None and max_value is None:
            raise ValueError(f"{factor} needs at least a min_value or max_value")
    elif factor in CATEGORICAL_FACTORS:
        if min_value is not None or max_value is not None:
            raise ValueError(f"{factor} is categorical; use allowed_values, not min_value/max_value")
        if not allowed_values:
            raise ValueError(f"{factor} needs a non-empty allowed_values list")
        if factor == "texture":
            bad = [v for v in allowed_values if v not in TEXTURE_CLASSES]
        elif factor == "water":
            bad = [v for v in allowed_values if v not in WATER_NEEDS]
        elif factor == "season":
            bad = [v for v in allowed_values if v not in SEASONS]
        else:  # region
            bad = []
        if bad:
            raise ValueError(f"{factor} has unrecognised values: {', '.join(bad)}")


class CropRequirementCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    factor: Factor
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[list[str]] = None
    is_essential: bool = False
    explanation: Optional[str] = PydanticField(default=None, max_length=500)
    source: str = PydanticField(min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    sequence: int = 0

    @model_validator(mode="after")
    def check(self) -> "CropRequirementCreate":
        validate_requirement(self.factor, self.min_value, self.max_value, self.allowed_values)
        return self


class CropRequirementUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[list[str]] = None
    is_essential: Optional[bool] = None
    explanation: Optional[str] = PydanticField(default=None, max_length=500)
    source: Optional[str] = PydanticField(default=None, min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    sequence: Optional[int] = None
    is_active: Optional[bool] = None


# --- Scoring configuration --------------------------------------------------


class ScoringConfigRead(BaseModel):
    id: int
    weights: dict[str, float]
    essential_factors: list[str]
    suitable_threshold: float
    min_coverage: float
    stale_soil_days: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ScoringConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    weights: Optional[dict[str, float]] = None
    essential_factors: Optional[list[str]] = None
    suitable_threshold: Optional[float] = PydanticField(default=None, ge=0, le=1)
    min_coverage: Optional[float] = PydanticField(default=None, ge=0, le=1)
    stale_soil_days: Optional[int] = PydanticField(default=None, ge=0)

    @model_validator(mode="after")
    def check(self) -> "ScoringConfigUpdate":
        if self.weights is not None:
            bad = [k for k in self.weights if k not in ALL_FACTORS]
            if bad:
                raise ValueError(f"Unknown weight factors: {', '.join(bad)}")
        if self.essential_factors is not None:
            bad = [f for f in self.essential_factors if f not in ALL_FACTORS]
            if bad:
                raise ValueError(f"Unknown essential factors: {', '.join(bad)}")
        return self


# --- Evaluation output ------------------------------------------------------


class FactorRead(BaseModel):
    factor: str
    label: str
    status: str
    score: Optional[float] = None
    weight: Optional[float] = None
    input: Optional[Any] = None
    # Older persisted evaluations predate the context-factor ``detail`` field;
    # default it so historical batches remain readable instead of 500-ing.
    detail: str = ""
    requirement: Optional[dict] = None
    is_essential: bool = False
    source: Optional[str] = None
    source_url: Optional[str] = None


class RiskRead(BaseModel):
    kind: str
    severity: str
    title: str
    detail: str
    basis: str
    period: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    source: str


class CropEvaluationRead(BaseModel):
    crop_id: int
    crop_name: str
    display_name: str
    category: str
    description: Optional[str] = None
    status: str
    status_label: str
    score: Optional[float] = None
    coverage: float
    # True when some documented requirement could not be checked (e.g. no soil
    # test yet): the verdict is an evidence-based preliminary estimate, not a
    # refusal. Older batches predate this flag, so it defaults to False.
    preliminary: bool = False
    factors: dict[str, FactorRead]
    context_factors: dict[str, FactorRead] = {}
    reasons: list[str]
    next_steps: list[str] = []
    risks: list[RiskRead]
    notes: list[str]
    source: str
    source_url: Optional[str] = None
    date_reviewed: Optional[str] = None


class RecommendationBatchRead(BaseModel):
    batch_id: str
    field_id: int
    field_name: str
    season: str
    generated_at: datetime
    weather: dict
    soil: dict
    notes: list[str]
    config: dict
    results: list[CropEvaluationRead]
    disclaimer: str


class RecommendationRead(BaseModel):
    id: int
    batch_id: str
    field_id: int
    crop_id: Optional[int] = None
    crop_name: Optional[str] = None
    display_name: Optional[str] = None
    status: str
    status_label: str
    score: Optional[float] = None
    coverage: Optional[float] = None
    season: Optional[str] = None
    engine_version: str
    created_at: datetime
    result: CropEvaluationRead
    input_snapshot: dict


class RecommendationCounts(BaseModel):
    suitable: int = 0
    needs_information: int = 0
    not_recommended: int = 0


class RecommendationBatchSummary(BaseModel):
    batch_id: str
    season: Optional[str] = None
    engine_version: str
    created_at: datetime
    counts: RecommendationCounts
    top_crop: Optional[str] = None


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    crop_ids: list[int] = PydanticField(min_length=1, max_length=20)


class CompareCellRead(BaseModel):
    crop_id: int
    status: str
    score: Optional[float] = None
    value_label: str = "—"
    requirement_text: str = ""
    detail: str = ""


class CompareFactorRead(BaseModel):
    factor: str
    label: str
    value_label: str
    compared: bool
    explanation: str
    cells: list[CompareCellRead] = []


class CompareRankedRead(BaseModel):
    rank: int
    crop_id: int
    display_name: str
    status: str
    status_label: str
    score: Optional[float] = None
    coverage: float
    # A crop with unrecorded requirements is preliminarily ranked, never "better".
    preliminary: bool = False
    supporting: list[str] = []
    constraints: list[str] = []
    missing: list[str] = []


class CompareCollectRead(BaseModel):
    input: str
    action: str


class CompareRead(BaseModel):
    """Full explainable comparison between a chosen subset of crops."""

    results: list[CropEvaluationRead]
    ranking: list[CompareRankedRead]
    factors: list[CompareFactorRead]
    differences: list[str] = []
    rank_changers: list[str] = []
    info_to_collect: list[CompareCollectRead] = []
    preliminary_note: Optional[str] = None
    context: dict
    disclaimer: str


__all__ = [
    "CropRead",
    "CropDetailRead",
    "CropCreate",
    "CropUpdate",
    "CropRequirementRead",
    "CropRequirementCreate",
    "CropRequirementUpdate",
    "ScoringConfigRead",
    "ScoringConfigUpdate",
    "CropEvaluationRead",
    "RecommendationBatchRead",
    "RecommendationRead",
    "RecommendationBatchSummary",
    "CompareRequest",
    "CompareCellRead",
    "CompareFactorRead",
    "CompareRankedRead",
    "CompareCollectRead",
    "CompareRead",
    "STATUS_LABELS",
    "FACTOR_LABELS",
]
