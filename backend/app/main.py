import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import actions, admin, auth, catalogue, crops, disease, fields, health, location, soil
from app.core.config import settings

logger = logging.getLogger("annadata")


def run_migrations() -> None:
    """Apply Alembic migrations on startup (documented, versioned schema)."""
    from alembic import command
    from alembic.config import Config

    ini_path = settings.BACKEND_DIR / "alembic.ini"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(settings.BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        run_migrations()
    except Exception:
        logger.exception("Database migration failed - refusing to start with an unknown schema")
        raise
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(fields.router, prefix="/api/fields", tags=["fields"])
app.include_router(location.router, prefix="/api/location", tags=["location"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(soil.router, prefix="/api/fields/{field_id}/soil", tags=["soil"])
app.include_router(crops.router, prefix="/api", tags=["crops"])
app.include_router(catalogue.router, prefix="/api/catalogue", tags=["catalogue"])
app.include_router(actions.router, prefix="/api", tags=["actions"])
app.include_router(disease.router, prefix="/api/disease", tags=["disease"])
