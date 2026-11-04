"""Request/response contracts for tickets.

These models are also the contract of the agent-facing tools (create_ticket, list_tickets):
field descriptions are written for an LLM reader, and unknown fields are rejected so a
forged `reporter` or `status` in a create call fails loudly instead of being ignored.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.tickets.constants import CreatedVia, EventType, Severity, Status
from app.tickets.models import Ticket, TicketEvent


def _blank_to_none(value: object) -> object:
    return None if isinstance(value, str) and not value.strip() else value


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ---------- inputs ----------


class TicketCreateIn(_Input):
    title: str = Field(
        min_length=3, max_length=120, description="Short, specific summary of what is broken (not 'bug')."
    )
    target_app: str = Field(
        min_length=1, max_length=80, description="Name of the app the bug is in, e.g. 'reports'."
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="critical = outage/data loss/security; high = main feature unusable; "
        "medium = degraded with workaround; low = cosmetic.",
    )
    description: str = Field(
        default="", max_length=10_000, description="What the reporter said, in their words plus context."
    )
    steps_to_reproduce: str | None = Field(
        default=None, max_length=5_000, description="Only steps the reporter actually gave. Never invent."
    )
    expected_behavior: str | None = Field(default=None, max_length=2_000)
    actual_behavior: str | None = Field(default=None, max_length=2_000)
    environment: str | None = Field(
        default=None, max_length=500, description="Browser/OS/version/account, if known."
    )
    confidential: bool = Field(
        default=False, description="True for security issues or sensitive data; hides it from non-triagers."
    )
    request_key: str | None = Field(
        default=None,
        max_length=128,
        description="Idempotency key. Retrying with the same key returns the original ticket instead of "
        "creating a duplicate.",
    )

    _blank = field_validator(
        "steps_to_reproduce",
        "expected_behavior",
        "actual_behavior",
        "environment",
        "request_key",
        mode="before",
    )(_blank_to_none)


class TicketUpdateIn(_Input):
    """Partial update. Only fields present in the request are changed."""

    version: int = Field(ge=1, description="The version you last read; a stale version is rejected (409).")
    title: str | None = Field(default=None, min_length=3, max_length=120)
    target_app: str | None = Field(default=None, min_length=1, max_length=80)
    severity: Severity | None = None
    description: str | None = Field(default=None, max_length=10_000)
    steps_to_reproduce: str | None = Field(default=None, max_length=5_000)
    expected_behavior: str | None = Field(default=None, max_length=2_000)
    actual_behavior: str | None = Field(default=None, max_length=2_000)
    environment: str | None = Field(default=None, max_length=500)
    confidential: bool | None = None
    status: Status | None = None
    assignee_id: str | None = Field(default=None, description="User id to assign; null to unassign.")

    _blank = field_validator(
        "steps_to_reproduce", "expected_behavior", "actual_behavior", "environment", mode="before"
    )(_blank_to_none)


class TicketListParams(_Input):
    status: Status | None = None
    severity: Severity | None = None
    target_app: str | None = Field(default=None, max_length=80)
    reporter: Literal["me"] | None = Field(default=None, description="'me' = only tickets I reported")
    assignee: Literal["me", "none"] | None = None
    q: str | None = Field(default=None, max_length=100, description="Text search in title/description/app")
    limit: int = Field(default=20, ge=1, le=100)
    cursor: int | None = Field(default=None, ge=1, description="next_cursor from the previous page")

    _blank = field_validator("target_app", "q", mode="before")(_blank_to_none)


class CommentIn(_Input):
    body: str = Field(min_length=1, max_length=5_000)


# ---------- outputs ----------


class PersonOut(BaseModel):
    id: str
    name: str | None
    email: str | None


class ActorOut(PersonOut):
    agent: str | None = Field(description="Agent that acted on this person's behalf, if any")


class TicketSummaryOut(BaseModel):
    id: uuid.UUID
    number: int
    title: str
    target_app: str
    severity: Severity
    status: Status
    confidential: bool
    reporter: PersonOut
    assignee: PersonOut | None
    created_via: CreatedVia
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, t: Ticket) -> "TicketSummaryOut":
        return cls.model_validate(_ticket_fields(t))


class TicketOut(TicketSummaryOut):
    description: str
    steps_to_reproduce: str | None
    expected_behavior: str | None
    actual_behavior: str | None
    environment: str | None
    created_by_agent: str | None
    version: int
    resolved_at: datetime | None
    url: str | None = Field(description="Link to the ticket in the web UI")

    @classmethod
    def from_model(cls, t: Ticket, base_url: str | None = None) -> "TicketOut":
        data = _ticket_fields(t)
        data.update(
            description=t.description,
            steps_to_reproduce=t.steps_to_reproduce,
            expected_behavior=t.expected_behavior,
            actual_behavior=t.actual_behavior,
            environment=t.environment,
            created_by_agent=t.created_by_agent,
            version=t.version,
            resolved_at=t.resolved_at,
            url=f"{base_url.rstrip('/')}/tickets/{t.number}" if base_url else None,
        )
        return cls.model_validate(data)


class TicketEventOut(BaseModel):
    id: int
    type: EventType
    actor: ActorOut
    body: str | None
    data: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_model(cls, e: TicketEvent) -> "TicketEventOut":
        return cls(
            id=e.id,
            type=EventType(e.type),
            actor=ActorOut(id=e.actor_id, name=e.actor_name, email=e.actor_email, agent=e.actor_agent),
            body=e.body,
            data=e.data,
            created_at=e.created_at,
        )


class TicketPermissionsOut(BaseModel):
    """What the current user may do with this ticket, so the UI never re-implements the rules."""

    can_edit: bool
    can_comment: bool
    can_assign: bool
    allowed_statuses: list[Status]


class TicketDetailOut(BaseModel):
    ticket: TicketOut
    events: list[TicketEventOut]
    permissions: TicketPermissionsOut


class TicketListOut(BaseModel):
    items: list[TicketSummaryOut]
    next_cursor: int | None = Field(
        description="Pass as `cursor` to get the next page; null on the last page"
    )


class TicketCreateOut(BaseModel):
    ticket: TicketOut
    created: bool = Field(description="False when this call matched an earlier identical request")
    deduplicated: bool


class CommentOut(BaseModel):
    comment: TicketEventOut


class TicketStatsOut(BaseModel):
    by_status: dict[Status, int]
    total: int


def _ticket_fields(t: Ticket) -> dict[str, Any]:
    return {
        "id": t.id,
        "number": t.number,
        "title": t.title,
        "target_app": t.target_app,
        "severity": t.severity,
        "status": t.status,
        "confidential": t.confidential,
        "reporter": PersonOut(id=t.reporter_id, name=t.reporter_name, email=t.reporter_email),
        "assignee": PersonOut(id=t.assignee_id, name=t.assignee_name, email=t.assignee_email)
        if t.assignee_id
        else None,
        "created_via": t.created_via,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }
