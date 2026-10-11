"""AI Crop Disease Identification API.

A genuine image-classification endpoint plus a per-user screening history.

Honesty and safety are enforced here:

- the authenticated user comes from the JWT, never from the request;
- uploaded images are validated (type + size) and processed in memory only -
  the bytes are never written to disk, so no photo is ever visible to anyone;
- a crop outside the model's documented coverage is rejected *before* any
  inference runs - the app never silently forces an unknown crop into a known
  disease;
- a result whose predicted crop does not match the selected crop is reported as
  a mismatch, and a low-confidence result as unreliable - neither is dressed up
  as a diagnosis;
- the response carries no pesticide or chemical recommendations, only a pointer
  to qualified local advice;
- every query filters on the owner's ``user_id``; a guessed id yields 404.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.database.deps import get_db
from app.models.disease import DiseaseAssessment
from app.models.user import User
from app.schemas.disease import DiseaseAssessmentRead, DiseaseCropRead
from app.services import plant_disease_model

router = APIRouter()

DISCLAIMER = (
    "This is an automated image-based screening, not a confirmed diagnosis. It "
    "estimates the most likely condition from a single leaf photo and can be "
    "wrong, especially for unclear photos or crops outside the supported list. "
    "It does not recommend pesticides or fertilisers. For treatment and any "
    "chemical use, consult your local agricultural extension officer or plant "
    "protection expert, and follow the product label and local rules."
)


def _owned_assessment(assessment_id: int, user: User, db: Session) -> DiseaseAssessment:
    record = (
        db.query(DiseaseAssessment)
        .filter(
            DiseaseAssessment.id == assessment_id,
            DiseaseAssessment.user_id == user.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found"
        )
    return record


@router.get("/crops", response_model=List[DiseaseCropRead])
async def list_supported_crops(current_user: User = Depends(get_current_user)):
    """The crops and conditions the installed model can actually assess."""
    try:
        return plant_disease_model.supported_crops()
    except plant_disease_model.ModelUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/assessments", response_model=List[DiseaseAssessmentRead])
async def list_assessments(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(DiseaseAssessment)
        .filter(DiseaseAssessment.user_id == current_user.id)
        .order_by(DiseaseAssessment.created_at.desc(), DiseaseAssessment.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/assessments/{assessment_id}", response_model=DiseaseAssessmentRead)
async def get_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_assessment(assessment_id, current_user, db)


@router.delete("/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _owned_assessment(assessment_id, current_user, db)
    db.delete(record)
    db.commit()
    return None


@router.post("/assess", response_model=DiseaseAssessmentRead, status_code=status.HTTP_201_CREATED)
async def assess_image(
    file: UploadFile = File(...),
    crop: str = Form(...),
    symptoms: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop_key = (crop or "").strip().lower()
    crop_meta = plant_disease_model.crop_meta(crop_key)
    if crop_meta is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Crop '{crop}' is not supported by the disease model. "
                f"Supported crops: {plant_disease_model.supported_crop_labels()}."
            ),
        )

    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The upload has no filename.",
        )

    max_bytes = settings.DISEASE_IMAGE_MAX_SIZE_BYTES
    payload = await file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image is too large. Maximum size is {settings.DISEASE_IMAGE_MAX_SIZE_MB} MB.",
        )
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded image is empty.",
        )

    try:
        result = plant_disease_model.predict(payload, crop_key)
    except plant_disease_model.CropNotSupported as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except plant_disease_model.InvalidImage as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except plant_disease_model.ModelUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    record = DiseaseAssessment(
        user_id=current_user.id,
        crop=crop_key,
        crop_label=crop_meta["label"],
        image_filename=plant_disease_model.safe_image_name(filename),
        image_content_type=(file.content_type or "application/octet-stream")[:100],
        image_size_bytes=len(payload),
        image_width=result.image_width,
        image_height=result.image_height,
        symptoms=(symptoms or "").strip() or None,
        status=result.status,
        predicted_class=result.predicted_class,
        predicted_crop=result.predicted_crop,
        predicted_crop_label=result.predicted_crop_label,
        predicted_disease_label=result.predicted_disease_label,
        is_healthy=result.is_healthy,
        confidence=result.confidence,
        candidates=result.candidates,
        model_name=result.model_name,
        model_version=result.model_version,
        latency_ms=result.latency_ms,
        disclaimer=DISCLAIMER,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
