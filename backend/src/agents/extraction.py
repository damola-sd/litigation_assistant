import json

from openai import AsyncOpenAI

from src.core.config import settings
from src.schemas.ai_schemas import ExtractionResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a Kenyan legal analyst. Extract structured information from the case description.
Return valid JSON matching this exact schema:
{
  "facts": ["list of key factual statements"],
  "entities": [{"name": "...", "type": "person|company|place|document", "role": "..."}],
  "timeline": [{"date": "...", "event": "..."}]
}
Be precise and comprehensive. Include all legally relevant facts."""


async def run_extraction_agent(case_text: str) -> ExtractionResult:
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Extract structured information from this case:\n\n{case_text}"},
        ],
        temperature=0.1,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return ExtractionResult(**data)


def extraction_agent(state: dict) -> dict:
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(run_extraction_agent(state["case_text"]))
    state["extraction"] = result.model_dump()
    return state
