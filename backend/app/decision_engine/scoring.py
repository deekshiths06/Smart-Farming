"""Deterministic scoring primitives for the Crop Intelligence engine.

Every function here is pure and side-effect free, so the scoring can be unit
tested directly and reasoned about exactly. No value is ever invented: when an
input is missing the function returns ``None`` and the caller marks that factor
as "needs input" rather than guessing.
"""

from __future__ import annotations

from typing import Optional

from app.decision_engine.constants import (
    FACTOR_FALLBACK_SPAN,
    RAIN_FED_HIGH_NEED_MULTIPLIER,
    SEASON_EXACT_SCORE,
    SEASON_MISMATCH_SCORE,
    TEXTURE_EXACT_SCORE,
    TEXTURE_GROUPS,
    TEXTURE_OTHER_GROUP_SCORE,
    TEXTURE_SAME_GROUP_SCORE,
    WATER_NEED_SCORE,
    WATER_PROVISION_SCORE,
    season_for_month,
)


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def range_score(
    value: Optional[float],
    min_value: Optional[float],
    max_value: Optional[float],
    factor: str,
) -> Optional[float]:
    """Score a measured value against a crop's preferred band (0-1).

    Inside the band -> 1.0. Outside, the score falls off linearly with distance
    measured in band-widths (or a documented fallback span for open bands), so a
    value just outside the band is only slightly penalised and a value far away
    approaches 0. Missing value -> ``None``.
    """
    if value is None:
        return None
    if min_value is None and max_value is None:
        return None

    if min_value is not None and max_value is not None:
        if min_value <= value <= max_value:
            return 1.0
        span = max(max_value - min_value, 1e-9)
        distance = (min_value - value) if value < min_value else (value - max_value)
        return clamp01(1.0 - distance / span)

    fallback = FACTOR_FALLBACK_SPAN.get(factor, 1.0)
    if min_value is not None:  # open upper bound
        if value >= min_value:
            return 1.0
        return clamp01(1.0 - (min_value - value) / max(fallback, 1e-9))
    # open lower bound
    assert max_value is not None
    if value <= max_value:
        return 1.0
    return clamp01(1.0 - (value - max_value) / max(fallback, 1e-9))


def water_score(
    availability: Optional[str],
    need_level: Optional[str],
    water_source: Optional[str],
) -> Optional[float]:
    """Compare farmer-reported water availability to a crop's documented need.

    Provision below need is partially credited in proportion to the shortfall.
    A rain-fed field with a high-water crop takes a documented additional
    penalty because there is no assured supply.
    """
    if availability is None or need_level is None:
        return None
    provision = WATER_PROVISION_SCORE.get(availability)
    need = WATER_NEED_SCORE.get(need_level)
    if provision is None or need is None:
        return None
    score = 1.0 if provision >= need else provision / need
    if water_source == "rain_fed" and need_level == "high":
        score *= RAIN_FED_HIGH_NEED_MULTIPLIER
    return clamp01(score)


def _texture_group(texture: str) -> Optional[str]:
    for group, classes in TEXTURE_GROUPS.items():
        if texture in classes:
            return group
    return None


def texture_score(field_texture: Optional[str], allowed: Optional[list[str]]) -> Optional[float]:
    """Transparent partial compatibility for soil texture.

    Exact class -> 1.0; same USDA textural group -> 0.5; otherwise -> 0.15. An
    unknown/"other" texture is treated as missing input, never guessed.
    """
    if not allowed or not field_texture or field_texture == "other":
        return None
    if field_texture in allowed:
        return TEXTURE_EXACT_SCORE
    field_group = _texture_group(field_texture)
    if field_group is not None and any(_texture_group(a) == field_group for a in allowed):
        return TEXTURE_SAME_GROUP_SCORE
    return TEXTURE_OTHER_GROUP_SCORE


def season_score(month: int, allowed: Optional[list[str]]) -> Optional[float]:
    """Exact season match scores 1.0, otherwise 0.0. No inputs -> ``None``."""
    if not allowed:
        return None
    current = season_for_month(month)
    return SEASON_EXACT_SCORE if current in allowed else SEASON_MISMATCH_SCORE


def region_score(field_state: Optional[str], allowed: Optional[list[str]]) -> Optional[float]:
    """A crop that names regions matches or does not; unknown field -> ``None``."""
    if not allowed:
        return None
    if not field_state:
        return None
    return 1.0 if field_state in allowed else 0.0


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def forecast_temperature_score(
    daily: list[dict],
    temp_min: Optional[float],
    temp_max: Optional[float],
    factor: str = "temperature",
) -> tuple[Optional[float], Optional[float]]:
    """Score the field's live temperature forecast against a crop's band.

    The representative value is the mean of each forecast day's mid-point
    ``(max + min) / 2`` — a transparent summary of the growing temperature the
    forecast implies for this exact location. Missing forecast or band ->
    ``(None, None)`` so the caller reports it as a gap, never a guess.
    """
    if temp_min is None and temp_max is None:
        return None, None
    means: list[float] = []
    for day in daily or []:
        high = _to_float(day.get("temperature_2m_max"))
        low = _to_float(day.get("temperature_2m_min"))
        if high is not None and low is not None:
            means.append((high + low) / 2.0)
        elif high is not None:
            means.append(high)
        elif low is not None:
            means.append(low)
    if not means:
        return None, None
    value = sum(means) / len(means)
    return range_score(value, temp_min, temp_max, factor), value


def forecast_rainfall_score(
    daily: list[dict],
    rainfall_min: Optional[float],
    rainfall_max: Optional[float],
    duration_min: Optional[float],
    duration_max: Optional[float],
    factor: str = "rainfall",
) -> tuple[Optional[float], Optional[float]]:
    """Score the field's forecast rainfall against a crop's seasonal band.

    A crop's documented rainfall band is *seasonal* (mm over the whole season),
    while live weather only offers a short forecast. Comparing them directly
    would be dishonest, so the band is pro-rated to the forecast window using
    the crop's own documented duration (``band * days / duration``). The
    forecast total is then scored against that window-equivalent band. Without a
    duration or a rainfall band the comparison cannot be made and the factor is
    reported as missing rather than invented.
    """
    precip = [p for p in (_to_float(day.get("precipitation_sum")) for day in daily or []) if p is not None]
    if not precip:
        return None, None
    if rainfall_min is None and rainfall_max is None:
        return None, None
    durations = [d for d in (duration_min, duration_max) if d is not None]
    if not durations:
        return None, None
    duration = sum(durations) / len(durations)
    if duration <= 0:
        return None, None
    days = len(precip)
    total = sum(precip)
    window_min = rainfall_min * days / duration if rainfall_min is not None else None
    window_max = rainfall_max * days / duration if rainfall_max is not None else None
    return range_score(total, window_min, window_max, factor), total


__all__ = [
    "clamp01",
    "range_score",
    "water_score",
    "texture_score",
    "season_score",
    "region_score",
    "forecast_temperature_score",
    "forecast_rainfall_score",
]
