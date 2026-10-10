"""Soil Intelligence tests: measurements, uploads, assessment, ownership."""

from datetime import date, timedelta

from tests.conftest import VALID_FIELD, auth_headers, fresh_email, register_user

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
PNG_PREFIX = b"\x89PNG\r\n\x1a\n" + b"binary-png-content"

TODAY = date.today().isoformat()
PAST = (date.today() - timedelta(days=90)).isoformat()
OLDER = (date.today() - timedelta(days=400)).isoformat()


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


def base_measurement(**overrides):
    payload = {"tested_on": TODAY, "test_source": "KVK Hassan"}
    payload.update(overrides)
    return payload


def promote_to_admin(client, email):
    from app.database.session import SessionLocal
    from app.models.user import ROLE_ADMIN, User

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        user.role = ROLE_ADMIN
        session.commit()
    finally:
        session.close()


def upload_report(client, headers, field_id, filename="report.pdf", content=PDF_BYTES, content_type="application/pdf", **data):
    return client.post(
        f"/api/fields/{field_id}/soil/reports",
        files={"file": (filename, content, content_type)},
        data=data,
        headers=headers,
    )


# --- Authentication ---------------------------------------------------------


def test_soil_endpoints_require_auth(client):
    assert client.get("/api/fields/1/soil").status_code == 401
    assert client.get("/api/fields/1/soil/measurements").status_code == 401
    assert client.post("/api/fields/1/soil/measurements", json={}).status_code == 401
    assert client.put("/api/fields/1/soil/measurements/1", json={}).status_code == 401
    assert client.delete("/api/fields/1/soil/measurements/1").status_code == 401
    assert client.get("/api/fields/1/soil/reports").status_code == 401
    assert client.post("/api/fields/1/soil/reports", files={"file": ("x.pdf", PDF_BYTES, "application/pdf")}).status_code == 401
    assert client.get("/api/fields/1/soil/reports/1/download").status_code == 401
    assert client.get("/api/admin/soil/reference-ranges").status_code == 401


# --- Measurements -----------------------------------------------------------


def test_save_and_retrieve_measurement(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]

    r = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.7, nitrogen=300, texture="loam"),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["ph"] == 6.7
    assert body["nitrogen"] == 300
    assert body["texture"] == "loam"
    assert body["source_kind"] == "farmer_entered"
    assert body["field_id"] == field_id
    assert body["tested_on"] == TODAY

    # Field soil_status flips to available only when values exist.
    field_after = client.get(f"/api/fields/{field_id}", headers=headers).json()
    assert field_after["soil_status"] == "available"

    profile = client.get(f"/api/fields/{field_id}/soil", headers=headers)
    assert profile.status_code == 200, profile.text
    data = profile.json()
    assert data["has_measurements"] is True
    assert data["last_tested_on"] == TODAY
    assert data["completeness"]["measured_count"] == 3
    assert data["completeness"]["total_count"] == 8
    assert data["completeness"]["percent"] == 38
    assert "phosphorus" in data["completeness"]["missing"]
    assert data["assessment"]["ph"]["status"] == "within"
    assert data["assessment"]["ph"]["value"] == 6.7
    assert data["assessment"]["nitrogen"]["status"] == "within"
    assert data["assessment"]["texture"]["texture_label"] == "Loam"


def test_optional_parameters_all_missing(client):
    _, headers, field = register_with_field(client)
    r = client.post(
        f"/api/fields/{field['id']}/soil/measurements",
        json=base_measurement(ph=6.5),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["phosphorus"] is None
    assert body["organic_carbon"] is None
    assert body["texture"] is None

    data = client.get(f"/api/fields/{field['id']}/soil", headers=headers).json()
    assert data["completeness"]["measured_count"] == 1
    assert set(data["completeness"]["missing"]) == {
        "nitrogen", "phosphorus", "potassium", "ec", "organic_carbon", "moisture", "texture",
    }


def test_measurement_requires_at_least_one_parameter(client):
    _, headers, field = register_with_field(client)
    r = client.post(
        f"/api/fields/{field['id']}/soil/measurements",
        json=base_measurement(),
        headers=headers,
    )
    assert r.status_code == 422


def test_invalid_values_rejected(client):
    _, headers, field = register_with_field(client)
    url = f"/api/fields/{field['id']}/soil/measurements"

    invalid = [
        {"ph": 15.0},
        {"ph": -1.0},
        {"nitrogen": -5.0},
        {"phosphorus": 600.0},
        {"potassium": 3000.0},
        {"ec": 50.0},
        {"organic_carbon": 20.0},
        {"moisture": 120.0},
        {"texture": "rocky"},
    ]
    for patch in invalid:
        payload = base_measurement(**patch)
        r = client.post(url, json=payload, headers=headers)
        assert r.status_code == 422, f"{patch} -> {r.status_code}: {r.text}"


def test_invalid_dates_rejected(client):
    _, headers, field = register_with_field(client)
    url = f"/api/fields/{field['id']}/soil/measurements"
    future = (date.today() + timedelta(days=5)).isoformat()
    r = client.post(url, json=base_measurement(tested_on=future, ph=6.5), headers=headers)
    assert r.status_code == 422
    r = client.post(url, json=base_measurement(tested_on="1899-01-01", ph=6.5), headers=headers)
    assert r.status_code == 422


def test_update_measurement_in_place_keeps_history(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    measurement_id = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.0, tested_on=PAST),
        headers=headers,
    ).json()["id"]

    r = client.put(
        f"/api/fields/{field_id}/soil/measurements/{measurement_id}",
        json={"ph": 6.3, "nitrogen": 280},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ph"] == 6.3
    assert body["nitrogen"] == 280
    assert body["tested_on"] == PAST  # untouched

    # A second test event is appended as new history, never overwriting the first.
    client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.9, tested_on=TODAY),
        headers=headers,
    )
    history = client.get(f"/api/fields/{field_id}/soil/measurements", headers=headers).json()
    assert len(history) == 2
    assert history[0]["tested_on"] == TODAY  # newest first
    assert history[1]["tested_on"] == PAST


def test_delete_measurement_updates_field_status(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    measurement_id = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.5),
        headers=headers,
    ).json()["id"]
    upload_report(client, headers, field_id)  # keep a report in place

    assert client.get(f"/api/fields/{field_id}", headers=headers).json()["soil_status"] == "available"

    r = client.delete(f"/api/fields/{field_id}/soil/measurements/{measurement_id}", headers=headers)
    assert r.status_code == 204
    # Report remains -> "pending", never a fabricated "available".
    assert client.get(f"/api/fields/{field_id}", headers=headers).json()["soil_status"] == "pending"


# --- Ownership --------------------------------------------------------------


def test_measurement_ownership_protection(client):
    owner_email = fresh_email("owner")
    intruder_email = fresh_email("intruder")
    register_user(client, email=owner_email)
    register_user(client, email=intruder_email)
    owner_headers = auth_headers(client, owner_email)
    intruder_headers = auth_headers(client, intruder_email)

    field_id = make_field(client, owner_headers)["id"]
    measurement_id = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.5),
        headers=owner_headers,
    ).json()["id"]

    assert client.get(f"/api/fields/{field_id}/soil", headers=intruder_headers).status_code == 404
    assert client.get(f"/api/fields/{field_id}/soil/measurements", headers=intruder_headers).status_code == 404
    assert (
        client.post(
            f"/api/fields/{field_id}/soil/measurements",
            json=base_measurement(ph=5.5),
            headers=intruder_headers,
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/fields/{field_id}/soil/measurements/{measurement_id}",
            json={"ph": 9.0},
            headers=intruder_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/fields/{field_id}/soil/measurements/{measurement_id}", headers=intruder_headers
        ).status_code
        == 404
    )

    # Owner still intact.
    assert client.get(f"/api/fields/{field_id}/soil", headers=owner_headers).json()["latest_measurement"]["ph"] == 6.5


def test_report_ownership_protection(client):
    owner_email = fresh_email("owner")
    intruder_email = fresh_email("intruder")
    register_user(client, email=owner_email)
    register_user(client, email=intruder_email)
    owner_headers = auth_headers(client, owner_email)
    intruder_headers = auth_headers(client, intruder_email)

    field_id = make_field(client, owner_headers)["id"]
    report = upload_report(client, owner_headers, field_id).json()

    assert client.get(f"/api/fields/{field_id}/soil/reports", headers=intruder_headers).status_code == 404
    assert (
        client.get(f"/api/fields/{field_id}/soil/reports/{report['id']}/download", headers=intruder_headers).status_code
        == 404
    )
    assert upload_report(client, intruder_headers, field_id).status_code == 404
    # A report_confirmed measurement referencing the owner's report is also denied.
    assert (
        client.post(
            f"/api/fields/{field_id}/soil/measurements",
            json=base_measurement(source_kind="report_confirmed", report_id=report["id"], ph=6.5),
            headers=intruder_headers,
        ).status_code
        == 404
    )

    # Owner downloads fine.
    down = client.get(f"/api/fields/{field_id}/soil/reports/{report['id']}/download", headers=owner_headers)
    assert down.status_code == 200
    assert down.content == PDF_BYTES


# --- Report uploads ---------------------------------------------------------


def test_report_upload_and_download(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]

    r = upload_report(
        client, headers, field_id, report_date=PAST, report_source="KVK Hassan"
    )
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["original_filename"] == "report.pdf"
    assert report["content_type"] == "application/pdf"
    assert report["file_size_bytes"] == len(PDF_BYTES)
    assert report["report_date"] == PAST
    assert report["report_source"] == "KVK Hassan"
    assert report["status"] == "uploaded"

    listing = client.get(f"/api/fields/{field_id}/soil/reports", headers=headers).json()
    assert [item["id"] for item in listing] == [report["id"]]

    down = client.get(f"/api/fields/{field_id}/soil/reports/{report['id']}/download", headers=headers)
    assert down.status_code == 200
    assert down.headers["content-type"].startswith("application/pdf")
    assert down.content == PDF_BYTES

    # PNG reports are accepted too.
    img = upload_report(client, headers, field_id, filename="scan.png", content=PNG_PREFIX, content_type="image/png")
    assert img.status_code == 201, img.text
    assert img.json()["content_type"] == "image/png"


def test_report_upload_rejects_bad_files(client):
    _, headers, field = register_with_field(client)
    url = f"/api/fields/{field['id']}/soil/reports"

    txt = upload_report(client, headers, field["id"], filename="notes.txt", content=b"hello", content_type="text/plain")
    assert txt.status_code == 422

    disguised = upload_report(client, headers, field["id"], filename="fake.pdf", content=b"not a pdf at all", content_type="application/pdf")
    assert disguised.status_code == 422

    mismatch = upload_report(client, headers, field["id"], content=PDF_BYTES, content_type="text/plain")
    assert mismatch.status_code == 422

    empty_name = client.post(url, files={"file": ("", PDF_BYTES, "application/pdf")}, headers=headers)
    assert empty_name.status_code in (400, 422)


def test_report_upload_size_limit(client, monkeypatch):
    from app.core.config import settings

    _, headers, field = register_with_field(client)
    monkeypatch.setattr(settings, "SOIL_REPORT_MAX_SIZE_BYTES", 100)
    r = upload_report(client, headers, field["id"], content=PDF_BYTES * 20)
    assert r.status_code == 422
    assert "too large" in r.json()["detail"].lower()


def test_unsafe_filename_sanitized(client):
    _, headers, field = register_with_field(client)
    r = upload_report(client, headers, field["id"], filename="..\\..\\evil.pdf", content=PDF_BYTES)
    assert r.status_code == 201, r.text
    assert r.json()["original_filename"] == "evil.pdf"
    assert "stored_filename" not in r.json()


def test_report_confirmed_measurement_links_report(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    report = upload_report(client, headers, field_id).json()

    # Cannot mark as report-confirmed without the report id.
    r = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(source_kind="report_confirmed", ph=6.5),
        headers=headers,
    )
    assert r.status_code == 422

    # Farmer-entered cannot silently reference a report.
    r = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(report_id=report["id"], ph=6.5),
        headers=headers,
    )
    assert r.status_code == 422

    r = client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(source_kind="report_confirmed", report_id=report["id"], ph=6.5),
        headers=headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["source_kind"] == "report_confirmed"
    assert r.json()["report_id"] == report["id"]

    reports = client.get(f"/api/fields/{field_id}/soil/reports", headers=headers).json()
    assert reports[0]["status"] == "linked"

    profile = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()
    assert profile["assessment"]["ph"]["source_kind"] == "From an uploaded report, confirmed"


def test_report_date_future_rejected(client):
    _, headers, field = register_with_field(client)
    r = upload_report(client, headers, field["id"], report_date=(date.today() + timedelta(days=3)).isoformat())
    assert r.status_code == 422


# --- Assessment -------------------------------------------------------------


def test_assessment_classification(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    url = f"/api/fields/{field_id}/soil/measurements"

    client.post(url, json=base_measurement(ph=6.2, ec=1.5, nitrogen=300, phosphorus=30, potassium=120, organic_carbon=0.5), headers=headers)
    data = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()
    assert data["assessment"]["ph"]["status"] == "below"
    assert data["assessment"]["ec"]["status"] == "within"
    assert data["assessment"]["nitrogen"]["status"] == "within"
    assert data["assessment"]["phosphorus"]["status"] == "within"
    assert data["assessment"]["potassium"]["status"] == "within"
    assert data["assessment"]["organic_carbon"]["status"] == "within"


def test_assessment_band_boundaries(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    url = f"/api/fields/{field_id}/soil/measurements"

    def status_for(payload):
        client.post(url, json=base_measurement(**payload), headers=headers)
        return client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]

    a = status_for({"ph": 6.5})  # lower edge of neutral band
    assert a["ph"]["status"] == "within"
    a = status_for({"ph": 8.6})
    assert a["ph"]["status"] == "above"
    a = status_for({"ec": 2.0})  # edge of non-saline band
    assert a["ec"]["status"] == "above"
    a = status_for({"nitrogen": 280})  # medium band starts
    assert a["nitrogen"]["status"] == "within"
    a = status_for({"nitrogen": 560})  # high band starts
    assert a["nitrogen"]["status"] == "above"
    a = status_for({"nitrogen": 120})
    assert a["nitrogen"]["status"] == "below"
    a = status_for({"phosphorus": 22})
    assert a["phosphorus"]["status"] == "within"
    a = status_for({"potassium": 110})
    assert a["potassium"]["status"] == "within"


def test_assessment_missing_and_unmeasurable(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]

    data = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()
    assert data["has_measurements"] is False
    assert data["completeness"]["measured_count"] == 0
    for parameter in ("ph", "nitrogen", "ec", "texture"):
        assert data["assessment"][parameter]["status"] == "missing"

    # Moisture without a soil texture cannot be assessed - no verified range applies.
    client.post(f"/api/fields/{field_id}/soil/measurements", json=base_measurement(moisture=25), headers=headers)
    assert client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]["moisture"]["status"] == "no_range"


def test_moisture_assessment_uses_texture_selected_ranges(client):
    _, headers, field = register_with_field(client)
    field_id = field["id"]
    url = f"/api/fields/{field_id}/soil/measurements"

    client.post(url, json=base_measurement(texture="loam", moisture=25), headers=headers)
    a = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]
    assert a["moisture"]["status"] == "within"
    assert a["moisture"]["applied_context"] == "For loam soils"

    client.post(url, json=base_measurement(texture="loam", moisture=12), headers=headers)
    a = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]
    assert a["moisture"]["status"] == "below"


def test_region_specific_ranges_take_precedence(client):
    _, headers, field = register_with_field(client, state="Karnataka")
    field_id = field["id"]
    client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(nitrogen=300),
        headers=headers,
    )
    a = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]
    assert a["nitrogen"]["applied_context"] == "For Karnataka"
    assert a["nitrogen"]["status"] == "within"


def test_no_range_is_honest_when_guidance_unavailable(client):
    _, headers, field = register_with_field(client, state="Tamil Nadu")
    field_id = field["id"]
    client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(moisture=25, texture="loam"),
        headers=headers,
    )
    a = client.get(f"/api/fields/{field_id}/soil", headers=headers).json()["assessment"]
    assert a["moisture"]["status"] == "within"


# --- Admin reference ranges -------------------------------------------------


def test_reference_ranges_are_admin_only(client):
    _, headers, _ = register_with_field(client)
    assert client.get("/api/admin/soil/reference-ranges", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/admin/soil/reference-ranges",
            json={"parameter": "ph", "label": "x", "min_value": 0, "max_value": 7, "source": "s"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.put("/api/admin/soil/reference-ranges/1", json={"label": "x"}, headers=headers).status_code == 403
    assert client.delete("/api/admin/soil/reference-ranges/1", headers=headers).status_code == 403


def test_admin_manages_reference_ranges(client):
    email = fresh_email("mgr")
    register_user(client, email=email)
    headers = auth_headers(client, email)
    promote_to_admin(client, email)

    listing = client.get("/api/admin/soil/reference-ranges", headers=headers)
    assert listing.status_code == 200, listing.text
    ph_ranges = [r for r in listing.json() if r["parameter"] == "ph" and r["context_type"] == "general"]
    assert len(ph_ranges) >= 5

    # Create
    created = client.post(
        "/api/admin/soil/reference-ranges",
        json={
            "parameter": "phosphorus",
            "context_type": "crop",
            "context_value": "tomato",
            "label": "Low for tomato",
            "min_value": 0,
            "max_value": 20,
            "unit": "kg/ha",
            "outcome": "below",
            "explanation": "Test band.",
            "source": "Test guide",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    range_id = created.json()["id"]

    filtered = client.get("/api/admin/soil/reference-ranges?parameter=phosphorus", headers=headers).json()
    assert any(r["id"] == range_id for r in filtered)

    # Update
    updated = client.put(
        f"/api/admin/soil/reference-ranges/{range_id}", json={"max_value": 15}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["max_value"] == 15

    # Invalid update (min > max) is rejected
    bad = client.put(
        f"/api/admin/soil/reference-ranges/{range_id}",
        json={"min_value": 50, "max_value": 15},
        headers=headers,
    )
    assert bad.status_code == 422

    # Texture cannot have a numeric band
    bad_create = client.post(
        "/api/admin/soil/reference-ranges",
        json={"parameter": "texture", "label": "x", "min_value": 1, "max_value": 2, "source": "s"},
        headers=headers,
    )
    assert bad_create.status_code == 422

    # Delete
    assert client.delete(f"/api/admin/soil/reference-ranges/{range_id}", headers=headers).status_code == 204
    remaining = client.get("/api/admin/soil/reference-ranges?parameter=phosphorus", headers=headers).json()
    assert not any(r["id"] == range_id for r in remaining)


def test_custom_range_changes_assessment(client):
    email = fresh_email("mgr")
    register_user(client, email=email)
    headers = auth_headers(client, email)
    promote_to_admin(client, email)

    _, farmer_headers, field = register_with_field(client)
    field_id = field["id"]
    client.post(
        f"/api/fields/{field_id}/soil/measurements",
        json=base_measurement(ph=6.4),
        headers=farmer_headers,
    )
    assert client.get(f"/api/fields/{field_id}/soil", headers=farmer_headers).json()["assessment"]["ph"]["status"] == "below"

    # Shift the neutral band to include 6.4 (admin controlled reference data).
    ph_general = [
        r
        for r in client.get("/api/admin/soil/reference-ranges", headers=headers).json()
        if r["parameter"] == "ph" and r["context_type"] == "general"
    ]
    # The "Slightly acidic" band (5.5-6.5) matches earlier in sequence and still
    # contains 6.4, so it must shrink before the Neutral band can own the value.
    slightly_acidic = next(r for r in ph_general if r["label"] == "Slightly acidic")
    client.put(
        f"/api/admin/soil/reference-ranges/{slightly_acidic['id']}",
        json={"max_value": 6.0},
        headers=headers,
    )
    neutral = next(r for r in ph_general if r["label"] == "Neutral")
    client.put(
        f"/api/admin/soil/reference-ranges/{neutral['id']}",
        json={"min_value": 6.0, "max_value": 7.5},
        headers=headers,
    )
    assert client.get(f"/api/fields/{field_id}/soil", headers=farmer_headers).json()["assessment"]["ph"]["status"] == "within"