"""Shared constants for the Crop Intelligence decision engine.

Everything here is a named, documented figure. Nothing is a hidden magic number:
the scoring weights and classification thresholds are seeded into the
``crop_scoring_config`` table (admin-editable) and these values are the safe
defaults used when the table is empty.
"""

from typing import Final

# Bumped whenever the scoring approach changes so persisted recommendations can
# be traced back to the rules that produced them.
ENGINE_VERSION: Final[str] = "1.1.0"

# --- Classification ---------------------------------------------------------

STATUS_SUITABLE: Final[str] = "suitable"
STATUS_NOT_RECOMMENDED: Final[str] = "not_recommended"
STATUS_NEEDS_INFO: Final[str] = "needs_information"

STATUS_LABELS: Final[dict[str, str]] = {
    STATUS_SUITABLE: "Potentially suitable",
    STATUS_NOT_RECOMMENDED: "Not recommended now",
    STATUS_NEEDS_INFO: "Needs more information",
}

# --- Factors ----------------------------------------------------------------
# Factors the engine can evaluate. Numeric factors compare a measured value to a
# crop band; categorical factors compare a recorded value to an accepted set.

FACTOR_PH: Final[str] = "ph"
FACTOR_TEXTURE: Final[str] = "texture"
FACTOR_WATER: Final[str] = "water"
FACTOR_SEASON: Final[str] = "season"
FACTOR_REGION: Final[str] = "region"

# Context-only factors: used for risk messaging, never folded into the score.
FACTOR_TEMPERATURE: Final[str] = "temperature"
FACTOR_RAINFALL: Final[str] = "rainfall"
FACTOR_DURATION: Final[str] = "duration"

SCORED_FACTORS: Final[tuple[str, ...]] = (
    FACTOR_PH,
    FACTOR_TEXTURE,
    FACTOR_WATER,
    FACTOR_SEASON,
    FACTOR_REGION,
)

CONTEXT_FACTORS: Final[tuple[str, ...]] = (
    FACTOR_TEMPERATURE,
    FACTOR_RAINFALL,
    FACTOR_DURATION,
)

ALL_FACTORS: Final[tuple[str, ...]] = SCORED_FACTORS + CONTEXT_FACTORS

FACTOR_LABELS: Final[dict[str, str]] = {
    FACTOR_PH: "Soil pH",
    FACTOR_TEXTURE: "Soil texture",
    FACTOR_WATER: "Water availability",
    FACTOR_SEASON: "Season",
    FACTOR_REGION: "Region",
    FACTOR_TEMPERATURE: "Temperature",
    FACTOR_RAINFALL: "Rainfall",
    FACTOR_DURATION: "Crop duration",
}

# Default scoring weights (admin-editable via CropScoringConfig).
DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    FACTOR_PH: 1.0,
    FACTOR_TEXTURE: 1.0,
    FACTOR_WATER: 1.0,
    FACTOR_SEASON: 0.8,
    FACTOR_REGION: 0.6,
}

# Factors the engine treats as deal-breakers when the recorded value misses the
# crop's band. Missing inputs never trigger this - they are reported as gaps.
DEFAULT_ESSENTIAL_FACTORS: Final[tuple[str, ...]] = (FACTOR_PH, FACTOR_WATER)

# Default classification thresholds.
DEFAULT_SUITABLE_THRESHOLD: Final[float] = 0.65
DEFAULT_MIN_COVERAGE: Final[float] = 0.5

# Soil older than this is treated as too old to score against (still shown).
DEFAULT_STALE_SOIL_DAYS: Final[int] = 1095  # ~3 years

# --- Numeric factor helpers -------------------------------------------------
# Fallback "span" used to turn a distance outside a crop band into a 0-1 score
# when a band has an open end (min or max is NULL). Chosen to be a sensible
# tolerance for each factor and documented, not hidden.
FACTOR_FALLBACK_SPAN: Final[dict[str, float]] = {
    FACTOR_PH: 1.5,
    FACTOR_TEMPERATURE: 5.0,
    FACTOR_RAINFALL: 150.0,
    FACTOR_DURATION: 20.0,
}

# --- Water ------------------------------------------------------------------
# Provision = how much water the field is judged to have.
WATER_PROVISION_SCORE: Final[dict[str, float]] = {
    "limited": 0.25,
    "seasonal": 0.5,
    "moderate": 0.75,
    "good": 1.0,
}

# Need = how much water the crop is documented to require.
WATER_NEED_SCORE: Final[dict[str, float]] = {
    "low": 0.3,
    "medium": 0.6,
    "high": 0.85,
}

# A rain-fed field judged to need high water is penalised for the missing
# assured supply. Documented, transparent multiplier.
RAIN_FED_HIGH_NEED_MULTIPLIER: Final[float] = 0.7

# --- Texture ----------------------------------------------------------------
# USDA textural groups (USDA-NRCS soil texture triangle), used only to give a
# transparent partial-compatibility credit when the field texture is not an
# exact match for the crop.
TEXTURE_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "coarse": ("sand", "loamy_sand", "sandy_loam"),
    "medium": ("loam", "silt_loam", "silt"),
    "fine": (
        "sandy_clay_loam",
        "clay_loam",
        "silty_clay_loam",
        "sandy_clay",
        "silty_clay",
        "clay",
    ),
}
TEXTURE_EXACT_SCORE: Final[float] = 1.0
TEXTURE_SAME_GROUP_SCORE: Final[float] = 0.5
TEXTURE_OTHER_GROUP_SCORE: Final[float] = 0.15

# --- Seasons ----------------------------------------------------------------
SEASONS: Final[tuple[str, ...]] = ("kharif", "rabi", "zaid")

SEASON_LABELS: Final[dict[str, str]] = {
    "kharif": "Kharif (monsoon)",
    "rabi": "Rabi (winter)",
    "zaid": "Zaid (summer)",
}

# Month -> season used to infer the current season from the reference date.
# Approximate, documented Indian cropping calendar.
_MONTH_SEASON: Final[dict[int, str]] = {
    1: "rabi",
    2: "rabi",
    3: "zaid",
    4: "zaid",
    5: "zaid",
    6: "kharif",
    7: "kharif",
    8: "kharif",
    9: "kharif",
    10: "kharif",
    11: "rabi",
    12: "rabi",
}

# A crop is either grown in a season or it is not: exact match scores 1.0,
# mismatch scores 0.0 (crops can list several accepted seasons).
SEASON_EXACT_SCORE: Final[float] = 1.0
SEASON_MISMATCH_SCORE: Final[float] = 0.0

REGION_MATCH_SCORE: Final[float] = 1.0
REGION_MISMATCH_SCORE: Final[float] = 0.0

# --- Water source labels (from the field profile) ---------------------------
WATER_SOURCE_LABELS: Final[dict[str, str]] = {
    "rain_fed": "Rain-fed",
    "borewell": "Borewell",
    "open_well": "Open well",
    "canal": "Canal",
    "multiple": "Multiple sources",
    "other": "Other",
    "not_sure": "Not sure",
}


def season_for_month(month: int) -> str:
    """Documented, approximate Indian season for a calendar month."""
    return _MONTH_SEASON.get(month, "kharif")


# --- Weather risk thresholds ------------------------------------------------
# All in the units Open-Meteo returns (mm of precipitation, degrees Celsius).
# Documented thresholds for "actionable weather context"; they are advisory.
RISK_HEAVY_RAIN_DAILY_MM: Final[float] = 50.0
RISK_WET_7D_MM: Final[float] = 150.0
RISK_DRY_7D_MM: Final[float] = 5.0

RISK_KIND_HEAVY_RAIN: Final[str] = "heavy_rain"
RISK_KIND_WET_SPELL: Final[str] = "wet_spell"
RISK_KIND_DRY_SPELL: Final[str] = "dry_spell"
RISK_KIND_HEAT: Final[str] = "heat"
RISK_KIND_COLD: Final[str] = "cold"

RISK_SEVERITY_HIGH: Final[str] = "high"
RISK_SEVERITY_MEDIUM: Final[str] = "medium"

WEATHER_SOURCE: Final[str] = "Open-Meteo"

# --- Data source statements -------------------------------------------------
CROP_KB_SOURCE_ID: Final[str] = "crop_knowledge_base"

# Shown with every set of estimates so the output is never mistaken for a
# guarantee, a yield forecast, or financial advice.
SUITABILITY_DISCLAIMER: Final[str] = (
    "These are suitability estimates based on the field's recorded soil, water "
    "and location data compared with documented crop requirements. They are "
    "guidance to support your decision - not a guarantee, yield forecast, price "
    "or profit estimate. Always confirm with local extension advice and your own "
    "experience."
)

__all__ = [name for name in dir() if not name.startswith("_")]
