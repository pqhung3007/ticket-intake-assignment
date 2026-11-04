"""FastAPI dependencies that authenticate the caller and enforce coarse role checks.

Fine-grained, per-ticket rules live in app/tickets/policy.py.
"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.principal import Identity, Principal
from app.auth.verifier import TokenVerifier
from app.core.config import Settings
from app.core.errors import Forbidden, Unauthenticated
from app.core.logging import agent_id_var, user_id_var
from app.db.session import get_session
from app.users.service import UserService


def _extract_token(request: Request, settings: Settings) -> str | None:
    auth = request.headers.get("authorization")
    if auth:
        scheme, _, value = auth.partition(" ")
        if scheme.lower() != "bearer":
            return None
        return value.strip() or None
    if settings.auth_token_header:
        value = request.headers.get(settings.auth_token_header, "")
        if value:
            return value.removeprefix("Bearer ").strip() or None
    if settings.auth_cookie_name:
        return request.cookies.get(settings.auth_cookie_name) or None
    return None


async def get_identity(request: Request) -> Identity:
    settings: Settings = request.app.state.settings
    verifier: TokenVerifier = request.app.state.verifier
    token = _extract_token(request, settings)
    if not token:
        raise Unauthenticated("Authentication required")
    return await verifier.verify(token)


async def get_principal(
    request: Request,
    identity: Annotated[Identity, Depends(get_identity)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Principal:
    principal = await UserService(session, request.app.state.settings).resolve_principal(identity)
    user_id_var.set(principal.user_id)
    agent_id_var.set(principal.agent_id)
    return principal


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


async def require_human(principal: CurrentPrincipal) -> Principal:
    """For endpoints that agents must never reach, whatever the user's own rights are."""
    if principal.is_agent:
        raise Forbidden("This action is not available to agents")
    return principal


async def require_triager(principal: Annotated[Principal, Depends(require_human)]) -> Principal:
    if not principal.is_triager:
        raise Forbidden("Triager role required")
    return principal


async def require_admin(principal: Annotated[Principal, Depends(require_human)]) -> Principal:
    if not principal.is_admin:
        raise Forbidden("Admin role required")
    return principal
