from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_history() -> dict[str, str]:
    # TODO: paginated analyses for current user
    return {"detail": "not_implemented"}


@router.get("/{analysis_id}")
def get_history_item(analysis_id: str) -> dict[str, str]:
    # TODO: full case result + agent steps
    return {"detail": "not_implemented", "analysis_id": analysis_id}
