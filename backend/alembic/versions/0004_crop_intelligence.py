"""Prompt 6: Crop Intelligence Engine.

Adds the crop knowledge base (crops + per-crop agronomic requirements), the
persisted crop recommendations, and the single admin-editable scoring config.
Seeds the knowledge base from ``app.data.crop_knowledge`` (sourced agronomic
guidance, not invented thresholds).

Revision ID: 0004_crop_intelligence
Revises: 0003_soil_intelligence
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.data.crop_knowledge import CROPS, SCORING_CONFIG

from datetime import date as _date
revision: str = "0004_crop_intelligence"
down_revision: Union[str, None] = "0003_soil_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES = ("cereal", "millet", "pulse", "oilseed", "fibre", "vegetable")
FACTORS = (
    "ph",
    "texture",
    "water",
    "season",
    "region",
    "temperature",
    "rainfall",
    "duration",
)
STATUSES = ("suitable", "not_recommended", "needs_information")


def _sql_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


def upgrade() -> None:
    crops_table = op.create_table(
        "crops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=60), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=300), nullable=True),
        sa.Column("date_reviewed", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("category IN " + _sql_list(CATEGORIES), name="ck_crops_category"),
    )
    op.create_index("ix_crops_name", "crops", ["name"])
    op.create_index("ix_crops_category", "crops", ["category"])

    requirements_table = op.create_table(
        "crop_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "crop_id",
            sa.Integer(),
            sa.ForeignKey("crops.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("factor", sa.String(length=30), nullable=False),
        sa.Column("min_value", sa.Double(), nullable=True),
        sa.Column("max_value", sa.Double(), nullable=True),
        sa.Column("allowed_values", sa.JSON(), nullable=True),
        sa.Column("is_essential", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("explanation", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.String(length=300), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("factor IN " + _sql_list(FACTORS), name="ck_crop_requirements_factor"),
        sa.CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value <= max_value",
            name="ck_crop_requirements_min_max",
        ),
        sa.UniqueConstraint("crop_id", "factor", name="uq_crop_requirements_crop_factor"),
    )
    op.create_index("ix_crop_requirements_crop_id", "crop_requirements", ["crop_id"])
    op.create_index("ix_crop_requirements_factor", "crop_requirements", ["factor"])

    scoring_table = op.create_table(
        "crop_scoring_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("essential_factors", sa.JSON(), nullable=False),
        sa.Column("suitable_threshold", sa.Double(), nullable=False, server_default="0.65"),
        sa.Column("min_coverage", sa.Double(), nullable=False, server_default="0.5"),
        sa.Column("stale_soil_days", sa.Integer(), nullable=False, server_default="1095"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "suitable_threshold >= 0 AND suitable_threshold <= 1",
            name="ck_crop_scoring_config_suitable",
        ),
        sa.CheckConstraint(
            "min_coverage >= 0 AND min_coverage <= 1",
            name="ck_crop_scoring_config_coverage",
        ),
        sa.CheckConstraint("stale_soil_days >= 0", name="ck_crop_scoring_config_stale"),
    )

    op.create_table(
        "crop_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "field_id",
            sa.Integer(),
            sa.ForeignKey("fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "crop_id",
            sa.Integer(),
            sa.ForeignKey("crops.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("batch_id", sa.String(length=40), nullable=False),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("season", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("coverage", sa.Double(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN " + _sql_list(STATUSES), name="ck_crop_recommendations_status"),
    )
    op.create_index("ix_crop_recommendations_field_id", "crop_recommendations", ["field_id"])
    op.create_index("ix_crop_recommendations_user_id", "crop_recommendations", ["user_id"])
    op.create_index("ix_crop_recommendations_crop_id", "crop_recommendations", ["crop_id"])
    op.create_index("ix_crop_recommendations_batch_id", "crop_recommendations", ["batch_id"])
    op.create_index("ix_crop_recommendations_status", "crop_recommendations", ["status"])
    op.create_index(
        "ix_crop_recommendations_field_created",
        "crop_recommendations",
        ["field_id", "created_at"],
    )

    # --- Seed the knowledge base -------------------------------------------------
    crop_rows = []
    requirement_rows = []
    for index, crop in enumerate(CROPS, start=1):
        crop_rows.append(
            {
                "id": index,
                "name": crop["name"],
                "display_name": crop["display_name"],
                "category": crop["category"],
                "description": crop["description"],
                "is_active": True,
                "source": crop["source"],
                "source_url": crop.get("source_url"),
                "date_reviewed": _date.fromisoformat(crop["date_reviewed"]),
            }
        )
        for req in crop["requirements"]:
            requirement_rows.append(
                {
                    "crop_id": index,
                    "factor": req["factor"],
                    "min_value": req.get("min_value"),
                    "max_value": req.get("max_value"),
                    "allowed_values": req.get("values"),
                    "is_essential": bool(req.get("is_essential", False)),
                    "explanation": req.get("explanation"),
                    "source": req["source"],
                    "source_url": req.get("source_url"),
                    "sequence": req.get("sequence", 0),
                    "is_active": True,
                }
            )

    op.bulk_insert(crops_table, crop_rows)
    op.bulk_insert(requirements_table, requirement_rows)

    op.bulk_insert(
        scoring_table,
        [
            {
                "id": 1,
                "weights": SCORING_CONFIG["weights"],
                "essential_factors": SCORING_CONFIG["essential_factors"],
                "suitable_threshold": SCORING_CONFIG["suitable_threshold"],
                "min_coverage": SCORING_CONFIG["min_coverage"],
                "stale_soil_days": SCORING_CONFIG["stale_soil_days"],
                "is_active": SCORING_CONFIG["is_active"],
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_crop_recommendations_field_created", table_name="crop_recommendations")
    op.drop_index("ix_crop_recommendations_status", table_name="crop_recommendations")
    op.drop_index("ix_crop_recommendations_batch_id", table_name="crop_recommendations")
    op.drop_index("ix_crop_recommendations_crop_id", table_name="crop_recommendations")
    op.drop_index("ix_crop_recommendations_user_id", table_name="crop_recommendations")
    op.drop_index("ix_crop_recommendations_field_id", table_name="crop_recommendations")
    op.drop_table("crop_recommendations")
    op.drop_table("crop_scoring_config")
    op.drop_index("ix_crop_requirements_factor", table_name="crop_requirements")
    op.drop_index("ix_crop_requirements_crop_id", table_name="crop_requirements")
    op.drop_table("crop_requirements")
    op.drop_index("ix_crops_category", table_name="crops")
    op.drop_index("ix_crops_name", table_name="crops")
    op.drop_table("crops")
