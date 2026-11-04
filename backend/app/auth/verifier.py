"""Verification of platform-issued tokens.

The app trusts exactly one thing: a JWT signed by the N0 issuer. Keys are discovered via
OIDC discovery (falling back to /.well-known/jwks.json) and cached; discovery is retried on
the next request if it fails, so a slow platform start does not permanently break auth.
"""

import asyncio
import json
import logging
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

import jwt

from app.auth.principal import Identity
from app.core.errors import Unauthenticated

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "ES256", "ES384", "EdDSA"]

# Resolves the verification key for a raw token (blocking; run in a worker thread).
KeyResolver = Callable[[str], Any]


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> Identity: ...


def _str_set(value: object) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(v.lower() for v in value.replace(",", " ").split() if v)
    if isinstance(value, list | tuple):
        return frozenset(str(v).lower() for v in value if isinstance(v, str) and v)
    return frozenset()


def _agent_of(claims: dict[str, Any]) -> str | None:
    act = claims.get("act")
    if isinstance(act, dict) and isinstance(act.get("sub"), str) and act["sub"]:
        return str(act["sub"])
    flat = claims.get("agent_id")
    return flat if isinstance(flat, str) and flat else None


def identity_from_claims(claims: dict[str, Any], roles_claim: str) -> Identity:
    email = claims.get("email") if isinstance(claims.get("email"), str) else None
    name = claims.get("name") or claims.get("preferred_username")
    scope = claims.get("scope", claims.get("scp"))
    return Identity(
        user_id=str(claims["sub"]),
        email=email,
        email_verified=claims.get("email_verified") is not False,
        name=name if isinstance(name, str) else None,
        platform_roles=_str_set(claims.get(roles_claim)),
        agent_id=_agent_of(claims),
        scopes=_str_set(scope) if scope is not None else None,
    )


class JwksKeyResolver:
    """Lazily discovers the JWKS URL and caches signing keys (PyJWKClient handles rotation)."""

    def __init__(self, issuer: str, jwks_url: str | None = None) -> None:
        self._issuer = issuer
        self._jwks_url = jwks_url
        self._client: jwt.PyJWKClient | None = None

    def _discover(self) -> str:
        if self._jwks_url:
            return self._jwks_url
        url = f"{self._issuer}/.well-known/openid-configuration"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310  (https issuer from config)
                jwks_uri = json.load(resp).get("jwks_uri")
                if isinstance(jwks_uri, str) and jwks_uri:
                    return jwks_uri
        except Exception as exc:
            logger.warning("OIDC discovery failed; using default JWKS path", extra={"error": str(exc)})
        return f"{self._issuer}/.well-known/jwks.json"

    def __call__(self, token: str) -> Any:
        if self._client is None:
            self._client = jwt.PyJWKClient(self._discover(), cache_keys=True, lifespan=300, timeout=5)
        try:
            return self._client.get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError:
            self._client = None  # retry discovery next time
            raise


class JwtVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        key_resolver: KeyResolver,
        audience: str | None = None,
        roles_claim: str = "roles",
    ) -> None:
        self._issuer = issuer
        self._audience = audience
        self._key_resolver = key_resolver
        self._roles_claim = roles_claim

    async def verify(self, token: str) -> Identity:
        try:
            key = await asyncio.to_thread(self._key_resolver, token)
            claims: dict[str, Any] = jwt.decode(
                token,
                key,
                algorithms=ALLOWED_ALGORITHMS,
                issuer=self._issuer,
                audience=self._audience,
                leeway=5,
                options={"require": ["sub", "exp", "iss"], "verify_aud": self._audience is not None},
            )
        except Exception as exc:
            # Never tell the caller *why* (expired vs bad signature vs wrong issuer).
            logger.info("token rejected", extra={"reason": type(exc).__name__})
            raise Unauthenticated("Invalid or expired token") from exc
        return identity_from_claims(claims, self._roles_claim)
