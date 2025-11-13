"""Base machinery for real-estate web collectors."""
from __future__ import annotations

import abc
from datetime import datetime
from typing import AsyncIterator

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from immotogo.config import get_settings
from immotogo.data.schemas import Listing


class CollectorError(RuntimeError):
    """Raised when a collector fails to fetch data."""


class BaseCollector(abc.ABC):
    """Abstract base class that all collectors must implement."""

    name: str
    base_url: str

    def __init__(self) -> None:
        settings = get_settings()
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": "ImmoTogoBot/0.1 (+https://github.com/immotogo)",
                "Accept-Language": "fr-FR,fr;q=0.9",
            },
            timeout=settings.crawl_timeout_seconds,
            follow_redirects=True,
        )
        self._retry = AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=20),
            retry=retry_if_exception_type(httpx.HTTPError),
            reraise=True,
        )

    async def __aenter__(self) -> "BaseCollector":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.aclose()

    async def fetch_html(self, url: str) -> str:
        """Retrieve HTML content with retries."""

        async for attempt in self._retry:  # type: ignore[assignment]
            with attempt:
                response = await self._client.get(url)
                response.raise_for_status()
                return response.text
        raise CollectorError(f"Unable to fetch url={url}")

    @abc.abstractmethod
    async def collect(self) -> AsyncIterator[Listing]:
        """Iterate over normalized listings."""

    def _now(self) -> datetime:
        return datetime.utcnow()
