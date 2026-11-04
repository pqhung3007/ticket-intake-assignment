import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.verifier import JwtVerifier
from app.core.errors import Unauthenticated
from tests.conftest import TokenFactory


async def test_valid_token_yields_identity(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    identity = await verifier.verify(make_token("u1", email="a@x.io", name="A", roles=["Triager"]))
    assert identity.user_id == "u1"
    assert identity.email == "a@x.io"
    assert identity.platform_roles == {"triager"}
    assert identity.agent_id is None
    assert identity.scopes is None


async def test_agent_from_act_claim(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    identity = await verifier.verify(make_token("u1", agent="agent-7"))
    assert identity.user_id == "u1"  # the agent acts *as* the user
    assert identity.agent_id == "agent-7"


async def test_agent_from_flat_claim(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    identity = await verifier.verify(make_token("u1", agent_id="agent-9"))
    assert identity.agent_id == "agent-9"


async def test_scopes_parsed(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    identity = await verifier.verify(make_token("u1", scope="tickets:read tickets:write"))
    assert identity.scopes == {"tickets:read", "tickets:write"}


async def test_unverified_email_flagged(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    identity = await verifier.verify(make_token("u1", email="a@x.io", email_verified=False))
    assert identity.email_verified is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_in": -60},
        {"issuer": "https://evil.test"},
    ],
    ids=["expired", "wrong-issuer"],
)
async def test_rejected_tokens(
    verifier: JwtVerifier, make_token: TokenFactory, kwargs: dict[str, object]
) -> None:
    with pytest.raises(Unauthenticated, match="Invalid or expired token"):
        await verifier.verify(make_token("u1", **kwargs))


async def test_token_signed_by_other_key_rejected(verifier: JwtVerifier, make_token: TokenFactory) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(Unauthenticated):
        await verifier.verify(make_token("u1", key=other))


async def test_garbage_rejected(verifier: JwtVerifier) -> None:
    with pytest.raises(Unauthenticated):
        await verifier.verify("not-a-jwt")
