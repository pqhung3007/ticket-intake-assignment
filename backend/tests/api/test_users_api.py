from collections.abc import Callable

import httpx

Auth = Callable[..., dict[str, str]]


async def visit(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    assert (await client.get("/api/v1/me", headers=headers)).status_code == 200


async def test_admin_grants_and_revokes_triager(client: httpx.AsyncClient, auth: Auth) -> None:
    await visit(client, auth("bob"))
    res = await client.put("/api/v1/users/u-bob/role", json={"role": "triager"}, headers=auth("adam"))
    assert res.status_code == 200 and res.json()["role"] == "triager"
    assert (await client.get("/api/v1/me", headers=auth("bob"))).json()["role"] == "triager"

    await client.put("/api/v1/users/u-bob/role", json={"role": "member"}, headers=auth("adam"))
    assert (await client.get("/api/v1/me", headers=auth("bob"))).json()["role"] == "member"


async def test_triager_cannot_grant_roles(client: httpx.AsyncClient, auth: Auth) -> None:
    await visit(client, auth("bob"))
    res = await client.put("/api/v1/users/u-bob/role", json={"role": "triager"}, headers=auth("tara"))
    assert res.status_code == 403


async def test_config_admin_role_is_immutable(client: httpx.AsyncClient, auth: Auth) -> None:
    await visit(client, auth("adam"))
    res = await client.put("/api/v1/users/u-adam/role", json={"role": "member"}, headers=auth("adam"))
    assert res.status_code == 409


async def test_grant_to_unknown_user_is_404(client: httpx.AsyncClient, auth: Auth) -> None:
    res = await client.put("/api/v1/users/ghost/role", json={"role": "triager"}, headers=auth("adam"))
    assert res.status_code == 404


async def test_user_directory_is_triager_only(client: httpx.AsyncClient, auth: Auth) -> None:
    await visit(client, auth("alice"))
    await visit(client, auth("bob"))
    assert (await client.get("/api/v1/users", headers=auth("alice"))).status_code == 403
    res = await client.get("/api/v1/users?q=bo", headers=auth("tara"))
    assert [u["name"] for u in res.json()["items"]] == ["Bob"]
