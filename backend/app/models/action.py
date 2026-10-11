"""Smart Farming Action Planner model.

One table:

- ``field_actions`` - a practical next step for a field, generated from the
  farmer's own recorded data (field profile, soil, live-weather context and the
  most recent crop-suitability assessment). Each row carries the content that
  was shown when it was generated, so a completed action stays reviewable even
  after the underlying data changes.

Completion is a per-field, per-action flag owned by the farmer. It is only ever
changed by an explicit request - ANNADATA never marks an action done on its own.
Deleting a field removes its actions (``ondelete=CASCADE``); nothing else is
ever deleted.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base

# Action categories group the step by the assessment factor it comes from.
CATEGORY_INFORMATION = "information"
CATEGORY_SOIL = "soil"
CATEGORY_WATER = "water"
CATEGORY_WEATHER = "weather"
CATEGORY_CROP = "crop"

ACTION_CATEGORIES: tuple[str, ...] = (
    CATEGORY_INFORMATION,
    CATEGORY_SOIL,
    CATEGORY_WATER,
    CATEGORY_WEATHER,
    CATEGORY_CROP,
)

# Priority is only ever set when it is justified by the data; routine steps may
# carry no priority at all.
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

ACTION_PRIORITIES: tuple[str, ...] = (PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW)

# The page groups steps so a farmer reads the most useful ones first. "Completed"
# is not a stored group - it is simply any step whose ``completed`` flag is set.
GROUP_DO_FIRST = "do_first"
GROUP_DO_NEXT = "do_next"
GROUP_CHECK_LATER = "check_later"

ACTION_GROUPS: tuple[str, ...] = (GROUP_DO_FIRST, GROUP_DO_NEXT, GROUP_CHECK_LATER)

GROUP_LABELS: dict[str, str] = {
    GROUP_DO_FIRST: "Do first",
    GROUP_DO_NEXT: "Do next",
    GROUP_CHECK_LATER: "Check later",
}


def _sql_list(values: tuple[str, ...]) -> str:
    return "(" + ",".join(f"'{v}'" for v in values) + ")"


class FieldAction(Base):
    """A single practical step for one field, with its completion state."""

    __tablename__ = "field_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id = Column(
        Integer,
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stable identity of the action (e.g. ``soil:add_test``), so regenerating
    # the plan reconnects to the same row and never loses its completion state.
    action_key = Column(String(80), nullable=False)

    category = Column(String(30), nullable=False)
    group_key = Column(
        String(20), nullable=False, default=GROUP_DO_NEXT, server_default=GROUP_DO_NEXT
    )
    title = Column(String(200), nullable=False)
    explanation = Column(String(1000), nullable=False)
    priority = Column(String(10), nullable=True)
    timing = Column(String(120), nullable=True)
    reason = Column(String(500), nullable=False)
    source = Column(String(160), nullable=False)

    # Practical detail shown when a step is expanded. Each is a short, plain
    # list of strings; ``done_when`` is a single sentence.
    steps = Column(JSON, nullable=True)
    materials = Column(JSON, nullable=True)
    check_first = Column(JSON, nullable=True)
    avoid = Column(JSON, nullable=True)
    done_when = Column(String(300), nullable=True)

    # Extra, structured context (e.g. the weather risk kind/severity/basis).
    details = Column(JSON, nullable=True)

    completed = Column(Boolean, nullable=False, default=False, server_default="0")
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now(), server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now(), server_default=func.now()
    )

    owner = relationship("User", back_populates="actions", passive_deletes=True)
    field = relationship("Field", back_populates="actions")

    __table_args__ = (
        CheckConstraint(
            "category IN " + _sql_list(ACTION_CATEGORIES),
            name="ck_field_actions_category",
        ),
        CheckConstraint(
            "priority IS NULL OR priority IN " + _sql_list(ACTION_PRIORITIES),
            name="ck_field_actions_priority",
        ),
        UniqueConstraint("field_id", "action_key", name="uq_field_actions_field_key"),
        Index("ix_field_actions_field_completed", "field_id", "completed"),
    )


__all__ = [
    "FieldAction",
    "ACTION_CATEGORIES",
    "ACTION_GROUPS",
    "ACTION_PRIORITIES",
    "GROUP_LABELS",
    "CATEGORY_INFORMATION",
    "CATEGORY_SOIL",
    "CATEGORY_WATER",
    "CATEGORY_WEATHER",
    "CATEGORY_CROP",
    "GROUP_DO_FIRST",
    "GROUP_DO_NEXT",
    "GROUP_CHECK_LATER",
    "PRIORITY_HIGH",
    "PRIORITY_MEDIUM",
    "PRIORITY_LOW",
]
