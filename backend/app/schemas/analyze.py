from pydantic import BaseModel, field_validator


class AnalyzeRequest(BaseModel):
    case_text: str

    @field_validator("case_text")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_text must not be blank")
        return v.strip()


# --- Per-agent structured outputs ---

class Entity(BaseModel):
    name: str
    type: str   # person | org | place
    role: str


class TimelineEvent(BaseModel):
    date: str
    event: str


class ExtractionResult(BaseModel):
    facts: list[str]
    entities: list[Entity]
    timeline: list[TimelineEvent]


class StrategyResult(BaseModel):
    legal_issues: list[str]
    applicable_laws: list[str]
    arguments: list[str]
    counterarguments: list[str]
    legal_reasoning: str


class Brief(BaseModel):
    facts: str
    issues: list[str]
    arguments: list[str]
    counterarguments: list[str]
    conclusion: str


class DraftingResult(BaseModel):
    brief: Brief


class QAResult(BaseModel):
    is_grounded: bool
    risk_level: str          # low | medium | high
    risk_notes: list[str]
    missing_logic: list[str]
    hallucination_flags: list[str]


# --- SSE event payloads ---

class StepEvent(BaseModel):
    step: str
    status: str              # running | done | failed
    step_index: int
    result: dict | None = None
