"""Prompt 7: Smart Farming Action Planner.

Adds ``field_actions`` - one row per generated practical step for a field. The
row keeps the content shown when it was generated (title, explanation, priority,
timing, reason, source) and the farmer's completion state, so completed steps
stay reviewable and completion is never lost when the plan is regenerated.

Additive only: no existing table or row is modified.

Revision ID: 0005_action_planner
Revises: 0004_crop_intelligence
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_action_planner"
down_revision: Union[str, None] = "0004_crop_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES = ("information", "soil", "water", "weather", "crop")
PRIORITIES = ("high", "medium", "low")


def _sql_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "field_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey("fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_key", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("explanation", sa.String(length=1000), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=True),
        sa.Column("timing", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "category IN " + _sql_list(CATEGORIES), name="ck_field_actions_category"
        ),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN " + _sql_list(PRIORITIES),
            name="ck_field_actions_priority",
        ),
        sa.UniqueConstraint("field_id", "action_key", name="uq_field_actions_field_key"),
    )
    op.create_index("ix_field_actions_id", "field_actions", ["id"])
    op.create_index("ix_field_actions_user_id", "field_actions", ["user_id"])
    op.create_index("ix_field_actions_field_id", "field_actions", ["field_id"])
    op.create_index(
        "ix_field_actions_field_completed", "field_actions", ["field_id", "completed"]
    )


def downgrade() -> None:
    op.drop_index("ix_field_actions_field_completed", table_name="field_actions")
    op.drop_index("ix_field_actions_field_id", table_name="field_actions")
    op.drop_index("ix_field_actions_user_id", table_name="field_actions")
    op.drop_index("ix_field_actions_id", table_name="field_actions")
    op.drop_table("field_actions")
