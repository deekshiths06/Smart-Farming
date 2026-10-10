"""Field CRUD.

Ownership rules:
- The authenticated user id always comes from the JWT (`get_current_user`).
- It is never accepted from the request body or query string.
- Every query filters on `user_id`, so another user's field is invisible and
  indistinguishable from a missing one (404 rather than 403).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.deps import get_db
from app.models.field import Field
from app.models.user import User
from app.schemas.field import FieldCreate, FieldRead, FieldUpdate
from app.services import geo, weather_service

router = APIRouter()


def _resolve_area(data: dict) -> dict:
    """Derive area consistently with the declared source.

    - calculated_boundary: area is recomputed from the boundary on the backend.
    - manual: the farmer's entered value is kept as-is (source stays manual).
    """
    boundary = data.get("boundary")
    area_source = data.get("area_source") or "not_provided"

    if boundary is not None and area_source == "calculated_boundary":
        square_metres = geo.boundary_area_square_metres(boundary)
        data["area"] = round(square_metres / geo.SQM_PER_UNIT["acre"], 4)
        data["area_unit"] = "acre"
    elif boundary is None and area_source == "calculated_boundary":
        # Cannot claim a calculated area without a boundary.
        data["boundary"] = None
        data["area"] = None
        data["area_source"] = "not_provided"
    elif boundary is None and area_source == "manual" and data.get("area") is None:
        data["area_source"] = "not_provided"
    return data


def _owned_field(field_id: int, user: User, db: Session) -> Field:
    field = (
        db.query(Field).filter(Field.id == field_id, Field.user_id == user.id).first()
    )
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.get("", response_model=List[FieldRead])
async def list_fields(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fields = (
        db.query(Field)
        .filter(Field.user_id == current_user.id)
        .order_by(Field.created_at.desc(), Field.id.desc())
        .all()
    )
    return fields


@router.post("", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
async def create_field(
    payload: FieldCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data = _resolve_area(data)
    field = Field(**data, user_id=current_user.id)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/{field_id}", response_model=FieldRead)
async def get_field(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _owned_field(field_id, current_user, db)


@router.put("/{field_id}", response_model=FieldRead)
async def update_field(
    field_id: int,
    payload: FieldUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    updates = payload.model_dump(exclude_unset=True)

    if updates.get("soil_status") is None:
        updates.pop("soil_status", None)

    # Merge with current state so area/boundary rules see the full picture.
    merged = {
        "boundary": field.boundary,
        "area": field.area,
        "area_unit": field.area_unit,
        "area_source": field.area_source,
    }
    merged.update(updates)
    updates = _resolve_area(merged)
    for key, value in updates.items():
        setattr(field, key, value)

    db.commit()
    db.refresh(field)
    return field


@router.get("/{field_id}/weather")
async def field_weather(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real weather for a field's coordinates (Open-Meteo).

    This verifies the coordinate-first weather architecture end to end. The
    weather dashboard itself is intentionally not surfaced in the UI yet.
    """
    field = _owned_field(field_id, current_user, db)
    if field.latitude is None or field.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This field has no confirmed coordinates yet",
        )
    try:
        snap = await weather_service.fetch_current_weather(field.latitude, field.longitude)
    except weather_service.WeatherServiceError as exc:
        return {"status": "unavailable", "message": exc.user_message, "weather": None}

    return {
        "status": "ok",
        "message": None,
        "weather": {
            "source": snap.source,
            "latitude": snap.latitude,
            "longitude": snap.longitude,
            "observed_at": snap.observed_at,
            "temperature_2m": snap.temperature_2m,
            "apparent_temperature": snap.apparent_temperature,
            "relative_humidity_2m": snap.relative_humidity_2m,
            "precipitation": snap.precipitation,
            "precipitation_probability": snap.precipitation_probability,
            "weather_code": snap.weather_code,
            "wind_speed_10m": snap.wind_speed_10m,
            "daily": snap.daily,
            "hourly": snap.hourly,
        },
    }


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    db.delete(field)
    db.commit()
    return None
