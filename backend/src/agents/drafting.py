import json

from openai import AsyncOpenAI

from src.core.config import settings
from src.schemas.ai_schemas import DraftingResult, ExtractionResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a Kenyan court drafting expert. Using the provided facts and legal strategy,
draft a formal litigation brief suitable for filing in a Kenyan court.
Return valid JSON matching this exact schema:
{
  "brief": {
    "facts": "narrative statement of facts",
    "issues": ["legal issues for determination"],
    "arguments": ["arguments supporting client's case with legal citations"],
    "counterarguments": ["anticipated opposing arguments"],
    "conclusion": "prayer / orders sought"
  }
}
Use formal court language appropriate for Kenyan High Court proceedings."""


async def run_drafting_agent(
    extraction: ExtractionResult,
    strategy: StrategyResult,
) -> DraftingResult:
    user_content = (
        f"Extracted facts:\n{json.dumps(extraction.model_dump(), indent=2)}\n\n"
        f"Legal strategy:\n{json.dumps(strategy.model_dump(), indent=2)}"
    )
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return DraftingResult(**data)


def drafting_agent(state: dict) -> dict:
    import asyncio
    from src.schemas.ai_schemas import ExtractionResult as ER, StrategyResult as SR
    extraction = ER(**state["extraction"])
    strategy = SR(**state["strategy"])
    result = asyncio.get_event_loop().run_until_complete(run_drafting_agent(extraction, strategy))
    state["draft"] = result.model_dump()
    return state
