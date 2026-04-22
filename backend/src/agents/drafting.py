import json

from openai import AsyncOpenAI

from src.agents.prompts import DRAFTING_PROMPT
from src.core.config import settings
from src.schemas.ai_schemas import DraftingResult, ExtractionResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def run_drafting_agent(
    extraction: ExtractionResult,
    strategy: StrategyResult,
) -> DraftingResult:
    user_content = (
        f"Core facts:\n{json.dumps(extraction.core_facts, indent=2)}\n\n"
        f"Timeline:\n{json.dumps([t.model_dump() for t in extraction.chronological_timeline], indent=2)}\n\n"
        f"Legal strategy:\n{json.dumps(strategy.model_dump(), indent=2)}"
    )
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": DRAFTING_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    brief_markdown = response.choices[0].message.content or ""
    return DraftingResult(brief_markdown=brief_markdown)


def drafting_agent(state: dict) -> dict:
    import asyncio
    extraction = ExtractionResult(**state["extraction"])
    strategy = StrategyResult(**state["strategy"])
    result = asyncio.get_event_loop().run_until_complete(run_drafting_agent(extraction, strategy))
    state["draft"] = result.model_dump()
    return state
