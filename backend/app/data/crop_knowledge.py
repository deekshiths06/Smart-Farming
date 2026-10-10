"""Crop knowledge base seed data.

Pure data (no database dependencies) so it can be consumed by both the Alembic
migration (0004) and the application/tests.

IMPORTANT — honesty rules followed here:

- Every crop and every requirement carries a named ``source`` (and, where one
  exists, a ``source_url``) plus a ``date_reviewed``.
- Ranges are *indicative agronomic bands* drawn from those named sources, not
  precise prescriptions. They exist to compare a field's measured context to a
  crop's documented preference. The application labels its output
  "suitability estimate" and never presents these as guarantees.
- No yield, price, profit or pest/disease claims are encoded anywhere.

To add a crop or adjust a band, edit this file (admin API changes persist in the
database but are overwritten on a fresh migration, so the canonical list lives
here).
"""

from typing import Final

DATE_REVIEWED: Final[str] = "2026-10-10"

SOURCES: Final[dict[str, dict[str, str]]] = {
    "irri": {
        "name": "IRRI Rice Knowledge Bank",
        "url": "http://www.knowledgebank.irri.org",
    },
    "iimr": {
        "name": "ICAR - Indian Institute of Maize Research (IIMR)",
        "url": "https://iimr.icar.gov.in",
    },
    "iiwbr": {
        "name": "ICAR - Indian Institute of Wheat & Barley Research (IIWBR)",
        "url": "https://iiwbr.icar.gov.in",
    },
    "icrisat": {
        "name": "ICRISAT crop guides (sorghum, pearl millet, groundnut, chickpea, pigeonpea)",
        "url": "https://www.icrisat.org",
    },
    "uas": {
        "name": "University of Agricultural Sciences (Bengaluru) / All India Coordinated Research Project on Small Millets",
        "url": "https://uasbangalore.edu.in",
    },
    "iipr": {
        "name": "ICAR - Indian Institute of Pulses Research (IIPR)",
        "url": "https://iipr.icar.gov.in",
    },
    "cicr": {
        "name": "ICAR - Central Institute for Cotton Research (CICR)",
        "url": "https://cicr.org.in",
    },
    "tnau": {
        "name": "TNAU Agritech Portal crop production guide",
        "url": "https://agritech.tnau.ac.in",
    },
    "fao": {
        "name": "FAO crop water & land requirements (indicative)",
        "url": "https://www.fao.org",
    },
}

_TEMP_NOTE = "Indicative growing temperature band for the crop."
_RAIN_NOTE = "Indicative seasonal rainfall band; consult local rainfall records."
_DURATION_NOTE = "Typical crop duration from sowing to harvest."


def _req(
    factor: str,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
    values: list[str] | None = None,
    is_essential: bool = False,
    explanation: str = "",
    sequence: int = 0,
    source: str | None = None,
) -> dict:
    return {
        "factor": factor,
        "min_value": min_value,
        "max_value": max_value,
        "values": values,
        "is_essential": is_essential,
        "explanation": explanation,
        "sequence": sequence,
        "source": source,
    }


def _crop(
    name: str,
    display_name: str,
    category: str,
    description: str,
    source_key: str,
    requirements: list[dict],
) -> dict:
    source = SOURCES[source_key]
    # Inherit the crop's source on any requirement that did not name one.
    for r in requirements:
        if not r.get("source"):
            r["source"] = source["name"]
        r["source_url"] = r.get("source_url") or source["url"]
    return {
        "name": name,
        "display_name": display_name,
        "category": category,
        "description": description,
        "source": source["name"],
        "source_url": source["url"],
        "date_reviewed": DATE_REVIEWED,
        "requirements": requirements,
    }


CROPS: Final[list[dict]] = [
    _crop(
        "rice",
        "Rice (paddy)",
        "cereal",
        "Staple cereal grown mainly in the kharif season under assured water. "
        "Best suited to heavier soils that hold standing water.",
        "irri",
        [
            _req("ph", min_value=5.5, max_value=6.5, is_essential=True,
                 explanation="IRRI reports best rice growth in this pH band; tolerant "
                 "varieties can perform outside it.", sequence=0),
            _req("texture", values=["clay", "silty_clay", "clay_loam", "silty_clay_loam"],
                 explanation="Puddled lowland rice favours soils that retain water.", sequence=0),
            _req("water", values=["high"], is_essential=True,
                 explanation="Rice needs an assured water supply; field is assessed on "
                 "farmer-reported availability.", sequence=0),
            _req("season", values=["kharif"], explanation="Main-season (kharif) crop.", sequence=0),
            _req("temperature", min_value=20, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=1000, max_value=2000, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=100, max_value=150, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "maize",
        "Maize",
        "cereal",
        "Versatile cereal for grain and fodder, grown in kharif and rabi where "
        "temperatures are moderate and soils drain well.",
        "iimr",
        [
            _req("ph", min_value=5.5, max_value=7.0, is_essential=True,
                 explanation="Maize grows well in this pH band.", sequence=0),
            _req("texture", values=["loam", "sandy_loam", "silt_loam", "clay_loam"],
                 explanation="Well-drained, medium-textured soils suit maize.", sequence=0),
            _req("water", values=["medium"], is_essential=True,
                 explanation="Maize needs moderate, well-distributed water.", sequence=0),
            _req("season", values=["kharif", "rabi"], explanation="Grown in kharif and rabi.", sequence=0),
            _req("temperature", min_value=18, max_value=32, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=500, max_value=800, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=85, max_value=130, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "wheat",
        "Wheat",
        "cereal",
        "Cool-season cereal grown in the rabi season on well-drained, fertile soils.",
        "iiwbr",
        [
            _req("ph", min_value=6.0, max_value=7.5, is_essential=True,
                 explanation="Wheat performs best near neutral pH.", sequence=0),
            _req("texture", values=["loam", "sandy_loam", "clay_loam", "silt_loam"],
                 explanation="Fertile, well-drained loams suit wheat.", sequence=0),
            _req("water", values=["medium"], is_essential=True,
                 explanation="Wheat needs moderate assured water (irrigation in rabi).", sequence=0),
            _req("season", values=["rabi"], explanation="Rabi (winter) crop.", sequence=0),
            _req("temperature", min_value=15, max_value=25, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=400, max_value=650, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=120, max_value=150, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "sorghum",
        "Sorghum (jowar)",
        "cereal",
        "Drought-tolerant cereal for kharif and rabi, suited to a wide range of soils.",
        "icrisat",
        [
            _req("ph", min_value=6.0, max_value=8.0, is_essential=True,
                 explanation="Sorghum tolerates a wide pH range around neutral.", sequence=0),
            _req("texture", values=["clay_loam", "sandy_loam", "loam", "clay"],
                 explanation="Sorghum adapts to many textures; deep soils preferred.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Sorghum is drought-tolerant and needs little water.", sequence=0),
            _req("season", values=["kharif", "rabi"], explanation="Grown in kharif and rabi.", sequence=0),
            _req("temperature", min_value=25, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=400, max_value=700, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=90, max_value=120, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "pearl_millet",
        "Pearl millet (bajra)",
        "millet",
        "Hardy monsoon millet for the driest, lightest soils with low water.",
        "icrisat",
        [
            _req("ph", min_value=6.0, max_value=8.0, is_essential=True,
                 explanation="Pearl millet tolerates mildly acid to alkaline soils.", sequence=0),
            _req("texture", values=["sandy_loam", "loamy_sand", "sand", "sandy_clay_loam"],
                 explanation="Pearl millet thrives on light, well-drained soils.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Very drought-tolerant; needs little water.", sequence=0),
            _req("season", values=["kharif"], explanation="Mainly a kharif crop.", sequence=0),
            _req("temperature", min_value=25, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=400, max_value=600, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=75, max_value=90, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "finger_millet",
        "Finger millet (ragi)",
        "millet",
        "Nutritious millet for kharif on well-drained loams with low to moderate water.",
        "uas",
        [
            _req("ph", min_value=5.5, max_value=7.5, is_essential=True,
                 explanation="Finger millet grows across mildly acid to neutral soils.", sequence=0),
            _req("texture", values=["loam", "sandy_loam", "silt_loam", "clay_loam"],
                 explanation="Well-drained loams suit finger millet.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Finger millet needs little water once established.", sequence=0),
            _req("season", values=["kharif"], explanation="Mainly a kharif crop.", sequence=0),
            _req("temperature", min_value=20, max_value=30, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=500, max_value=700, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=95, max_value=120, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "groundnut",
        "Groundnut",
        "oilseed",
        "Kharif oilseed needing light, well-drained soils for pod development.",
        "icrisat",
        [
            _req("ph", min_value=6.0, max_value=7.5, is_essential=True,
                 explanation="Groundnut prefers near-neutral, calcium-rich soils.", sequence=0),
            _req("texture", values=["sandy_loam", "loamy_sand", "sandy_clay_loam", "loam"],
                 explanation="Light soils ease pegging and pod harvest.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Groundnut is fairly drought-tolerant.", sequence=0),
            _req("season", values=["kharif"], explanation="Mainly a kharif crop.", sequence=0),
            _req("temperature", min_value=25, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=500, max_value=1000, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=90, max_value=130, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "chickpea",
        "Chickpea (chana)",
        "pulse",
        "Cool-season pulse grown in rabi, fixing nitrogen and improving soil.",
        "icrisat",
        [
            _req("ph", min_value=6.0, max_value=8.0, is_essential=True,
                 explanation="Chickpea tolerates neutral to mildly alkaline soils.", sequence=0),
            _req("texture", values=["clay_loam", "sandy_loam", "loam", "clay"],
                 explanation="Well-drained medium to heavy soils suit chickpea.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Chickpea is a low-water rabi pulse.", sequence=0),
            _req("season", values=["rabi"], explanation="Rabi (winter) pulse.", sequence=0),
            _req("temperature", min_value=15, max_value=25, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=300, max_value=500, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=95, max_value=120, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "pigeonpea",
        "Pigeonpea (tur)",
        "pulse",
        "Long-duration kharif pulse for medium to heavy soils; improves soil nitrogen.",
        "icrisat",
        [
            _req("ph", min_value=6.0, max_value=7.5, is_essential=True,
                 explanation="Pigeonpea prefers slightly acid to neutral soils.", sequence=0),
            _req("texture", values=["loam", "clay_loam", "sandy_loam"],
                 explanation="Medium to heavy, well-drained soils suit pigeonpea.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Deep-rooted and relatively drought-tolerant.", sequence=0),
            _req("season", values=["kharif"], explanation="Kharif pulse.", sequence=0),
            _req("temperature", min_value=25, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=600, max_value=1000, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=120, max_value=180, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "green_gram",
        "Green gram (moong)",
        "pulse",
        "Short-duration kharif pulse needing light, well-drained soils and little water.",
        "iipr",
        [
            _req("ph", min_value=6.0, max_value=7.5, is_essential=True,
                 explanation="Green gram prefers near-neutral soils.", sequence=0),
            _req("texture", values=["loam", "sandy_loam", "clay_loam"],
                 explanation="Well-drained loams suit green gram.", sequence=0),
            _req("water", values=["low"], is_essential=True,
                 explanation="Short-duration, low-water pulse.", sequence=0),
            _req("season", values=["kharif"], explanation="Kharif (and short summer) pulse.", sequence=0),
            _req("temperature", min_value=25, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=400, max_value=700, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=60, max_value=90, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "cotton",
        "Cotton",
        "fibre",
        "Long-duration kharif fibre crop for deep, moisture-retentive soils.",
        "cicr",
        [
            _req("ph", min_value=6.0, max_value=8.0, is_essential=True,
                 explanation="Cotton tolerates neutral to mildly alkaline soils.", sequence=0),
            _req("texture", values=["clay", "clay_loam", "sandy_clay_loam", "sandy_loam", "loam"],
                 explanation="Deep, well-drained soils suit cotton.", sequence=0),
            _req("water", values=["medium"], is_essential=True,
                 explanation="Cotton needs moderate water, often partly rain-fed.", sequence=0),
            _req("season", values=["kharif"], explanation="Kharif crop.", sequence=0),
            _req("temperature", min_value=21, max_value=35, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=500, max_value=1000, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=150, max_value=180, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
    _crop(
        "tomato",
        "Tomato",
        "vegetable",
        "High-water vegetable for well-drained, fertile soils; grown across seasons "
        "with assured irrigation.",
        "tnau",
        [
            _req("ph", min_value=6.0, max_value=7.0, is_essential=True,
                 explanation="Tomato prefers slightly acid to neutral soils.", sequence=0),
            _req("texture", values=["loam", "sandy_loam", "silt_loam", "clay_loam"],
                 explanation="Well-drained loams suit tomato.", sequence=0),
            _req("water", values=["high"], is_essential=True,
                 explanation="Tomato needs assured, regular irrigation.", sequence=0),
            _req("season", values=["kharif", "rabi", "zaid"],
                 explanation="Grown in multiple seasons under irrigation.", sequence=0),
            _req("temperature", min_value=20, max_value=30, explanation=_TEMP_NOTE, sequence=0),
            _req("rainfall", min_value=400, max_value=600, explanation=_RAIN_NOTE, sequence=0),
            _req("duration", min_value=90, max_value=120, explanation=_DURATION_NOTE, sequence=0),
        ],
    ),
]

# Seeded default scoring configuration (one row; admin-editable).
SCORING_CONFIG: Final[dict] = {
    "weights": {
        "ph": 1.0,
        "texture": 1.0,
        "water": 1.0,
        "season": 0.8,
        "region": 0.6,
    },
    "essential_factors": ["ph", "water"],
    "suitable_threshold": 0.65,
    "min_coverage": 0.5,
    "stale_soil_days": 1095,
    "is_active": True,
}

__all__ = ["CROPS", "SCORING_CONFIG", "SOURCES", "DATE_REVIEWED"]
