"""AI Crop Disease Identification tests.

Most tests stub ``plant_disease_model.predict`` so the API contract (validation,
persistence, ownership, statuses) is exercised deterministically without loading
the 92 MB model. ``test_real_model_inference`` runs the genuine model end to end
and is skipped when the model file has not been downloaded.
"""

from io import BytesIO

import pytest
from PIL import Image

from app.services import plant_disease_model as svc
from tests.conftest import auth_headers, fresh_email, register_user


def make_image(fmt: str = "JPEG", size: tuple[int, int] = (320, 240), color=(70, 150, 70)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


JPEG = make_image()
PNG = make_image("PNG")


def register(client):
    email = fresh_email("disease")
    register_user(client, email=email)
    return email, auth_headers(client, email)


def assess(client, headers, crop="tomato", content=JPEG, filename="leaf.jpg", content_type="image/jpeg", symptoms=None):
    data = {"crop": crop}
    if symptoms is not None:
        data["symptoms"] = symptoms
    return client.post(
        "/api/disease/assess",
        files={"file": (filename, content, content_type)},
        data=data,
        headers=headers,
    )


def fake_result(**overrides) -> svc.PredictResult:
    base = dict(
        status=svc.STATUS_IDENTIFIED,
        predicted_class="Tomato___Early_blight",
        predicted_crop="Tomato",
        predicted_crop_label="Tomato",
        predicted_disease_label="Early blight",
        is_healthy=False,
        confidence=0.91,
        candidates=[
            {
                "class_name": "Tomato___Early_blight",
                "crop_label": "Tomato",
                "disease_label": "Early blight",
                "is_healthy": False,
                "confidence": 0.91,
            },
            {
                "class_name": "Tomato___Late_blight",
                "crop_label": "Tomato",
                "disease_label": "Late blight",
                "is_healthy": False,
                "confidence": 0.05,
            },
        ],
        image_width=224,
        image_height=224,
        latency_ms=15,
    )
    base.update(overrides)
    return svc.PredictResult(**base)


def stub_predict(monkeypatch, **overrides):
    monkeypatch.setattr(svc, "predict", lambda data, crop: fake_result(**overrides))


# --- Authentication ---------------------------------------------------------


def test_disease_endpoints_require_auth(client):
    assert client.get("/api/disease/crops").status_code == 401
    assert client.get("/api/disease/assessments").status_code == 401
    assert client.get("/api/disease/assessments/1").status_code == 401
    assert client.delete("/api/disease/assessments/1").status_code == 401
    assert (
        client.post(
            "/api/disease/assess",
            files={"file": ("leaf.jpg", JPEG, "image/jpeg")},
            data={"crop": "tomato"},
        ).status_code
        == 401
    )


# --- Coverage ---------------------------------------------------------------


def test_supported_crops_are_the_model_coverage(client):
    _, headers = register(client)
    r = client.get("/api/disease/crops", headers=headers)
    assert r.status_code == 200, r.text
    crops = r.json()
    keys = [crop["key"] for crop in crops]
    assert len(crops) == len(svc.SUPPORTED_CROPS)
    assert {"maize", "tomato", "potato"} <= set(keys)

    tomato = next(crop for crop in crops if crop["key"] == "tomato")
    classes = {disease["class_name"] for disease in tomato["diseases"]}
    assert "Tomato___Early_blight" in classes
    assert "Tomato___healthy" in classes


def test_assess_rejects_unsupported_crop(client):
    _, headers = register(client)
    r = assess(client, headers, crop="rice")
    assert r.status_code == 422
    assert "not supported" in r.json()["detail"].lower()


# --- Upload validation ------------------------------------------------------


def test_assess_rejects_non_image(client):
    _, headers = register(client)
    r = assess(client, headers, content=b"this is not an image")
    assert r.status_code == 422
    assert "image" in r.json()["detail"].lower()


def test_assess_rejects_empty_upload(client):
    _, headers = register(client)
    r = assess(client, headers, content=b"")
    assert r.status_code == 422


def test_assess_rejects_oversize_image(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DISEASE_IMAGE_MAX_SIZE_BYTES", 100)
    _, headers = register(client)
    r = assess(client, headers, content=JPEG * 10)
    assert r.status_code == 422
    assert "too large" in r.json()["detail"].lower()


def test_assess_returns_503_without_model(client, monkeypatch):
    monkeypatch.setattr(
        svc,
        "predict",
        lambda data, crop: (_ for _ in ()).throw(
            svc.ModelUnavailable("model missing; run the download script")
        ),
    )
    _, headers = register(client)
    r = assess(client, headers)
    assert r.status_code == 503


# --- Results and persistence ------------------------------------------------


@pytest.mark.parametrize(
    "status,overrides,expected_healthy",
    [
        (svc.STATUS_IDENTIFIED, {}, False),
        (
            svc.STATUS_HEALTHY,
            {
                "predicted_class": "Tomato___healthy",
                "predicted_disease_label": "healthy",
                "is_healthy": True,
                "confidence": 0.97,
            },
            True,
        ),
        (svc.STATUS_LOW_CONFIDENCE, {"confidence": 0.31}, False),
        (
            svc.STATUS_CROP_MISMATCH,
            {"predicted_class": "Potato___Late_blight", "predicted_crop": "Potato", "predicted_crop_label": "Potato"},
            False,
        ),
    ],
)
def test_assess_persists_result(client, monkeypatch, status, overrides, expected_healthy):
    stub_predict(monkeypatch, status=status, **overrides)
    email, headers = register(client)

    r = assess(client, headers, crop="tomato", symptoms="dark spots on lower leaves")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == status
    assert body["crop"] == "tomato"
    assert body["crop_label"] == "Tomato"
    assert body["is_healthy"] is expected_healthy
    assert body["symptoms"] == "dark spots on lower leaves"
    assert body["predicted_class"] in svc.load_classes()
    assert len(body["candidates"]) == 2
    assert body["model_name"] == svc.MODEL_NAME
    assert "not a confirmed diagnosis" in body["disclaimer"]
    assert body["image_width"] == 224 and body["image_height"] == 224
    assert body["image_size_bytes"] == len(JPEG)

    listed = client.get("/api/disease/assessments", headers=headers).json()
    assert [item["id"] for item in listed] == [body["id"]]
    assert listed[0]["image_filename"] == "leaf.jpg"


def test_image_bytes_are_never_persisted(client, monkeypatch):
    stub_predict(monkeypatch)
    _, headers = register(client)
    body = assess(client, headers).json()
    # Only metadata is stored - no path or blob fields exist on the record.
    assert "stored_filename" not in body
    assert "image_path" not in body
    assert "image_data" not in body


def test_unsafe_filename_is_sanitized(client, monkeypatch):
    stub_predict(monkeypatch)
    _, headers = register(client)
    r = assess(client, headers, filename="..\\..\\evil name!.jpg")
    assert r.status_code == 201, r.text
    assert "/" not in r.json()["image_filename"]
    assert "\\" not in r.json()["image_filename"]
    assert r.json()["image_filename"].endswith(".jpg")


# --- Ownership --------------------------------------------------------------


def test_assessment_ownership_isolation(client, monkeypatch):
    stub_predict(monkeypatch)
    owner_email, owner_headers = register(client)
    _, intruder_headers = register(client)

    created = assess(client, owner_headers).json()

    assert client.get("/api/disease/assessments", headers=intruder_headers).json() == []
    assert client.get(f"/api/disease/assessments/{created['id']}", headers=intruder_headers).status_code == 404
    assert client.delete(f"/api/disease/assessments/{created['id']}", headers=intruder_headers).status_code == 404

    # Owner still sees it.
    assert client.get(f"/api/disease/assessments/{created['id']}", headers=owner_headers).status_code == 200


def test_delete_own_assessment(client, monkeypatch):
    stub_predict(monkeypatch)
    _, headers = register(client)
    created = assess(client, headers).json()

    assert client.delete(f"/api/disease/assessments/{created['id']}", headers=headers).status_code == 204
    assert client.get("/api/disease/assessments", headers=headers).json() == []
    assert client.get(f"/api/disease/assessments/{created['id']}", headers=headers).status_code == 404


# --- Real, end-to-end inference ---------------------------------------------


def test_real_model_inference(client):
    if not svc.is_available():
        pytest.skip("disease model not downloaded (run scripts/download_disease_model.py)")
    pytest.importorskip("onnxruntime")

    _, headers = register(client)
    r = assess(client, headers, crop="tomato", content=make_image("JPEG", (256, 256)))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] in svc.ASSESSMENT_STATUSES
    assert body["predicted_class"] in svc.load_classes()
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["model_name"] == svc.MODEL_NAME
    assert body["latency_ms"] is not None
