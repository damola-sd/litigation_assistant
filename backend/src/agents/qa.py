import json

from openai import AsyncOpenAI

from src.core.config import settings
from src.schemas.ai_schemas import DraftingResult, ExtractionResult, QAResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)

_SYSTEM = """You are a legal QA auditor. Review the drafted brief against the original facts.
Identify any hallucinations (claims in the draft not supported by the source facts) or logical gaps.
Return valid JSON matching this exact schema:
{
  "risk_level": "LOW|MEDIUM|HIGH",
  "hallucination_warnings": ["any claims not supported by the source facts"],
  "missing_logic": ["logical gaps in the brief's arguments"],
  "risk_notes": ["general risk observations"]
}
Be rigorous — this brief may be filed in court."""


async def run_qa_agent(
    extraction: ExtractionResult,
    draft: DraftingResult,
) -> QAResult:
    user_content = (
        f"Source facts:\n{json.dumps(extraction.core_facts, indent=2)}\n\n"
        f"Draft brief (markdown):\n{draft.brief_markdown}"
    )
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
    )
    data = json.loads(response.choices[0].message.content or "{}")
    return QAResult(**data)


def qa_agent(state: dict) -> dict:
    import asyncio
    extraction = ExtractionResult(**state["extraction"])
    draft = DraftingResult(**state["draft"])
    result = asyncio.get_event_loop().run_until_complete(run_qa_agent(extraction, draft))
    state["qa"] = result.model_dump()
    return state
