"""Smart Farming Action Planner API.

Ownership follows the rest of ANNADATA: the authenticated user comes from the
JWT and every query filters on the field's ``user_id``. A guessed field or action
id yields 404.

Reading the plan (re)generates the steps supported by the field's current data
and reconciles them into ``field_actions`` by their stable ``action_key``. This
never deletes a row and never changes a completion flag, so completed steps stay
reviewable and completion is only ever set by an explicit request.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.deps import get_db
from app.decision_engine import action_planner
from app.decision_engine import recommendation as engine
from app.decision_engine import soil_context
from app.models.action import (
    ACTION_CATEGORIES,
    FieldAction,
    GROUP_CHECK_LATER,
    GROUP_DO_FIRST,
    GROUP_DO_NEXT,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)
from app.models.crop import CropRecommendation
from app.models.field import Field
from app.models.user import User
from app.schemas.action import ActionPlanRead, ActionRead, ActionUpdate

router = APIRouter()

_PRIORITY_RANK = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
_CATEGORY_RANK = {name: index for index, name in enumerate(ACTION_CATEGORIES)}
_GROUP_RANK = {GROUP_DO_FIRST: 0, GROUP_DO_NEXT: 1, GROUP_CHECK_LATER: 2}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _owned_field(field_id: int, user: User, db: Session) -> Field:
    field = (
        db.query(Field).filter(Field.id == field_id, Field.user_id == user.id).first()
    )
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return field


def _owned_action(field: Field, action_id: int, db: Session) -> FieldAction:
    row = (
        db.query(FieldAction)
        .filter(
            FieldAction.id == action_id,
            FieldAction.field_id == field.id,
            FieldAction.user_id == field.user_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")
    return row


def _latest_results(
    db: Session, field: Field
) -> tuple[list[dict], Optional[datetime], Optional[dict]]:
    """Crop evaluations and weather context from the most recent assessment batch."""
    newest = (
        db.query(CropRecommendation)
        .filter(
            CropRecommendation.field_id == field.id,
            CropRecommendation.user_id == field.user_id,
        )
        .order_by(CropRecommendation.created_at.desc(), CropRecommendation.id.desc())
        .first()
    )
    if newest is None:
        return [], None, None

    rows = (
        db.query(CropRecommendation)
        .filter(
            CropRecommendation.field_id == field.id,
            CropRecommendation.user_id == field.user_id,
            CropRecommendation.batch_id == newest.batch_id,
        )
        .order_by(CropRecommendation.id)
        .all()
    )
    results = [row.result for row in rows if row.result]
    weather = (newest.input_snapshot or {}).get("weather")
    return results, newest.created_at, weather


def _sync(db: Session, field: Field, generated: list[dict]) -> list[FieldAction]:
    """Upsert generated actions, preserving completion state. Never deletes."""
    existing = {
        row.action_key: row
        for row in db.query(FieldAction)
        .filter(FieldAction.field_id == field.id, FieldAction.user_id == field.user_id)
        .all()
    }

    for item in generated:
        row = existing.get(item["action_key"])
        if row is None:
            row = FieldAction(
                user_id=field.user_id,
                field_id=field.id,
                action_key=item["action_key"],
                category=item["category"],
                group_key=item["group_key"],
                title=item["title"],
                explanation=item["explanation"],
                priority=item["priority"],
                timing=item["timing"],
                reason=item["reason"],
                source=item["source"],
                steps=item.get("steps"),
                materials=item.get("materials"),
                check_first=item.get("check_first"),
                avoid=item.get("avoid"),
                done_when=item.get("done_when"),
                details=item["details"],
                completed=False,
                completed_at=None,
            )
            db.add(row)
            existing[item["action_key"]] = row
        else:
            # Refresh the content but never touch ``completed``/``completed_at``.
            row.category = item["category"]
            row.group_key = item["group_key"]
            row.title = item["title"]
            row.explanation = item["explanation"]
            row.priority = item["priority"]
            row.timing = item["timing"]
            row.reason = item["reason"]
            row.source = item["source"]
            row.steps = item.get("steps")
            row.materials = item.get("materials")
            row.check_first = item.get("check_first")
            row.avoid = item.get("avoid")
            row.done_when = item.get("done_when")
            row.details = item["details"]

    db.commit()

    return (
        db.query(FieldAction)
        .filter(FieldAction.field_id == field.id, FieldAction.user_id == field.user_id)
        .all()
    )


def _sorted(rows: list[FieldAction]) -> list[FieldAction]:
    return sorted(
        rows,
        key=lambda row: (
            row.completed,
            _GROUP_RANK.get(row.group_key, 3),
            _PRIORITY_RANK.get(row.priority or "", 3),
            _CATEGORY_RANK.get(row.category, len(_CATEGORY_RANK)),
            row.id,
        ),
    )


def _build_plan(db: Session, field: Field) -> dict:
    config = engine.load_config(db)
    soil = soil_context.build_soil_context(db, field, config["stale_soil_days"])
    results, assessment_at, weather_summary = _latest_results(db, field)
    generated = action_planner.build_actions(
        field,
        soil,
        results,
        weather_summary=weather_summary,
        assessment_at=assessment_at,
    )
    rows = _sorted(_sync(db, field, generated))

    updated_at = max((row.updated_at for row in rows), default=None) or assessment_at
    top = action_planner.top_suitable_crop(results) if results else None

    return {
        "field_id": field.id,
        "field_name": field.field_name,
        "planner_version": action_planner.PLANNER_VERSION,
        "has_assessment": bool(results),
        "assessment_at": assessment_at,
        "top_crop": top.get("display_name") if top else None,
        "updated_at": updated_at,
        "actions": rows,
        "disclaimer": action_planner.ACTION_DISCLAIMER,
    }


@router.get("/fields/{field_id}/actions", response_model=ActionPlanRead)
async def get_actions(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The field's current action plan, with each step's completion state."""
    field = _owned_field(field_id, current_user, db)
    return _build_plan(db, field)


@router.post("/fields/{field_id}/actions/refresh", response_model=ActionPlanRead)
async def refresh_actions(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate the plan from the latest field/soil/assessment data."""
    field = _owned_field(field_id, current_user, db)
    return _build_plan(db, field)


@router.patch(
    "/fields/{field_id}/actions/{action_id}",
    response_model=ActionRead,
)
async def update_action(
    field_id: int,
    action_id: int,
    payload: ActionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a step done or reopen it. ANNADATA never changes this on its own."""
    field = _owned_field(field_id, current_user, db)
    row = _owned_action(field, action_id, db)
    row.completed = payload.completed
    row.completed_at = _utc_now() if payload.completed else None
    db.commit()
    db.refresh(row)
    return row


__all__ = ["router"]
