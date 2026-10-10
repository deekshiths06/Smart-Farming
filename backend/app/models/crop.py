"""Crop Intelligence models.

Four tables:

- ``crops``              - a crop definition with a named source and review date.
- ``crop_requirements``  - one agronomic requirement (factor) per crop: either a
                           numeric band (pH, temperature, rainfall, duration) or an
                           accepted set of categorical values (texture, water need,
                           season, region). Every row carries its own source.
- ``crop_recommendations`` - a persisted suitability estimate for one crop against
                           one field, including the full input snapshot so a past
                           result can be explained later.
- ``crop_scoring_config`` - the single admin-editable scoring configuration
                           (weights, essential factors, thresholds).

The engine only ever compares measured field/soil values and live weather to these
documented requirements. Missing inputs are reported, never guessed.
"""

from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base
from app.decision_engine.constants import (
    ALL_FACTORS,
    DEFAULT_ESSENTIAL_FACTORS,
    DEFAULT_MIN_COVERAGE,
    DEFAULT_STALE_SOIL_DAYS,
    DEFAULT_SUITABLE_THRESHOLD,
    STATUS_LABELS,
)

CROP_CATEGORIES: tuple[str, ...] = (
    "cereal",
    "millet",
    "pulse",
    "oilseed",
    "fibre",
    "vegetable",
)

RECOMMENDATION_STATUSES: tuple[str, ...] = tuple(STATUS_LABELS.keys())


def _sql_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


class Crop(Base):
    """A crop with a documented source for its agronomic guidance."""

    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(60), nullable=False, unique=True, index=True)
    display_name = Column(String(120), nullable=False)
    category = Column(String(30), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    source = Column(String(200), nullable=False)
    source_url = Column(String(300), nullable=True)
    date_reviewed = Column(Date, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    requirements = relationship(
        "CropRequirement",
        back_populates="crop",
        cascade="all, delete-orphan",
        order_by="CropRequirement.factor, CropRequirement.sequence",
    )
    recommendations = relationship(
        "CropRecommendation", back_populates="crop", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint(
            "category IN " + _sql_list(CROP_CATEGORIES),
            name="ck_crops_category",
        ),
    )


class CropRequirement(Base):
    """One documented agronomic requirement for a crop."""

    __tablename__ = "crop_requirements"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(
        Integer, ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    factor = Column(String(30), nullable=False, index=True)

    # Numeric band (pH, temperature, rainfall, duration). Either end may be NULL
    # for an open-ended band, but never both for a numeric factor (enforced in
    # the API layer; the score treats an open end with a documented fallback).
    min_value = Column(Double, nullable=True)
    max_value = Column(Double, nullable=True)

    # Categorical set (texture classes, water need, seasons, regions).
    allowed_values = Column(JSON, nullable=True)

    # A factor the crop cannot be judged without (e.g. pH, water).
    is_essential = Column(Boolean, nullable=False, default=False, server_default="0")

    explanation = Column(String(500), nullable=True)
    source = Column(String(200), nullable=False)
    source_url = Column(String(300), nullable=True)
    sequence = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    crop = relationship("Crop", back_populates="requirements")

    @property
    def factor_label(self) -> str:
        from app.decision_engine.constants import FACTOR_LABELS

        return FACTOR_LABELS.get(self.factor, self.factor)

    __table_args__ = (
        CheckConstraint(
            "factor IN " + _sql_list(ALL_FACTORS),
            name="ck_crop_requirements_factor",
        ),
        CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
            name="ck_crop_requirements_min_max",
        ),
        UniqueConstraint("crop_id", "factor", name="uq_crop_requirements_crop_factor"),
    )


class CropScoringConfig(Base):
    """The single admin-editable scoring configuration.

    Exactly one active row is expected. The engine falls back to the documented
    defaults in ``app.decision_engine.constants`` if the table is empty.
    """

    __tablename__ = "crop_scoring_config"

    id = Column(Integer, primary_key=True, index=True)
    weights = Column(JSON, nullable=False)
    essential_factors = Column(JSON, nullable=False)
    suitable_threshold = Column(
        Double, nullable=False, default=DEFAULT_SUITABLE_THRESHOLD
    )
    min_coverage = Column(Double, nullable=False, default=DEFAULT_MIN_COVERAGE)
    stale_soil_days = Column(Integer, nullable=False, default=DEFAULT_STALE_SOIL_DAYS)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "suitable_threshold >= 0 AND suitable_threshold <= 1",
            name="ck_crop_scoring_config_suitable",
        ),
        CheckConstraint(
            "min_coverage >= 0 AND min_coverage <= 1",
            name="ck_crop_scoring_config_coverage",
        ),
        CheckConstraint("stale_soil_days >= 0", name="ck_crop_scoring_config_stale"),
    )

    def default_essential_factors(self) -> list[str]:
        return list(DEFAULT_ESSENTIAL_FACTORS)


class CropRecommendation(Base):
    """A persisted suitability estimate for one crop against one field.

    ``result`` holds the transparent breakdown (per-factor scores and reasons,
    risks, notes); ``input_snapshot`` holds the exact field/soil/weather inputs
    used, so a later request can explain or audit a past estimate.
    """

    __tablename__ = "crop_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(
        Integer, ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_id = Column(
        Integer, ForeignKey("crops.id", ondelete="SET NULL"), nullable=True, index=True
    )

    batch_id = Column(String(40), nullable=False, index=True)
    engine_version = Column(String(20), nullable=False)
    season = Column(String(20), nullable=True)

    status = Column(String(20), nullable=False, index=True)
    score = Column(Double, nullable=True)
    coverage = Column(Double, nullable=True)

    result = Column(JSON, nullable=False)
    input_snapshot = Column(JSON, nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    field = relationship("Field", back_populates="crop_recommendations")
    owner = relationship("User", back_populates="crop_recommendations", passive_deletes=True)
    crop = relationship("Crop", back_populates="recommendations")

    __table_args__ = (
        CheckConstraint(
            "status IN " + _sql_list(RECOMMENDATION_STATUSES),
            name="ck_crop_recommendations_status",
        ),
        Index("ix_crop_recommendations_field_created", "field_id", "created_at"),
    )


__all__ = [
    "Crop",
    "CropRequirement",
    "CropRecommendation",
    "CropScoringConfig",
    "CROP_CATEGORIES",
    "RECOMMENDATION_STATUSES",
    "date",
]
