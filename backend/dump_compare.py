import json
import os
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="annadata_dump_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'dump.db').as_posix()}"
os.environ["SOIL_REPORT_STORAGE_DIR"] = str(Path(_TMP_DIR, "soil_uploads"))

from fastapi.testclient import TestClient

from app.main import app

_client_ctx = TestClient(app)
client = _client_ctx.__enter__()

email = "dump@example.com"
client.post("/api/auth/register", json={"name": "Dump", "email": email, "password": "secret123"})
token = client.post("/api/auth/login", data={"username": email, "password": "secret123"}).json()[
    "access_token"
]
headers = {"Authorization": f"Bearer {token}"}

field = client.post(
    "/api/fields",
    json={
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
    },
    headers=headers,
).json()
fid = field["id"]

# Deterministic, offline forecast so the dump is reproducible and every scored
# factor (soil, water, season, temperature, rainfall) is evaluated, producing
# the full range of match categories.
from datetime import date as _date

from app.services import weather_service
from app.services.weather_service import WeatherSnapshot


async def _fixed_weather(latitude, longitude):
    days = [
        {
            "time": f"2026-10-{10 + i:02d}",
            "precipitation_sum": 8.0,
            "temperature_2m_max": 30.0,
            "temperature_2m_min": 21.0,
        }
        for i in range(7)
    ]
    return WeatherSnapshot(
        source="Open-Meteo",
        latitude=latitude,
        longitude=longitude,
        observed_at="2026-10-10T12:00",
        daily=days,
    )


weather_service.fetch_full_weather = _fixed_weather

# A recorded soil report so the dump shows the full range of match categories.
import datetime as _dt

soil = client.post(
    f"/api/fields/{fid}/soil/measurements",
    json={
        "tested_on": _date.today().isoformat(),
        "test_source": "Govt lab",
        "ph": 6.5,
        "texture": "loam",
    },
    headers=headers,
)
assert soil.status_code == 201, soil.text

r = client.post(
    f"/api/fields/{fid}/crops/recommendations", json={}, headers=headers
)
assert r.status_code == 201, r.text
batch = r.json()

crops = client.get("/api/crops", headers=headers).json()
wanted = [c["id"] for c in crops[:3]]
cmp_res = client.post(
    f"/api/fields/{fid}/crops/compare", json={"crop_ids": wanted}, headers=headers
)
assert cmp_res.status_code == 200, cmp_res.text

out = {
    "batch": batch,
    "compare": cmp_res.json(),
}
Path("../compare_dump.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("wrote compare_dump.json")
print("rank statuses:", [(e["rank"], e["status"], e["score"]) for e in cmp_res.json()["ranking"]])
print("factor keys:", [row["factor"] for row in cmp_res.json()["factors"]])
print("context keys:", list(cmp_res.json()["context"].keys()))
print("preliminary_note:", cmp_res.json()["preliminary_note"])
