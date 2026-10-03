"""
Exports router — CSV, JSON, XLSX (with provenance + quality sheets), HTML report.
"""
from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models.field_provenance import FieldProvenance
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun
from app.models.workflow import Workflow

router = APIRouter(prefix="/runs", tags=["exports"])


def _get_records_data(run_id: str, session: Session) -> list[dict[str, Any]]:
    from app.models.schedule import RecordFeedback
    wrong_records = set(
        session.exec(
            select(RecordFeedback.record_id).where(RecordFeedback.feedback_type == "wrong")
        ).all()
    )
    records = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
    data = []
    for r in records:
        if r.id in wrong_records:
            continue
        parsed = json.loads(r.data)
        item: dict[str, Any] = {
            "_id": r.id,
            "_source_url": r.source_url,
            "_confidence": round(r.confidence, 3),
            "_verification_status": r.verification_status,
            "_corroboration_count": r.corroboration_count,
        }
        item.update(parsed)
        data.append(item)
    return data


@router.get("/{run_id}/export")
def export_run(
    run_id: str,
    format: str = Query("csv", pattern="^(csv|json|xlsx|report)$"),
    session: Session = Depends(get_session),
) -> Any:
    run = session.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    data = _get_records_data(run_id, session)

    if format == "csv":
        import pandas as pd
        df = pd.DataFrame(data)
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id[:8]}.csv"},
        )

    elif format == "json":
        # Include provenance in JSON export
        records_with_prov = []
        for item in data:
            record_id = item["_id"]
            provs = session.exec(
                select(FieldProvenance).where(FieldProvenance.record_id == record_id)
            ).all()
            item["_provenance"] = [
                {
                    "field": p.field_name,
                    "value": p.value,
                    "evidence": p.evidence_text,
                    "source_url": p.source_url,
                    "confidence": p.confidence,
                    "verified": p.verified,
                }
                for p in provs
            ]
            records_with_prov.append(item)

        content = json.dumps(records_with_prov, indent=2, ensure_ascii=False)
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id[:8]}.json"},
        )

    elif format == "xlsx":
        try:
            import pandas as pd
        except ImportError:
            raise HTTPException(status_code=500, detail="pandas not installed")

        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="openpyxl") as writer:  # type: ignore[call-arg]
            # Sheet 1: Data
            df_data = pd.DataFrame(data)
            df_data.to_excel(writer, sheet_name="Data", index=False)

            # Sheet 2: Provenance
            prov_rows = []
            for item in data:
                record_id = item["_id"]
                provs = session.exec(
                    select(FieldProvenance).where(FieldProvenance.record_id == record_id)
                ).all()
                for p in provs:
                    prov_rows.append({
                        "record_id": record_id,
                        "field_name": p.field_name,
                        "value": p.value,
                        "evidence_text": p.evidence_text[:200],
                        "source_url": p.source_url,
                        "confidence": round(p.confidence, 3),
                        "verified": p.verified,
                    })

            if prov_rows:
                pd.DataFrame(prov_rows).to_excel(writer, sheet_name="Provenance", index=False)

            # Sheet 3: Quality
            records_raw = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
            total = len(records_raw)
            verified = sum(1 for r in records_raw if r.verification_status == "verified")
            quality_data = [
                {"metric": "Total Records", "value": total},
                {"metric": "Verified Records", "value": verified},
                {"metric": "Verification Rate", "value": f"{verified/total*100:.1f}%" if total > 0 else "N/A"},
                {"metric": "Average Confidence", "value": f"{sum(r.confidence for r in records_raw)/total:.3f}" if total > 0 else "N/A"},
                {"metric": "Run ID", "value": run_id},
                {"metric": "Engine Mode", "value": run.engine_mode},
                {"metric": "LLM Mode", "value": run.llm_mode},
            ]
            pd.DataFrame(quality_data).to_excel(writer, sheet_name="Quality", index=False)

        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=run_{run_id[:8]}.xlsx"},
        )

    elif format == "report":
        # HTML report
        wf = session.get(Workflow, run.workflow_id)
        records_raw = session.exec(select(ExtractedRecord).where(ExtractedRecord.run_id == run_id)).all()
        total = len(records_raw)
        verified = sum(1 for r in records_raw if r.verification_status == "verified")

        rows_html = ""
        for item in data[:100]:  # cap at 100 rows for report
            cells = "".join(f"<td>{v}</td>" for v in list(item.values())[:8])
            rows_html += f"<tr>{cells}</tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SchemaFlow Run Report — {run_id[:8]}</title>
<style>
body {{font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 2rem; background: #f9fafb;}}
h1 {{color: #4f46e5;}} h2 {{color: #374151;}}
table {{width: 100%; border-collapse: collapse; margin: 1rem 0;}}
th {{background: #4f46e5; color: white; padding: 0.5rem; text-align: left;}}
td {{padding: 0.5rem; border-bottom: 1px solid #e5e7eb;}}
tr:hover {{background: #f3f4f6;}}
.badge {{padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8em; font-weight: bold;}}
.verified {{background: #d1fae5; color: #065f46;}}
.partial {{background: #fef3c7; color: #92400e;}}
.metric {{background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); display: inline-block; margin: 0.5rem;}}
</style>
</head>
<body>
<h1>⚡ SchemaFlow — Run Report</h1>
<p><strong>Run ID:</strong> {run_id}</p>
<p><strong>Prompt:</strong> {wf.prompt if wf else "N/A"}</p>
<p><strong>Generated:</strong> {run.created_at.isoformat() if run.created_at else "N/A"}</p>

<h2>Summary</h2>
<div>
<div class="metric"><strong>{total}</strong><br>Total Records</div>
<div class="metric"><strong>{verified}</strong><br>Verified Records</div>
<div class="metric"><strong>{verified/total*100:.0f}%</strong><br>Verification Rate</div>
<div class="metric"><strong>{run.engine_mode}</strong><br>Engine Mode</div>
</div>

<h2>Records (first 100)</h2>
<table>
<thead><tr>{"".join(f"<th>{k}</th>" for k in (list(data[0].keys())[:8] if data else []))}</tr></thead>
<tbody>{rows_html}</tbody>
</table>

<hr>
<p style="color: #9ca3af; font-size: 0.8em;">
Generated by SchemaFlow v2.0 — Evidence-verified extraction.
Every non-null field was checked against its source quote; unsupported values were discarded.
</p>
</body>
</html>"""

        return HTMLResponse(content=html, headers={"Content-Disposition": f"attachment; filename=run_{run_id[:8]}_report.html"})
