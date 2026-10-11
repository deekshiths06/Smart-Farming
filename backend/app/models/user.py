from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database.session import Base
from app.models.field import Field  # noqa: F401  (registers Field for mapper configuration)

ROLE_FARMER = "farmer"
ROLE_ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=ROLE_FARMER, index=True)
    phone = Column(String(20))
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    fields = relationship("Field", back_populates="owner", cascade="all, delete-orphan")
    soil_measurements = relationship(
        "SoilMeasurement", back_populates="owner", passive_deletes=True
    )
    soil_reports = relationship("SoilReport", back_populates="owner", passive_deletes=True)
    crop_recommendations = relationship(
        "CropRecommendation", back_populates="owner", passive_deletes=True
    )
    actions = relationship("FieldAction", back_populates="owner", passive_deletes=True)
    disease_assessments = relationship(
        "DiseaseAssessment", back_populates="owner", passive_deletes=True
    )
