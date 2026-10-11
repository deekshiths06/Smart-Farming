import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


def _cors_origins() -> list[str]:
    raw = os.getenv("BACKEND_CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


class Settings:
    PROJECT_NAME: str = "ANNADATA"
    PROJECT_DESCRIPTION: str = "Field Intelligence & Smart Crop Decision Support"
    VERSION: str = "1.1.0"

    BACKEND_DIR: Path = BACKEND_DIR

    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'annadata.db'}")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    OPEN_METEO_BASE_URL: str = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")
    OPEN_METEO_TIMEOUT_SECONDS: float = float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "10"))

    NOMINATIM_BASE_URL: str = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
    NOMINATIM_USER_AGENT: str = os.getenv(
        "NOMINATIM_USER_AGENT", "ANNADATA/1.1 (field-intelligence-app; contact: admin@annadata.local)"
    )
    NOMINATIM_TIMEOUT_SECONDS: float = float(os.getenv("NOMINATIM_TIMEOUT_SECONDS", "10"))
    NOMINATIM_MIN_INTERVAL_SECONDS: float = float(os.getenv("NOMINATIM_MIN_INTERVAL_SECONDS", "1.0"))

    BACKEND_CORS_ORIGINS: list[str] = _cors_origins()

    # Soil intelligence
    # Directory that holds uploaded Soil Health Cards / laboratory reports.
    # Always kept outside the response layer; stored names are internal only.
    SOIL_REPORT_STORAGE_DIR: Path = Path(
        os.getenv("SOIL_REPORT_STORAGE_DIR", str(BACKEND_DIR / "storage" / "soil_reports"))
    )
    SOIL_REPORT_MAX_SIZE_MB: int = int(os.getenv("SOIL_REPORT_MAX_SIZE_MB", "10"))
    SOIL_REPORT_MAX_SIZE_BYTES: int = SOIL_REPORT_MAX_SIZE_MB * 1024 * 1024

    # AI Crop Disease Identification
    # Directory holding the pre-trained ONNX classifier and its class list.
    # The model file (~92 MB) is NOT committed; see scripts/download_disease_model.py.
    DISEASE_MODEL_DIR: Path = Path(
        os.getenv("DISEASE_MODEL_DIR", str(BACKEND_DIR / "models" / "plant_disease"))
    )
    DISEASE_IMAGE_MAX_SIZE_MB: int = int(os.getenv("DISEASE_IMAGE_MAX_SIZE_MB", "5"))
    DISEASE_IMAGE_MAX_SIZE_BYTES: int = DISEASE_IMAGE_MAX_SIZE_MB * 1024 * 1024
    # Calibrated-confidence floor below which a result is reported as unreliable.
    DISEASE_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("DISEASE_CONFIDENCE_THRESHOLD", "0.60")
    )
    # Guard against decompression-bomb images before Pillow decodes them.
    DISEASE_MAX_IMAGE_PIXELS: int = int(os.getenv("DISEASE_MAX_IMAGE_PIXELS", "50000000"))


settings = Settings()
