"""Liveness and readiness probes (unauthenticated)."""

from fastapi import APIRouter, Request, Response, status

from app.db.session import ping

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness: the process is up")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness: the database is reachable")
async def readyz(request: Request, response: Response) -> dict[str, str]:
    try:
        await ping(request.app.state.engine)
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ready"}
