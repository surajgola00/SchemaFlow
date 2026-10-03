# 🎬 SchemaFlow — 3-Minute Live Demo Script & Contingency Plan

This demo script is tailored for the **Code Cubicle 6.0 — Problem Statement 01** jury presentation. It showcases the exact workflow from business requirement to verified structured dataset, emphasizing architectural integrity, real-time controls, and compliance.

---

## Pitch Overview (30 Seconds)

> *"Good morning judges. Most web data extraction demos fail in two ways: either they break the moment an LLM hallucinates data that doesn’t exist on the page, or they act as black-box scrapers that blindly ignore rate limits, robots.txt, and site terms.
> 
> We built **SchemaFlow** — an AI-powered Data Intelligence Platform that dynamically compiles natural-language prompts into typed DAG execution pipelines, collects data ethically, and guarantees **Evidence-Verified Extraction** where every single field is backed by an exact, verifiable quote from source documents with character span offsets."*

---

## 3-Minute Walkthrough (Minute by Minute)

### Minute 1: Dynamic Requirement Compilation
1. **Navigate to Prompt Studio** (`http://localhost:5173`).
2. **Point out the Engine Mode Badge** in the top navigation:
   - Notice the badge showing `LIVE LLM: gemini-3.1-flash-lite` (or toggle to Demo Replay).
3. **Select Preset 1**: *"Collect seed-stage AI startups in India with company name, founders, funding amount, location, and careers page URL."*
4. **Click "Compile Workflow Spec"**:
   - The LLM dynamically identifies the entity type (`ai_startup`), extracts required & optional fields with validators (e.g., `url` validator for `careers_page_url`, `currency` validator for `funding_amount`).
   - Highlight **Workflow Intelligence**: Key Assumptions made, Compliance & Exclusions identified (e.g., "Excluding dead startups and unverified stealth announcements"), and Clarifying Questions for edge cases.
   - Point out the **Interactive Pipeline DAG** rendered using React Flow showing the topological execution sequence (`discover_sources` -> `fetch` -> `extract` -> `normalize` -> `validate` -> `dedupe` -> `score` -> `finalize`).
5. **Adjust Limits**:
   - Demonstrate the sliders: set `Max Records` to 25 and `Per-Domain RPS` to 1.0.

### Minute 2: Managed Execution & Live Compliance
1. **Click "Launch Pipeline Execution"**:
   - The UI transitions to the **Execution Monitor**.
   - Show the **Live Pipeline DAG**: nodes transition color in real-time (slate `pending` -> blue pulsing `running` -> emerald `succeeded`) with live item counters (`in: X -> out: Y`).
2. **Demonstrate Pipeline Management**:
   - Click **Pause**: show that the pipeline immediately halts at the current node boundary.
   - Click **Resume**: show work picking up smoothly without state corruption.
3. **Inspect the Sources Used & Blocked Panel**:
   - Switch to the **Sources (Used & Blocked)** tab.
   - Show how SchemaFlow respects `robots.txt` and enforces SSRF protection. Any blocked or rate-limited URL is surfaced with an explicit reason (e.g. `robots.txt disallows path /apply`, `domain rate limit reached`), proving ethical scraping compliance.
4. **Inspect Terminal Logs**:
   - Switch to **Terminal Logs** to show structured, correlated logs with node IDs and timestamps.

### Minute 3: Evidence Grounding, Data Explorer & Export
1. **Click "Explore Extracted Dataset"** (or switch to Data Explorer):
   - TanStack Table renders the extracted records with confidence scores.
   - Demonstrate the **Evidence Score Slider**: drag to 85% to filter out borderline records.
   - Toggle **Verified Only** to view only 100% grounded records.
   - Click **Column Filters** to filter by specific fields (e.g. filter location by "Bengaluru").
   - Click **Columns** dropdown to hide or show columns dynamically.
2. **Inspect Provenance**:
   - Click on any row to open the **Provenance Drawer**.
   - Show the exact character span highlighting the verbatim quote found in the original source document.
   - Point to the confidence breakdown and source URL link.
3. **Human-in-the-Loop Feedback & Export**:
   - In the Data Grid, demonstrate the **Audit & Feedback** column: click `ThumbsDown` on an unwanted record.
   - The record is immediately tagged as `Excluded`.
   - Click **Export CSV** or **Export XLSX**: show that records flagged as wrong are automatically filtered out from downstream exports.
4. **History & Dataset Versioning**:
   - Switch to **History & Datasets**.
   - Show the **Dataset Version Timeline** (v1 vs v2).
   - Click **Compute Diff** to demonstrate the exact run-to-run changes (`+Added`, `-Removed`, `~Changed`).
   - Open the **Schedule** modal to show automated cron triggers.

---

## ⚡ Contingency Plan: Wi-Fi / API Key Failure Fallback

If conference Wi-Fi is congested or external APIs are blocked:

1. **Switch to Demo Replay Mode**:
   - In the Studio header, toggle the Mode switch from **Live** to **Demo Mode**.
2. **Replay Realistic Fixtures through the Real DAG Engine**:
   - Select any of the 5 shipped demo fixtures:
     1. `ai_startups_india`
     2. `remote_python_internships`
     3. `open_source_ml_repos`
     4. `arxiv_rag_papers`
     5. `tech_sponsorship_opportunities`
3. **Explain to Judges**:
   - *"Notice that in Demo Mode, SchemaFlow replays raw offline web responses through the REAL topological DAG engine, real quote verifier, real currency/date normalizers, real multi-tier deduplication, and real SSE stream. Only the raw external network fetch and LLM API calls are replayed from cached fixtures, ensuring 100% deterministic, zero-latency demonstration even with zero internet connectivity."*
4. **Run Pre-compiled Smoke Test**:
   - Run `python scripts/smoke_live.py` from the terminal to show live API capability if Wi-Fi recovers.
