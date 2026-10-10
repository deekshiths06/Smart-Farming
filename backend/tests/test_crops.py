"""Crop Intelligence tests: knowledge base, scoring, ranking, risks, history.

Deterministic fixtures are used for everything except the explicitly
``@pytest.mark.network`` live-weather test, so results never depend on the
weather of the day.
"""

from datetime import date, timedelta

import pytest

from app.decision_engine import constants as C
from app.decision_engine import scoring, weather_risk
from app.decision_engine.recommendation import load_config
from app.schemas.crop import validate_requirement
from app.services.weather_service import WeatherServiceError, WeatherSnapshot
from tests.conftest import VALID_FIELD, auth_headers, fresh_email, register_user

TODAY = date.today().isoformat()
STALE = (date.today() - timedelta(days=1500)).isoformat()
FUTURE = (date.today() + timedelta(days=30)).isoformat()

VALID_STATUSES = {"suitable", "not_recommended", "needs_information"}
SCORED_FACTORS = ("ph", "texture", "water", "season")


# --- Helpers ----------------------------------------------------------------


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


def promote_to_admin(email):
    from app.database.session import SessionLocal
    from app.models.user import ROLE_ADMIN, User

    session = SessionLocal()
    try:
        session.query(User).filter(User.email == email).update({"role": ROLE_ADMIN})
        session.commit()
    finally:
        session.close()


def forecast(daily=None, observed_at="2026-10-10T12:00"):
    """A deterministic Open-Meteo-shaped snapshot."""
    days = daily if daily is not None else [
        {"time": f"2026-10-{10 + i:02d}", "precipitation_sum": 8.0,
         "temperature_2m_max": 30.0, "temperature_2m_min": 21.0}
        for i in range(7)
    ]
    return WeatherSnapshot(
        source="Open-Meteo",
        latitude=12.9716,
        longitude=77.5946,
        observed_at=observed_at,
        daily=days,
    )


@pytest.fixture(autouse=True)
def fake_weather(request, monkeypatch):
    """Patch live weather for every test except the ones marked ``network``."""
    if request.node.get_closest_marker("network"):
        yield None
        return

    state = {"snapshot": forecast(), "error": None}

    async def _fetch(latitude, longitude):
        if state["error"] is not None:
            raise state["error"]
        return state["snapshot"]

    from app.services import weather_service

    monkeypatch.setattr(weather_service, "fetch_full_weather", _fetch)
    yield state


def generate(client, headers, field_id):
    r = client.post(
        f"/api/fields/{field_id}/crops/recommendations", json={}, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- Authentication ---------------------------------------------------------


def test_crop_endpoints_require_auth(client):
    assert client.get("/api/crops").status_code == 401
    assert client.get("/api/crops/1").status_code == 401
    assert client.post("/api/fields/1/crops/recommendations", json={}).status_code == 401
    assert client.post("/api/fields/1/crops/compare", json={"crop_ids": [1]}).status_code == 401
    assert client.get("/api/fields/1/crops/recommendations").status_code == 401
    assert client.get("/api/fields/1/crops/recommendations/1").status_code == 401
    assert client.get("/api/fields/1/crops/recommendations/batches/abc").status_code == 401


def test_field_ownership_is_enforced(client):
    _, owner_headers, field = register_with_field(client)

    other_email = fresh_email()
    register_user(client, email=other_email)
    other_headers = auth_headers(client, other_email)

    assert (
        client.post(
            f"/api/fields/{field['id']}/crops/recommendations", json={}, headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/fields/{field['id']}/crops/recommendations", headers=other_headers)
        .status_code
        == 404
    )
    assert (
        client.post(
            f"/api/fields/{field['id']}/crops/compare",
            json={"crop_ids": [1]},
            headers=other_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/fields/{field['id']}/crops/recommendations/1", headers=other_headers)
        .status_code
        == 404
    )
    # The owner can still reach their own field.
    assert (
        client.get(f"/api/fields/{field['id']}/crops/recommendations", headers=owner_headers)
        .status_code
        == 200
    )


# --- Knowledge base ---------------------------------------------------------


def test_knowledge_base_is_seeded_documented_and_read_only(client):
    _, headers, _ = register_with_field(client)

    r = client.get("/api/crops", headers=headers)
    assert r.status_code == 200, r.text
    crops = r.json()
    assert len(crops) >= 10
    for crop in crops:
        assert crop["source"], crop["name"]
        assert crop["date_reviewed"], crop["name"]
        assert crop["is_active"] is True

    names = {c["name"] for c in crops}
    assert {"rice", "maize", "wheat", "cotton"} <= names

    detail = client.get(f"/api/crops/{crops[0]['id']}", headers=headers).json()
    assert detail["requirements"], "every crop should document requirements"
    factors = {r_["factor"] for r_ in detail["requirements"]}
    assert {"ph", "water"} <= factors
    for req in detail["requirements"]:
        assert req["source"], req
        assert req["explanation"] is not None, req["factor"]
        assert req["factor_label"] and req["factor_label"] != req["factor"]


def test_unknown_crop_is_404(client):
    _, headers, _ = register_with_field(client)
    assert client.get("/api/crops/999999", headers=headers).status_code == 404


def test_farmers_cannot_modify_knowledge_base_or_config(client):
    _, headers, _ = register_with_field(client)
    assert client.get("/api/admin/crops", headers=headers).status_code == 403
    assert client.post("/api/admin/crops", json={}, headers=headers).status_code == 403
    assert client.put("/api/admin/crops/1", json={}, headers=headers).status_code == 403
    assert client.get("/api/admin/crop-scoring-config", headers=headers).status_code == 403
    assert (
        client.put("/api/admin/crop-scoring-config", json={}, headers=headers).status_code
        == 403
    )
    assert client.post("/api/admin/crops/1/requirements", json={}, headers=headers).status_code == 403
    assert client.put("/api/admin/requirements/1", json={}, headers=headers).status_code == 403
    assert client.delete("/api/admin/requirements/1", headers=headers).status_code == 403


# --- Requirement validation -------------------------------------------------


def test_requirement_validation_rules():
    # Numeric factors need a band and must not carry categorical values.
    with pytest.raises(ValueError):
        validate_requirement("ph", None, None, None)
    with pytest.raises(ValueError):
        validate_requirement("ph", 6.5, 5.5, None)
    with pytest.raises(ValueError):
        validate_requirement("ph", 5.5, 6.5, ["loam"])
    # Categorical factors need values from the documented vocabulary.
    with pytest.raises(ValueError):
        validate_requirement("texture", 1.0, 2.0, None)
    with pytest.raises(ValueError):
        validate_requirement("texture", None, None, None)
    with pytest.raises(ValueError):
        validate_requirement("texture", None, None, ["loam", "rock"])
    with pytest.raises(ValueError):
        validate_requirement("water", None, None, ["thirsty"])
    with pytest.raises(ValueError):
        validate_requirement("season", None, None, ["summer"])
    # Valid shapes do not raise.
    validate_requirement("ph", 5.5, 6.5, None)
    validate_requirement("ph", 6.0, None, None)  # open upper band
    validate_requirement("texture", None, None, ["loam", "clay"])
    validate_requirement("water", None, None, ["low"])
    validate_requirement("season", None, None, ["kharif", "rabi"])
    validate_requirement("region", None, None, ["Karnataka"])


def test_admin_requirement_api_rejects_invalid_payload(client):
    email = fresh_email()
    register_user(client, email=email)
    promote_to_admin(email)
    headers = auth_headers(client, email)

    crop_id = client.get("/api/admin/crops", headers=headers).json()[0]["id"]

    bad = client.post(
        f"/api/admin/crops/{crop_id}/requirements",
        json={"factor": "ph", "allowed_values": ["loam"], "source": "Test"},
        headers=headers,
    )
    assert bad.status_code == 422, bad.text

    bad_factor = client.post(
        f"/api/admin/crops/{crop_id}/requirements",
        json={"factor": "yield", "min_value": 1, "max_value": 2, "source": "Test"},
        headers=headers,
    )
    assert bad_factor.status_code == 422, bad_factor.text

    duplicate = client.post(
        f"/api/admin/crops/{crop_id}/requirements",
        json={"factor": "ph", "min_value": 5.0, "max_value": 6.0, "source": "Test"},
        headers=headers,
    )
    assert duplicate.status_code == 409, duplicate.text


# --- Scoring primitives -----------------------------------------------------


def test_range_score_inside_outside_and_open_bands():
    assert scoring.range_score(6.0, 5.5, 6.5, "ph") == 1.0
    assert scoring.range_score(None, 5.5, 6.5, "ph") is None
    assert scoring.range_score(6.0, None, None, "ph") is None
    # Half a band-width outside -> 0.5, far outside -> clamped at 0.
    assert scoring.range_score(7.0, 5.5, 6.5, "ph") == pytest.approx(0.5)
    assert scoring.range_score(12.0, 5.5, 6.5, "ph") == 0.0
    # Open bands use the documented fallback span.
    assert scoring.range_score(9.0, 6.0, None, "ph") == 1.0
    assert scoring.range_score(5.25, 6.0, None, "ph") == pytest.approx(0.5)
    assert scoring.range_score(30.0, None, 25.0, "temperature") == pytest.approx(0.0)


def test_water_score_credit_shortfall_and_rainfed_penalty():
    assert scoring.water_score("good", "high", "borewell") == 1.0
    assert scoring.water_score("moderate", "medium", "borewell") == 1.0
    # 0.5 provision against a 0.6 need -> 0.833...
    assert scoring.water_score("seasonal", "medium", "borewell") == pytest.approx(0.5 / 0.6)
    # A rain-fed field with a high-water crop takes the documented penalty.
    assert scoring.water_score("good", "high", "rain_fed") == pytest.approx(0.7)
    assert scoring.water_score("good", "high", "canal") == 1.0
    assert scoring.water_score(None, "high", None) is None
    assert scoring.water_score("nonsense", "high", None) is None


def test_texture_score_exact_group_and_other():
    assert scoring.texture_score("loam", ["loam", "clay"]) == 1.0
    # Same USDA textural group (medium): silt_loam and loam.
    assert scoring.texture_score("silt_loam", ["loam"]) == pytest.approx(0.5)
    # Different groups: clay (fine) against loam (medium).
    assert scoring.texture_score("clay", ["loam"]) == pytest.approx(0.15)
    assert scoring.texture_score("other", ["loam"]) is None
    assert scoring.texture_score(None, ["loam"]) is None
    assert scoring.texture_score("loam", None) is None


def test_season_and_region_scores():
    assert scoring.season_score(7, ["kharif"]) == 1.0  # July -> kharif
    assert scoring.season_score(7, ["rabi"]) == 0.0
    assert scoring.season_score(7, None) is None
    assert scoring.region_score("Karnataka", ["Karnataka"]) == 1.0
    assert scoring.region_score("Kerala", ["Karnataka"]) == 0.0
    assert scoring.region_score(None, ["Karnataka"]) is None
    assert scoring.region_score("Karnataka", None) is None


def test_load_config_falls_back_to_documented_defaults(db):
    config = load_config(db)
    assert config["weights"] == dict(C.DEFAULT_WEIGHTS)
    assert list(config["essential_factors"]) == list(C.DEFAULT_ESSENTIAL_FACTORS)
    assert config["suitable_threshold"] == C.DEFAULT_SUITABLE_THRESHOLD
    assert 0.0 < config["min_coverage"] <= 1.0
    assert config["stale_soil_days"] > 0


# --- Generation, ranking, insufficient data ---------------------------------


def test_generate_without_soil_uses_available_evidence(client):
    _, headers, field = register_with_field(client)
    body = generate(client, headers, field["id"])

    results = body["results"]
    assert results, "every active crop should be evaluated"
    assert body["disclaimer"]
    assert body["season"] in C.SEASONS

    for result in results:
        assert result["status"] in VALID_STATUSES
        factors = result["factors"]
        # A missing soil test is a reported gap, never a reason to refuse.
        assert factors["ph"]["status"] == "missing_input"
        assert factors["texture"]["status"] == "missing_input"
        assert factors["ph"]["input"] is None
        assert factors["texture"]["input"] is None
        assert factors["water"]["status"] == "evaluated"  # the field records water
        # The crop is still scored on the evidence that exists, as preliminary.
        assert result["score"] is not None and 0.0 <= result["score"] <= 1.0
        assert result["preliminary"] is True
        assert result["reasons"], "every result explains itself"
        assert result["next_steps"], "every result suggests next actions"
        assert any("soil test" in step for step in result["next_steps"])

    # The engine never invents pH/texture, but it also never hides every crop
    # behind "needs more information": season-appropriate crops are recommended
    # from the recorded water + location/season evidence, sized by season.
    assert any(r["status"] == C.STATUS_SUITABLE for r in results)
    # A crop out of the current season is genuinely not recommended right now.
    assert any(r["status"] == C.STATUS_NOT_RECOMMENDED for r in results)


def test_generate_with_full_data_scores_and_ranks(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"], ph=6.8, texture="loam")
    body = generate(client, headers, field["id"])

    results = body["results"]
    assert body["soil"]["has_measurement"] is True
    assert body["soil"]["tested_on"] == TODAY

    for result in results:
        factors = result["factors"]
        # The four scored factors have real inputs now.
        for factor in SCORED_FACTORS:
            assert factors[factor]["status"] == "evaluated", (result["crop_name"], factor)
            assert factors[factor]["input"] is not None
            assert 0.0 <= factors[factor]["score"] <= 1.0
        assert result["coverage"] == pytest.approx(1.0)
        assert result["score"] is not None
        assert result["status"] in VALID_STATUSES
        assert 0.0 <= result["score"] <= 1.0
        # Complete data means the verdict is a full one, not preliminary.
        assert result["preliminary"] is False

    # Ranking: suitable first, then needs_information, then not recommended;
    # inside a status, higher scores come first.
    order = {C.STATUS_SUITABLE: 0, C.STATUS_NEEDS_INFO: 1, C.STATUS_NOT_RECOMMENDED: 2}
    keys = [
        (order[r["status"]], -(r["score"] or 0.0), r["display_name"]) for r in results
    ]
    assert keys == sorted(keys)

    # At least one crop matches this field and season - evidence, not a guess.
    assert any(r["status"] == C.STATUS_SUITABLE for r in results)


def test_missing_water_recorded_is_reported_not_guessed(client):
    _, headers, field = register_with_field(client, water_availability=None)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    for result in body["results"]:
        assert result["factors"]["water"]["status"] == "missing_input"
        assert result["factors"]["water"]["input"] is None
        assert result["status"] in VALID_STATUSES
        assert any("water availability" in step for step in result["next_steps"])

    # Water is reported as missing, never invented - and its absence is a gap,
    # not a red verdict. The soil + season evidence is still scored, so crops
    # are not left hanging under "needs more information".
    assert any(r["status"] == C.STATUS_SUITABLE for r in body["results"])


def test_stale_soil_measurement_is_excluded_with_note(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"], tested_on=STALE, ph=5.0, texture="clay")
    body = generate(client, headers, field["id"])

    assert body["soil"]["is_stale"] is True
    assert any("older than" in note for note in body["notes"])
    for result in body["results"]:
        assert result["factors"]["ph"]["status"] == "missing_input"
        # The stale soil test is excluded with a note, but the crop is still
        # scored on the other recorded evidence - just flagged as preliminary.
        assert result["preliminary"] is True
        assert any("Refresh the soil test" in step for step in result["next_steps"])


def test_future_dated_soil_measurement_is_ignored(client, db):
    from app.models.soil import SoilMeasurement
    from app.models.user import User

    email, headers, field = register_with_field(client)
    owner = db.query(User).filter(User.email == email).first()
    db.add(
        SoilMeasurement(
            field_id=field["id"],
            user_id=owner.id,
            tested_on=date.today() + timedelta(days=30),
            ph=6.2,
            texture="loam",
            source_kind="farmer_entered",
        )
    )
    db.commit()

    body = generate(client, headers, field["id"])
    assert body["soil"]["is_future"] is True
    assert any("future" in note for note in body["notes"])
    for result in body["results"]:
        assert result["factors"]["ph"]["status"] == "missing_input"
        assert result["preliminary"] is True


def test_partial_manual_soil_is_scored_as_preliminary(client):
    _, headers, field = register_with_field(client)
    # Only pH is recorded - no texture. The engine uses pH and keeps texture
    # as a flagged gap rather than refusing to score the crop.
    add_soil(client, headers, field["id"], ph=6.8, texture=None)
    body = generate(client, headers, field["id"])

    results = body["results"]
    assert body["soil"]["has_measurement"] is True
    assert any(r["status"] == C.STATUS_SUITABLE for r in results)
    for result in results:
        assert result["status"] in VALID_STATUSES
        assert result["factors"]["ph"]["status"] == "evaluated"
        assert result["factors"]["texture"]["status"] == "missing_input"
        assert result["preliminary"] is True
        assert any("soil test" in step for step in result["next_steps"])


def test_crop_out_of_season_is_not_recommended_even_with_perfect_soil(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    current = C.season_for_month(date.today().month)
    mismatched = [
        result
        for result in body["results"]
        if current
        not in (result["factors"]["season"]["requirement"].get("allowed_values") or [])
    ]
    assert mismatched, "every month has at least one crop out of season"
    for result in mismatched:
        # Good soil and water never override a hard season mismatch: the crop
        # is genuinely not the one to plant right now.
        assert result["status"] == C.STATUS_NOT_RECOMMENDED
        assert any("Season" in reason for reason in result["reasons"])


def test_no_soil_and_no_weather_still_recommend_from_recorded_context(client):
    _, headers, field = register_with_field(client)

    from app.database.session import SessionLocal
    from app.models.field import Field

    session = SessionLocal()
    try:
        record = session.query(Field).filter(Field.id == field["id"]).first()
        record.latitude = None
        record.longitude = None
        session.commit()
    finally:
        session.close()

    body = generate(client, headers, field["id"])

    assert body["soil"]["has_measurement"] is False
    assert body["weather"]["available"] is False
    assert "coordinates" in (body["weather"]["reason"] or "")

    for result in body["results"]:
        assert result["status"] in VALID_STATUSES
        assert result["preliminary"] is True
        assert result["score"] is not None
        assert any("soil test" in step for step in result["next_steps"])
        assert any("coordinates" in step for step in result["next_steps"])

    # Even with neither soil nor live weather, the recorded location + season
    # + water still produce ranked, transparent recommendations.
    assert any(r["status"] == C.STATUS_SUITABLE for r in body["results"])


def test_field_without_coordinates_skips_weather_honestly(client):
    _, headers, field = register_with_field(client)

    # Remove the coordinates directly to simulate an unlocated field (the
    # create API always requires confirmed coordinates).
    from app.database.session import SessionLocal
    from app.models.field import Field

    session = SessionLocal()
    try:
        record = session.query(Field).filter(Field.id == field["id"]).first()
        record.latitude = None
        record.longitude = None
        session.commit()
    finally:
        session.close()

    body = generate(client, headers, field["id"])

    assert body["weather"]["available"] is False
    assert "coordinates" in body["weather"]["reason"]
    for result in body["results"]:
        assert any("coordinates" in step for step in result["next_steps"])


def test_weather_service_failure_does_not_block_recommendations(client, fake_weather):
    _, headers, field = register_with_field(client)
    fake_weather["error"] = WeatherServiceError(
        "Weather data could not be fetched right now. Please try again later."
    )

    body = generate(client, headers, field["id"])
    assert body["weather"]["available"] is False
    assert body["results"]
    for result in body["results"]:
        assert result["status"] in VALID_STATUSES
        assert result["risks"] == []
        assert any("weather" in note.lower() for note in result["notes"])


# --- Weather risk integration ----------------------------------------------


def test_heavy_rain_and_temperature_risks_include_basis_and_source(client, fake_weather):
    fake_weather["snapshot"] = forecast(
        daily=[
            {"time": "2026-10-10", "precipitation_sum": 72.0,
             "temperature_2m_max": 39.0, "temperature_2m_min": 24.0},
        ]
        + [
            {"time": f"2026-10-{11 + i:02d}", "precipitation_sum": 15.0,
             "temperature_2m_max": 30.0, "temperature_2m_min": 22.0}
            for i in range(6)
        ],
        observed_at="2026-10-10T06:00",
    )
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    kinds = set()
    for result in body["results"]:
        for risk in result["risks"]:
            kinds.add(risk["kind"])
            assert risk["basis"], risk
            assert risk["period"], risk
            assert risk["source"] == "Open-Meteo"
            assert risk["detail"]
            assert risk["severity"] in {C.RISK_SEVERITY_HIGH, C.RISK_SEVERITY_MEDIUM}

    assert C.RISK_KIND_HEAVY_RAIN in kinds  # 72 mm day
    assert C.RISK_KIND_WET_SPELL in kinds  # wet week
    # Rice documents 20-35 C, so a 39 C forecast day is flagged for it.
    assert C.RISK_KIND_HEAT in kinds


def test_dry_spell_risk_when_forecast_is_dry(client, fake_weather):
    fake_weather["snapshot"] = forecast(
        daily=[
            {"time": f"2026-10-{10 + i:02d}", "precipitation_sum": 0.0,
             "temperature_2m_max": 31.0, "temperature_2m_min": 20.0}
            for i in range(7)
        ]
    )
    _, headers, field = register_with_field(client)
    body = generate(client, headers, field["id"])
    kinds = {risk["kind"] for result in body["results"] for risk in result["risks"]}
    assert C.RISK_KIND_DRY_SPELL in kinds
    assert C.RISK_KIND_HEAVY_RAIN not in kinds


def test_weather_summary_is_persisted_in_the_input_snapshot(client, fake_weather):
    fake_weather["snapshot"] = forecast(observed_at="2026-10-10T06:00")
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    batch = client.get(
        f"/api/fields/{field['id']}/crops/recommendations", headers=headers
    ).json()[0]
    assert batch["batch_id"] == body["batch_id"]

    # Read the persisted snapshot from the first row of the batch.
    from app.database.session import SessionLocal
    from app.models.crop import CropRecommendation

    session = SessionLocal()
    try:
        row = (
            session.query(CropRecommendation)
            .filter(CropRecommendation.batch_id == body["batch_id"])
            .order_by(CropRecommendation.id)
            .first()
        )
        snapshot = row.input_snapshot
        assert row.input_snapshot is not None
    finally:
        session.close()

    assert snapshot["engine_version"] == C.ENGINE_VERSION
    assert snapshot["reference_date"] == TODAY
    assert snapshot["season"] == body["season"]
    assert snapshot["soil"]["tested_on"] == TODAY
    assert snapshot["weather"]["available"] is True
    assert snapshot["weather"]["observed_at"] == "2026-10-10T06:00"
    assert snapshot["weather"]["source"] == "Open-Meteo"
    assert snapshot["scoring"]["weights"] == body["config"]["weights"]
    assert snapshot["field"]["id"] == field["id"]
    assert "crop" not in snapshot  # the snapshot is inputs, not outputs


# --- Comparison -------------------------------------------------------------


def test_compare_selected_crops_side_by_side(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])

    crops = client.get("/api/crops", headers=headers).json()
    wanted = [c["id"] for c in crops[:3]]

    r = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": wanted},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert {c["crop_id"] for c in body["results"]} == set(wanted)
    assert len(body["ranking"]) == 3
    assert body["disclaimer"]
    assert body["context"]["season"] in C.SEASONS
    for evaluation in body["results"]:
        assert evaluation["status"] in VALID_STATUSES
        assert evaluation["factors"]
        assert evaluation["reasons"]

    # Ranking reproduces the recommendations page order (status, then score).
    order = {C.STATUS_SUITABLE: 0, C.STATUS_NEEDS_INFO: 1, C.STATUS_NOT_RECOMMENDED: 2}
    ranks = [
        (order[e["status"]], -(e["score"] or 0.0), e["display_name"])
        for e in body["ranking"]
    ]
    assert ranks == sorted(ranks)
    for entry in body["ranking"]:
        assert entry["status_label"]
        assert entry["rank"] == body["ranking"].index(entry) + 1

    # The factor matrix exposes the working for the scored factors.
    factor_names = {row["factor"] for row in body["factors"]}
    assert {"ph", "texture", "water", "season"} <= factor_names
    for row in body["factors"]:
        assert row["cells"], row
        assert row["label"]

    unknown = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": [999999]},
        headers=headers,
    )
    assert unknown.status_code == 404

    empty = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": []},
        headers=headers,
    )
    assert empty.status_code == 422


def test_compare_without_soil_marks_preliminary_and_explains_missing(client):
    _, headers, field = register_with_field(client)
    crops = client.get("/api/crops", headers=headers).json()
    wanted = [c["id"] for c in crops[:2]]

    r = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": wanted},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # No soil means the comparison is honestly preliminary, not "better".
    assert body["preliminary_note"] is not None
    assert all(entry["preliminary"] for entry in body["ranking"])
    ph_row = next(row for row in body["factors"] if row["factor"] == "ph")
    assert ph_row["compared"] is False
    assert all(cell["status"] == "missing_input" for cell in ph_row["cells"])
    # The farmer is told exactly which inputs to collect to firm the estimate.
    collect = {item["input"] for item in body["info_to_collect"]}
    assert {"ph", "texture"} <= collect
    # Nothing is invented: inputs stay null and scores stay within bounds.
    for result in body["results"]:
        assert result["factors"]["ph"]["input"] is None
        assert result["score"] is None or 0.0 <= result["score"] <= 1.0
    # Every ranking row explains what supports it and what is missing.
    assert any(entry["missing"] for entry in body["ranking"])


def test_compare_partial_soil_compares_pH_only_as_preliminary(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"], ph=6.8, texture=None)
    crops = client.get("/api/crops", headers=headers).json()
    wanted = [c["id"] for c in crops[:2]]

    body = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": wanted},
        headers=headers,
    ).json()

    ph_row = next(row for row in body["factors"] if row["factor"] == "ph")
    tex_row = next(row for row in body["factors"] if row["factor"] == "texture")
    assert ph_row["compared"] is True
    assert all(cell["status"] == "evaluated" for cell in ph_row["cells"])
    assert tex_row["compared"] is False
    assert all(cell["status"] == "missing_input" for cell in tex_row["cells"])
    assert body["preliminary_note"] is not None


def test_compare_full_soil_is_not_preliminary(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    crops = client.get("/api/crops", headers=headers).json()
    wanted = [c["id"] for c in crops[:2]]

    body = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": wanted},
        headers=headers,
    ).json()

    assert body["preliminary_note"] is None
    assert all(not entry["preliminary"] for entry in body["ranking"])
    for name in SCORED_FACTORS:
        row = next(r for r in body["factors"] if r["factor"] == name)
        assert row["compared"] is True
        assert all(cell["status"] == "evaluated" for cell in row["cells"])


def test_compare_without_weather_reports_missing_context(client):
    _, headers, field = register_with_field(client)

    from app.database.session import SessionLocal
    from app.models.field import Field

    session = SessionLocal()
    try:
        record = session.query(Field).filter(Field.id == field["id"]).first()
        record.latitude = None
        record.longitude = None
        session.commit()
    finally:
        session.close()

    crops = client.get("/api/crops", headers=headers).json()
    wanted = [c["id"] for c in crops[:2]]
    body = client.post(
        f"/api/fields/{field['id']}/crops/compare",
        json={"crop_ids": wanted},
        headers=headers,
    ).json()

    assert body["context"]["weather"]["available"] is False
    assert any(item["input"] == "weather" for item in body["info_to_collect"])
    assert any("weather was not available" in line for line in body["rank_changers"])
    # The comparison still generates and is still explained.
    assert len(body["ranking"]) == 2
    assert all(entry["status"] in VALID_STATUSES for entry in body["ranking"])


# --- History ----------------------------------------------------------------


def test_recommendation_history_and_detail(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    batches = client.get(
        f"/api/fields/{field['id']}/crops/recommendations", headers=headers
    ).json()
    assert len(batches) == 1
    summary = batches[0]
    assert summary["batch_id"] == body["batch_id"]
    assert summary["season"] == body["season"]
    assert summary["engine_version"] == C.ENGINE_VERSION
    counts = summary["counts"]
    total = counts["suitable"] + counts["needs_information"] + counts["not_recommended"]
    assert total == len(body["results"])

    # A second run creates a second batch, newest first.
    generate(client, headers, field["id"])
    batches = client.get(
        f"/api/fields/{field['id']}/crops/recommendations", headers=headers
    ).json()
    assert len(batches) == 2
    assert batches[0]["created_at"] >= batches[1]["created_at"]

    # Detail endpoint returns the full working and the input snapshot.
    from app.database.session import SessionLocal
    from app.models.crop import CropRecommendation

    session = SessionLocal()
    try:
        row = (
            session.query(CropRecommendation)
            .filter(CropRecommendation.batch_id == body["batch_id"])
            .order_by(CropRecommendation.id)
            .first()
        )
        rec_id = row.id
    finally:
        session.close()

    detail = client.get(
        f"/api/fields/{field['id']}/crops/recommendations/{rec_id}", headers=headers
    )
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["batch_id"] == body["batch_id"]
    assert payload["status"] in VALID_STATUSES
    assert payload["status_label"]
    assert payload["engine_version"] == C.ENGINE_VERSION
    assert payload["result"]["factors"]
    assert payload["input_snapshot"]["soil"]["tested_on"] == TODAY

    # Guessing an id that belongs to nobody returns 404, never someone else's row.
    assert (
        client.get(
            f"/api/fields/{field['id']}/crops/recommendations/{rec_id + 100000}",
            headers=headers,
        ).status_code
        == 404
    )


def test_recommendation_batch_can_be_re_read(client):
    _, headers, field = register_with_field(client)
    add_soil(client, headers, field["id"])
    body = generate(client, headers, field["id"])

    r = client.get(
        f"/api/fields/{field['id']}/crops/recommendations/batches/{body['batch_id']}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == len(body["results"])

    for row in rows:
        assert row["batch_id"] == body["batch_id"]
        assert row["status"] in VALID_STATUSES
        assert row["status_label"]
        assert row["engine_version"] == C.ENGINE_VERSION
        assert row["result"]["factors"]
        assert row["input_snapshot"]["reference_date"] == TODAY
        assert row["display_name"]

    # A batch that does not belong to this field is a 404, never an empty 200.
    unknown = client.get(
        f"/api/fields/{field['id']}/crops/recommendations/batches/deadbeef",
        headers=headers,
    )
    assert unknown.status_code == 404

    # Another farmer cannot read this batch either.
    other_email = fresh_email()
    register_user(client, email=other_email)
    other_headers = auth_headers(client, other_email)
    assert (
        client.get(
            f"/api/fields/{field['id']}/crops/recommendations/batches/{body['batch_id']}",
            headers=other_headers,
        ).status_code
        == 404
    )


# --- Admin scoring configuration -------------------------------------------


def test_admin_reads_and_updates_scoring_config(client):
    email = fresh_email()
    register_user(client, email=email)
    promote_to_admin(email)
    headers = auth_headers(client, email)

    current = client.get("/api/admin/crop-scoring-config", headers=headers)
    assert current.status_code == 200, current.text
    original = current.json()
    assert original["weights"]
    assert original["essential_factors"]

    bad = client.put(
        "/api/admin/crop-scoring-config",
        json={"weights": {"nonsense": 1.0}},
        headers=headers,
    )
    assert bad.status_code == 422

    try:
        changed = client.put(
            "/api/admin/crop-scoring-config",
            json={"suitable_threshold": 0.42},
            headers=headers,
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["suitable_threshold"] == 0.42

        # The engine reads the stored configuration, not the hard-coded default.
        from app.database.session import SessionLocal

        session = SessionLocal()
        try:
            assert load_config(session)["suitable_threshold"] == 0.42
        finally:
            session.close()
    finally:
        client.put(
            "/api/admin/crop-scoring-config",
            json={"suitable_threshold": original["suitable_threshold"]},
            headers=headers,
        )


# --- Live integration (real Open-Meteo) -------------------------------------


@pytest.mark.network
def test_generate_recommendations_with_live_weather(client):
    _, headers, field = register_with_field(client)
    body = generate(client, headers, field["id"])
    assert body["results"]
    if body["weather"]["available"]:
        assert body["weather"]["source"] == "Open-Meteo"
        assert body["weather"]["observed_at"]
        for result in body["results"]:
            for risk in result["risks"]:
                assert risk["source"] == "Open-Meteo"
    else:
        assert body["weather"]["reason"]
