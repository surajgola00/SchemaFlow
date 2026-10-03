"""
SpecValidator — validates and clamps a WorkflowSpec produced by the planner.
"""
from __future__ import annotations

from collections import defaultdict, deque

from app.config import get_settings
from app.schemas.workflow import WorkflowSpec


class SpecValidator:
    def validate(self, spec: WorkflowSpec) -> list[str]:
        """
        Validate WorkflowSpec. Returns list of error strings (empty = valid).
        Checks: unique field names, at least one unique_key, DAG structure,
        acyclicity, connector validity, field count.
        """
        errors: list[str] = []
        settings = get_settings()

        # Field count
        if len(spec.fields) < 2:
            errors.append(f"Must have at least 2 fields, got {len(spec.fields)}")
        if len(spec.fields) > 12:
            errors.append(f"Must have at most 12 fields, got {len(spec.fields)}")

        # Unique field names
        field_names = [f.name for f in spec.fields]
        seen: set[str] = set()
        for name in field_names:
            if name in seen:
                errors.append(f"Duplicate field name: {name}")
            seen.add(name)

        # At least one unique_key
        if not any(f.unique_key for f in spec.fields):
            errors.append("At least one field must be marked unique_key=true")

        # At least one connector
        if not spec.source_strategy.connectors:
            errors.append("At least one connector must be specified")

        # DAG: unique node IDs
        node_ids = [n.id for n in spec.dag]
        seen_ids: set[str] = set()
        for nid in node_ids:
            if nid in seen_ids:
                errors.append(f"Duplicate DAG node id: {nid}")
            seen_ids.add(nid)

        # DAG: all depends_on reference existing node IDs
        for node in spec.dag:
            for dep in node.depends_on:
                if dep not in seen_ids:
                    errors.append(
                        f"Node '{node.id}' depends_on '{dep}' which does not exist"
                    )

        # DAG: acyclicity check (Kahn's algorithm)
        dag_errors = [e for e in errors if "Node" in e or "DAG" in e or "duplicate DAG" in e]
        if not dag_errors:
            in_degree: dict[str, int] = defaultdict(int)
            adj: dict[str, list[str]] = defaultdict(list)
            for node in spec.dag:
                for dep in node.depends_on:
                    adj[dep].append(node.id)
                    in_degree[node.id] += 1
                if node.id not in in_degree:
                    in_degree[node.id] = in_degree[node.id]  # ensure key exists

            queue: deque[str] = deque(
                nid for nid in node_ids if in_degree.get(nid, 0) == 0
            )
            visited_count = 0
            while queue:
                nid = queue.popleft()
                visited_count += 1
                for neighbor in adj[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if visited_count != len(node_ids):
                errors.append("DAG contains a cycle — execution order cannot be determined")

        return errors

    def clamp_limits(self, spec: WorkflowSpec) -> WorkflowSpec:
        """Return spec with limits clamped to server maximums."""
        settings = get_settings()
        clamped = dict(spec.limits)
        clamped["max_pages"] = min(
            int(clamped.get("max_pages", 30)), settings.max_pages_per_run
        )
        clamped["max_records"] = min(
            int(clamped.get("max_records", 100)), settings.max_records_per_run
        )
        clamped["per_domain_rps"] = min(
            float(clamped.get("per_domain_rps", 1.0)), settings.per_domain_rps
        )
        return spec.model_copy(update={"limits": clamped})
