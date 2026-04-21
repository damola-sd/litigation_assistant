from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_me() -> dict[str, str]:
    # TODO: resolve user from Clerk JWT
    return {"detail": "not_implemented"}
