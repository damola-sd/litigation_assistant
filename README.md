# Litigation Prep Assistant

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Clerk](https://img.shields.io/badge/Clerk-Auth%20%26%20Billing-6C47FF?logo=clerk&logoColor=white)](https://clerk.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Store-E85D04?logo=databricks&logoColor=white)](https://www.trychroma.com)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?logo=vercel&logoColor=white)](https://vercel.com)
[![Render](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render&logoColor=white)](https://render.com)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=astral&logoColor=white)](https://docs.astral.sh/uv/)

> **AI-powered litigation preparation for Kenyan law firms and paralegals.**

Litigation Prep Assistant is a multi-agent AI system that transforms raw case input - text descriptions or uploaded PDFs - into a structured legal brief. Four sequential agents (Extraction → Strategy → Drafting → QA) process the case and stream their outputs step-by-step to the UI in real time via Server-Sent Events (SSE), giving lawyers and paralegals an interactive, auditable view of the AI's reasoning.

---

## Architecture

```mermaid
flowchart TB
    classDef frontend fill:#000000,stroke:#333,stroke-width:2px,color:#fff
    classDef backend fill:#026e3f,stroke:#333,stroke-width:2px,color:#fff
    classDef external fill:#f39c12,stroke:#333,stroke-width:2px,color:#fff
    classDef database fill:#2980b9,stroke:#333,stroke-width:2px,color:#fff
    classDef agent fill:#8e44ad,stroke:#333,stroke-width:2px,color:#fff
    classDef rag fill:#c0392b,stroke:#333,stroke-width:2px,color:#fff

    subgraph Client_Tier [Client & UI Tier]
        U((User / Lawyer))
        FE[Next.js App Router<br>Vercel]:::frontend
    end

    subgraph External_Services[Identity & Billing]
        Clerk[Clerk Auth & Billing UI]:::external
    end

    subgraph Backend_Tier [Backend Application Tier - FastAPI on Render]
        API_GW[FastAPI REST / API Router]:::backend
        Auth_MW[Clerk JWT Middleware]:::backend
        SSE[SSE Streamer<br>Step-by-step updates]:::backend

        API_GW --> Auth_MW
        Auth_MW --> SSE
    end

    subgraph AI_Pipeline[AI Multi-Agent Orchestration]
        Orchestrator[State Graph / Orchestrator]:::agent
        A1[1. Extraction Agent<br>Facts, Entities, Timeline]:::agent
        A2[2. Strategy Agent<br>Legal Mapping]:::agent
        A3[3. Drafting Agent<br>Structured Brief]:::agent
        A4[4. QA Agent<br>Risk & Hallucination Check]:::agent

        Orchestrator --> A1
        A1 --> A2
        A2 --> A3
        A3 --> A4
        A4 --> Orchestrator
    end

    subgraph Data_Tier[Data & RAG Storage]
        DB[(PostgreSQL<br>Users, Cases, History)]:::database
        VD[(ChromaDB / FAISS<br>Vector Store)]:::database
        RAG_Retriever[RAG Retrieval Layer<br>Kenyan Law Context]:::rag
    end

    subgraph LLM_Tier [External Intelligence]
        LLM[External LLM APIs<br>OpenAI / Anthropic]:::external
    end

    U -->|Uploads PDF / Enters Text| FE
    FE <-->|Authenticates / Paywall| Clerk
    FE -->|POST /analyze| API_GW
    FE -.->|Listens to SSE stream| SSE

    API_GW <-->|Reads/Writes| DB
    Auth_MW <-->|Validates JWT| Clerk
    API_GW -->|Triggers| Orchestrator
    Orchestrator -.->|Yields Status| SSE

    A2 <-->|Queries for precedents| RAG_Retriever
    RAG_Retriever <-->|Fetches Embeddings| VD

    A1 & A2 & A3 & A4 <-->|Prompts & Completions| LLM
```

The backend orchestrates four agents sequentially. As each agent completes, the FastAPI `StreamingResponse` yields a `markdown_section` SSE event containing the rendered Markdown for that step. A final `complete` event carrying the `case_id` signals the end of the stream. The Next.js frontend consumes the stream and renders each section live -- no polling, no page reloads.

---

## Agent Roles

| Agent | Responsibility |
|-------|---------------|
| **Extraction Agent** | Pulls facts, named entities, and a chronological timeline from the raw case input |
| **Strategy Agent** | Maps extracted facts to applicable Kenyan statutes and legal arguments via RAG retrieval |
| **Drafting Agent** | Produces a structured legal brief: Facts, Issues, Arguments, Counterarguments, Conclusion |
| **QA Agent** | Validates grounding, flags logical gaps, and assigns a hallucination-risk score |

---

## Features

- **Workflow automation** - not a chatbot; a deterministic agent pipeline with a clear start and end
- **Structured output** - every agent emits a typed Pydantic schema, not freeform text
- **Real-time step viewer** - SSE stream lets the UI render each agent's output as it completes
- **Kenyan law RAG** - Strategy Agent retrieves relevant statutes and case-law excerpts before reasoning
- **Auth & billing** - Clerk handles sign-in, route protection, and subscription gating
- **History** - every analysis is stored in Postgres and retrievable from the dashboard
- **Monorepo** - frontend, backend, and infra live in one repo with clean domain boundaries

---

## Repository Layout

```
litigation-prep-assistant/
│
├── .github/workflows/          # CI checks (frontend build, backend lint)
│
├── frontend/                   # Next.js App Router (John)
│   └── src/
│       ├── app/
│       │   ├── (public)/       # / landing, /pricing, /login
│       │   └── (dashboard)/    # /dashboard, /dashboard/new, /dashboard/case/[id]
│       ├── components/
│       │   ├── ui/             # shadcn/ui primitives
│       │   ├── forms/          # CaseInputForm
│       │   ├── dashboard/      # HistoryTable, FileUploader
│       │   └── agents/         # AgentStepViewer (SSE consumer), ResultPanel
│       ├── lib/                # API clients, Clerk helpers, custom hooks
│       └── types/              # TypeScript interfaces (Case, AgentStep, FinalBrief)
│
├── backend/                    # FastAPI app (Rithwik, Damola, Amit)
│   └── src/
│       ├── api/                # Route handlers + Clerk JWT dependency
│       │   ├── dependencies.py
│       │   ├── routes_auth.py       # GET /me
│       │   ├── routes_cases.py      # GET /history, GET /history/{id}
│       │   └── routes_analyze.py    # POST /analyze → SSE StreamingResponse
│       ├── core/               # Config (pydantic-settings), security helpers
│       ├── database/           # SQLAlchemy session + User/Case/Result models
│       ├── agents/             # Orchestrator + four agent modules + prompts/
│       ├── rag/                # Ingestion, retriever, vector store wrapper
│       └── schemas/            # API + AI Pydantic schemas
│
├── data/                       # Legal corpus (Amit)
│   ├── raw/                    # Kenyan statutes, case-law PDFs/TXT
│   ├── processed/              # Cleaned JSONL chunks
│   └── vector_db/              # Local FAISS/Chroma index (git-ignored)
│
├── infra/                      # Local dev infrastructure (Sodiq)
│   ├── docker-compose.yml      # Postgres + optional vector DB
│   ├── Dockerfile.backend      # Container image for Render
│   └── init.sql                # Database bootstrap
│
└── README.md
```

---

## Prerequisites

| Layer | Requirement |
|-------|-------------|
| Backend | Python 3.11+ and [uv](https://docs.astral.sh/uv/) (recommended) |
| Frontend | Node.js 20+ LTS and npm |
| Local DB | Docker + Docker Compose (for Postgres) |
| Auth | A [Clerk](https://clerk.com) application (free tier sufficient) |
| LLM | An OpenAI or Anthropic API key |

---

## Quick Start

### 1. Clone and configure environment variables

```bash
git clone https://github.com/<your-org>/litigation-prep-assistant.git
cd litigation-prep-assistant
```

Copy the example env files and fill in your keys:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

**`backend/.env` (minimum required):**

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/litigation_prep
CLERK_JWKS_URL=https://<your-clerk-domain>/.well-known/jwks.json
OPENAI_API_KEY=sk-...
```

**`frontend/.env.local` (minimum required):**

```dotenv
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 2. Start the local database

```bash
cd infra
docker compose up -d
```

Postgres will be available at `localhost:5432` with the default credentials above.

### 3. Run the API

```bash
cd backend
uv sync
uv run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API docs: `http://127.0.0.1:8000/docs`

### 4. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:3000`

### 5. Build the RAG vector store (first time only)

```bash
cd backend
uv run python -m src.rag.ingestion
```

Re-run whenever you add documents to `data/raw/`.

---

## Testing

### Backend

The backend test suite uses `pytest` with async support. All agents, the LLM, and the database are mocked — tests run instantly with zero API cost.

```bash
cd backend
uv run pytest             # run all tests
uv run pytest -v          # verbose — show each test name
uv run pytest -x          # stop on first failure
uv run pytest --tb=short  # concise failure tracebacks
```

**Test coverage:**

| File | What it covers |
|------|---------------|
| `tests/test_health.py` | `GET /health` liveness check |
| `tests/test_me.py` | `GET /api/v1/me` user identity endpoint |
| `tests/test_analyze.py` | `POST /api/v1/analyze` -- SSE pipeline, input validation, section ordering, error handling, `DELETE /api/v1/cases/{id}` |
| `tests/test_history.py` | `GET /api/v1/cases` + `GET /api/v1/cases/{id}` -- history listing, user isolation, step detail retrieval |
| `tests/test_schemas.py` | AI Pydantic schema unit tests -- model validation and serialization |

Run with coverage:

```bash
uv run pytest tests/ --cov=src --cov-report=term-missing
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | - | System health check |
| `GET` | `/api/v1/me` | Clerk JWT | Returns authenticated user profile |
| `POST` | `/api/v1/analyze` | Clerk JWT | Multipart form (`title`, `case_text`, optional `case_file`); returns SSE stream |
| `GET` | `/api/v1/cases` | Clerk JWT | Lists all past analyses for the user (optional `?q=` title filter) |
| `GET` | `/api/v1/cases/{id}` | Clerk JWT | Returns full case result and agent steps |
| `DELETE` | `/api/v1/cases/{id}` | Clerk JWT | Deletes a case and its agent steps |

### SSE stream format (`POST /api/v1/analyze`)

Each line has the form `data: <json>\n\n`. Three event types are emitted:

```json
{ "type": "markdown_section", "section_id": "extraction",   "heading": "Fact extraction",    "markdown": "..." }
{ "type": "markdown_section", "section_id": "rag_retrieval","heading": "Precedent retrieval", "markdown": "..." }
{ "type": "markdown_section", "section_id": "strategy",     "heading": "Legal strategy",      "markdown": "..." }
{ "type": "markdown_section", "section_id": "drafting",     "heading": "Draft brief",         "markdown": "..." }
{ "type": "markdown_section", "section_id": "qa",           "heading": "Quality review",      "markdown": "..." }
{ "type": "complete", "case_id": "<uuid>" }
{ "type": "error",    "detail": "<message>" }
```

### Evaluations (live API calls, incurs cost)

Two offline eval scripts are provided in `backend/evals/`:

```bash
# Schema regression against 3 golden Kenyan cases (uses real OpenAI API)
uv run python -m evals.eval_extraction

# LLM-as-judge scoring of the full pipeline (GPT-4o scores completeness, grounding, actionability)
uv run python -m evals.eval_llm_judge
uv run python -m evals.eval_llm_judge --threshold 3.5   # stricter pass threshold
```

---

## Deployment

| Service | Platform | Notes |
|---------|----------|-------|
| Frontend | [Vercel](https://vercel.com) | Set project root to `frontend/`; `vercel.json` preset included |
| Backend | [Render](https://render.com) | Use `infra/Dockerfile.backend`; set all env vars in Render dashboard |
| Database | Render Postgres / any managed PG | Point `DATABASE_URL` at your instance |
| Vector store | Packed into Docker image or managed Chroma | See `data/vector_db/` - add to `.dockerignore` carefully |

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Frontend framework | Next.js 16 (App Router) |
| UI components | shadcn/ui + Tailwind CSS |
| Auth & billing | Clerk |
| Backend framework | FastAPI |
| Agent orchestration | Custom async pipeline with tenacity retries |
| LLM gateway | OpenAI API |
| Structured output | Pydantic + instructor (JSON mode) |
| Logging | structlog (JSON in production, console in dev) |
| RAG vector store | Stub -- ChromaDB integration planned |
| Relational database | PostgreSQL / SQLite (SQLAlchemy async) |
| Real-time streaming | Server-Sent Events (SSE) |
| Package manager (BE) | uv |
| CI/CD | GitHub Actions (pytest + ruff + mypy + build) |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| SSE over REST polling | FastAPI's `StreamingResponse` can yield each step result as it completes, giving the UI a live feed without a long-polling loop |
| Sequential async pipeline over multi-agent framework | Four agents with a fixed causal order do not need a routing framework; a plain async generator is easier to trace, test, and extend |
| instructor (JSON mode) for structured output | Automatic schema injection into the prompt and transparent retry on malformed JSON; removes manual `json.loads` + exception handling from every agent |
| tenacity retry on OpenAI calls | Transient rate-limit and connection errors are retried with exponential backoff rather than surfaced to the user immediately |
| QA step treated as non-critical | A failed QA step must not discard an otherwise complete brief; the pipeline emits a `complete` event regardless, skipping the QA section |
| structlog for logging | Newline-delimited JSON output in production is ingestible by any log aggregator without format negotiation |
| Clerk for auth and billing | Handles JWT validation, subscription plans, and route protection; JWKS validation is implemented server-side with a 5-minute cache |

---

## Team Contributions

| Name | Role |
|------|------|
| **Rithwik** | FastAPI backend architecture, agent orchestration, AI integration |
| **John** | Next.js frontend (App Router), Clerk integration (auth + billing UI) |
| **Amit** | RAG pipeline, legal dataset ingestion + embeddings |
| **Damola** | Agent design (prompts + reasoning flow), QA agent logic |
| **Sodiq** | Deployment (Vercel + Render), database setup, logging + monitoring |

---

## Documentation

- [backend/README.md](./backend/README.md) - Python layout, dependencies, and API stubs
- [frontend/README.md](./frontend/README.md) - Next.js scripts, routing, and environment variables
