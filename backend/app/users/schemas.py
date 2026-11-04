from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.auth.principal import Role


class MeOut(BaseModel):
    id: str
    email: str | None
    name: str | None
    role: Role
    is_triager: bool
    is_admin: bool
    # Set when the request was made by an agent acting for this user.
    agent_id: str | None


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
