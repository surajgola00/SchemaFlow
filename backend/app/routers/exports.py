from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
import json
import io
import pandas as pd
from app.database import get_session
from app.models.run import ExecutionRun
from app.models.record import ExtractedRecord

router = APIRouter(prefix="/runs", tags=["exports"])

@router.get("/{run_id}/export")
def export_run(run_id: str, format: str = Query("csv", pattern="^(csv|json)$"), session: Session = Depends(get_session)):
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    records = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
    
    data = []
    for r in records:
        parsed_data = json.loads(r.data)
        item = {
            "id": r.id,
            "source_url": r.source_url,
            "source_snippet": r.source_snippet,
            "confidence_score": r.confidence_score,
            "is_duplicate": r.is_duplicate
        }
        item.update(parsed_data)
        data.append(item)
        
    if format == "csv":
        df = pd.DataFrame(data)
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id}.csv"}
        )
    else:
        stream = io.StringIO()
        json.dump(data, stream)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id}.json"}
        )
