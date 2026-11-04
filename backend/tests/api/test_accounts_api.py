"""Password sign-in against the real app: cookie session, roles, account management."""

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import SESSION_COOKIE, Settings
from app.main import create_app

SECRET = "t" * 40
ADMIN = "adam@example.com"
ADMIN_PASSWORD = "admin-password-1"


@pytest.fixture
async def pw_app(engine: AsyncEngine, clean_db: None) -> AsyncIterator[Any]:
    settings = Settings(
        env="test",
        database_url="postgresql://x/x",
        auth_mode="password",
        session_secret=SECRET,
        admin_emails=[ADMIN],
        bootstrap_admin_password=ADMIN_PASSWORD,
        log_level="WARNING",
    )
    app = create_app(settings, engine=engine)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def http(pw_app: Any) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=pw_app), base_url="http://test") as c:
        yield c


def new_client(app: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def login(c: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    return await c.post("/api/v1/auth/login", json={"email": email, "password": password})


async def create_user(admin: httpx.AsyncClient, email: str, password: str = "member-password-1") -> Any:
    body = {"email": email, "name": email.split("@")[0], "password": password}
    res = await admin.post("/api/v1/users", json=body)
    assert res.status_code == 201, res.text
    return res.json()


async def test_requests_without_session_are_401(http: httpx.AsyncClient) -> None:
    assert (await http.get("/api/v1/me")).status_code == 401


async def test_bootstrap_admin_can_sign_in_and_cookie_is_httponly(http: httpx.AsyncClient) -> None:
    res = await login(http, ADMIN.upper(), ADMIN_PASSWORD)  # email is case-insensitive
    assert res.status_code == 200 and res.json()["role"] == "admin"
    cookie = res.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE}=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    me = await http.get("/api/v1/me")  # the client now carries the cookie
    assert me.status_code == 200 and me.json()["email"] == ADMIN


async def test_wrong_password_and_unknown_email_look_identical(http: httpx.AsyncClient) -> None:
    bad = await login(http, ADMIN, "nope")
    unknown = await login(http, "ghost@example.com", "nope")
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert SESSION_COOKIE not in bad.headers.get("set-cookie", "")


async def test_lockout_after_repeated_failures(http: httpx.AsyncClient) -> None:
    for _ in range(5):
        assert (await login(http, ADMIN, "nope")).status_code == 401
    assert (await login(http, ADMIN, ADMIN_PASSWORD)).status_code == 429


async def test_logout_clears_cookie(http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    res = await http.post("/api/v1/auth/logout")
    assert res.status_code == 204
    http.cookies.clear()  # the browser drops the cookie the server expired
    assert (await http.get("/api/v1/me")).status_code == 401


async def test_admin_creates_member_who_gets_member_role(pw_app: Any, http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    await create_user(http, "mia@example.com")
    async with new_client(pw_app) as mia:
        res = await login(mia, "mia@example.com", "member-password-1")
        assert res.json()["role"] == "member" and res.json()["is_admin"] is False


async def test_member_cannot_create_users_or_list_directory(pw_app: Any, http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    await create_user(http, "mia@example.com")
    async with new_client(pw_app) as mia:
        await login(mia, "mia@example.com", "member-password-1")
        body = {"email": "x@example.com", "name": "X", "password": "member-password-1"}
        assert (await mia.post("/api/v1/users", json=body)).status_code == 403
        assert (await mia.get("/api/v1/users")).status_code == 403


async def test_triager_grant_changes_role_on_next_request(pw_app: Any, http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    user = await create_user(http, "tess@example.com")
    async with new_client(pw_app) as tess:
        await login(tess, "tess@example.com", "member-password-1")
        await http.put(f"/api/v1/users/{user['id']}/role", json={"role": "triager"})
        assert (await tess.get("/api/v1/me")).json()["role"] == "triager"  # no re-login needed


async def test_duplicate_email_and_weak_password_rejected(http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    await create_user(http, "mia@example.com")
    dup = {"email": "MIA@example.com", "name": "Mia", "password": "member-password-1"}
    assert (await http.post("/api/v1/users", json=dup)).status_code == 409
    weak = {"email": "new@example.com", "name": "New", "password": "short"}
    assert (await http.post("/api/v1/users", json=weak)).status_code == 400


async def test_change_password(pw_app: Any, http: httpx.AsyncClient) -> None:
    await login(http, ADMIN, ADMIN_PASSWORD)
    await create_user(http, "mia@example.com")
    async with new_client(pw_app) as mia:
        await login(mia, "mia@example.com", "member-password-1")
        wrong = {"current_password": "bad", "new_password": "another-password-2"}
        assert (await mia.post("/api/v1/auth/password", json=wrong)).status_code == 401
        ok = {"current_password": "member-password-1", "new_password": "another-password-2"}
        assert (await mia.post("/api/v1/auth/password", json=ok)).status_code == 204
    async with new_client(pw_app) as again:
        assert (await login(again, "mia@example.com", "member-password-1")).status_code == 401
        assert (await login(again, "mia@example.com", "another-password-2")).status_code == 200


def forge(**overrides: Any) -> str:
    claims = {"sub": "x", "iss": "ticket-intake", "exp": int(time.time()) + 300, **overrides}
    return jwt.encode(claims, SECRET, algorithm="HS256")


async def test_forged_or_expired_tokens_rejected(http: httpx.AsyncClient) -> None:
    wrong_key = jwt.encode(
        {"sub": "x", "iss": "ticket-intake", "exp": int(time.time()) + 300}, "z" * 40, algorithm="HS256"
    )
    expired = forge(exp=int(time.time()) - 60)
    for token in (wrong_key, expired, "garbage"):
        res = await http.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 401


async def test_token_cannot_claim_a_role(pw_app: Any, http: httpx.AsyncClient) -> None:
    """A valid session for a member that also carries roles=['admin'] must still be a member."""
    await login(http, ADMIN, ADMIN_PASSWORD)
    await create_user(http, "mia@example.com")
    async with new_client(pw_app) as mia:
        await login(mia, "mia@example.com", "member-password-1")
        sub = (await mia.get("/api/v1/me")).json()["id"]
    token = forge(sub=sub, email="mia@example.com", roles=["admin"], role="admin")
    res = await http.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["role"] == "member"
