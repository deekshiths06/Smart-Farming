"""Geometry helpers for field boundaries and area.

All calculations are approximate by design: they are derived from a
user-drawn boundary, never from a legal land survey.
"""

from __future__ import annotations

import math
from typing import Optional

# Mean Earth radius (metres), IUGG authalic mean radius.
EARTH_RADIUS_M = 6371008.8

SQM_PER_UNIT = {
    "acre": 4046.8564224,
    "hectare": 10000.0,
    "square_metre": 1.0,
    "bigha": None,  # Bigha size differs by state - never converted implicitly.
}
ACRES_PER_HECTARE = 2.4710538146717
HECTARES_PER_ACRE = 1.0 / ACRES_PER_HECTARE


def polygon_area_square_metres(ring_lonlat: list[list[float]]) -> float:
    """Approximate area of a lon/lat ring using the Chamberlain-Duquette formula.

    Coordinates are [longitude, latitude] in degrees (GeoJSON order).
    """
    if not ring_lonlat or len(ring_lonlat) < 4:
        return 0.0

    ring = [list(p[:2]) for p in ring_lonlat]
    if ring[0] != ring[-1]:
        ring.append(ring[0][:])

    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = math.radians(ring[i][0]), math.radians(ring[i][1])
        lon2, lat2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
        delta_lon = lon2 - lon1
        while delta_lon > math.pi:
            delta_lon -= 2 * math.pi
        while delta_lon < -math.pi:
            delta_lon += 2 * math.pi
        total += delta_lon * (2.0 + math.sin(lat1) + math.sin(lat2))

    return abs(total) * EARTH_RADIUS_M * EARTH_RADIUS_M / 2.0


def boundary_area_square_metres(boundary: dict) -> float:
    """Area of the outer ring of a GeoJSON Polygon (first ring)."""
    coordinates = boundary.get("coordinates") or []
    if not coordinates:
        return 0.0
    return polygon_area_square_metres(coordinates[0])


def convert_area(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert between area units. Returns None when conversion is not defined."""
    from_sqm = SQM_PER_UNIT.get(from_unit)
    to_sqm = SQM_PER_UNIT.get(to_unit)
    if from_sqm is None or to_sqm is None:
        return None
    return value * from_sqm / to_sqm


def area_summary(area: Optional[float], unit: Optional[str]) -> Optional[dict]:
    """Human-friendly breakdown of an area, when the unit is convertible."""
    if area is None or unit is None:
        return None
    acres = convert_area(area, unit, "acre")
    hectares = convert_area(area, unit, "hectare")
    if acres is None:
        return None
    return {
        "acres": round(acres, 3),
        "hectares": round(hectares, 4),
    }
