"""
Connector Registry — maps connector names to instances.
"""
from __future__ import annotations

from typing import Optional

from app.services.connectors.base import Connector
from app.services.connectors.rss import RSSConnector
from app.services.connectors.sources import (
    ArxivConnector,
    DirectURLsConnector,
    GitHubConnector,
    HackerNewsConnector,
    SitemapConnector,
    WikipediaConnector,
)
from app.services.connectors.web_search import WebSearchConnector

CONNECTOR_REGISTRY: dict[str, Connector] = {
    "web_search": WebSearchConnector(),
    "rss": RSSConnector(),
    "hackernews": HackerNewsConnector(),
    "github": GitHubConnector(),
    "wikipedia": WikipediaConnector(),
    "arxiv": ArxivConnector(),
    "direct_urls": DirectURLsConnector(),
    "sitemap": SitemapConnector(),
}


def get_connector(name: str) -> Optional[Connector]:
    return CONNECTOR_REGISTRY.get(name)
