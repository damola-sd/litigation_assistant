from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    case_text: str


class AgentStep(BaseModel):
    agent: str
    status: str
    data: dict | None = None
