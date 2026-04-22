# Backend (FastAPI)

Python service for the Litigation Prep Assistant: planned responsibilities include AI orchestration, Clerk JWT validation, persistence, and structured responses for `/analyze` and history endpoints. This package is currently a **scaffold** with stub routes.

## Requirements

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (recommended for installs and virtual environments)

## Install

From this directory (`backend/`):

```bash
uv sync
```

That creates `.venv/`, resolves dependencies in `uv.lock`, and installs the project in editable mode.

### Using `requirements.txt` only

If you prefer not to use `pyproject.toml` for installs:

```bash
uv venv
uv pip install -r requirements.txt
```

Alternatively, with plain pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the dev server

```bash
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

This runs Uvicorn with reload on `http://127.0.0.1:8000`. Equivalent manual command:

```bash
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

## Project layout

```
backend/
├── src/
│   ├── main.py              # FastAPI app + router registration
│   ├── api/                 # Route modules and auth dependencies
│   ├── core/                # Settings and security placeholders
│   ├── database/            # SQLAlchemy engine + models
│   ├── agents/              # Extraction/Strategy/Drafting/QA scaffolds
│   ├── rag/                 # RAG ingestion/retriever/vector store stubs
│   └── schemas/             # API + AI response models
├── app/                     # Legacy scaffold kept temporarily for compatibility
├── pyproject.toml           # Project metadata and dependencies (uv)
├── requirements.txt         # Same dependencies for pip-based workflows
└── uv.lock                  # Locked versions (uv)
```

## API surface (planned)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness check (returns `{"status":"ok"}`). |
| `GET` | `/me` | User profile from Clerk JWT (stub). |
| `POST` | `/api/v1/analyze` | Multipart form: `title` (required), `case_text` (optional), `case_file` (optional `.txt`/`.md`/`.pdf`). At least one of `case_text` or file body must yield text; file contents are appended after typed text. Returns SSE. |
| `GET` | `/api/v1/cases` | List cases for the user. |
| `GET` | `/api/v1/cases/{id}` | Single case with agent steps. |

Interactive docs: `http://127.0.0.1:8000/docs` (Swagger UI) and `http://127.0.0.1:8000/redoc`.

## Environment variables

Not wired yet. When you implement auth and data layers, you will typically add variables such as database URL, Clerk JWKS URL or secrets, and AI provider keys. Use `app/core/config.py` (or pydantic-settings) as the single place to load them.
