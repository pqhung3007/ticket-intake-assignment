from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """A workspace member this app has seen, upserted from verified tokens.

    Used to populate assignee and role pickers. It is never a source of identity:
    who the caller is always comes from the platform token.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (Index("ix_users_lower_email", func.lower(email)),)


class AppRole(Base):
    """Roles granted inside the app by an admin. Admins are configured at deploy time."""

    __tablename__ = "app_roles"

    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32))
    granted_by: Mapped[str] = mapped_column(Text)
    granted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (CheckConstraint("role in ('triager')", name="role_valid"),)
