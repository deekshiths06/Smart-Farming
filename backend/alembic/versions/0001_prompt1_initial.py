"""Prompt 1 baseline: users and fields tables.

On a database created by Prompt 1 these tables already exist, so this
migration is a no-op there. On a brand new database it recreates the
Prompt 1 schema, which revision 0002 then upgrades - both paths run the
same upgrade code.

Revision ID: 0001_prompt1_initial
Revises:
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_prompt1_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=100), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_users_id", "users", ["id"], unique=False)
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "fields" not in existing:
        op.create_table(
            "fields",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("area", sa.Float(), nullable=True),
            sa.Column("area_unit", sa.String(length=10), nullable=True),
            sa.Column("irrigation_type", sa.String(length=50), nullable=True),
            sa.Column("water_availability", sa.String(length=50), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("address", sa.String(length=255), nullable=True),
            sa.Column("soil_status", sa.String(length=50), nullable=True),
            sa.Column("water_status", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index("ix_fields_id", "fields", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    existing = sa.inspect(bind).get_table_names()
    if "fields" in existing:
        op.drop_table("fields")
    if "users" in existing:
        op.drop_table("users")
