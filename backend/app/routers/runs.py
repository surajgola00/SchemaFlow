from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from pydantic import BaseModel
import json
import asyncio
from app.database import get_session
from app.models.workflow import Workflow
from app.models.run import ExecutionRun, RunStatus
from app.models.record import ExtractedRecord
from app.services.executor import start_execution_task, run_events

router = APIRouter(prefix="/runs", tags=["runs"])

class StartRunRequest(BaseModel):
    workflow_id: str
    approved_schema: list
    approved_dag: list
    use_mock: bool = True

@router.post("/start")
async def start_run(req: StartRunRequest, session: Session = Depends(get_session)):
    wf = session.get(Workflow, req.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    run = ExecutionRun(
        workflow_id=wf.id,
        status=RunStatus.queued,
        use_mock=req.use_mock
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    
    await start_execution_task(
        run_id=run.id,
        workflow_id=wf.id,
        schema=req.approved_schema,
        dag=req.approved_dag,
        prompt=wf.prompt,
        use_mock=req.use_mock
    )
    
    return {"run_id": run.id, "status": run.status.value}

@router.get("/{run_id}/stream")
async def stream_run(run_id: str, request: Request, session: Session = Depends(get_session)):
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        events_list = run_events.get(run_id, [])
        last_idx = 0
        for ev in events_list:
            yield f"data: {json.dumps(ev)}\n\n"
            last_idx += 1
            if ev.get("type") == "done":
                return
                
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
                run_db = session.get(ExecutionRun, run_id)
                if run_db and run_db.status in [RunStatus.completed, RunStatus.failed]:
                    yield f"data: {json.dumps({'type': 'done', 'status': run_db.status.value})}\n\n"
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/{run_id}/records")
def get_run_records(
    run_id: str, 
    page: int = Query(1, ge=1), 
    page_size: int = Query(20, ge=1, le=100), 
    search: str = None,
    session: Session = Depends(get_session)
):
    offset = (page - 1) * page_size
    query = select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)
    
    total = len(session.exec(query).all())
    records = session.exec(query.offset(offset).limit(page_size)).all()
    
    res = []
    for r in records:
        res.append({
            "id": r.id,
            "data": json.loads(r.data),
            "source_url": r.source_url,
            "source_snippet": r.source_snippet,
            "confidence_score": r.confidence_score,
            "is_duplicate": r.is_duplicate
        })
        
    return {
        "total": total,
        "page": page,
        "records": res
    }

@router.get("/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)):
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "status": run.status,
        "progress_pct": run.progress_pct,
        "compliance_status": json.loads(run.compliance_status),
        "logs": json.loads(run.logs)
    }
