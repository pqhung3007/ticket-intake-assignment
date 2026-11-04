"""Test fixtures.

Tests run the real app (real middleware, auth and SQL) against a real Postgres database.
Tokens are real RS256 JWTs signed with a key generated per test session, so the JWT
verification path is exercised end to end, not mocked.
"""

import os
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth.verifier import JwtVerifier
from app.core.config import Settings
from app.db.session import create_engine
from app.main import create_app

ISSUER = "https://issuer.test"
ADMIN_EMAIL = "adam@example.com"

TokenFactory = Callable[..., str]


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        env="test",
        database_url=os.environ.get(
            "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tickets_test"
        ),
        auth_mode="jwt",
        n0_issuer=ISSUER,
        admin_emails=[ADMIN_EMAIL],
        public_base_url="https://tickets.test",
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="session")
def make_token(signing_key: rsa.RSAPrivateKey) -> TokenFactory:
    def factory(
        sub: str,
        *,
        email: str | None = None,
        name: str | None = None,
        roles: list[str] | None = None,
        agent: str | None = None,
        scope: str | None = None,
        expires_in: int = 300,
        issuer: str = ISSUER,
        key: Any = None,
        **extra: Any,
    ) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {"sub": sub, "iss": issuer, "iat": now, "exp": now + expires_in, **extra}
        if email:
            claims["email"] = email
        if name:
            claims["name"] = name
        if roles is not None:
            claims["roles"] = roles
        if agent:
            claims["act"] = {"sub": agent}
        if scope is not None:
            claims["scope"] = scope
        return jwt.encode(claims, key or signing_key, algorithm="RS256", headers={"kid": "test"})

    return factory


@pytest.fixture(scope="session")
def verifier(signing_key: rsa.RSAPrivateKey) -> JwtVerifier:
    public_key = signing_key.public_key()
    return JwtVerifier(issuer=ISSUER, key_resolver=lambda _token: public_key)


@pytest.fixture(scope="session")
async def engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings)
    async with engine.begin() as conn:  # start from an empty schema every run
        await conn.execute(text("drop schema public cascade"))
        await conn.execute(text("create schema public"))
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def app(settings: Settings, engine: AsyncEngine, verifier: JwtVerifier) -> AsyncIterator[Any]:
    application = create_app(settings, engine=engine, verifier=verifier)
    async with application.router.lifespan_context(application):  # runs migrations
        yield application


@pytest.fixture
async def clean_db(app: Any, engine: AsyncEngine) -> AsyncIterator[None]:
    """Empties all tables after the test. Made autouse for DB-backed suites in their conftest."""
    yield
    async with engine.begin() as conn:
        await conn.execute(text("truncate tickets, ticket_events, app_roles, users restart identity cascade"))


@pytest.fixture
def session_factory(app: Any) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    return factory


@pytest.fixture
async def client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---- named test users ----


@pytest.fixture
def auth(make_token: TokenFactory) -> Callable[..., dict[str, str]]:
    users: dict[str, dict[str, Any]] = {
        "alice": {"sub": "u-alice", "email": "alice@example.com", "name": "Alice"},
        "bob": {"sub": "u-bob", "email": "bob@example.com", "name": "Bob"},
        "tara": {"sub": "u-tara", "email": "tara@example.com", "name": "Tara", "roles": ["triager"]},
        "adam": {"sub": "u-adam", "email": ADMIN_EMAIL, "name": "Adam"},
    }

    def headers(user: str, *, agent: str | None = None, **overrides: Any) -> dict[str, str]:
        claims = {**users[user], **overrides}
        sub = claims.pop("sub")
        return {"Authorization": f"Bearer {make_token(sub, agent=agent, **claims)}"}

    return headers
