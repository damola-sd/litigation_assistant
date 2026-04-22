"""RAG retriever — embed query with OpenAI, then similarity-search ChromaDB.

The function signature (query: str) -> list[str] is the integration contract with
the orchestrator. Do not change the signature; only this body should need to change
when swapping vector backends.
"""

import asyncio

from openai import AsyncOpenAI

from src.core.config import settings
from src.rag.vector_store import DEFAULT_PERSIST_DIR, EMBED_MODEL, get_chroma_client, get_collection

_openai = AsyncOpenAI(api_key=settings.openai_api_key)

_DEFAULT_N_RESULTS = 5


async def rag_retrieve(query: str, n_results: int = _DEFAULT_N_RESULTS) -> list[str]:
    """Return the top-k most relevant legal corpus chunks for the given query.

    Returns an empty list if the query is blank or the vector store is empty.
    The ChromaDB query runs in a thread pool via asyncio.to_thread to avoid
    blocking the FastAPI event loop.
    """
    if not query.strip():
        return []

    embed_resp = await _openai.embeddings.create(model=EMBED_MODEL, input=query)
    query_embedding: list[float] = embed_resp.data[0].embedding

    def _query_chroma() -> list[str]:
        client = get_chroma_client(DEFAULT_PERSIST_DIR)
        collection = get_collection(client)
        count = collection.count()
        if count == 0:
            return []
        k = min(n_results, count)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents"],
        )
        return [doc for doc in (result.get("documents") or [[]])[0] if doc and doc.strip()]

    return await asyncio.to_thread(_query_chroma)
