"""
Fixture manager for recording and replaying demo executions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


class FixtureManager:
    def __init__(self) -> None:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    def save_fixture(
        self,
        title: str,
        spec: dict[str, Any],
        source_docs: list[dict[str, Any]],
        records: list[dict[str, Any]],
        fixture_id: str | None = None,
    ) -> str:
        fid = fixture_id or hashlib.md5(title.encode("utf-8")).hexdigest()[:8]
        fixture_payload = {
            "fixture_id": fid,
            "title": title,
            "entity_type": spec.get("entity_type", ""),
            "spec": spec,
            "source_docs": source_docs,
            "records": records,
        }
        target_path = FIXTURES_DIR / f"{fid}.json"
        target_path.write_text(json.dumps(fixture_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return fid

    def load_fixture(self, fixture_id: str) -> dict[str, Any] | None:
        target_path = FIXTURES_DIR / f"{fixture_id}.json"
        if not target_path.exists():
            # Try searching by matching prefix or title
            for p in FIXTURES_DIR.glob("*.json"):
                if p.stem == fixture_id or fixture_id in p.stem:
                    return json.loads(p.read_text(encoding="utf-8"))
            return None
        return json.loads(target_path.read_text(encoding="utf-8"))

    def list_fixtures(self) -> list[dict[str, Any]]:
        results = []
        for p in FIXTURES_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                results.append({
                    "fixture_id": data.get("fixture_id", p.stem),
                    "title": data.get("title", p.stem),
                    "entity_type": data.get("entity_type", ""),
                    "record_count": len(data.get("records", [])),
                })
            except Exception:
                pass
        return results


fixture_manager = FixtureManager()
