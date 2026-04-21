import json

from openai import AsyncOpenAI

from src.core.config import settings
from src.schemas.ai_schemas import ExtractionResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a Kenyan paralegal. Extract structured information from the case description.
Return valid JSON matching this exact schema:
{
  "core_facts": ["list of key factual statements — no emotions, only legally relevant facts"],
  "entities": [{"name": "...", "type": "person|company|place|document", "role": "..."}],
  "chronological_timeline": [{"date": "...", "event": "..."}]
}
Exclude emotional language. Build a strict chronological timeline. Be precise and comprehensive."""


async def run_extraction_agent(case_text: str) -> ExtractionResult:
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
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
    result = asyncio.get_event_loop().run_until_complete(run_extraction_agent(state["raw_text"]))
    state["extraction"] = result.model_dump()
    return state
