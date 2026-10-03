"""
Comprehensive API integration test suite covering full workflow lifecycle:
compile -> edit -> run -> records -> quality -> diff -> export,
plus pause / resume / cancel / retry-failed.
"""
import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from app.database import create_db_and_tables
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    create_db_and_tables()


def test_full_pipeline_api_lifecycle():
    with TestClient(app) as client:
        # 1. Compile workflow
        compile_res = client.post(
            "/api/v1/compile",
            json={"prompt": "Collect seed-stage AI startups in India", "use_mock": True},
        )
        assert compile_res.status_code == 200
        compile_data = compile_res.json()
        wf_id = compile_data["workflow_id"]
        spec = compile_data["spec"]
        assert wf_id is not None
        assert spec["entity_type"] == "startup"

        # 2. Edit workflow
        spec["title"] = "Custom Edited AI Startups in India"
        spec["assumptions"].append("Edited for high-growth sectors")
        update_res = client.put(
            f"/api/v1/workflows/{wf_id}",
            json={"spec": spec},
        )
        assert update_res.status_code == 200
        assert update_res.json()["spec"]["title"] == "Custom Edited AI Startups in India"

        # 3. Start execution run in demo mode (fast speed)
        start_res = client.post(
            "/api/v1/runs/start",
            json={
                "workflow_id": wf_id,
                "engine_mode": "demo",
                "use_mock": True,
                "replay_speed": "fast",
            },
        )
        assert start_res.status_code == 200
        run_id = start_res.json()["run_id"]
        assert run_id is not None

        # Wait a short moment for async DAG completion
        import time
        for _ in range(30):
            time.sleep(0.1)
            run_check = client.get(f"/api/v1/runs/{run_id}")
            if run_check.status_code == 200 and run_check.json().get("status") in ("completed", "failed"):
                break

        # 4. Get run records
        records_res = client.get(f"/api/v1/runs/{run_id}/records?page=1&page_size=20")
        assert records_res.status_code == 200
        records_data = records_res.json()
        assert "records" in records_data
        assert records_data["total"] >= 1
        first_rec = records_data["records"][0]
        assert "data" in first_rec
        assert "confidence" in first_rec

        # 5. Get quality report
        quality_res = client.get(f"/api/v1/runs/{run_id}/quality")
        assert quality_res.status_code == 200
        q_data = quality_res.json()
        assert "rows_in" in q_data or "verified_ratio" in q_data

        # 6. Test exports (csv, json, xlsx)
        csv_res = client.get(f"/api/v1/runs/{run_id}/export?format=csv")
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers.get("content-type", "")

        json_res = client.get(f"/api/v1/runs/{run_id}/export?format=json")
        assert json_res.status_code == 200
        assert "application/json" in json_res.headers.get("content-type", "")

        xlsx_res = client.get(f"/api/v1/runs/{run_id}/export?format=xlsx")
        assert xlsx_res.status_code == 200
        assert "spreadsheet" in xlsx_res.headers.get("content-type", "") or "octet-stream" in xlsx_res.headers.get("content-type", "")

        # 7. Test datasets and diff
        datasets_res = client.get("/api/v1/datasets")
        assert datasets_res.status_code == 200
        datasets = datasets_res.json()
        assert isinstance(datasets, list)

        if len(datasets) > 0:
            ds_id = datasets[0]["id"]
            diff_res = client.get(f"/api/v1/datasets/{ds_id}/diff?from_ver=1&to_ver=1")
            assert diff_res.status_code == 200
            diff_data = diff_res.json()
            assert "summary" in diff_data


def test_run_controls_pause_resume_cancel_retry():
    with TestClient(app) as client:
        # Create a workflow
        compile_res = client.post(
            "/api/v1/compile",
            json={"prompt": "Find remote Python internships", "use_mock": True},
        )
        wf_id = compile_res.json()["workflow_id"]

        # Start run
        start_res = client.post(
            "/api/v1/runs/start",
            json={"workflow_id": wf_id, "engine_mode": "demo", "use_mock": True, "replay_speed": "fast"},
        )
        run_id = start_res.json()["run_id"]

        # 1. Pause
        pause_res = client.post(f"/api/v1/runs/{run_id}/pause")
        assert pause_res.status_code == 200
        assert pause_res.json()["state"] == "paused"

        # 2. Resume
        resume_res = client.post(f"/api/v1/runs/{run_id}/resume")
        assert resume_res.status_code == 200
        assert resume_res.json()["state"] == "running"

        # 3. Cancel
        cancel_res = client.post(f"/api/v1/runs/{run_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["state"] == "cancelled"

        # 4. Retry failed
        retry_res = client.post(f"/api/v1/runs/{run_id}/retry-failed")
        assert retry_res.status_code == 200
        assert "retried_nodes" in retry_res.json()
