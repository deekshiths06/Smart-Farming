"""Migration tests: fresh database and legacy Prompt 1 database upgrade paths."""

import sqlite3

from alembic import command
from alembic.config import Config

from app.core.config import settings as app_settings


def _config() -> Config:
    cfg = Config(str(app_settings.BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(app_settings.BACKEND_DIR / "alembic"))
    return cfg


def _upgrade(url: str, target: str = "head") -> None:
    app_settings.DATABASE_URL = url
    command.upgrade(_config(), target)


def _cols(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        return [row[1] for row in conn.execute("PRAGMA table_info(fields)")]
    finally:
        conn.close()


def _version(db_path: str) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("select * from alembic_version").fetchall()
    finally:
        conn.close()


def test_fresh_database_upgrade(tmp_path):
    db_path = (tmp_path / "fresh.db").as_posix()
    _upgrade(f"sqlite:///{db_path}")

    cols = set(_cols(db_path))
    assert {"field_name", "water_source"} <= cols
    assert "name" not in cols
    assert "irrigation_type" not in cols
    assert "water_status" not in cols
    for required in (
        "user_id",
        "latitude",
        "longitude",
        "location_accuracy",
        "location_confirmed",
        "locality",
        "sub_district",
        "district",
        "state",
        "country",
        "boundary",
        "area",
        "area_unit",
        "area_source",
        "water_source",
        "water_availability",
        "soil_status",
    ):
        assert required in cols, required
    # Head of the chain: 0001 -> 0002 -> 0003 -> 0004_crop_intelligence.
    assert _version(db_path) == [("0004_crop_intelligence",)]

    conn = sqlite3.connect(db_path)
    try:
        names = [r[0] for r in conn.execute("select name from sqlite_master where type='index'")]
        tables = [r[0] for r in conn.execute("select name from sqlite_master where type='table'")]
        soil_reports_cols = [row[1] for row in conn.execute("PRAGMA table_info(soil_reports)")]
        reference_count = conn.execute("select count(*) from soil_reference_ranges").fetchone()[0]
        crop_count = conn.execute("select count(*) from crops").fetchone()[0]
        requirement_count = conn.execute("select count(*) from crop_requirements").fetchone()[0]
        config_count = conn.execute("select count(*) from crop_scoring_config").fetchone()[0]
        required_source = conn.execute(
            "select count(*) from crops where source is null or trim(source) = ''"
        ).fetchone()[0]
        scored = conn.execute(
            "select count(*) from crop_requirements where factor = 'ph' and min_value is not null"
        ).fetchone()[0]
    finally:
        conn.close()
    assert "ix_fields_user_id" in names
    assert "ix_fields_lat_lon" in names
    # Soil Intelligence tables exist with their key columns, and reference data is seeded.
    assert {"soil_measurements", "soil_reports", "soil_reference_ranges"} <= set(tables)
    assert {"stored_filename", "content_type", "status"} <= set(soil_reports_cols)
    assert reference_count >= 30
    # Crop Intelligence tables exist and the knowledge base is seeded from
    # app.data.crop_knowledge with a source on every crop.
    assert {"crops", "crop_requirements", "crop_scoring_config", "crop_recommendations"} <= set(
        tables
    )
    assert crop_count >= 10
    assert requirement_count >= crop_count
    assert config_count == 1
    assert required_source == 0
    assert scored >= crop_count  # every crop documents a pH band


def test_prompt1_database_upgrade_keeps_and_maps_data(tmp_path):
    """Simulates the real scenario: a Prompt-1 DB with legacy rows upgrades in place."""
    db_path = (tmp_path / "legacy.db").as_posix()

    # Step 1: create the Prompt-1 schema (revision 0001) and drop alembic's stamp.
    _upgrade(f"sqlite:///{db_path}", "0001_prompt1_initial")
    conn = sqlite3.connect(db_path)
    conn.execute("drop table alembic_version")
    conn.execute("delete from fields")
    conn.execute(
        "insert into users (name, email, password_hash) values ('Old', 'old@example.com', 'x')"
    )
    conn.execute(
        "insert into fields (name, user_id, area, area_unit, irrigation_type, "
        "water_availability, latitude, longitude, soil_status, water_status) "
        "values ('Old Field', 1, 3, 'acre', 'Rainfed', 'High', 12.9, 77.5, NULL, 'ok')"
    )
    conn.commit()
    conn.close()

    # Step 2: upgrade to head as a migration would.
    _upgrade(f"sqlite:///{db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(fields)")]
        row = conn.execute("select * from fields where id = 1").fetchone()
        colmap = dict(zip(cols, row))
        version = conn.execute("select * from alembic_version").fetchall()
    finally:
        conn.close()

    # Record survives with renamed + mapped values.
    assert colmap["field_name"] == "Old Field"
    assert colmap["water_source"] == "rain_fed"
    assert colmap["water_availability"] == "good"
    assert colmap["soil_status"] == "not_provided"
    assert colmap["area_unit"] == "acre"
    assert colmap["location_confirmed"] == 0
    assert "water_status" not in colmap  # column dropped
    assert version == [("0004_crop_intelligence",)]


def test_migration_is_idempotent_on_second_run(tmp_path):
    db_path = (tmp_path / "twice.db").as_posix()
    _upgrade(f"sqlite:///{db_path}")
    _upgrade(f"sqlite:///{db_path}")  # already at head -> no-op
    assert _version(db_path) == [("0004_crop_intelligence",)]