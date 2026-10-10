"""Soil parameter metadata and physically-documented validation limits.

Numeric parameters are always stored in ONE canonical unit (shown to the
farmer on every input and card). The limits below are "physically or
scientifically plausible" bounds - generous enough never to reject a real
laboratory value, tight enough to reject typos and unit confusion.

These are living, documented figures. Sources:

- pH scale 0-14: USDA-NRCS. Practical arable soils sit ~4.5-9.5.
- Available N/P/K (kg/ha) ratings: ICAR - Soil Health Card ratings
  (Muhr et al. 1959 classification adopted by the Indian Soil Health Card
  scheme; www.soilhealth.dac.gov.in). Typical values N<600, P<120, K<600.
- EC (dS/m): FAO Irrigation & Drainage Paper 29 salinity classes.
- Organic carbon (%): single-factor medium/low thresholds used by ICAR.
- Moisture (%): a percentage; 0-100 is the physical envelope. Interpretation
  depends on method (gravimetric/volumetric) and texture.
"""

from typing import Optional

# Parameter name -> (display label, unit string)
PARAMETER_LABELS: dict[str, str] = {
    "ph": "Soil pH",
    "nitrogen": "Available nitrogen (N)",
    "phosphorus": "Available phosphorus (P)",
    "potassium": "Available potassium (K)",
    "ec": "Electrical conductivity",
    "organic_carbon": "Organic carbon",
    "moisture": "Soil moisture",
    "texture": "Soil texture",
}

PARAMETER_UNITS: dict[str, str] = {
    "ph": "",
    "nitrogen": "kg/ha",
    "phosphorus": "kg/ha",
    "potassium": "kg/ha",
    "ec": "dS/m",
    "organic_carbon": "%",
    "moisture": "%",
    "texture": "",
}

# Order used for completeness reporting and card grids.
PARAMETER_NAMES: list[str] = [
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "ec",
    "organic_carbon",
    "moisture",
    "texture",
]

# Numeric parameters only.
NUMERIC_PARAMETERS: list[str] = [name for name in PARAMETER_NAMES if name != "texture"]

# Parameters whose value can only be established by a laboratory analysis
# (e.g. a Soil Health Card). pH, moisture and texture can be measured or
# estimated in the field; the rest need a laboratory test.
LAB_PARAMETERS: frozenset[str] = frozenset(
    {"nitrogen", "phosphorus", "potassium", "ec", "organic_carbon"}
)

# parameter -> (min, max, note). Open values beyond the max are implausible.
PARAMETER_LIMITS: dict[str, tuple[float, float, str]] = {
    "ph": (0.0, 14.0, "The pH scale runs 0-14 (USDA-NRCS). Values outside it are physically impossible."),
    "nitrogen": (
        0.0,
        2000.0,
        "Available nitrogen reported in kg/ha (Soil Health Card, ICAR). Values above ~600 are "
        "exceptional for Indian soils.",
    ),
    "phosphorus": (
        0.0,
        500.0,
        "Available phosphorus reported in kg/ha (Soil Health Card, ICAR). Values above ~120 are "
        "exceptional.",
    ),
    "potassium": (
        0.0,
        2000.0,
        "Available potassium reported in kg/ha (Soil Health Card, ICAR). Values above ~600 are "
        "unusual.",
    ),
    "ec": (
        0.0,
        40.0,
        "Electrical conductivity in dS/m (FAO/IUSS). Even strongly saline soils rarely exceed 25.",
    ),
    "organic_carbon": (
        0.0,
        15.0,
        "Organic carbon in %. Mineral soils are normally below 5%; peat soils are the "
        "documented exception.",
    ),
    "moisture": (
        0.0,
        100.0,
        "Moisture as a percentage. The physical envelope is 0-100%.",
    ),
}

# USDA 12 basic texture classes (USDA-NRCS Soil Texture Triangle).
TEXTURE_CLASSES: list[str] = [
    "sand",
    "loamy_sand",
    "sandy_loam",
    "loam",
    "silt_loam",
    "silt",
    "sandy_clay_loam",
    "clay_loam",
    "silty_clay_loam",
    "sandy_clay",
    "silty_clay",
    "clay",
    "other",
]

TEXTURE_LABELS: dict[str, str] = {
    "sand": "Sandy",
    "loamy_sand": "Loamy sand",
    "sandy_loam": "Sandy loam",
    "loam": "Loam",
    "silt_loam": "Silt loam",
    "silt": "Silty",
    "sandy_clay_loam": "Sandy clay loam",
    "clay_loam": "Clay loam",
    "silty_clay_loam": "Silty clay loam",
    "sandy_clay": "Sandy clay",
    "silty_clay": "Silty clay",
    "clay": "Clayey",
    "other": "Other / unknown",
}

# Descriptive, texture-only guidance (not a numeric band). Source: USDA-NRCS
# soil texture guidance.
TEXTURE_INFO: dict[str, dict[str, str]] = {
    "sand": {
        "label": "Sandy",
        "description": "Free-draining, low water and nutrient holding. Dries out fast; needs "
        "frequent irrigation and careful fertiliser splitting.",
    },
    "loamy_sand": {
        "label": "Loamy sand",
        "description": "Mostly sand with some silt and clay. Drains well but holds little water.",
    },
    "sandy_loam": {
        "label": "Sandy loam",
        "description": "A comfortably worked soil: good drainage with moderate water/nutrient "
        "holding - a common cropping soil.",
    },
    "loam": {
        "label": "Loam",
        "description": "A balanced mix of sand, silt and clay: good structure, moisture and "
        "nutrient holding. Widely considered the best general cropping soil.",
    },
    "silt_loam": {
        "label": "Silt loam",
        "description": "Fine, fertile and moisture-retentive but can crust and erode.",
    },
    "silt": {
        "label": "Silty",
        "description": "Very fine particles; holds moisture well but compacts and crusts easily.",
    },
    "sandy_clay_loam": {
        "label": "Sandy clay loam",
        "description": "Fair drainage with improved nutrient holding over sandy types.",
    },
    "clay_loam": {
        "label": "Clay loam",
        "description": "Good nutrient and moisture holding with acceptable drainage when managed.",
    },
    "silty_clay_loam": {
        "label": "Silty clay loam",
        "description": "Moisture-retentive and fertile but slow to drain.",
    },
    "sandy_clay": {
        "label": "Sandy clay",
        "description": "Sticky when wet and hard when dry; drains slowly.",
    },
    "silty_clay": {
        "label": "Silty clay",
        "description": "Very tight texture; high moisture holding, poor aeration unless managed.",
    },
    "clay": {
        "label": "Clayey",
        "description": "Holds water and nutrients well but drains slowly and hardens when dry. "
        "Needs careful tillage timing.",
    },
    "other": {
        "label": "Other / unknown",
        "description": "Not one of the standard USDA classes. Texture-specific guidance is not "
        "applied until a standard class is recorded.",
    },
}

# Description of why each parameter matters (shown in cards and the
# missing-measurements section).
PARAMETER_WHY: dict[str, str] = {
    "ph": "pH controls nutrient availability and microbial activity. Most crops grow best near "
    "neutral (6.5-7.5); very acid or alkaline soils lock up nutrients.",
    "nitrogen": "Nitrogen drives vegetative growth and is usually the first nutrient to limit "
    "yield. Low available N means the crop may respond to N fertiliser.",
    "phosphorus": "Phosphorus is critical for root growth, flowering and grain fill. Many Indian "
    "soils are low in available P.",
    "potassium": "Potassium supports water balance, stalk strength and disease resistance. "
    "Deficiency is common in light-textured soils.",
    "ec": "EC measures soluble salts. High salinity restricts water uptake and hurts "
    "germination and yield.",
    "organic_carbon": "Organic carbon is a proxy for soil organic matter and general soil "
    "health: structure, water holding and nutrient cycling.",
    "moisture": "Moisture at sampling helps interpret other values (e.g. EC drifts with "
    "moisture). Only meaningful when actually measured.",
    "texture": "Texture governs drainage, water holding and nutrient retention, and changes "
    "which reference ranges apply.",
}


def is_numeric(parameter: str) -> bool:
    return parameter in NUMERIC_PARAMETERS


def limits_for(parameter: str) -> Optional[tuple[float, float, str]]:
    return PARAMETER_LIMITS.get(parameter)