import json

from openai import AsyncOpenAI

from src.agents.prompts import QA_PROMPT
from src.core.config import settings
from src.schemas.ai_schemas import DraftingResult, ExtractionResult, QAResult

_client = AsyncOpenAI(api_key=settings.openai_api_key)


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
            {"role": "system", "content": QA_PROMPT},
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
