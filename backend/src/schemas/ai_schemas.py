from pydantic import BaseModel


class Entity(BaseModel):
    name: str
    type: str
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
    risk_level: str
    risk_notes: list[str]
    missing_logic: list[str]
    hallucination_flags: list[str]


class FinalBrief(BaseModel):
    case_summary: str
    legal_issues: list[str]
    arguments_for_client: list[str]
    risks: list[str]
    recommendations: list[str]
