import json
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.drafting import run_drafting_agent
from src.agents.extraction import run_extraction_agent
from src.agents.format_markdown import (
    drafting_to_markdown,
    extraction_to_markdown,
    qa_to_markdown,
    rag_chunks_to_markdown,
    strategy_to_markdown,
)
from src.agents.qa import run_qa_agent
from src.agents.strategy import run_strategy_agent
from src.database.models import AgentStep, Case
from src.rag.retriever import rag_retrieve
from src.schemas.api_schemas import AnalyzePipelineInput


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _markdown_section(section_id: str, heading: str, markdown: str) -> str:
    return _sse(
        {
            "type": "markdown_section",
            "section_id": section_id,
            "heading": heading,
            "markdown": markdown,
        }
    )


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
    request: AnalyzePipelineInput, user_id: str, db: AsyncSession
) -> AsyncGenerator[str, None]:
    case_id = str(uuid.uuid4())
    case = Case(
        id=case_id,
        user_id=user_id,
        title=request.title[:255],
        raw_input=request.raw_case_text,
        status="PROCESSING",
    )
    db.add(case)
    await db.commit()

    try:
        # Step 0 — Extraction
        step = await _start_step(db, case, "extraction", 0)
        extraction = await run_extraction_agent(request.raw_case_text)
        await _finish_step(db, step, extraction.model_dump())
        yield _markdown_section(
            "extraction",
            "Fact extraction",
            extraction_to_markdown(extraction),
        )

        # Step 1 — RAG retrieval
        step = await _start_step(db, case, "rag_retrieval", 1)
        chunks = await rag_retrieve(request.raw_case_text)
        rag_result = {"chunks": chunks}
        await _finish_step(db, step, rag_result)
        yield _markdown_section(
            "rag_retrieval",
            "Precedent retrieval",
            rag_chunks_to_markdown(chunks),
        )

        # Step 2 — Strategy
        step = await _start_step(db, case, "strategy", 2)
        strategy = await run_strategy_agent(extraction, chunks)
        await _finish_step(db, step, strategy.model_dump())
        yield _markdown_section(
            "strategy",
            "Legal strategy",
            strategy_to_markdown(strategy),
        )

        # Step 3 — Drafting
        step = await _start_step(db, case, "drafting", 3)
        draft = await run_drafting_agent(extraction, strategy)
        await _finish_step(db, step, draft.model_dump())
        yield _markdown_section(
            "drafting",
            "Draft brief",
            drafting_to_markdown(draft),
        )

        # Step 4 — QA
        step = await _start_step(db, case, "qa", 4)
        qa = await run_qa_agent(extraction, draft)
        await _finish_step(db, step, qa.model_dump())
        yield _markdown_section(
            "qa",
            "Quality review",
            qa_to_markdown(qa),
        )

        case.status = "COMPLETED"
        await db.commit()
        yield _sse({"type": "complete", "case_id": case_id})

    except Exception as exc:
        case.status = "FAILED"
        await db.commit()
        yield _sse({"type": "error", "detail": str(exc)})
