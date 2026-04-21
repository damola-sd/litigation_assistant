"""
Shared fixtures, mock data, and helpers for all test modules.

Architecture:
- Each test gets a fresh per-test SQLite file (via tmp_path) — no shared state.
- `get_db` is overridden so routes hit the test DB, not production.
- `init_db` is patched so the lifespan doesn't touch the production DB.
- All 4 agents + RAG are patched at the orchestrator level so tests run
  instantly with zero API cost. Individual tests can override side_effect
  on specific mocks to simulate failures.
"""

import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Import models first so they register with Base.metadata before any test creates tables.
# This must come before `from app.main import app` to avoid the `app` name being rebound.
import app.models.case as _models_case  # noqa: F401

from app.main import app as fastapi_app
from app.models.database import Base, get_db
from app.schemas.analyze import (
    Brief,
    DraftingResult,
    Entity,
    ExtractionResult,
    QAResult,
    StrategyResult,
    TimelineEvent,
)

# ── Canonical mock outputs (stand-ins for real LLM responses) ─────────────────
# These define the shape teammates can expect from each agent.

MOCK_EXTRACTION = ExtractionResult(
    facts=[
        "John Kamau signed a written land sale agreement with Sarah Wanjiru on 15 March 2023",
        "The agreed price was KES 5,000,000 for parcel No. 123/456 in Kiambu County",
        "John paid a deposit of KES 500,000 and was given possession",
        "Sarah refuses to execute transfer documents and claims the agreement is void",
    ],
    entities=[
        Entity(name="John Kamau", type="person", role="buyer"),
        Entity(name="Sarah Wanjiru", type="person", role="seller"),
        Entity(name="Kiambu County", type="place", role="jurisdiction"),
    ],
    timeline=[
        TimelineEvent(date="15 March 2023", event="Written sale agreement signed"),
        TimelineEvent(date="15 March 2023", event="Deposit of KES 500,000 paid; possession granted"),
        TimelineEvent(date="after 15 March 2023", event="Sarah refuses to execute transfer documents"),
    ],
)

MOCK_STRATEGY = StrategyResult(
    legal_issues=[
        "Validity of the written land sale contract",
        "Entitlement to specific performance",
        "Claim for damages for breach of contract",
    ],
    applicable_laws=[
        "Law of Contract Act, Cap 23 — Section 3(3)",
        "Land Act, No. 6 of 2012 — Section 38",
        "Civil Procedure Act, Cap 21",
    ],
    arguments=[
        "The written contract satisfies Section 3(3) of the Law of Contract Act",
        "Part performance (deposit + possession) entitles John to specific performance",
        "Sarah's refusal constitutes a repudiatory breach entitling John to damages",
    ],
    counterarguments=[
        "Sarah may claim the contract is void for lack of essential terms",
        "Sarah may argue the deposit was conditional and possession was temporary",
    ],
    legal_reasoning=(
        "The contract is valid under Kenyan law. John's part performance strengthens "
        "his claim for specific performance under the Land Act."
    ),
)

MOCK_DRAFT = DraftingResult(
    brief=Brief(
        facts=(
            "On 15 March 2023, John Kamau entered into a written agreement with Sarah Wanjiru "
            "for the purchase of land parcel No. 123/456 in Kiambu County at KES 5,000,000. "
            "John paid a deposit of KES 500,000 and was given possession. Sarah subsequently "
            "refused to execute the transfer documents, alleging the agreement is void."
        ),
        issues=[
            "Whether the written agreement constitutes a valid and enforceable contract",
            "Whether John Kamau is entitled to an order of specific performance",
            "Whether John Kamau is entitled to damages for breach of contract",
        ],
        arguments=[
            "The agreement is in writing and signed by both parties, satisfying Section 3(3) "
            "of the Law of Contract Act, Cap 23",
            "John Kamau's payment of the deposit and taking of possession constitutes "
            "part performance, entitling him to specific performance under Section 38 of the Land Act",
        ],
        counterarguments=[
            "Sarah Wanjiru may allege lack of essential terms renders the contract void",
            "Sarah Wanjiru may contend that equitable defences preclude specific performance",
        ],
        conclusion=(
            "The Honourable Court should grant an order of specific performance compelling "
            "Sarah Wanjiru to execute the transfer documents, together with general damages "
            "for the period of delay and costs of the suit."
        ),
    )
)

MOCK_QA = QAResult(
    is_grounded=True,
    risk_level="low",
    risk_notes=[],
    missing_logic=[],
    hallucination_flags=[],
)

# ── Shared test constants ─────────────────────────────────────────────────────

SAMPLE_CASE = (
    "On 15 March 2023, John Kamau entered into a written agreement with Sarah Wanjiru "
    "for the sale of land parcel No. 123/456 in Kiambu County for KES 5,000,000. "
    "John paid a deposit of KES 500,000 and was given possession of the land. "
    "Sarah has since refused to execute the transfer documents, claiming the agreement is void. "
    "John now seeks specific performance and damages."
)

USER_A = "user-alice-001"
USER_B = "user-bob-002"
HEADERS_A = {"x-user-id": USER_A}
HEADERS_B = {"x-user-id": USER_B}

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(tmp_path) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx AsyncClient backed by a fresh per-test SQLite file DB.
    - get_db dependency is overridden to use the test engine.
    - init_db is patched to a no-op so the lifespan doesn't hit production.
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url)

    # Models are already registered via the module-level import above.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override_get_db

    with patch("app.main.init_db", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as ac:
            yield ac

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def mock_agents():
    """
    Patches all 4 agents and rag_retrieve at the orchestrator import level.

    Tests that simulate a specific agent failing can do:
        mock_agents["extraction"].side_effect = RuntimeError("boom")
    """
    with (
        patch(
            "app.services.orchestrator.run_extraction_agent",
            new_callable=AsyncMock,
        ) as m_ext,
        patch(
            "app.services.orchestrator.run_strategy_agent",
            new_callable=AsyncMock,
        ) as m_strat,
        patch(
            "app.services.orchestrator.run_drafting_agent",
            new_callable=AsyncMock,
        ) as m_draft,
        patch(
            "app.services.orchestrator.run_qa_agent",
            new_callable=AsyncMock,
        ) as m_qa,
        patch(
            "app.services.orchestrator.rag_retrieve",
            new_callable=AsyncMock,
        ) as m_rag,
    ):
        m_ext.return_value = MOCK_EXTRACTION
        m_strat.return_value = MOCK_STRATEGY
        m_draft.return_value = MOCK_DRAFT
        m_qa.return_value = MOCK_QA
        m_rag.return_value = []
        yield {
            "extraction": m_ext,
            "strategy": m_strat,
            "drafting": m_draft,
            "qa": m_qa,
            "rag": m_rag,
        }


# ── Helper ────────────────────────────────────────────────────────────────────


async def collect_sse(response) -> list[dict]:
    """Read an SSE response stream and return all data: payloads as dicts."""
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    return events


async def run_analyze(client: AsyncClient, headers: dict = HEADERS_A) -> str:
    """Run the full pipeline and return the analysis_id from the complete event."""
    async with client.stream(
        "POST",
        "/analyze",
        json={"case_text": SAMPLE_CASE},
        headers=headers,
    ) as resp:
        events = await collect_sse(resp)
    return events[-1]["analysis_id"]
