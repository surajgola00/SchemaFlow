"""
SchemaFlow v2 — FastAPI entrypoint.
"""
from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import create_db_and_tables
from app.logging_config import configure_logging, get_logger

# Import all models so SQLModel.metadata.create_all creates their tables
import app.models  # noqa: F401

from app.routers import workflows, runs, exports
from app.routers import records, schedules, datasets

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # Startup
    configure_logging()
    create_db_and_tables()

    # Start APScheduler (graceful if not importable)
    scheduler_started = False
    try:
        from app.services.scheduler import start_scheduler
        start_scheduler()
        scheduler_started = True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Scheduler not started: {e}")

    # Startup self-check log
    settings = get_settings()
    raw_key = settings.llm_api_key.strip()
    masked_key = (raw_key[:4] + "..." + raw_key[-4:]) if len(raw_key) > 8 else ("(none)" if not raw_key else "***")
    llm_mode = "live" if raw_key else "mock"

    logger = get_logger("schemaflow.startup")
    logger.info(
        f"STARTUP SELF-CHECK: LLM Mode={llm_mode} | Model={settings.llm_model} | "
        f"Key={masked_key} | BaseURL={settings.llm_base_url} | "
        f"Search={settings.search_provider} | DB={settings.database_url} | "
        f"Scheduler={scheduler_started} | CORS={CORS_ORIGINS}"
    )

    yield

    # Shutdown
    if scheduler_started:
        try:
            from app.services.scheduler import stop_scheduler
            stop_scheduler()
        except Exception:
            pass


app = FastAPI(
    title="SchemaFlow v2 API",
    version="2.0.0",
    description="AI-Powered Data Intelligence Platform — evidence-verified extraction from permitted public sources.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = get_logger(__name__)
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "error_type": exc.__class__.__name__,
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(records.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "SchemaFlow v2 API"}
