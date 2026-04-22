from fastapi import Header

from src.schemas.api_schemas import CurrentUser


async def get_current_user(x_user_id: str = Header(default="dev-user-001")) -> CurrentUser:
    return CurrentUser(user_id=x_user_id)
