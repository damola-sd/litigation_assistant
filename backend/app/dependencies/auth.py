from fastapi import Header
from pydantic import BaseModel


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None


async def get_current_user(
    x_user_id: str = Header(default="dev-user-001", alias="x-user-id"),
) -> CurrentUser:
    """
    Stub auth dependency. Reads user identity from the X-User-Id header.
    John will replace this with full Clerk JWT validation once auth is wired.
    """
    return CurrentUser(user_id=x_user_id)
