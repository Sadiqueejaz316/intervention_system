from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import service
from app.auth.dependencies import CurrentUser, DbSession
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.auth.security import create_access_token
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def register(data: RegisterRequest, db: DbSession) -> UserRead:
    user = service.register(db, data)

    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
)
def login(data: LoginRequest, db: DbSession) -> TokenResponse:
    user = service.authenticate(db, data.email, data.password)
    if user is None:
        raise _invalid_credentials()

    return TokenResponse(
        access_token=create_access_token(user_id=user.id, role=user.role)
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 password flow, for the /docs Authorize button",
)
def login_with_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenResponse:
    """Same exchange as /auth/login, taking the form encoding OAuth2 mandates.

    The OAuth2 spec calls the identifier `username`; here it is the email.
    """
    user = service.authenticate(db, form.username, form.password)
    if user is None:
        raise _invalid_credentials()

    return TokenResponse(
        access_token=create_access_token(user_id=user.id, role=user.role)
    )


@router.get("/me", response_model=UserRead, summary="The signed-in user")
def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


def _invalid_credentials() -> HTTPException:
    """One answer for both a wrong email and a wrong password."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )
