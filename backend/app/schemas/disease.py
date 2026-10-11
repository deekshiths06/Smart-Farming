"""AI Crop Disease Identification request/response schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class DiseaseClassRead(BaseModel):
    class_name: str
    disease_label: str
    is_healthy: bool


class DiseaseCropRead(BaseModel):
    key: str
    label: str
    diseases: list[DiseaseClassRead]


class DiseaseAssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    crop: str
    crop_label: str
    image_filename: str
    image_content_type: str
    image_size_bytes: int
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    symptoms: Optional[str] = None
    status: str
    predicted_class: Optional[str] = None
    predicted_crop: Optional[str] = None
    predicted_crop_label: Optional[str] = None
    predicted_disease_label: Optional[str] = None
    is_healthy: Optional[bool] = None
    confidence: Optional[float] = None
    candidates: Optional[list[dict[str, Any]]] = None
    model_name: str
    model_version: str
    latency_ms: Optional[int] = None
    disclaimer: str
    created_at: datetime
