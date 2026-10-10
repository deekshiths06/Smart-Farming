"""Soil Intelligence models.

Three tables:

- ``soil_measurements``   - one row per soil test event for a field. The latest
                            event (by ``tested_on``) is the field's current
                            measurements; older events are the recorded history.
                            Values are only ever stored when actually measured.
- ``soil_reports``        - an uploaded Soil Health Card / laboratory document.
                            Reports are stored securely on disk; this table only
                            keeps metadata and an internal opaque stored name.
- ``soil_reference_ranges`` - configurable agronomic reference values. Rows are
                            seeded by migration 0003 from published guidance and
                            are managed by admins only. Farmers never edit them.

Measurement values are always kept in one documented canonical unit per
parameter (see ``app.services.soil_limits``). A value of ``None`` means "not
measured" - ANNADATA never invents or substitutes averages.
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
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base
from app.services.soil_limits import PARAMETER_NAMES, TEXTURE_CLASSES

SOURCE_KIND_FARMER = "farmer_entered"
SOURCE_KIND_REPORT = "report_confirmed"

REPORT_STATUS_UPLOADED = "uploaded"
REPORT_STATUS_LINKED = "linked"


class SoilMeasurement(Base):
    """One soil test event (laboratory, Soil Health Card, or self-test)."""

    __tablename__ = "soil_measurements"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(
        Integer, ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalised ownership so a measurement can never be fetched for a field
    # the user does not own even by guessing ids.
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # When the soil was actually tested (from the report / laboratory note).
    tested_on = Column(Date, nullable=False, index=True)
    # Free-text testing source, e.g. "Government Soil Testing Lab, Hassan".
    test_source = Column(String(200), nullable=True)
    # farmer_entered = typed by the farmer directly or from a paper report.
    # report_confirmed = values taken from an uploaded report and confirmed.
    source_kind = Column(String(30), nullable=False, default=SOURCE_KIND_FARMER)
    report_id = Column(
        Integer, ForeignKey("soil_reports.id", ondelete="SET NULL"), nullable=True
    )

    # Parameters. All in canonical units (see app.services.soil_limits). None = missing.
    ph = Column(Double, nullable=True)  # unitless (0-14)
    nitrogen = Column(Double, nullable=True)  # kg/ha available N
    phosphorus = Column(Double, nullable=True)  # kg/ha available P
    potassium = Column(Double, nullable=True)  # kg/ha available K
    ec = Column(Double, nullable=True)  # dS/m (1:2 or saturated extract as reported)
    organic_carbon = Column(Double, nullable=True)  # %
    moisture = Column(Double, nullable=True)  # % moisture at time of sampling (gravimetric/volumetric as reported)
    texture = Column(String(30), nullable=True)  # USDA texture class

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    field = relationship("Field", back_populates="soil_measurements", passive_deletes=True)
    owner = relationship("User", back_populates="soil_measurements", passive_deletes=True)
    report = relationship("SoilReport", back_populates="measurements")

    __table_args__ = (
        CheckConstraint(
            "ph IS NULL OR (ph >= 0 AND ph <= 14)",
            name="ck_soil_measurements_ph_range",
        ),
        CheckConstraint(
            "nitrogen IS NULL OR nitrogen >= 0",
            name="ck_soil_measurements_nitrogen_non_negative",
        ),
        CheckConstraint(
            "phosphorus IS NULL OR phosphorus >= 0",
            name="ck_soil_measurements_phosphorus_non_negative",
        ),
        CheckConstraint(
            "potassium IS NULL OR potassium >= 0",
            name="ck_soil_measurements_potassium_non_negative",
        ),
        CheckConstraint(
            "ec IS NULL OR ec >= 0",
            name="ck_soil_measurements_ec_non_negative",
        ),
        CheckConstraint(
            "organic_carbon IS NULL OR organic_carbon >= 0",
            name="ck_soil_measurements_organic_carbon_non_negative",
        ),
        CheckConstraint(
            "moisture IS NULL OR (moisture >= 0 AND moisture <= 100)",
            name="ck_soil_measurements_moisture_range",
        ),
        CheckConstraint(
            f"source_kind IN ('{SOURCE_KIND_FARMER}', '{SOURCE_KIND_REPORT}')",
            name="ck_soil_measurements_source_kind",
        ),
        CheckConstraint(
            "texture IS NULL OR texture IN " + "(" + ",".join(f"'{t}'" for t in TEXTURE_CLASSES) + ")",
            name="ck_soil_measurements_texture",
        ),
        Index("ix_soil_measurements_field_tested", "field_id", "tested_on"),
    )


class SoilReport(Base):
    """Metadata for an uploaded soil report document.

    The file itself lives on disk under ``settings.SOIL_REPORT_STORAGE_DIR``
    using the opaque ``stored_filename``. Only the owner may download it.
    """

    __tablename__ = "soil_reports"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(
        Integer, ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    content_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    report_date = Column(Date, nullable=True)
    report_source = Column(String(200), nullable=True)

    # uploaded = file stored, values not yet entered; linked = measurements
    # confirmed from this report exist.
    status = Column(String(20), nullable=False, default=REPORT_STATUS_UPLOADED)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    field = relationship("Field", back_populates="soil_reports", passive_deletes=True)
    owner = relationship("User", back_populates="soil_reports", passive_deletes=True)
    measurements = relationship(
        "SoilMeasurement", back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'linked')",
            name="ck_soil_reports_status",
        ),
        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_soil_reports_file_size_non_negative",
        ),
    )


class SoilReferenceRange(Base):
    """An agronomic reference band for a soil parameter.

    ``context_type``/``context_value`` express applicability:

    - general  (context_value NULL)       - applies to all soils
    - region   (e.g. "Karnataka")         - narrower geographic guidance
    - soil_class (e.g. "loam")            - applies when soil texture is known
    - crop     (e.g. "rice")              - crop-specific guidance (consumed once
                                            a farmer chooses a crop)

    Ranges are contiguous tiers by default. ``outcome`` records what it means
    for a measured value to fall inside the band: below / within / above an
    ideal target. A band that is the *only* ideal range (e.g. moisture at field
    capacity) is stored with ``outcome='within'`` and the assessment service
    derives below/above for values outside it.
    """

    __tablename__ = "soil_reference_ranges"

    id = Column(Integer, primary_key=True, index=True)
    parameter = Column(String(30), nullable=False, index=True)
    context_type = Column(
        String(20), nullable=False, default="general", index=True
    )
    context_value = Column(String(60), nullable=True)
    label = Column(String(120), nullable=False)
    min_value = Column(Double, nullable=True)
    max_value = Column(Double, nullable=True)
    unit = Column(String(20), nullable=True)
    outcome = Column(String(10), nullable=False, default="within")
    explanation = Column(String(500), nullable=True)
    source = Column(String(200), nullable=False)
    source_url = Column(String(300), nullable=True)
    sequence = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "parameter IN " + "(" + ",".join(f"'{n}'" for n in PARAMETER_NAMES) + ")",
            name="ck_soil_reference_ranges_parameter",
        ),
        CheckConstraint(
            "context_type IN ('general', 'region', 'soil_class', 'crop')",
            name="ck_soil_reference_ranges_context_type",
        ),
        CheckConstraint(
            "outcome IN ('below', 'within', 'above')",
            name="ck_soil_reference_ranges_outcome",
        ),
    )


# Field.user_id ordering keeps assessment context joins cheap.
__all__ = ["SoilMeasurement", "SoilReport", "SoilReferenceRange", "date"]