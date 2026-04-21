from fastapi import APIRouter

router = APIRouter()


@router.post("/analyze")
def analyze() -> dict[str, str]:
    # TODO: case_text, optional files, agent pipeline
    return {"detail": "not_implemented"}
