import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.analyze import DraftingResult, ExtractionResult, QAResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a legal QA auditor reviewing AI-generated briefs for accuracy and grounding.
Be conservative — flag anything that is unverified, speculative, or potentially hallucinated.
Respond ONLY with valid JSON — no prose, no markdown fences."""

_USER = """Audit the legal brief below against the original source material.

Original case text:
{case_text}

Extracted facts:
{extraction_json}

Legal strategy:
{strategy_json}

Draft brief:
{draft_json}

Check for:
1. Is the brief grounded in the stated facts?
2. Are cited Kenyan laws real and correctly applied?
3. Are there logical gaps or unsupported leaps?
4. Any risk of hallucinated case law or statutes?

Respond with JSON matching this exact shape:
{{
  "is_grounded":        true,
  "risk_level":         "low|medium|high",
  "risk_notes":         ["note 1"],
  "missing_logic":      ["gap 1"],
  "hallucination_flags": ["flag 1"]
}}"""


async def run_qa_agent(
    case_text: str,
    extraction: ExtractionResult,
    strategy: StrategyResult,
    draft: DraftingResult,
) -> QAResult:
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": _USER.format(
                    case_text=case_text,
                    extraction_json=extraction.model_dump_json(indent=2),
                    strategy_json=strategy.model_dump_json(indent=2),
                    draft_json=draft.model_dump_json(indent=2),
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    data = json.loads(response.choices[0].message.content)
    return QAResult(**data)
