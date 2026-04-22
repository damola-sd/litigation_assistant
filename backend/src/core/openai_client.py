"""Singleton factory for the shared AsyncOpenAI client.

All agent modules obtain their client through ``get_async_client()`` so that
the underlying connection pool is shared across the process and tests can
override the instance in a single place.
"""

from openai import AsyncOpenAI

from src.core.config import settings

_client: AsyncOpenAI | None = None


def get_async_client() -> AsyncOpenAI:
    """Return the process-level AsyncOpenAI singleton, creating it on first call."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client
