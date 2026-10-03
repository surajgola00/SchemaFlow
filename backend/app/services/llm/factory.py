"""
LLM client factory — returns real or mock client based on settings.
"""
from __future__ import annotations

from typing import Literal, Union

from app.config import get_settings
from app.services.llm.client import LLMClient
from app.services.llm.mock import MockLLMClient

AnyLLMClient = Union[LLMClient, MockLLMClient]


def get_llm(force_mock: bool = False) -> AnyLLMClient:
    """Return MockLLMClient if force_mock or no API key is set, else real LLMClient."""
    if force_mock:
        return MockLLMClient()
    settings = get_settings()
    if settings.llm_api_key.strip():
        return LLMClient()
    return MockLLMClient()


def get_llm_mode() -> Literal["live", "mock"]:
    settings = get_settings()
    return "live" if settings.llm_api_key.strip() else "mock"
