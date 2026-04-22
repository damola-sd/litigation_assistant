"""ChromaDB client and collection management for the litigation prep RAG pipeline."""

from pathlib import Path

import chromadb

COLLECTION_NAME = "kenyan_legal_corpus"
EMBED_MODEL = "text-embedding-3-small"

# Absolute path to data/vector_db/ relative to this file's location in the repo tree.
# File is at: backend/src/rag/vector_store.py  → parents[3] == repo root.
DEFAULT_PERSIST_DIR = str(Path(__file__).resolve().parents[3] / "data" / "vector_db")


def get_chroma_client(persist_dir: str = DEFAULT_PERSIST_DIR) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=persist_dir)


def get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
