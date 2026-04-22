import json

from openai import AsyncOpenAI

from src.agents.prompts import EXTRACTION_PROMPT
from src.core.config import settings
from src.schemas.ai_schemas import ExtractionResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)


async def run_extraction_agent(case_text: str) -> ExtractionResult:
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
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
