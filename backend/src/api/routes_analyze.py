from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.orchestrator import run_pipeline
from src.api.dependencies import get_current_user
from src.database.session import get_db
from src.schemas.api_schemas import AnalyzeRequest, CurrentUser

router = APIRouter()


@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    return StreamingResponse(
        run_pipeline(request, current_user.user_id, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
