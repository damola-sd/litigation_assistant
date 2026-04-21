import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.drafting import run_drafting_agent
from src.agents.extraction import run_extraction_agent
from src.agents.qa import run_qa_agent
from src.agents.strategy import run_strategy_agent
from src.database.models import AgentStep, Case
from src.database.session import AsyncSessionLocal
from src.rag.retriever import rag_retrieve
from src.schemas.api_schemas import AnalyzeRequest


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _start_step(db: AsyncSession, case: Case, name: str, index: int) -> AgentStep:
    step = AgentStep(
        id=str(uuid.uuid4()),
        case_id=case.id,
        step_name=name,
        step_index=index,
        status="running",
    )
    db.add(step)
    await db.commit()
    return step


async def _finish_step(db: AsyncSession, step: AgentStep, result: dict) -> None:
    step.status = "done"
    step.result = result
    await db.commit()


async def run_pipeline(
    request: AnalyzeRequest, user_id: str, db: AsyncSession
) -> AsyncGenerator[str, None]:
    case_id = str(uuid.uuid4())
    case = Case(id=case_id, user_id=user_id, case_text=request.case_text, status="running")
    db.add(case)
    await db.commit()

    try:
        # Step 0 — Extraction
        step = await _start_step(db, case, "extraction", 0)
        yield _sse({"step": "extraction", "status": "running", "step_index": 0})
        extraction = await run_extraction_agent(request.case_text)
        await _finish_step(db, step, extraction.model_dump())
        yield _sse({"step": "extraction", "status": "done", "step_index": 0, "result": extraction.model_dump()})

        # Step 1 — RAG retrieval
        step = await _start_step(db, case, "rag_retrieval", 1)
        yield _sse({"step": "rag_retrieval", "status": "running", "step_index": 1})
        chunks = await rag_retrieve(request.case_text)
        rag_result = {"chunks": chunks}
        await _finish_step(db, step, rag_result)
        yield _sse({"step": "rag_retrieval", "status": "done", "step_index": 1, "result": rag_result})

        # Step 2 — Strategy
        step = await _start_step(db, case, "strategy", 2)
        yield _sse({"step": "strategy", "status": "running", "step_index": 2})
        strategy = await run_strategy_agent(extraction, chunks)
        await _finish_step(db, step, strategy.model_dump())
        yield _sse({"step": "strategy", "status": "done", "step_index": 2, "result": strategy.model_dump()})

        # Step 3 — Drafting
        step = await _start_step(db, case, "drafting", 3)
        yield _sse({"step": "drafting", "status": "running", "step_index": 3})
        draft = await run_drafting_agent(extraction, strategy)
        await _finish_step(db, step, draft.model_dump())
        yield _sse({"step": "drafting", "status": "done", "step_index": 3, "result": draft.model_dump()})

        # Step 4 — QA
        step = await _start_step(db, case, "qa", 4)
        yield _sse({"step": "qa", "status": "running", "step_index": 4})
        qa = await run_qa_agent(extraction, draft)
        await _finish_step(db, step, qa.model_dump())
        yield _sse({"step": "qa", "status": "done", "step_index": 4, "result": qa.model_dump()})

        case.status = "completed"
        await db.commit()
        yield _sse({"event": "complete", "analysis_id": case_id})

    except Exception as exc:
        case.status = "failed"
        await db.commit()
        yield _sse({"event": "error", "detail": str(exc)})
