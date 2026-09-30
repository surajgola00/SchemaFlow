from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
import json
from app.database import get_session
from app.models.workflow import Workflow
from app.models.run import ExecutionRun
from app.services.compiler import compile_workflow

router = APIRouter(tags=["workflows"])

class CompileRequest(BaseModel):
    prompt: str
    use_mock: bool = True

@router.post("/compile")
def compile_workflow_endpoint(req: CompileRequest, session: Session = Depends(get_session)):
    target_schema, execution_dag = compile_workflow(req.prompt, req.use_mock)
    
    wf = Workflow(
        prompt=req.prompt,
        target_schema=target_schema,
        execution_dag=execution_dag
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)
    
    return {
        "workflow_id": wf.id,
        "target_schema": json.loads(wf.target_schema),
        "execution_dag": json.loads(wf.execution_dag),
        "prompt": wf.prompt
    }

@router.get("/history")
def get_history(session: Session = Depends(get_session)):
    workflows = session.exec(select(Workflow)).all()
    history = []
    for wf in workflows:
        runs = session.exec(select(ExecutionRun).where(ExecutionRun.workflow_id == wf.id)).all()
        runs_data = []
        for r in runs:
            from app.models.record import ExtractedRecord
            count = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == r.id)).all()
            runs_data.append({
                "run_id": r.id,
                "status": r.status,
                "record_count": len(count),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None
            })
        history.append({
            "workflow": {
                "id": wf.id,
                "prompt": wf.prompt,
                "target_schema": json.loads(wf.target_schema),
                "execution_dag": json.loads(wf.execution_dag),
                "created_at": wf.created_at.isoformat() if wf.created_at else None
            },
            "runs": runs_data
        })
    return history
