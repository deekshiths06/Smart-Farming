from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field as PydanticField, field_validator, model_validator

AreaUnit = Literal["acre", "hectare", "bigha", "square_metre"]
AreaSource = Literal["calculated_boundary", "manual", "not_provided"]
WaterSource = Literal[
    "rain_fed", "borewell", "open_well", "canal", "multiple", "other", "not_sure"
]
WaterAvailability = Literal["limited", "moderate", "good", "seasonal", "not_sure"]
SoilStatus = Literal["not_provided", "pending", "available"]

MAX_AREA = 10_000_000


class BoundaryPolygon(BaseModel):
    """GeoJSON Polygon in WGS84 (longitude, latitude) order."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]

    @field_validator("coordinates")
    @classmethod
    def validate_rings(cls, rings: list) -> list:
        if not rings:
            raise ValueError("A boundary must contain at least one ring")
        cleaned: list[list[list[float]]] = []
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("A boundary ring needs at least 4 positions")
            points: list[list[float]] = []
            for position in ring:
                if len(position) < 2:
                    raise ValueError("Each boundary position needs longitude and latitude")
                lng, lat = float(position[0]), float(position[1])
                if not -180 <= lng <= 180:
                    raise ValueError("Boundary longitude out of range (-180..180)")
                if not -90 <= lat <= 90:
                    raise ValueError("Boundary latitude out of range (-90..90)")
                points.append([lng, lat])
            if points[0][0] != points[-1][0] or points[0][1] != points[-1][1]:
                points.append(points[0][:])
            cleaned.append(points)
        return cleaned


class FieldBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    field_name: Optional[str] = PydanticField(default=None, min_length=1, max_length=120)
    latitude: Optional[float] = PydanticField(default=None, ge=-90, le=90)
    longitude: Optional[float] = PydanticField(default=None, ge=-180, le=180)
    location_accuracy: Optional[float] = PydanticField(default=None, ge=0)
    location_confirmed: Optional[bool] = None
    address: Optional[str] = PydanticField(default=None, max_length=512)
    locality: Optional[str] = PydanticField(default=None, max_length=120)
    sub_district: Optional[str] = PydanticField(default=None, max_length=120)
    district: Optional[str] = PydanticField(default=None, max_length=120)
    state: Optional[str] = PydanticField(default=None, max_length=120)
    country: Optional[str] = PydanticField(default=None, max_length=80)
    boundary: Optional[BoundaryPolygon] = None
    area: Optional[float] = PydanticField(default=None, ge=0, le=MAX_AREA)
    area_unit: Optional[AreaUnit] = "acre"
    area_source: Optional[AreaSource] = "not_provided"
    water_source: Optional[WaterSource] = None
    water_availability: Optional[WaterAvailability] = None
    soil_status: Optional[SoilStatus] = None

    @field_validator("field_name", "address", "locality", "sub_district", "district", "state", "country")
    @classmethod
    def strip_blank_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class FieldCreate(FieldBase):
    field_name: str = PydanticField(min_length=1, max_length=120)
    latitude: float = PydanticField(ge=-90, le=90)
    longitude: float = PydanticField(ge=-180, le=180)
    location_confirmed: bool = True

    @model_validator(mode="after")
    def require_confirmed_location(self) -> "FieldCreate":
        if not self.location_confirmed:
            raise ValueError("Location must be confirmed before saving a field")
        return self


class FieldUpdate(FieldBase):
    @model_validator(mode="after")
    def check_location_confirmation(self) -> "FieldUpdate":
        if "field_name" in self.model_fields_set and self.field_name is None:
            raise ValueError("Field name cannot be null; leave it unchanged instead")
        if "latitude" in self.model_fields_set and self.latitude is None:
            raise ValueError("Latitude cannot be null; omit it to keep the current value")
        if "longitude" in self.model_fields_set and self.longitude is None:
            raise ValueError("Longitude cannot be null; omit it to keep the current value")
        moves_location = "latitude" in self.model_fields_set or "longitude" in self.model_fields_set
        if moves_location and self.location_confirmed is not True:
            raise ValueError("Location must be confirmed before saving new coordinates")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self


class FieldRead(FieldBase):
    id: int
    user_id: int
    field_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
