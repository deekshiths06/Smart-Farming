"""Soil context for the Crop Intelligence engine.

Wraps the existing Soil Intelligence data: the field's latest measurement and the
explainable nutrient assessment. The engine consumes the measured pH and texture
for scoring and the nutrient assessment as supporting context. A measurement that
is stale or (unexpectedly) dated in the future is surfaced with a note and
excluded from scoring rather than silently trusted.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.soil import SoilMeasurement
from app.services import soil_assessment
from app.services.soil_limits import NUMERIC_PARAMETERS


@dataclass
class SoilContext:
    has_measurement: bool = False
    tested_on: Optional[date] = None
    age_days: Optional[int] = None
    is_stale: bool = False
    is_future: bool = False

    ph: Optional[float] = None
    texture: Optional[str] = None
    values: dict = dataclass_field(default_factory=dict)
    nutrients: dict = dataclass_field(default_factory=dict)
    notes: list[str] = dataclass_field(default_factory=list)

    @property
    def scorable(self) -> bool:
        """True when the pH/texture may be used in scoring."""
        return self.has_measurement and not self.is_stale and not self.is_future


def _latest_measurement(db: Session, field: Field) -> Optional[SoilMeasurement]:
    return (
        db.query(SoilMeasurement)
        .filter(
            SoilMeasurement.field_id == field.id,
            SoilMeasurement.user_id == field.user_id,
        )
        .order_by(SoilMeasurement.tested_on.desc(), SoilMeasurement.id.desc())
        .first()
    )


def build_soil_context(
    db: Session, field: Field, stale_days: int, today: Optional[date] = None
) -> SoilContext:
    today = today or date.today()
    measurement = _latest_measurement(db, field)
    ctx = SoilContext()

    if measurement is None:
        ctx.notes.append(
            "No soil test has been recorded for this field, so pH and texture "
            "cannot be compared yet."
        )
        return ctx

    ctx.has_measurement = True
    ctx.tested_on = measurement.tested_on
    ctx.age_days = (today - measurement.tested_on).days
    ctx.ph = measurement.ph
    ctx.texture = measurement.texture

    values = {name: getattr(measurement, name) for name in NUMERIC_PARAMETERS + ["texture"]}
    values["source_kind"] = measurement.source_kind
    ctx.values = values

    if ctx.age_days is not None and ctx.age_days < 0:
        ctx.is_future = True
        ctx.notes.append(
            "The latest soil test is dated in the future, so it is ignored for "
            "scoring until the date is corrected."
        )
    elif ctx.age_days is not None and ctx.age_days > stale_days:
        ctx.is_stale = True
        ctx.notes.append(
            f"The latest soil test is {ctx.age_days} days old (older than "
            f"{stale_days} days), so pH and texture are not used for scoring. "
            "A fresh test would improve accuracy."
        )

    ctx.nutrients = soil_assessment.build_assessment(db, field, values)
    return ctx


__all__ = ["SoilContext", "build_soil_context"]
