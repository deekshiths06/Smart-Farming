"""Soil Intelligence request/response schemas.

Validation rules mirror ``app.services.soil_limits``:

- every numeric value is rejected when physically implausible,
- the date of the soil test cannot be in the future,
- an empty record (no parameters at all) is rejected so we never store blanks,
- ``report_confirmed`` entries must reference an owned report; plain
  ``farmer_entered`` entries must not.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field as PydanticField,
    field_validator,
    model_validator,
)

from app.services.soil_limits import (
    PARAMETER_LIMITS,
    PARAMETER_UNITS,
    TEXTURE_CLASSES,
    TEXTURE_LABELS,
)

SourceKind = Literal["farmer_entered", "report_confirmed"]
Texture = Literal[tuple(TEXTURE_CLASSES)]  # type: ignore


class _SoilValues(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    ec: Optional[float] = None
    organic_carbon: Optional[float] = None
    moisture: Optional[float] = None
    texture: Optional[Texture] = None

    @field_validator("ph", "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture")
    @classmethod
    def check_plausible(cls, value: Optional[float], info) -> Optional[float]:
        if value is None:
            return None
        parameter = info.field_name
        low, high, _ = PARAMETER_LIMITS[parameter]
        if not (low <= value <= high):
            unit = PARAMETER_UNITS[parameter]
            unit_text = f" {unit}" if unit else ""
            raise ValueError(
                f"{parameter} must be between {low} and {high}{unit_text} " f"(recorded value {value} is not physically plausible)"
            )
        return value

    def parameter_count(self) -> int:
        return sum(1 for name in PARAMETER_LIMITS if getattr(self, name, None) is not None) + (
            1 if self.texture is not None else 0
        )


class SoilMeasurementBase(_SoilValues):
    tested_on: date

    @field_validator("tested_on")
    @classmethod
    def not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("The soil test date cannot be in the future")
        if value.year < 1900:
            raise ValueError("The soil test date looks incorrect")
        return value

    @model_validator(mode="after")
    def require_at_least_one_parameter(self) -> "SoilMeasurementBase":
        if self.parameter_count() == 0:
            raise ValueError(
                "At least one soil parameter must be recorded (every value can stay missing)"
            )
        return self


class SoilMeasurementCreate(SoilMeasurementBase):
    test_source: Optional[str] = PydanticField(default=None, max_length=200)
    source_kind: SourceKind = "farmer_entered"
    report_id: Optional[int] = None

    @field_validator("test_source")
    @classmethod
    def strip_source(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def link_matches_source_kind(self) -> "SoilMeasurementCreate":
        if self.source_kind == "report_confirmed" and self.report_id is None:
            raise ValueError(
                "A report-confirmed measurement must reference the uploaded report id"
            )
        if self.source_kind == "farmer_entered" and self.report_id is not None:
            raise ValueError(
                "Farmer-entered measurements do not reference report ids; "
                "use source_kind='report_confirmed' to link a report"
            )
        return self


class SoilMeasurementUpdate(_SoilValues):
    tested_on: Optional[date] = None
    test_source: Optional[str] = PydanticField(default=None, max_length=200)
    source_kind: Optional[SourceKind] = None
    report_id: Optional[int] = None

    @field_validator("tested_on")
    @classmethod
    def not_in_future(cls, value: Optional[date]) -> Optional[date]:
        if value is None:
            return None
        if value > date.today():
            raise ValueError("The soil test date cannot be in the future")
        if value.year < 1900:
            raise ValueError("The soil test date looks incorrect")
        return value

    @field_validator("test_source")
    @classmethod
    def strip_source(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def link_matches_source_kind(self) -> "SoilMeasurementUpdate":
        if self.source_kind == "report_confirmed" and self.report_id is None:
            raise ValueError(
                "A report-confirmed measurement must reference the uploaded report id"
            )
        if self.source_kind == "farmer_entered" and self.report_id is not None:
            raise ValueError(
                "Farmer-entered measurements do not reference report ids"
            )
        return self


class SoilMeasurementRead(SoilMeasurementBase):
    id: int
    field_id: int
    user_id: int
    test_source: Optional[str] = None
    source_kind: str
    report_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SoilReportCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    report_date: Optional[date] = None
    report_source: Optional[str] = None

    @field_validator("report_date")
    @classmethod
    def not_in_future(cls, value: Optional[date]) -> Optional[date]:
        if value is None:
            return None
        today = date.today()
        if value > today:
            raise ValueError("The report date cannot be in the future")
        return value


class SoilReportRead(BaseModel):
    id: int
    field_id: int
    user_id: int
    original_filename: str
    content_type: str
    file_size_bytes: int
    report_date: Optional[date] = None
    report_source: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParamAssessmentRead(BaseModel):
    parameter: str
    label: str
    unit: str
    value: Optional[float] = None
    texture_label: Optional[str] = None
    measured: bool
    # below | within | above | no_range | missing | info
    status: str
    range_label: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    explanation: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    applied_context: Optional[str] = None
    source_kind: Optional[str] = None
    requires_lab: bool = False

    @classmethod
    def texture_labelled(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return TEXTURE_LABELS.get(value, value)


class CompletenessRead(BaseModel):
    measured_count: int
    total_count: int
    percent: int
    missing: list[str]
    measured: list[str]


class SoilProfileRead(BaseModel):
    field_id: int
    field_name: str
    has_measurements: bool
    latest_measurement: Optional[SoilMeasurementRead] = None
    history: list[SoilMeasurementRead]
    reports: list[SoilReportRead]
    completeness: CompletenessRead
    last_tested_on: Optional[date] = None
    last_tested_source: Optional[str] = None
    assessment: dict[str, ParamAssessmentRead]


class ReferenceRangeBase(BaseModel):
    parameter: Literal[
        "ph", "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture", "texture"
    ]
    context_type: Literal["general", "region", "soil_class", "crop"] = "general"
    context_value: Optional[str] = PydanticField(default=None, max_length=60)
    label: str = PydanticField(min_length=1, max_length=120)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = PydanticField(default=None, max_length=20)
    outcome: Literal["below", "within", "above"] = "within"
    explanation: Optional[str] = PydanticField(default=None, max_length=500)
    source: str = PydanticField(min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    sequence: int = 0
    is_active: bool = True

    @model_validator(mode="after")
    def range_makes_sense(self) -> "ReferenceRangeBase":
        lo, hi = self.min_value, self.max_value
        if lo is not None and hi is not None and lo > hi:
            raise ValueError("min_value must be <= max_value")
        if self.parameter == "texture":
            raise ValueError("Texture is described, not ranged; use soil-texture guidance instead")
        if self.context_type != "general" and not self.context_value:
            raise ValueError("A non-general range needs a context_value (e.g. region, soil class or crop)")
        return self

    @field_validator("context_value", "label", "unit", "explanation", "source", "source_url")
    @classmethod
    def strip_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReferenceRangeCreate(ReferenceRangeBase):
    pass


class ReferenceRangeUpdate(BaseModel):
    """Partial update: only supplied fields change."""

    model_config = ConfigDict(extra="ignore")

    parameter: Optional[Literal[
        "ph", "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture", "texture"
    ]] = None
    context_type: Optional[Literal["general", "region", "soil_class", "crop"]] = None
    context_value: Optional[str] = PydanticField(default=None, max_length=60)
    label: Optional[str] = PydanticField(default=None, min_length=1, max_length=120)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = PydanticField(default=None, max_length=20)
    outcome: Optional[Literal["below", "within", "above"]] = None
    explanation: Optional[str] = PydanticField(default=None, max_length=500)
    source: Optional[str] = PydanticField(default=None, min_length=1, max_length=200)
    source_url: Optional[str] = PydanticField(default=None, max_length=300)
    sequence: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("context_value", "label", "unit", "explanation", "source", "source_url")
    @classmethod
    def strip_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReferenceRangeRead(ReferenceRangeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)