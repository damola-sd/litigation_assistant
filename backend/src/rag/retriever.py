"""RAG retriever — embed query with OpenAI, then similarity-search ChromaDB.

The function signature ``(query: str) -> list[str]`` is the integration contract
with the orchestrator.  Do not change the signature; only this body should need
to change when swapping vector backends.
"""

import asyncio
import time

from src.core.logging import get_logger
from src.core.openai_client import get_async_client
from src.rag.vector_store import DEFAULT_PERSIST_DIR, EMBED_MODEL, get_chroma_client, get_collection

logger = get_logger(__name__)

# Module-level reference shares the process-level AsyncOpenAI singleton.
# Tests that patch "src.rag.retriever._openai" continue to work unchanged
# because patching replaces this name in the module namespace.
_openai = get_async_client()

_DEFAULT_N_RESULTS = 5


async def rag_retrieve(query: str, n_results: int = _DEFAULT_N_RESULTS) -> list[str]:
    """Return the top-k most relevant legal corpus chunks for the given query.

    Returns an empty list if the query is blank or the vector store is empty.
    The ChromaDB query runs in a thread pool via ``asyncio.to_thread`` to avoid
    blocking the FastAPI event loop.
    """
    if not query.strip():
        return []

    logger.info("rag_embed_start", model=EMBED_MODEL, query_len=len(query))
    start = time.monotonic()

    embed_resp = await _openai.embeddings.create(model=EMBED_MODEL, input=query)
    query_embedding: list[float] = embed_resp.data[0].embedding

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info("rag_embed_complete", model=EMBED_MODEL, duration_ms=duration_ms)

    def _query_chroma() -> list[str]:
        client = get_chroma_client(DEFAULT_PERSIST_DIR)
        collection = get_collection(client)
        count = collection.count()
        if count == 0:
            logger.info("rag_collection_empty")
            return []
        k = min(n_results, count)
        result = collection.query(
            query_embeddings=[query_embedding],  # type: ignore[arg-type]
            n_results=k,
            include=["documents"],
        )
        docs = [doc for doc in (result.get("documents") or [[]])[0] if doc and doc.strip()]
        logger.info("rag_retrieve_complete", chunks_returned=len(docs), collection_size=count)
        return docs

    return await asyncio.to_thread(_query_chroma)
