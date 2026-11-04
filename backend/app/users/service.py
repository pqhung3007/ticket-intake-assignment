"""Role resolution and member directory.

Role precedence (highest wins):
  admin   - verified email in ADMIN_EMAILS, or a platform role in ADMIN_ROLES
  triager - a platform role in TRIAGER_ROLES, or granted in the app by an admin
  member  - everyone else who is signed in to the workspace
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import DUMMY_HASH, hash_password, verify_password
from app.auth.principal import Identity, Principal, Role
from app.core.config import Settings
from app.core.errors import Conflict, NotFound, Unauthenticated
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserOut
from app.users.throttle import LoginThrottle

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self, session: AsyncSession, settings: Settings, throttle: LoginThrottle | None = None
    ) -> None:
        self.session = session
        self.settings = settings
        self.throttle = throttle
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

    async def authenticate(self, email: str, password: str) -> User:
        """Check credentials. Every failure looks the same and costs the same."""
        key = email.strip().lower()
        if self.throttle:
            self.throttle.check(key)
        async with self.session.begin():
            user = await self.repo.get_by_email(key)
        # Always run one scrypt verification, so unknown emails are not distinguishable by timing.
        ok = verify_password(password, user.password_hash if user and user.password_hash else DUMMY_HASH)
        if not (user and ok):
            if self.throttle:
                self.throttle.fail(key)
            raise Unauthenticated("Invalid email or password")
        if self.throttle:
            self.throttle.clear(key)
        return user

    async def create_user(self, email: str, name: str, password: str) -> UserOut:
        try:
            async with self.session.begin():
                if await self.repo.get_by_email(email):
                    raise Conflict("An account with this email already exists.")
                user = await self.repo.create_with_password(
                    uuid.uuid4().hex, email, name.strip(), hash_password(password)
                )
        except IntegrityError as exc:  # lost a race with a concurrent create
            raise Conflict("An account with this email already exists.") from exc
        return self._to_out(user, None)

    async def change_password(self, principal: Principal, current: str, new: str) -> None:
        async with self.session.begin():
            user = await self.repo.get(principal.user_id)
            stored = user.password_hash if user else None
            if not stored or not verify_password(current, stored):
                raise Unauthenticated("Current password is incorrect")
            await self.repo.set_password(principal.user_id, hash_password(new))

    async def bootstrap_admin(self) -> None:
        """Create the first admin from config so a fresh deployment can sign in. Never overwrites."""
        password = self.settings.bootstrap_admin_password
        if not password:
            return
        email = self.settings.admin_emails[0]
        try:
            async with self.session.begin():
                if await self.repo.get_by_email(email):
                    return
                await self.repo.create_with_password(
                    uuid.uuid4().hex, email, "Administrator", hash_password(password)
                )
        except IntegrityError:
            return  # another replica created it first
        logger.info("bootstrap admin created", extra={"email": email})

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
