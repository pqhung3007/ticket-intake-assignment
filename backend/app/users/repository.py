from collections.abc import Sequence

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.utils import escape_like
from app.users.models import AppRole, User

# Re-write last_seen_at at most this often per user, so authentication is not a write per request.
SEEN_THROTTLE = text("interval '5 minutes'")


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_seen(self, user_id: str, email: str | None, name: str | None) -> None:
        stmt = insert(User).values(id=user_id, email=email, name=name)
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.id],
            set_={"email": stmt.excluded.email, "name": stmt.excluded.name, "last_seen_at": func.now()},
            where=or_(
                User.last_seen_at < func.now() - SEEN_THROTTLE,
                User.email.is_distinct_from(stmt.excluded.email),
                User.name.is_distinct_from(stmt.excluded.name),
            ),
        )
        await self.session.execute(stmt)

    async def get_granted_role(self, user_id: str) -> str | None:
        result = await self.session.execute(select(AppRole.role).where(AppRole.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """The password account for this email, if any (platform-seen rows are ignored)."""
        stmt = select(User).where(func.lower(User.email) == email.lower(), User.password_hash.is_not(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_with_password(self, user_id: str, email: str, name: str, password_hash: str) -> User:
        user = User(id=user_id, email=email.lower(), name=name, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_password(self, user_id: str, password_hash: str) -> None:
        await self.session.execute(update(User).where(User.id == user_id).values(password_hash=password_hash))

    async def get(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def search(self, query: str | None, limit: int) -> Sequence[tuple[User, str | None]]:
        stmt = (
            select(User, AppRole.role)
            .outerjoin(AppRole, AppRole.user_id == User.id)
            .order_by(User.name.asc().nulls_last(), User.email.asc())
            .limit(limit)
        )
        if query:
            like = f"%{escape_like(query)}%"
            stmt = stmt.where(or_(User.name.ilike(like, escape="\\"), User.email.ilike(like, escape="\\")))
        return (await self.session.execute(stmt)).all()

    async def grant_role(self, user_id: str, role: str, granted_by: str) -> None:
        stmt = insert(AppRole).values(user_id=user_id, role=role, granted_by=granted_by)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AppRole.user_id],
            set_={"role": role, "granted_by": granted_by, "granted_at": func.now()},
        )
        await self.session.execute(stmt)

    async def revoke_role(self, user_id: str) -> None:
        await self.session.execute(delete(AppRole).where(AppRole.user_id == user_id))
