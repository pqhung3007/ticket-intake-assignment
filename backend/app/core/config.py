"""Application settings, loaded from environment variables and validated at startup.

A misconfigured deployment should fail fast on boot rather than at the first request.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv(value: object) -> list[str]:
    if isinstance(value, str):
        return [part.strip().lower() for part in value.split(",") if part.strip()]
    if isinstance(value, list | tuple | set):
        return [str(part).strip().lower() for part in value if str(part).strip()]
    return []


CsvList = Annotated[list[str], NoDecode]

SESSION_COOKIE = "ti_session"
# Compose default for local use only; production refuses it.
INSECURE_LOCAL_SECRET = "local-dev-only-session-secret-do-not-use-in-production"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    port: int = 8000

    # --- Database (N0 App Data) ---
    database_url: str = Field(description="Postgres URL; driver is normalised to asyncpg")
    # App Data gives each app an isolated schema. When set, all tables live there.
    db_schema: str | None = None
    db_pool_size: int = Field(default=5, ge=1, le=50)
    run_migrations_on_startup: bool = True

    # --- Authentication ---
    # "jwt": identity comes only from a token signed by the platform (production).
    # "password": the app owns accounts; users sign in with email + password and get a session cookie.
    auth_mode: Literal["jwt", "password"] = "jwt"
    session_secret: str | None = None
    session_ttl_minutes: int = Field(default=480, ge=5, le=60 * 24 * 30)
    # Creates the first admin (first ADMIN_EMAILS entry) on startup if that account does not exist yet.
    bootstrap_admin_password: str | None = None
    n0_issuer: str | None = None
    n0_jwks_url: str | None = None
    jwt_audience: str | None = None
    # Extra places the platform may put the token besides `Authorization: Bearer`.
    auth_token_header: str | None = None
    auth_cookie_name: str | None = None
    roles_claim: str = "roles"

    # --- Authorization ---
    # Deploy-time admins. Admins are triagers and can grant/revoke the triager role.
    admin_emails: CsvList = Field(default_factory=list)
    admin_roles: CsvList = Field(default_factory=lambda: ["admin", "owner"])
    # Platform role names that make someone a triager (in addition to in-app grants).
    triager_roles: CsvList = Field(default_factory=lambda: ["triager"])

    # --- Web ---
    # Public base URL of the app (used for links returned to agents).
    public_base_url: str | None = None
    static_dir: str | None = None
    # Who may embed the UI in an iframe (the N0 workspace).
    frame_ancestors: str = "'self' https://*.nzero.pro"

    @field_validator("admin_emails", "admin_roles", "triager_roles", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> list[str]:
        return _csv(value)

    @field_validator("database_url")
    @classmethod
    def _asyncpg_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def _check_auth(self) -> "Settings":
        if self.auth_mode == "password":
            if not self.session_secret or len(self.session_secret) < 32:
                raise ValueError("SESSION_SECRET (32+ characters) is required when AUTH_MODE=password")
            if self.env == "production" and self.session_secret == INSECURE_LOCAL_SECRET:
                raise ValueError("SESSION_SECRET must be changed when ENV=production")
            self.auth_cookie_name = self.auth_cookie_name or SESSION_COOKIE
            if self.bootstrap_admin_password and not self.admin_emails:
                raise ValueError("BOOTSTRAP_ADMIN_PASSWORD needs at least one ADMIN_EMAILS entry")
        if self.auth_mode == "jwt" and not self.n0_issuer:
            raise ValueError("N0_ISSUER is required when AUTH_MODE=jwt")
        if self.n0_issuer:
            self.n0_issuer = self.n0_issuer.rstrip("/")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
