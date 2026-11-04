"""App-issued session tokens (AUTH_MODE=password).

A session is a short-lived HS256 JWT signed with SESSION_SECRET, carried in an httpOnly cookie
(browsers) or as a Bearer token (scripts). Stateless: logout clears the cookie but cannot revoke
a token that was already copied; keep SESSION_TTL_MINUTES short.
"""

import time

import jwt
from fastapi import Response

from app.auth.principal import Identity
from app.auth.verifier import JwtVerifier
from app.core.config import Settings

SESSION_ISSUER = "ticket-intake"


def issue_session_token(settings: Settings, identity: Identity) -> str:
    assert settings.session_secret  # guaranteed by Settings validation
    now = int(time.time())
    claims = {
        "sub": identity.user_id,
        "iss": SESSION_ISSUER,
        "iat": now,
        "exp": now + settings.session_ttl_minutes * 60,
        "email": identity.email,
        "name": identity.name,
    }
    return jwt.encode(claims, settings.session_secret, algorithm="HS256")


def build_session_verifier(settings: Settings) -> JwtVerifier:
    secret = settings.session_secret
    assert secret
    # Roles never come from a session token: they are resolved from config and the database on every
    # request, so a role change takes effect immediately. The claim name below is deliberately unused.
    return JwtVerifier(
        issuer=SESSION_ISSUER,
        key_resolver=lambda _token: secret,
        algorithms=["HS256"],
        roles_claim="_not_used",
    )


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        settings.auth_cookie_name or "",
        token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.auth_cookie_name or "",
        httponly=True,
        samesite="lax",
        secure=settings.env == "production",
        path="/",
    )
