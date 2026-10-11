"""Prompt 9: AI Crop Disease Identification.

Adds ``disease_assessments`` - one row per leaf-image screening a signed-in user
runs. Only image metadata is stored (never the bytes), plus the model's actual
output and result status.

Additive only: no existing table or row is modified.

Revision ID: 0008_disease_identification
Revises: 0007_crop_catalogue_expansion
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_disease_identification"
down_revision: Union[str, None] = "0007_crop_catalogue_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUSES = ("identified", "healthy", "low_confidence", "crop_mismatch")


def _sql_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    op.create_table(
        "disease_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("crop", sa.String(length=40), nullable=False),
        sa.Column("crop_label", sa.String(length=80), nullable=False),
        sa.Column("image_filename", sa.String(length=255), nullable=False),
        sa.Column("image_content_type", sa.String(length=100), nullable=False),
        sa.Column("image_size_bytes", sa.Integer(), nullable=False),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("predicted_class", sa.String(length=160), nullable=True),
        sa.Column("predicted_crop", sa.String(length=80), nullable=True),
        sa.Column("predicted_crop_label", sa.String(length=80), nullable=True),
        sa.Column("predicted_disease_label", sa.String(length=160), nullable=True),
        sa.Column("is_healthy", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Double(), nullable=True),
        sa.Column("candidates", sa.JSON(), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("disclaimer", sa.String(length=700), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN " + _sql_list(STATUSES), name="ck_disease_assessments_status"
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_disease_assessments_confidence_range",
        ),
        sa.CheckConstraint(
            "image_size_bytes >= 0", name="ck_disease_assessments_image_size_non_negative"
        ),
    )
    op.create_index("ix_disease_assessments_id", "disease_assessments", ["id"])
    op.create_index("ix_disease_assessments_user_id", "disease_assessments", ["user_id"])
    op.create_index(
        "ix_disease_assessments_user_created", "disease_assessments", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_disease_assessments_user_created", table_name="disease_assessments")
    op.drop_index("ix_disease_assessments_user_id", table_name="disease_assessments")
    op.drop_index("ix_disease_assessments_id", table_name="disease_assessments")
    op.drop_table("disease_assessments")
