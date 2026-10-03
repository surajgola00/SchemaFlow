"""
APScheduler-based workflow scheduler service.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: AsyncIOScheduler | None = None


def _get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def _run_scheduled_workflow(workflow_id: str, schedule_id: str) -> None:
    """Triggered by APScheduler — starts a new run for the workflow."""
    from sqlmodel import Session, select
    from app.database import engine
    from app.models.workflow import Workflow
    from app.models.run import ExecutionRun, RunStatus
    from app.models.schedule import Schedule
    from app.services.executor.mock_executor import start_execution_task
    from app.services.executor.events import run_events

    with Session(engine) as session:
        wf = session.get(Workflow, workflow_id)
        if not wf:
            return

        run = ExecutionRun(
            workflow_id=wf.id,
            status=RunStatus.queued,
            state="queued",
            engine_mode="demo",
            llm_mode="mock",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

        # Update schedule's last_run_id
        schedule = session.get(Schedule, schedule_id)
        if schedule:
            schedule.last_run_id = run_id
            # Update next_run_at
            try:
                trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone="UTC")
                schedule.next_run_at = trigger.next()
            except Exception:
                pass
            session.add(schedule)
            session.commit()

    # Initialize events
    run_events[run_id] = []

    # Start execution
    await start_execution_task(
        run_id=run_id,
        workflow_id=workflow_id,
        prompt=wf.prompt,
        engine_mode="demo",
    )


class SchedulerService:
    def start(self) -> None:
        sched = _get_scheduler()
        if not sched.running:
            sched.start()
        self._rehydrate()

    def stop(self) -> None:
        sched = _get_scheduler()
        if sched.running:
            sched.shutdown(wait=False)

    def _rehydrate(self) -> None:
        """Load enabled schedules from DB and re-register them."""
        try:
            from sqlmodel import Session, select
            from app.database import engine
            from app.models.schedule import Schedule

            with Session(engine) as session:
                schedules = session.exec(
                    select(Schedule).where(Schedule.enabled == True)  # noqa: E712
                ).all()
                for s in schedules:
                    self.add_schedule(s.id, s.workflow_id, s.cron_expression)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to rehydrate schedules: {e}")

    def add_schedule(self, schedule_id: str, workflow_id: str, cron_expression: str) -> None:
        sched = _get_scheduler()
        try:
            sched.add_job(
                _run_scheduled_workflow,
                CronTrigger.from_crontab(cron_expression, timezone="UTC"),
                id=schedule_id,
                replace_existing=True,
                args=[workflow_id, schedule_id],
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to add schedule {schedule_id}: {e}")

    def remove_schedule(self, schedule_id: str) -> None:
        sched = _get_scheduler()
        try:
            if sched.get_job(schedule_id):
                sched.remove_job(schedule_id)
        except Exception:
            pass


# Module-level singleton
scheduler_service = SchedulerService()


def start_scheduler() -> None:
    scheduler_service.start()


def stop_scheduler() -> None:
    scheduler_service.stop()
