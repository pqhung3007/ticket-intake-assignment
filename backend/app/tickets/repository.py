"""All SQL for tickets and their events. No business rules here: callers pass in
already-authorized parameters (e.g. which confidential tickets the viewer may see)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, and_, func, insert, or_, select, text, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.utils import escape_like
from app.tickets.constants import MAX_EVENTS_PER_TICKET
from app.tickets.models import Ticket, TicketEvent


@dataclass(frozen=True, slots=True)
class TicketFilters:
    status: str | None = None
    severity: str | None = None
    target_app: str | None = None
    reporter_id: str | None = None
    assignee_id: str | None = None
    unassigned: bool = False
    q: str | None = None


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----- locking / idempotency -----

    async def lock_reporter(self, reporter_id: str) -> None:
        """Serialise ticket creation per reporter for the current transaction, so concurrent
        retries of the same request cannot both pass the duplicate check."""
        await self.session.execute(
            text("select pg_advisory_xact_lock(hashtext(:k))"), {"k": f"tickets:create:{reporter_id}"}
        )

    async def find_by_request_key(self, reporter_id: str, request_key: str) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.reporter_id == reporter_id, Ticket.request_key == request_key)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_recent_identical(
        self, reporter_id: str, request_hash: str, window_seconds: int
    ) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(
                Ticket.reporter_id == reporter_id,
                Ticket.request_hash == request_hash,
                Ticket.created_at > func.now() - func.make_interval(0, 0, 0, 0, 0, 0, window_seconds),
            )
            .order_by(Ticket.number.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    # ----- tickets -----

    async def insert(self, values: dict[str, Any]) -> Ticket:
        result = await self.session.execute(insert(Ticket).values(**values).returning(Ticket))
        return result.scalar_one()

    async def get_by_number(self, number: int, *, for_update: bool = False) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.number == number)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_page(
        self,
        filters: TicketFilters,
        *,
        confidential_visible_to: str | None,
        sees_all_confidential: bool,
        limit: int,
        before_number: int | None,
    ) -> Sequence[Ticket]:
        """Newest first, keyset-paginated on the monotonic ticket number (stable under inserts)."""
        conditions = self._conditions(filters)
        conditions.append(self._visibility(confidential_visible_to, sees_all_confidential))
        if before_number is not None:
            conditions.append(Ticket.number < before_number)
        stmt = select(Ticket).where(and_(*conditions)).order_by(Ticket.number.desc()).limit(limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def count_by_status(
        self, *, confidential_visible_to: str | None, sees_all_confidential: bool
    ) -> dict[str, int]:
        stmt = (
            select(Ticket.status, func.count())
            .where(self._visibility(confidential_visible_to, sees_all_confidential))
            .group_by(Ticket.status)
        )
        return {status: count for status, count in (await self.session.execute(stmt)).all()}

    async def touch(self, ticket: Ticket) -> None:
        ticket.updated_at = func.now()
        await self.session.flush()

    async def save(self, ticket: Ticket) -> Ticket:
        await self.session.flush()
        await self.session.refresh(ticket)
        return ticket

    # ----- events -----

    async def add_event(
        self,
        ticket_id: uuid.UUID,
        *,
        type: str,
        actor_id: str,
        actor_name: str | None,
        actor_email: str | None,
        actor_agent: str | None,
        body: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> TicketEvent:
        values = {
            "ticket_id": ticket_id,
            "type": type,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "actor_email": actor_email,
            "actor_agent": actor_agent,
            "body": body,
            "data": data or {},
        }
        result = await self.session.execute(insert(TicketEvent).values(**values).returning(TicketEvent))
        return result.scalar_one()

    async def list_events(self, ticket_id: uuid.UUID) -> Sequence[TicketEvent]:
        stmt = (
            select(TicketEvent)
            .where(TicketEvent.ticket_id == ticket_id)
            .order_by(TicketEvent.id)
            .limit(MAX_EVENTS_PER_TICKET)
        )
        return (await self.session.execute(stmt)).scalars().all()

    # ----- helpers -----

    @staticmethod
    def _visibility(viewer_id: str | None, sees_all: bool) -> ColumnElement[bool]:
        if sees_all:
            return true()
        return or_(Ticket.confidential.is_(False), Ticket.reporter_id == viewer_id)

    @staticmethod
    def _conditions(f: TicketFilters) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []
        if f.status:
            conditions.append(Ticket.status == f.status)
        if f.severity:
            conditions.append(Ticket.severity == f.severity)
        if f.target_app:
            conditions.append(func.lower(Ticket.target_app) == f.target_app.lower())
        if f.reporter_id:
            conditions.append(Ticket.reporter_id == f.reporter_id)
        if f.assignee_id:
            conditions.append(Ticket.assignee_id == f.assignee_id)
        if f.unassigned:
            conditions.append(Ticket.assignee_id.is_(None))
        if f.q:
            like = f"%{escape_like(f.q)}%"
            conditions.append(
                or_(
                    Ticket.title.ilike(like, escape="\\"),
                    Ticket.description.ilike(like, escape="\\"),
                    Ticket.target_app.ilike(like, escape="\\"),
                )
            )
        return conditions
