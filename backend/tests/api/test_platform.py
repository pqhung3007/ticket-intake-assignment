"""Health probes, error shape, headers and SPA serving."""

from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.verifier import JwtVerifier
from app.core.config import Settings
from app.main import create_app


async def test_health_endpoints(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).json() == {"status": "ok"}
    assert (await client.get("/readyz")).json() == {"status": "ready"}


async def test_security_and_request_id_headers(client: httpx.AsyncClient) -> None:
    res = await client.get("/healthz", headers={"X-Request-Id": "abc-123"})
    assert res.headers["x-request-id"] == "abc-123"
    assert res.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors" in res.headers["content-security-policy"]


async def test_malicious_request_id_replaced(client: httpx.AsyncClient) -> None:
    res = await client.get("/healthz", headers={"X-Request-Id": "evil\tlog-injection"})
    assert res.headers["x-request-id"] != "evil\tlog-injection"


async def test_unknown_api_route_is_json_404(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/v1/nope")
    assert res.status_code == 404 and res.json()["error"]["code"] == "not_found"


async def test_openapi_exposes_tool_operations(client: httpx.AsyncClient) -> None:
    spec = (await client.get("/api/v1/openapi.json")).json()
    op_ids = {op["operationId"] for path in spec["paths"].values() for op in path.values()}
    assert {"create_ticket", "list_tickets"} <= op_ids


@pytest.fixture
def spa_dir(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    (tmp_path / "index.html").write_text("<!doctype html><div id=root></div>")
    return tmp_path


async def test_spa_fallback_and_assets(
    settings: Settings, spa_dir: Path, engine: AsyncEngine, verifier: JwtVerifier
) -> None:
    app = create_app(
        settings.model_copy(update={"static_dir": str(spa_dir)}), engine=engine, verifier=verifier
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        assert "id=root" in (await c.get("/tickets/42")).text  # client-side route
        assert (await c.get("/assets/app.js")).status_code == 200
        assert "root:" not in (await c.get("/..%2F..%2Fetc%2Fpasswd")).text
        assert (await c.get("/api/v1/unknown")).status_code in (401, 404)
