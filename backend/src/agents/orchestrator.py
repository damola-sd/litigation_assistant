from collections.abc import Generator

from src.agents.drafting import drafting_agent
from src.agents.extraction import extraction_agent
from src.agents.qa import qa_agent
from src.agents.strategy import strategy_agent


def run_agents(case_text: str) -> Generator[dict, None, dict]:
    state: dict = {"case_text": case_text}

    for name, fn in (
        ("Extraction", extraction_agent),
        ("Strategy", strategy_agent),
        ("Drafting", drafting_agent),
        ("QA", qa_agent),
    ):
        state = fn(state)
        yield {"agent": name, "status": "completed"}

    return state
