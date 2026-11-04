import pytest
from pydantic import ValidationError

from app.core.config import INSECURE_LOCAL_SECRET, SESSION_COOKIE, Settings

DB = "postgresql://u:p@db:5432/app"


def test_database_url_uses_asyncpg_driver() -> None:
    s = Settings(database_url="postgres://u:p@db/app", n0_issuer="https://n0.test")
    assert s.database_url == "postgresql+asyncpg://u:p@db/app"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dev container sets these; tests must see only what they pass in."""
    for name in ("SESSION_SECRET", "BOOTSTRAP_ADMIN_PASSWORD", "ADMIN_EMAILS", "AUTH_MODE"):
        monkeypatch.delenv(name, raising=False)


def test_password_mode_requires_strong_secret() -> None:
    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings(database_url=DB, auth_mode="password")
    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings(database_url=DB, auth_mode="password", session_secret="short")


def test_local_session_secret_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="must be changed"):
        Settings(
            database_url=DB, env="production", auth_mode="password", session_secret=INSECURE_LOCAL_SECRET
        )


def test_password_mode_uses_session_cookie() -> None:
    s = Settings(database_url=DB, auth_mode="password", session_secret="x" * 32)
    assert s.auth_cookie_name == SESSION_COOKIE


def test_bootstrap_password_needs_admin_email() -> None:
    with pytest.raises(ValidationError, match="ADMIN_EMAILS"):
        Settings(database_url=DB, auth_mode="password", session_secret="x" * 32, bootstrap_admin_password="p")


def test_jwt_mode_requires_issuer() -> None:
    with pytest.raises(ValidationError, match="N0_ISSUER is required"):
        Settings(database_url=DB, auth_mode="jwt")


def test_admin_emails_from_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_EMAILS", " Adam@Example.com, ,eve@example.com ")
    s = Settings(database_url=DB, n0_issuer="https://n0.test")
    assert s.admin_emails == ["adam@example.com", "eve@example.com"]


def test_issuer_trailing_slash_removed() -> None:
    s = Settings(database_url=DB, n0_issuer="https://n0.test/")
    assert s.n0_issuer == "https://n0.test"
