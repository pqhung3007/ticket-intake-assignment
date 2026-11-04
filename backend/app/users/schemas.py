from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.auth.passwords import MIN_LENGTH
from app.auth.principal import Principal, Role


class MeOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    role: Role
    is_triager: bool
    is_admin: bool
    # Set when the request was made by an agent acting for this user.
    agent_id: str | None

    @classmethod
    def from_principal(cls, p: Principal) -> "MeOut":
        return cls(
            id=p.user_id,
            email=p.email,
            name=p.name,
            role=p.role,
            is_triager=p.is_triager,
            is_admin=p.is_admin,
            agent_id=p.agent_id,
        )


class UserOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    role: Role
    # "config": admin set at deploy time (cannot be changed in the app).
    # "grant": triager role granted by an admin in the app.
    role_source: Literal["config", "grant"] | None
    last_seen_at: datetime


class UserListOut(BaseModel):
    items: list[UserOut]


class RoleUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["member", "triager"] = Field(description="Grant or revoke the triager role")


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class CreateUserIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(
        min_length=MIN_LENGTH, max_length=200, description="Initial password; the user can change it"
    )


class ChangePasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=MIN_LENGTH, max_length=200)
