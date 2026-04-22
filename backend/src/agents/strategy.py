import json

from openai import AsyncOpenAI

from src.agents.prompts import STRATEGY_PROMPT
from src.core.config import settings
from src.schemas.ai_schemas import ExtractionResult, LegalArgument, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def run_strategy_agent(
    extraction: ExtractionResult, rag_context: list[str]
) -> StrategyResult:
    context_block = "\n".join(rag_context) if rag_context else "No precedents retrieved."
    user_content = (
        f"Core facts:\n{json.dumps(extraction.core_facts, indent=2)}\n\n"
        f"Timeline:\n{json.dumps([t.model_dump() for t in extraction.chronological_timeline], indent=2)}\n\n"
        f"Entities:\n{json.dumps([e.model_dump() for e in extraction.entities], indent=2)}\n\n"
        f"Relevant Kenyan precedents:\n{context_block}"
    )
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": STRATEGY_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return StrategyResult(**data)


def strategy_agent(state: dict) -> dict:
    import asyncio
    extraction = ExtractionResult(**state["extraction"])
    result = asyncio.get_event_loop().run_until_complete(run_strategy_agent(extraction, []))
    state["strategy"] = result.model_dump()
    return state
