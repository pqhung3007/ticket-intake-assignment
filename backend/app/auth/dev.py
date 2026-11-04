"""Development-only identities, so the app can run locally without the N0 platform.

Token format: `dev:<user>` or `dev:<user>:agent:<agent-id>` (to simulate an agent call).
Settings refuse AUTH_MODE=dev when ENV=production.
"""

from app.auth.principal import Identity
from app.core.errors import Unauthenticated

DEV_USERS: dict[str, Identity] = {
    "alice": Identity(user_id="dev-alice", email="alice@example.com", name="Alice Member"),
    "bob": Identity(user_id="dev-bob", email="bob@example.com", name="Bob Member"),
    "tara": Identity(
        user_id="dev-tara",
        email="tara@example.com",
        name="Tara Triager",
        platform_roles=frozenset({"triager"}),
    ),
    "adam": Identity(
        user_id="dev-adam", email="adam@example.com", name="Adam Admin", platform_roles=frozenset({"admin"})
    ),
}


class DevVerifier:
    async def verify(self, token: str) -> Identity:
        parts = token.split(":")
        if len(parts) not in (2, 4) or parts[0] != "dev" or parts[1] not in DEV_USERS:
            raise Unauthenticated("Unknown dev identity")
        base = DEV_USERS[parts[1]]
        if len(parts) == 4:
            if parts[2] != "agent" or not parts[3]:
                raise Unauthenticated("Malformed dev agent token")
            return Identity(
                user_id=base.user_id,
                email=base.email,
                name=base.name,
                platform_roles=base.platform_roles,
                agent_id=parts[3],
            )
        return base
