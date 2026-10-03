"""
Datasets router — versioned dataset management and diff view.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.dataset import Dataset, DatasetVersion
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun
from app.models.workflow import Workflow

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _get_or_create_dataset(workflow_id: str, session: Session) -> Dataset:
    """Get or create Dataset for a workflow."""
    existing = session.exec(
        select(Dataset).where(Dataset.workflow_id == workflow_id)
    ).first()
    if existing:
        return existing
    wf = session.get(Workflow, workflow_id)
    ds = Dataset(
        workflow_id=workflow_id,
        title=wf.title if wf else "",
        entity_type=wf.entity_type if wf else "",
    )
    session.add(ds)
    session.commit()
    session.refresh(ds)
    return ds


@router.get("")
def list_datasets(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    datasets = session.exec(select(Dataset)).all()
    result = []
    for ds in datasets:
        versions = session.exec(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == ds.id)
            .order_by(DatasetVersion.version_no.desc())  # type: ignore[arg-type]
        ).all()
        latest = versions[0] if versions else None
        result.append({
            "id": ds.id,
            "workflow_id": ds.workflow_id,
            "title": ds.title,
            "entity_type": ds.entity_type,
            "created_at": ds.created_at.isoformat(),
            "updated_at": ds.updated_at.isoformat(),
            "version_count": len(versions),
            "latest_version": {
                "version_no": latest.version_no,
                "record_count": latest.record_count,
                "created_at": latest.created_at.isoformat(),
            } if latest else None,
        })
    return result


@router.get("/{dataset_id}/versions")
def get_dataset_versions(
    dataset_id: str,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    ds = session.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    versions = session.exec(
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version_no)  # type: ignore[arg-type]
    ).all()

    return [
        {
            "id": v.id,
            "dataset_id": v.dataset_id,
            "version_no": v.version_no,
            "run_id": v.run_id,
            "created_at": v.created_at.isoformat(),
            "record_count": v.record_count,
            "quality_summary": json.loads(v.quality_summary) if v.quality_summary else {},
            "schema_hash": v.schema_hash,
        }
        for v in versions
    ]


@router.get("/{dataset_id}/diff")
def get_dataset_diff(
    dataset_id: str,
    from_ver: int = Query(..., alias="from_ver"),
    to_ver: int = Query(..., alias="to_ver"),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Compute added/removed/changed records between two dataset versions."""
    ds = session.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    versions = {
        v.version_no: v
        for v in session.exec(
            select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
        ).all()
    }

    if from_ver not in versions:
        raise HTTPException(status_code=404, detail=f"Version {from_ver} not found")
    if to_ver not in versions:
        raise HTTPException(status_code=404, detail=f"Version {to_ver} not found")

    from_run_id = versions[from_ver].run_id
    to_run_id = versions[to_ver].run_id

    from_records = session.exec(
        select(ExtractedRecord).where(ExtractedRecord.run_id == from_run_id)
    ).all()
    to_records = session.exec(
        select(ExtractedRecord).where(ExtractedRecord.run_id == to_run_id)
    ).all()

    # Index by dedupe_key
    from_map = {r.dedupe_key: json.loads(r.data) for r in from_records if r.dedupe_key}
    to_map = {r.dedupe_key: json.loads(r.data) for r in to_records if r.dedupe_key}

    added = [{"key": k, "data": v} for k, v in to_map.items() if k not in from_map]
    removed = [{"key": k, "data": v} for k, v in from_map.items() if k not in to_map]

    changed = []
    for key in set(from_map.keys()) & set(to_map.keys()):
        old_data = from_map[key]
        new_data = to_map[key]
        for field in set(list(old_data.keys()) + list(new_data.keys())):
            old_val = old_data.get(field)
            new_val = new_data.get(field)
            if old_val != new_val:
                changed.append({
                    "key": key,
                    "field": field,
                    "old": old_val,
                    "new": new_val,
                })

    schema_changed = versions[from_ver].schema_hash != versions[to_ver].schema_hash

    return {
        "from_version": from_ver,
        "to_version": to_ver,
        "added": added,
        "removed": removed,
        "changed": changed,
        "schema_changed": schema_changed,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "changed_count": len(changed),
        },
    }
