"""
Tests for Workflow Compiler and SpecValidator.
"""
import pytest
from app.services.compiler.service import CompilerService
from app.services.compiler.validator import SpecValidator
from app.services.llm.mock import MockLLMClient


@pytest.mark.asyncio
async def test_compile_startup_prompt():
    client = MockLLMClient()
    service = CompilerService(client)
    spec = await service.compile("Collect seed-stage AI startups in India")

    assert spec.entity_type == "startup"
    assert len(spec.fields) >= 4
    assert any(f.unique_key for f in spec.fields)
    assert len(spec.dag) >= 5
    assert len(spec.source_strategy.connectors) >= 1


@pytest.mark.asyncio
async def test_compile_jobs_prompt():
    client = MockLLMClient()
    service = CompilerService(client)
    spec = await service.compile("Find remote Python internship opportunities")

    assert spec.entity_type == "job_opening"
    assert any(f.name == "title" for f in spec.fields)
    assert any(f.unique_key for f in spec.fields)


def test_validator_detects_cycles():
    client = MockLLMClient()
    service = CompilerService(client)
    validator = SpecValidator()

    from app.schemas.workflow import WorkflowSpec, DagNode, FieldSpec, SourceStrategy

    # Spec with cycle n1 -> n2 -> n1
    spec = WorkflowSpec(
        title="Cycle Test",
        intent_summary="Test cycle",
        entity_type="test",
        fields=[
            FieldSpec(name="id", label="ID", type="string", description="ID", unique_key=True),
            FieldSpec(name="title", label="Title", type="string", description="Title"),
        ],
        source_strategy=SourceStrategy(connectors=["web_search"], seed_queries=["q"], rationale="test"),
        dag=[
            DagNode(id="n1", type="discover_sources", depends_on=["n2"], label="N1"),
            DagNode(id="n2", type="fetch", depends_on=["n1"], label="N2"),
        ],
    )
    errors = validator.validate(spec)
    assert any("cycle" in e.lower() for e in errors)
