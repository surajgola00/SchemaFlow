"""
Schedules router — CRUD for recurring workflow runs via APScheduler.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.schedule import Schedule

router = APIRouter(prefix="/schedules", tags=["schedules"])


class CreateScheduleRequest(BaseModel):
    workflow_id: str
    cron_expression: str
    label: str = ""


class UpdateScheduleRequest(BaseModel):
    enabled: bool | None = None
    cron_expression: str | None = None
    label: str | None = None


def _get_scheduler():  # type: ignore[return]
    """Lazy import to avoid circular imports."""
    try:
        from app.services.scheduler import scheduler_service
        return scheduler_service
    except ImportError:
        return None


@router.get("")
def list_schedules(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    schedules = session.exec(select(Schedule)).all()
    return [
        {
            "id": s.id,
            "workflow_id": s.workflow_id,
            "cron_expression": s.cron_expression,
            "enabled": s.enabled,
            "label": s.label,
            "created_at": s.created_at.isoformat(),
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "last_run_id": s.last_run_id,
        }
        for s in schedules
    ]


@router.post("")
def create_schedule(
    req: CreateScheduleRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    # Validate cron expression
    try:
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger.from_crontab(req.cron_expression, timezone="UTC")
        next_run = trigger.next()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid cron expression: {e}")

    schedule = Schedule(
        workflow_id=req.workflow_id,
        cron_expression=req.cron_expression,
        label=req.label,
        enabled=True,
        next_run_at=next_run,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    svc = _get_scheduler()
    if svc:
        svc.add_schedule(schedule.id, schedule.workflow_id, schedule.cron_expression)

    return {
        "id": schedule.id,
        "workflow_id": schedule.workflow_id,
        "cron_expression": schedule.cron_expression,
        "enabled": schedule.enabled,
        "label": schedule.label,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
    }


@router.get("/{schedule_id}")
def get_schedule(schedule_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {
        "id": schedule.id,
        "workflow_id": schedule.workflow_id,
        "cron_expression": schedule.cron_expression,
        "enabled": schedule.enabled,
        "label": schedule.label,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "last_run_id": schedule.last_run_id,
    }


@router.patch("/{schedule_id}")
def update_schedule(
    schedule_id: str,
    req: UpdateScheduleRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    svc = _get_scheduler()

    if req.enabled is not None:
        schedule.enabled = req.enabled
        if not req.enabled and svc:
            svc.remove_schedule(schedule_id)
        elif req.enabled and svc:
            svc.add_schedule(schedule_id, schedule.workflow_id, schedule.cron_expression)

    if req.cron_expression is not None:
        try:
            from apscheduler.triggers.cron import CronTrigger
            trigger = CronTrigger.from_crontab(req.cron_expression, timezone="UTC")
            schedule.next_run_at = trigger.next()
            schedule.cron_expression = req.cron_expression
            if svc and schedule.enabled:
                svc.add_schedule(schedule_id, schedule.workflow_id, req.cron_expression)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid cron expression: {e}")

    if req.label is not None:
        schedule.label = req.label

    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    return {
        "id": schedule.id,
        "workflow_id": schedule.workflow_id,
        "cron_expression": schedule.cron_expression,
        "enabled": schedule.enabled,
        "label": schedule.label,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
    }


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    svc = _get_scheduler()
    if svc:
        svc.remove_schedule(schedule_id)

    session.delete(schedule)
    session.commit()
    return {"deleted": schedule_id}
