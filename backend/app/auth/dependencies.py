"""Who is calling, and may they call this endpoint at all?

`get_current_user` answers the first question from the bearer token; `require_roles`
answers the coarse half of the second. Per-resource ownership lives in
`app.auth.access`, because it needs the ticket, not just the user.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User

# Points at the form-encoded variant, which is what the /docs Authorize button posts.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

DbSession = Annotated[Session, Depends(get_db)]

# One message for every authentication failure: a caller must not be able to
# tell a forged token from an expired one, or a real account from a deleted one.
_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """Resolve the bearer token to the live user row.

    The token only says *which* user; every attribute used for authorization is
    read back from the database, so revoking a role takes effect immediately
    instead of when the token expires.
    """
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = UUID(str(subject))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CREDENTIALS_ERROR from None

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory restricting an endpoint to the given roles.

    ADMIN is always allowed, so no endpoint has to remember to list it.
    """
    allowed = {UserRole(role) for role in roles} | {UserRole.ADMIN}

    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires one of: "
                    f"{', '.join(sorted(role.value for role in allowed))}."
                ),
            )

        return current_user

    return dependency
