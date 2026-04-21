import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.analyze import ExtractionResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a legal case extraction specialist.
Extract structured information from raw case facts.
Respond ONLY with valid JSON — no prose, no markdown fences."""

_USER = """Extract the following from this case:
1. facts     — list of key factual statements
2. entities  — people, organisations, places with their type and role
3. timeline  — chronological events with approximate dates

Case text:
{case_text}

Respond with JSON matching this exact shape:
{{
  "facts": ["..."],
  "entities": [{{"name": "...", "type": "person|org|place", "role": "..."}}],
  "timeline": [{{"date": "...", "event": "..."}}]
}}"""


async def run_extraction_agent(case_text: str) -> ExtractionResult:
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _USER.format(case_text=case_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    data = json.loads(response.choices[0].message.content)
    return ExtractionResult(**data)
