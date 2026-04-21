import json
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import AgentStep, Case
from app.schemas.analyze import AnalyzeRequest, DraftingResult, ExtractionResult, QAResult, StrategyResult
from app.services.agents.drafting import run_drafting_agent
from app.services.agents.extraction import run_extraction_agent
from app.services.agents.qa import run_qa_agent
from app.services.agents.strategy import run_strategy_agent
from app.services.rag import rag_retrieve


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _start_step(db: AsyncSession, case_id: str, name: str, index: int) -> AgentStep:
    step = AgentStep(case_id=case_id, step_name=name, step_index=index)
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def _finish_step(db: AsyncSession, step: AgentStep, result: dict) -> None:
    step.status = "done"
    step.result = result
    step.completed_at = datetime.utcnow()
    await db.commit()


async def run_pipeline(
    request: AnalyzeRequest,
    user_id: str,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Sequential agent pipeline streamed as SSE events.

    Each step emits two events:
      {"step": "<name>", "status": "running", "step_index": N}
      {"step": "<name>", "status": "done",    "step_index": N, "result": {...}}

    Final event:
      {"event": "complete", "analysis_id": "<uuid>"}

    On any failure:
      {"event": "error", "detail": "<message>"}
    """
    case = Case(user_id=user_id, case_text=request.case_text, status="running")
    db.add(case)
    await db.commit()
    await db.refresh(case)

    extraction: ExtractionResult | None = None
    rag_context: list[str] = []
    strategy: StrategyResult | None = None
    draft: DraftingResult | None = None
    qa: QAResult | None = None

    try:
        # ── 0 · Extraction ──────────────────────────────────────────────────
        step = await _start_step(db, case.id, "extraction", 0)
        yield _sse({"step": "extraction", "status": "running", "step_index": 0})

        extraction = await run_extraction_agent(request.case_text)
        await _finish_step(db, step, extraction.model_dump())
        yield _sse({"step": "extraction", "status": "done", "step_index": 0, "result": extraction.model_dump()})

        # ── 1 · RAG Retrieval ────────────────────────────────────────────────
        step = await _start_step(db, case.id, "rag_retrieval", 1)
        yield _sse({"step": "rag_retrieval", "status": "running", "step_index": 1})

        rag_context = await rag_retrieve(request.case_text)
        await _finish_step(db, step, {"chunks": rag_context})
        yield _sse({"step": "rag_retrieval", "status": "done", "step_index": 1, "result": {"chunks": rag_context}})

        # ── 2 · Strategy ─────────────────────────────────────────────────────
        step = await _start_step(db, case.id, "strategy", 2)
        yield _sse({"step": "strategy", "status": "running", "step_index": 2})

        strategy = await run_strategy_agent(extraction, rag_context)
        await _finish_step(db, step, strategy.model_dump())
        yield _sse({"step": "strategy", "status": "done", "step_index": 2, "result": strategy.model_dump()})

        # ── 3 · Drafting ─────────────────────────────────────────────────────
        step = await _start_step(db, case.id, "drafting", 3)
        yield _sse({"step": "drafting", "status": "running", "step_index": 3})

        draft = await run_drafting_agent(extraction, strategy)
        await _finish_step(db, step, draft.model_dump())
        yield _sse({"step": "drafting", "status": "done", "step_index": 3, "result": draft.model_dump()})

        # ── 4 · QA ───────────────────────────────────────────────────────────
        step = await _start_step(db, case.id, "qa", 4)
        yield _sse({"step": "qa", "status": "running", "step_index": 4})

        qa = await run_qa_agent(request.case_text, extraction, strategy, draft)
        await _finish_step(db, step, qa.model_dump())
        yield _sse({"step": "qa", "status": "done", "step_index": 4, "result": qa.model_dump()})

        # ── Complete ─────────────────────────────────────────────────────────
        case.status = "completed"
        case.completed_at = datetime.utcnow()
        await db.commit()
        yield _sse({"event": "complete", "analysis_id": case.id})

    except Exception as exc:
        case.status = "failed"
        await db.commit()
        yield _sse({"event": "error", "detail": str(exc)})
