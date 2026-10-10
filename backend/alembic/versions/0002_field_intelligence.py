"""Prompt 2: field intelligence foundation.

Upgrades the Prompt 1 field schema to the field-centric model:

- renames:  name -> field_name, irrigation_type -> water_source
- drops:    water_status (redundant with water_availability)
- adds:     location_accuracy, location_confirmed, locality, sub_district,
            district, state, country, boundary (GeoJSON), area_source
- types:    latitude/longitude promoted to double precision,
            address widened, strict CHECK constraints and indexes added
- legacy data: Prompt 1 water values mapped onto the new enums

Revision ID: 0002_field_intelligence
Revises: 0001_prompt1_initial
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_field_intelligence"
down_revision: Union[str, None] = "0001_prompt1_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_COLUMNS = [
    ("location_accuracy", sa.Double(), True, None),
    ("location_confirmed", sa.Boolean(), False, sa.text("0")),
    ("locality", sa.String(length=120), True, None),
    ("sub_district", sa.String(length=120), True, None),
    ("district", sa.String(length=120), True, None),
    ("state", sa.String(length=120), True, None),
    ("country", sa.String(length=80), True, None),
    ("boundary", sa.JSON(), True, None),
    ("area_source", sa.String(length=30), False, sa.text("'not_provided'")),
]

WATER_SOURCE_LEGACY_MAP = {
    "Rainfed": "rain_fed",
    "Rain-fed": "rain_fed",
    "Rain feed": "rain_fed",
    "Borewell": "borewell",
    "borewell": "borewell",
    "Open well": "open_well",
    "Open well irrigation": "open_well",
    "Canal": "canal",
    "canal": "canal",
    "Drip Irrigation": "other",
    "Drip": "other",
    "Sprinkler": "other",
    "Sprinkler Irrigation": "other",
    "Multiple": "multiple",
    "Other": "other",
    "Not sure": "not_sure",
}

WATER_AVAILABILITY_LEGACY_MAP = {
    "Low": "limited",
    "Medium": "moderate",
    "High": "good",
}


def upgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("fields")}
    field_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("fields")}
    user_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("users")}

    # 1) New columns (plain ADD COLUMN; server defaults cover existing rows).
    for name, type_, nullable, server_default in NEW_COLUMNS:
        if name not in columns:
            op.add_column(
                "fields",
                sa.Column(name, type_, nullable=nullable, server_default=server_default),
            )

    # 2) Backfill defaults before tightening nullability.
    bind.execute(
        sa.text("UPDATE fields SET soil_status = 'not_provided' WHERE soil_status IS NULL OR soil_status = ''")
    )
    bind.execute(
        sa.text("UPDATE fields SET area_unit = 'acre' WHERE area_unit IS NULL OR area_unit = ''")
    )

    # 3) Normalize legacy Prompt 1 water values BEFORE the batch rebuild, because
    #    SQLite copies data into the new table while the new CHECK constraints
    #    are already in place - a legacy value would violate them.
    for legacy, current in WATER_SOURCE_LEGACY_MAP.items():
        bind.execute(
            sa.text("UPDATE fields SET irrigation_type = :current WHERE irrigation_type = :legacy"),
            {"current": current, "legacy": legacy},
        )
    for legacy, current in WATER_AVAILABILITY_LEGACY_MAP.items():
        bind.execute(
            sa.text(
                "UPDATE fields SET water_availability = :current WHERE water_availability = :legacy"
            ),
            {"current": current, "legacy": legacy},
        )

    # 4) Structural changes via batch mode (required on SQLite, plain ALTER on MySQL).
    with op.batch_alter_table("fields") as batch:
        if "name" in columns and "field_name" not in columns:
            batch.alter_column(
                "name",
                new_column_name="field_name",
                existing_type=sa.String(length=100),
                existing_nullable=False,
            )
        if "irrigation_type" in columns:
            batch.alter_column(
                "irrigation_type",
                new_column_name="water_source",
                existing_type=sa.String(length=50),
                existing_nullable=True,
            )
        if "water_status" in columns:
            batch.drop_column("water_status")

        batch.alter_column(
            "area_unit",
            existing_type=sa.String(length=10),
            type_=sa.String(length=20),
            existing_nullable=True,
            nullable=False,
            server_default=sa.text("'acre'"),
        )
        batch.alter_column(
            "soil_status",
            existing_type=sa.String(length=50),
            type_=sa.String(length=20),
            existing_nullable=True,
            nullable=False,
            server_default=sa.text("'not_provided'"),
        )
        batch.alter_column(
            "address",
            existing_type=sa.String(length=255),
            type_=sa.String(length=512),
            existing_nullable=True,
            nullable=True,
        )
        batch.alter_column(
            "latitude",
            existing_type=sa.Float(),
            type_=sa.Double(),
            existing_nullable=True,
            nullable=True,
        )
        batch.alter_column(
            "longitude",
            existing_type=sa.Float(),
            type_=sa.Double(),
            existing_nullable=True,
            nullable=True,
        )

        batch.create_check_constraint(
            "ck_fields_latitude_range",
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
        )
        batch.create_check_constraint(
            "ck_fields_longitude_range",
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
        )
        batch.create_check_constraint(
            "ck_fields_location_accuracy_non_negative",
            "location_accuracy IS NULL OR location_accuracy >= 0",
        )
        batch.create_check_constraint(
            "ck_fields_area_non_negative", "area IS NULL OR area >= 0"
        )
        batch.create_check_constraint(
            "ck_fields_area_source",
            "area_source IN ('calculated_boundary', 'manual', 'not_provided')",
        )
        batch.create_check_constraint(
            "ck_fields_soil_status",
            "soil_status IN ('not_provided', 'pending', 'available')",
        )
        batch.create_check_constraint(
            "ck_fields_water_source",
            "water_source IS NULL OR water_source IN "
            "('rain_fed', 'borewell', 'open_well', 'canal', 'multiple', 'other', 'not_sure')",
        )
        batch.create_check_constraint(
            "ck_fields_water_availability",
            "water_availability IS NULL OR water_availability IN "
            "('limited', 'moderate', 'good', 'seasonal', 'not_sure')",
        )
        batch.create_check_constraint(
            "ck_fields_area_unit",
            "area_unit IN ('acre', 'hectare', 'bigha', 'square_metre')",
        )

        if "ix_fields_user_id" not in field_indexes:
            batch.create_index("ix_fields_user_id", ["user_id"])
        if "ix_fields_lat_lon" not in field_indexes:
            batch.create_index("ix_fields_lat_lon", ["latitude", "longitude"])

    # 5) Suffix indexes on the users table.
    if "ix_users_role" not in user_indexes:
        op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("fields")}

    with op.batch_alter_table("fields") as batch:
        if "field_name" in columns:
            batch.alter_column(
                "field_name",
                new_column_name="name",
                existing_type=sa.String(length=120),
                existing_nullable=False,
            )
        if "water_source" in columns:
            batch.alter_column(
                "water_source",
                new_column_name="irrigation_type",
                existing_type=sa.String(length=30),
                existing_nullable=True,
            )
        if "water_status" not in columns:
            batch.add_column(sa.Column("water_status", sa.String(length=50), nullable=True))

    for name, type_, nullable, server_default in NEW_COLUMNS:
        if name in {c["name"] for c in sa.inspect(bind).get_columns("fields")}:
            op.drop_column("fields", name)

    op.drop_index("ix_users_role", table_name="users")