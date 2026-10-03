"""
Records router — per-field provenance and user feedback.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models.field_provenance import FieldProvenance
from app.models.record import ExtractedRecord
from app.models.schedule import RecordFeedback

router = APIRouter(prefix="/records", tags=["records"])


class FeedbackRequest(BaseModel):
    feedback_type: str  # "wrong" | "correct" | "duplicate"
    note: str | None = None


@router.get("/{record_id}/provenance")
def get_record_provenance(
    record_id: str,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Return per-field provenance for a record."""
    record = session.get(ExtractedRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    provenances = session.exec(
        select(FieldProvenance).where(FieldProvenance.record_id == record_id)
    ).all()

    if provenances:
        return [
            {
                "id": p.id,
                "record_id": p.record_id,
                "field_name": p.field_name,
                "value": p.value,
                "evidence_text": p.evidence_text,
                "evidence_start": p.evidence_start,
                "evidence_end": p.evidence_end,
                "source_url": p.source_url,
                "confidence": p.confidence,
                "verified": p.verified,
            }
            for p in provenances
        ]

    # Generate provenance on-the-fly from the source_snippet for demo runs
    data = json.loads(record.data)
    return [
        {
            "id": f"{record_id}_{field_name}",
            "record_id": record_id,
            "field_name": field_name,
            "value": str(value) if value is not None else None,
            "evidence_text": record.source_snippet,
            "evidence_start": -1,
            "evidence_end": -1,
            "source_url": record.source_url,
            "confidence": record.confidence,
            "verified": record.verification_status in ("verified", "partial"),
        }
        for field_name, value in data.items()
    ]


@router.post("/{record_id}/feedback")
def submit_feedback(
    record_id: str,
    req: FeedbackRequest,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Submit user feedback (flag as wrong, correct, or duplicate)."""
    record = session.get(ExtractedRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if req.feedback_type not in ("wrong", "correct", "duplicate"):
        raise HTTPException(
            status_code=422,
            detail="feedback_type must be 'wrong', 'correct', or 'duplicate'",
        )

    feedback = RecordFeedback(
        record_id=record_id,
        feedback_type=req.feedback_type,
        note=req.note,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)

    return {
        "id": feedback.id,
        "record_id": feedback.record_id,
        "feedback_type": feedback.feedback_type,
        "note": feedback.note,
        "created_at": feedback.created_at.isoformat(),
    }
