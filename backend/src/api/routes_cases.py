from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_current_user
from src.database.models import Case
from src.database.session import get_db
from src.schemas.api_schemas import CurrentUser, HistoryDetail, HistoryItem

router = APIRouter()


@router.get("", response_model=list[HistoryItem])
async def list_history(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Case]:
    result = await db.execute(
        select(Case)
        .where(Case.user_id == current_user.user_id)
        .order_by(Case.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{analysis_id}", response_model=HistoryDetail)
async def get_history_item(
    analysis_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Case:
    result = await db.execute(
        select(Case)
        .where(Case.id == analysis_id, Case.user_id == current_user.user_id)
        .options(selectinload(Case.steps))
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return case
