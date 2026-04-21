import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.schemas.analyze import ExtractionResult, StrategyResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a senior Kenyan advocate specialising in litigation strategy.
Analyse cases strictly within Kenyan jurisdiction — cite Kenyan statutes, case law, and legal doctrine.
Respond ONLY with valid JSON — no prose, no markdown fences."""

_USER = """Analyse the extracted case information and relevant legal context below.
Identify the legal issues, map them to applicable Kenyan law, and build a balanced argument strategy.

Extracted case data:
{extraction_json}

Relevant Kenya Law context (RAG retrieval):
{rag_context}

Respond with JSON matching this exact shape:
{{
  "legal_issues": ["..."],
  "applicable_laws": ["Kenyan statute or case citation"],
  "arguments":        ["argument in favour of the client"],
  "counterarguments": ["likely opposing argument"],
  "legal_reasoning":  "narrative reasoning tying it together"
}}"""


async def run_strategy_agent(
    extraction: ExtractionResult,
    rag_context: list[str],
) -> StrategyResult:
    rag_text = "\n---\n".join(rag_context) if rag_context else "No documents retrieved."

    response = await _client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": _USER.format(
                    extraction_json=extraction.model_dump_json(indent=2),
                    rag_context=rag_text,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    data = json.loads(response.choices[0].message.content)
    return StrategyResult(**data)
