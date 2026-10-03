"""
Test error handling for invalid/deliberately wrong LLM keys.
Verifies that:
1. Returns HTTP 400 Bad Request with clear actionable message (not 500 / unhandled crash).
2. App does not crash.
3. Demo Mock mode continues to work even if an invalid key is present in env.
"""
import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import app


def test_deliberately_wrong_llm_key_error_handling():
    settings = get_settings()
    original_key = settings.llm_api_key
    settings.llm_api_key = "DELIBERATELY_WRONG_INVALID_KEY_XYZ"

    try:
        with TestClient(app) as client:
            # 1. Live mode compile with wrong key
            res = client.post(
                "/api/v1/compile",
                json={"prompt": "Find AI startups", "use_mock": False},
            )
            assert res.status_code == 400
            detail = res.json().get("detail", "")
            assert "LLM API Authentication Failed" in detail
            assert "Please verify your LLM_API_KEY" in detail

            # 2. App health check right after (must not crash)
            health = client.get("/")
            assert health.status_code == 200

            # 3. Demo Mock mode still functions cleanly
            mock_res = client.post(
                "/api/v1/compile",
                json={"prompt": "Find AI startups", "use_mock": True},
            )
            assert mock_res.status_code == 200
            assert mock_res.json().get("spec") is not None

    finally:
        settings.llm_api_key = original_key
