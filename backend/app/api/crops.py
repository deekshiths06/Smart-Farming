"""Crop Intelligence API.

Ownership follows the rest of ANNADATA: the authenticated user comes from the
JWT, and every field-scoped query filters on the field's ``user_id``. A guessed
field or recommendation id yields 404.

The knowledge base (crops and requirements) is read-only to farmers; admins
manage it through ``/api/admin/crops``. Generating recommendations persists the
result plus the exact input snapshot so a past estimate can be explained later.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.deps import get_db
from app.decision_engine import constants as C
from app.decision_engine import comparison, recommendation as engine
from app.models.crop import Crop, CropRecommendation
from app.models.field import Field
from app.models.user import User
from app.schemas.crop import (
    CompareRead,
    CompareRequest,
    CropDetailRead,
    CropEvaluationRead,
    CropRead,
    RecommendationBatchRead,
    RecommendationBatchSummary,
    RecommendationCounts,
    RecommendationRead,
)
from app.services import weather_service

router = APIRouter()


def _owned_field(field_id: int, user: User, db: Session) -> Field:
    field = (
        db.query(Field).filter(Field.id == field_id, Field.user_id == user.id).first()
    )
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return field


def _owned_recommendation(field: Field, rec_id: int, db: Session) -> CropRecommendation:
    record = (
        db.query(CropRecommendation)
        .filter(
            CropRecommendation.id == rec_id,
            CropRecommendation.field_id == field.id,
            CropRecommendation.user_id == field.user_id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
    return record


def _recommendation_payload(record: CropRecommendation, crop: Optional[Crop]) -> dict:
    return {
        "id": record.id,
        "batch_id": record.batch_id,
        "field_id": record.field_id,
        "crop_id": record.crop_id,
        "crop_name": crop.name if crop else None,
        "display_name": crop.display_name if crop else None,
        "status": record.status,
        "status_label": C.STATUS_LABELS.get(record.status, record.status),
        "score": record.score,
        "coverage": record.coverage,
        "season": record.season,
        "engine_version": record.engine_version,
        "created_at": record.created_at,
        "result": record.result,
        "input_snapshot": record.input_snapshot,
    }


async def _fetch_weather(field: Field) -> tuple[Optional[weather_service.WeatherSnapshot], Optional[str]]:
    """Best-effort live weather. Never blocks a recommendation if unavailable."""
    if field.latitude is None or field.longitude is None:
        return None, "This field has no confirmed coordinates, so live weather was not fetched."
    try:
        snapshot = await weather_service.fetch_full_weather(field.latitude, field.longitude)
        return snapshot, None
    except weather_service.WeatherServiceError as exc:
        return None, exc.user_message


# --- Knowledge base ---------------------------------------------------------


@router.get("/crops", response_model=List[CropRead])
async def list_crops(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Every active crop in the knowledge base (read-only to farmers)."""
    return (
        db.query(Crop)
        .filter(Crop.is_active.is_(True))
        .order_by(Crop.display_name)
        .all()
    )


@router.get("/crops/{crop_id}", response_model=CropDetailRead)
async def get_crop(
    crop_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crop = db.query(Crop).filter(Crop.id == crop_id, Crop.is_active.is_(True)).first()
    if crop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    return crop


# --- Recommendations --------------------------------------------------------


@router.post(
    "/fields/{field_id}/crops/recommendations",
    response_model=RecommendationBatchRead,
    status_code=status.HTTP_201_CREATED,
)
async def generate_recommendations(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and persist a fresh suitability estimate for every crop."""
    field = _owned_field(field_id, current_user, db)
    weather, weather_reason = await _fetch_weather(field)
    evaluation = engine.generate_recommendations(db, field, weather, weather_reason)
    return {
        "batch_id": evaluation["batch_id"],
        "field_id": field.id,
        "field_name": field.field_name,
        "season": evaluation["season"],
        "generated_at": datetime.now(timezone.utc),
        "weather": evaluation["weather"],
        "soil": evaluation["soil"],
        "notes": evaluation["notes"],
        "config": evaluation["config"],
        "results": evaluation["results"],
        "disclaimer": C.SUITABILITY_DISCLAIMER,
    }


@router.post(
    "/fields/{field_id}/crops/compare",
    response_model=CompareRead,
)
async def compare_crops(
    field_id: int,
    payload: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate a chosen subset of crops and explain the differences between them.

    Not persisted. The scoring reuses the same engine as the ranked
    recommendations, so ``ranking`` matches the order the farmer just saw.
    """
    field = _owned_field(field_id, current_user, db)
    known = {
        crop.id
        for crop in db.query(Crop.id).filter(Crop.id.in_(payload.crop_ids)).all()
    }
    unknown = [cid for cid in payload.crop_ids if cid not in known]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown crop id(s): {', '.join(str(c) for c in unknown)}",
        )
    weather, weather_reason = await _fetch_weather(field)
    evaluation = engine.evaluate_field(db, field, weather, weather_reason)
    return comparison.build_comparison(evaluation, payload.crop_ids)


@router.get(
    "/fields/{field_id}/crops/recommendations",
    response_model=List[RecommendationBatchSummary],
)
async def list_recommendation_batches(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """History of past recommendation batches for a field, newest first."""
    field = _owned_field(field_id, current_user, db)
    rows = (
        db.query(CropRecommendation)
        .filter(
            CropRecommendation.field_id == field.id,
            CropRecommendation.user_id == field.user_id,
        )
        .order_by(CropRecommendation.created_at.desc(), CropRecommendation.id.desc())
        .all()
    )

    batches: list[RecommendationBatchSummary] = []
    grouped: dict[str, list[CropRecommendation]] = {}
    order: list[str] = []
    for row in rows:
        if row.batch_id not in grouped:
            grouped[row.batch_id] = []
            order.append(row.batch_id)
        grouped[row.batch_id].append(row)

    for batch_id in order:
        batch_rows = grouped[batch_id]
        counts = RecommendationCounts()
        top_crop = None
        top_score = -1.0
        newest = batch_rows[0]
        for row in batch_rows:
            if row.status == C.STATUS_SUITABLE:
                counts.suitable += 1
                if row.score is not None and row.score > top_score:
                    top_score = row.score
                    top_crop = row.result.get("display_name") if row.result else None
            elif row.status == C.STATUS_NEEDS_INFO:
                counts.needs_information += 1
            else:
                counts.not_recommended += 1
        batches.append(
            RecommendationBatchSummary(
                batch_id=batch_id,
                season=newest.season,
                engine_version=newest.engine_version,
                created_at=newest.created_at,
                counts=counts,
                top_crop=top_crop,
            )
        )
    return batches


@router.get(
    "/fields/{field_id}/crops/recommendations/batches/{batch_id}",
    response_model=List[RecommendationRead],
)
async def get_recommendation_batch(
    field_id: int,
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All persisted estimates from one past batch, so history can be re-read."""
    field = _owned_field(field_id, current_user, db)
    rows = (
        db.query(CropRecommendation)
        .filter(
            CropRecommendation.field_id == field.id,
            CropRecommendation.user_id == field.user_id,
            CropRecommendation.batch_id == batch_id,
        )
        .order_by(CropRecommendation.id)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation batch not found"
        )
    crop_ids = {row.crop_id for row in rows if row.crop_id is not None}
    crops = {
        crop.id: crop
        for crop in db.query(Crop).filter(Crop.id.in_(crop_ids)).all()
    }
    return [_recommendation_payload(row, crops.get(row.crop_id)) for row in rows]


@router.get(
    "/fields/{field_id}/crops/recommendations/{recommendation_id}",
    response_model=RecommendationRead,
)
async def get_recommendation(
    field_id: int,
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A single persisted estimate, with its full working and input snapshot."""
    field = _owned_field(field_id, current_user, db)
    record = _owned_recommendation(field, recommendation_id, db)
    crop = db.query(Crop).filter(Crop.id == record.crop_id).first() if record.crop_id else None
    return _recommendation_payload(record, crop)


__all__ = ["router"]
