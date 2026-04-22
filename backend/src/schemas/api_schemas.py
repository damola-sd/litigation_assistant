from datetime import datetime

from pydantic import BaseModel, field_validator


class AnalyzeRequest(BaseModel):
    raw_case_text: str

    @field_validator("raw_case_text")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_case_text must not be blank")
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
    raw_input: str
    status: str
    created_at: datetime


class HistoryDetail(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    raw_input: str
    status: str
    created_at: datetime
    steps: list[AgentStepOut]


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
