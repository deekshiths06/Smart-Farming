"""Registers every model with SQLAlchemy's mapper configuration.

Importing ``app.models`` (or any submodule, which first imports this package)
guarantees that string-backed relationships resolve.
"""

from app.models.crop import (  # noqa: F401
    Crop,
    CropRecommendation,
    CropRequirement,
    CropScoringConfig,
)
from app.models.field import Field  # noqa: F401
from app.models.soil import SoilMeasurement, SoilReferenceRange, SoilReport  # noqa: F401
from app.models.user import User  # noqa: F401