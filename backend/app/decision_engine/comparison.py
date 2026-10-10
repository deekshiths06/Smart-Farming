"""Explainable crop comparison.

Given a full field evaluation (from :func:`app.decision_engine.recommendation.evaluate_field`)
and a small chosen subset of crops, this module builds a comparison the farmer
can actually reason about:

- an unambiguous ``ranking`` using exactly the same ordering rules as the ranked
  recommendations (status bucket, then score, then name);
- a per-factor side-by-side ``factors`` matrix, where every value comes from the
  evaluated factors of the selected crops (never invented);
- plain-language ``differences`` explaining why one crop ranks higher or lower
  than another on the current evidence;
- ``rank_changers`` (missing inputs, weather warnings) that could change the
  order;
- ``info_to_collect`` naming exactly which field inputs would firm the estimate.

Honesty rules baked in:

- a crop is never declared "better" on incomplete evidence: whenever any
  compared crop has unrecorded inputs, ``preliminary_note`` spells out that the
  ranking is preliminary and that a higher score is not proof of a better match;
- season/region mismatches and essential-factor shortfalls are reported as
  constraints, never as missing-data slashes;
- live weather (if fetched) is reported as advisory context, not scored.
"""

from __future__ import annotations

from typing import Optional

from app.decision_engine import constants as C
from app.services.soil_limits import TEXTURE_LABELS

# Water availability values as recorded on the field profile (labels only).
WATER_AVAILABILITY_LABELS: dict[str, str] = {
    "limited": "Limited",
    "seasonal": "Seasonal",
    "moderate": "Moderate",
    "good": "Good",
    "not_sure": "Not sure",
}

# factor -> (friendly name used in "information to collect", action statement)
COLLECT_ACTIONS: dict[str, tuple[str, str]] = {
    C.FACTOR_PH: (
        "soil pH",
        "Record soil pH in a soil test through Soil Intelligence",
    ),
    C.FACTOR_TEXTURE: (
        "soil texture",
        "Record soil texture in the soil test through Soil Intelligence",
    ),
    C.FACTOR_WATER: (
        "water availability",
        "Record the field's water availability in its profile",
    ),
    C.FACTOR_REGION: (
        "field region",
        "Add the field's state/district so regional suitability can be checked",
    ),
}


def _status_order(status: str) -> int:
    order = {
        C.STATUS_SUITABLE: 0,
        C.STATUS_NEEDS_INFO: 1,
        C.STATUS_NOT_RECOMMENDED: 2,
    }
    return order.get(status, 3)


def _pct(score: Optional[float]) -> str:
    if score is None:
        return "—"
    return f"{score * 100:.0f}%"


def _value_label(factor: str, value) -> str:
    if value is None:
        return "—"
    if factor == C.FACTOR_TEXTURE:
        return TEXTURE_LABELS.get(str(value), str(value))
    if factor == C.FACTOR_SEASON:
        return C.SEASON_LABELS.get(str(value), str(value))
    if factor == C.FACTOR_WATER:
        return WATER_AVAILABILITY_LABELS.get(str(value), str(value))
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


def _requirement_text(req: Optional[dict]) -> str:
    if not req:
        return "no documented requirement"
    values = req.get("allowed_values") or []
    if values:
        shown = ", ".join(values[:3])
        if len(values) > 3:
            shown += "…"
        return f"prefers {shown}"
    low, high = req.get("min_value"), req.get("max_value")
    if low is not None and high is not None:
        return f"needs {low:g}–{high:g}"
    if low is not None:
        return f"needs {low:g}+"
    if high is not None:
        return f"needs up to {high:g}"
    return "no documented requirement"


def _per_crop(
    result: dict, config: dict
) -> tuple[list[str], list[str], list[str]]:
    """Return (constraints, supporting, missing) for one evaluated crop.

    - ``constraints``: evaluated factors that genuinely argue against the crop
      right now (an essential factor below the threshold, or a season/region
      mismatch scored 0);
    - ``supporting``: evaluated factors that meet or beat the threshold;
    - ``missing``: factors documented for the crop but not recorded for the field.
    """
    threshold = config["suitable_threshold"]
    essentials = set(config["essential_factors"])
    constraints: list[str] = []
    supporting: list[str] = []
    missing: list[str] = []

    for factor in C.SCORED_FACTORS:
        f = result["factors"].get(factor)
        if f is None:
            continue
        if f["status"] == "missing_input":
            missing.append(f["label"])
            continue
        if f["status"] != "evaluated" or f["score"] is None:
            continue
        score = f["score"]
        label = f["label"]
        short = f"{label} ({_pct(score)})"
        is_season_or_region = factor in (C.FACTOR_SEASON, C.FACTOR_REGION)
        if (is_season_or_region and score == 0.0) or (
            factor in essentials and score < threshold
        ):
            constraints.append(short)
        elif score >= threshold:
            supporting.append(short)

    return constraints, supporting, missing


def _names_by_id(results: list[dict]) -> dict[int, str]:
    return {r["crop_id"]: r["display_name"] for r in results}


def _factor_row(
    factor: str, results: list[dict], names: dict[int, str]
) -> dict:
    cells: list[dict] = []
    for result in results:
        f = result["factors"].get(factor)
        if f is None:
            continue
        req = f.get("requirement") or {}
        cells.append(
            {
                "crop_id": result["crop_id"],
                "status": f["status"],
                "score": f["score"],
                "value_label": _value_label(factor, f.get("input")),
                "requirement_text": _requirement_text(req),
                "detail": f.get("detail", ""),
            }
        )

    evaluated = [c for c in cells if c["status"] == "evaluated"]
    value_labels = [c["value_label"] for c in evaluated if c["value_label"] != "—"]
    value_label = (
        value_labels[0] if value_labels else ("—" if evaluated else "not recorded")
    )

    if not evaluated:
        explanation = "Not recorded for this field — cannot be compared."
        compared = False
    else:
        compared = True
        missing_here = [
            names[c["crop_id"]] for c in cells if c["status"] == "missing_input"
        ]
        if missing_here:
            explanation = (
                f"Recorded for some crops ({value_label}); cannot be compared for "
                f"{', '.join(missing_here)} until recorded."
            )
        else:
            scored = {c["crop_id"]: c["score"] for c in evaluated}
            scores = {k: v for k, v in scored.items() if v is not None}
            best_score = max(scores.values())
            worst_score = min(scores.values())
            best = ", ".join(names[k] for k in scores if scores[k] == best_score)
            worst = ", ".join(names[k] for k in scores if scores[k] == worst_score)
            explanation = (
                f"Favours {best} ({_pct(best_score)}) over {worst} "
                f"({_pct(worst_score)}) — field value '{value_label}'."
            )

    return {
        "factor": factor,
        "label": C.FACTOR_LABELS[factor],
        "value_label": value_label,
        "compared": compared,
        "explanation": explanation,
        "cells": cells,
    }


def build_comparison(evaluation: dict, crop_ids: list[int]) -> dict:
    """Build the explainable comparison payload for a subset of evaluated crops."""
    results = [r for r in evaluation["results"] if r["crop_id"] in crop_ids]
    results.sort(
        key=lambda r: (_status_order(r["status"]), -(r["score"] or 0.0), r["display_name"])
    )
    names = _names_by_id(results)
    config = evaluation["config"]

    ranking: list[dict] = []
    for rank, result in enumerate(results, start=1):
        constraints, supporting, missing = _per_crop(result, config)
        ranking.append(
            {
                "rank": rank,
                "crop_id": result["crop_id"],
                "display_name": result["display_name"],
                "status": result["status"],
                "status_label": result["status_label"],
                "score": result["score"],
                "coverage": result["coverage"],
                "preliminary": result.get("preliminary", False),
                "supporting": supporting,
                "constraints": constraints,
                "missing": missing,
            }
        )

    factors = [_factor_row(factor, results, names) for factor in C.SCORED_FACTORS]

    # -- Differences: why one crop ranks higher or lower -----------------------
    differences: list[str] = []
    if len(ranking) >= 2:
        order_parts = []
        for entry in ranking:
            score_text = f", {_pct(entry['score'])}" if entry["score"] is not None else ""
            order_parts.append(
                f"{entry['rank']}. {entry['display_name']} "
                f"({entry['status_label']}{score_text})"
            )
        differences.append("Rank order on the current evidence: " + " · ".join(order_parts) + ".")

    for entry in ranking:
        if entry["status"] == C.STATUS_NOT_RECOMMENDED and entry["constraints"]:
            differences.append(
                f"Why {entry['display_name']} is not recommended now: "
                + ", ".join(entry["constraints"])
                + "."
            )

    for row in factors:
        scored = [c for c in row["cells"] if c["score"] is not None]
        scores = {c["score"] for c in scored}
        if len(scores) > 1:
            differences.append(f"{row['label']}: {row['explanation']}")

    incomplete = [e for e in ranking if e["missing"]]
    complete = [e for e in ranking if not e["missing"]]
    if incomplete:
        labels = ", ".join(dict.fromkeys(e["display_name"] for e in incomplete))
        if complete:
            differences.append(
                f"Ranking order is not final: {labels} still have unrecorded "
                "inputs (see below) that could change it."
            )
        else:
            differences.append(
                f"The estimates for {labels} are preliminary until their missing "
                "inputs are recorded."
            )

    # -- What could change the ranking ----------------------------------------
    rank_changers: list[str] = []
    for entry in ranking:
        if entry["missing"]:
            rank_changers.append(
                f"Recording {', '.join(entry['missing'])} for "
                f"{entry['display_name']} would firm its estimate and could "
                "change the order."
            )

    weather = evaluation["weather"]
    weather_available = bool(weather.get("available"))
    risks: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        for risk in result["risks"]:
            key = (risk["kind"], risk["title"])
            if key not in seen:
                seen.add(key)
                risks.append(risk)

    if weather_available:
        if risks:
            rank_changers.append(
                f"The forecast carries {len(risks)} active warning(s) for this "
                "field (below); they add risk context and are not part of the "
                "suitability score."
            )
        else:
            rank_changers.append(
                "No weather warnings are active in the current forecast."
            )
    else:
        rank_changers.append(
            "Live weather was not available, so rainfall and temperature risks "
            "are not included in this comparison."
        )

    # -- Information to collect -----------------------------------------------
    missing_keys: set[str] = set()
    for result in results:
        for factor in C.SCORED_FACTORS:
            if result["factors"][factor]["status"] == "missing_input":
                missing_keys.add(factor)
    info_to_collect: list[dict] = []
    for key in sorted(missing_keys):
        if key in COLLECT_ACTIONS:
            _, action = COLLECT_ACTIONS[key]
            info_to_collect.append({"input": key, "action": action})
    if not weather_available:
        info_to_collect.append(
            {
                "input": "weather",
                "action": "Confirm the field's coordinates to include live weather risks",
            }
        )

    # -- Preliminary honesty note ---------------------------------------------
    prelims = [e for e in ranking if e["preliminary"]]
    preliminary_note: Optional[str] = None
    if prelims:
        crop_names = ", ".join(e["display_name"] for e in prelims)
        gap = ", ".join(
            dict.fromkeys(f for e in prelims if e["missing"] for f in e["missing"])
        )
        gap_text = f" ({gap})" if gap else ""
        preliminary_note = (
            f"The comparison is preliminary: {crop_names} could not be checked "
            f"against every documented requirement{gap_text}. A higher score on "
            "incomplete evidence is not proof of a better match — record the "
            "missing inputs below, then re-run, to firm the comparison."
        )

    return {
        "results": results,
        "ranking": ranking,
        "factors": factors,
        "differences": differences,
        "rank_changers": rank_changers,
        "info_to_collect": info_to_collect,
        "preliminary_note": preliminary_note,
        "context": {
            "season": evaluation.get("season"),
            "weather": weather,
            "soil": evaluation.get("soil"),
            "config": {
                "weights": config["weights"],
                "essential_factors": config["essential_factors"],
                "suitable_threshold": config["suitable_threshold"],
                "min_coverage": config["min_coverage"],
                "stale_soil_days": config["stale_soil_days"],
            },
        },
        "disclaimer": C.SUITABILITY_DISCLAIMER,
    }


__all__ = ["build_comparison"]