# Litigation Prep Assistant

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
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

The backend orchestrates four agents sequentially. As each agent completes, the FastAPI `StreamingResponse` yields a JSON payload (e.g. `{"agent": "Extraction", "status": "completed", "data": ...}`) over SSE. The Next.js frontend consumes the stream via an `EventSource` hook and renders each step live - no polling, no page reloads.

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
| `tests/test_me.py` | `GET /me` user identity endpoint |
| `tests/test_analyze.py` | `POST /analyze` — full SSE pipeline, input validation, per-agent output shapes, error handling |
| `tests/test_history.py` | `GET /cases` + `GET /cases/{id}` — history, user isolation, detail retrieval |
| `tests/test_schemas.py` | AI Pydantic schema unit tests — model validation and serialisation |

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | - | System health check |
| `GET` | `/me` | Clerk JWT | Returns authenticated user profile |
| `POST` | `/analyze` | Clerk JWT | Runs agent pipeline; returns SSE stream |
| `GET` | `/history` | Clerk JWT | Lists all past analyses for the user |
| `GET` | `/history/{id}` | Clerk JWT | Returns full case result and agent steps |

### SSE stream format (`POST /analyze`)

Each event is a JSON object yielded as each agent finishes:

```json
{ "agent": "Extraction", "status": "completed", "data": { ... } }
{ "agent": "Strategy",   "status": "completed", "data": { ... } }
{ "agent": "Drafting",   "status": "completed", "data": { ... } }
{ "agent": "QA",         "status": "completed", "data": { ... } }
{ "agent": "pipeline",   "status": "done",      "data": { "case_id": "..." } }
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
| Frontend framework | Next.js 15 (App Router) |
| UI components | shadcn/ui + Tailwind CSS |
| Auth & billing | Clerk |
| Backend framework | FastAPI |
| Agent orchestration | LangGraph / Python state machine |
| LLM gateway | OpenAI / Anthropic APIs |
| Structured output | Pydantic + Instructor |
| RAG vector store | ChromaDB / FAISS |
| Relational database | PostgreSQL (SQLAlchemy) |
| Real-time streaming | Server-Sent Events (SSE) |
| Package manager (BE) | uv |
| CI/CD | GitHub Actions → Vercel + Render |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| SSE over REST polling | Vercel Serverless Functions have strict timeouts; SSE lets FastAPI yield each agent result as it completes without holding a single long-lived HTTP connection |
| Sequential state machine over CrewAI | Four agents with a fixed order don't need a complex framework; a simple dict-based state passed from agent to agent is easier to debug and demo |
| Pydantic + Instructor for structured output | Eliminates unpredictable freeform text from the Drafting Agent; every brief section maps to a typed field |
| Kenyan law RAG before Strategy Agent | Grounds legal arguments in real statutes and precedents before the model reasons, reducing hallucination risk |
| ChromaDB / FAISS over managed vector DB | Keeps local dev free and fast; the index is packed into the Docker image for Render so it survives ephemeral disk wipes |
| Clerk for auth and billing | Handles JWT validation, subscription plans, and route protection without custom auth code |

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
