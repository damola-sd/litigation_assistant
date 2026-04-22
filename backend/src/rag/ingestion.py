"""Ingest Kenyan legal corpus from data/raw/ into ChromaDB.

Run once to build the index:
    uv run python -m src.rag.ingestion

Re-run whenever documents are added to data/raw/.
"""

import uuid
from pathlib import Path

from openai import OpenAI

from src.core.config import settings
from src.rag.vector_store import DEFAULT_PERSIST_DIR, EMBED_MODEL, get_chroma_client, get_collection

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
_EMBED_BATCH_SIZE = 256


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-based chunks, stripping whitespace from each."""
    if not text.strip():
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += size - overlap
    return chunks


def ingest_documents(
    raw_dir: Path = RAW_DIR,
    persist_dir: str = DEFAULT_PERSIST_DIR,
    api_key: str | None = None,
) -> dict:
    """Load all .txt and .md files from raw_dir, chunk, embed, and store in ChromaDB.

    Returns a summary dict with 'detail' and 'chunks_added'.
    """
    resolved_key = api_key or settings.openai_api_key
    txt_files = sorted(raw_dir.glob("*.txt")) + sorted(raw_dir.glob("*.md"))
    if not txt_files:
        return {"detail": "no_files_found", "chunks_added": 0}

    all_docs: list[str] = []
    all_ids: list[str] = []
    all_metadata: list[dict] = []

    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for i, chunk in enumerate(chunk_text(text)):
            all_docs.append(chunk)
            all_ids.append(f"{fpath.stem}_{i}_{uuid.uuid4().hex[:6]}")
            all_metadata.append({"source": fpath.name, "chunk_index": i})

    if not all_docs:
        return {"detail": "no_content", "chunks_added": 0}

    openai_client = OpenAI(api_key=resolved_key)
    embeddings: list[list[float]] = []
    for i in range(0, len(all_docs), _EMBED_BATCH_SIZE):
        batch = all_docs[i : i + _EMBED_BATCH_SIZE]
        resp = openai_client.embeddings.create(model=EMBED_MODEL, input=batch)
        embeddings.extend(item.embedding for item in resp.data)

    chroma = get_chroma_client(persist_dir)
    collection = get_collection(chroma)
    collection.add(documents=all_docs, embeddings=embeddings, ids=all_ids, metadatas=all_metadata)

    return {"detail": "ok", "chunks_added": len(all_docs)}


if __name__ == "__main__":
    result = ingest_documents()
    print(result)
