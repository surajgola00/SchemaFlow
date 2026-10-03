"""
Workflows router — compile, edit, clone, history, and system status.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowSpec
from app.services.compiler.service import CompilerService
from app.services.llm.factory import get_llm, get_llm_mode

router = APIRouter(tags=["workflows"])


# ── Request / Response models ─────────────────────────────────────────────────

class CompileRequest(BaseModel):
    prompt: str
    use_mock: bool = True  # backward compat; ignored — mode auto-detected from env


class CompileResponse(BaseModel):
    workflow_id: str
    prompt: str
    spec: dict[str, Any]
    # Backward-compat fields
    target_schema: list[dict[str, Any]]
    execution_dag: list[dict[str, Any]]


class UpdateWorkflowRequest(BaseModel):
    spec: dict[str, Any]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _spec_to_legacy(spec: WorkflowSpec) -> tuple[list[dict], list[dict]]:
    """Convert WorkflowSpec to legacy target_schema + execution_dag format."""
    target_schema = [
        {
            "name": f.name,
            "type": f.type,
            "required": f.required,
            "description": f.description,
            "unique_key": f.unique_key,
            "validators": f.validators,
        }
        for f in spec.fields
    ]
    execution_dag = [
        {
            "step": i + 1,
            "name": node.label,
            "description": f"Node type: {node.type}",
            "id": node.id,
            "type": node.type,
            "depends_on": node.depends_on,
            "status": "pending",
        }
        for i, node in enumerate(spec.dag)
    ]
    return target_schema, execution_dag


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/system/status")
def system_status() -> dict[str, Any]:
    """Return LLM mode, model, search provider, version, and any configuration warnings. Never raises."""
    warnings: list[str] = []
    try:
        settings = get_settings()
        llm_mode = get_llm_mode()
        model = settings.llm_model if settings.llm_api_key.strip() else "mock"
        search_provider = settings.search_provider
    except Exception as e:
        llm_mode = "mock"
        model = "mock"
        search_provider = "duckduckgo_html"
        warnings.append(f"Configuration error: {str(e)}")

    return {
        "llm_mode": llm_mode,
        "model": model,
        "search_provider": search_provider,
        "version": "2.0",
        "warnings": warnings,
    }


@router.post("/compile")
async def compile_workflow_endpoint(
    req: CompileRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    llm = get_llm(force_mock=req.use_mock)
    service = CompilerService(llm)
    try:
        spec = await service.compile(req.prompt)
    except Exception as e:
        from app.services.llm.client import LLMConfigurationError
        if isinstance(e, LLMConfigurationError):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow compilation failed: {str(e)}")

    target_schema, execution_dag = _spec_to_legacy(spec)

    wf = Workflow(
        prompt=req.prompt,
        target_schema=json.dumps(target_schema),
        execution_dag=json.dumps(execution_dag),
        spec_json=spec.model_dump_json(),
        title=spec.title,
        entity_type=spec.entity_type,
    )
    session.add(wf)
    session.commit()
    session.refresh(wf)

    return {
        "workflow_id": wf.id,
        "prompt": wf.prompt,
        "spec": spec.model_dump(),
        # Backward compat
        "target_schema": target_schema,
        "execution_dag": execution_dag,
    }


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: str,
    req: UpdateWorkflowRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Save user-edited WorkflowSpec back to the workflow."""
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        spec = WorkflowSpec.model_validate(req.spec)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid spec: {e}")

    target_schema, execution_dag = _spec_to_legacy(spec)

    wf.spec_json = spec.model_dump_json()
    wf.target_schema = json.dumps(target_schema)
    wf.execution_dag = json.dumps(execution_dag)
    wf.title = spec.title
    wf.entity_type = spec.entity_type
    session.add(wf)
    session.commit()
    session.refresh(wf)

    return {
        "workflow_id": wf.id,
        "spec": spec.model_dump(),
        "target_schema": target_schema,
        "execution_dag": execution_dag,
    }


@router.post("/workflows/{workflow_id}/clone")
def clone_workflow(
    workflow_id: str,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Clone a workflow, creating a new one with parent_id set."""
    wf = session.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    clone = Workflow(
        prompt=wf.prompt,
        target_schema=wf.target_schema,
        execution_dag=wf.execution_dag,
        spec_json=wf.spec_json,
        title=f"{wf.title} (Copy)" if wf.title else wf.prompt[:50],
        entity_type=wf.entity_type,
        parent_id=wf.id,
        version=wf.version + 1,
    )
    session.add(clone)
    session.commit()
    session.refresh(clone)

    return {"workflow_id": clone.id, "parent_id": clone.parent_id}


@router.get("/history")
def get_history(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    workflows = session.exec(select(Workflow).order_by(Workflow.created_at.desc())).all()  # type: ignore[arg-type]
    history = []
    for wf in workflows:
        runs = session.exec(
            select(ExecutionRun).where(ExecutionRun.workflow_id == wf.id)
        ).all()
        runs_data = []
        for r in runs:
            count = len(
                session.exec(
                    select(ExtractedRecord).where(ExtractedRecord.run_id == r.id)
                ).all()
            )
            runs_data.append({
                "run_id": r.id,
                "status": r.status,
                "record_count": count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            })
        history.append({
            "workflow": {
                "id": wf.id,
                "prompt": wf.prompt,
                "title": wf.title,
                "entity_type": wf.entity_type,
                "target_schema": json.loads(wf.target_schema),
                "execution_dag": json.loads(wf.execution_dag),
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
            },
            "runs": runs_data,
        })
    return history
