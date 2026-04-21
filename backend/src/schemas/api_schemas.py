from datetime import datetime

from pydantic import BaseModel, field_validator

from src.schemas.ai_schemas import (
    DraftingResult,
    ExtractionResult,
    QAResult,
    StrategyResult,
)


class AnalyzeRequest(BaseModel):
    case_text: str

    @field_validator("case_text")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_text must not be blank")
        return v.strip()


class AgentStepOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    step_name: str
    step_index: int
    status: str
    result: dict | None


class HistoryItem(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    case_text: str
    status: str
    created_at: datetime


class HistoryDetail(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    case_text: str
    status: str
    created_at: datetime
    steps: list[AgentStepOut]


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
