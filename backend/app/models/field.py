from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.session import Base


class Field(Base):
    """A farmer's field. The central object ANNADATA reasons about."""

    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_name = Column(String(120), nullable=False)

    # Location (browser GPS + user confirmation)
    latitude = Column(Double, nullable=True)
    longitude = Column(Double, nullable=True)
    location_accuracy = Column(Double, nullable=True)
    location_confirmed = Column(Boolean, nullable=False, default=False, server_default="0")

    # Reverse-geocoded administrative context (only populated when actually resolved)
    address = Column(String(512), nullable=True)
    locality = Column(String(120), nullable=True)
    sub_district = Column(String(120), nullable=True)
    district = Column(String(120), nullable=True)
    state = Column(String(120), nullable=True)
    country = Column(String(80), nullable=True)

    # Optional field boundary (GeoJSON Polygon, WGS84 lon/lat)
    boundary = Column(JSON, nullable=True)

    # Area
    area = Column(Double, nullable=True)
    area_unit = Column(String(20), nullable=False, default="acre", server_default="acre")
    area_source = Column(String(30), nullable=False, default="not_provided", server_default="not_provided")

    # Water profile (farmer-reported, never technical sensor values)
    water_source = Column(String(30), nullable=True)
    water_availability = Column(String(30), nullable=True)

    # Soil intelligence status: not_provided | pending | available
    soil_status = Column(
        String(20), nullable=False, default="not_provided", server_default="not_provided"
    )

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    owner = relationship("User", back_populates="fields")

    soil_measurements = relationship(
        "SoilMeasurement", back_populates="field", cascade="all, delete-orphan"
    )
    soil_reports = relationship(
        "SoilReport", back_populates="field", cascade="all, delete-orphan"
    )
    crop_recommendations = relationship(
        "CropRecommendation", back_populates="field", cascade="all, delete-orphan"
    )
    actions = relationship(
        "FieldAction", back_populates="field", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_fields_latitude_range",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_fields_longitude_range",
        ),
        CheckConstraint(
            "location_accuracy IS NULL OR location_accuracy >= 0",
            name="ck_fields_location_accuracy_non_negative",
        ),
        CheckConstraint("area IS NULL OR area >= 0", name="ck_fields_area_non_negative"),
        CheckConstraint(
            "area_source IN ('calculated_boundary', 'manual', 'not_provided')",
            name="ck_fields_area_source",
        ),
        CheckConstraint(
            "soil_status IN ('not_provided', 'pending', 'available')",
            name="ck_fields_soil_status",
        ),
        CheckConstraint(
            "water_source IS NULL OR water_source IN "
            "('rain_fed', 'borewell', 'open_well', 'canal', 'multiple', 'other', 'not_sure')",
            name="ck_fields_water_source",
        ),
        CheckConstraint(
            "water_availability IS NULL OR water_availability IN "
            "('limited', 'moderate', 'good', 'seasonal', 'not_sure')",
            name="ck_fields_water_availability",
        ),
        CheckConstraint(
            "area_unit IN ('acre', 'hectare', 'bigha', 'square_metre')",
            name="ck_fields_area_unit",
        ),
        Index("ix_fields_lat_lon", "latitude", "longitude"),
    )
