"""
Smoke test for Live LLM integration.
Compiles two completely different prompts using the live LLM (when LLM_API_KEY is set),
prints their schema field names, connectors, and DAG node types, and asserts they differ dynamically.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from dotenv import load_dotenv

# Load backend/.env
backend_env = Path(__file__).resolve().parent.parent / "backend" / ".env"
if backend_env.exists():
    load_dotenv(backend_env)

from app.config import get_settings
from app.services.compiler.service import CompilerService
from app.services.llm.factory import get_llm


async def run_smoke_test() -> None:
    settings = get_settings()
    api_key = settings.llm_api_key.strip()
    if not api_key:
        print("[!] LLM_API_KEY is not configured. Please set LLM_API_KEY in backend/.env to run live check.")
        sys.exit(0)

    print(f"[*] Starting Live LLM Smoke Test with model '{settings.llm_model}'...")
    llm = get_llm(force_mock=False)
    compiler = CompilerService(llm)

    prompt_1 = "Find seed-stage AI hardware startups in India with company name, founders, funding amount, headquarters location, and chip architecture description."
    prompt_2 = "Track clinical trial publications for oncology therapies with drug name, phase number, patient sample size, primary sponsor, and completion date."

    print("\n------------------------------------------------------------")
    print(f"Prompt 1: {prompt_1}")
    spec_1 = await compiler.compile(prompt_1)
    fields_1 = [f.name for f in spec_1.fields]
    connectors_1 = spec_1.source_strategy.connectors
    dag_nodes_1 = [n.type for n in spec_1.dag]

    print(f"  Title:        {spec_1.title}")
    print(f"  Entity Type:  {spec_1.entity_type}")
    print(f"  Fields:       {fields_1}")
    print(f"  Connectors:   {connectors_1}")
    print(f"  DAG Nodes:    {dag_nodes_1}")

    print("\n------------------------------------------------------------")
    print(f"Prompt 2: {prompt_2}")
    spec_2 = await compiler.compile(prompt_2)
    fields_2 = [f.name for f in spec_2.fields]
    connectors_2 = spec_2.source_strategy.connectors
    dag_nodes_2 = [n.type for n in spec_2.dag]

    print(f"  Title:        {spec_2.title}")
    print(f"  Entity Type:  {spec_2.entity_type}")
    print(f"  Fields:       {fields_2}")
    print(f"  Connectors:   {connectors_2}")
    print(f"  DAG Nodes:    {dag_nodes_2}")

    print("\n------------------------------------------------------------")
    print("[*] Verifying dynamic compilation differences...")

    # Assertions
    assert spec_1.entity_type != spec_2.entity_type, f"Entity types should differ: {spec_1.entity_type} vs {spec_2.entity_type}"
    assert set(fields_1) != set(fields_2), f"Schema fields should differ: {fields_1} vs {fields_2}"
    print(f"[OK] Entity types differ: '{spec_1.entity_type}' != '{spec_2.entity_type}'")
    print(f"[OK] Field schemas differ completely:")
    print(f"     Prompt 1 unique fields: {set(fields_1) - set(fields_2)}")
    print(f"     Prompt 2 unique fields: {set(fields_2) - set(fields_1)}")
    print("\n>>> LIVE LLM COMPILATION VERIFIED: Dynamic schemas generated successfully! <<<\n")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
