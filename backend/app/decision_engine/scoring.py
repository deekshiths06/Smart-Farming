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


__all__ = [
    "clamp01",
    "range_score",
    "water_score",
    "texture_score",
    "season_score",
    "region_score",
]
