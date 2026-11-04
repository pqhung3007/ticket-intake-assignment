"""HTTP-level tests: the real app, real JWTs, real database, one test per access rule."""

from collections.abc import Callable
from typing import Any

import httpx

Auth = Callable[..., dict[str, str]]

REPORT = {"title": "CSV export times out", "target_app": "reports", "severity": "high"}


async def file_ticket(client: httpx.AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    res = await client.post("/api/v1/tickets", json={**REPORT, **overrides}, headers=headers)
    assert res.status_code == 201, res.text
    ticket: dict[str, Any] = res.json()["ticket"]
    return ticket


class TestAuthentication:
    async def test_no_token_is_401(self, client: httpx.AsyncClient) -> None:
        res = await client.get("/api/v1/tickets")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "unauthenticated"
        assert res.headers["www-authenticate"] == "Bearer"

    async def test_bad_token_is_401(self, client: httpx.AsyncClient) -> None:
        res = await client.get("/api/v1/tickets", headers={"Authorization": "Bearer nope"})
        assert res.status_code == 401

    async def test_me_reports_role(self, client: httpx.AsyncClient, auth: Auth) -> None:
        assert (await client.get("/api/v1/me", headers=auth("alice"))).json()["role"] == "member"
        assert (await client.get("/api/v1/me", headers=auth("tara"))).json()["role"] == "triager"
        me = (await client.get("/api/v1/me", headers=auth("adam"))).json()
        assert me["role"] == "admin" and me["is_triager"]

    async def test_unverified_admin_email_is_not_admin(self, client: httpx.AsyncClient, auth: Auth) -> None:
        res = await client.get("/api/v1/me", headers=auth("adam", email_verified=False))
        assert res.json()["role"] == "member"


class TestCreate:
    async def test_create_records_reporter_from_token(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        assert ticket["reporter"] == {"id": "u-alice", "name": "Alice", "email": "alice@example.com"}
        assert ticket["created_via"] == "ui"
        assert ticket["status"] == "open" and ticket["version"] == 1
        assert ticket["url"] == f"https://tickets.test/tickets/{ticket['number']}"

    async def test_forged_reporter_is_rejected(self, client: httpx.AsyncClient, auth: Auth) -> None:
        res = await client.post(
            "/api/v1/tickets",
            json={**REPORT, "reporter_id": "u-bob", "status": "closed"},
            headers=auth("alice"),
        )
        assert res.status_code == 400
        fields = {d["field"] for d in res.json()["error"]["details"]}
        assert fields == {"reporter_id", "status"}

    async def test_validation_errors_are_actionable(self, client: httpx.AsyncClient, auth: Auth) -> None:
        res = await client.post(
            "/api/v1/tickets", json={"title": "x", "severity": "urgent"}, headers=auth("alice")
        )
        assert res.status_code == 400
        error = res.json()["error"]
        assert error["code"] == "validation_error"
        assert {d["field"] for d in error["details"]} == {"title", "severity", "target_app"}

    async def test_retry_with_key_returns_200_and_same_ticket(
        self, client: httpx.AsyncClient, auth: Auth
    ) -> None:
        body = {**REPORT, "request_key": "chat-123"}
        first = await client.post("/api/v1/tickets", json=body, headers=auth("alice"))
        retry = await client.post("/api/v1/tickets", json=body, headers=auth("alice"))
        assert (first.status_code, retry.status_code) == (201, 200)
        assert retry.json()["deduplicated"] is True
        assert retry.json()["ticket"]["number"] == first.json()["ticket"]["number"]

    async def test_empty_optional_strings_accepted(self, client: httpx.AsyncClient, auth: Auth) -> None:
        # The N0 connector template sends '' for unset optional parameters.
        ticket = await file_ticket(client, auth("alice"), request_key="", environment="", description="")
        assert ticket["environment"] is None


class TestAgentAccess:
    async def test_agent_can_create_as_user(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice", agent="intake-agent"))
        assert ticket["reporter"]["id"] == "u-alice"
        assert ticket["created_via"] == "agent"
        assert ticket["created_by_agent"] == "intake-agent"

    async def test_agent_can_list(self, client: httpx.AsyncClient, auth: Auth) -> None:
        await file_ticket(client, auth("bob"))
        res = await client.get("/api/v1/tickets", headers=auth("alice", agent="intake-agent"))
        assert res.status_code == 200 and len(res.json()["items"]) == 1

    async def test_agent_cannot_update_even_for_triager(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        res = await client.patch(
            f"/api/v1/tickets/{ticket['number']}",
            json={"version": 1, "status": "closed"},
            headers=auth("tara", agent="intake-agent"),
        )
        assert res.status_code == 403

    async def test_agent_cannot_comment(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        res = await client.post(
            f"/api/v1/tickets/{ticket['number']}/comments",
            json={"body": "hi"},
            headers=auth("alice", agent="a"),
        )
        assert res.status_code == 403

    async def test_agent_cannot_reach_user_admin(self, client: httpx.AsyncClient, auth: Auth) -> None:
        assert (await client.get("/api/v1/users", headers=auth("adam", agent="a"))).status_code == 403

    async def test_agent_detail_shows_no_permissions(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        res = await client.get(f"/api/v1/tickets/{ticket['number']}", headers=auth("alice", agent="a"))
        assert res.json()["permissions"] == {
            "can_edit": False,
            "can_comment": False,
            "can_assign": False,
            "allowed_statuses": [],
        }


class TestConfidential:
    async def test_hidden_from_other_members(self, client: httpx.AsyncClient, auth: Auth) -> None:
        secret = await file_ticket(client, auth("alice"), title="Auth bypass on export", confidential=True)
        await file_ticket(client, auth("alice"), title="Public bug")

        bob_list = (await client.get("/api/v1/tickets", headers=auth("bob"))).json()["items"]
        assert [t["title"] for t in bob_list] == ["Public bug"]
        res = await client.get(f"/api/v1/tickets/{secret['number']}", headers=auth("bob"))
        assert res.status_code == 404  # not 403: existence is not leaked
        bob_stats = (await client.get("/api/v1/tickets/stats", headers=auth("bob"))).json()
        assert bob_stats["total"] == 1

    async def test_visible_to_reporter_and_triagers(self, client: httpx.AsyncClient, auth: Auth) -> None:
        secret = await file_ticket(client, auth("alice"), confidential=True)
        for user in ("alice", "tara", "adam"):
            res = await client.get(f"/api/v1/tickets/{secret['number']}", headers=auth(user))
            assert res.status_code == 200, user


class TestWorkflow:
    async def test_member_cannot_touch_others_ticket(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        url = f"/api/v1/tickets/{ticket['number']}"
        assert (
            await client.patch(url, json={"version": 1, "title": "Hijacked"}, headers=auth("bob"))
        ).status_code == 403
        assert (
            await client.patch(url, json={"version": 1, "status": "closed"}, headers=auth("bob"))
        ).status_code == 403

    async def test_reporter_can_withdraw_but_not_resolve(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        url = f"/api/v1/tickets/{ticket['number']}"
        assert (
            await client.patch(url, json={"version": 1, "status": "resolved"}, headers=auth("alice"))
        ).status_code == 403
        res = await client.patch(url, json={"version": 1, "status": "closed"}, headers=auth("alice"))
        assert res.status_code == 200 and res.json()["status"] == "closed"

    async def test_triager_assigns_and_resolves(self, client: httpx.AsyncClient, auth: Auth) -> None:
        await client.get("/api/v1/me", headers=auth("bob"))  # bob has used the app
        ticket = await file_ticket(client, auth("alice"))
        url = f"/api/v1/tickets/{ticket['number']}"
        res = await client.patch(
            url, json={"version": 1, "assignee_id": "u-bob", "status": "in_progress"}, headers=auth("tara")
        )
        assert res.status_code == 200, res.text
        assert res.json()["assignee"]["name"] == "Bob"
        res = await client.patch(url, json={"version": 2, "status": "resolved"}, headers=auth("tara"))
        assert res.json()["status"] == "resolved" and res.json()["resolved_at"] is not None

    async def test_assign_unknown_user_is_400(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        res = await client.patch(
            f"/api/v1/tickets/{ticket['number']}",
            json={"version": 1, "assignee_id": "ghost"},
            headers=auth("tara"),
        )
        assert res.status_code == 400

    async def test_stale_version_is_409(self, client: httpx.AsyncClient, auth: Auth) -> None:
        ticket = await file_ticket(client, auth("alice"))
        url = f"/api/v1/tickets/{ticket['number']}"
        await client.patch(url, json={"version": 1, "severity": "low"}, headers=auth("tara"))
        res = await client.patch(url, json={"version": 1, "severity": "critical"}, headers=auth("alice"))
        assert res.status_code == 409
        assert res.json()["error"]["details"] == {"current_version": 2}

    async def test_detail_includes_timeline_and_permissions(
        self, client: httpx.AsyncClient, auth: Auth
    ) -> None:
        ticket = await file_ticket(client, auth("alice"))
        url = f"/api/v1/tickets/{ticket['number']}"
        await client.post(f"{url}/comments", json={"body": "Still happening"}, headers=auth("bob"))
        detail = (await client.get(url, headers=auth("alice"))).json()
        assert [e["type"] for e in detail["events"]] == ["created", "comment"]
        assert detail["events"][1]["actor"]["name"] == "Bob"
        assert detail["permissions"] == {
            "can_edit": True,
            "can_comment": True,
            "can_assign": False,
            "allowed_statuses": ["closed"],
        }

    async def test_unknown_ticket_is_404(self, client: httpx.AsyncClient, auth: Auth) -> None:
        assert (await client.get("/api/v1/tickets/999", headers=auth("alice"))).status_code == 404


class TestListing:
    async def test_pagination_is_stable(self, client: httpx.AsyncClient, auth: Auth) -> None:
        for i in range(5):
            await file_ticket(client, auth("alice"), title=f"Bug number {i}")
        page1 = (await client.get("/api/v1/tickets?limit=2", headers=auth("bob"))).json()
        page2 = (
            await client.get(f"/api/v1/tickets?limit=2&cursor={page1['next_cursor']}", headers=auth("bob"))
        ).json()
        page3 = (
            await client.get(f"/api/v1/tickets?limit=2&cursor={page2['next_cursor']}", headers=auth("bob"))
        ).json()
        titles = [t["title"] for p in (page1, page2, page3) for t in p["items"]]
        assert titles == [f"Bug number {i}" for i in (4, 3, 2, 1, 0)]
        assert page3["next_cursor"] is None

    async def test_filters_and_search(self, client: httpx.AsyncClient, auth: Auth) -> None:
        await file_ticket(client, auth("alice"), title="Export to CSV fails", severity="critical")
        await file_ticket(client, auth("bob"), title="Typo on login page", target_app="auth", severity="low")
        h = auth("alice")
        assert len((await client.get("/api/v1/tickets?severity=critical", headers=h)).json()["items"]) == 1
        assert len((await client.get("/api/v1/tickets?target_app=AUTH", headers=h)).json()["items"]) == 1
        assert len((await client.get("/api/v1/tickets?reporter=me", headers=h)).json()["items"]) == 1
        assert len((await client.get("/api/v1/tickets?q=csv", headers=h)).json()["items"]) == 1
        # LIKE wildcards in search input are matched literally
        assert len((await client.get("/api/v1/tickets?q=%25", headers=h)).json()["items"]) == 0

    async def test_unknown_query_param_rejected(self, client: httpx.AsyncClient, auth: Auth) -> None:
        res = await client.get("/api/v1/tickets?reporter_id=u-bob", headers=auth("alice"))
        assert res.status_code == 400
