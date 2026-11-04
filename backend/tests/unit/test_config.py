import pytest
from pydantic import ValidationError

from app.core.config import Settings

DB = "postgresql://u:p@db:5432/app"


def test_database_url_uses_asyncpg_driver() -> None:
    s = Settings(database_url="postgres://u:p@db/app", auth_mode="dev")
    assert s.database_url == "postgresql+asyncpg://u:p@db/app"


def test_dev_auth_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE=dev is not allowed"):
        Settings(database_url=DB, env="production", auth_mode="dev")


def test_jwt_mode_requires_issuer() -> None:
    with pytest.raises(ValidationError, match="N0_ISSUER is required"):
        Settings(database_url=DB, auth_mode="jwt")


def test_admin_emails_from_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_EMAILS", " Adam@Example.com, ,eve@example.com ")
    s = Settings(database_url=DB, auth_mode="dev")
    assert s.admin_emails == ["adam@example.com", "eve@example.com"]


def test_issuer_trailing_slash_removed() -> None:
    s = Settings(database_url=DB, n0_issuer="https://n0.test/")
    assert s.n0_issuer == "https://n0.test"
