"""HTTP layer for tickets: parse input, call the service, shape the response.

`create_ticket` and `list_tickets` are also exposed to agents as N0 tools (see n0-app.json);
operation ids match the tool names.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.core.config import Settings
from app.db.session import get_session
from app.tickets.schemas import (
    CommentIn,
    CommentOut,
    TicketCreateIn,
    TicketCreateOut,
    TicketDetailOut,
    TicketEventOut,
    TicketListOut,
    TicketListParams,
    TicketOut,
    TicketStatsOut,
    TicketSummaryOut,
    TicketUpdateIn,
)
from app.tickets.service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])

Session = Annotated[AsyncSession, Depends(get_session)]
TicketNumber = Annotated[int, Path(ge=1, description="Ticket number, e.g. 42 for #42")]


def _service(request: Request, session: AsyncSession) -> TicketService:
    return TicketService(session, request.app.state.settings)


def _base_url(request: Request) -> str | None:
    settings: Settings = request.app.state.settings
    return settings.public_base_url


@router.post(
    "",
    operation_id="create_ticket",
    status_code=status.HTTP_201_CREATED,
    summary="File a bug report",
    responses={200: {"model": TicketCreateOut, "description": "Matched an earlier identical request"}},
)
async def create_ticket(
    request: Request, response: Response, session: Session, principal: CurrentPrincipal, body: TicketCreateIn
) -> TicketCreateOut:
    result = await _service(request, session).create(principal, body)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return TicketCreateOut(
        ticket=TicketOut.from_model(result.ticket, _base_url(request)),
        created=result.created,
        deduplicated=result.deduplicated,
    )


@router.get("", operation_id="list_tickets", summary="List tickets visible to the current user, newest first")
async def list_tickets(
    request: Request,
    session: Session,
    principal: CurrentPrincipal,
    params: Annotated[TicketListParams, Query()],
) -> TicketListOut:
    items, next_cursor = await _service(request, session).list(principal, params)
    return TicketListOut(items=[TicketSummaryOut.from_model(t) for t in items], next_cursor=next_cursor)


@router.get("/stats", operation_id="ticket_stats", summary="Ticket counts by status")
async def ticket_stats(request: Request, session: Session, principal: CurrentPrincipal) -> TicketStatsOut:
    by_status = await _service(request, session).stats(principal)
    return TicketStatsOut(by_status=by_status, total=sum(by_status.values()))


@router.get("/{number}", operation_id="get_ticket", summary="A ticket with its activity and your permissions")
async def get_ticket(
    request: Request, session: Session, principal: CurrentPrincipal, number: TicketNumber
) -> TicketDetailOut:
    detail = await _service(request, session).get(principal, number)
    return TicketDetailOut(
        ticket=TicketOut.from_model(detail.ticket, _base_url(request)),
        events=[TicketEventOut.from_model(e) for e in detail.events],
        permissions=detail.permissions,
    )


@router.patch("/{number}", operation_id="update_ticket", summary="Edit, change status or assign")
async def update_ticket(
    request: Request,
    session: Session,
    principal: CurrentPrincipal,
    number: TicketNumber,
    body: TicketUpdateIn,
) -> TicketOut:
    ticket = await _service(request, session).update(principal, number, body)
    return TicketOut.from_model(ticket, _base_url(request))


@router.post(
    "/{number}/comments",
    operation_id="add_comment",
    status_code=status.HTTP_201_CREATED,
    summary="Comment on a ticket",
)
async def add_comment(
    request: Request, session: Session, principal: CurrentPrincipal, number: TicketNumber, body: CommentIn
) -> CommentOut:
    event = await _service(request, session).comment(principal, number, body.body)
    return CommentOut(comment=TicketEventOut.from_model(event))
