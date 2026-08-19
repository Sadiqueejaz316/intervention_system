from pydantic import BaseModel, EmailStr, Field

from app.core.enums import UserRole

#: Roles anyone may pick when registering.
#:
#: TEMPORARY HACKATHON SIMPLIFICATION: self-registration exists at all. Even so,
#: DISPATCHER and ADMIN are deliberately excluded — those accounts come from the
#: seed script or administrative provisioning, so nobody can grant themselves
#: dispatch or full access.
SELF_REGISTERABLE_ROLES = (UserRole.REPORTER, UserRole.CONTRACTOR)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.REPORTER
    skills: list[str] = Field(default_factory=list)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
