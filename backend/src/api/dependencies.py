from fastapi import Depends, HTTPException, status


def require_user() -> dict[str, str]:
    """
    Placeholder for Clerk JWT validation dependency.
    """
    # TODO: validate bearer token and resolve Clerk user ID.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Auth dependency not implemented",
    )


def get_current_user(user: dict[str, str] = Depends(require_user)) -> dict[str, str]:
    return user
