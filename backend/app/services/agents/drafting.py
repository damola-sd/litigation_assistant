import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.analyze import DraftingResult, ExtractionResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a senior Kenyan advocate drafting formal legal briefs for court submission.
Write in precise, formal legal language appropriate for Kenyan courts.
Respond ONLY with valid JSON — no prose, no markdown fences."""

_USER = """Draft a structured legal brief from the case analysis below.

Extracted facts:
{extraction_json}

Legal strategy:
{strategy_json}

Respond with JSON matching this exact shape:
{{
  "brief": {{
    "facts":            "narrative summary of the material facts",
    "issues":           ["legal issue 1", "legal issue 2"],
    "arguments":        ["argument 1 with legal basis", "argument 2"],
    "counterarguments": ["anticipated counter 1", "anticipated counter 2"],
    "conclusion":       "proposed conclusion and remedy sought"
  }}
}}"""


async def run_drafting_agent(
    extraction: ExtractionResult,
    strategy: StrategyResult,
) -> DraftingResult:
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": _USER.format(
                    extraction_json=extraction.model_dump_json(indent=2),
                    strategy_json=strategy.model_dump_json(indent=2),
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    data = json.loads(response.choices[0].message.content)
    return DraftingResult(**data)
