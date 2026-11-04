"""Authorization rules for tickets.

Pure functions with no I/O, so the rules are unit-testable and shared by every entry
point: the web UI and agent tool calls hit the same service, which calls these.

  Read     every member sees every ticket, except confidential ones, which only the
           reporter and triagers see (others get 404, so existence is not leaked).
  Create   any member; an agent acts as the user who invoked it.
  Edit     the reporter while the ticket is active (open / in_progress); triagers always.
  Status   triagers: any transition. Reporter: close their own active ticket (withdraw),
           or reopen it once resolved/closed.
  Assign   triagers only.
  Comment  anyone who can see the ticket.
  Agents   limited to list / get / create, regardless of the user's own rights, so a
           prompt-injected agent cannot close, reassign or edit tickets.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.auth.principal import Principal
from app.core.errors import Forbidden
from app.tickets.constants import ACTIVE_STATUSES, DONE_STATUSES, Status


class Operation(StrEnum):
    LIST = "list"
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    COMMENT = "comment"


AGENT_OPERATIONS = frozenset({Operation.LIST, Operation.GET, Operation.CREATE})
READ_OPERATIONS = frozenset({Operation.LIST, Operation.GET})


@dataclass(frozen=True, slots=True)
class TicketAccess:
    """The facts about a ticket that permissions depend on."""

    reporter_id: str
    status: Status
    confidential: bool


def ensure_operation_allowed(p: Principal, op: Operation) -> None:
    if p.is_agent and op not in AGENT_OPERATIONS:
        raise Forbidden(f"Agents may only list, read and create tickets (attempted: {op}).")
    if p.scopes is not None:
        needed = "tickets:read" if op in READ_OPERATIONS else "tickets:write"
        if needed not in p.scopes:
            raise Forbidden(f"Token is missing scope {needed}.")


def sees_all_confidential(p: Principal) -> bool:
    return p.is_triager


def _is_reporter(p: Principal, t: TicketAccess) -> bool:
    return p.user_id == t.reporter_id


def can_view(p: Principal, t: TicketAccess) -> bool:
    return not t.confidential or _is_reporter(p, t) or sees_all_confidential(p)


def can_edit_content(p: Principal, t: TicketAccess) -> bool:
    if p.is_agent:
        return False
    return p.is_triager or (_is_reporter(p, t) and t.status in ACTIVE_STATUSES)


def allowed_transitions(p: Principal, t: TicketAccess) -> frozenset[Status]:
    if p.is_agent:
        return frozenset()
    if p.is_triager:
        return frozenset(Status) - {t.status}
    if _is_reporter(p, t):
        if t.status in ACTIVE_STATUSES:
            return frozenset({Status.CLOSED})
        if t.status in DONE_STATUSES:
            return frozenset({Status.OPEN})
    return frozenset()


def can_assign(p: Principal) -> bool:
    return p.is_triager and not p.is_agent


def can_comment(p: Principal, t: TicketAccess) -> bool:
    return not p.is_agent and can_view(p, t)
