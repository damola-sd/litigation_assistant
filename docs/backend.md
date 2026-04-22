# Backend — Technical Reference

**Stack:** FastAPI · Python 3.11+ · SQLAlchemy (async) · SQLite (dev) → Postgres (prod) · OpenAI GPT-4o  

---

## Table of Contents

1. [How to Run Locally](#1-how-to-run-locally)
2. [Project Structure](#2-project-structure)
3. [API Reference](#3-api-reference)
4. [SSE Stream Format](#4-sse-stream-format)
5. [Database Schema](#5-database-schema)
6. [AI Agent Pipeline](#6-ai-agent-pipeline)
7. [Integration Guide](#7-integration-guide)
8. [Environment Variables](#8-environment-variables)

---

## 1. How to Run Locally

```bash
cd backend

# Run the automated test suite (no API key needed, ~1 second)
uv run pytest tests/ -v

# Start the live development server
uv run uvicorn src.main:app --reload --port 8000
```

Make sure `backend/.env` contains your OpenAI API key before starting the server:
```
OPENAI_API_KEY=sk-...
```

Delete `backend/litigation.db` if you get a database error on first run — the schema may have changed.

### Smoke test with curl

```bash
# Health check
curl http://localhost:8000/health

# Who am I
curl http://localhost:8000/api/v1/me -H "x-user-id: alice"

# Run an analysis (streams live)
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -H "x-user-id: alice" \
  -d '{"raw_case_text": "On 1 Jan 2024, John signed a contract with ABC Ltd for delivery of goods worth KES 200,000. ABC failed to deliver. John seeks damages."}'

# List past cases
curl http://localhost:8000/api/v1/cases -H "x-user-id: alice"

# Case detail (paste case_id from the done event above)
curl http://localhost:8000/api/v1/cases/<case_id> -H "x-user-id: alice"
```

---

## 2. Project Structure

```
backend/
├── main.py              # entry point shim: from src.main import app
├── src/
│   ├── main.py          # FastAPI app, CORS middleware, routers, lifespan hook
│   ├── cli.py           # dev server launcher
│   ├── core/
│   │   └── config.py    # reads .env, exposes settings singleton
│   ├── database/
│   │   ├── models.py    # ORM table definitions: User, Case, AgentStep
│   │   └── session.py   # engine, session factory, get_db, init_db
│   ├── schemas/
│   │   ├── ai_schemas.py   # Pydantic shapes for AI agent inputs/outputs
│   │   └── api_schemas.py  # Pydantic shapes for HTTP requests/responses
│   ├── agents/
│   │   ├── extraction.py   # GPT-4o-mini: extract facts, entities, timeline
│   │   ├── strategy.py     # GPT-4o: map facts to Kenyan law + arguments
│   │   ├── drafting.py     # GPT-4o: produce formal markdown brief
│   │   ├── qa.py           # GPT-4o-mini: hallucination + logic audit
│   │   └── orchestrator.py # runs all 5 steps, streams SSE, saves to DB
│   ├── api/
│   │   ├── dependencies.py  # auth dependency stub (John replaces with Clerk JWT)
│   │   ├── routes_analyze.py
│   │   ├── routes_auth.py
│   │   └── routes_cases.py
│   └── rag/
│       └── retriever.py     # returns [] stub (Amit replaces with ChromaDB)
└── tests/
    ├── conftest.py          # fixtures, mock agent data, helpers
    ├── test_analyze.py      # 27 tests for POST /api/v1/analyze
    ├── test_history.py      # 21 tests for case history endpoints
    ├── test_health.py       # 3 tests
    └── test_me.py           # 5 tests
```

---

## 3. API Reference

### `GET /health`
Public. No auth required.
```json
{ "status": "ok" }
```

---

### `GET /api/v1/me`
Returns the authenticated user. Currently reads the `x-user-id` header (stub). John replaces this with Clerk JWT.

**Headers:** `x-user-id: <user_id>` (dev stub) → `Authorization: Bearer <token>` (production)

**Response:**
```json
{ "user_id": "alice", "email": null }
```

---

### `POST /api/v1/analyze`
Runs the full multi-agent pipeline. Returns a Server-Sent Events stream.

**Headers:**
```
x-user-id: alice
Content-Type: application/json
```

**Request body:**
```json
{ "raw_case_text": "Your messy case description here..." }
```

- `raw_case_text` is required. Empty or whitespace-only values return `422`.
- Sending the old name `case_text` also returns `422`.

**Response:** `text/event-stream` — see [SSE Stream Format](#4-sse-stream-format) below.

---

### `GET /api/v1/cases`
Returns all cases for the authenticated user, newest first.

**Response:**
```json
[
  {
    "id": "753fc3cb-17d0-4529-9aaf-2caa8dff611b",
    "raw_input": "On 1 Jan 2024, John signed...",
    "status": "COMPLETED",
    "created_at": "2024-01-15T10:30:00+00:00"
  }
]
```

---

### `GET /api/v1/cases/{case_id}`
Returns a single case with all 5 agent step results.

Returns `404` if the case doesn't exist **or** belongs to a different user.

**Response:**
```json
{
  "id": "753fc3cb-...",
  "raw_input": "On 1 Jan 2024...",
  "status": "COMPLETED",
  "created_at": "2024-01-15T10:30:00+00:00",
  "steps": [
    {
      "id": "...",
      "step_name": "extraction",
      "step_index": 0,
      "status": "COMPLETED",
      "result": { "core_facts": [...], "entities": [...], "chronological_timeline": [...] }
    },
    {
      "step_name": "rag_retrieval",
      "step_index": 1,
      "result": { "chunks": [] }
    },
    {
      "step_name": "strategy",
      "step_index": 2,
      "result": { "legal_issues": [...], "applicable_laws": [...], "arguments": [...], ... }
    },
    {
      "step_name": "drafting",
      "step_index": 3,
      "result": { "brief_markdown": "# IN THE MATTER OF...\n\n## FACTS\n..." }
    },
    {
      "step_name": "qa",
      "step_index": 4,
      "result": { "risk_level": "LOW", "hallucination_warnings": [], "missing_logic": [] }
    }
  ]
}
```

---

## 4. SSE Stream Format

The `/api/v1/analyze` endpoint streams events using the [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) standard. Each message is a line starting with `data: ` followed by JSON, terminated by a blank line.

> **Frontend note:** Standard `EventSource` does not support POST or custom headers. Use `@microsoft/fetch-event-source` as specified in the FSD.

### Step running event
Emitted immediately when a step starts. Use this to show a spinner.
```json
{ "step": "extraction", "status": "running", "step_index": 0 }
```

### Step completed event
Emitted when a step finishes. Contains the full result.
```json
{
  "step": "extraction",
  "status": "completed",
  "step_index": 0,
  "data": {
    "core_facts": ["John Kamau signed a contract..."],
    "entities": [{ "name": "John Kamau", "type": "person", "role": "buyer" }],
    "chronological_timeline": [{ "date": "15 March 2023", "event": "Agreement signed" }]
  }
}
```

### Final event
Emitted after all 5 steps complete successfully. Use `case_id` to navigate to the results page.
```json
{ "step": "done", "status": "completed", "case_id": "753fc3cb-17d0-4529-9aaf-2caa8dff611b" }
```

### Error event
Emitted if any step fails. The stream ends after this.
```json
{ "event": "error", "detail": "OpenAI rate limit exceeded" }
```

### Full event sequence (happy path)
```
data: {"step":"extraction",   "status":"running",   "step_index":0}
data: {"step":"extraction",   "status":"completed", "step_index":0, "data":{...}}
data: {"step":"rag_retrieval","status":"running",   "step_index":1}
data: {"step":"rag_retrieval","status":"completed", "step_index":1, "data":{"chunks":[]}}
data: {"step":"strategy",     "status":"running",   "step_index":2}
data: {"step":"strategy",     "status":"completed", "step_index":2, "data":{...}}
data: {"step":"drafting",     "status":"running",   "step_index":3}
data: {"step":"drafting",     "status":"completed", "step_index":3, "data":{"brief_markdown":"# IN THE MATTER OF..."}}
data: {"step":"qa",           "status":"running",   "step_index":4}
data: {"step":"qa",           "status":"completed", "step_index":4, "data":{"risk_level":"LOW",...}}
data: {"step":"done",         "status":"completed", "case_id":"753fc3cb-..."}
```

---

## 5. Database Schema

Three tables. Status values are uppercase strings throughout.

### `users`
Populated by John when Clerk JWT auth is live.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID string | Primary key |
| `clerk_id` | string | Unique, indexed |
| `email` | string | |
| `tier` | string | `"FREE"` or `"PRO"` |
| `created_at` | timestamp with tz | |

### `cases`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID string | Primary key |
| `user_id` | string | Indexed. FK to `users.id` added by Sodiq when auth is live |
| `title` | string | Auto-generated from first sentence of `raw_input` |
| `raw_input` | text | The full case text submitted by the user |
| `status` | string | `PROCESSING` → `COMPLETED` or `FAILED` |
| `created_at` | timestamp with tz | |

### `agent_steps`
One row per agent step per case. A completed case always has exactly 5 rows.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID string | Primary key |
| `case_id` | UUID string | FK → `cases.id` |
| `step_name` | string | `extraction`, `rag_retrieval`, `strategy`, `drafting`, `qa` |
| `step_index` | int | `0` through `4` |
| `status` | string | `PROCESSING` → `COMPLETED` |
| `result` | JSON | Full output of the agent for this step |

---

## 6. AI Agent Pipeline

Data flows sequentially. Each agent receives the output of all previous agents.

```
raw_case_text
    │
    ▼
[0] Extraction  (gpt-4o-mini, temp=0.1)
    → core_facts: list[str]
    → entities: list[{name, type, role}]
    → chronological_timeline: list[{date, event}]
    │
    ▼
[1] RAG Retrieval  (Amit's ChromaDB — currently returns [])
    → chunks: list[str]  (relevant Kenyan statutes / case law excerpts)
    │
    ▼
[2] Strategy  (gpt-4o, temp=0.2)  ← receives extraction + rag chunks
    → legal_issues: list[str]
    → applicable_laws: list[str]
    → arguments: list[{issue, applicable_kenyan_law, argument_summary}]
    → counterarguments: list[str]
    → legal_reasoning: str
    │
    ▼
[3] Drafting  (gpt-4o, temp=0.3)  ← receives extraction + strategy
    → brief_markdown: str
      (sections: IN THE MATTER OF / FACTS / ISSUES / LEGAL ARGUMENTS / CONCLUSION)
    │
    ▼
[4] QA  (gpt-4o-mini, temp=0.1)  ← receives extraction + draft markdown
    → risk_level: "LOW" | "MEDIUM" | "HIGH"
    → hallucination_warnings: list[str]
    → missing_logic: list[str]
    → risk_notes: list[str]
```

### Prompt strategy

- **Extraction:** instructed to exclude emotional language, build strict chronological timeline, output valid JSON
- **Strategy:** instructed to cite specific Kenyan statutes (Law of Contract Act Cap 23, Land Act No. 6 of 2012, etc.)
- **Drafting:** instructed to produce formal Kenyan High Court language, output raw markdown (not JSON)
- **QA:** instructed to cross-reference draft against source facts, flag anything not grounded

---

## 7. Integration Guide

### Clerk JWT Auth

Replace the body of `src/api/dependencies.py`:

```python
# Current stub — trusts x-user-id header
async def get_current_user(x_user_id: str = Header(default="dev-user-001")) -> CurrentUser:
    return CurrentUser(user_id=x_user_id)

# After Clerk integration
async def get_current_user(authorization: str = Header(...)) -> CurrentUser:
    token = authorization.removeprefix("Bearer ")
    claims = validate_clerk_jwt(token)  # implement in src/core/security.py
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))
```

`CurrentUser` shape is unchanged — it has `user_id: str` and `email: str | None`. Every route that uses `Depends(get_current_user)` gets real auth instantly once you change this one function.

**Frontend note:** the FSD specifies `Authorization: Bearer <token>` header. Standard `EventSource` doesn't support custom headers, which is why `@microsoft/fetch-event-source` is required for the SSE stream.

**After wiring:** run `uv run pytest tests/` — mock-based tests still pass. Do one live test with a real Clerk token.

---

### ChromaDB RAG Retriever

Replace the body of `src/rag/retriever.py`:

```python
# Current stub
async def rag_retrieve(_query: str) -> list[str]:
    return []

# After ChromaDB integration
async def rag_retrieve(query: str) -> list[str]:
    results = chroma_collection.similarity_search(query, k=5)
    return [doc.page_content for doc in results]
```

The function signature must stay the same: takes a `str`, returns `list[str]`. The orchestrator passes these chunks directly to the strategy agent as context.

**ChromaDB path:** the FSD specifies `./data/vector_db` locally, committed to the repo or on a Render persistent disk for prod.

**After wiring:** run `uv run pytest tests/` — tests mock `rag_retrieve` at the orchestrator level so they still pass. Do one live test and check that `applicable_laws` in the strategy result contains actual statute citations.

---

### Postgres + Alembic

**Step 1 — add `asyncpg` to `backend/pyproject.toml`:**
```toml
"asyncpg>=0.29.0",
```

**Step 2 — set the environment variable (Render / production):**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/litigation
```

No code change needed — `src/core/config.py` reads `DATABASE_URL` automatically.

**Step 3 — set up Alembic migrations:**
```bash
cd backend
uv run alembic init alembic
# edit alembic/env.py to point at src.database.models.Base
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

**Step 4 — add FK constraint on `cases.user_id` → `users.id`** once John's auth is live and the `users` table is being populated. Do this as a new Alembic migration, not a schema change in `models.py`.

**After wiring:** run `uv run pytest tests/` — tests always use their own SQLite regardless of `DATABASE_URL`, so they still pass.

---

### Frontend SSE Integration

**Request:**
```javascript
await fetchEventSource('http://localhost:8000/api/v1/analyze', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${await getToken()}`,  // Clerk token
    },
    body: JSON.stringify({ raw_case_text: inputText }),  // field name is raw_case_text
    onmessage(ev) {
        const data = JSON.parse(ev.data);

        if (data.step === 'done') {
            // pipeline complete — navigate to results
            navigate(`/dashboard/case/${data.case_id}`);
            return;
        }

        if (data.event === 'error') {
            // show error state
            showError(data.detail);
            return;
        }

        // update step status: data.step, data.status ("running" | "completed")
        updateStep(data.step, data.status, data.data);
    }
});
```

**Key field locations:**
| What | Where |
|------|-------|
| Brief markdown | `data.data.brief_markdown` on the `drafting` completed event |
| Risk level | `data.data.risk_level` on the `qa` completed event (`"LOW"`, `"MEDIUM"`, `"HIGH"`) |
| Hallucination warnings | `data.data.hallucination_warnings` on the `qa` completed event (array of strings) |
| Case ID after completion | `data.case_id` on the `done` event |
| History case text | `raw_input` field (not `case_text`) on `/api/v1/cases` response |

**CORS:** if you hit a CORS error, ask Rithwik to add your Vercel URL to `allowed_origins` in `src/core/config.py`, or set the `ALLOWED_ORIGINS` env var on Render.

---

## 8. Environment Variables

All read from `backend/.env`. Copy `backend/.env.example` as a starting point.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (live server) | `""` | OpenAI API key |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./litigation.db` | Sodiq sets this to Postgres for prod |
| `OPENAI_MODEL` | No | `gpt-4o` | Used for strategy + drafting agents |
| `CLERK_JWKS_URL` | No | `""` | John sets this for JWT verification |
| `ALLOWED_ORIGINS` | No | `["http://localhost:3000"]` | Comma-separated frontend URLs for CORS |
| `APP_ENV` | No | `development` | |
