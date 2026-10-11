"""Smart Farming Action Planner: turn recorded data into plain, practical steps.

The planner is deliberately conservative. Every step it produces is derived from
data the farmer (or a live forecast) actually provided:

- the field profile (location, water availability) - always available;
- the latest soil test (Soil Intelligence);
- the most recent crop-suitability assessment, which already carries the
  live-weather risks (heavy rain, wet/dry spell, heat, cold) and the crop
  verdicts.

It never invents weather or soil values, never recommends a fertiliser or
pesticide amount, and never raises a pest or disease warning from a guess. When
something needed to judge a crop is simply not recorded, the planner asks for it
as an information-gathering step instead of guessing - and it says so plainly.

Each step is written in simple English for a farmer with limited technical
knowledge, and carries only the sections that are relevant to it:

- what to do (``title``) and why (``explanation``);
- when (``timing`` - a real date only when the forecast gives one, otherwise a
  condition or stage);
- how, as numbered ``steps``;
- what is needed (``materials``), what to check first (``check_first``), what to
  avoid (``avoid``) and how you know it is done (``done_when``);
- the source or reason (``reason`` and ``source``).

Steps are grouped so the most useful ones read first: "Do first", "Do next" and
"Check later". A step uses a stable ``action_key`` so a regenerated plan
reconnects to the same row and never loses the farmer's completion state.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.decision_engine import constants as C
from app.decision_engine.soil_context import SoilContext
from app.models.action import (
    CATEGORY_CROP,
    CATEGORY_INFORMATION,
    CATEGORY_SOIL,
    CATEGORY_WATER,
    CATEGORY_WEATHER,
    GROUP_CHECK_LATER,
    GROUP_DO_FIRST,
    GROUP_DO_NEXT,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)
from app.models.field import Field

# Bumped when the action-generation rules change, so persisted plans can be
# traced back to the logic that produced them.
PLANNER_VERSION = "2.0.0"

SOURCE_FIELD_PROFILE = "Your field profile"
SOURCE_SOIL = "Soil Intelligence"
SOURCE_ASSESSMENT = "Crop assessment"
SOURCE_RECOMMENDATIONS = "Crop Recommendations"

# Factors the farmer can actually record. Weather-derived factors (temperature,
# rainfall) are handled by the assessment itself, so they are never asked for.
_RECORDABLE_FACTORS = (
    C.FACTOR_PH,
    C.FACTOR_TEXTURE,
    C.FACTOR_WATER,
    C.FACTOR_REGION,
)

# Water availability values that mean water is not assured, so a "check before
# you water" step is worth showing. "moderate"/"good" fields are left alone.
_TIGHT_WATER = {"limited", "seasonal", "not_sure"}

ACTION_DISCLAIMER = (
    "This plan is built only from the information you have saved for this field - "
    "the field details, any soil test, the latest crop assessment and its weather "
    "forecast risks. It is general guidance to help you plan, not a guarantee. It "
    "never gives fertiliser or pesticide amounts. If a decision is high-risk or "
    "you are unsure, ask your local agriculture officer or Krishi Vigyan Kendra "
    "(KVK) before you act."
)


def _date_label(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.strftime("%d %b %Y")
    except AttributeError:
        return str(value)


def _action(
    *,
    action_key: str,
    category: str,
    group_key: str,
    title: str,
    explanation: str,
    priority: Optional[str],
    timing: Optional[str],
    reason: str,
    source: str,
    steps: Optional[list[str]] = None,
    materials: Optional[list[str]] = None,
    check_first: Optional[list[str]] = None,
    avoid: Optional[list[str]] = None,
    done_when: Optional[str] = None,
    details: Optional[dict] = None,
) -> dict:
    return {
        "action_key": action_key,
        "category": category,
        "group_key": group_key,
        "title": title,
        "explanation": explanation,
        "priority": priority,
        "timing": timing,
        "reason": reason,
        "source": source,
        "steps": steps,
        "materials": materials,
        "check_first": check_first,
        "avoid": avoid,
        "done_when": done_when,
        "details": details,
    }


# --- Field information -------------------------------------------------------


def _location_actions(field: Field) -> list[dict]:
    actions: list[dict] = []

    if field.latitude is None or field.longitude is None:
        actions.append(
            _action(
                action_key="information:confirm_location",
                category=CATEGORY_INFORMATION,
                group_key=GROUP_DO_NEXT,
                title="Save your field's location",
                explanation=(
                    "ANNADATA uses your field's location to find the local weather "
                    "and to check whether a crop suits your area. Without it, these "
                    "checks cannot be done."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Do this first, when you can.",
                reason="This field has no location saved yet.",
                source=SOURCE_FIELD_PROFILE,
                steps=[
                    "Open this field from My Fields.",
                    "Tap Edit, then use the button that finds your phone's location.",
                    "Stand in or near the field while you do this.",
                    "Check the pin sits on the correct field, then save.",
                ],
                materials=["A phone with location (GPS) switched on"],
                check_first=[
                    "Make sure you are at the field, not at home.",
                    "Location on your phone is switched on.",
                ],
                avoid=["Do not save a location that belongs to a different field."],
                done_when="The field shows a pin on the map and says the location is confirmed.",
            )
        )
    elif not field.location_confirmed:
        actions.append(
            _action(
                action_key="information:confirm_location",
                category=CATEGORY_INFORMATION,
                group_key=GROUP_DO_NEXT,
                title="Confirm your field's location",
                explanation=(
                    "A pin is saved for this field but it is not confirmed yet. "
                    "Confirming it makes the weather and area checks reliable."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Do this when you next open the field.",
                reason="The field's location has not been confirmed.",
                source=SOURCE_FIELD_PROFILE,
                steps=[
                    "Open this field from My Fields.",
                    "Tap Edit and look at where the pin is placed.",
                    "Move the pin if it is not on the field, then save.",
                ],
                check_first=["Check the pin is on the correct field."],
                avoid=["Do not confirm a pin that is on a different field."],
                done_when="The field says the location is confirmed.",
            )
        )
    elif not field.state:
        actions.append(
            _action(
                action_key="information:record_region",
                category=CATEGORY_INFORMATION,
                group_key=GROUP_DO_NEXT,
                title="Add the state or region of your field",
                explanation=(
                    "Some crops grow well only in certain areas. Adding your state "
                    "lets ANNADATA check this for your field."
                ),
                priority=PRIORITY_LOW,
                timing="Do this when you next edit the field.",
                reason="The field's state or region is not recorded.",
                source=SOURCE_FIELD_PROFILE,
                steps=[
                    "Open this field from My Fields and tap Edit.",
                    "Fill in the state or region.",
                    "Save the field.",
                ],
                check_first=["Choose the state where the field really is."],
                avoid=["Do not choose a nearby state if the field is somewhere else."],
                done_when="The field profile shows the correct state.",
            )
        )

    return actions


# --- Water -------------------------------------------------------------------


def _water_actions(field: Field) -> list[dict]:
    actions: list[dict] = []

    if field.water_availability is None:
        actions.append(
            _action(
                action_key="water:record_availability",
                category=CATEGORY_WATER,
                group_key=GROUP_DO_NEXT,
                title="Tell us how much water your field gets",
                explanation=(
                    "Crops need different amounts of water. When you tell us what "
                    "water you have, we can suggest crops that fit your field."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Do this when you next edit the field.",
                reason="Water availability has not been recorded for this field.",
                source=SOURCE_FIELD_PROFILE,
                steps=[
                    "Think about your main water source (rain, borewell, well, canal).",
                    "Open the field and tap Edit.",
                    "Choose your water source and how much water you usually have.",
                    "Save the field.",
                ],
                check_first=[
                    "Think about the dry season, not just the rainy season.",
                ],
                avoid=["Do not choose 'good' if the field often runs out of water."],
                done_when="The field profile shows your water source and how much water you have.",
            )
        )
    elif field.water_availability in _TIGHT_WATER:
        actions.append(
            _action(
                action_key="water:check_irrigation",
                category=CATEGORY_WATER,
                group_key=GROUP_DO_NEXT,
                title="Check if your crop needs watering before you water",
                explanation=(
                    "Water is limited or seasonal on this field. Before you water, "
                    "check a few simple things so you do not waste water or give the "
                    "crop more than it needs."
                ),
                priority=PRIORITY_LOW,
                timing="Check before you plan to water.",
                reason=(
                    "Water availability is recorded as limited or seasonal for this "
                    "field."
                ),
                source=SOURCE_FIELD_PROFILE,
                steps=[
                    "Push a finger or a stick about 5 cm into the soil.",
                    "If it feels dry, the crop may need water. If it feels damp, wait.",
                    "Check how much rain fell in the last few days.",
                    "Check the weather forecast for the next few days.",
                    "Look at the crop stage - young plants and flowering plants need water most.",
                    "If you are still unsure, ask your local agriculture officer.",
                ],
                materials=["A small stick or your finger", "The weather forecast in ANNADATA"],
                check_first=[
                    "Is the soil dry below the surface, not just on top?",
                    "Is rain expected soon?",
                    "What stage is the crop at?",
                ],
                avoid=[
                    "Do not water just because the top of the soil looks dry.",
                    "Do not use a fixed amount of water - it depends on your soil and crop.",
                ],
                done_when="You have checked the soil, rainfall, forecast and crop stage and then decided.",
            )
        )

    return actions


# --- Soil --------------------------------------------------------------------


def _soil_actions(soil: SoilContext) -> list[dict]:
    if not soil.has_measurement:
        return [
            _action(
                action_key="soil:add_test",
                category=CATEGORY_SOIL,
                group_key=GROUP_DO_NEXT,
                title="Get your soil tested and add the report",
                explanation=(
                    "A soil test shows whether your soil is acidic or alkaline (this "
                    "is what 'soil pH' means) and which nutrients it has. With this, "
                    "we can suggest the right crops and you can plan fertiliser better."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Best before sowing. You can also do it after harvest.",
                reason="No soil test has been recorded for this field.",
                source=SOURCE_SOIL,
                steps=[
                    "Collect soil from 5 to 6 different spots in the field.",
                    "Scrape away leaves and take soil from about 15 cm deep at each spot.",
                    "Mix all the soil together in a clean bucket.",
                    "Take about 500 g of the mixed soil in a clean cloth or bag.",
                    "Give it to your nearest soil testing lab, Krishi Vigyan Kendra "
                    "(KVK) or agriculture office, and ask for a Soil Health Card.",
                    "When the card arrives, open Soil Intelligence in ANNADATA.",
                    "Enter the pH, texture and nutrient values, or upload the card.",
                ],
                materials=[
                    "A clean bucket or cloth",
                    "A clean bag for the sample",
                    "The Soil Health Card form from your agriculture office",
                ],
                check_first=[
                    "Take the sample before adding fertiliser or manure.",
                    "Avoid sampling right after heavy rain or watering.",
                ],
                avoid=[
                    "Do not take soil from only one spot.",
                    "Do not send wet soil.",
                ],
                done_when="The soil test shows in Soil Intelligence with its test date.",
            )
        ]

    if soil.is_future:
        return [
            _action(
                action_key="soil:fix_test_date",
                category=CATEGORY_SOIL,
                group_key=GROUP_DO_NEXT,
                title="Correct the soil test date",
                explanation=(
                    "The soil test is dated in the future, so we cannot use it. Please "
                    "check the date and correct it."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Now.",
                reason="The latest soil test is dated in the future.",
                source=SOURCE_SOIL,
                steps=[
                    "Open Soil Intelligence and find the test.",
                    "Open the test and correct the test date.",
                    "Save it.",
                ],
                check_first=["Check the date printed on the report."],
                avoid=["Do not change the measured values, only the date."],
                done_when="The test date is today or in the past.",
            )
        ]

    if soil.is_stale:
        age = soil.age_days if soil.age_days is not None else "many"
        return [
            _action(
                action_key="soil:refresh_test",
                category=CATEGORY_SOIL,
                group_key=GROUP_DO_NEXT,
                title="Get a fresh soil test",
                explanation=(
                    "Your last soil test is old, so we do not use it to judge crops. "
                    "A new test brings your field's soil information up to date."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Before the next sowing season.",
                reason=f"The latest soil test is about {age} days old.",
                source=SOURCE_SOIL,
                steps=[
                    "Take a new soil sample the same way as before.",
                    "Give the sample to the soil testing lab or KVK.",
                    "When the card arrives, add or update the values in Soil Intelligence.",
                ],
                materials=["A clean sample bag", "The Soil Health Card form from your agriculture office"],
                check_first=["Use the same sampling method so results can be compared."],
                avoid=["Do not reuse the values from the old test."],
                done_when="A newer test shows in Soil Intelligence with a recent date.",
            )
        ]

    missing = [
        label
        for label, value in (("pH", soil.ph), ("texture", soil.texture))
        if value is None
    ]
    if missing:
        labels = ", ".join(missing)
        return [
            _action(
                action_key="soil:complete_record",
                category=CATEGORY_SOIL,
                group_key=GROUP_CHECK_LATER,
                title="Complete the missing soil test details",
                explanation=(
                    f"Your soil test is saved but it is missing {labels}. Adding this "
                    "gives us the full picture of your soil."
                ),
                priority=PRIORITY_LOW,
                timing="When you next open Soil Intelligence.",
                reason=f"The soil test does not include {labels}.",
                source=SOURCE_SOIL,
                steps=[
                    "Open the soil test in Soil Intelligence.",
                    f"Add the missing value(s): {labels}.",
                    "Save the test.",
                ],
                check_first=["Find the values on your Soil Health Card."],
                avoid=["Do not guess a value you cannot read on the card."],
                done_when="The soil test shows all the main values.",
            )
        ]

    return []


# --- Weather risks -----------------------------------------------------------

_WEATHER_TITLES = {
    C.RISK_KIND_HEAVY_RAIN: "Get the field ready before heavy rain",
    C.RISK_KIND_WET_SPELL: "Prepare for a wet spell",
    C.RISK_KIND_DRY_SPELL: "Plan for a dry spell",
}


def _weather_content(kind: str, crop: str, risk: dict) -> dict:
    detail = risk.get("detail") or ""
    if kind == C.RISK_KIND_HEAVY_RAIN:
        return {
            "explanation": (
                f"{detail} Heavy rain can flood low spots, wash away seed and make the "
                "soil too wet to work."
            ).strip(),
            "steps": [
                "Walk the field and note where water collects.",
                "Clear the drains and small channels so water can flow out.",
                "In low spots, make a small ridge or channel to guide water away.",
                "Wait until the soil drains before sowing or working the field.",
            ],
            "materials": ["A spade, hoe or crowbar for clearing drains"],
            "check_first": [
                "Where does water stand after heavy rain?",
                "Are the drains blocked with soil or weeds?",
            ],
            "avoid": [
                "Do not add fertiliser or manure just before heavy rain - it can wash away.",
                "Do not walk or drive on very wet soil.",
            ],
            "done_when": "Water can drain out and the low spots are clear.",
        }
    if kind == C.RISK_KIND_WET_SPELL:
        return {
            "explanation": (
                f"{detail} Several wet days can waterlog the soil and delay sowing or "
                "field work."
            ).strip(),
            "steps": [
                "Clear the drains so water does not stand.",
                "Wait for the soil to drain before sowing or adding anything to the soil.",
                "For rain-fed fields, this wet spell can be a good time to sow rain-fed crops.",
            ],
            "materials": ["A spade or hoe for clearing drains"],
            "check_first": ["Is the field well drained?"],
            "avoid": ["Do not work the soil while it is very wet."],
            "done_when": "The field drains well and you have adjusted your plans for the wet days.",
        }
    if kind == C.RISK_KIND_DRY_SPELL:
        return {
            "explanation": (
                f"{detail} Dry days can stress your crop, especially when it is young "
                "or flowering."
            ).strip(),
            "steps": [
                "Push a finger or a stick about 5 cm into the soil. If it is dry, the crop may need water.",
                "Check how much rain fell in the last few days.",
                "Check the weather forecast for the next few days.",
                "If you can water, do it in the early morning or evening, not in the hot afternoon.",
                "If you cannot water, keep a light mulch (dry leaves or straw) on the "
                "soil to hold moisture.",
            ],
            "materials": ["A small stick or your finger", "Dry leaves or straw for mulch"],
            "check_first": [
                "Is the soil dry below the surface, not just on top?",
                "What stage is the crop at - young or flowering plants need water most.",
                "Is rain expected soon?",
            ],
            "avoid": [
                "Do not water in the hot afternoon.",
                "Do not use a fixed amount of water - it depends on your soil and crop.",
            ],
            "done_when": "You have checked the soil, rain, forecast and crop stage and acted as needed.",
        }
    if kind == C.RISK_KIND_HEAT:
        return {
            "explanation": (
                f"{detail} Hot days can stress {crop}, especially around flowering."
            ).strip(),
            "steps": [
                "Water in the early morning or evening.",
                "Put a light mulch (dry leaves or straw) around the plants to keep the soil cool and moist.",
                "Avoid disturbing the plants during the hottest hours.",
            ],
            "materials": ["Dry leaves or straw for mulch"],
            "check_first": ["Check the forecast high for the next few days."],
            "avoid": ["Do not water in the hot afternoon."],
            "done_when": f"{crop.capitalize()} has water and soil cover during the hot days.",
        }
    if kind == C.RISK_KIND_COLD:
        return {
            "explanation": (
                f"{detail} Cold nights can slow germination and early growth for {crop}."
            ).strip(),
            "steps": [
                "Cover young plants at night with straw or a light cloth.",
                "Avoid watering late in the evening on cold nights.",
                "If the cold is expected to continue, delay sowing.",
            ],
            "materials": ["Straw or a light cloth to cover young plants"],
            "check_first": ["Check the forecast low for the next few nights."],
            "avoid": ["Do not leave young plants uncovered on cold nights."],
            "done_when": "Young plants are protected during the cold nights.",
        }
    return {
        "explanation": detail or "A weather risk was noted for your field.",
        "steps": None,
        "materials": None,
        "check_first": None,
        "avoid": None,
        "done_when": None,
    }


def _weather_actions(
    results: list[dict],
    *,
    weather_summary: Optional[dict],
    assessment_at: Optional[datetime],
) -> list[dict]:
    actions: list[dict] = []
    seen: set[str] = set()

    observed_at = (weather_summary or {}).get("observed_at")
    assessment_label = _date_label(assessment_at)

    for result in results:
        display_name = result.get("display_name")
        crop_id = result.get("crop_id")
        crop_label = display_name or "the crop"
        for risk in result.get("risks") or []:
            kind = risk.get("kind")
            if kind is None:
                continue
            # Heat/cold are tied to a crop's own temperature band; rainfall risks
            # apply to the field, so they are not repeated for every crop.
            scope = crop_id if kind in (C.RISK_KIND_HEAT, C.RISK_KIND_COLD) else "global"
            period = risk.get("period")
            key = f"weather:{kind}:{scope}:{period or 'window'}"
            if key in seen:
                continue
            seen.add(key)

            severity = risk.get("severity")
            high = severity == C.RISK_SEVERITY_HIGH
            content = _weather_content(kind, crop_label, risk)

            if kind in _WEATHER_TITLES:
                title = _WEATHER_TITLES[kind]
            elif kind == C.RISK_KIND_HEAT:
                title = f"Protect {crop_label} from heat"
            elif kind == C.RISK_KIND_COLD:
                title = f"Protect {crop_label} from cold"
            else:
                title = risk.get("title") or "Prepare for a weather risk"

            if observed_at:
                source = f"{risk.get('source') or C.WEATHER_SOURCE} forecast (issued {observed_at})"
            elif assessment_label:
                source = f"{risk.get('source') or C.WEATHER_SOURCE} forecast (from the {assessment_label} assessment)"
            else:
                source = f"{risk.get('source') or C.WEATHER_SOURCE} forecast"

            actions.append(
                _action(
                    action_key=key,
                    category=CATEGORY_WEATHER,
                    group_key=GROUP_DO_FIRST if high else GROUP_DO_NEXT,
                    title=title,
                    explanation=content["explanation"],
                    priority=PRIORITY_HIGH if high else PRIORITY_MEDIUM,
                    timing=period,
                    reason=risk.get("detail") or risk.get("basis") or "Noted by your latest assessment.",
                    source=source,
                    steps=content["steps"],
                    materials=content["materials"],
                    check_first=content["check_first"],
                    avoid=content["avoid"],
                    done_when=content["done_when"],
                    details={
                        "risk_kind": kind,
                        "severity": severity,
                        "basis": risk.get("basis"),
                        "issued_at": observed_at,
                    },
                )
            )

    return actions


# --- Crop --------------------------------------------------------------------


def top_suitable_crop(results: list[dict]) -> Optional[dict]:
    """The highest-scoring crop the latest assessment rated as suitable."""
    suitable = [r for r in results if r.get("status") == C.STATUS_SUITABLE]
    if not suitable:
        return None
    suitable.sort(key=lambda r: (-(r.get("score") or 0.0), r.get("display_name") or ""))
    return suitable[0]


def _missing_recordable_labels(result: dict) -> list[str]:
    labels: list[str] = []
    for factor, detail in (result.get("factors") or {}).items():
        if factor not in _RECORDABLE_FACTORS:
            continue
        if detail.get("status") == "missing_input":
            labels.append(detail.get("label") or factor)
    return labels


def _crop_actions(results: list[dict], *, assessment_at: Optional[datetime]) -> list[dict]:
    top = top_suitable_crop(results)
    if top is None:
        return []

    crop_id = top.get("crop_id")
    crop_name = top.get("display_name") or "your top crop"
    score = top.get("score") or 0.0
    preliminary = bool(top.get("preliminary"))
    assessment_label = _date_label(assessment_at)

    if preliminary:
        missing = _missing_recordable_labels(top)
        missing_text = ", ".join(missing) if missing else "some details"
        return [
            _action(
                action_key=f"crop:check:{crop_id}",
                category=CATEGORY_CROP,
                group_key=GROUP_DO_NEXT,
                title=f"Add the missing details for {crop_name}",
                explanation=(
                    f"Our estimate says {crop_name} could suit your field, but some "
                    "information is missing, so this is only a first guess. Adding the "
                    "missing details will give you a clearer answer."
                ),
                priority=PRIORITY_MEDIUM,
                timing="Before you decide on the crop.",
                reason=f"{crop_name} scored {score * 100:.0f}% but some details are missing.",
                source=SOURCE_ASSESSMENT,
                steps=[
                    f"Add the missing details listed below ({missing_text}).",
                    "Run the crop assessment again on the Crop Recommendations page.",
                    "Compare the new result with this one before deciding.",
                ],
                check_first=[f"Missing details: {missing_text}."],
                avoid=["Do not treat this first guess as a final answer."],
                done_when="The crop assessment no longer shows these details as missing.",
                details={
                    "crop_id": crop_id,
                    "preliminary": True,
                    "missing_factors": missing,
                    "assessment_at": assessment_label,
                },
            )
        ]

    return [
        _action(
            action_key=f"crop:confirm:{crop_id}",
            category=CATEGORY_CROP,
            group_key=GROUP_CHECK_LATER,
            title=f"Confirm {crop_name} with your local expert",
            explanation=(
                f"Our estimate says {crop_name} suits your field well. A local "
                "agriculture officer knows your area's soil and weather, so check the "
                "plan with them before you buy seed."
            ),
            priority=PRIORITY_LOW,
            timing="Before you buy seed or plan the season.",
            reason=f"{crop_name} scored {score * 100:.0f}% on the latest assessment.",
            source=SOURCE_ASSESSMENT,
            steps=[
                "Note the crop and the score shown in the assessment.",
                "Visit or call your local agriculture officer or KVK.",
                "Ask whether the crop and its timing suit your area and your water.",
                "Buy seed only after this check.",
            ],
            materials=["Your crop assessment result from ANNADATA"],
            check_first=["Make sure the seed you plan to buy matches the season."],
            avoid=["Do not change your whole farm based on one estimate."],
            done_when="You have confirmed the crop with your local expert.",
            details={
                "crop_id": crop_id,
                "preliminary": False,
                "assessment_at": assessment_label,
            },
        )
    ]


def _assessment_action() -> list[dict]:
    return [
        _action(
            action_key="monitoring:run_assessment",
            category=CATEGORY_CROP,
            group_key=GROUP_DO_FIRST,
            title="Run a crop assessment",
            explanation=(
                "This is the first step. The assessment checks every crop against "
                "your field, soil, water and weather. Once it is done, this page will "
                "show your full action plan."
            ),
            priority=PRIORITY_LOW,
            timing="Do this first.",
            reason="No crop assessment has been run for this field yet.",
            source=SOURCE_RECOMMENDATIONS,
            steps=[
                "Open the Crop Recommendations page.",
                "Choose this field.",
                "Press 'Run recommendations'.",
                "Come back to the Action Planner.",
            ],
            check_first=[
                "Make sure the field's location and water details are filled in first.",
            ],
            avoid=["Do not expect a full plan before an assessment is run."],
            done_when="The Crop Recommendations page shows crop results.",
        )
    ]


def build_actions(
    field: Field,
    soil: SoilContext,
    results: Optional[list[dict]] = None,
    *,
    weather_summary: Optional[dict] = None,
    assessment_at: Optional[datetime] = None,
) -> list[dict]:
    """Return the practical steps supported by the recorded data.

    ``results`` are the crop evaluations from the most recent assessment batch
    (empty when no assessment has run). ``weather_summary`` and ``assessment_at``
    come from that same batch so weather steps can show the forecast's issue time.
    Nothing is added that the data does not support.
    """
    results = results or []

    actions: list[dict] = []
    actions.extend(_location_actions(field))
    actions.extend(_water_actions(field))
    actions.extend(_soil_actions(soil))

    if results:
        actions.extend(
            _weather_actions(
                results, weather_summary=weather_summary, assessment_at=assessment_at
            )
        )
        actions.extend(_crop_actions(results, assessment_at=assessment_at))
    else:
        actions.extend(_assessment_action())

    return actions


__all__ = [
    "PLANNER_VERSION",
    "ACTION_DISCLAIMER",
    "build_actions",
    "top_suitable_crop",
]
