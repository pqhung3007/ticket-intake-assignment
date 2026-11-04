"""Role resolution and member directory.

Role precedence (highest wins):
  admin   - verified email in ADMIN_EMAILS, or a platform role in ADMIN_ROLES
  triager - a platform role in TRIAGER_ROLES, or granted in the app by an admin
  member  - everyone else who is signed in to the workspace
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Identity, Principal, Role
from app.core.config import Settings
from app.core.errors import Conflict, NotFound
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserOut


class UserService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = UserRepository(session)

    def _is_config_admin(self, email: str | None, email_verified: bool = True) -> bool:
        # An unverified email must never grant admin.
        return bool(email and email_verified and email.lower() in self.settings.admin_emails)

    async def resolve_principal(self, identity: Identity) -> Principal:
        async with self.session.begin():
            await self.repo.upsert_seen(identity.user_id, identity.email, identity.name)
            granted = await self.repo.get_granted_role(identity.user_id)

        if self._is_config_admin(identity.email, identity.email_verified) or (
            identity.platform_roles & set(self.settings.admin_roles)
        ):
            role = Role.ADMIN
        elif granted == Role.TRIAGER or identity.platform_roles & set(self.settings.triager_roles):
            role = Role.TRIAGER
        else:
            role = Role.MEMBER

        return Principal(
            user_id=identity.user_id,
            role=role,
            email=identity.email,
            name=identity.name,
            agent_id=identity.agent_id,
            scopes=identity.scopes,
        )

    async def get(self, user_id: str) -> User | None:
        return await self.repo.get(user_id)

    async def search(self, query: str | None, limit: int) -> list[UserOut]:
        rows = await self.repo.search(query, limit)
        return [self._to_out(user, granted) for user, granted in rows]

    async def set_role(self, actor: Principal, user_id: str, role: Role) -> UserOut:
        async with self.session.begin():
            user = await self.repo.get(user_id)
            if user is None:
                raise NotFound(
                    "User not found. They must open the app at least once before a role can be granted."
                )
            if self._is_config_admin(user.email):
                raise Conflict(
                    "This user is an admin by deployment configuration; their role cannot be changed here."
                )
            if role is Role.TRIAGER:
                await self.repo.grant_role(user_id, Role.TRIAGER, granted_by=actor.user_id)
            else:
                await self.repo.revoke_role(user_id)
            granted = await self.repo.get_granted_role(user_id)
        return self._to_out(user, granted)

    def _to_out(self, user: User, granted: str | None) -> UserOut:
        if self._is_config_admin(user.email):
            role, source = Role.ADMIN, "config"
        elif granted == Role.TRIAGER:
            role, source = Role.TRIAGER, "grant"
        else:
            role, source = Role.MEMBER, None
        return UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            role=role,
            role_source=source,  # type: ignore[arg-type]
            last_seen_at=user.last_seen_at,
        )
