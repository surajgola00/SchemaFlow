"""Crawler package."""
from app.services.crawler.fetcher import fetcher, FetchResult
from app.services.crawler.rate_limiter import rate_limiter
from app.services.crawler.robots import robots_cache
from app.services.crawler.ssrf import is_safe_url

__all__ = ["fetcher", "FetchResult", "rate_limiter", "robots_cache", "is_safe_url"]
