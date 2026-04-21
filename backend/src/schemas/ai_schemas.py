from pydantic import BaseModel


class FinalBrief(BaseModel):
    case_summary: str
    legal_issues: list[str]
    arguments_for_client: list[str]
    risks: list[str]
    recommendations: list[str]
