"""
Tests for DagEngine:
1. Topological execution order
2. Parallel branch execution
3. Failure isolation (independent parallel nodes succeed, downstream dependent nodes skipped)
4. Cancellation halting execution
5. Pause/resume halting work between units
6. Budget limits halting execution
"""
import asyncio
import time
from typing import Any
import pytest
from sqlmodel import Session

from app.database import engine, create_db_and_tables
from app.models.node_run import NodeRun
from app.models.run import ExecutionRun, RunStatus
from app.models.workflow import Workflow
from app.schemas.workflow import DagNode, WorkflowSpec
from app.services.executor.context import RunContext
from app.services.executor.engine import DagEngine
from app.services.executor.nodes.base import BaseNode, NodeResult
from app.services.executor.nodes import NODE_REGISTRY
from app.services.llm.mock import MockLLMClient


@pytest.fixture(autouse=True)
def setup_db():
    create_db_and_tables()


class RecordingNode(BaseNode):
    """Test node that records its execution time and order."""
    def __init__(self, node_type: str, execution_log: list[str], sleep_secs: float = 0.0, should_fail: bool = False):
        self.node_type = node_type
        self.execution_log = execution_log
        self.sleep_secs = sleep_secs
        self.should_fail = should_fail

    async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
        self.execution_log.append(f"{node.id}_start")
        if self.sleep_secs > 0:
            await asyncio.sleep(self.sleep_secs)
        if self.should_fail:
            self.execution_log.append(f"{node.id}_failed")
            return NodeResult(status="failed", error="Deliberate node failure")
        self.execution_log.append(f"{node.id}_end")
        return NodeResult(status="succeeded", data={f"{node.id}_out": 1})


def create_test_context(spec: WorkflowSpec, prefix: str = "test") -> tuple[RunContext, list[dict]]:
    from uuid import uuid4
    uid = uuid4().hex[:8]
    run_id = f"{prefix}_{uid}"
    wf_id = f"wf_{uid}"
    events: list[dict] = []
    cancel_event = asyncio.Event()
    pause_event = asyncio.Event()

    with Session(engine) as session:
        wf = Workflow(id=wf_id, prompt="Test", title="Test Spec", entity_type="test", target_schema_json="[]", execution_dag_json="[]")
        run = ExecutionRun(id=run_id, workflow_id=wf_id, status=RunStatus.running)
        session.add(wf)
        session.add(run)
        session.commit()

    ctx = RunContext(
        run_id=run_id,
        workflow_id=wf_id,
        spec=spec,
        llm=MockLLMClient(),
        emit=lambda e: events.append(e),
        cancel_event=cancel_event,
        pause_event=pause_event,
        replay_speed="fast",
        budget={"max_pages": 10, "max_records": 10, "max_runtime_seconds": 30},
    )
    return ctx, events


@pytest.mark.asyncio
async def test_topological_order():
    """Verify nodes execute strictly in topological order (parents before children)."""
    execution_log: list[str] = []
    saved = {k: NODE_REGISTRY.get(k) for k in ("discover_sources", "fetch", "extract")}
    NODE_REGISTRY["discover_sources"] = RecordingNode("discover_sources", execution_log)
    NODE_REGISTRY["fetch"] = RecordingNode("fetch", execution_log)
    NODE_REGISTRY["extract"] = RecordingNode("extract", execution_log)

    try:
        spec = WorkflowSpec(
            title="Topological Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "n1", "type": "discover_sources", "depends_on": [], "label": "Node 1"},
                {"id": "n2", "type": "fetch", "depends_on": ["n1"], "label": "Node 2"},
                {"id": "n3", "type": "extract", "depends_on": ["n2"], "label": "Node 3"},
            ],
            limits={"max_pages": 10, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_topo")
        engine_instance = DagEngine()
        await engine_instance.run(ctx)

        # Assert n1 completed before n2 started, and n2 before n3
        assert execution_log == ["n1_start", "n1_end", "n2_start", "n2_end", "n3_start", "n3_end"]
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v


@pytest.mark.asyncio
async def test_parallel_nodes():
    """Verify independent parallel nodes run concurrently."""
    execution_log: list[str] = []
    saved = {k: NODE_REGISTRY.get(k) for k in ("fetch", "normalize")}
    # Both sleep 0.08s
    NODE_REGISTRY["fetch"] = RecordingNode("fetch", execution_log, sleep_secs=0.08)
    NODE_REGISTRY["normalize"] = RecordingNode("normalize", execution_log, sleep_secs=0.08)

    try:
        spec = WorkflowSpec(
            title="Parallel Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "p1", "type": "fetch", "depends_on": [], "label": "Parallel 1"},
                {"id": "p2", "type": "normalize", "depends_on": [], "label": "Parallel 2"},
            ],
            limits={"max_pages": 10, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_parallel")
        engine_instance = DagEngine()

        t0 = time.monotonic()
        await engine_instance.run(ctx)
        duration = time.monotonic() - t0

        # Both started before either ended (interleaved start proves concurrent execution)
        first_two_events = {execution_log[0], execution_log[1]}
        assert first_two_events == {"p1_start", "p2_start"}
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v


@pytest.mark.asyncio
async def test_failure_isolation():
    """Verify one branch failing does NOT break an independent parallel branch, but skips dependents."""
    execution_log: list[str] = []
    saved = {k: NODE_REGISTRY.get(k) for k in ("fetch", "normalize", "validate")}
    NODE_REGISTRY["fetch"] = RecordingNode("fetch", execution_log, should_fail=True)
    NODE_REGISTRY["normalize"] = RecordingNode("normalize", execution_log, should_fail=False)
    NODE_REGISTRY["validate"] = RecordingNode("validate", execution_log, should_fail=False)

    try:
        spec = WorkflowSpec(
            title="Failure Isolation Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "n_fail", "type": "fetch", "depends_on": [], "label": "Failing Node"},
                {"id": "n_succ", "type": "normalize", "depends_on": [], "label": "Independent Success Node"},
                {"id": "n_dep", "type": "validate", "depends_on": ["n_fail"], "label": "Dependent on Fail"},
            ],
            limits={"max_pages": 10, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_fail_iso")
        engine_instance = DagEngine()
        await engine_instance.run(ctx)

        # Independent node succeeded
        assert "n_succ_start" in execution_log
        assert "n_succ_end" in execution_log

        # Failing node was recorded
        assert "n_fail_start" in execution_log
        assert "n_fail_failed" in execution_log

        # Dependent node was SKIPPED (never started)
        assert "n_dep_start" not in execution_log

        with Session(engine) as session:
            from sqlmodel import select
            runs = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id)).all()
            status_by_id = {r.node_id: r.status for r in runs}
            assert status_by_id["n_succ"] == "succeeded"
            assert status_by_id["n_fail"] == "failed"
            assert status_by_id["n_dep"] == "skipped"
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v


@pytest.mark.asyncio
async def test_cancellation():
    """Verify setting cancel_event halts remaining work and marks remaining nodes cancelled."""
    execution_log: list[str] = []

    class SlowCancelNode(BaseNode):
        node_type = "fetch"
        async def run(self, ctx: RunContext, node: DagNode, inputs: dict[str, Any]) -> NodeResult:
            execution_log.append(f"{node.id}_run")
            # Set cancel event during first node
            ctx.cancel_event.set()
            return NodeResult(status="succeeded")

    saved = {k: NODE_REGISTRY.get(k) for k in ("fetch", "extract")}
    NODE_REGISTRY["fetch"] = SlowCancelNode()
    NODE_REGISTRY["extract"] = SlowCancelNode()

    try:
        spec = WorkflowSpec(
            title="Cancel Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "c1", "type": "fetch", "depends_on": [], "label": "C1"},
                {"id": "c2", "type": "extract", "depends_on": ["c1"], "label": "C2"},
            ],
            limits={"max_pages": 10, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_cancel")
        engine_instance = DagEngine()
        await engine_instance.run(ctx)

        # Only c1 ran, c2 was cancelled
        assert execution_log == ["c1_run"]

        with Session(engine) as session:
            from sqlmodel import select
            c2_run = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == "c2")).first()
            assert c2_run is not None
            assert c2_run.status == "cancelled"
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v


@pytest.mark.asyncio
async def test_pause_resume_halting():
    """Verify pause_event actually halts execution until resume clears it."""
    execution_log: list[str] = []
    saved = {k: NODE_REGISTRY.get(k) for k in ("fetch", "extract")}
    NODE_REGISTRY["fetch"] = RecordingNode("fetch", execution_log)
    NODE_REGISTRY["extract"] = RecordingNode("extract", execution_log)

    try:
        spec = WorkflowSpec(
            title="Pause Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "step1", "type": "fetch", "depends_on": [], "label": "Step 1"},
                {"id": "step2", "type": "extract", "depends_on": ["step1"], "label": "Step 2"},
            ],
            limits={"max_pages": 10, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_pause")

        # Pause before running
        ctx.pause_event.set()

        engine_task = asyncio.create_task(DagEngine().run(ctx))
        # Wait a short while — execution must be halted at step1 checkpoint
        await asyncio.sleep(0.1)
        assert len(execution_log) == 0  # nothing executed while paused!

        # Now resume
        ctx.pause_event.clear()
        await engine_task

        assert execution_log == ["step1_start", "step1_end", "step2_start", "step2_end"]
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v


@pytest.mark.asyncio
async def test_budget_stop():
    """Verify budget limits (max_pages / max_records) stop execution via checkpoint."""
    execution_log: list[str] = []
    saved = {k: NODE_REGISTRY.get(k) for k in ("fetch", "extract")}
    NODE_REGISTRY["fetch"] = RecordingNode("fetch", execution_log)
    NODE_REGISTRY["extract"] = RecordingNode("extract", execution_log)

    try:
        spec = WorkflowSpec(
            title="Budget Test",
            intent_summary="test",
            entity_type="test",
            fields=[{"name": "id", "label": "ID", "type": "string", "description": "Unique ID", "required": True, "unique_key": True}],
            source_strategy={"connectors": ["web_search"], "seed_queries": ["test"], "rationale": "test"},
            dag=[
                {"id": "b1", "type": "fetch", "depends_on": [], "label": "B1"},
                {"id": "b2", "type": "extract", "depends_on": ["b1"], "label": "B2"},
            ],
            limits={"max_pages": 1, "max_records": 10},
        )
        ctx, _ = create_test_context(spec, "run_budget")
        ctx.budget["max_pages"] = 1
        # Trigger page limit exceeded
        ctx.counters["pages"] = 1

        await DagEngine().run(ctx)

        # Checkpoint failed immediately due to budget exceeded -> 0 nodes executed
        assert len(execution_log) == 0

        with Session(engine) as session:
            from sqlmodel import select
            runs = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id)).all()
            for r in runs:
                assert r.status == "cancelled"
    finally:
        for k, v in saved.items():
            if v:
                NODE_REGISTRY[k] = v
