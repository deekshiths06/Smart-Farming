"""Smart Farming Action Planner schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ActionRead(BaseModel):
    id: int
    action_key: str
    category: str
    group_key: str
    title: str
    explanation: str
    priority: Optional[str] = None
    timing: Optional[str] = None
    reason: str
    source: str
    steps: Optional[list[str]] = None
    materials: Optional[list[str]] = None
    check_first: Optional[list[str]] = None
    avoid: Optional[list[str]] = None
    done_when: Optional[str] = None
    details: Optional[dict] = None
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    completed: bool


class ActionPlanRead(BaseModel):
    field_id: int
    field_name: str
    planner_version: str
    has_assessment: bool
    assessment_at: Optional[datetime] = None
    top_crop: Optional[str] = None
    updated_at: Optional[datetime] = None
    actions: list[ActionRead]
    disclaimer: str


__all__ = ["ActionRead", "ActionUpdate", "ActionPlanRead"]
