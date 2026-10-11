"""Shared constants for the Crop Intelligence decision engine.

Everything here is a named, documented figure. Nothing is a hidden magic number:
the scoring weights and classification thresholds are seeded into the
``crop_scoring_config`` table (admin-editable) and these values are the safe
defaults used when the table is empty.
"""

from typing import Final

# Bumped whenever the scoring approach changes so persisted recommendations can
# be traced back to the rules that produced them.
ENGINE_VERSION: Final[str] = "1.3.0"

# --- Classification ---------------------------------------------------------

STATUS_SUITABLE: Final[str] = "suitable"
STATUS_NOT_RECOMMENDED: Final[str] = "not_recommended"
STATUS_NEEDS_INFO: Final[str] = "needs_information"

STATUS_LABELS: Final[dict[str, str]] = {
    STATUS_SUITABLE: "Potentially suitable",
    STATUS_NOT_RECOMMENDED: "Not recommended now",
    STATUS_NEEDS_INFO: "Needs more information",
}

# --- Match categories -------------------------------------------------------
# A plain-language grouping of the same evidence the status is built from. It
# never invents a new threshold: "Good match" is "suitable" with no unchecked
# requirements, "Possible option" is "suitable" but preliminary, "Needs more
# information" is the no-evidence verdict, and "Important limitations" is a
# genuine mismatch (an essential factor or season/region that does not fit).
MATCH_CATEGORY_GOOD: Final[str] = "good_match"
MATCH_CATEGORY_POSSIBLE: Final[str] = "possible_option"
MATCH_CATEGORY_NEEDS_INFO: Final[str] = "needs_more_information"
MATCH_CATEGORY_LIMITATIONS: Final[str] = "important_limitations"

MATCH_CATEGORY_ORDER: Final[tuple[str, ...]] = (
    MATCH_CATEGORY_GOOD,
    MATCH_CATEGORY_POSSIBLE,
    MATCH_CATEGORY_NEEDS_INFO,
    MATCH_CATEGORY_LIMITATIONS,
)

MATCH_CATEGORY_LABELS: Final[dict[str, str]] = {
    MATCH_CATEGORY_GOOD: "Good match",
    MATCH_CATEGORY_POSSIBLE: "Possible option",
    MATCH_CATEGORY_NEEDS_INFO: "Needs more information",
    MATCH_CATEGORY_LIMITATIONS: "Important limitations",
}

MATCH_CATEGORY_DESCRIPTIONS: Final[dict[str, str]] = {
    MATCH_CATEGORY_GOOD: (
        "Matches the crop's documented requirements on the recorded soil, water, "
        "season and this location's forecast, with every scored factor checked."
    ),
    MATCH_CATEGORY_POSSIBLE: (
        "Looks promising on the information recorded so far, but at least one "
        "documented requirement could not be checked yet - treat it as preliminary."
    ),
    MATCH_CATEGORY_NEEDS_INFO: (
        "There is not enough recorded information about this field to judge this "
        "crop yet. That is missing data, not a bad crop."
    ),
    MATCH_CATEGORY_LIMITATIONS: (
        "A recorded requirement does not match this field right now (for example an "
        "essential soil or water need, or the current season)."
    ),
}


def classify_match(status: str, preliminary: bool) -> str:
    """Map an evidence-based status to a plain-language match category."""
    if status == STATUS_NEEDS_INFO:
        return MATCH_CATEGORY_NEEDS_INFO
    if status == STATUS_NOT_RECOMMENDED:
        return MATCH_CATEGORY_LIMITATIONS
    return MATCH_CATEGORY_POSSIBLE if preliminary else MATCH_CATEGORY_GOOD


# --- Factors ----------------------------------------------------------------
# Factors the engine can evaluate. Numeric factors compare a measured value to a
# crop band; categorical factors compare a recorded value to an accepted set.

FACTOR_PH: Final[str] = "ph"
FACTOR_TEXTURE: Final[str] = "texture"
FACTOR_WATER: Final[str] = "water"
FACTOR_SEASON: Final[str] = "season"
FACTOR_REGION: Final[str] = "region"

# Live-weather-derived factors. Temperature and rainfall are compared against a
# crop's documented bands using the field's own coordinates via Open-Meteo, so
# the score genuinely reflects the field's location. They are scored softly:
# they adjust the weighted suitability, but only missing data (never a short
# forecast spell) is treated as a gap.
FACTOR_TEMPERATURE: Final[str] = "temperature"
FACTOR_RAINFALL: Final[str] = "rainfall"
# Crop duration stays context-only: it is used to pro-rate the seasonal rainfall
# band to the forecast window, but is never scored on its own.
FACTOR_DURATION: Final[str] = "duration"

SCORED_FACTORS: Final[tuple[str, ...]] = (
    FACTOR_PH,
    FACTOR_TEXTURE,
    FACTOR_WATER,
    FACTOR_SEASON,
    FACTOR_REGION,
    FACTOR_TEMPERATURE,
    FACTOR_RAINFALL,
)

CONTEXT_FACTORS: Final[tuple[str, ...]] = (FACTOR_DURATION,)

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
# Temperature and rainfall carry a moderate weight: they move the suitability
# estimate with the field's actual location/forecast without dominating the
# durable soil, water and season evidence.
DEFAULT_WEIGHTS: Final[dict[str, float]] = {
    FACTOR_PH: 1.0,
    FACTOR_TEXTURE: 1.0,
    FACTOR_WATER: 1.0,
    FACTOR_SEASON: 0.8,
    FACTOR_REGION: 0.6,
    FACTOR_TEMPERATURE: 0.5,
    FACTOR_RAINFALL: 0.5,
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
