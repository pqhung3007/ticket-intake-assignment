"""Ticket use cases. Each public method is one transaction and applies the policy first."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Principal
from app.core.config import Settings
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.tickets import policy
from app.tickets.constants import (
    ACTIVE_STATUSES,
    AUTO_DEDUPE_WINDOW_SECONDS,
    CONTENT_FIELDS,
    CreatedVia,
    EventType,
    Status,
)
from app.tickets.models import Ticket, TicketEvent
from app.tickets.policy import Operation, TicketAccess
from app.tickets.repository import TicketFilters, TicketRepository
from app.tickets.schemas import (
    TicketCreateIn,
    TicketListParams,
    TicketPermissionsOut,
    TicketUpdateIn,
)
from app.users.service import UserService

# Fields that may be omitted from an update but never set to null.
NON_NULLABLE_UPDATE_FIELDS = frozenset(
    {"title", "target_app", "severity", "description", "confidential", "status"}
)


@dataclass(frozen=True, slots=True)
class CreateResult:
    ticket: Ticket
    created: bool

    @property
    def deduplicated(self) -> bool:
        return not self.created


@dataclass(frozen=True, slots=True)
class TicketDetail:
    ticket: Ticket
    events: list[TicketEvent]
    permissions: TicketPermissionsOut


def _access(t: Ticket) -> TicketAccess:
    return TicketAccess(reporter_id=t.reporter_id, status=Status(t.status), confidential=t.confidential)


def _norm(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def _request_hash(data: TicketCreateIn) -> str:
    """Fingerprint of the report's content, used to recognise retries of the same request."""
    payload = [
        _norm(data.title),
        _norm(data.target_app),
        data.severity.value,
        _norm(data.description),
        _norm(data.steps_to_reproduce),
        _norm(data.expected_behavior),
        _norm(data.actual_behavior),
        _norm(data.environment),
        data.confidential,
    ]
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()


class TicketService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = TicketRepository(session)

    # ---------- create ----------

    async def create(self, p: Principal, data: TicketCreateIn) -> CreateResult:
        """Idempotent create.

        - With `request_key`: the same (reporter, key) returns the original ticket; reusing a key
          for a different report is a 409 so the caller notices its bug.
        - Without a key: an identical report from the same user within 10 minutes is treated as a
          retry (covers clients and agents that retry without keys).
        Creation is serialised per reporter, so concurrent retries cannot race past the check.
        """
        policy.ensure_operation_allowed(p, Operation.CREATE)
        request_hash = _request_hash(data)

        async with self.session.begin():
            await self.repo.lock_reporter(p.user_id)

            if data.request_key:
                existing = await self.repo.find_by_request_key(p.user_id, data.request_key)
                if existing is not None:
                    if existing.request_hash != request_hash:
                        raise Conflict(
                            "request_key was already used for a different report "
                            f"(ticket #{existing.number}). "
                            "Use a new key for a new report.",
                            code="idempotency_key_reuse",
                            details={"number": existing.number},
                        )
                    return CreateResult(existing, created=False)
            else:
                existing = await self.repo.find_recent_identical(
                    p.user_id, request_hash, AUTO_DEDUPE_WINDOW_SECONDS
                )
                if existing is not None:
                    return CreateResult(existing, created=False)

            via = CreatedVia.AGENT if p.is_agent else CreatedVia.UI
            ticket = await self.repo.insert(
                {
                    **data.model_dump(include=set(CONTENT_FIELDS)),
                    "severity": data.severity.value,
                    "reporter_id": p.user_id,
                    "reporter_email": p.email,
                    "reporter_name": p.name,
                    "created_via": via.value,
                    "created_by_agent": p.agent_id,
                    "request_key": data.request_key,
                    "request_hash": request_hash,
                }
            )
            await self._event(p, ticket, EventType.CREATED, data={"via": via.value})
        return CreateResult(ticket, created=True)

    # ---------- read ----------

    async def list(self, p: Principal, params: TicketListParams) -> tuple[list[Ticket], int | None]:
        policy.ensure_operation_allowed(p, Operation.LIST)
        filters = TicketFilters(
            status=params.status.value if params.status else None,
            severity=params.severity.value if params.severity else None,
            target_app=params.target_app,
            reporter_id=p.user_id if params.reporter == "me" else None,
            assignee_id=p.user_id if params.assignee == "me" else None,
            unassigned=params.assignee == "none",
            q=params.q,
        )
        async with self.session.begin():
            rows = list(
                await self.repo.list_page(
                    filters,
                    confidential_visible_to=p.user_id,
                    sees_all_confidential=policy.sees_all_confidential(p),
                    limit=params.limit + 1,
                    before_number=params.cursor,
                )
            )
        page = rows[: params.limit]
        next_cursor = page[-1].number if len(rows) > params.limit else None
        return page, next_cursor

    async def get(self, p: Principal, number: int) -> TicketDetail:
        policy.ensure_operation_allowed(p, Operation.GET)
        async with self.session.begin():
            ticket = await self._get_visible(p, number)
            events = list(await self.repo.list_events(ticket.id))
        return TicketDetail(ticket, events, self.permissions(p, ticket))

    async def stats(self, p: Principal) -> dict[Status, int]:
        policy.ensure_operation_allowed(p, Operation.LIST)
        async with self.session.begin():
            counts = await self.repo.count_by_status(
                confidential_visible_to=p.user_id, sees_all_confidential=policy.sees_all_confidential(p)
            )
        return {status: counts.get(status.value, 0) for status in Status}

    @staticmethod
    def permissions(p: Principal, t: Ticket) -> TicketPermissionsOut:
        access = _access(t)
        return TicketPermissionsOut(
            can_edit=policy.can_edit_content(p, access),
            can_comment=policy.can_comment(p, access),
            can_assign=policy.can_assign(p),
            allowed_statuses=sorted(policy.allowed_transitions(p, access)),
        )

    # ---------- update ----------

    async def update(self, p: Principal, number: int, patch: TicketUpdateIn) -> Ticket:
        """Partial update with optimistic concurrency. All-or-nothing: every requested change is
        authorised before anything is written."""
        policy.ensure_operation_allowed(p, Operation.UPDATE)
        requested = patch.model_fields_set - {"version"}
        for field in requested & NON_NULLABLE_UPDATE_FIELDS:
            if getattr(patch, field) is None:
                raise AppError(f"{field} cannot be null", code="validation_error")

        async with self.session.begin():
            ticket = await self._get_visible(p, number, for_update=True)
            if ticket.version != patch.version:
                raise Conflict(
                    "Ticket was modified by someone else. Reload and try again.",
                    code="version_conflict",
                    details={"current_version": ticket.version},
                )
            access = _access(ticket)

            content_changes: dict[str, dict[str, Any]] = {}
            for field in CONTENT_FIELDS:
                if field in requested:
                    new = getattr(patch, field)
                    new = new.value if hasattr(new, "value") else new
                    old = getattr(ticket, field)
                    if new != old:
                        content_changes[field] = {"from": old, "to": new}
            if content_changes and not policy.can_edit_content(p, access):
                raise Forbidden(
                    "Only the reporter (while the ticket is active) or a triager can edit this ticket."
                )

            status_change: dict[str, str] | None = None
            if "status" in requested and patch.status is not None and patch.status != ticket.status:
                if patch.status not in policy.allowed_transitions(p, access):
                    raise Forbidden(
                        f"You cannot move this ticket from {ticket.status} to {patch.status.value}."
                    )
                status_change = {"from": ticket.status, "to": patch.status.value}

            assign_change: dict[str, Any] | None = None
            if "assignee_id" in requested and patch.assignee_id != ticket.assignee_id:
                if not policy.can_assign(p):
                    raise Forbidden("Only triagers can assign tickets.")
                assign_change = await self._apply_assignee(ticket, patch.assignee_id)

            if not (content_changes or status_change or assign_change):
                return ticket  # no-op: don't bump the version or write events

            for field, change in content_changes.items():
                setattr(ticket, field, change["to"])
            if status_change:
                self._apply_status(ticket, Status(status_change["to"]))
            ticket.version += 1
            ticket.updated_at = func.now()
            ticket = await self.repo.save(ticket)

            if content_changes:
                await self._event(p, ticket, EventType.UPDATED, data={"changes": content_changes})
            if status_change:
                await self._event(p, ticket, EventType.STATUS_CHANGED, data=status_change)
            if assign_change:
                await self._event(p, ticket, EventType.ASSIGNED, data=assign_change)
        return ticket

    async def comment(self, p: Principal, number: int, body: str) -> TicketEvent:
        policy.ensure_operation_allowed(p, Operation.COMMENT)
        async with self.session.begin():
            ticket = await self._get_visible(p, number, for_update=True)
            if not policy.can_comment(p, _access(ticket)):
                raise Forbidden("You cannot comment on this ticket.")
            await self.repo.touch(ticket)
            return await self._event(p, ticket, EventType.COMMENT, body=body)

    # ---------- helpers ----------

    async def _get_visible(self, p: Principal, number: int, *, for_update: bool = False) -> Ticket:
        ticket = await self.repo.get_by_number(number, for_update=for_update)
        # Invisible confidential tickets are reported as missing, not forbidden.
        if ticket is None or not policy.can_view(p, _access(ticket)):
            raise NotFound(f"Ticket #{number} not found.")
        return ticket

    async def _apply_assignee(self, ticket: Ticket, assignee_id: str | None) -> dict[str, Any]:
        before = {"id": ticket.assignee_id, "name": ticket.assignee_name}
        if assignee_id is None:
            ticket.assignee_id = ticket.assignee_name = ticket.assignee_email = None
        else:
            user = await UserService(self.session, self.settings).get(assignee_id)
            if user is None:
                raise AppError(
                    "Unknown assignee: they must have opened the app at least once.", code="validation_error"
                )
            ticket.assignee_id, ticket.assignee_name, ticket.assignee_email = user.id, user.name, user.email
        return {"from": before, "to": {"id": ticket.assignee_id, "name": ticket.assignee_name}}

    @staticmethod
    def _apply_status(ticket: Ticket, to: Status) -> None:
        ticket.status = to.value
        if to is Status.RESOLVED:
            ticket.resolved_at = func.now()
        elif to in ACTIVE_STATUSES:
            ticket.resolved_at = None
        elif ticket.resolved_at is None:  # closed without having been resolved
            ticket.resolved_at = func.now()

    async def _event(
        self,
        p: Principal,
        ticket: Ticket,
        type: EventType,
        *,
        body: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> TicketEvent:
        return await self.repo.add_event(
            ticket.id,
            type=type.value,
            actor_id=p.user_id,
            actor_name=p.name,
            actor_email=p.email,
            actor_agent=p.agent_id,
            body=body,
            data=data,
        )
