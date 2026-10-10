"""Soil Intelligence API.

Ownership model follows the rest of ANNADATA: the authenticated user comes from
the JWT, never from request bodies, and every query filters on the field's
``user_id``. Any guessed id yields 404 - a stranger's record is
indistinguishable from a missing one.

Every numeric value is validated against ``app.services.soil_limits`` before it
reaches the database, uploads are validated by magic bytes + size in
``app.services.soil_storage``, and reports are only downloadable by their owner.
"""

from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.deps import get_db
from app.models.field import Field
from app.models.soil import (
    SOURCE_KIND_FARMER,
    SOURCE_KIND_REPORT,
    REPORT_STATUS_LINKED,
    REPORT_STATUS_UPLOADED,
    SoilMeasurement,
    SoilReport,
)
from app.models.user import User
from app.schemas.soil import (
    SoilMeasurementCreate,
    SoilMeasurementRead,
    SoilMeasurementUpdate,
    SoilProfileRead,
    SoilReportRead,
)
from app.services import soil_assessment, soil_storage
from app.services.soil_limits import (
    NUMERIC_PARAMETERS,
    PARAMETER_LABELS,
    PARAMETER_NAMES,
    PARAMETER_UNITS,
    PARAMETER_WHY,
    TEXTURE_LABELS,
)

router = APIRouter()


def _owned_field(field_id: int, user: User, db: Session) -> Field:
    field = (
        db.query(Field).filter(Field.id == field_id, Field.user_id == user.id).first()
    )
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return field


def _owned_measurement(field: Field, measurement_id: int, db: Session) -> SoilMeasurement:
    measurement = (
        db.query(SoilMeasurement)
        .filter(
            SoilMeasurement.id == measurement_id,
            SoilMeasurement.field_id == field.id,
            SoilMeasurement.user_id == field.user_id,
        )
        .first()
    )
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Soil measurement not found"
        )
    return measurement


def _owned_report(field: Field, report_id: int, db: Session) -> SoilReport:
    report = (
        db.query(SoilReport)
        .filter(
            SoilReport.id == report_id,
            SoilReport.field_id == field.id,
            SoilReport.user_id == field.user_id,
        )
        .first()
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil report not found")
    return report


def _validate_report_link(field: Field, report_id: Optional[int], db: Session) -> None:
    """A linked report must exist and belong to this field and user."""
    if report_id is None:
        return
    report = _owned_report(field, report_id, db)
    if report.field_id != field.id or report.user_id != field.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Soil report not found")


def _sync_field_soil_status(field: Field, db: Session) -> None:
    has_measurement = (
        db.query(SoilMeasurement)
        .filter(SoilMeasurement.field_id == field.id, SoilMeasurement.user_id == field.user_id)
        .first()
        is not None
    )
    has_report = (
        db.query(SoilReport)
        .filter(SoilReport.field_id == field.id, SoilReport.user_id == field.user_id)
        .first()
        is not None
    )
    field.soil_status = (
        "available" if has_measurement else ("pending" if has_report else "not_provided")
    )


def _measurement_values(measurement: SoilMeasurement) -> dict:
    values = {name: getattr(measurement, name) for name in NUMERIC_PARAMETERS + ["texture"]}
    values["source_kind"] = measurement.source_kind
    return values


def _build_profile(db: Session, field: Field) -> dict:
    measurements = (
        db.query(SoilMeasurement)
        .filter(SoilMeasurement.field_id == field.id, SoilMeasurement.user_id == field.user_id)
        .order_by(SoilMeasurement.tested_on.desc(), SoilMeasurement.id.desc())
        .all()
    )
    reports = (
        db.query(SoilReport)
        .filter(SoilReport.field_id == field.id, SoilReport.user_id == field.user_id)
        .order_by(SoilReport.created_at.desc(), SoilReport.id.desc())
        .all()
    )
    latest = measurements[0] if measurements else None

    measured = []
    missing = []
    if latest is not None:
        values = _measurement_values(latest)
        for name in PARAMETER_NAMES:
            if values.get(name) is not None:
                measured.append(name)
            else:
                missing.append(name)
    else:
        missing = list(PARAMETER_NAMES)

    assessment = soil_assessment.build_assessment(
        db, field, _measurement_values(latest) if latest else None
    )

    return {
        "field_id": field.id,
        "field_name": field.field_name,
        "has_measurements": latest is not None,
        "latest_measurement": latest,
        "history": measurements,
        "reports": reports,
        "completeness": {
            "measured_count": len(measured),
            "total_count": len(PARAMETER_NAMES),
            "percent": round(len(measured) / len(PARAMETER_NAMES) * 100),
            "missing": missing,
            "measured": measured,
        },
        "last_tested_on": latest.tested_on if latest else None,
        "last_tested_source": latest.test_source if latest else None,
        "assessment": assessment,
    }


@router.get("", response_model=SoilProfileRead)
async def get_soil_profile(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    return _build_profile(db, field)


@router.get("/measurements", response_model=List[SoilMeasurementRead])
async def list_measurements(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    return (
        db.query(SoilMeasurement)
        .filter(SoilMeasurement.field_id == field.id, SoilMeasurement.user_id == field.user_id)
        .order_by(SoilMeasurement.tested_on.desc(), SoilMeasurement.id.desc())
        .all()
    )


@router.post("/measurements", response_model=SoilMeasurementRead, status_code=status.HTTP_201_CREATED)
async def create_measurement(
    field_id: int,
    payload: SoilMeasurementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    _validate_report_link(field, payload.report_id, db)

    record = SoilMeasurement(**payload.model_dump(), field_id=field.id, user_id=field.user_id)
    if record.source_kind == SOURCE_KIND_REPORT:
        report = _owned_report(field, record.report_id, db)
        report.status = REPORT_STATUS_LINKED

    db.add(record)
    field.soil_status = "available"
    db.commit()
    db.refresh(record)
    return record


@router.put("/measurements/{measurement_id}", response_model=SoilMeasurementRead)
async def update_measurement(
    field_id: int,
    measurement_id: int,
    payload: SoilMeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    record = _owned_measurement(field, measurement_id, db)

    updates = payload.model_dump(exclude_unset=True)
    new_source_kind = updates.get("source_kind", record.source_kind)
    new_report_id = updates.get("report_id", record.report_id)
    if new_source_kind == SOURCE_KIND_REPORT and new_report_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A report-confirmed measurement must reference the uploaded report id",
        )
    if new_source_kind == SOURCE_KIND_FARMER:
        new_report_id = None
    _validate_report_link(field, new_report_id, db)

    # Unset a report link when reported values are now farmer-entered.
    if new_source_kind != SOURCE_KIND_REPORT:
        updates.pop("report_id", None)
        record.report_id = None

    for key, value in updates.items():
        setattr(record, key, value)

    if record.source_kind == SOURCE_KIND_REPORT and record.report_id is not None:
        report = _owned_report(field, record.report_id, db)
        report.status = REPORT_STATUS_LINKED

    db.commit()
    db.refresh(record)
    return record


@router.delete("/measurements/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_measurement(
    field_id: int,
    measurement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    record = _owned_measurement(field, measurement_id, db)
    db.delete(record)
    db.flush()
    _sync_field_soil_status(field, db)
    db.commit()
    return None


@router.get("/reports", response_model=List[SoilReportRead])
async def list_reports(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    return (
        db.query(SoilReport)
        .filter(SoilReport.field_id == field.id, SoilReport.user_id == field.user_id)
        .order_by(SoilReport.created_at.desc(), SoilReport.id.desc())
        .all()
    )


@router.post("/reports", response_model=SoilReportRead, status_code=status.HTTP_201_CREATED)
async def upload_soil_report(
    field_id: int,
    file: UploadFile = File(...),
    report_date: Optional[date] = Form(default=None),
    report_source: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The upload has no filename"
        )
    if report_date is not None and report_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The report date cannot be in the future",
        )

    try:
        stored = await soil_storage.store_report(file, filename, file.content_type or "")
    except soil_storage.SoilStorageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    record = SoilReport(
        field_id=field.id,
        user_id=field.user_id,
        original_filename=stored.original_filename,
        stored_filename=stored.stored_filename,
        content_type=stored.content_type,
        file_size_bytes=stored.file_size_bytes,
        report_date=report_date,
        report_source=report_source,
        status=REPORT_STATUS_UPLOADED,
    )
    db.add(record)
    # A report alone does not make soil "available" - values must still be
    # entered and confirmed.
    if field.soil_status == "not_provided":
        field.soil_status = "pending"
    db.commit()
    db.refresh(record)
    return record


@router.get("/reports/{report_id}/download")
async def download_soil_report(
    field_id: int,
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    field = _owned_field(field_id, current_user, db)
    report = _owned_report(field, report_id, db)
    path: Path = soil_storage.report_path(report.stored_filename)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The report file is missing on the server",
        )
    return FileResponse(
        str(path),
        media_type=report.content_type,
        filename=report.original_filename,
    )


# Module-level defaults so the upload form keeps the optional fields simple.
__all__ = ["router"]