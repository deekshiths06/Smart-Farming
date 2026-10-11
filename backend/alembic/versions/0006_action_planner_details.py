"""Prompt 7 (extended): richer, plainer Action Planner steps.

Adds the fields the redesigned planner page needs to the existing
``field_actions`` table:

- ``group_key``  - whether the step is shown under "Do first", "Do next" or
  "Check later" (Completed is derived from the completion flag, not stored);
- ``steps``      - the numbered "How to do it" list;
- ``materials``  - the short "What is needed" list;
- ``check_first``- the "What to check first" list;
- ``avoid``      - the "What to avoid" list;
- ``done_when``  - one plain sentence for "How you know it is done".

Additive only and safe on existing data: ``group_key`` gets a server default so
any row written by revision 0005 keeps working, and the list/sentence columns are
nullable.

Revision ID: 0006_action_planner_details
Revises: 0005_action_planner
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_action_planner_details"
down_revision: Union[str, None] = "0005_action_planner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "field_actions",
        sa.Column(
            "group_key",
            sa.String(length=20),
            nullable=False,
            server_default="do_next",
        ),
    )
    op.add_column("field_actions", sa.Column("steps", sa.JSON(), nullable=True))
    op.add_column("field_actions", sa.Column("materials", sa.JSON(), nullable=True))
    op.add_column("field_actions", sa.Column("check_first", sa.JSON(), nullable=True))
    op.add_column("field_actions", sa.Column("avoid", sa.JSON(), nullable=True))
    op.add_column("field_actions", sa.Column("done_when", sa.String(length=300), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("field_actions") as batch:
        batch.drop_column("done_when")
        batch.drop_column("avoid")
        batch.drop_column("check_first")
        batch.drop_column("materials")
        batch.drop_column("steps")
        batch.drop_column("group_key")
