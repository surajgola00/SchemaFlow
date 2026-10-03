"""
Mock/Demo executor — plays back preset datasets through the real event system and DB.
Used when engine_mode=="demo" or no LLM key is configured.
Keeps all existing behavior from executor.py v1 but uses new models + events.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from sqlmodel import Session

from app.database import engine
from app.models.record import ExtractedRecord
from app.models.run import ExecutionRun, RunStatus
from app.services.executor.events import add_log, emit_event

# ── Preset datasets (from v1 executor, preserved exactly) ─────────────────────

STARTUP_RECORDS = [
    {"name": "Sarvam AI", "founders": "Vivek Raghavan, Pratyush Kumar", "funding_amount": "$41M Series A", "location": "Bengaluru, India", "career_page_url": "https://sarvam.ai/careers", "description": "Building multilingual LLMs for Indian languages"},
    {"name": "Krutrim", "founders": "Bhavish Aggarwal", "funding_amount": "$50M Seed", "location": "Bengaluru, India", "career_page_url": "https://krutrim.com/careers", "description": "India-first AI company building foundation models"},
    {"name": "Gnani.ai", "founders": "Ganesh Gopalan, Ananth Nagaraj", "funding_amount": "$13.2M Series A", "location": "Bengaluru, India", "career_page_url": "https://gnani.ai/careers", "description": "Conversational AI platform for enterprises"},
    {"name": "Lexi AI", "founders": "Siddharth Srivastava", "funding_amount": "$4M Pre-Seed", "location": "Mumbai, India", "career_page_url": "https://lexiai.in/jobs", "description": "AI-powered legal document analysis"},
    {"name": "Mihup", "founders": "Sandipan Chattopadhyay, Biplab Chakraborty", "funding_amount": "$8M Series A", "location": "Kolkata, India", "career_page_url": "https://mihup.com/careers", "description": "Voice AI platform for contact centres"},
    {"name": "Yellow.ai", "founders": "Raghu Ravinutala, Jaya Kishore Reddy", "funding_amount": "$102M Series C", "location": "San Francisco / Bengaluru", "career_page_url": "https://yellow.ai/careers", "description": "Enterprise-grade conversational AI platform"},
    {"name": "Haptik", "founders": "Aakrit Vaish, Swapan Rajdev", "funding_amount": "Acquired by Reliance", "location": "Mumbai, India", "career_page_url": "https://haptik.ai/careers", "description": "Conversational AI for customer support"},
    {"name": "Mad Street Den", "founders": "Ashwini Asokan, Anand Chandrasekaran", "funding_amount": "$30M Series B", "location": "Chennai, India", "career_page_url": "https://madstreetden.com/careers", "description": "AI-powered computer vision for retail"},
    {"name": "Niramai", "founders": "Geetha Manjunath, Nidhi Mathur", "funding_amount": "$6M Series A", "location": "Bengaluru, India", "career_page_url": "https://niramai.com/careers", "description": "AI-based breast cancer screening"},
    {"name": "SigTuple", "founders": "Rohit Kumar Pandey, Apurv Anand", "funding_amount": "$19.5M Series B", "location": "Bengaluru, India", "career_page_url": "https://sigtuple.com/careers", "description": "AI for automated medical diagnostics"},
    {"name": "Scalenut", "founders": "Mayank Jain, Saurabh Wadhawan, Rakesh Rajput", "funding_amount": "$3.1M Seed", "location": "Gurugram, India", "career_page_url": "https://scalenut.com/careers", "description": "AI-powered SEO and content intelligence"},
    {"name": "Rephrase.ai", "founders": "Ashray Malhotra, Nisheeth Ranjan, Shivam Mangla", "funding_amount": "$10.7M Series A", "location": "Bengaluru, India", "career_page_url": "https://rephrase.ai/careers", "description": "AI video generation from text"},
]

HACKATHON_RECORDS = [
    {"event_name": "HackAI 2026", "date": "March 15-17, 2026", "location": "San Francisco, CA", "prize_pool": "$50,000", "registration_url": "https://hackai2026.dev/register", "organizer": "MLH"},
    {"event_name": "Google AI Hackathon 2026", "date": "April 5-6, 2026", "location": "Online (Global)", "prize_pool": "$100,000", "registration_url": "https://events.google.com/ai-hackathon-2026", "organizer": "Google DeepMind"},
    {"event_name": "Meta LlamaCon Hack", "date": "May 1-2, 2026", "location": "Menlo Park, CA", "prize_pool": "$75,000", "registration_url": "https://llamahack.meta.com/register", "organizer": "Meta AI"},
    {"event_name": "Devfolio BuildSpace 2026", "date": "February 28 - March 2, 2026", "location": "Bengaluru, India", "prize_pool": "₹20,00,000", "registration_url": "https://buildspace.devfolio.co", "organizer": "Devfolio"},
    {"event_name": "HackMIT 2026", "date": "September 12-13, 2026", "location": "Cambridge, MA", "prize_pool": "$30,000", "registration_url": "https://hackmit.org/apply", "organizer": "MIT"},
    {"event_name": "SIH 2026 (Smart India Hackathon)", "date": "December 1-2, 2026", "location": "Pan-India (Multiple Venues)", "prize_pool": "₹1,00,000 per team", "registration_url": "https://sih.gov.in/register", "organizer": "Ministry of Education, India"},
]

SAAS_RECORDS = [
    {"company_name": "Notion", "website": "https://notion.so", "pricing_tier": "Free / $8 / $15 per user/month", "features": "Wikis, Docs, Databases, AI Writing", "contact_email": "sales@notion.so", "category": "Productivity"},
    {"company_name": "Linear", "website": "https://linear.app", "pricing_tier": "Free / $8 / $14 per user/month", "features": "Issue Tracking, Cycles, Roadmaps, Git sync", "contact_email": "sales@linear.app", "category": "Project Management"},
    {"company_name": "Vercel", "website": "https://vercel.com", "pricing_tier": "Free / $20 / $40 per user/month", "features": "Frontend deployments, Edge Network, Analytics", "contact_email": "sales@vercel.com", "category": "DevOps / Hosting"},
    {"company_name": "Supabase", "website": "https://supabase.com", "pricing_tier": "Free / $25 / $599 per month", "features": "Postgres DB, Auth, Storage, Edge Functions", "contact_email": "sales@supabase.io", "category": "Backend-as-a-Service"},
    {"company_name": "Retool", "website": "https://retool.com", "pricing_tier": "$10 / $50 per user/month", "features": "Internal tool builder, DB connectors, Workflows", "contact_email": "sales@retool.com", "category": "Low-Code / Internal Tools"},
    {"company_name": "PostHog", "website": "https://posthog.com", "pricing_tier": "Free (usage-based) / $450/month", "features": "Product Analytics, Session Replay, Feature Flags", "contact_email": "sales@posthog.com", "category": "Product Analytics"},
    {"company_name": "Trigger.dev", "website": "https://trigger.dev", "pricing_tier": "Free / $20 / $500 per month", "features": "Background jobs, Workflows, Scheduling, Retries", "contact_email": "hello@trigger.dev", "category": "Developer Tools"},
]

SOURCE_SNIPPETS = {
    "startup": "According to Crunchbase and YourStory, {name} was founded by {founders} and is headquartered in {location}. The company raised {funding_amount} to accelerate product development. Their careers page is available at {career_page_url}.",
    "hackathon": "{event_name} is scheduled for {date} in {location}. Organized by {organizer}, the event offers a total prize pool of {prize_pool}. Register at {registration_url} before slots fill up.",
    "saas": "{company_name} ({website}) is a leading {category} platform. Pricing starts at {pricing_tier}. Key features include {features}. For enterprise enquiries, reach out to {contact_email}.",
    "default": "Extracted data point. Source data available via structured workflow.",
}


def _detect_type(prompt: str) -> tuple[list[dict], str, list[str]]:
    """Detect dataset type from prompt and return (records, snippet_key, domains)."""
    p = prompt.lower()
    if any(w in p for w in ("startup", "company", "india", "founder", "funding")):
        return STARTUP_RECORDS, "startup", ["crunchbase.com", "yourstory.com", "inc42.com", "tracxn.com"]
    elif any(w in p for w in ("hackathon", "event", "conference", "competition")):
        return HACKATHON_RECORDS, "hackathon", ["devpost.com", "mlh.io", "devfolio.co"]
    elif any(w in p for w in ("lead", "saas", "software", "directory")):
        return SAAS_RECORDS, "saas", ["g2.com", "capterra.com", "producthunt.com"]
    else:
        generic = [
            {"title": f"Result {i}", "description": f"Extracted data item {i}", "url": f"https://example.com/item-{i}", "date": "2026-01-01", "category": "General"}
            for i in range(1, 11)
        ]
        return generic, "default", ["example.com", "data.gov"]


def _update_run_db(run_id: str, status: RunStatus, progress_pct: int) -> None:
    with Session(engine) as session:
        run = session.get(ExecutionRun, run_id)
        if run:
            run.status = status
            run.state = status.value
            run.progress_pct = progress_pct
            if status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
                run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()


def _save_records(run_id: str, records: list[dict]) -> None:
    with Session(engine) as session:
        for r in records:
            rec = ExtractedRecord(
                run_id=run_id,
                data=json.dumps(r["data"]),
                data_json=json.dumps(r["data"]),
                source_url=r["source_url"],
                source_snippet=r["source_snippet"],
                confidence_score=r["confidence"],
                confidence=r["confidence"],
                verification_status="verified",
                is_duplicate=False,
                dedupe_key=str(list(r["data"].values())[0]).lower()[:64] if r["data"] else "",
            )
            session.add(rec)
        session.commit()


async def run_demo_execution(run_id: str, prompt: str) -> None:
    """
    Demo execution: replays preset data through the real event system + DB.
    Exercises real SSE, real DB writes, and real event ordering.
    """
    try:
        dataset, snippet_key, domains = _detect_type(prompt)
        template = SOURCE_SNIPPETS.get(snippet_key, SOURCE_SNIPPETS["default"])

        # Step 1 — Query Construction
        add_log(run_id, "INFO", f'Analysing prompt: "{prompt[:60]}..."')
        _update_run_db(run_id, RunStatus.running, 5)
        await asyncio.sleep(0.3)
        add_log(run_id, "INFO", "Generated 4 semantic search queries from schema fields")
        emit_event(run_id, {"type": "node_started", "node_id": "n1", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"label": "Discover Sources"}})
        _update_run_db(run_id, RunStatus.running, 15)

        await asyncio.sleep(0.4)

        # Step 2 — Source Discovery
        add_log(run_id, "INFO", f"Discovering permitted sources: {', '.join(domains)}")
        for domain in domains:
            emit_event(run_id, {
                "type": "compliance", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(),
                "data": {"event": "robots_check", "url": f"https://{domain}/", "allowed": True}
            })
        await asyncio.sleep(0.3)
        add_log(run_id, "SUCCESS", f"robots.txt verified for {len(domains)} domains — all compliant")
        emit_event(run_id, {"type": "node_finished", "node_id": "n1", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"status": "succeeded", "items_out": len(domains) * 5}})
        emit_event(run_id, {"type": "progress", "pct": 25, "step": "Source Discovery", "run_id": run_id})
        _update_run_db(run_id, RunStatus.running, 25)

        # Update compliance in DB
        with Session(engine) as session:
            run_obj = session.get(ExecutionRun, run_id)
            if run_obj:
                run_obj.compliance_status = json.dumps({
                    "robots_txt_checked": True,
                    "rate_limited": False,
                    "permitted_domains": domains,
                })
                session.add(run_obj)
                session.commit()

        # Step 3 — Page Retrieval
        emit_event(run_id, {"type": "node_started", "node_id": "n2", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"label": "Fetch Pages"}})
        add_log(run_id, "INFO", f"Fetching {len(dataset)} pages (rate-limited to 1 req/s)")
        for i, domain in enumerate(domains[:3]):
            await asyncio.sleep(0.15)
            add_log(run_id, "INFO", f"  Fetched: https://{domain}/listings (200 OK, {1200 + i * 340} chars)")
        add_log(run_id, "INFO", "HTML parsed → Markdown normalized for all pages")
        emit_event(run_id, {"type": "node_finished", "node_id": "n2", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"status": "succeeded", "items_out": len(domains) * 3}})
        emit_event(run_id, {"type": "progress", "pct": 50, "step": "Page Retrieval", "run_id": run_id})
        _update_run_db(run_id, RunStatus.running, 50)

        # Step 4 — Entity Extraction
        emit_event(run_id, {"type": "node_started", "node_id": "n3", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"label": "Extract Entities"}})
        add_log(run_id, "INFO", f"Running structured extraction against schema fields")
        await asyncio.sleep(0.3)

        records: list[dict] = []
        confidences = [0.97, 0.94, 0.91, 0.96, 0.89, 0.98, 0.93, 0.95, 0.92, 0.97, 0.90, 0.94]
        for i, item in enumerate(dataset):
            try:
                snippet = template.format(**item)
            except KeyError:
                snippet = f"Extracted from {domains[i % len(domains)]}: {json.dumps(item)}"

            confidence = confidences[i % len(confidences)]
            records.append({
                "data": item,
                "source_url": f"https://{domains[i % len(domains)]}/listing/{i + 1}",
                "source_snippet": snippet,
                "confidence": confidence,
            })
            add_log(run_id, "INFO", f"[{i + 1}/{len(dataset)}] Extracted: {list(item.values())[0]} (conf: {confidence:.0%})")
            if i % 3 == 2:
                await asyncio.sleep(0.1)

        emit_event(run_id, {"type": "record", "count": len(records), "run_id": run_id})
        add_log(run_id, "SUCCESS", f"{len(records)} records extracted with evidence verification")
        emit_event(run_id, {"type": "node_finished", "node_id": "n3", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"status": "succeeded", "items_out": len(records)}})
        emit_event(run_id, {"type": "progress", "pct": 75, "step": "Entity Extraction", "run_id": run_id})
        _update_run_db(run_id, RunStatus.running, 75)

        # Step 5 — Deduplication & Validation
        emit_event(run_id, {"type": "node_started", "node_id": "n6", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"label": "Deduplicate"}})
        add_log(run_id, "INFO", "Running 3-level deduplication (exact → URL → fuzzy)...")
        await asyncio.sleep(0.2)
        add_log(run_id, "SUCCESS", f"0 duplicates found — all {len(records)} records are unique")

        _save_records(run_id, records)

        # Update metrics
        avg_confidence = sum(r["confidence"] for r in records) / len(records) if records else 0.0
        with Session(engine) as session:
            run_obj = session.get(ExecutionRun, run_id)
            if run_obj:
                run_obj.metrics_json = json.dumps({
                    "records_total": len(records),
                    "records_verified": len(records),
                    "verified_ratio": 1.0,
                    "avg_confidence": round(avg_confidence, 3),
                    "pages_fetched": len(domains) * 3,
                    "duplicates_merged": 0,
                })
                session.add(run_obj)
                session.commit()

        emit_event(run_id, {"type": "node_finished", "node_id": "n6", "run_id": run_id, "ts": datetime.now(timezone.utc).isoformat(), "data": {"status": "succeeded", "items_out": len(records)}})
        emit_event(run_id, {"type": "progress", "pct": 100, "step": "Complete", "run_id": run_id})
        emit_event(run_id, {"type": "done", "status": "completed", "run_id": run_id})
        _update_run_db(run_id, RunStatus.completed, 100)
        add_log(run_id, "SUCCESS", f"Pipeline complete — {len(records)} records saved with evidence provenance")

    except Exception as e:
        add_log(run_id, "ERROR", f"Execution failed: {str(e)}")
        _update_run_db(run_id, RunStatus.failed, 0)
        emit_event(run_id, {"type": "done", "status": "failed", "run_id": run_id})


async def start_execution_task(
    run_id: str,
    workflow_id: str,
    prompt: str,
    engine_mode: str = "demo",
    use_mock: bool = True,
) -> None:
    """Start demo execution as a background asyncio task."""
    from app.services.executor.registry import run_registry
    cancel_event = asyncio.Event()
    pause_event = asyncio.Event()

    task = asyncio.create_task(run_demo_execution(run_id, prompt))
    run_registry.register(run_id, task, cancel_event, pause_event)
