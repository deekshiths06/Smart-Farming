"""Prompt 8: expandable crop catalogue.

Widens the seeded knowledge base beyond the original twelve crops so the
recommendation engine can discover and rank a broader range of crops. The data
itself lives in ``app.data.crop_knowledge`` (sourced agronomic bands, not
invented thresholds) and the 0004 migration seeded the first twelve rows.

This migration is *additive and idempotent*: it inserts any catalogue crop that
is not already present by name, and any of its requirements that are missing.
Existing rows - including admin edits - are left untouched, so it is safe to run
against a live database and safe to re-run.

Revision ID: 0007_crop_catalogue_expansion
Revises: 0006_action_planner_details
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.data.crop_knowledge import CROPS

revision: str = "0007_crop_catalogue_expansion"
down_revision: Union[str, None] = "0006_action_planner_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The crops seeded by migration 0004 (the original fixed list).
_ORIGINAL_NAMES = (
    "rice",
    "maize",
    "wheat",
    "sorghum",
    "pearl_millet",
    "finger_millet",
    "groundnut",
    "chickpea",
    "pigeonpea",
    "green_gram",
    "cotton",
    "tomato",
)

_ADDED_NAMES = tuple(c["name"] for c in CROPS if c["name"] not in _ORIGINAL_NAMES)


def _quoted(names: tuple[str, ...]) -> str:
    return "(" + ",".join("'" + n.replace("'", "''") + "'" for n in names) + ")"


def upgrade() -> None:
    conn = op.get_bind()

    for crop in CROPS:
        row = conn.execute(
            sa.text("SELECT id FROM crops WHERE name = :name"), {"name": crop["name"]}
        ).first()
        if row is not None:
            crop_id = row[0]
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO crops "
                    "(name, display_name, category, description, is_active, "
                    " source, source_url, date_reviewed) "
                    "VALUES (:name, :display_name, :category, :description, 1, "
                    " :source, :source_url, :date_reviewed)"
                ),
                {
                    "name": crop["name"],
                    "display_name": crop["display_name"],
                    "category": crop["category"],
                    "description": crop["description"],
                    "source": crop["source"],
                    "source_url": crop.get("source_url"),
                    "date_reviewed": crop["date_reviewed"],
                },
            )
            crop_id = conn.execute(
                sa.text("SELECT id FROM crops WHERE name = :name"), {"name": crop["name"]}
            ).scalar()

        for req in crop["requirements"]:
            present = conn.execute(
                sa.text(
                    "SELECT id FROM crop_requirements "
                    "WHERE crop_id = :crop_id AND factor = :factor"
                ),
                {"crop_id": crop_id, "factor": req["factor"]},
            ).first()
            if present is not None:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO crop_requirements "
                    "(crop_id, factor, min_value, max_value, allowed_values, "
                    " is_essential, explanation, source, source_url, sequence, is_active) "
                    "VALUES (:crop_id, :factor, :min_value, :max_value, :allowed_values, "
                    " :is_essential, :explanation, :source, :source_url, :sequence, 1)"
                ),
                {
                    "crop_id": crop_id,
                    "factor": req["factor"],
                    "min_value": req.get("min_value"),
                    "max_value": req.get("max_value"),
                    "allowed_values": sa_json(req.get("values")),
                    "is_essential": bool(req.get("is_essential", False)),
                    "explanation": req.get("explanation"),
                    "source": req["source"],
                    "source_url": req.get("source_url"),
                    "sequence": req.get("sequence", 0),
                },
            )


def sa_json(value):
    """JSON-encode a value for the ``allowed_values`` JSON column."""
    import json

    if value is None:
        return None
    return json.dumps(value)


def downgrade() -> None:
    if not _ADDED_NAMES:
        return
    conn = op.get_bind()
    names = _quoted(_ADDED_NAMES)
    conn.execute(
        sa.text(
            "DELETE FROM crop_requirements WHERE crop_id IN "
            "(SELECT id FROM crops WHERE name IN " + names + ")"
        )
    )
    conn.execute(sa.text("DELETE FROM crops WHERE name IN " + names))
