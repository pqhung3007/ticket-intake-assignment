"""Application factory.

`create_app()` wires settings, database, auth and routers. Dependencies can be injected
(engine, verifier) so tests run the real app against a test database and test keys.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.session import build_session_verifier
from app.auth.verifier import JwksKeyResolver, JwtVerifier, TokenVerifier
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.db.migrate import run_migrations
from app.db.session import create_engine, create_session_factory
from app.health.router import router as health_router
from app.tickets.router import router as tickets_router
from app.users.accounts_router import router as accounts_router
from app.users.router import router as users_router
from app.users.service import UserService
from app.users.throttle import LoginThrottle

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


def build_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_mode == "password":
        return build_session_verifier(settings)
    assert settings.n0_issuer  # guaranteed by Settings validation
    return JwtVerifier(
        issuer=settings.n0_issuer,
        audience=settings.jwt_audience,
        roles_claim=settings.roles_claim,
        key_resolver=JwksKeyResolver(settings.n0_issuer, settings.n0_jwks_url),
    )


def create_app(
    settings: Settings | None = None,
    *,
    engine: AsyncEngine | None = None,
    verifier: TokenVerifier | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_engine = engine is None
        app.state.engine = engine or create_engine(settings)
        app.state.session_factory = create_session_factory(app.state.engine)
        app.state.verifier = verifier or build_verifier(settings)
        if settings.run_migrations_on_startup:
            await run_migrations(app.state.engine)
        if settings.auth_mode == "password":
            async with app.state.session_factory() as session:
                await UserService(session, settings).bootstrap_admin()
        logger.info("startup complete", extra={"env": settings.env, "auth_mode": settings.auth_mode})
        try:
            yield
        finally:
            if owns_engine:
                await app.state.engine.dispose()

    app = FastAPI(
        title="Ticket Intake",
        version="1.0.0",
        description="Report bugs for workspace apps. Agents use create_ticket and list_tickets.",
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json",
    )
    app.state.settings = settings
    app.state.login_throttle = LoginThrottle()

    app.add_middleware(SecurityHeadersMiddleware, frame_ancestors=settings.frame_ancestors)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    if settings.auth_mode == "password":
        api.include_router(accounts_router)
    api.include_router(users_router)
    api.include_router(tickets_router)
    app.include_router(api)
    app.include_router(health_router)

    if settings.static_dir:
        _mount_spa(app, Path(settings.static_dir))
    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    """Serve the built React app; unknown non-API GETs fall back to index.html (client routing)."""
    index = static_dir / "index.html"
    if not index.is_file():
        logger.warning("static_dir has no index.html; web UI disabled", extra={"static_dir": str(static_dir)})
        return
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    def spa(path: str) -> FileResponse | JSONResponse:  # sync: runs in threadpool (file I/O)
        if path.startswith("api/"):
            return JSONResponse({"error": {"code": "not_found", "message": "Not found"}}, status_code=404)
        candidate = (static_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static_dir.resolve()):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
