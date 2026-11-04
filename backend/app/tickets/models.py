import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} in ({', '.join(repr(v) for v in values)})"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # Human-friendly, monotonic number (#42). Also the keyset pagination cursor.
    number: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)

    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, server_default="")
    steps_to_reproduce: Mapped[str | None] = mapped_column(Text)
    expected_behavior: Mapped[str | None] = mapped_column(Text)
    actual_behavior: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), server_default="medium")
    status: Mapped[str] = mapped_column(String(16), server_default="open")
    target_app: Mapped[str] = mapped_column(Text)
    # Confidential tickets are visible to their reporter and triagers only.
    confidential: Mapped[bool] = mapped_column(server_default=text("false"))

    # Identity always comes from the verified token, never from request bodies.
    reporter_id: Mapped[str] = mapped_column(Text)
    reporter_email: Mapped[str | None] = mapped_column(Text)
    reporter_name: Mapped[str | None] = mapped_column(Text)
    created_via: Mapped[str] = mapped_column(String(16))
    created_by_agent: Mapped[str | None] = mapped_column(Text)

    assignee_id: Mapped[str | None] = mapped_column(Text)
    assignee_email: Mapped[str | None] = mapped_column(Text)
    assignee_name: Mapped[str | None] = mapped_column(Text)

    # Idempotency: (reporter_id, request_key) is unique; request_hash detects key reuse
    # with a different payload.
    request_key: Mapped[str | None] = mapped_column(Text)
    request_hash: Mapped[str | None] = mapped_column(Text)

    # Optimistic concurrency: updates must present the version they read.
    version: Mapped[int] = mapped_column(server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]

    __table_args__ = (
        CheckConstraint("char_length(title) between 3 and 120", name="title_length"),
        CheckConstraint("char_length(description) <= 10000", name="description_length"),
        CheckConstraint("char_length(steps_to_reproduce) <= 5000", name="steps_length"),
        CheckConstraint("char_length(expected_behavior) <= 2000", name="expected_length"),
        CheckConstraint("char_length(actual_behavior) <= 2000", name="actual_length"),
        CheckConstraint("char_length(environment) <= 500", name="environment_length"),
        CheckConstraint("char_length(target_app) between 1 and 80", name="target_app_length"),
        CheckConstraint(_in("severity", ("low", "medium", "high", "critical")), name="severity_valid"),
        CheckConstraint(_in("status", ("open", "in_progress", "resolved", "closed")), name="status_valid"),
        CheckConstraint(_in("created_via", ("ui", "agent")), name="created_via_valid"),
        Index(
            "uq_tickets_reporter_request_key",
            "reporter_id",
            "request_key",
            unique=True,
            postgresql_where=text("request_key is not null"),
        ),
        Index("ix_tickets_status_number", "status", number.desc()),
        Index("ix_tickets_reporter_number", "reporter_id", number.desc()),
        Index("ix_tickets_assignee_number", "assignee_id", number.desc()),
        Index("ix_tickets_target_app_number", func.lower(target_app), number.desc()),
    )


class TicketEvent(Base):
    """Append-only activity log: audit trail and comments."""

    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE")
    )
    type: Mapped[str] = mapped_column(String(32))
    actor_id: Mapped[str] = mapped_column(Text)
    actor_name: Mapped[str | None] = mapped_column(Text)
    actor_email: Mapped[str | None] = mapped_column(Text)
    actor_agent: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            _in("type", ("created", "updated", "status_changed", "assigned", "comment")),
            name="type_valid",
        ),
        CheckConstraint("char_length(body) <= 5000", name="body_length"),
        Index("ix_ticket_events_ticket_id_id", "ticket_id", "id"),
    )
