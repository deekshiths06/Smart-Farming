"""End-to-end API tests: auth, field lifecycle, ownership, validation, admin."""

from tests.conftest import VALID_FIELD, auth_headers, fresh_email, login_user, register_user


def test_register_and_login_flow(client):
    email = fresh_email()
    r = register_user(client, email=email)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "farmer"
    assert "password" not in body
    assert "password_hash" not in body

    login = login_user(client, email)
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "farmer"


def test_register_ignores_client_role(client):
    email = fresh_email()
    r = register_user(client, email=email, role="admin", is_active=True)
    assert r.status_code == 201
    assert r.json()["role"] == "farmer"


def test_register_duplicate_email(client):
    email = fresh_email()
    assert register_user(client, email=email).status_code == 201
    r = register_user(client, email=email)
    assert r.status_code == 400


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_field_requires_auth(client):
    assert client.get("/api/fields").status_code == 401
    assert client.post("/api/fields", json=VALID_FIELD).status_code == 401
    assert client.get("/api/fields/1").status_code == 401
    assert client.put("/api/fields/1", json={}).status_code == 401
    assert client.delete("/api/fields/1").status_code == 401


def test_create_and_retrieve_field(client, db):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    r = client.post("/api/fields", json=VALID_FIELD, headers=headers)
    assert r.status_code == 201, r.text
    field = r.json()
    field_id = field["id"]
    assert field["user_id"]
    assert field["field_name"] == "North Field"
    assert field["location_confirmed"] is True
    assert field["water_source"] == "rain_fed"
    assert field["soil_status"] == "not_provided"

    # Persistence: values survive in the real database, not just in memory.
    from app.models.field import Field

    stored = db.query(Field).filter(Field.id == field_id).first()
    assert stored is not None
    assert stored.field_name == "North Field"
    assert abs(stored.latitude - 12.9716) < 1e-9

    listing = client.get("/api/fields", headers=headers)
    assert listing.status_code == 200
    assert [f["id"] for f in listing.json()] == [field_id]


def test_create_field_requires_confirmed_location(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    payload = dict(VALID_FIELD, location_confirmed=False)
    r = client.post("/api/fields", json=payload, headers=headers)
    assert r.status_code == 422

    missing_coords = {k: v for k, v in VALID_FIELD.items() if k not in ("latitude", "longitude")}
    assert client.post("/api/fields", json=missing_coords, headers=headers).status_code == 422


def test_create_field_rejects_invalid_coordinates(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    for lat, lon in [(91, 0), (-91, 0), (0, 181), (0, -181)]:
        payload = dict(VALID_FIELD, latitude=lat, longitude=lon)
        assert client.post("/api/fields", json=payload, headers=headers).status_code == 422

    payload = dict(VALID_FIELD, area=-5)
    assert client.post("/api/fields", json=payload, headers=headers).status_code == 422

    payload = dict(VALID_FIELD, water_source="unknown_source")
    assert client.post("/api/fields", json=payload, headers=headers).status_code == 422


def test_create_field_rejects_malformed_boundary(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    bad_payloads = [
        dict(VALID_FIELD, boundary={"type": "Point", "coordinates": [0, 0]}),  # wrong type
        dict(
            VALID_FIELD,
            boundary={
                "type": "Polygon",
                "coordinates": [[[77.5, 12.9], [77.6, 12.9], [77.6, 13.0]]],  # < 4 positions
            },
        ),
        dict(
            VALID_FIELD,
            boundary={
                "type": "Polygon",
                "coordinates": [[[77.5, 12.9], [77.6, 12.9], [77.6, 13.0], [190.0, 13.0]]],
            },  # lon out of range
        ),
    ]
    for payload in bad_payloads:
        assert client.post("/api/fields", json=payload, headers=headers).status_code == 422


def test_create_field_computes_area_from_boundary(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    boundary = {
        "type": "Polygon",
        "coordinates": [
            [
                [77.5944, 12.9710],
                [77.5960, 12.9710],
                [77.5960, 12.9722],
                [77.5944, 12.9722],
            ]
        ],
    }
    payload = dict(VALID_FIELD, boundary=boundary, area_source="calculated_boundary", area=None)
    r = client.post("/api/fields", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    field = r.json()
    assert field["area_source"] == "calculated_boundary"
    assert field["area_unit"] == "acre"
    # ~300m x ~130m plot -> roughly 10 acres or less; assert a sane bracket.
    acres = field["area"]
    assert 0.5 < acres < 20, acres
    assert field["boundary"]["type"] == "Polygon"


def test_update_field(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    field_id = client.post("/api/fields", json=VALID_FIELD, headers=headers).json()["id"]

    r = client.put(
        f"/api/fields/{field_id}",
        json={"field_name": "Renamed Field", "water_availability": "good"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["field_name"] == "Renamed Field"
    assert body["water_availability"] == "good"
    assert body["water_source"] == "rain_fed"  # untouched

    # Partial update with empty body is allowed and preserves data.
    r = client.put(f"/api/fields/{field_id}", json={}, headers=headers)
    assert r.status_code == 200
    assert r.json()["field_name"] == "Renamed Field"


def test_update_location_requires_confirmation(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    field_id = client.post("/api/fields", json=VALID_FIELD, headers=headers).json()["id"]

    r = client.put(
        f"/api/fields/{field_id}",
        json={"latitude": 12.99, "longitude": 77.60},
        headers=headers,
    )
    assert r.status_code == 422

    r = client.put(
        f"/api/fields/{field_id}",
        json={"latitude": 12.99, "longitude": 77.60, "location_confirmed": True},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["latitude"] == 12.99


def test_delete_field(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    field_id = client.post("/api/fields", json=VALID_FIELD, headers=headers).json()["id"]

    r = client.delete(f"/api/fields/{field_id}", headers=headers)
    assert r.status_code == 204
    assert client.get(f"/api/fields/{field_id}", headers=headers).status_code == 404


def test_ownership_protection(client):
    owner_email = fresh_email("owner")
    intruder_email = fresh_email("intruder")
    register_user(client, email=owner_email)
    register_user(client, email=intruder_email)

    owner_headers = auth_headers(client, owner_email)
    intruder_headers = auth_headers(client, intruder_email)

    field_id = client.post("/api/fields", json=VALID_FIELD, headers=owner_headers).json()["id"]

    # The intruder cannot see the field by guessing ids: all return 404.
    assert client.get(f"/api/fields/{field_id}", headers=intruder_headers).status_code == 404
    assert client.put(f"/api/fields/{field_id}", json={"field_name": "stolen"}, headers=intruder_headers).status_code == 404
    assert client.delete(f"/api/fields/{field_id}", headers=intruder_headers).status_code == 404
    assert field_id not in [f["id"] for f in client.get("/api/fields", headers=intruder_headers).json()]

    # owner still sees it, unchanged
    assert client.get(f"/api/fields/{field_id}", headers=owner_headers).json()["field_name"] == "North Field"


def test_admin_stats_require_admin_role(client):
    email = fresh_email()
    register_user(client, email=email)
    farmer_headers = auth_headers(client, email)

    r = client.get("/api/admin/stats", headers=farmer_headers)
    assert r.status_code == 403
    r = client.get("/api/admin/data-sources", headers=farmer_headers)
    assert r.status_code == 403


def test_admin_stats_are_real(client):
    from app.models.user import ROLE_ADMIN, User

    email = fresh_email("admin")
    register_user(client, email=email)
    token = login_user(client, email).json()["access_token"]

    # Promote via the database (same path the create_admin script uses).
    from app.database.session import SessionLocal

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        user.role = ROLE_ADMIN
        session.commit()
    finally:
        session.close()

    headers = {"Authorization": f"Bearer {token}"}
    stats = client.get("/api/admin/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["application"]["name"] == "ANNADATA"
    assert body["counts"]["admins"] >= 1
    assert body["counts"]["farmers"] >= 1
    # The registered farmer owns a field in this session - real count, not fabricated.
    assert body["counts"]["total_fields"] >= 1
    assert body["database"]["engine"] == "sqlite"

    sources = client.get("/api/admin/data-sources", headers=headers)
    assert sources.status_code == 200
    ids = {s["id"] for s in sources.json()["sources"]}
    assert {"nominatim", "open_meteo", "soil_verified", "soil_geospatial", "market", "crop_knowledge_base"} <= ids


def test_reverse_geocode_endpoint(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)

    r = client.post(
        "/api/location/reverse-geocode",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    location = body["location"]
    assert location["state"] == "Karnataka"
    assert location["country"] == "India"
    assert location["district"]
    assert location["address"]


def test_reverse_geocode_validation(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    r = client.post(
        "/api/location/reverse-geocode",
        json={"latitude": 120.0, "longitude": 77.0},
        headers=headers,
    )
    assert r.status_code == 422


def test_field_weather_real_call(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    field_id = client.post("/api/fields", json=VALID_FIELD, headers=headers).json()["id"]

    r = client.get(f"/api/fields/{field_id}/weather", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    weather = body["weather"]
    assert weather["source"] == "Open-Meteo"
    assert weather["latitude"] is not None
    assert weather["temperature_2m"] is not None
    assert weather["observed_at"]


def test_weather_unavailable_for_unlocated_field(client):
    email = fresh_email()
    register_user(client, email=email)
    headers = auth_headers(client, email)
    payload = {k: v for k, v in VALID_FIELD.items() if k in ("field_name", "location_confirmed")}
    payload.update({"latitude": 12.97, "longitude": 77.59})
    field_id = client.post("/api/fields", json=payload, headers=headers).json()["id"]

    # Remove the coordinates directly to simulate an unlocated field.
    from app.database.session import SessionLocal
    from app.models.field import Field

    session = SessionLocal()
    try:
        field = session.query(Field).filter(Field.id == field_id).first()
        field.latitude = None
        field.longitude = None
        session.commit()
    finally:
        session.close()

    r = client.get(f"/api/fields/{field_id}/weather", headers=headers)
    assert r.status_code == 400