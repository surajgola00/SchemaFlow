"""
Tests for Planner and CompilerService:
1. Invalid LLM spec -> validator detects issues -> re-prompt with errors -> valid spec accepted.
2. Cyclic DAG rejected by SpecValidator and CompilerService with 422 error.
"""
from typing import Any
import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from app.schemas.workflow import WorkflowSpec
from app.services.compiler.service import CompilerService
from app.services.compiler.validator import SpecValidator


class SequenceLLMClient:
    """Mock LLM that returns a sequence of predetermined responses for testing retries."""
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.call_count = 0
        self.prompts_received = []

    async def complete_json(self, system: str, user: str, schema: type[BaseModel], max_retries: int = 2) -> BaseModel:
        self.prompts_received.append(user)
        idx = min(self.call_count, len(self.responses) - 1)
        resp = self.responses[idx]
        self.call_count += 1
        return schema.model_validate(resp)


def _valid_spec_dict() -> dict:
    return {
        "title": "Valid Workflow",
        "intent_summary": "Collect valid data",
        "entity_type": "entity",
        "fields": [
            {"name": "id", "label": "ID", "type": "string", "description": "Unique key", "required": True, "unique_key": True},
            {"name": "title", "label": "Title", "type": "string", "description": "Entity title", "required": True, "unique_key": False},
        ],
        "source_strategy": {
            "connectors": ["web_search"],
            "seed_queries": ["query 1"],
            "rationale": "High quality sources",
        },
        "dag": [
            {"id": "n1", "type": "discover_sources", "depends_on": [], "label": "Discover"},
            {"id": "n2", "type": "fetch", "depends_on": ["n1"], "label": "Fetch"},
            {"id": "n3", "type": "extract", "depends_on": ["n2"], "label": "Extract"},
            {"id": "n4", "type": "finalize", "depends_on": ["n3"], "label": "Finalize"},
        ],
        "limits": {"max_pages": 20, "max_records": 50},
    }


@pytest.mark.asyncio
async def test_invalid_spec_reprompt_recovery():
    """Verify that when the LLM returns an invalid spec (e.g. missing unique_key),

    CompilerService re-prompts the LLM with the validation error and succeeds on 2nd try.
    """
    # 1. Invalid spec (no unique_key=True on any field)
    invalid_spec = _valid_spec_dict()
    for f in invalid_spec["fields"]:
        f["unique_key"] = False

    # 2. Valid spec
    valid_spec = _valid_spec_dict()

    mock_llm = SequenceLLMClient([invalid_spec, valid_spec])
    compiler = CompilerService(mock_llm)

    result_spec = await compiler.compile("Find entities")

    # Assert LLM was called twice
    assert mock_llm.call_count == 2

    # Assert the retry prompt contained the validation error
    retry_prompt = mock_llm.prompts_received[1]
    assert "IMPORTANT: The previous response had validation errors:" in retry_prompt
    assert "At least one field must be marked unique_key=true" in retry_prompt

    # Assert resulting spec is valid and has unique_key
    assert any(f.unique_key for f in result_spec.fields)


@pytest.mark.asyncio
async def test_cyclic_dag_rejected_by_validator():
    """Verify SpecValidator Kahn's algorithm detects and rejects cyclic DAG dependencies."""
    validator = SpecValidator()

    cyclic_spec_dict = _valid_spec_dict()
    # Create cycle: n1 -> n2 -> n3 -> n1
    cyclic_spec_dict["dag"] = [
        {"id": "n1", "type": "discover_sources", "depends_on": ["n3"], "label": "Node 1"},
        {"id": "n2", "type": "fetch", "depends_on": ["n1"], "label": "Node 2"},
        {"id": "n3", "type": "extract", "depends_on": ["n2"], "label": "Node 3"},
    ]
    spec = WorkflowSpec.model_validate(cyclic_spec_dict)
    errors = validator.validate(spec)

    assert any("contains a cycle" in e for e in errors)


@pytest.mark.asyncio
async def test_cyclic_dag_rejected_by_compiler_service():
    """Verify CompilerService raises HTTP 422 if retry still produces a cyclic DAG."""
    cyclic_spec_dict = _valid_spec_dict()
    cyclic_spec_dict["dag"] = [
        {"id": "n1", "type": "discover_sources", "depends_on": ["n2"], "label": "Node 1"},
        {"id": "n2", "type": "fetch", "depends_on": ["n1"], "label": "Node 2"},
    ]

    mock_llm = SequenceLLMClient([cyclic_spec_dict, cyclic_spec_dict])
    compiler = CompilerService(mock_llm)

    with pytest.raises(HTTPException) as exc_info:
        await compiler.compile("Cycle test prompt")

    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert "errors" in detail
    assert any("contains a cycle" in e for e in detail["errors"])
