from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, require_admin, require_triager
from app.auth.principal import Principal, Role
from app.db.session import get_session
from app.users.schemas import MeOut, RoleUpdateIn, UserListOut, UserOut
from app.users.service import UserService

router = APIRouter(tags=["users"])

Session = Annotated[AsyncSession, Depends(get_session)]


def _service(request: Request, session: AsyncSession) -> UserService:
    return UserService(session, request.app.state.settings)


@router.get("/me", summary="The current user and their role")
async def me(principal: CurrentPrincipal) -> MeOut:
    return MeOut(
        id=principal.user_id,
        email=principal.email,
        name=principal.name,
        role=principal.role,
        is_triager=principal.is_triager,
        is_admin=principal.is_admin,
        agent_id=principal.agent_id,
    )


@router.get("/users", summary="Search workspace members who have used the app (triagers only)")
async def list_users(
    request: Request,
    session: Session,
    _: Annotated[Principal, Depends(require_triager)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserListOut:
    return UserListOut(items=await _service(request, session).search(q, limit))


@router.put("/users/{user_id}/role", summary="Grant or revoke the triager role (admins only)")
async def set_role(
    request: Request,
    session: Session,
    user_id: str,
    body: RoleUpdateIn,
    actor: Annotated[Principal, Depends(require_admin)],
) -> UserOut:
    return await _service(request, session).set_role(actor, user_id, Role(body.role))
