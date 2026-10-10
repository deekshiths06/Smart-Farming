"""Admin foundation.

Deliberately small: real database/system values only. No fake statistics, no
farmer private data, and no crop-rule management (that arrives later).
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.core.config import settings
from app.database.deps import get_db
from app.database.session import engine
from app.decision_engine import constants as engine_constants
from app.models.crop import Crop, CropRequirement, CropScoringConfig
from app.models.field import Field
from app.models.soil import SoilReferenceRange
from app.models.user import ROLE_ADMIN, ROLE_FARMER, User
from app.schemas.crop import (
    CropCreate,
    CropDetailRead,
    CropRequirementCreate,
    CropRequirementRead,
    CropRequirementUpdate,
    CropUpdate,
    ScoringConfigRead,
    ScoringConfigUpdate,
    validate_requirement
)
from app.schemas.soil import ReferenceRangeCreate, ReferenceRangeRead, ReferenceRangeUpdate
from app.services import location_service, weather_service

router = APIRouter()


@router.get("/stats")
async def admin_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)

    total_users = db.query(User).count()
    total_fields = db.query(Field).count()
    farmer_count = db.query(User).filter(User.role == ROLE_FARMER).count()
    admin_count = db.query(User).filter(User.role == ROLE_ADMIN).count()
    active_users = db.query(User).filter(User.is_active.is_(True)).count()
    new_users_week = db.query(User).filter(User.created_at >= week_ago).count()
    new_fields_week = db.query(Field).filter(Field.created_at >= week_ago).count()
    fields_with_location = db.query(Field).filter(Field.latitude.isnot(None)).count()
    soil_reported = db.query(Field).filter(Field.soil_status == "available").count()

    return {
        "application": {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
        },
        "database": {
            "engine": engine.dialect.name,
        },
        "counts": {
            "total_users": total_users,
            "total_fields": total_fields,
            "farmers": farmer_count,
            "admins": admin_count,
            "active_users": active_users,
            "fields_with_location": fields_with_location,
            "fields_with_verified_soil": soil_reported,
        },
        "recent_activity": {
            "new_users_last_7_days": new_users_week,
            "new_fields_last_7_days": new_fields_week,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/data-sources")
async def data_sources(admin: User = Depends(require_admin)):
    return {
        "sources": [
            {
                "id": "nominatim",
                "name": "OpenStreetMap Nominatim",
                "purpose": "Reverse geocoding of confirmed field coordinates",
                "endpoint": settings.NOMINATIM_BASE_URL,
                "status": "configured",
            },
            {
                "id": "open_meteo",
                "name": "Open-Meteo",
                "purpose": "Weather intelligence from field coordinates",
                "endpoint": settings.OPEN_METEO_BASE_URL,
                "status": "configured",
            },
            {
                "id": "soil_verified",
                "name": "Farmer soil reports",
                "purpose": "Verified laboratory / Soil Health Card values",
                "endpoint": None,
                "status": "implemented",
                "note": "PDF/JPEG/PNG reports stored per field; values are entered and "
                "confirmed by the farmer (no unverified OCR extraction)",
            },
            {
                "id": "soil_geospatial",
                "name": "Regional / geospatial soil datasets",
                "purpose": "Estimated soil information where legally available",
                "endpoint": None,
                "status": "not_implemented",
                "note": "Would be labelled as estimated, never as field-tested",
            },
            {
                "id": "market",
                "name": "Market intelligence",
                "purpose": "Price context for recommendations",
                "endpoint": None,
                "status": "not_implemented",
            },
            {
                "id": "crop_knowledge_base",
                "name": "Crop knowledge base",
                "purpose": "Crop rules consumed by the decision engine",
                "endpoint": None,
                "status": "implemented",
                "note": "Admin-managed crops and sourced agronomic requirements scored by "
                "the deterministic Crop Intelligence engine",
            },
        ]
    }


@router.post("/data-sources/check")
async def check_data_sources(admin: User = Depends(require_admin)):
    """Real reachability probes (connectivity only - never shown as farm data)."""
    nominatim, open_meteo = await asyncio.gather(
        location_service.check_service_reachable(),
        weather_service.check_service_reachable(),
    )
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": {"nominatim": nominatim, "open_meteo": open_meteo},
        "note": "Connectivity check only. No farm-level data is produced by this probe.",
    }


@router.get("/schema")
async def schema_overview(admin: User = Depends(require_admin)):
    """Real table/column inventory from the live database."""
    inspector = sa_inspect(engine)
    overview = {}
    for table in sorted(inspector.get_table_names()):
        if table == "alembic_version":
            continue
        overview[table] = sorted(column["name"] for column in inspector.get_columns(table))
    return {"tables": overview}


@router.get("/soil/reference-ranges", response_model=list[ReferenceRangeRead])
async def list_reference_ranges(
    parameter: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only view of agronomic reference bands (farmers see them via the
    soil assessment, never edit them)."""
    query = db.query(SoilReferenceRange).order_by(
        SoilReferenceRange.parameter,
        SoilReferenceRange.context_type,
        SoilReferenceRange.sequence,
    )
    if parameter:
        query = query.filter(SoilReferenceRange.parameter == parameter)
    return query.all()


@router.post(
    "/soil/reference-ranges",
    response_model=ReferenceRangeRead,
    status_code=201,
)
async def create_reference_range(
    payload: ReferenceRangeCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add a documented agronomic reference band. Only admins may do this."""
    record = SoilReferenceRange(**payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/soil/reference-ranges/{range_id}", response_model=ReferenceRangeRead)
async def update_reference_range(
    range_id: int,
    payload: ReferenceRangeUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Modify an existing reference band (bin it via is_active for soft off)."""
    record = db.query(SoilReferenceRange).filter(SoilReferenceRange.id == range_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Reference range not found")
    updates = payload.model_dump(exclude_unset=True)

    if updates.get("parameter") == "texture":
        raise HTTPException(status_code=422, detail="Texture is described, not ranged")

    if "min_value" in updates and "max_value" in updates:
        if updates["min_value"] is not None and updates["max_value"] is not None:
            if updates["min_value"] > updates["max_value"]:
                raise HTTPException(status_code=422, detail="min_value must be <= max_value")
    elif "min_value" in updates and updates["min_value"] is not None:
        if record.max_value is not None and updates["min_value"] > record.max_value:
            raise HTTPException(status_code=422, detail="min_value must be <= max_value")
    elif "max_value" in updates and updates["max_value"] is not None:
        if record.min_value is not None and record.min_value > updates["max_value"]:
            raise HTTPException(status_code=422, detail="min_value must be <= max_value")

    if updates.get("context_type", record.context_type) != "general":
        if not (updates.get("context_value") or record.context_value):
            raise HTTPException(
                status_code=422, detail="A non-general range needs a context_value"
            )

    for key, value in updates.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/soil/reference-ranges/{range_id}", status_code=204)
async def delete_reference_range(
    range_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    record = db.query(SoilReferenceRange).filter(SoilReferenceRange.id == range_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Reference range not found")
    db.delete(record)
    db.commit()
    return None
@router.get("/crops", response_model=List[CropDetailRead])
async def admin_list_crops(
    active_only: bool = False,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List crops. By default include inactive for editing."""
    query = db.query(Crop).order_by(Crop.display_name)
    if active_only:
        query = query.filter(Crop.is_active.is_(True))
    return query.all()


@router.post("/crops", response_model=CropDetailRead, status_code=201)
async def admin_create_crop(
    payload: CropCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(Crop).filter(Crop.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Crop name already exists")
    crop = Crop(**payload.model_dump())
    db.add(crop)
    db.commit()
    db.refresh(crop)
    return crop


@router.put("/crops/{crop_id}", response_model=CropDetailRead)
async def admin_update_crop(
    crop_id: int,
    payload: CropUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(crop, key, value)
    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/crops/{crop_id}", status_code=204)
async def admin_delete_crop(
    crop_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    db.delete(crop)
    db.commit()
    return None


@router.post("/crops/{crop_id}/requirements", response_model=CropRequirementRead, status_code=201)
async def admin_create_requirement(
    crop_id: int,
    payload: CropRequirementCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    existing = (
        db.query(CropRequirement)
        .filter(CropRequirement.crop_id == crop_id, CropRequirement.factor == payload.factor)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A requirement for '{payload.factor}' already exists for this crop",
        )
    req = CropRequirement(**payload.model_dump(), crop_id=crop_id)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.put("/requirements/{requirement_id}", response_model=CropRequirementRead)
async def admin_update_requirement(
    requirement_id: int,
    payload: CropRequirementUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    req = db.query(CropRequirement).filter(CropRequirement.id == requirement_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    updates = payload.model_dump(exclude_unset=True)
    if any(k in updates for k in ("factor", "min_value", "max_value", "allowed_values")):
        factor = updates.get("factor", req.factor)
        min_v = updates.get("min_value", req.min_value)
        max_v = updates.get("max_value", req.max_value)
        allowed = updates.get("allowed_values", req.allowed_values)
        try:
            validate_requirement(factor, min_v, max_v, allowed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    for key, value in updates.items():
        setattr(req, key, value)
    db.commit()
    db.refresh(req)
    return req


@router.delete("/requirements/{requirement_id}", status_code=204)
async def admin_delete_requirement(
    requirement_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    req = db.query(CropRequirement).filter(CropRequirement.id == requirement_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    db.delete(req)
    db.commit()
    return None


@router.get("/crop-scoring-config", response_model=ScoringConfigRead)
async def admin_get_scoring_config(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    row = (
        db.query(CropScoringConfig)
        .order_by(CropScoringConfig.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No scoring config found")
    return row


@router.put("/crop-scoring-config", response_model=ScoringConfigRead)
async def admin_update_scoring_config(
    payload: ScoringConfigUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = (
        db.query(CropScoringConfig)
        .order_by(CropScoringConfig.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No scoring config found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
