import json

from openai import AsyncOpenAI

from src.core.config import settings
from src.schemas.ai_schemas import ExtractionResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a senior Kenyan litigation attorney. Analyze the extracted case facts and develop
a comprehensive legal strategy under Kenyan law.
Return valid JSON matching this exact schema:
{
  "legal_issues": ["list of legal issues raised"],
  "applicable_laws": ["Act name and specific section"],
  "arguments": ["arguments in favour of the client"],
  "counterarguments": ["likely opposing arguments"],
  "legal_reasoning": "narrative explanation of the legal position"
}
Cite specific Kenyan statutes and case law where applicable."""


async def run_strategy_agent(
    extraction: ExtractionResult, rag_context: list[str]
) -> StrategyResult:
    context_block = "\n".join(rag_context) if rag_context else "No precedents retrieved."
    user_content = (
        f"Case facts:\n{json.dumps(extraction.model_dump(), indent=2)}\n\n"
        f"Relevant precedents:\n{context_block}"
    )
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return StrategyResult(**data)


def strategy_agent(state: dict) -> dict:
    import asyncio
    from src.schemas.ai_schemas import ExtractionResult as ER
    extraction = ER(**state["extraction"])
    result = asyncio.get_event_loop().run_until_complete(run_strategy_agent(extraction, []))
    state["strategy"] = result.model_dump()
    return state
