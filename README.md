# ⚡ SchemaFlow — AI-Powered Data Intelligence Platform

> Transform natural-language data requests into structured, traceable datasets — instantly.

---

## 🏗️ Architecture

```
schemaflow/
├── backend/                  # FastAPI + SQLite + async task runner
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint, CORS, lifespan
│   │   ├── database.py       # SQLite engine + session factory
│   │   ├── models/           # SQLModel entities (Workflow, Run, Record)
│   │   ├── routers/          # API route handlers
│   │   └── services/         # Compiler, Crawler, Extractor, Executor
│   └── requirements.txt
└── frontend/                 # React 18 + Vite + TypeScript + Tailwind
    ├── src/
    │   ├── App.tsx            # Root app + tab navigation
    │   ├── api/client.ts      # API + SSE helpers
    │   ├── types/index.ts     # TypeScript interfaces
    │   └── components/        # Studio, ExecutionView, DataGrid, History
    ├── package.json
    └── vite.config.ts
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **npm** or **pnpm**

---

### 1. Start the Backend

```bash
cd schemaflow/backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: **http://localhost:8000**
API docs at: **http://localhost:8000/docs**

---

### 2. Start the Frontend

```bash
cd schemaflow/frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 🎮 Demo Walkthrough

### Step 1 — Prompt Studio
1. Open **http://localhost:5173**
2. Click one of the **preset suggestion cards** (or type your own prompt)
3. Click **"Compile Workflow"** — the AI parses your intent into a structured schema + DAG
4. Review the **Schema Fields** (type-tagged pills) and **Execution DAG** pipeline
5. Click **"Execute Workflow"**

### Step 2 — Live Execution Monitor
- Watch the **progress bar** advance through 5 pipeline phases
- See **compliance badges** confirm robots.txt + rate-limit adherence
- Read the **streaming terminal** as records are discovered and extracted
- Live **record counter** shows ingestion in real time

### Step 3 — Data Explorer
- Browse all extracted records in a **sortable, filterable table**
- Use the **search bar** to filter across all fields
- **Click any row** to open the **Provenance Drawer**:
  - Original source URL
  - Exact text snippet the data was extracted from
  - Confidence score + timestamp
- Export as **CSV** or **JSON**

### Step 4 — History
- View all past workflows and runs
- See status badges, record counts, and runtime
- **Re-run** any past workflow with one click

---

## 🔀 Engine Modes

| Mode | Description |
|------|-------------|
| 🟡 **Demo Mock** | Simulates realistic crawling over pre-cached data. Works offline. Perfect for demos. |
| 🟢 **Live Web** | Real HTTP crawling with robots.txt compliance, rate limiting, and live LLM extraction. |

Toggle the **engine switch in the header** to switch modes at any time.

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/compile` | POST | Compile prompt into schema + DAG |
| `/api/v1/runs/start` | POST | Start workflow execution |
| `/api/v1/runs/{id}` | GET | Get run status + progress |
| `/api/v1/runs/{id}/stream` | GET | SSE stream of live progress/logs |
| `/api/v1/runs/{id}/records` | GET | Paginated extracted records |
| `/api/v1/runs/{id}/export` | GET | Download as CSV or JSON |
| `/api/v1/history` | GET | All workflows + runs |

---

## 🔒 Compliance & Ethics

SchemaFlow enforces responsible data collection:
- ✅ `robots.txt` verified before every domain fetch
- ✅ 1 request/second rate limiting (no IP bans)
- ✅ Only public, permitted sources
- ✅ Source snippets stored for 100% provenance traceability
- ✅ Deduplication prevents redundant records

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLModel, SQLite, asyncio |
| LLM Layer | OpenAI-compatible (mock fallback built-in) |
| Crawling | httpx, BeautifulSoup4, html2text |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| Tables | TanStack Table v8 |
| Icons | Lucide React |
| Streaming | Server-Sent Events (SSE) |

---

## ⚙️ Environment Variables (Optional)

Create `backend/.env` to enable live LLM extraction:

```env
OPENAI_API_KEY=sk-...        # Optional: enables live LLM extraction
OPENAI_MODEL=gpt-4o-mini     # Default model
```

Without these, the mock compiler and extractor handle everything automatically.

---

## 🏆 Hackathon Notes

- **No API keys needed** — Demo Mock mode works fully offline
- **No Docker required** — Pure Python + Node.js setup
- **Cold start < 30 seconds** — Just `pip install` + `npm install`
- **Zero hallucination guarantee** — All records backed by stored source snippets
