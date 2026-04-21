import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.drafting import run_drafting_agent
from src.agents.extraction import run_extraction_agent
from src.agents.qa import run_qa_agent
from src.agents.strategy import run_strategy_agent
from src.database.models import AgentStep, Case
from src.rag.retriever import rag_retrieve
from src.schemas.api_schemas import AnalyzeRequest


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _make_title(text: str) -> str:
    """Auto-generate a short title from the first sentence of the case text."""
    first_sentence = text.split(".")[0].strip()
    return first_sentence[:60] + ("..." if len(first_sentence) > 60 else "")


async def _start_step(db: AsyncSession, case: Case, name: str, index: int) -> AgentStep:
    step = AgentStep(
        id=str(uuid.uuid4()),
        case_id=case.id,
        step_name=name,
        step_index=index,
        status="PROCESSING",
    )
    db.add(step)
    await db.commit()
    return step


async def _finish_step(db: AsyncSession, step: AgentStep, result: dict) -> None:
    step.status = "COMPLETED"
    step.result = result
    await db.commit()


async def run_pipeline(
    request: AnalyzeRequest, user_id: str, db: AsyncSession
) -> AsyncGenerator[str, None]:
    case_id = str(uuid.uuid4())
    case = Case(
        id=case_id,
        user_id=user_id,
        title=_make_title(request.raw_case_text),
        raw_input=request.raw_case_text,
        status="PROCESSING",
    )
    db.add(case)
    await db.commit()

    try:
        # Step 0 — Extraction
        step = await _start_step(db, case, "extraction", 0)
        yield _sse({"step": "extraction", "status": "running", "step_index": 0})
        extraction = await run_extraction_agent(request.raw_case_text)
        await _finish_step(db, step, extraction.model_dump())
        yield _sse({"step": "extraction", "status": "completed", "step_index": 0, "data": extraction.model_dump()})

        # Step 1 — RAG retrieval
        step = await _start_step(db, case, "rag_retrieval", 1)
        yield _sse({"step": "rag_retrieval", "status": "running", "step_index": 1})
        chunks = await rag_retrieve(request.raw_case_text)
        rag_result = {"chunks": chunks}
        await _finish_step(db, step, rag_result)
        yield _sse({"step": "rag_retrieval", "status": "completed", "step_index": 1, "data": rag_result})

        # Step 2 — Strategy
        step = await _start_step(db, case, "strategy", 2)
        yield _sse({"step": "strategy", "status": "running", "step_index": 2})
        strategy = await run_strategy_agent(extraction, chunks)
        await _finish_step(db, step, strategy.model_dump())
        yield _sse({"step": "strategy", "status": "completed", "step_index": 2, "data": strategy.model_dump()})

        # Step 3 — Drafting
        step = await _start_step(db, case, "drafting", 3)
        yield _sse({"step": "drafting", "status": "running", "step_index": 3})
        draft = await run_drafting_agent(extraction, strategy)
        await _finish_step(db, step, draft.model_dump())
        yield _sse({"step": "drafting", "status": "completed", "step_index": 3, "data": draft.model_dump()})

        # Step 4 — QA
        step = await _start_step(db, case, "qa", 4)
        yield _sse({"step": "qa", "status": "running", "step_index": 4})
        qa = await run_qa_agent(extraction, draft)
        await _finish_step(db, step, qa.model_dump())
        yield _sse({"step": "qa", "status": "completed", "step_index": 4, "data": qa.model_dump()})

        case.status = "COMPLETED"
        await db.commit()
        yield _sse({"step": "done", "status": "completed", "case_id": case_id})

    except Exception as exc:
        case.status = "FAILED"
        await db.commit()
        yield _sse({"event": "error", "detail": str(exc)})
