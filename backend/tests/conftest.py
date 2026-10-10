import os
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="annadata_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["SOIL_REPORT_STORAGE_DIR"] = str(Path(_TMP_DIR, "soil_uploads"))
os.environ["NOMINATIM_MIN_INTERVAL_SECONDS"] = "0"
os.environ["NOMINATIM_TIMEOUT_SECONDS"] = "15"
os.environ["OPEN_METEO_TIMEOUT_SECONDS"] = "15"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

_counter = [0]


def fresh_email(prefix: str = "farmer") -> str:
    _counter[0] += 1
    return f"{prefix}{_counter[0]}@example.com"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register_user(client, email=fresh_email(), password="secret123", name="Test Farmer", **extra):
    payload = {"name": name, "email": email, "password": password}
    payload.update(extra)
    return client.post("/api/auth/register", json=payload)


def login_user(client, email, password="secret123"):
    return client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
    )


def auth_headers(client, email, password="secret123"):
    token = login_user(client, email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


VALID_FIELD = {
    "field_name": "North Field",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "location_accuracy": 18.0,
    "location_confirmed": True,
    "area": 2.5,
    "area_unit": "acre",
    "area_source": "manual",
    "water_source": "rain_fed",
    "water_availability": "seasonal",
    "soil_status": "not_provided",
}