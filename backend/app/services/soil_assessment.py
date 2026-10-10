"""Explainable soil assessment service.

The service evaluates ONLY measured, validated values and compares them to the
applicable, admin-managed reference ranges (see ``SoilReferenceRange``).

Range selection is deliberately specificity-ordered:

1. ``soil_class`` - applies when the field's latest texture is a standard USDA class,
2. ``region`` - applies when the field's state/admin area is recorded,
3. ``general`` - national/all-soil guidance.

Crop ranges exist for the future Crop Recommendation Engine but never override
the levels above until a crop is chosen for the field.

The service never diagnoses a deficiency from a missing measurement - a missing
parameter reports status ``missing``, and a measured parameter with no suitable
range reports status ``no_range`` with an explicit "cannot be assessed yet".
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.field import Field
from app.models.soil import SOURCE_KIND_FARMER, SOURCE_KIND_REPORT, SoilReferenceRange
from app.services.soil_limits import (
    LAB_PARAMETERS,
    NUMERIC_PARAMETERS,
    PARAMETER_LABELS,
    PARAMETER_UNITS,
    PARAMETER_WHY,
    TEXTURE_INFO,
    is_numeric,
)

# Selection order: most specific applicable context first.
_CONTEXT_ORDER = ("soil_class", "region", "general")


@dataclass
class Context:
    soil_class: Optional[str] = None
    region: Optional[str] = None


class AssessmentError(ValueError):
    pass


def _context_matches(level: str, rng: SoilReferenceRange, ctx: Context) -> bool:
    if level != rng.context_type:
        return False
    if level == "soil_class":
        return ctx.soil_class is not None and rng.context_value == ctx.soil_class
    if level == "region":
        return ctx.region is not None and rng.context_value == ctx.region
    if level == "general":
        return rng.context_value in (None, "")
    return False


def _selected_ranges(db: Session, parameter: str, ctx: Context) -> list[SoilReferenceRange]:
    """All active ranges for a parameter ordered by specificity, then sequence."""
    candidates = (
        db.query(SoilReferenceRange)
        .filter(
            SoilReferenceRange.parameter == parameter,
            SoilReferenceRange.is_active.is_(True),
        )
        .all()
    )
    for level in _CONTEXT_ORDER:
        matched = [r for r in candidates if _context_matches(level, r, ctx)]
        if matched:
            return sorted(matched, key=lambda r: (r.sequence, r.id))
    return []


def _band_contains(value: float, rng: SoilReferenceRange) -> bool:
    lo, hi = rng.min_value, rng.max_value
    if lo is not None and value < lo:
        return False
    # Half-open on the upper edge so contiguous tiers never overlap/leave gaps.
    if hi is not None and value >= hi:
        return False
    return True


def _format(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    # Round to at most 2 decimals for display without altering stored precision.
    return round(value, 4)


def assess_parameter(
    db: Session, parameter: str, value: Optional[float], ctx: Context
) -> dict:
    """Assess one parameter from a measured value (or its absence)."""
    label = PARAMETER_LABELS[parameter]
    unit = PARAMETER_UNITS[parameter]

    if value is None:
        return {
            "parameter": parameter,
            "label": label,
            "unit": unit,
            "value": None,
            "texture_label": None,
            "measured": False,
            "status": "missing" if parameter in NUMERIC_PARAMETERS else "missing",
            "range_label": None,
            "min_value": None,
            "max_value": None,
            "explanation": (
                f"No record for {label}. {_method_note(parameter)} It is optional - "
                "enter it whenever you have it. Without it an assessment cannot be made."
            ),
            "source": None,
            "source_url": None,
            "applied_context": None,
            "source_kind": None,
        }

    if not is_numeric(parameter):
        # texture handled separately by the caller
        return {
            "parameter": parameter,
            "label": label,
            "unit": unit,
            "value": None,
            "texture_label": None,
            "measured": True,
            "status": "info",
            "explanation": "Soil texture is descriptive; it is used to select matching reference bands.",
            "source": None,
            "source_url": None,
            "applied_context": None,
        }

    ranges = _selected_ranges(db, parameter, ctx)
    if not ranges:
        return {
            "parameter": parameter,
            "label": label,
            "unit": unit,
            "value": _format(value),
            "texture_label": None,
            "measured": True,
            "status": "no_range",
            "range_label": None,
            "min_value": None,
            "max_value": None,
            "explanation": (
                f"{label} is recorded, but no verified reference range applies to this "
                "field yet (crop, region or soil-class guidance needed). An assessment "
                "cannot be made for this parameter right now."
            ),
            "source": None,
            "source_url": None,
            "applied_context": None,
        }

    matched = next((r for r in ranges if _band_contains(value, r)), None)
    if matched is not None:
        status = matched.outcome
        explanation = matched.explanation or _default_explanation(parameter, matched.outcome)
        context_label = _context_label(matched)
        return {
            "parameter": parameter,
            "label": label,
            "unit": unit,
            "value": _format(value),
            "texture_label": None,
            "measured": True,
            "status": status,
            "range_label": matched.label,
            "min_value": matched.min_value,
            "max_value": matched.max_value,
            "explanation": explanation,
            "source": matched.source,
            "source_url": matched.source_url,
            "applied_context": context_label,
        }

    # Value outside every band -> single ideal band (e.g. moisture) or a gap.
    if len(ranges) == 1:
        only = ranges[0]
        status = "below" if value < (only.min_value if only.min_value is not None else 0) else "above"
    else:
        # Contiguous classification bands: place by nearest boundary, honestly bounded.
        below = [r for r in ranges if r.max_value is not None and value < r.max_value]
        above = [r for r in ranges if r.min_value is not None and value >= r.min_value]
        status = "below" if below else "above"
    return {
        "parameter": parameter,
        "label": label,
        "unit": unit,
        "value": _format(value),
        "texture_label": None,
        "measured": True,
        "status": status,
        "range_label": None,
        "min_value": None,
        "max_value": None,
        "explanation": (
            f"{label} ({value} {unit}) falls outside every documented reference band for "
            "this field. Treat this value and any nearby laboratory reading with care."
        ),
        "source": None,
        "source_url": None,
        "applied_context": _context_label(ranges[0]),
    }


def assess_texture(value: Optional[str], source_kind: Optional[str]) -> dict:
    """Descriptive assessment for soil texture."""
    if value is None:
        return {
            "parameter": "texture",
            "label": PARAMETER_LABELS["texture"],
            "unit": "",
            "value": None,
            "texture_label": None,
            "measured": False,
            "status": "missing",
            "range_label": None,
            "min_value": None,
            "max_value": None,
            "explanation": (
                "No soil texture recorded. Texture tells us how the soil drains and holds "
                "water and nutrients - optional, but it sharpens every other comparison."
            ),
            "source": None,
            "source_url": None,
            "applied_context": None,
            "source_kind": source_kind,
            "requires_lab": False,
        }
    info = TEXTURE_INFO.get(value)
    return {
        "parameter": "texture",
        "label": PARAMETER_LABELS["texture"],
        "unit": "",
        "value": None,
        "texture_label": info["label"] if info else value,
        "measured": True,
        "status": "info",
        "range_label": None,
        "min_value": None,
        "max_value": None,
        "explanation": info["description"] if info else "Soil texture as recorded.",
        "source": "USDA-NRCS soil texture guidance",
        "source_url": None,
        "applied_context": "USDA texture triangle class",
        "source_kind": source_kind,
        "requires_lab": False,
    }


def _context_label(rng: SoilReferenceRange) -> str:
    if rng.context_type == "soil_class":
        return f"For {rng.context_value} soils"
    if rng.context_type == "region":
        return f"For {rng.context_value}"
    if rng.context_type == "crop":
        return f"For {rng.context_value}"
    return "General guidance"


def _default_explanation(parameter: str, outcome: str) -> str:
    if outcome == "within":
        return (
            f"{PARAMETER_LABELS[parameter]} sits inside the documented reference band for "
            "this field. Keep monitoring; re-test when the crop or season changes."
        )
    if outcome == "below":
        return (
            f"{PARAMETER_LABELS[parameter]} is below the ideal reference band for this field. "
            "This is a signal to investigate, not a diagnosis on its own."
        )
    return (
        f"{PARAMETER_LABELS[parameter]} is above the ideal reference band for this field. "
        "This is a signal to investigate, not a diagnosis on its own."
    )


def _source_kind_label(kind: Optional[str]) -> Optional[str]:
    if kind == SOURCE_KIND_REPORT:
        return "From an uploaded report, confirmed"
    if kind == SOURCE_KIND_FARMER:
        return "Farmer-entered"
    return None


def _method_note(parameter: str) -> str:
    """How the farmer obtains this value: laboratory vs in-field measurement."""
    if parameter in LAB_PARAMETERS:
        return "This value needs a laboratory soil test (for example a Soil Health Card)."
    if parameter in NUMERIC_PARAMETERS:
        return "This can be checked with a simple field test."
    return "This is read by feel in the field."


def build_assessment(
    db: Session, field: Field, values: Optional[dict]
) -> dict[str, dict]:
    """Full assessment for one field based on its latest measurement values."""
    ctx = Context(
        soil_class=(values or {}).get("texture") if values else None,
        region=field.state,
    )
    source_kind = (values or {}).get("source_kind")

    result: dict[str, dict] = {}
    for parameter in ("ph", "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture"):
        value = (values or {}).get(parameter)
        assessment = assess_parameter(db, parameter, value, ctx)
        assessment["source_kind"] = _source_kind_label(source_kind)
        assessment["requires_lab"] = parameter in LAB_PARAMETERS
        result[parameter] = assessment

    texture = (values or {}).get("texture")
    result["texture"] = assess_texture(texture, _source_kind_label(source_kind))
    # Context shows which soil class was used to pick bands (for transparency).
    for parameter in ("moisture",):
        if ctx.soil_class:
            result.setdefault(parameter, {})
    return result


def why_missing(parameter: str) -> str:
    return PARAMETER_WHY.get(parameter, "")