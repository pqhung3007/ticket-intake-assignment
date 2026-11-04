"""Who is calling.

`Identity` is what a verified token says. `Principal` is the identity plus the app-level role
resolved for it; every service and policy function works with a Principal.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    MEMBER = "member"
    TRIAGER = "triager"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class Identity:
    user_id: str
    email: str | None = None
    email_verified: bool = True
    name: str | None = None
    platform_roles: frozenset[str] = field(default_factory=frozenset)
    # Set when an agent calls on behalf of the user (RFC 8693 `act` claim).
    agent_id: str | None = None
    # OAuth scopes, when the token carries them. None means "not scope-restricted".
    scopes: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    role: Role
    email: str | None = None
    name: str | None = None
    agent_id: str | None = None
    scopes: frozenset[str] | None = None

    @property
    def is_agent(self) -> bool:
        return self.agent_id is not None

    @property
    def is_triager(self) -> bool:
        return self.role in (Role.TRIAGER, Role.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN
