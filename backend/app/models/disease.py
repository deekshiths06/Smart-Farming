"""AI Crop Disease Identification model.

One table:

- ``disease_assessments`` - one row per leaf-image assessment a signed-in user
  runs. Each row keeps the image's *metadata* only - never the image bytes.
  Uploaded photos are decoded and processed in memory, then discarded, so no
  farmer's photo is ever stored on disk or visible to anyone else. The row also
  keeps the selected crop, the model's actual output (predicted class,
  confidence and the top candidates) and an honest result status.

Rows are owned by exactly one user (``user_id``); every query filters on it and
guessed ids yield 404. Deleting a user removes their rows
(``ondelete=CASCADE``). Assessments are immutable once written - they are a
screening history, not an editable record.
"""

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
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base
from app.services.plant_disease_model import ASSESSMENT_STATUSES

_STATUSES_SQL = "(" + ",".join(f"'{value}'" for value in ASSESSMENT_STATUSES) + ")"


class DiseaseAssessment(Base):
    """One image-based disease screening for a signed-in user."""

    __tablename__ = "disease_assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The crop the farmer selected (a model-supported key + its label).
    crop = Column(String(40), nullable=False)
    crop_label = Column(String(80), nullable=False)

    # Uploaded-image metadata. The bytes are never persisted.
    image_filename = Column(String(255), nullable=False)
    image_content_type = Column(String(100), nullable=False)
    image_size_bytes = Column(Integer, nullable=False)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)

    # Optional symptoms the farmer typed in, used only as context in the UI.
    symptoms = Column(Text, nullable=True)

    # Result. ``status`` is one of ASSESSMENT_STATUSES.
    status = Column(String(30), nullable=False)
    predicted_class = Column(String(160), nullable=True)
    predicted_crop = Column(String(80), nullable=True)
    predicted_crop_label = Column(String(80), nullable=True)
    predicted_disease_label = Column(String(160), nullable=True)
    is_healthy = Column(Boolean, nullable=True)
    confidence = Column(Double, nullable=True)
    candidates = Column(JSON, nullable=True)

    model_name = Column(String(120), nullable=False)
    model_version = Column(String(40), nullable=False)
    latency_ms = Column(Integer, nullable=True)
    disclaimer = Column(String(700), nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())

    owner = relationship("User", back_populates="disease_assessments", passive_deletes=True)

    __table_args__ = (
        CheckConstraint(f"status IN {_STATUSES_SQL}", name="ck_disease_assessments_status"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_disease_assessments_confidence_range",
        ),
        CheckConstraint(
            "image_size_bytes >= 0",
            name="ck_disease_assessments_image_size_non_negative",
        ),
        Index("ix_disease_assessments_user_created", "user_id", "created_at"),
    )


__all__ = ["DiseaseAssessment"]
