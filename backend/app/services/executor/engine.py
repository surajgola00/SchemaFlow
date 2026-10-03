"""
DagEngine — Topological execution of workflow DAG with level-based concurrency and NodeRun tracking.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session

from app.database import engine
from app.logging_config import get_logger
from app.models.node_run import NodeRun
from app.models.run import ExecutionRun, RunStatus
from app.services.executor.context import RunContext
from app.services.executor.nodes import NODE_REGISTRY

log = get_logger(__name__)


class DagEngine:
    async def run(self, ctx: RunContext) -> None:
        nodes = ctx.spec.dag
        node_map = {n.id: n for n in nodes}

        # 1. Build adjacency and in-degrees
        in_degree: dict[str, int] = {n.id: 0 for n in nodes}
        adj: dict[str, list[str]] = defaultdict(list)
        for n in nodes:
            for dep in n.depends_on:
                adj[dep].append(n.id)
                in_degree[n.id] += 1

        # 2. Initialize NodeRun records in DB
        with Session(engine) as session:
            for n in nodes:
                nr = NodeRun(
                    run_id=ctx.run_id,
                    node_id=n.id,
                    status="pending",
                )
                session.add(nr)
            session.commit()

        # 3. Execution queue with level grouping
        queue: deque[str] = deque([nid for nid, deg in in_degree.items() if deg == 0])
        node_outputs: dict[str, dict[str, Any]] = {}
        failed_nodes: set[str] = set()
        sem = asyncio.Semaphore(5)

        total_nodes = len(nodes)
        completed_nodes = 0

        while queue:
            if not await ctx.checkpoint():
                ctx.emit_log("WARNING", "Execution halted by budget or cancellation.")
                self._mark_remaining_cancelled(ctx, [n.id for n in nodes if n.id not in node_outputs and n.id not in failed_nodes])
                return

            current_batch = list(queue)
            queue.clear()

            async def execute_node(node_id: str) -> None:
                if not await ctx.checkpoint():
                    with Session(engine) as session:
                        from sqlmodel import select
                        nr = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == node_id)).first()
                        if nr and nr.status == "pending":
                            nr.status = "cancelled"
                            nr.finished_at = datetime.now(timezone.utc)
                            session.add(nr)
                            session.commit()
                    return

                async with sem:
                    node = node_map[node_id]

                    # Failure isolation: skip if any upstream dependency failed
                    if any(dep in failed_nodes for dep in node.depends_on):
                        failed_nodes.add(node_id)
                        with Session(engine) as session:
                            from sqlmodel import select
                            nr = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == node_id)).first()
                            if nr:
                                nr.status = "skipped"
                                nr.error = "Upstream dependency failed"
                                nr.finished_at = datetime.now(timezone.utc)
                                session.add(nr)
                                session.commit()
                        ctx.emit_node_event("node_finished", node_id, {"status": "skipped", "error": "Upstream dependency failed"})
                        return

                    handler = NODE_REGISTRY.get(node.type)
                    if not handler:
                        ctx.emit_log("WARNING", f"No handler registered for node type '{node.type}'", node_id=node_id)
                        return

                    # Gather inputs from parent nodes
                    inputs: dict[str, Any] = {}
                    for dep in node.depends_on:
                        inputs.update(node_outputs.get(dep, {}))

                    # Update DB status -> running
                    with Session(engine) as session:
                        from sqlmodel import select
                        nr = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == node_id)).first()
                        if nr:
                            nr.status = "running"
                            nr.started_at = datetime.now(timezone.utc)
                            session.add(nr)
                            session.commit()

                    ctx.emit_node_event("node_started", node_id, {"label": node.label, "type": node.type})

                    try:
                        res = await handler.run(ctx, node, inputs)
                        if res.status == "failed":
                            failed_nodes.add(node_id)
                        else:
                            node_outputs[node_id] = res.data

                        with Session(engine) as session:
                            from sqlmodel import select
                            nr = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == node_id)).first()
                            if nr:
                                nr.status = res.status
                                nr.finished_at = datetime.now(timezone.utc)
                                nr.items_in = res.items_in
                                nr.items_out = res.items_out
                                nr.error = res.error
                                session.add(nr)
                                session.commit()

                        ctx.emit_node_event("node_finished", node_id, {
                            "status": res.status,
                            "items_in": res.items_in,
                            "items_out": res.items_out,
                            "error": res.error,
                        })

                    except Exception as e:
                        failed_nodes.add(node_id)
                        ctx.emit_log("ERROR", f"Node '{node.label}' failed: {e}", node_id=node_id)
                        with Session(engine) as session:
                            from sqlmodel import select
                            nr = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id == node_id)).first()
                            if nr:
                                nr.status = "failed"
                                nr.finished_at = datetime.now(timezone.utc)
                                nr.error = str(e)
                                session.add(nr)
                                session.commit()

                        ctx.emit_node_event("node_finished", node_id, {"status": "failed", "error": str(e)})

            await asyncio.gather(*[execute_node(nid) for nid in current_batch])

            if getattr(ctx, "replay_speed", "fast") == "cinematic":
                await asyncio.sleep(0.4)
            else:
                await asyncio.sleep(0.01)

            completed_nodes += len(current_batch)
            progress_pct = int((completed_nodes / total_nodes) * 100)
            ctx.emit({"type": "progress", "pct": progress_pct, "run_id": ctx.run_id})

            with Session(engine) as session:
                run = session.get(ExecutionRun, ctx.run_id)
                if run:
                    run.progress_pct = progress_pct
                    session.add(run)
                    session.commit()

            # Advance in-degrees
            for finished_nid in current_batch:
                for child_nid in adj[finished_nid]:
                    in_degree[child_nid] -= 1
                    if in_degree[child_nid] == 0:
                        queue.append(child_nid)

    def _mark_remaining_cancelled(self, ctx: RunContext, remaining_ids: list[str]) -> None:
        with Session(engine) as session:
            from sqlmodel import select
            runs = session.exec(select(NodeRun).where(NodeRun.run_id == ctx.run_id, NodeRun.node_id.in_(remaining_ids))).all()
            for r in runs:
                if r.status in ("pending", "running"):
                    r.status = "cancelled"
                    r.finished_at = datetime.now(timezone.utc)
                    session.add(r)
            session.commit()
