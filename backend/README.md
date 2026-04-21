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
uv run dev
```

This runs Uvicorn with reload on `http://127.0.0.1:8000`. Equivalent manual command:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Project layout

```
backend/
├── app/
│   ├── main.py              # FastAPI app + router registration
│   ├── api/routers/         # Route modules (health, me, analyze, history)
│   ├── core/                # Settings and shared config (placeholder)
│   ├── models/              # Domain / DB models (placeholder)
│   └── services/            # Business logic and agents (placeholder)
├── pyproject.toml           # Project metadata and dependencies (uv)
├── requirements.txt         # Same dependencies for pip-based workflows
└── uv.lock                  # Locked versions (uv)
```

## API surface (planned)

| Method | Path | Notes |
|--------|------|--------|
| `GET` | `/health` | Liveness check (returns `{"status":"ok"}`). |
| `GET` | `/me` | User profile from Clerk JWT (stub). |
| `POST` | `/analyze` | Case input and agent pipeline (stub). |
| `GET` | `/history` | List analyses for the user (stub). |
| `GET` | `/history/{analysis_id}` | Single analysis with agent steps (stub). |

Interactive docs: `http://127.0.0.1:8000/docs` (Swagger UI) and `http://127.0.0.1:8000/redoc`.

## Environment variables

Not wired yet. When you implement auth and data layers, you will typically add variables such as database URL, Clerk JWKS URL or secrets, and AI provider keys. Use `app/core/config.py` (or pydantic-settings) as the single place to load them.
