"""
Execution Task Dispatcher — runs DAG engine for live execution or mock/demo executor for replay.
"""
from __future__ import annotations

import asyncio
from sqlmodel import Session

from app.database import engine
from app.models.run import ExecutionRun, RunStatus
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowSpec
from app.services.executor.context import RunContext
from app.services.executor.engine import DagEngine
from app.services.executor.events import get_emitter
from app.services.executor.mock_executor import run_demo_execution
from app.services.executor.registry import run_registry
from app.services.llm.factory import get_llm


async def start_execution_task(
    run_id: str,
    workflow_id: str,
    prompt: str,
    engine_mode: str = "demo",
    use_mock: bool = True,
    replay_speed: str = "fast",
) -> None:
    cancel_event = asyncio.Event()
    pause_event = asyncio.Event()

    async def _runner() -> None:
        try:
            import json
            from app.config import get_settings
            from app.services.demo.fixture_manager import fixture_manager

            settings = get_settings()
            speed = replay_speed or settings.demo_replay_speed

            # 1. Fetch workflow
            with Session(engine) as session:
                wf = session.get(Workflow, workflow_id)
                spec_dict = {}
                if wf and wf.spec_json:
                    spec_dict = json.loads(wf.spec_json)

            fixture_docs: list[dict] = []
            fixture_records: list[dict] = []

            if engine_mode == "demo" or use_mock:
                p = (prompt or (wf.prompt if wf else "")).lower()
                if any(w in p for w in ("job", "intern", "hiring", "career", "python")):
                    fid = "remote_python_internships"
                elif any(w in p for w in ("repo", "github", "library", "framework")):
                    fid = "open_source_ml_repos"
                elif any(w in p for w in ("arxiv", "paper", "rag", "research")):
                    fid = "arxiv_rag_papers"
                elif any(w in p for w in ("sponsor", "newsletter", "media kit")):
                    fid = "tech_sponsorship_opportunities"
                else:
                    fid = "ai_startups_india"

                fix = fixture_manager.load_fixture(fid)
                if fix:
                    fixture_docs = fix.get("source_docs", [])
                    fixture_records = fix.get("records", [])
                    if not spec_dict and fix.get("spec"):
                        spec_dict = fix["spec"]

            if not spec_dict:
                from app.services.llm.mock import _startup_spec
                spec_dict = _startup_spec()

            spec = WorkflowSpec.model_validate(spec_dict)
            llm = get_llm(force_mock=(engine_mode == "demo" or use_mock))
            emit = get_emitter(run_id)

            ctx = RunContext(
                run_id=run_id,
                workflow_id=workflow_id,
                spec=spec,
                llm=llm,
                emit=emit,
                cancel_event=cancel_event,
                pause_event=pause_event,
                counters={"pages": 0, "records": 0, "verified": 0, "rejected": 0},
                budget={
                    "max_pages": spec.limits.get("max_pages", 30),
                    "max_records": spec.limits.get("max_records", 100),
                    "max_runtime_seconds": 300,
                },
                engine_mode=engine_mode,
                replay_speed=speed,
                fixture_docs=fixture_docs,
                fixture_records=fixture_records,
            )

            dag_engine = DagEngine()
            await dag_engine.run(ctx)

        except Exception as e:
            with Session(engine) as session:
                run = session.get(ExecutionRun, run_id)
                if run:
                    run.status = RunStatus.failed
                    session.add(run)
                    session.commit()
            emit = get_emitter(run_id)
            emit({"type": "done", "status": "failed", "run_id": run_id, "error": str(e)})

    task = asyncio.create_task(_runner())
    run_registry.register(run_id, task, cancel_event, pause_event)
