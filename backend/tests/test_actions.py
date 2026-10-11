"""Smart Farming Action Planner tests.

Covers: authentication, per-user field ownership, generation from incomplete and
complete data, weather-risk derivation from the latest assessment, persistence of
completion (including survival across a refresh), reopening, and the guarantee
that regeneration never invents or deletes steps.
"""

from datetime import date

import pytest

from app.services.weather_service import WeatherSnapshot
from tests.conftest import VALID_FIELD, auth_headers, fresh_email, register_user

TODAY = date.today().isoformat()


def make_field(client, headers, **overrides):
    payload = dict(VALID_FIELD)
    payload.update(overrides)
    r = client.post("/api/fields", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def register_with_field(client, **field_overrides):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    field = make_field(client, headers, **field_overrides)
    return email, headers, field


def add_soil(client, headers, field_id, **overrides):
    payload = {"tested_on": TODAY, "test_source": "Govt lab", "ph": 6.8, "texture": "loam"}
    payload.update(overrides)
    r = client.post(
        f"/api/fields/{field_id}/soil/measurements", json=payload, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


def keys(plan):
    return {a["action_key"] for a in plan["actions"]}


@pytest.fixture()
def heavy_rain(monkeypatch):
    """Patch live weather with a deterministic heavy-rain forecast."""
    days = [
        {"time": "2026-10-11", "precipitation_sum": 120.0,
         "temperature_2m_max": 31.0, "temperature_2m_min": 22.0},
        {"time": "2026-10-12", "precipitation_sum": 4.0,
         "temperature_2m_max": 30.0, "temperature_2m_min": 21.0},
    ]
    snapshot = WeatherSnapshot(
        source="Open-Meteo", latitude=12.9716, longitude=77.5946,
        observed_at="2026-10-11T06:00", daily=days,
    )

    async def _fetch(latitude, longitude):
        return snapshot

    from app.services import weather_service

    monkeypatch.setattr(weather_service, "fetch_full_weather", _fetch)


# --- Authentication & ownership ---------------------------------------------


def test_action_endpoints_require_auth(client):
    assert client.get("/api/fields/1/actions").status_code == 401
    assert client.post("/api/fields/1/actions/refresh").status_code == 401
    assert client.patch("/api/fields/1/actions/1", json={"completed": True}).status_code == 401


def test_field_ownership_is_enforced(client):
    _, owner_headers, field = register_with_field(client)

    other_email = fresh_email()
    register_user(client, email=other_email)
    other_headers = auth_headers(client, other_email)

    assert client.get(f"/api/fields/{field['id']}/actions", headers=other_headers).status_code == 404
    assert (
        client.post(f"/api/fields/{field['id']}/actions/refresh", headers=other_headers).status_code
        == 404
    )

    # The owner can read their own plan, then cannot touch another user's action.
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=owner_headers).json()
    action_id = plan["actions"][0]["id"]
    assert (
        client.patch(
            f"/api/fields/{field['id']}/actions/{action_id}",
            json={"completed": True},
            headers=other_headers,
        ).status_code
        == 404
    )


# --- Generation on incomplete data ------------------------------------------


def test_incomplete_data_yields_information_steps(client):
    _, headers, field = register_with_field(client)

    r = client.get(f"/api/fields/{field['id']}/actions", headers=headers)
    assert r.status_code == 200, r.text
    plan = r.json()

    assert plan["field_id"] == field["id"]
    assert plan["field_name"] == field["field_name"]
    assert plan["has_assessment"] is False
    assert plan["planner_version"]
    assert plan["disclaimer"]
    assert len(plan["actions"]) >= 1

    present = keys(plan)
    # No soil test -> a soil information step; no assessment -> a run-assessment step.
    assert "soil:add_test" in present
    assert "monitoring:run_assessment" in present
    # VALID_FIELD has coordinates confirmed and water recorded, so no such gaps.
    assert "information:confirm_location" not in present
    assert "water:record_availability" not in present

    soil_step = next(a for a in plan["actions"] if a["action_key"] == "soil:add_test")
    assert soil_step["category"] == "soil"
    assert soil_step["priority"] == "medium"
    assert soil_step["completed"] is False
    assert soil_step["completed_at"] is None
    assert soil_step["source"] == "Soil Intelligence"
    # Rich, plain-language detail is present and grouped.
    assert soil_step["group_key"] == "do_next"
    assert isinstance(soil_step["steps"], list) and len(soil_step["steps"]) >= 3
    assert isinstance(soil_step["check_first"], list)
    assert isinstance(soil_step["avoid"], list)
    assert soil_step["done_when"]
    assert "acidic or alkaline" in soil_step["explanation"]


def test_missing_water_is_flagged(client):
    _, headers, field = register_with_field(client, water_source=None, water_availability=None)
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    present = keys(plan)
    assert "water:record_availability" in present
    # Location is confirmed and coordinates are present, so no location step.
    assert "information:confirm_location" not in present


def test_tight_water_adds_a_check_before_watering_step(client):
    _, headers, field = register_with_field(
        client, water_source="rain_fed", water_availability="seasonal"
    )
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    by_key = {a["action_key"]: a for a in plan["actions"]}
    # Water is recorded, so the "record availability" step is gone, but a
    # conservative "check before you water" step is offered instead.
    assert "water:record_availability" not in by_key
    assert "water:check_irrigation" in by_key
    step = by_key["water:check_irrigation"]
    assert step["group_key"] == "do_next"
    # It never tells the farmer to water or gives an amount.
    text = (
        f"{step['title']} {step['explanation']} "
        f"{' '.join(step['steps'])} {' '.join(step['avoid'])}"
    ).lower()
    assert "do not use a fixed amount" in text



def test_build_actions_flags_missing_location_and_water():
    from app.decision_engine.action_planner import build_actions
    from app.decision_engine.soil_context import SoilContext
    from app.models.field import Field

    field = Field(
        field_name="Legacy",
        latitude=None,
        longitude=None,
        location_confirmed=False,
        state=None,
        water_source=None,
        water_availability=None,
    )
    actions = build_actions(field, SoilContext(has_measurement=False), [])
    present = {a["action_key"] for a in actions}
    assert "information:confirm_location" in present
    assert "water:record_availability" in present
    assert "soil:add_test" in present
    assert "monitoring:run_assessment" in present


# --- Completion lifecycle ----------------------------------------------------


def test_complete_persist_and_reopen(client):
    _, headers, field = register_with_field(client)
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    action = plan["actions"][0]

    done = client.patch(
        f"/api/fields/{field['id']}/actions/{action['id']}",
        json={"completed": True},
        headers=headers,
    )
    assert done.status_code == 200, done.text
    body = done.json()
    assert body["completed"] is True
    assert body["completed_at"] is not None
    assert body["action_key"] == action["action_key"]

    # A fresh read keeps the completion (it is persisted, never auto-reset).
    again = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    stored = next(a for a in again["actions"] if a["id"] == action["id"])
    assert stored["completed"] is True

    # Reopen.
    reopened = client.patch(
        f"/api/fields/{field['id']}/actions/{action['id']}",
        json={"completed": False},
        headers=headers,
    ).json()
    assert reopened["completed"] is False
    assert reopened["completed_at"] is None


def test_completion_survives_refresh_without_duplicating(client):
    _, headers, field = register_with_field(client)
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    action = next(a for a in plan["actions"] if a["action_key"] == "soil:add_test")

    client.patch(
        f"/api/fields/{field['id']}/actions/{action['id']}",
        json={"completed": True},
        headers=headers,
    )

    refreshed = client.post(f"/api/fields/{field['id']}/actions/refresh", headers=headers).json()
    matching = [a for a in refreshed["actions"] if a["action_key"] == "soil:add_test"]
    assert len(matching) == 1  # no duplicate row
    assert matching[0]["completed"] is True  # completion preserved
    # No duplicate action keys overall.
    all_keys = [a["action_key"] for a in refreshed["actions"]]
    assert len(all_keys) == len(set(all_keys))


def test_regeneration_keeps_completed_step_when_data_changes(client):
    """A completed step stays for review even after the underlying gap is fixed."""
    _, headers, field = register_with_field(client)
    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    soil_step = next(a for a in plan["actions"] if a["action_key"] == "soil:add_test")
    client.patch(
        f"/api/fields/{field['id']}/actions/{soil_step['id']}",
        json={"completed": True},
        headers=headers,
    )

    # Now record a soil test, which means the gap no longer exists in a fresh plan.
    add_soil(client, headers, field["id"])
    refreshed = client.post(f"/api/fields/{field['id']}/actions/refresh", headers=headers).json()
    stored = next(a for a in refreshed["actions"] if a["action_key"] == "soil:add_test")
    assert stored["completed"] is True  # kept for review, never deleted


# --- Assessment-driven steps -------------------------------------------------


def test_weather_risk_becomes_a_step(client, heavy_rain):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])

    gen = client.post(
        f"/api/fields/{field['id']}/crops/recommendations", json={}, headers=headers
    )
    assert gen.status_code == 201, gen.text

    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    assert plan["has_assessment"] is True

    heavy = [a for a in plan["actions"] if a["action_key"].startswith("weather:heavy_rain")]
    assert heavy, plan["actions"]
    assert heavy[0]["category"] == "weather"
    assert heavy[0]["priority"] == "high"  # 120 mm is a high-severity risk
    assert heavy[0]["timing"] == "2026-10-11"
    assert "Open-Meteo" in heavy[0]["source"]


def test_build_actions_from_crafted_results():
    """The pure generator is deterministic and derives steps only from inputs."""
    from app.decision_engine.action_planner import build_actions
    from app.decision_engine.soil_context import SoilContext
    from app.models.field import Field

    field = Field(
        field_name="Test",
        latitude=12.9,
        longitude=77.5,
        location_confirmed=True,
        state="Karnataka",
        water_source="rain_fed",
        water_availability="seasonal",
    )
    results = [
        {
            "crop_id": 7,
            "display_name": "Ragi",
            "status": "suitable",
            "score": 0.8,
            "preliminary": False,
            "risks": [
                {
                    "kind": "heavy_rain",
                    "severity": "high",
                    "title": "Heavy rain expected",
                    "detail": "110 mm is forecast for 2026-10-11.",
                    "basis": "Daily precipitation ≥ 50 mm",
                    "period": "2026-10-11",
                    "source": "Open-Meteo",
                },
                {
                    "kind": "heat",
                    "severity": "medium",
                    "title": "Heat above Ragi's range",
                    "detail": "High of 35C on 2026-10-11.",
                    "basis": "Forecast daily max ≥ upper band",
                    "period": "2026-10-11",
                    "source": "Open-Meteo",
                },
            ],
        }
    ]
    actions = build_actions(field, SoilContext(has_measurement=False), results)
    by_key = {a["action_key"]: a for a in actions}

    # The no-soil gap, the high-risk rainfall step and the crop review are all present.
    assert "soil:add_test" in by_key
    assert "weather:heavy_rain:global:2026-10-11" in by_key
    assert by_key["weather:heavy_rain:global:2026-10-11"]["priority"] == "high"
    assert "weather:heat:7:2026-10-11" in by_key
    assert by_key["weather:heat:7:2026-10-11"]["priority"] == "medium"
    assert "crop:confirm:7" in by_key
    # No assessment step once results exist.
    assert "monitoring:run_assessment" not in by_key

    # Grouping: high-severity forecast risks are "Do first"; medium weather and
    # the crop confirmation are lower down.
    assert by_key["weather:heavy_rain:global:2026-10-11"]["group_key"] == "do_first"
    assert by_key["weather:heat:7:2026-10-11"]["group_key"] == "do_next"
    assert by_key["crop:confirm:7"]["group_key"] == "check_later"


def test_preliminary_crop_gets_a_missing_details_step():
    """A preliminary crop asks for the missing information instead of confirming."""
    from app.decision_engine.action_planner import build_actions
    from app.decision_engine.soil_context import SoilContext
    from app.models.field import Field

    field = Field(
        field_name="Test",
        latitude=12.9,
        longitude=77.5,
        location_confirmed=True,
        state="Karnataka",
        water_source="rain_fed",
        water_availability="good",
    )
    results = [
        {
            "crop_id": 7,
            "display_name": "Ragi",
            "status": "suitable",
            "score": 0.7,
            "preliminary": True,
            "risks": [],
            "factors": {
                "ph": {"factor": "ph", "label": "Soil pH", "status": "evaluated"},
                "water": {
                    "factor": "water",
                    "label": "Water availability",
                    "status": "missing_input",
                },
            },
        }
    ]
    actions = build_actions(field, SoilContext(has_measurement=False), results)
    by_key = {a["action_key"]: a for a in actions}
    assert "crop:confirm:7" not in by_key
    assert "crop:check:7" in by_key
    step = by_key["crop:check:7"]
    assert step["group_key"] == "do_next"
    assert "Water availability" in step["check_first"][0]




def test_no_fertiliser_or_pesticide_doses_are_ever_generated(client, heavy_rain):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    client.post(f"/api/fields/{field['id']}/crops/recommendations", json={}, headers=headers)

    plan = client.get(f"/api/fields/{field['id']}/actions", headers=headers).json()
    text = " ".join(
        f"{a['title']} {a['explanation']} {a['reason']}" for a in plan["actions"]
    ).lower()
    for forbidden in ("kg/", "kg per", "litre", "liter", "ml/", "dose", "spray", "pesticide", "fungicide"):
        assert forbidden not in text, forbidden
