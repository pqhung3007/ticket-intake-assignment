"""Sign-in and account management. Mounted only when AUTH_MODE=password."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_human
from app.auth.principal import Identity, Principal
from app.auth.session import clear_session_cookie, issue_session_token, set_session_cookie
from app.db.session import get_session
from app.users.schemas import ChangePasswordIn, CreateUserIn, LoginIn, MeOut, UserOut
from app.users.service import UserService

router = APIRouter(tags=["accounts"])

Session = Annotated[AsyncSession, Depends(get_session)]


def _service(request: Request, session: AsyncSession) -> UserService:
    return UserService(session, request.app.state.settings, request.app.state.login_throttle)


@router.post("/auth/login", summary="Sign in with email and password; sets the session cookie")
async def login(request: Request, response: Response, session: Session, body: LoginIn) -> MeOut:
    service = _service(request, session)
    user = await service.authenticate(body.email, body.password)
    identity = Identity(user_id=user.id, email=user.email, name=user.name)
    principal = await service.resolve_principal(identity)
    settings = request.app.state.settings
    set_session_cookie(response, settings, issue_session_token(settings, identity))
    return MeOut.from_principal(principal)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Clear the session cookie")
async def logout(request: Request) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, request.app.state.settings)
    return response


@router.post("/auth/password", status_code=status.HTTP_204_NO_CONTENT, summary="Change your own password")
async def change_password(
    request: Request,
    session: Session,
    principal: Annotated[Principal, Depends(require_human)],
    body: ChangePasswordIn,
) -> Response:
    await _service(request, session).change_password(principal, body.current_password, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    summary="Create a member account with an initial password (admins only)",
)
async def create_user(
    request: Request,
    session: Session,
    _: Annotated[Principal, Depends(require_admin)],
    body: CreateUserIn,
) -> UserOut:
    return await _service(request, session).create_user(body.email, body.name, body.password)
