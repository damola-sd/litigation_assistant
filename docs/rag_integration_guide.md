# Litigation Prep Assistant — RAG Integration Guide

**Branch:** `rag-basic`  
**Audience:** Beginner-friendly. Every code snippet is explained line by line.  
**What this covers:** How the RAG pipeline works, how to run everything locally,
how to test it, and what still needs to be done for production.

---

## Table of Contents

1. [What we built and why](#1-what-we-built-and-why)
2. [Repository layout](#2-repository-layout)
3. [How the agent pipeline works](#3-how-the-agent-pipeline-works)
4. [RAG deep-dive](#4-rag-deep-dive)
5. [How SSE streaming works](#5-how-sse-streaming-works)
6. [Local setup — step by step](#6-local-setup--step-by-step)
7. [Testing guide](#7-testing-guide)
8. [Remaining integration steps](#8-remaining-integration-steps)
9. [Known issues and security notes](#9-known-issues-and-security-notes)

---

## 1. What we built and why

The system transforms raw case text (or a PDF/txt file) into a structured Kenyan
legal brief using four AI agents running sequentially.

```
User types case facts
        │
        ▼
[Extraction Agent]   → pulls out facts, entities, timeline
        │
        ▼
[RAG Retrieval]      → searches Kenyan law database for relevant statutes
        │
        ▼
[Strategy Agent]     → maps facts + statutes → legal arguments
        │
        ▼
[Drafting Agent]     → writes the formal brief in Kenyan High Court style
        │
        ▼
[QA Agent]           → checks the brief for hallucinations or logical gaps
        │
        ▼
Frontend renders each section live as it arrives (Server-Sent Events)
```

**Why SSE (Server-Sent Events) instead of a normal API response?**
Each agent takes 5–15 seconds. With a normal request you'd stare at a spinner
for 60+ seconds. SSE lets the backend push each section to the browser the moment
it is ready, so the user sees results appearing in real time.

---

## 2. Repository layout

```
litigation-prep-assistant/
│
├── backend/                    ← FastAPI service (Python)
│   ├── src/
│   │   ├── main.py             ← app entry point, CORS, routers
│   │   ├── core/
│   │   │   └── config.py       ← reads .env into a settings object
│   │   ├── database/
│   │   │   ├── models.py       ← User, Case, AgentStep ORM tables
│   │   │   └── session.py      ← async SQLAlchemy engine + get_db
│   │   ├── schemas/
│   │   │   ├── ai_schemas.py   ← Pydantic shapes for each agent's output
│   │   │   └── api_schemas.py  ← Pydantic shapes for HTTP requests/responses
│   │   ├── agents/
│   │   │   ├── orchestrator.py ← runs all 5 steps, streams SSE, writes DB
│   │   │   ├── extraction.py   ← Agent 1: fact extraction (gpt-4o-mini)
│   │   │   ├── strategy.py     ← Agent 2: legal strategy (gpt-4o)
│   │   │   ├── drafting.py     ← Agent 3: brief drafting (gpt-4o)
│   │   │   ├── qa.py           ← Agent 4: quality audit (gpt-4o-mini)
│   │   │   ├── format_markdown.py  ← converts agent outputs to Markdown
│   │   │   └── prompts/        ← system prompts for each agent
│   │   ├── api/
│   │   │   ├── dependencies.py ← auth stub (reads x-user-id header)
│   │   │   ├── routes_analyze.py   ← POST /api/v1/analyze
│   │   │   ├── routes_cases.py     ← GET/DELETE /api/v1/cases
│   │   │   └── routes_auth.py      ← GET /api/v1/me
│   │   ├── rag/
│   │   │   ├── vector_store.py ← ChromaDB client + collection setup
│   │   │   ├── ingestion.py    ← chunks + embeds law files → ChromaDB
│   │   │   └── retriever.py    ← rag_retrieve(query) → list[str]
│   │   ├── serializers/
│   │   │   └── cases.py        ← DB queries for history endpoints
│   │   └── services/
│   │       └── case_file_text.py   ← extracts text from uploaded files
│   ├── tests/
│   │   ├── conftest.py         ← fixtures, mock data, shared helpers
│   │   ├── test_analyze.py     ← tests for POST /analyze
│   │   ├── test_history.py     ← tests for case history endpoints
│   │   ├── test_rag.py         ← tests for RAG components + integration
│   │   ├── test_health.py      ← liveness check
│   │   └── test_me.py          ← identity endpoint
│   ├── .env                    ← your secrets (gitignored)
│   ├── .env.example            ← template to copy from
│   └── pyproject.toml          ← Python dependencies
│
├── frontend/                   ← Next.js app (TypeScript)
│   └── src/
│       ├── app/
│       │   ├── dashboard/
│       │   │   ├── new-scan/page.tsx    ← form + live SSE stream
│       │   │   ├── scans/page.tsx       ← history list
│       │   │   └── scans/[id]/page.tsx  ← case detail
│       │   └── ...
│       ├── components/
│       │   └── pipeline-markdown-panel.tsx  ← renders collapsible sections
│       └── lib/
│           └── api.ts           ← all API calls + SSE reader
│
├── data/
│   ├── raw/                    ← Kenyan law .txt/.md files (ingestion reads these)
│   │   ├── contract_act_cap_23.txt
│   │   ├── land_act_2012.txt
│   │   └── employment_act_2007.txt
│   ├── processed/              ← (reserved for cleaned JSONL)
│   ├── test_cases/             ← sample cases for manual testing
│   │   └── john_kamau_v_sarah_wanjiru.txt
│   └── vector_db/              ← ChromaDB index (generated, gitignored)
│
└── infra/
    ├── docker-compose.yml      ← local Postgres (optional)
    ├── Dockerfile.backend      ← Render deployment image
    └── init.sql                ← DB bootstrap
```

---

## 3. How the agent pipeline works

### 3.1 The orchestrator

`backend/src/agents/orchestrator.py` is the brain. It is an **async generator**
— a Python function that uses `yield` to send data back to the caller piece by
piece, instead of all at once.

```python
async def run_pipeline(
    request: AnalyzePipelineInput, user_id: str, db: AsyncSession
) -> AsyncGenerator[str, None]:
```

**What "async generator" means for a beginner:**
Normal functions `return` once. Generator functions can `yield` many times, pausing
between yields. The caller gets each yielded value immediately, without waiting for
the function to finish. FastAPI's `StreamingResponse` wraps this so each yield
becomes one chunk sent to the browser.

Here is the pattern used for every agent step:

```python
# 1. Create a DB row for this step (status = PROCESSING)
step = await _start_step(db, case, "extraction", 0)

# 2. Call the agent — this hits OpenAI and may take 5–15s
extraction = await run_extraction_agent(request.raw_case_text)

# 3. Mark the DB row done and save the result JSON
await _finish_step(db, step, extraction.model_dump())

# 4. Yield a markdown_section SSE event — browser renders it immediately
yield _markdown_section("extraction", "Fact extraction", extraction_to_markdown(extraction))
```

Step 3 happens before step 4, so the result is always in the database even if the
browser disconnects mid-stream.

### 3.2 The agents

Each agent is a single async function that calls OpenAI and returns a typed
Pydantic model.

**Extraction agent** (`agents/extraction.py`):
```python
async def run_extraction_agent(case_text: str) -> ExtractionResult:
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},   # forces strict JSON output
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user",   "content": f"Extract structured information from:\n\n{case_text}"},
        ],
        temperature=0.1,   # low temperature = more deterministic output
    )
    data = json.loads(response.choices[0].message.content)
    return ExtractionResult(**data)   # Pydantic validates the shape
```

`response_format={"type": "json_object"}` tells OpenAI to return only valid JSON,
no prose. Pydantic then validates that the JSON matches `ExtractionResult` — if
a field is missing or the wrong type, you get an error immediately instead of
silently passing bad data to the next agent.

**Why different models for different agents?**

| Agent      | Model       | Why |
|------------|-------------|-----|
| Extraction | gpt-4o-mini | Simple extraction task; cheaper; fast |
| Strategy   | gpt-4o      | Needs legal reasoning ability |
| Drafting   | gpt-4o      | Needs quality prose; complex format |
| QA         | gpt-4o-mini | Pattern matching against source text; cheaper |

### 3.3 Data flow between agents

Each agent receives the outputs of previous agents as context:

```python
extraction = await run_extraction_agent(raw_text)
chunks     = await rag_retrieve(raw_text)            # ← RAG runs here
strategy   = await run_strategy_agent(extraction, chunks)   # gets both
draft      = await run_drafting_agent(extraction, strategy) # gets extraction + strategy
qa         = await run_qa_agent(extraction, draft)          # compares draft vs source facts
```

This is a **sequential state machine** — no agent runs until the previous one
finishes, and each passes its output forward.

### 3.4 Pydantic schemas

`src/schemas/ai_schemas.py` defines the contract for every agent's output:

```python
class ExtractionResult(BaseModel):
    core_facts: list[str]
    entities: list[Entity]
    chronological_timeline: list[TimelineEvent]

class StrategyResult(BaseModel):
    legal_issues: list[str]
    applicable_laws: list[str]
    arguments: list[LegalArgument]
    counterarguments: list[Counterargument]
    legal_reasoning: str

class DraftingResult(BaseModel):
    brief_markdown: str    # the full brief as Markdown

class QAResult(BaseModel):
    risk_level: str        # "LOW", "MEDIUM", or "HIGH"
    hallucination_warnings: list[str]
    missing_logic: list[str]
    risk_notes: list[str]
```

If OpenAI returns JSON that doesn't match these shapes, `Pydantic` raises an error
immediately — you fail loudly instead of silently passing broken data downstream.

---

## 4. RAG deep-dive

RAG = **Retrieval-Augmented Generation**. Instead of relying purely on what the
LLM was trained on, we retrieve relevant text from our own database and inject it
into the prompt. This means the Strategy agent cites real Kenyan statutes instead
of making up plausible-sounding but potentially wrong ones.

### 4.1 Three components

```
data/raw/*.txt   →  ingestion.py  →  data/vector_db/  →  retriever.py  →  orchestrator
(law text files)    (offline script)  (ChromaDB index)    (async fn)       (calls it)
```

### 4.2 Why ChromaDB?

- **SQLite-backed**: no separate database server to run. It's just a folder on disk.
- **Persistent**: commit `data/vector_db/` to the repo or mount it on Render's
  persistent disk — it just works.
- **Stores text alongside embeddings**: when you query it, you get the original
  text chunks back directly, without a separate lookup.
- Alternative FAISS would require manually saving/loading `.index` files and
  maintaining a separate metadata dictionary — more moving parts, same result.

### 4.3 `vector_store.py` — client setup

```python
# src/rag/vector_store.py

COLLECTION_NAME = "kenyan_legal_corpus"
EMBED_MODEL = "text-embedding-3-small"

# Points to data/vector_db/ relative to the repo root.
# __file__ is backend/src/rag/vector_store.py
# parents[3] climbs up 3 levels: rag/ → src/ → backend/ → repo root
DEFAULT_PERSIST_DIR = str(Path(__file__).resolve().parents[3] / "data" / "vector_db")

def get_chroma_client(persist_dir: str = DEFAULT_PERSIST_DIR) -> chromadb.PersistentClient:
    # PersistentClient saves the index to disk automatically
    return chromadb.PersistentClient(path=persist_dir)

def get_collection(client) -> chromadb.Collection:
    # get_or_create: safe to call repeatedly — won't wipe existing data
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity for text
    )
```

### 4.4 `ingestion.py` — building the index

This is an **offline script** you run once (or whenever you add new law files).
It does not run as part of the web server.

```python
# src/rag/ingestion.py

CHUNK_SIZE = 800     # characters per chunk (~200 tokens)
CHUNK_OVERLAP = 100  # characters shared between adjacent chunks

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split a long document into overlapping chunks.

    Why overlap? A sentence that straddles a chunk boundary would otherwise
    be split in half. Overlap ensures every complete thought appears in at
    least one chunk.

    Example with size=10, overlap=3:
      text = "ABCDEFGHIJKLMNO"
      chunk 0: "ABCDEFGHIJ"    (positions 0–9)
      chunk 1: "HIJKLMNOP"     (positions 7–16) ← shares "HIJ" with chunk 0
    """
    if not text.strip():
        return []
    chunks = []
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

def ingest_documents(raw_dir, persist_dir, api_key=None):
    # 1. Find all .txt and .md files in data/raw/
    txt_files = sorted(raw_dir.glob("*.txt")) + sorted(raw_dir.glob("*.md"))

    # 2. Chunk every file
    all_docs, all_ids, all_metadata = [], [], []
    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(text)):
            all_docs.append(chunk)
            all_ids.append(f"{fpath.stem}_{i}_{uuid.uuid4().hex[:6]}")
            all_metadata.append({"source": fpath.name, "chunk_index": i})

    # 3. Embed all chunks with OpenAI text-embedding-3-small
    #    Embedding = a list of 1536 numbers that captures the "meaning" of text.
    #    Similar texts have embeddings that are close together in vector space.
    openai_client = OpenAI(api_key=api_key)
    embeddings = []
    for i in range(0, len(all_docs), 256):   # batch to avoid rate limits
        batch = all_docs[i : i + 256]
        resp = openai_client.embeddings.create(model=EMBED_MODEL, input=batch)
        embeddings.extend(item.embedding for item in resp.data)

    # 4. Store everything in ChromaDB
    collection = get_collection(get_chroma_client(persist_dir))
    collection.add(documents=all_docs, embeddings=embeddings, ids=all_ids, metadatas=all_metadata)
```

**Run this script once to build the index:**
```bash
cd backend
uv run python -m src.rag.ingestion
# → {'detail': 'ok', 'chunks_added': 42}
```

### 4.5 `retriever.py` — querying at runtime

This is called during every analysis. It must be **async** because the web server
is async and we cannot block the event loop.

```python
# src/rag/retriever.py

_openai = AsyncOpenAI(api_key=settings.openai_api_key)

async def rag_retrieve(query: str, n_results: int = 5) -> list[str]:
    # Guard: empty queries return nothing without hitting OpenAI
    if not query.strip():
        return []

    # Step 1: embed the query (async — does not block the server)
    embed_resp = await _openai.embeddings.create(model=EMBED_MODEL, input=query)
    query_embedding = embed_resp.data[0].embedding   # list of 1536 floats

    # Step 2: search ChromaDB for the most similar chunks
    # ChromaDB is a synchronous library, so we run it in a thread pool.
    # asyncio.to_thread() runs a sync function in a separate OS thread so it
    # doesn't freeze the async event loop while the disk is being read.
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
            include=["documents"],   # return the text, not just IDs
        )
        return [doc for doc in result["documents"][0] if doc and doc.strip()]

    return await asyncio.to_thread(_query_chroma)
```

**What `asyncio.to_thread` does:**
The FastAPI server runs an async event loop. If you call a slow synchronous
function directly (like a disk read), it blocks the entire loop and no other
requests can be handled. `asyncio.to_thread` runs the function in a separate
thread, freeing the event loop for other work.

### 4.6 How RAG plugs into the orchestrator

```python
# agents/orchestrator.py (Step 1 — RAG retrieval)

step = await _start_step(db, case, "rag_retrieval", 1)
chunks = await rag_retrieve(request.raw_case_text)   # ← calls retriever.py
rag_result = {"chunks": chunks}
await _finish_step(db, step, rag_result)
yield _markdown_section("rag_retrieval", "Precedent retrieval", rag_chunks_to_markdown(chunks))

# Step 2 — Strategy (receives the chunks)
step = await _start_step(db, case, "strategy", 2)
strategy = await run_strategy_agent(extraction, chunks)   # ← chunks injected here
```

When `chunks` is empty (vector store not built yet), `run_strategy_agent` still
works — the prompt tells the model "No precedents retrieved" and it falls back to
general Kenyan law knowledge.

---

## 5. How SSE streaming works

### 5.1 What SSE is

Server-Sent Events (SSE) is a one-way channel from server to browser. Unlike
WebSockets (two-way), SSE is simpler: the browser opens a connection, and the
server keeps it open and pushes messages whenever it has something to say.

Each message looks like this over the wire:
```
data: {"type":"markdown_section","section_id":"extraction","heading":"Fact extraction","markdown":"### Core facts\n..."}

data: {"type":"complete","case_id":"753fc3cb-..."}

```

(The blank line between messages is mandatory — it tells the browser one message
has ended.)

### 5.2 Backend SSE format

```python
# agents/orchestrator.py

def _sse(payload: dict) -> str:
    # Formats a Python dict as an SSE message string
    return f"data: {json.dumps(payload)}\n\n"

def _markdown_section(section_id: str, heading: str, markdown: str) -> str:
    return _sse({
        "type": "markdown_section",
        "section_id": section_id,   # e.g. "extraction"
        "heading": heading,          # e.g. "Fact extraction"
        "markdown": markdown,        # the rendered Markdown body
    })
```

The full event sequence for a successful run:
```
data: {"type":"markdown_section","section_id":"extraction",    "heading":"Fact extraction",  "markdown":"..."}
data: {"type":"markdown_section","section_id":"rag_retrieval", "heading":"Precedent retrieval","markdown":"..."}
data: {"type":"markdown_section","section_id":"strategy",      "heading":"Legal strategy",   "markdown":"..."}
data: {"type":"markdown_section","section_id":"drafting",      "heading":"Draft brief",      "markdown":"..."}
data: {"type":"markdown_section","section_id":"qa",            "heading":"Quality review",   "markdown":"..."}
data: {"type":"complete","case_id":"753fc3cb-..."}
```

On error:
```
data: {"type":"error","detail":"OpenAI rate limit exceeded"}
```

### 5.3 Frontend SSE reader

`frontend/src/lib/api.ts` reads the stream using the browser's native `fetch` API:

```typescript
// lib/api.ts

export async function postAnalyzeStream(input, userId, signal, onSseData, onError) {
    // Build multipart form — server expects form fields, not JSON
    const fd = new FormData();
    fd.append("title", input.title.trim());
    fd.append("case_text", input.caseText);
    if (input.file) fd.append("case_file", input.file);

    const res = await fetch(`${apiBaseUrl}/api/v1/analyze`, {
        method: "POST",
        signal,             // AbortSignal — lets the Stop button work
        headers: { "X-User-Id": userId },
        body: fd,
    });

    // Get a ReadableStream from the response body
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (value) buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by double newlines (\n\n)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";   // keep the incomplete last part in buffer

        for (const block of parts) {
            // Each block starts with "data: "
            const line = block.trim();
            if (line.startsWith("data:")) {
                const payload = JSON.parse(line.slice(5).trim());
                onSseData(payload);   // → updates React state
            }
        }
        if (done) break;
    }
}
```

### 5.4 Frontend state management

`frontend/src/app/dashboard/new-scan/page.tsx`:

```typescript
// Each markdown_section event adds/updates an entry in this array
const [sections, setSections] = useState<MarkdownSection[]>([]);

function handleStreamPayload(payload) {
    if (payload.type === "markdown_section") {
        setSections(prev => {
            // Find by section_id — update if exists, append if new
            const idx = prev.findIndex(s => s.section_id === payload.section_id);
            const row = { section_id: payload.section_id, heading: payload.heading,
                          markdown: payload.markdown };
            if (idx >= 0) {
                const next = [...prev];
                next[idx] = row;
                return next;
            }
            return [...prev, row];
        });
    }
    if (payload.type === "error") setError(payload.detail);
    // "complete" event is not handled here — navigation would go here
}
```

`PipelineMarkdownPanel` renders each section as a collapsible accordion using
`<details>` + `<summary>`, with `ReactMarkdown` rendering the markdown body.

---

## 6. Local setup — step by step

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | python.org |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ LTS | nodejs.org |
| npm | bundled with Node | — |

### Step 1 — Clone and configure environment

```bash
git clone <repo-url>
cd litigation-prep-assistant
```

**Backend `.env`** — copy the example and fill in your OpenAI key:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```
OPENAI_API_KEY=sk-...         ← your key from platform.openai.com
OPENAI_MODEL=gpt-4o           ← leave as-is
DATABASE_URL=sqlite+aiosqlite:///./litigation.db   ← leave as-is for local dev
ALLOWED_ORIGINS=["http://localhost:3000"]          ← leave as-is
```

**Frontend `.env.local`** — create from the example:
```bash
cp frontend/.env.example frontend/.env.local
```

Edit `frontend/.env.local`:
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...   ← from John / Clerk dashboard
CLERK_SECRET_KEY=sk_test_...                    ← from John / Clerk dashboard
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000       ← leave as-is
```

### Step 2 — Install backend dependencies

```bash
cd backend
uv sync
```

`uv sync` reads `pyproject.toml`, creates a `.venv/`, and installs all packages
including the new `chromadb` dependency.

### Step 3 — Run the test suite (no API key needed)

```bash
cd backend
uv run pytest tests/ -v
```

All 133 tests should pass in under 3 seconds. Every agent, database call, and RAG
component is mocked — no network, no OpenAI, no cost.

**If tests pass: your environment is configured correctly.**
**If tests fail: stop here and fix the error before proceeding.**

### Step 4 — Build the RAG vector store

This calls OpenAI embeddings once (~50 chunks × fractions of a cent = < $0.01)
and writes the ChromaDB index to `data/vector_db/`.

```bash
cd backend
uv run python -m src.rag.ingestion
# Expected output: {'detail': 'ok', 'chunks_added': 42}
```

You only need to run this once, or whenever you add new law files to `data/raw/`.

If you skip this step, the pipeline still works — the RAG step will return empty
chunks and the Strategy agent will use general knowledge instead of retrieved statutes.

### Step 5 — Delete the old SQLite database (if it exists)

If you've run the server before, the old `litigation.db` file may have an outdated
schema. Delete it — the server recreates it automatically on next start.

```bash
rm -f backend/litigation.db
```

### Step 6 — Start the backend server

Open a terminal and keep it running:

```bash
cd backend
uv run dev
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 7 — Verify the backend with curl

Open a second terminal and run these in order:

```bash
# 1. Liveness check
curl http://localhost:8000/health
# → {"status":"ok"}

# 2. Identity endpoint
curl http://localhost:8000/api/v1/me -H "x-user-id: alice"
# → {"user_id":"alice","email":null}

# 3. Full pipeline (streams live; takes 30-60s with real OpenAI calls)
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "x-user-id: alice" \
  -F "title=John Kamau v Sarah Wanjiru" \
  -F "case_text=On 15 March 2023, John Kamau signed a land sale agreement with Sarah Wanjiru for KES 5,000,000. He paid a deposit and took possession. Sarah now refuses to execute transfer documents."
# → streams 5 markdown_section events then {"type":"complete","case_id":"..."}

# 4. View history
curl http://localhost:8000/api/v1/cases -H "x-user-id: alice"
# → [{"id":"...","title":"John Kamau v Sarah Wanjiru",...}]
```

**Alternatively**, visit the interactive Swagger UI at `http://127.0.0.1:8000/docs`
and run requests from your browser.

You can also upload the included test file:
```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "x-user-id: alice" \
  -F "title=John Kamau v Sarah Wanjiru" \
  -F "case_file=@../data/test_cases/john_kamau_v_sarah_wanjiru.txt"
```

### Step 8 — Start the frontend

Open a third terminal:

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

Visit `http://localhost:3000`, sign in with Clerk, then go to **Dashboard → New Scan**.

The backend must be running (Step 6) before you submit a scan. "Failed to fetch"
means the backend is not running or is on a different port than `NEXT_PUBLIC_API_URL`.

---

## 7. Testing guide

### 7.1 What is being tested

The project has 133 automated tests split across five files:

| File | Tests | What it covers |
|------|-------|----------------|
| `test_health.py` | 3 | `/health` liveness endpoint |
| `test_me.py` | 5 | `/me` identity endpoint |
| `test_analyze.py` | 35 | Full SSE pipeline — input validation, event shapes, error handling, per-step content, DB persistence |
| `test_history.py` | 21 | History endpoints — user isolation, ordering, search, delete |
| `test_rag.py` | 69 | `chunk_text`, `rag_retrieve`, `ingest_documents`, + integration (RAG chunks flow to strategy agent) |

### 7.2 How mocking works

Tests should not call real APIs or write to a production database. We use Python's
`unittest.mock` library to replace real functions with fake ones that return
pre-defined values instantly.

**Two levels of mocking in this project:**

**1. Database:** each test gets a fresh temporary SQLite file via `tmp_path`.

```python
# conftest.py (simplified)
@pytest_asyncio.fixture
async def client(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url)
    # ... create tables ...
    fastapi_app.dependency_overrides[get_db] = override_with_test_db
    yield AsyncClient(app=fastapi_app, base_url="http://test")
```

`dependency_overrides` is a FastAPI feature that replaces `get_db` with a function
that returns the test database. Every test that uses the `client` fixture gets its
own isolated, empty database.

**2. AI agents:** all four agents and RAG are patched at the orchestrator level.

```python
# conftest.py (simplified)
@pytest.fixture
def mock_agents():
    with patch("src.agents.orchestrator.run_extraction_agent") as m_ext, \
         patch("src.agents.orchestrator.run_strategy_agent")  as m_strat, \
         patch("src.agents.orchestrator.rag_retrieve")        as m_rag:
        m_ext.return_value = MOCK_EXTRACTION   # pre-built ExtractionResult
        m_strat.return_value = MOCK_STRATEGY
        yield {"extraction": m_ext, "strategy": m_strat, ...}
```

Why patch at `src.agents.orchestrator.run_extraction_agent` and not at
`src.agents.extraction.run_extraction_agent`? Because Python binds names at
import time. The orchestrator imports `run_extraction_agent` once. Patching the
name inside `orchestrator` replaces the binding the orchestrator actually uses.

**3. RAG tests:** ChromaDB and OpenAI are mocked separately.

```python
# test_rag.py example
async def test_rag_retrieve_returns_list_of_strings():
    col = MagicMock()
    col.count.return_value = 3
    col.query.return_value = {"documents": [["Chunk A.", "Chunk B.", "Chunk C."]]}

    with patch("src.rag.retriever._openai") as mock_openai, \
         patch("src.rag.retriever.get_collection", return_value=col):
        mock_openai.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1]*1536)])
        )
        result = await rag_retrieve("contract dispute")

    assert result == ["Chunk A.", "Chunk B.", "Chunk C."]
```

`MagicMock` creates an object that accepts any attribute access or method call.
`AsyncMock` is the same but returns an awaitable — needed for `async/await`.

### 7.3 Running specific tests

```bash
cd backend

# Run everything
uv run pytest tests/ -v

# Run only RAG tests
uv run pytest tests/test_rag.py -v

# Run one specific test by name
uv run pytest tests/test_rag.py::test_strategy_receives_rag_chunks_as_second_argument -v

# Stop on first failure
uv run pytest tests/ -x

# Show print statements during test run
uv run pytest tests/ -s
```

### 7.4 Manual end-to-end test with the test case file

Once the backend is running:

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "x-user-id: test-user" \
  -F "title=John Kamau v Sarah Wanjiru" \
  -F "case_file=@../data/test_cases/john_kamau_v_sarah_wanjiru.txt"
```

What to check in the output:

1. **rag_retrieval section** should say "Retrieved excerpts" (if ingestion was run)
   or "No precedents were retrieved" (if skipped) — not an error.
2. **strategy section** should reference "Law of Contract Act" or "Land Act" in
   the applicable laws list.
3. **drafting section** should contain `## FACTS`, `## ISSUES FOR DETERMINATION`,
   `## LEGAL ARGUMENTS`, `## CONCLUSION AND PRAYER FOR RELIEF`.
4. **qa section** should show a `risk_level` of LOW, MEDIUM, or HIGH.
5. **Final event** should be `{"type":"complete","case_id":"<uuid>"}`.

---

## 8. Remaining integration steps

### 8.1 Backend Clerk JWT verification (security — pre-production)

**Current state:** The backend reads `x-user-id` from the HTTP header and trusts
it blindly. The frontend sends the real Clerk user ID there, so the system works
correctly. However, anyone who knows the API URL could send any user ID in that
header and read another user's data — there is no signature check.

**What needs to change:** Replace the body of `src/api/dependencies.py`:

```python
# CURRENT (stub — trusts header blindly)
async def get_current_user(x_user_id: str = Header(default="dev-user-001")) -> CurrentUser:
    return CurrentUser(user_id=x_user_id)

# TARGET (validates Clerk JWT signature)
async def get_current_user(authorization: str = Header(...)) -> CurrentUser:
    token = authorization.removeprefix("Bearer ")
    claims = await validate_clerk_jwt(token)   # implement in src/core/security.py
    return CurrentUser(user_id=claims["sub"], email=claims.get("email"))
```

`validate_clerk_jwt` fetches Clerk's public keys from `CLERK_JWKS_URL` and uses
them to verify that the token was actually signed by your Clerk instance — not just
any string someone typed.

**Backend `.env` values needed (from John's Clerk dashboard):**
```
CLERK_JWKS_URL=https://your-instance.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://your-instance.clerk.accounts.dev
```

**Frontend change needed:** The frontend currently sends `X-User-Id: <clerk_id>`.
After backend JWT is wired, it needs to send `Authorization: Bearer <jwt_token>`:

```typescript
// lib/api.ts — after Clerk JWT is wired
import { useAuth } from "@clerk/nextjs";
const { getToken } = useAuth();
const token = await getToken();

headers: { "Authorization": `Bearer ${token}` }
```

**No other files change.** Every route that uses `Depends(get_current_user)` gets
real auth automatically. All existing tests continue to pass because they use the
`x-user-id` header via dependency overrides.

**Who does this:** John (frontend token change) + whoever implements `validate_clerk_jwt`
in `src/core/security.py`.

### 8.2 Postgres + Alembic migrations (pre-production)

**Current state:** The backend uses SQLite locally. SQLite is a single file — no
server needed, great for development, not suitable for production (no concurrent
writes, no hosted service).

**What needs to change (Sodiq's task):**

**Step 1 — Add asyncpg to dependencies:**
```toml
# pyproject.toml
"asyncpg>=0.29.0",
```

**Step 2 — Set DATABASE_URL in production:**
```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/litigation
```

No code change is needed — `src/core/config.py` reads `DATABASE_URL` automatically.

**Step 3 — Set up Alembic for migrations:**
```bash
cd backend
uv run alembic init alembic
# Edit alembic/env.py to point at src.database.models.Base
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

Without Alembic, the only way to change the schema is to drop and recreate the
database — which destroys all data. Alembic tracks schema changes as numbered
migration files and applies them incrementally.

**Step 4 — Add FK constraint on cases.user_id → users.id:**
Once Clerk JWT auth is live and the `users` table is being populated, add this
as a new Alembic migration (not a direct change to `models.py`).

### 8.3 Real Kenyan legal corpus

**Current state:** `data/raw/` contains three short placeholder files covering
the Law of Contract Act, Land Act, and Employment Act. The RAG pipeline works
correctly end-to-end but the retrieved chunks are placeholder text, not real
statute language.

**What needs to change:**

1. Add real Kenyan statute and case law files to `data/raw/`:
   - Download from [Kenya Law](https://www.kenyalaw.org) (eKLR)
   - Preferred formats: `.txt` or `.md`
   - Suggested sources: Law of Contract Act Cap 23, Land Act No. 6 of 2012,
     Employment Act No. 11 of 2007, Civil Procedure Act Cap 21,
     selected High Court judgments

2. Re-run ingestion:
   ```bash
   cd backend
   uv run python -m src.rag.ingestion
   ```

3. For production on Render — two options:
   - **Option A:** Commit `data/vector_db/` to the repo. Ingestion runs locally,
     index is in version control, Render reads it at startup. Simple, works well
     for a corpus that rarely changes.
   - **Option B:** Mount a Render persistent disk, run ingestion as part of the
     deploy script. More complex but keeps the repo smaller.

**No code changes needed.** The ingestion and retrieval code is already complete.

### 8.4 Deployment

**Backend on Render:**
```
Build command: pip install -r requirements.txt
Start command: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Environment variables to set in Render dashboard:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://...
CLERK_JWKS_URL=https://...
ALLOWED_ORIGINS=["https://your-app.vercel.app"]
```

**Frontend on Vercel:**
- Root directory: `frontend/`
- Environment variables: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`,
  `NEXT_PUBLIC_API_URL=https://your-render-api-url`

**CORS:** When the Vercel URL is known, add it to `ALLOWED_ORIGINS` in the Render
environment variables. The backend reads this at startup.

---

## 9. Known issues and security notes

### 9.1 Auth is not production-secure (see §8.1)

The `x-user-id` header approach works correctly for the demo but is not safe for
a real deployment. Any user who can reach the API can impersonate any other user
by changing the header. Clerk JWT verification must be implemented before going
to production.

**Impact:** Low for the demo (Clerk still protects the frontend routes). High for
production.

### 9.2 RAG uses placeholder data (see §8.3)

The Strategy agent currently retrieves from a small placeholder corpus. Real Kenyan
statute text will significantly improve the quality of legal citations. This is a
data task, not a code task — the retrieval logic is complete.

### 9.3 No rate limiting on `/analyze`

Each request to `/analyze` triggers 4–5 OpenAI API calls costing approximately
$0.05–$0.20 per analysis depending on case length. Without rate limiting, a single
user could run many analyses quickly. For the demo this is fine; for production,
consider Clerk's billing tier to gate usage (already in the schema — `users.tier`
column exists).

### 9.4 SQLite is not safe for concurrent writes

If two users submit analyses at the exact same moment in local dev, SQLite may
produce a "database is locked" error. This is fine for single-person development
and demos. Postgres (§8.2) handles concurrent writes correctly.

---

## Quick reference

```bash
# Run tests (fast, no API key)
cd backend && uv run pytest tests/ -v

# Build vector store (once, requires OPENAI_API_KEY)
cd backend && uv run python -m src.rag.ingestion

# Start backend
cd backend && uv run dev

# Start frontend
cd frontend && npm run dev

# Curl full pipeline test
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "x-user-id: test" \
  -F "title=Test Matter" \
  -F "case_file=@../data/test_cases/john_kamau_v_sarah_wanjiru.txt"
```
