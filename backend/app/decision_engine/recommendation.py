"""Crop Intelligence engine: evaluate crops against a field, transparently.

The engine combines three real inputs - the field profile, the latest soil test
(Soil Intelligence) and the live weather forecast where available - with the
admin-managed crop knowledge base. It returns a per-crop *suitability estimate*
with the full working shown: each factor's score, the reason for the
classification, and any weather risks.

It is deliberately transparent and honest:

- missing inputs are reported as gaps; they never become a zero or a red verdict,
  and the score uses only the evidence that was actually evaluated;
- a missing soil test in particular does not block a crop - the estimate is
  built from what is recorded (location, season, water) and flagged as
  preliminary until soil can be compared;
- stale or future-dated soil tests are excluded with a note;
- a crop whose season or region does not match the current one is genuinely
  not recommended now, regardless of other matches;
- weather is context only and never silently changes the score;
- outputs are never yields, prices, profits or pest/disease predictions.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.decision_engine import constants as C
from app.decision_engine import scoring, soil_context, weather_risk
from app.decision_engine.soil_context import SoilContext
from app.models.crop import Crop, CropRecommendation, CropRequirement, CropScoringConfig
from app.models.field import Field
from app.services.soil_limits import NUMERIC_PARAMETERS, TEXTURE_LABELS
from app.services.weather_service import WeatherSnapshot


def load_config(db: Session) -> dict:
    """Merge the admin-managed scoring config over the documented defaults."""
    weights = dict(C.DEFAULT_WEIGHTS)
    essential = list(C.DEFAULT_ESSENTIAL_FACTORS)
    suitable = C.DEFAULT_SUITABLE_THRESHOLD
    min_coverage = C.DEFAULT_MIN_COVERAGE
    stale_days = C.DEFAULT_STALE_SOIL_DAYS

    row = (
        db.query(CropScoringConfig)
        .filter(CropScoringConfig.is_active.is_(True))
        .order_by(CropScoringConfig.id)
        .first()
    )
    if row is not None:
        stored = row.weights or {}
        for factor, value in stored.items():
            if factor in C.SCORED_FACTORS:
                try:
                    weights[factor] = float(value)
                except (TypeError, ValueError):
                    continue
        stored_essential = row.essential_factors
        if stored_essential:
            essential = [f for f in stored_essential if f in C.SCORED_FACTORS]
        suitable = float(row.suitable_threshold)
        min_coverage = float(row.min_coverage)
        stale_days = int(row.stale_soil_days)

    return {
        "weights": weights,
        "essential_factors": essential,
        "suitable_threshold": suitable,
        "min_coverage": min_coverage,
        "stale_soil_days": stale_days,
    }


def _requirement_dict(req: CropRequirement) -> dict:
    return {
        "factor": req.factor,
        "min_value": req.min_value,
        "max_value": req.max_value,
        "allowed_values": list(req.allowed_values) if req.allowed_values else None,
        "is_essential": bool(req.is_essential),
        "explanation": req.explanation,
        "source": req.source,
        "source_url": req.source_url,
    }


def _first_value(req: CropRequirement) -> Optional[str]:
    if not req.allowed_values:
        return None
    return req.allowed_values[0]


def _factor_score(
    factor: str, req: CropRequirement, field: Field, soil: SoilContext, today: date
) -> tuple[Optional[float], object, str]:
    """Return (score, input_value, detail) for one scored factor."""
    if factor == C.FACTOR_PH:
        value = soil.ph if soil.scorable else None
        if value is None:
            return None, None, "No current soil pH to compare (add or refresh a soil test)."
        lo, hi = req.min_value, req.max_value
        score = scoring.range_score(value, lo, hi, factor)
        band = f"{lo:g}–{hi:g}" if lo is not None and hi is not None else "the preferred band"
        return score, value, f"Measured pH {value:g} against preferred {band}."

    if factor == C.FACTOR_TEXTURE:
        value = soil.texture if soil.scorable else None
        if value is None:
            return None, None, "No current soil texture to compare (record it in Soil Intelligence)."
        score = scoring.texture_score(value, req.allowed_values)
        label = TEXTURE_LABELS.get(value, value)
        preferred = ", ".join(TEXTURE_LABELS.get(v, v) for v in (req.allowed_values or []))
        if score is None:
            return None, value, f"Soil texture {label} cannot be compared to a standard class."
        return score, value, f"Soil texture {label} against crops preferring {preferred}."

    if factor == C.FACTOR_WATER:
        availability = field.water_availability
        need = _first_value(req)
        if availability is None:
            return None, None, "Water availability has not been recorded for this field."
        score = scoring.water_score(availability, need, field.water_source)
        if score is None:
            return None, availability, "Water availability or crop need is not recognised."
        source_label = C.WATER_SOURCE_LABELS.get(field.water_source or "", field.water_source or "unrecorded")
        return (
            score,
            availability,
            f"Reported water availability '{availability}' ({source_label}) against a {need}-water crop.",
        )

    if factor == C.FACTOR_SEASON:
        current = C.season_for_month(today.month)
        allowed = req.allowed_values
        if not allowed:
            return None, current, "Crop season not specified."
        score = scoring.season_score(today.month, allowed)
        allowed_labels = ", ".join(C.SEASON_LABELS.get(s, s) for s in allowed)
        return score, current, f"Current season {C.SEASON_LABELS.get(current, current)} against {allowed_labels}."

    if factor == C.FACTOR_REGION:
        allowed = req.allowed_values
        if not allowed:
            return None, field.state, "Crop region not specified."
        if not field.state:
            return None, None, "Field region (state) is not recorded."
        score = scoring.region_score(field.state, allowed)
        return score, field.state, f"Field region {field.state} against {', '.join(allowed)}."

    return None, None, "Unknown factor."


def _classify(
    declared: list[str], evaluated: dict[str, float], config: dict
) -> tuple[str, Optional[float], float, list[str], list[str]]:
    """Classify a crop from the available evidence only.

    Missing inputs never penalise a crop: they are reported as gaps that would
    improve confidence, never as failures. The verdict comes from factors that
    were actually evaluated:

    - an essential factor scored below the threshold, or a season/region
      mismatch, is a genuine reason NOT to recommend right now;
    - with no evaluable evidence at all the crop needs more information;
    - otherwise the weighted overall score decides, and a partial-coverage
      estimate is still emitted (flagged as ``preliminary`` upstream) so
      farmers get useful guidance before a soil test exists.

    Returns ``(status, overall, coverage, essential_fail, drift_fail)``.
    """
    weights = config["weights"]
    suitable = config["suitable_threshold"]
    essentials_declared = [f for f in config["essential_factors"] if f in declared]

    weight_total = sum(weights.get(f, 0.0) for f in declared)
    weight_eval = sum(weights.get(f, 0.0) for f in evaluated)
    coverage = weight_eval / weight_total if weight_total else 0.0
    overall = (
        sum(weights.get(f, 0.0) * s for f, s in evaluated.items()) / weight_eval
        if weight_eval
        else None
    )

    essential_fail = [
        f for f in essentials_declared if f in evaluated and evaluated[f] < suitable
    ]
    drift_fail = [
        f
        for f in (C.FACTOR_SEASON, C.FACTOR_REGION)
        if f in evaluated and evaluated[f] == 0.0
    ]

    if essential_fail or drift_fail:
        status = C.STATUS_NOT_RECOMMENDED
    elif overall is None:
        status = C.STATUS_NEEDS_INFO
    elif overall >= suitable:
        status = C.STATUS_SUITABLE
    else:
        status = C.STATUS_NOT_RECOMMENDED

    return status, overall, coverage, essential_fail, drift_fail


def _next_steps(
    status: str,
    missing: list[str],
    fail: list[str],
    field: Field,
    soil: SoilContext,
    weather: Optional[WeatherSnapshot],
    config: dict,
) -> list[str]:
    """Concrete, honest actions that would improve or unblock this estimate.

    Every step names a real action available in ANNADATA (or in the field
    records). Nothing here is a promise of a better score - only what would let
    the engine check more of the crop's documented requirements.
    """
    steps: list[str] = []

    if not soil.has_measurement:
        steps.append(
            "Add a soil test for this field in Soil Intelligence so pH and soil "
            "texture can be compared with this crop's requirements."
        )
    elif soil.is_stale:
        steps.append(
            "Refresh the soil test - the recorded one is older than the "
            f"{config['stale_soil_days']}-day limit used for scoring."
        )
    elif soil.is_future:
        steps.append(
            "Correct the soil test date - it is dated in the future, so it is "
            "not used for scoring."
        )

    soil_gaps = [f for f in (C.FACTOR_PH, C.FACTOR_TEXTURE) if f in missing]
    if soil_gaps and soil.has_measurement:
        labels = ", ".join(C.FACTOR_LABELS[f] for f in soil_gaps)
        steps.append(
            f"Complete the soil test by recording {labels} in Soil Intelligence "
            "so the crop's full soil picture can be checked."
        )

    if field.water_availability is None:
        steps.append(
            "Record water availability for this field (field profile) so the "
            "crop's water need can be compared."
        )

    if C.FACTOR_REGION in missing:
        steps.append(
            "Add the field's state/location so regional suitability can be "
            "checked against this crop's documented regions."
        )

    if weather is None and field.latitude is not None:
        steps.append(
            "Live weather is unavailable right now; retry later to add "
            "rainfall and temperature risks to this estimate."
        )
    elif weather is None:
        steps.append(
            "Confirm the field's coordinates so live weather can be included "
            "as risk context."
        )

    if status == C.STATUS_NOT_RECOMMENDED and fail:
        labels = ", ".join(C.FACTOR_LABELS[f] for f in fail)
        steps.append(
            f"Address the limiting factor(s) for this field ({labels}) or "
            "compare crops that match the conditions you already have."
        )
    elif status == C.STATUS_NOT_RECOMMENDED:
        steps.append(
            "Compare other crops in the ranked list, or improve the limiting "
            "factors named above before reassessing."
        )
    elif status == C.STATUS_NEEDS_INFO:
        steps.append(
            "Re-run the assessment after adding the information above to get a "
            "full suitability estimate."
        )
    elif missing:
        steps.append(
            "Add the missing information above, then re-run, to turn this "
            "preliminary estimate into a full one."
        )
    else:
        steps.append(
            "Review the factors below, then confirm with local extension advice "
            "before committing to this crop."
        )

    return steps


def evaluate_crop(
    crop: Crop,
    requirements: list[CropRequirement],
    field: Field,
    soil: SoilContext,
    config: dict,
    weather: Optional[WeatherSnapshot],
    today: date,
) -> dict:
    req_map = {r.factor: r for r in requirements if r.is_active}

    factors: dict[str, dict] = {}
    declared: list[str] = []
    evaluated: dict[str, float] = {}
    missing: list[str] = []

    for factor in C.SCORED_FACTORS:
        req = req_map.get(factor)
        if req is None:
            factors[factor] = {
                "factor": factor,
                "label": C.FACTOR_LABELS[factor],
                "status": "not_required",
                "score": None,
                "weight": config["weights"].get(factor, 0.0),
                "input": None,
                "detail": "This crop has no documented requirement for this factor.",
                "requirement": None,
                "is_essential": False,
                "source": None,
                "source_url": None,
            }
            continue

        declared.append(factor)
        score, value, detail = _factor_score(factor, req, field, soil, today)
        if score is None:
            status = "missing_input"
            missing.append(factor)
        else:
            status = "evaluated"
            evaluated[factor] = score
        factors[factor] = {
            "factor": factor,
            "label": C.FACTOR_LABELS[factor],
            "status": status,
            "score": round(score, 4) if score is not None else None,
            "weight": config["weights"].get(factor, 0.0),
            "input": value,
            "detail": detail,
            "requirement": _requirement_dict(req),
            "is_essential": bool(req.is_essential),
            "source": req.source,
            "source_url": req.source_url,
        }

    # Context-only factors: shown as supporting information, never scored.
    context: dict[str, dict] = {}
    for factor in C.CONTEXT_FACTORS:
        req = req_map.get(factor)
        if req is None:
            continue
        context[factor] = {
            "factor": factor,
            "label": C.FACTOR_LABELS[factor],
            "status": "context",
            "detail": req.explanation
            or "Shown as supporting information only; it does not change the score.",
            "requirement": _requirement_dict(req),
            "source": req.source,
            "source_url": req.source_url,
        }

    status, overall, coverage, essential_fail, drift_fail = _classify(
        declared, evaluated, config
    )
    preliminary = bool(missing)

    # Weather risks: global rainfall risks plus heat/cold vs this crop's band.
    risks = weather_risk.global_risks(weather)
    temp_req = req_map.get(C.FACTOR_TEMPERATURE)
    if temp_req is not None:
        risks = risks + weather_risk.temperature_risks(
            weather, temp_req.min_value, temp_req.max_value, crop.display_name
        )

    reasons = _reasons(
        crop, status, overall, coverage, missing, essential_fail + drift_fail, config
    )
    next_steps = _next_steps(status, missing, essential_fail + drift_fail, field, soil, weather, config)

    notes = list(soil.notes)
    if weather is None:
        notes.append(
            "Live weather was not available; the estimate uses field and soil data only."
        )
    if preliminary:
        notes.append(
            "Preliminary estimate: some documented requirements were not checked "
            "because the data is not recorded yet. The score reflects only the "
            "evidence actually available."
        )

    return {
        "crop_id": crop.id,
        "crop_name": crop.name,
        "display_name": crop.display_name,
        "category": crop.category,
        "description": crop.description,
        "status": status,
        "status_label": C.STATUS_LABELS[status],
        "score": round(overall, 4) if overall is not None else None,
        "coverage": round(coverage, 4),
        "preliminary": preliminary,
        "factors": factors,
        "context_factors": context,
        "reasons": reasons,
        "next_steps": next_steps,
        "risks": risks,
        "notes": notes,
        "source": crop.source,
        "source_url": crop.source_url,
        "date_reviewed": crop.date_reviewed.isoformat() if crop.date_reviewed else None,
    }


def _missing_labels(missing: list[str]) -> str:
    return ", ".join(C.FACTOR_LABELS.get(f, f) for f in missing)


def _reasons(
    crop: Crop,
    status: str,
    overall: Optional[float],
    coverage: float,
    missing: list[str],
    fail: list[str],
    config: dict,
) -> list[str]:
    reasons: list[str] = []
    if status == C.STATUS_NEEDS_INFO:
        reasons.append(
            "Not enough recorded information exists about this field to score this "
            "crop yet - no documented requirement could be compared."
        )
        return reasons

    if fail:
        labels = ", ".join(C.FACTOR_LABELS.get(f, f) for f in fail)
        reasons.append(
            f"A documented requirement is not met for this field right now: {labels}. "
            "This is a genuine limitation of the field, not missing data."
        )
        if missing:
            reasons.append(
                f"Missing information that could improve confidence: {_missing_labels(missing)}."
            )
        return reasons

    if status == C.STATUS_SUITABLE:
        if missing:
            reasons.append(
                f"Preliminary estimate - matches the recorded information for "
                f"{crop.display_name} (suitability {overall:.2f} across "
                f"{coverage * 100:.0f}% of its documented requirements)."
            )
            reasons.append(
                f"Checking the missing factor(s) "
                f"({_missing_labels(missing)}) would improve confidence."
            )
        else:
            reasons.append(
                f"Meets the documented thresholds for {crop.display_name} "
                f"(suitability {overall:.2f} across {coverage * 100:.0f}% of "
                "requirements)."
            )
    else:
        reasons.append(
            f"Scored {overall:.2f} on the available information, below the "
            f"suitability threshold of {config['suitable_threshold']:.2f}."
        )
        if missing:
            reasons.append(
                f"Missing information that could improve confidence: {_missing_labels(missing)}."
            )

    return reasons


def _season(today: date) -> str:
    return C.season_for_month(today.month)


def _input_snapshot(
    field: Field, soil: SoilContext, weather_summary: dict, config: dict, today: date
) -> dict:
    return {
        "engine_version": C.ENGINE_VERSION,
        "reference_date": today.isoformat(),
        "season": _season(today),
        "field": {
            "id": field.id,
            "field_name": field.field_name,
            "state": field.state,
            "district": field.district,
            "water_source": field.water_source,
            "water_availability": field.water_availability,
            "has_coordinates": field.latitude is not None and field.longitude is not None,
        },
        "soil": {
            "has_measurement": soil.has_measurement,
            "tested_on": soil.tested_on.isoformat() if soil.tested_on else None,
            "age_days": soil.age_days,
            "is_stale": soil.is_stale,
            "is_future": soil.is_future,
            "ph": soil.ph,
            "texture": soil.texture,
            "source_kind": soil.values.get("source_kind"),
            "measured_parameters": [
                name for name in NUMERIC_PARAMETERS if soil.values.get(name) is not None
            ],
        },
        "weather": weather_summary,
        "scoring": {
            "weights": config["weights"],
            "essential_factors": config["essential_factors"],
            "suitable_threshold": config["suitable_threshold"],
            "min_coverage": config["min_coverage"],
            "stale_soil_days": config["stale_soil_days"],
        },
    }


def _sort_results(results: list[dict]) -> list[dict]:
    order = {
        C.STATUS_SUITABLE: 0,
        C.STATUS_NEEDS_INFO: 1,
        C.STATUS_NOT_RECOMMENDED: 2,
    }
    return sorted(
        results,
        key=lambda r: (order.get(r["status"], 3), -(r["score"] or 0.0), r["display_name"]),
    )


def evaluate_field(
    db: Session,
    field: Field,
    weather: Optional[WeatherSnapshot],
    weather_reason: Optional[str] = None,
    today: Optional[date] = None,
) -> dict:
    """Evaluate every active crop against a field (no persistence)."""
    today = today or date.today()
    config = load_config(db)
    soil = soil_context.build_soil_context(db, field, config["stale_soil_days"], today)
    weather_summary = weather_risk.summarize(weather, weather_reason)

    crops = (
        db.query(Crop).filter(Crop.is_active.is_(True)).order_by(Crop.display_name).all()
    )
    results = [
        evaluate_crop(crop, crop.requirements, field, soil, config, weather, today)
        for crop in crops
    ]

    return {
        "field_id": field.id,
        "season": _season(today),
        "weather": weather_summary,
        "soil": {
            "has_measurement": soil.has_measurement,
            "tested_on": soil.tested_on.isoformat() if soil.tested_on else None,
            "is_stale": soil.is_stale,
            "is_future": soil.is_future,
        },
        "notes": list(soil.notes),
        "config": config,
        "results": _sort_results(results),
        "_snapshot": _input_snapshot(field, soil, weather_summary, config, today),
    }


def generate_recommendations(
    db: Session,
    field: Field,
    weather: Optional[WeatherSnapshot],
    weather_reason: Optional[str] = None,
    today: Optional[date] = None,
) -> dict:
    """Evaluate and persist one recommendation row per active crop."""
    evaluation = evaluate_field(db, field, weather, weather_reason, today)
    batch_id = uuid.uuid4().hex[:32]
    snapshot = evaluation["_snapshot"]

    for result in evaluation["results"]:
        db.add(
            CropRecommendation(
                field_id=field.id,
                user_id=field.user_id,
                crop_id=result["crop_id"],
                batch_id=batch_id,
                engine_version=C.ENGINE_VERSION,
                season=evaluation["season"],
                status=result["status"],
                score=result["score"],
                coverage=result["coverage"],
                result=result,
                input_snapshot=snapshot,
            )
        )
    db.commit()

    evaluation["batch_id"] = batch_id
    return evaluation


__all__ = [
    "load_config",
    "evaluate_crop",
    "evaluate_field",
    "generate_recommendations",
]
