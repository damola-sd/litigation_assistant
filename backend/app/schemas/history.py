from datetime import datetime

from pydantic import BaseModel


class AgentStepOut(BaseModel):
    step_name: str
    step_index: int
    status: str
    result: dict | None

    model_config = {"from_attributes": True}


class HistoryItem(BaseModel):
    id: str
    case_text: str
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class HistoryDetail(HistoryItem):
    steps: list[AgentStepOut]
