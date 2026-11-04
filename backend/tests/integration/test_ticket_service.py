import asyncio
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.principal import Principal, Role
from app.core.config import Settings
from app.core.errors import Conflict, Forbidden, NotFound
from app.tickets.constants import Status
from app.tickets.models import Ticket, TicketEvent
from app.tickets.schemas import TicketCreateIn, TicketUpdateIn
from app.tickets.service import TicketService

ALICE = Principal(user_id="alice", role=Role.MEMBER, name="Alice", email="alice@example.com")
BOB = Principal(user_id="bob", role=Role.MEMBER)
TARA = Principal(user_id="tara", role=Role.TRIAGER)
ALICE_AGENT = Principal(user_id="alice", role=Role.MEMBER, agent_id="intake-agent")

Factory = async_sessionmaker[AsyncSession]


def report(**overrides: Any) -> TicketCreateIn:
    data: dict[str, Any] = {"title": "CSV export times out", "target_app": "reports", **overrides}
    return TicketCreateIn(**data)


async def create(factory: Factory, settings: Settings, p: Principal, data: TicketCreateIn) -> Any:
    async with factory() as session:
        return await TicketService(session, settings).create(p, data)


async def count(factory: Factory, model: type[Any] = Ticket) -> int:
    async with factory() as session:
        return int((await session.execute(select(func.count()).select_from(model))).scalar_one())


class TestIdempotentCreate:
    async def test_same_key_returns_original(self, session_factory: Factory, settings: Settings) -> None:
        first = await create(session_factory, settings, ALICE, report(request_key="k1"))
        again = await create(session_factory, settings, ALICE, report(request_key="k1"))
        assert first.created and not again.created
        assert again.ticket.number == first.ticket.number
        assert await count(session_factory) == 1

    async def test_key_reuse_with_different_payload_conflicts(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        await create(session_factory, settings, ALICE, report(request_key="k1"))
        with pytest.raises(Conflict) as exc:
            await create(
                session_factory, settings, ALICE, report(request_key="k1", title="Other bug entirely")
            )
        assert exc.value.code == "idempotency_key_reuse"

    async def test_keys_are_scoped_per_reporter(self, session_factory: Factory, settings: Settings) -> None:
        await create(session_factory, settings, ALICE, report(request_key="k1"))
        other = await create(session_factory, settings, BOB, report(request_key="k1"))
        assert other.created

    async def test_keyless_identical_retry_is_deduplicated(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        first = await create(session_factory, settings, ALICE, report(description="Since Monday"))
        retry = await create(session_factory, settings, ALICE, report(description="  since   monday "))
        assert retry.deduplicated and retry.ticket.id == first.ticket.id

    async def test_keyless_different_content_creates_new(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        await create(session_factory, settings, ALICE, report())
        second = await create(session_factory, settings, ALICE, report(severity="high"))
        assert second.created

    async def test_concurrent_retries_create_exactly_one(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        results = await asyncio.gather(
            *(create(session_factory, settings, ALICE, report(request_key="race")) for _ in range(8))
        )
        assert sum(r.created for r in results) == 1
        assert len({r.ticket.id for r in results}) == 1
        assert await count(session_factory) == 1

    async def test_agent_create_is_attributed_to_user_and_agent(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        result = await create(session_factory, settings, ALICE_AGENT, report())
        assert result.ticket.reporter_id == "alice"
        assert result.ticket.created_via == "agent"
        assert result.ticket.created_by_agent == "intake-agent"
        assert await count(session_factory, TicketEvent) == 1


class TestUpdate:
    async def _ticket(self, factory: Factory, settings: Settings, **kw: Any) -> Ticket:
        return (await create(factory, settings, ALICE, report(**kw))).ticket  # type: ignore[no-any-return]

    async def update(
        self, factory: Factory, settings: Settings, p: Principal, number: int, **patch: Any
    ) -> Ticket:
        async with factory() as session:
            return await TicketService(session, settings).update(p, number, TicketUpdateIn(**patch))

    async def test_stale_version_conflicts(self, session_factory: Factory, settings: Settings) -> None:
        t = await self._ticket(session_factory, settings)
        await self.update(
            session_factory, settings, ALICE, t.number, version=1, title="Export to CSV times out"
        )
        with pytest.raises(Conflict) as exc:
            await self.update(session_factory, settings, ALICE, t.number, version=1, severity="high")
        assert exc.value.code == "version_conflict"

    async def test_noop_update_keeps_version(self, session_factory: Factory, settings: Settings) -> None:
        t = await self._ticket(session_factory, settings)
        same = await self.update(session_factory, settings, ALICE, t.number, version=1, title=t.title)
        assert same.version == 1

    async def test_changes_are_audited(self, session_factory: Factory, settings: Settings) -> None:
        t = await self._ticket(session_factory, settings)
        await self.update(
            session_factory, settings, TARA, t.number, version=1, severity="high", status="in_progress"
        )
        async with session_factory() as session:
            detail = await TicketService(session, settings).get(TARA, t.number)
        types = [e.type for e in detail.events]
        assert types == ["created", "updated", "status_changed"]
        assert detail.events[1].data == {"changes": {"severity": {"from": "medium", "to": "high"}}}

    async def test_resolved_at_follows_status(self, session_factory: Factory, settings: Settings) -> None:
        t = await self._ticket(session_factory, settings)
        resolved = await self.update(session_factory, settings, TARA, t.number, version=1, status="resolved")
        assert resolved.resolved_at is not None
        reopened = await self.update(session_factory, settings, ALICE, t.number, version=2, status="open")
        assert reopened.status == Status.OPEN and reopened.resolved_at is None

    async def test_unauthorized_change_writes_nothing(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        t = await self._ticket(session_factory, settings)
        with pytest.raises(Forbidden):
            # Title change alone would be allowed for the reporter; the status change is not.
            await self.update(
                session_factory, settings, ALICE, t.number, version=1, title="New title", status="resolved"
            )
        async with session_factory() as session:
            fresh = await session.get(Ticket, t.id)
        assert fresh is not None and fresh.title == t.title and fresh.version == 1

    async def test_null_for_required_field_rejected(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        t = await self._ticket(session_factory, settings)
        with pytest.raises(Exception, match="title cannot be null"):
            await self.update(session_factory, settings, ALICE, t.number, version=1, title=None)

    async def test_confidential_hidden_as_not_found(
        self, session_factory: Factory, settings: Settings
    ) -> None:
        t = await self._ticket(session_factory, settings, confidential=True)
        async with session_factory() as session:
            with pytest.raises(NotFound):
                await TicketService(session, settings).get(BOB, t.number)
