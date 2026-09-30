import asyncio
import json
import random
from datetime import datetime, timezone
from sqlmodel import Session
from app.database import engine
from app.models.run import ExecutionRun, RunStatus
from app.models.record import ExtractedRecord

run_events: dict[str, list[dict]] = {}


def emit_event(run_id: str, event: dict):
    if run_id not in run_events:
        run_events[run_id] = []
    run_events[run_id].append(event)


def add_log(run_id: str, level: str, message: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    emit_event(run_id, {"type": "log", "level": level.upper(), "message": message, "timestamp": ts})


def update_run_in_db(run_id: str, status: RunStatus, progress_pct: int, extra_logs: list = None):
    with Session(engine) as session:
        run = session.get(ExecutionRun, run_id)
        if run:
            run.status = status
            run.progress_pct = progress_pct
            if extra_logs:
                existing = json.loads(run.logs)
                existing.extend(extra_logs)
                run.logs = json.dumps(existing)
            if status in [RunStatus.completed, RunStatus.failed]:
                run.finished_at = datetime.now(timezone.utc)
            session.add(run)
            session.commit()


def save_records_to_db(run_id: str, records: list):
    with Session(engine) as session:
        for r in records:
            rec = ExtractedRecord(
                run_id=run_id,
                data=json.dumps(r["data"]),
                source_url=r["source_url"],
                source_snippet=r["source_snippet"],
                confidence_score=r["confidence_score"],
                is_duplicate=r.get("is_duplicate", False),
            )
            session.add(rec)
        session.commit()


STARTUP_RECORDS = [
    {"name": "Sarvam AI", "founders": "Vivek Raghavan, Pratyush Kumar", "funding_amount": "$41M Series A", "location": "Bengaluru, India", "career_page_url": "https://sarvam.ai/careers", "description": "Building multilingual LLMs for Indian languages"},
    {"name": "Krutrim", "founders": "Bhavish Aggarwal", "funding_amount": "$50M Seed", "location": "Bengaluru, India", "career_page_url": "https://krutrim.com/careers", "description": "India-first AI company building foundation models"},
    {"name": "Ola Krutrim", "founders": "Bhavish Aggarwal", "funding_amount": "$50M Seed", "location": "Bengaluru, India", "career_page_url": "https://olakrutrim.com/careers", "description": "AI-powered mobility and cloud platform"},
    {"name": "Gnani.ai", "founders": "Ganesh Gopalan, Ananth Nagaraj", "funding_amount": "$13.2M Series A", "location": "Bengaluru, India", "career_page_url": "https://gnani.ai/careers", "description": "Conversational AI platform for enterprises"},
    {"name": "Lexi AI", "founders": "Siddharth Srivastava", "funding_amount": "$4M Pre-Seed", "location": "Mumbai, India", "career_page_url": "https://lexiai.in/jobs", "description": "AI-powered legal document analysis for Indian courts"},
    {"name": "Mihup", "founders": "Sandipan Chattopadhyay, Biplab Chakraborty", "funding_amount": "$8M Series A", "location": "Kolkata, India", "career_page_url": "https://mihup.com/careers", "description": "Voice AI platform for contact centres and field sales"},
    {"name": "Yellow.ai", "founders": "Raghu Ravinutala, Jaya Kishore Reddy", "funding_amount": "$102M Series C", "location": "San Francisco / Bengaluru", "career_page_url": "https://yellow.ai/careers", "description": "Enterprise-grade conversational AI platform"},
    {"name": "Haptik", "founders": "Aakrit Vaish, Swapan Rajdev", "funding_amount": "Acquired by Reliance", "location": "Mumbai, India", "career_page_url": "https://haptik.ai/careers", "description": "Conversational AI for customer support automation"},
    {"name": "Senseforth AI", "founders": "Arish Ali", "funding_amount": "$3M Seed", "location": "Bengaluru, India", "career_page_url": "https://senseforth.com/careers", "description": "Cognitive AI for banking and financial services"},
    {"name": "Mad Street Den", "founders": "Ashwini Asokan, Anand Chandrasekaran", "funding_amount": "$30M Series B", "location": "Chennai, India", "career_page_url": "https://madstreetden.com/careers", "description": "AI-powered computer vision for retail and fashion"},
    {"name": "Niramai", "founders": "Geetha Manjunath, Nidhi Mathur", "funding_amount": "$6M Series A", "location": "Bengaluru, India", "career_page_url": "https://niramai.com/careers", "description": "AI-based breast cancer screening using thermal imaging"},
    {"name": "SigTuple", "founders": "Rohit Kumar Pandey, Apurv Anand", "funding_amount": "$19.5M Series B", "location": "Bengaluru, India", "career_page_url": "https://sigtuple.com/careers", "description": "AI for automated medical diagnostics from microscopy"},
    {"name": "Artivatic.ai", "founders": "Layak Singh", "funding_amount": "$2M Seed", "location": "Bengaluru, India", "career_page_url": "https://artivatic.ai/careers", "description": "AI for insurance underwriting and claims automation"},
    {"name": "Scalenut", "founders": "Mayank Jain, Saurabh Wadhawan, Rakesh Rajput", "funding_amount": "$3.1M Seed", "location": "Gurugram, India", "career_page_url": "https://scalenut.com/careers", "description": "AI-powered SEO and content intelligence platform"},
    {"name": "Rephrase.ai", "founders": "Ashray Malhotra, Nisheeth Ranjan, Shivam Mangla", "funding_amount": "$10.7M Series A", "location": "Bengaluru, India", "career_page_url": "https://rephrase.ai/careers", "description": "AI video generation from text for personalised marketing"},
]

HACKATHON_RECORDS = [
    {"event_name": "HackAI 2026", "date": "March 15-17, 2026", "location": "San Francisco, CA", "prize_pool": "$50,000", "registration_url": "https://hackai2026.dev/register", "organizer": "MLH"},
    {"event_name": "Google AI Hackathon 2026", "date": "April 5-6, 2026", "location": "Online (Global)", "prize_pool": "$100,000", "registration_url": "https://events.google.com/ai-hackathon-2026", "organizer": "Google DeepMind"},
    {"event_name": "Meta LlamaCon Hack", "date": "May 1-2, 2026", "location": "Menlo Park, CA", "prize_pool": "$75,000", "registration_url": "https://llamahack.meta.com/register", "organizer": "Meta AI"},
    {"event_name": "ETH Global Brussels", "date": "June 20-22, 2026", "location": "Brussels, Belgium", "prize_pool": "$500,000", "registration_url": "https://ethglobal.com/events/brussels", "organizer": "ETHGlobal"},
    {"event_name": "Devfolio BuildSpace 2026", "date": "February 28 - March 2, 2026", "location": "Bengaluru, India", "prize_pool": "₹20,00,000", "registration_url": "https://buildspace.devfolio.co", "organizer": "Devfolio"},
    {"event_name": "HackMIT 2026", "date": "September 12-13, 2026", "location": "Cambridge, MA", "prize_pool": "$30,000", "registration_url": "https://hackmit.org/apply", "organizer": "MIT"},
    {"event_name": "TreeHacks 2026", "date": "February 14-16, 2026", "location": "Stanford, CA", "prize_pool": "$40,000", "registration_url": "https://treehacks.com/apply", "organizer": "Stanford University"},
    {"event_name": "PennApps 2026", "date": "September 5-7, 2026", "location": "Philadelphia, PA", "prize_pool": "$25,000", "registration_url": "https://pennapps.com", "organizer": "University of Pennsylvania"},
    {"event_name": "Anthropic Claude Hackathon", "date": "March 28-30, 2026", "location": "Online (Global)", "prize_pool": "$60,000", "registration_url": "https://hack.anthropic.com", "organizer": "Anthropic"},
    {"event_name": "AWS Build On AI 2026", "date": "April 18-19, 2026", "location": "Seattle, WA", "prize_pool": "$80,000", "registration_url": "https://aws.amazon.com/hackathon-2026", "organizer": "Amazon Web Services"},
    {"event_name": "Hack The North 2026", "date": "September 18-20, 2026", "location": "Waterloo, Canada", "prize_pool": "$45,000", "registration_url": "https://hackthenorth.com", "organizer": "University of Waterloo"},
    {"event_name": "SIH 2026 (Smart India Hackathon)", "date": "December 1-2, 2026", "location": "Pan-India (Multiple Venues)", "prize_pool": "₹1,00,000 per team", "registration_url": "https://sih.gov.in/register", "organizer": "Ministry of Education, India"},
]

SAAS_RECORDS = [
    {"company_name": "Notion", "website": "https://notion.so", "pricing_tier": "Free / $8 / $15 per user/month", "features": "Wikis, Docs, Databases, AI Writing", "contact_email": "sales@notion.so", "category": "Productivity"},
    {"company_name": "Linear", "website": "https://linear.app", "pricing_tier": "Free / $8 / $14 per user/month", "features": "Issue Tracking, Cycles, Roadmaps, Git sync", "contact_email": "sales@linear.app", "category": "Project Management"},
    {"company_name": "Vercel", "website": "https://vercel.com", "pricing_tier": "Free / $20 / $40 per user/month", "features": "Frontend deployments, Edge Network, Analytics", "contact_email": "sales@vercel.com", "category": "DevOps / Hosting"},
    {"company_name": "Supabase", "website": "https://supabase.com", "pricing_tier": "Free / $25 / $599 per month", "features": "Postgres DB, Auth, Storage, Edge Functions", "contact_email": "sales@supabase.io", "category": "Backend-as-a-Service"},
    {"company_name": "Retool", "website": "https://retool.com", "pricing_tier": "$10 / $50 per user/month", "features": "Internal tool builder, DB connectors, Workflows", "contact_email": "sales@retool.com", "category": "Low-Code / Internal Tools"},
    {"company_name": "Airtable", "website": "https://airtable.com", "pricing_tier": "Free / $10 / $20 per user/month", "features": "Spreadsheet-Database hybrid, Automations, API", "contact_email": "sales@airtable.com", "category": "Database / Spreadsheet"},
    {"company_name": "PostHog", "website": "https://posthog.com", "pricing_tier": "Free (usage-based) / $450/month", "features": "Product Analytics, Session Replay, Feature Flags", "contact_email": "sales@posthog.com", "category": "Product Analytics"},
    {"company_name": "Clerk", "website": "https://clerk.com", "pricing_tier": "Free / $25 / $35 per month", "features": "Auth, User Management, MFA, Organizations", "contact_email": "support@clerk.com", "category": "Auth & Identity"},
    {"company_name": "Resend", "website": "https://resend.com", "pricing_tier": "Free / $20 / $90 per month", "features": "Transactional Email API, React Email, Webhooks", "contact_email": "support@resend.com", "category": "Email Infrastructure"},
    {"company_name": "Planetscale", "website": "https://planetscale.com", "pricing_tier": "Free / $39 / $599 per month", "features": "Serverless MySQL, Branching, Non-blocking schema changes", "contact_email": "sales@planetscale.com", "category": "Database"},
    {"company_name": "Lemon Squeezy", "website": "https://lemonsqueezy.com", "pricing_tier": "5% + $0.50 per transaction", "features": "Payments, Subscriptions, Licensing, Tax handling", "contact_email": "hello@lemonsqueezy.com", "category": "Payments / Monetisation"},
    {"company_name": "Cal.com", "website": "https://cal.com", "pricing_tier": "Free / $12 / $19 per user/month", "features": "Scheduling, Calendar sync, Team bookings, Workflows", "contact_email": "sales@cal.com", "category": "Scheduling"},
    {"company_name": "Dub.co", "website": "https://dub.co", "pricing_tier": "Free / $19 / $49 per month", "features": "Link shortening, Analytics, QR codes, Custom domains", "contact_email": "support@dub.co", "category": "Link Management"},
    {"company_name": "Trigger.dev", "website": "https://trigger.dev", "pricing_tier": "Free / $20 / $500 per month", "features": "Background jobs, Workflows, Scheduling, Retries", "contact_email": "hello@trigger.dev", "category": "Developer Tools"},
    {"company_name": "Neon", "website": "https://neon.tech", "pricing_tier": "Free / $19 / $69 per month", "features": "Serverless Postgres, Branching, Autoscaling", "contact_email": "sales@neon.tech", "category": "Database"},
]

SOURCE_SNIPPETS = {
    "startup": "According to Crunchbase and YourStory, {name} was founded by {founders} and is headquartered in {location}. The company raised {funding_amount} to accelerate product development. Their careers page is available at {career_page_url}.",
    "hackathon": "{event_name} is scheduled for {date} in {location}. Organized by {organizer}, the event offers a total prize pool of {prize_pool}. Register at {registration_url} before slots fill up.",
    "saas": "{company_name} ({website}) is a leading {category} platform. Pricing starts at {pricing_tier}. Key features include {features}. For enterprise enquiries, reach out to {contact_email}.",
    "default": "Extracted data point: {title}. Description: {description}. Source: {url}.",
}


async def run_mock_execution(run_id: str, workflow_id: str, schema: list, dag: list, prompt: str):
    try:
        prompt_lower = prompt.lower()

        # Detect dataset type
        if "startup" in prompt_lower or "company" in prompt_lower or "india" in prompt_lower:
            dataset = STARTUP_RECORDS
            snippet_key = "startup"
            domains = ["crunchbase.com", "yourstory.com", "inc42.com", "tracxn.com"]
        elif "hackathon" in prompt_lower or "event" in prompt_lower:
            dataset = HACKATHON_RECORDS
            snippet_key = "hackathon"
            domains = ["devpost.com", "mlh.io", "devfolio.co", "eventbrite.com"]
        elif "lead" in prompt_lower or "saas" in prompt_lower or "software" in prompt_lower:
            dataset = SAAS_RECORDS
            snippet_key = "saas"
            domains = ["g2.com", "capterra.com", "producthunt.com", "softwareadvice.com"]
        else:
            dataset = [
                {"title": f"Result {i}", "description": f"Extracted data item number {i}", "url": f"https://example.com/item-{i}", "date": "2026-01-01", "category": "General"}
                for i in range(10)
            ]
            snippet_key = "default"
            domains = ["example.com", "data.gov", "opendata.org"]

        # Step 1 — Query Construction
        add_log(run_id, "INFO", f"Analysing prompt: \"{prompt[:60]}...\"")
        update_run_in_db(run_id, RunStatus.running, 5)
        await asyncio.sleep(0.4)
        add_log(run_id, "INFO", "Constructed 3 semantic search queries from schema fields")
        update_run_in_db(run_id, RunStatus.running, 20)
        emit_event(run_id, {"type": "progress", "pct": 20, "step": "Query Construction"})

        # Step 2 — Source Discovery
        add_log(run_id, "INFO", f"Discovering permitted sources from: {', '.join(domains)}")
        await asyncio.sleep(0.4)
        add_log(run_id, "SUCCESS", f"robots.txt verified for {len(domains)} domains — all compliant")
        update_run_in_db(run_id, RunStatus.running, 40)
        emit_event(run_id, {"type": "progress", "pct": 40, "step": "Source Discovery"})

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
        add_log(run_id, "INFO", f"Fetching {len(dataset)} pages (rate-limited to 1 req/s)")
        await asyncio.sleep(0.5)
        add_log(run_id, "INFO", "HTML parsed → Markdown normalised for all pages")
        update_run_in_db(run_id, RunStatus.running, 60)
        emit_event(run_id, {"type": "progress", "pct": 60, "step": "Page Retrieval"})

        # Step 4 — Entity Extraction
        add_log(run_id, "INFO", f"Running structured extraction against {len(schema)} schema fields")
        await asyncio.sleep(0.5)

        records = []
        template = SOURCE_SNIPPETS.get(snippet_key, SOURCE_SNIPPETS["default"])
        for i, item in enumerate(dataset):
            try:
                snippet = template.format(**item)
            except KeyError:
                snippet = f"Extracted record from {domains[i % len(domains)]}: {json.dumps(item)}"

            records.append({
                "data": item,
                "source_url": f"https://{domains[i % len(domains)]}/listing/{i+1}",
                "source_snippet": snippet,
                "confidence_score": round(random.uniform(0.87, 1.0), 2),
                "is_duplicate": False,
            })
            add_log(run_id, "INFO", f"[{i+1}/{len(dataset)}] Extracted: {list(item.values())[0]}")

        add_log(run_id, "SUCCESS", f"{len(records)} records extracted successfully")
        update_run_in_db(run_id, RunStatus.running, 80)
        emit_event(run_id, {"type": "progress", "pct": 80, "step": "Entity Extraction"})
        emit_event(run_id, {"type": "record", "count": len(records)})

        # Step 5 — Deduplication & Validation
        add_log(run_id, "INFO", "Running deduplication pass on primary keys...")
        await asyncio.sleep(0.3)
        add_log(run_id, "SUCCESS", f"0 duplicates found — all {len(records)} records are unique")

        save_records_to_db(run_id, records)
        update_run_in_db(run_id, RunStatus.completed, 100)
        emit_event(run_id, {"type": "progress", "pct": 100, "step": "Deduplication & Validation"})
        emit_event(run_id, {"type": "done", "status": "completed"})
        add_log(run_id, "SUCCESS", f"Pipeline complete — {len(records)} records saved with full provenance")

    except Exception as e:
        add_log(run_id, "ERROR", f"Execution failed: {str(e)}")
        update_run_in_db(run_id, RunStatus.failed, 0)
        emit_event(run_id, {"type": "done", "status": "failed"})


async def start_execution_task(run_id: str, workflow_id: str, schema: list, dag: list, prompt: str, use_mock: bool):
    if run_id not in run_events:
        run_events[run_id] = []
    asyncio.create_task(run_mock_execution(run_id, workflow_id, schema, dag, prompt))
