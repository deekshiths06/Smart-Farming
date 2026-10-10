"""Weather risk context for the Crop Intelligence engine.

Turns a live :class:`~app.services.weather_service.WeatherSnapshot` into
transparent, advisory risk notes. These are *context only* - they never change
the suitability score. They describe what the forecast implies for the coming
days (heavy rain, a wet spell, a dry spell, heat and cold relative to a crop's
documented temperature band), each with its basis and the exact values used.

When weather is unavailable the engine still produces a suitability estimate from
field + soil data; this module simply reports that weather context is missing.
"""

from __future__ import annotations

from typing import Optional

from app.decision_engine.constants import (
    RISK_DRY_7D_MM,
    RISK_HEAVY_RAIN_DAILY_MM,
    RISK_KIND_COLD,
    RISK_KIND_DRY_SPELL,
    RISK_KIND_HEAVY_RAIN,
    RISK_KIND_HEAT,
    RISK_KIND_WET_SPELL,
    RISK_SEVERITY_HIGH,
    RISK_SEVERITY_MEDIUM,
    RISK_WET_7D_MM,
    WEATHER_SOURCE,
)
from app.services.weather_service import WeatherSnapshot


def _num(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize(snapshot: Optional[WeatherSnapshot], reason: Optional[str] = None) -> dict:
    """Compact weather summary stored in the input snapshot."""
    if snapshot is None:
        return {
            "available": False,
            "source": WEATHER_SOURCE,
            "observed_at": None,
            "reason": reason or "Weather data was not available for this field.",
            "daily": [],
        }
    daily = []
    for day in snapshot.daily[:7]:
        daily.append(
            {
                "time": day.get("time"),
                "precipitation_sum": _num(day.get("precipitation_sum")),
                "temperature_2m_max": _num(day.get("temperature_2m_max")),
                "temperature_2m_min": _num(day.get("temperature_2m_min")),
            }
        )
    return {
        "available": True,
        "source": snapshot.source,
        "observed_at": snapshot.observed_at,
        "reason": None,
        "daily": daily,
    }


def _daily_sum(snapshot: WeatherSnapshot, key: str, limit: int = 7) -> Optional[float]:
    values = [_num(day.get(key)) for day in snapshot.daily[:limit]]
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present)


def global_risks(snapshot: Optional[WeatherSnapshot]) -> list[dict]:
    """Rainfall risks that apply regardless of the crop."""
    if snapshot is None or not snapshot.daily:
        return []
    risks: list[dict] = []

    for day in snapshot.daily[:7]:
        precip = _num(day.get("precipitation_sum"))
        if precip is not None and precip >= RISK_HEAVY_RAIN_DAILY_MM:
            risks.append(
                {
                    "kind": RISK_KIND_HEAVY_RAIN,
                    "severity": RISK_SEVERITY_HIGH if precip >= 100 else RISK_SEVERITY_MEDIUM,
                    "title": "Heavy rain expected",
                    "detail": (
                        f"{precip:.0f} mm of rain is forecast for {day.get('time')}. "
                        "Expect waterlogging in low spots and possible sowing/field-work delays."
                    ),
                    "basis": f"Daily precipitation forecast ≥ {RISK_HEAVY_RAIN_DAILY_MM:.0f} mm",
                    "period": day.get("time"),
                    "value": precip,
                    "unit": "mm",
                    "source": snapshot.source,
                }
            )

    week_precip = _daily_sum(snapshot, "precipitation_sum")
    if week_precip is not None:
        if week_precip >= RISK_WET_7D_MM:
            risks.append(
                {
                    "kind": RISK_KIND_WET_SPELL,
                    "severity": RISK_SEVERITY_MEDIUM,
                    "title": "Wet spell ahead",
                    "detail": (
                        f"About {week_precip:.0f} mm of rain is forecast over the next 7 days. "
                        "Good for rain-fed sowing, but watch drainage and delayed operations."
                    ),
                    "basis": f"7-day precipitation total ≥ {RISK_WET_7D_MM:.0f} mm",
                    "period": "next 7 days",
                    "value": week_precip,
                    "unit": "mm",
                    "source": snapshot.source,
                }
            )
        elif week_precip <= RISK_DRY_7D_MM:
            risks.append(
                {
                    "kind": RISK_KIND_DRY_SPELL,
                    "severity": RISK_SEVERITY_MEDIUM,
                    "title": "Dry spell ahead",
                    "detail": (
                        f"Only about {week_precip:.0f} mm of rain is forecast over the next 7 days. "
                        "Rain-fed crops may need irrigation; plan water accordingly."
                    ),
                    "basis": f"7-day precipitation total ≤ {RISK_DRY_7D_MM:.0f} mm",
                    "period": "next 7 days",
                    "value": week_precip,
                    "unit": "mm",
                    "source": snapshot.source,
                }
            )
    return risks


def temperature_risks(
    snapshot: Optional[WeatherSnapshot],
    temp_min: Optional[float],
    temp_max: Optional[float],
    crop_name: str,
) -> list[dict]:
    """Heat/cold notes relative to a crop's documented temperature band."""
    if snapshot is None or not snapshot.daily:
        return []
    risks: list[dict] = []

    for day in snapshot.daily[:7]:
        day_max = _num(day.get("temperature_2m_max"))
        day_min = _num(day.get("temperature_2m_min"))
        if temp_max is not None and day_max is not None and day_max >= temp_max:
            risks.append(
                {
                    "kind": RISK_KIND_HEAT,
                    "severity": RISK_SEVERITY_MEDIUM,
                    "title": f"Heat above {crop_name}'s range",
                    "detail": (
                        f"Forecast high of {day_max:.0f}°C on {day.get('time')} is at or above "
                        f"{crop_name}'s indicative upper limit ({temp_max:.0f}°C). Heat can stress "
                        "the crop, especially around flowering."
                    ),
                    "basis": f"Forecast daily max ≥ crop upper temperature {temp_max:.0f}°C",
                    "period": day.get("time"),
                    "value": day_max,
                    "unit": "°C",
                    "source": snapshot.source,
                }
            )
        if temp_min is not None and day_min is not None and day_min <= temp_min:
            risks.append(
                {
                    "kind": RISK_KIND_COLD,
                    "severity": RISK_SEVERITY_MEDIUM,
                    "title": f"Cold below {crop_name}'s range",
                    "detail": (
                        f"Forecast low of {day_min:.0f}°C on {day.get('time')} is at or below "
                        f"{crop_name}'s indicative lower limit ({temp_min:.0f}°C). Cold can slow "
                        "germination and early growth."
                    ),
                    "basis": f"Forecast daily min ≤ crop lower temperature {temp_min:.0f}°C",
                    "period": day.get("time"),
                    "value": day_min,
                    "unit": "°C",
                    "source": snapshot.source,
                }
            )
    return risks


__all__ = ["summarize", "global_risks", "temperature_risks"]
