"""
Runs router — start, stream, pause, resume, cancel, records, export, quality, sources.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

import asyncio

from app.database import get_session, engine
from app.models.node_run import NodeRun
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun, RunStatus
from app.models.source_document import SourceDocument
from app.models.workflow import Workflow
from app.models.quality import QualityReport
from app.models.field_provenance import FieldProvenance
from app.models.schedule import RecordFeedback
from app.services.executor.events import run_events, emit_event, add_log
from app.services.executor.task import start_execution_task
from app.services.executor.registry import run_registry

router = APIRouter(prefix="/runs", tags=["runs"])


# ── Request models ────────────────────────────────────────────────────────────

class StartRunRequest(BaseModel):
    workflow_id: str
    approved_schema: list[dict[str, Any]] = []   # backward compat
    approved_dag: list[dict[str, Any]] = []       # backward compat
    use_mock: bool = True
    engine_mode: str = "demo"  # "live" | "demo"
    replay_speed: str = "fast"  # "fast" | "cinematic"


class FeedbackRequest(BaseModel):
    feedback_type: str  # "wrong" | "correct" | "duplicate"
    note: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_run(
    req: StartRunRequest,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    wf = session.get(Workflow, req.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    from app.services.llm.factory import get_llm_mode
    llm_mode = get_llm_mode()

    run = ExecutionRun(
        workflow_id=wf.id,
        status=RunStatus.queued,
        state="queued",
        use_mock=req.use_mock,
        engine_mode=req.engine_mode,
        llm_mode=llm_mode,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    # Initialize event list
    if run.id not in run_events:
        run_events[run.id] = []

    await start_execution_task(
        run_id=run.id,
        workflow_id=wf.id,
        prompt=wf.prompt,
        engine_mode=req.engine_mode,
        use_mock=req.use_mock,
        replay_speed=req.replay_speed,
    )

    return {"run_id": run.id, "status": run.status.value}


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():  # type: ignore[return]
        events_list = run_events.get(run_id, [])
        last_idx = 0

        # First: flush buffered events
        for ev in events_list:
            yield f"data: {json.dumps(ev)}\n\n"
            last_idx += 1
            if ev.get("type") == "done":
                return

        # Then: live poll
        while True:
            if await request.is_disconnected():
                break
            current_events = run_events.get(run_id, [])
            if last_idx < len(current_events):
                for i in range(last_idx, len(current_events)):
                    ev = current_events[i]
                    yield f"data: {json.dumps(ev)}\n\n"
                    if ev.get("type") == "done":
                        return
                last_idx = len(current_events)
            else:
                with Session(engine) as s:
                    run_db = s.get(ExecutionRun, run_id)
                    if run_db and run_db.status in (
                        RunStatus.completed, RunStatus.failed, RunStatus.cancelled
                    ):
                        yield f"data: {json.dumps({'type': 'done', 'status': run_db.status.value})}\n\n"
                        return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{run_id}/records")
def get_run_records(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    min_confidence: float | None = None,
    verified_only: bool = False,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    query = select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)
    all_records = session.exec(query).all()

    # Server-side filtering
    filtered = list(all_records)
    if search:
        search_lower = search.lower()
        filtered = [r for r in filtered if search_lower in r.data.lower()]
    if min_confidence is not None:
        filtered = [r for r in filtered if r.confidence >= min_confidence]
    if verified_only:
        filtered = [r for r in filtered if r.verification_status == "verified"]

    total = len(filtered)
    offset = (page - 1) * page_size
    page_records = filtered[offset:offset + page_size]

    res = []
    for r in page_records:
        res.append({
            "id": r.id,
            "data": json.loads(r.data),
            "source_url": r.source_url,
            "source_snippet": r.source_snippet,
            "confidence_score": r.confidence_score,
            "confidence": r.confidence,
            "is_duplicate": r.is_duplicate,
            "verification_status": r.verification_status,
            "corroboration_count": r.corroboration_count,
            "dedupe_key": r.dedupe_key,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"total": total, "page": page, "records": res}


@router.get("/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    wf = session.get(Workflow, run.workflow_id) if run.workflow_id else None
    return {
        "run_id": run.id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "state": run.state,
        "progress_pct": run.progress_pct,
        "compliance_status": json.loads(run.compliance_status),
        "logs": json.loads(run.logs),
        "engine_mode": run.engine_mode,
        "llm_mode": run.llm_mode,
        "metrics": json.loads(run.metrics_json) if run.metrics_json else {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "dag": json.loads(wf.execution_dag) if wf and wf.execution_dag else [],
        "spec": json.loads(wf.spec_json) if wf and wf.spec_json else None,
    }


@router.get("/{run_id}/nodes")
def get_run_nodes(run_id: str, session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    nodes = session.exec(select(NodeRun).where(NodeRun.run_id == run_id)).all()
    return [
        {
            "id": n.id,
            "run_id": n.run_id,
            "node_id": n.node_id,
            "status": n.status,
            "started_at": n.started_at.isoformat() if n.started_at else None,
            "finished_at": n.finished_at.isoformat() if n.finished_at else None,
            "items_in": n.items_in,
            "items_out": n.items_out,
            "error": n.error,
        }
        for n in nodes
    ]


@router.get("/{run_id}/quality")
def get_run_quality(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    report = session.exec(select(QualityReport).where(QualityReport.run_id == run_id)).first()
    if not report:
        # Generate on-the-fly from records
        records = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
        total = len(records)
        verified = sum(1 for r in records if r.verification_status == "verified")
        return {
            "rows_in": total,
            "rows_out": total,
            "duplicates_merged": 0,
            "verified_ratio": verified / total if total > 0 else 0.0,
            "avg_confidence": sum(r.confidence for r in records) / total if total > 0 else 0.0,
            "validation_failures_by_reason": {},
            "rejection_reasons_by_reason": {},
            "fields_fixed_examples": [],
        }
    return json.loads(report.report_json)


@router.get("/{run_id}/sources")
def get_run_sources(run_id: str, session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    sources = session.exec(select(SourceDocument).where(SourceDocument.run_id == run_id)).all()
    return [
        {
            "id": s.id,
            "url": s.url,
            "canonical_url": s.canonical_url,
            "connector": s.connector,
            "status": s.status,
            "http_status": s.http_status,
            "content_hash": s.content_hash,
            "fetched_at": s.fetched_at.isoformat() if s.fetched_at else None,
            "blocked_reason": s.blocked_reason,
        }
        for s in sources
    ]


@router.post("/{run_id}/pause")
def pause_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run_registry.pause(run_id)
    run.status = RunStatus.paused
    run.state = "paused"
    session.add(run)
    session.commit()
    add_log(run_id, "INFO", "Run paused by user")
    emit_event(run_id, {"type": "run_state", "status": "paused", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat()})
    return {"run_id": run_id, "state": "paused"}


@router.post("/{run_id}/resume")
def resume_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run_registry.resume(run_id)
    run.status = RunStatus.running
    run.state = "running"
    session.add(run)
    session.commit()
    add_log(run_id, "INFO", "Run resumed by user")
    emit_event(run_id, {"type": "run_state", "status": "running", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat()})
    return {"run_id": run_id, "state": "running"}


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run_registry.cancel(run_id)
    run.status = RunStatus.cancelled
    run.state = "cancelled"
    run.finished_at = datetime.now(timezone.utc)
    session.add(run)
    session.commit()
    add_log(run_id, "WARNING", "Run cancelled by user")
    emit_event(run_id, {"type": "done", "status": "cancelled", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat()})
    return {"run_id": run_id, "state": "cancelled"}


@router.post("/{run_id}/retry-failed")
async def retry_failed(run_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Reset failed NodeRun entries
    failed_nodes = session.exec(
        select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.status == "failed")
    ).all()
    for node in failed_nodes:
        node.status = "pending"
        node.error = None
        session.add(node)

    run.status = RunStatus.running
    run.state = "running"
    session.commit()

    add_log(run_id, "INFO", f"Retrying {len(failed_nodes)} failed nodes")
    return {"run_id": run_id, "retried_nodes": len(failed_nodes)}


@router.delete("/{run_id}")
def delete_run(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Delete associated records
    records = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
    for r in records:
        # Delete provenance
        provs = session.exec(select(FieldProvenance).where(FieldProvenance.record_id == r.id)).all()
        for p in provs:
            session.delete(p)
        session.delete(r)

    # Delete node runs
    nodes = session.exec(select(NodeRun).where(NodeRun.run_id == run_id)).all()
    for n in nodes:
        session.delete(n)

    # Delete sources
    sources = session.exec(select(SourceDocument).where(SourceDocument.run_id == run_id)).all()
    for s in sources:
        session.delete(s)

    # Delete quality report
    qr = session.exec(select(QualityReport).where(QualityReport.run_id == run_id)).first()
    if qr:
        session.delete(qr)

    session.delete(run)
    session.commit()

    # Clear events
    from app.services.executor.events import clear_events
    clear_events(run_id)

    return {"deleted": run_id}


@router.post("/{run_id}/save-as-demo")
def save_as_demo(run_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    """Save a completed run as a demo fixture for offline replay."""
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    wf = session.get(Workflow, run.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    records = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
    sources = session.exec(select(SourceDocument).where(SourceDocument.run_id == run_id)).all()

    spec_dict = json.loads(wf.spec_json) if wf.spec_json != "{}" else {}
    records_data = [
        {
            "data": json.loads(r.data),
            "source_url": r.source_url,
            "source_snippet": r.source_snippet,
            "confidence": r.confidence,
            "verification_status": r.verification_status,
            "corroboration_count": r.corroboration_count,
            "dedupe_key": r.dedupe_key,
        }
        for r in records
    ]
    source_docs = [
        {"url": s.url, "title": s.url, "text": s.text[:500], "content_hash": s.content_hash, "connector": s.connector}
        for s in sources
    ]

    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from pathlib import Path
        import hashlib

        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)

        fixture_id = hashlib.md5(wf.prompt.encode()).hexdigest()[:8]
        import json as _json
        fixture = {
            "fixture_id": fixture_id,
            "title": spec_dict.get("title", wf.title or wf.prompt[:50]),
            "entity_type": spec_dict.get("entity_type", wf.entity_type),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "spec": spec_dict,
            "source_docs": source_docs,
            "llm_responses": [],
            "records": records_data,
        }
        (fixtures_dir / f"{fixture_id}.json").write_text(
            _json.dumps(fixture, indent=2, ensure_ascii=False)
        )
        return {"fixture_id": fixture_id, "record_count": len(records_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save fixture: {e}")
