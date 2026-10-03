"""
Central configuration via pydantic-settings.
All settings can be overridden by environment variables or a backend/.env file.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # ── Search ────────────────────────────────────────────────────────────────
    search_provider: Literal[
        "duckduckgo_html", "serper", "brave", "searxng"
    ] = "duckduckgo_html"
    search_api_key: str = ""

    # ── Crawler ───────────────────────────────────────────────────────────────
    user_agent: str = "SchemaFlow/2.0 (data-intelligence)"
    max_pages_per_run: int = 50
    max_records_per_run: int = 200
    max_runtime_seconds: int = 300
    per_domain_rps: float = 1.0
    max_response_size_bytes: int = 2 * 1024 * 1024  # 2 MB
    max_redirects: int = 3

    # ── Concurrency ───────────────────────────────────────────────────────────
    max_concurrent_runs: int = 2

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./database.db"

    # ── Demo ──────────────────────────────────────────────────────────────────
    demo_replay_speed: Literal["fast", "cinematic"] = "fast"

    # ── Derived ───────────────────────────────────────────────────────────────
    @property
    def llm_mode(self) -> Literal["live", "mock"]:
        """Return 'live' only when an API key is configured."""
        return "live" if self.llm_api_key.strip() else "mock"

    @field_validator("max_pages_per_run", mode="before")
    @classmethod
    def clamp_pages(cls, v: int) -> int:
        return max(1, min(int(v), 500))

    @field_validator("max_records_per_run", mode="before")
    @classmethod
    def clamp_records(cls, v: int) -> int:
        return max(1, min(int(v), 2000))

    @field_validator("per_domain_rps", mode="before")
    @classmethod
    def clamp_rps(cls, v: float) -> float:
        return max(0.1, min(float(v), 10.0))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
