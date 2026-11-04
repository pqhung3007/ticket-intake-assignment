import pytest

from app.auth.principal import Principal, Role
from app.core.errors import Forbidden
from app.tickets import policy
from app.tickets.constants import Status
from app.tickets.policy import Operation, TicketAccess

ALICE = Principal(user_id="alice", role=Role.MEMBER)
BOB = Principal(user_id="bob", role=Role.MEMBER)
TARA = Principal(user_id="tara", role=Role.TRIAGER)
ADAM = Principal(user_id="adam", role=Role.ADMIN)
ALICE_AGENT = Principal(user_id="alice", role=Role.MEMBER, agent_id="intake-agent")
TARA_AGENT = Principal(user_id="tara", role=Role.TRIAGER, agent_id="intake-agent")


def ticket(
    status: Status = Status.OPEN, *, confidential: bool = False, reporter: str = "alice"
) -> TicketAccess:
    return TicketAccess(reporter_id=reporter, status=status, confidential=confidential)


class TestVisibility:
    def test_public_ticket_visible_to_everyone(self) -> None:
        assert all(policy.can_view(p, ticket()) for p in (ALICE, BOB, TARA, ALICE_AGENT))

    @pytest.mark.parametrize(("who", "visible"), [(ALICE, True), (BOB, False), (TARA, True), (ADAM, True)])
    def test_confidential_only_reporter_and_triagers(self, who: Principal, visible: bool) -> None:
        assert policy.can_view(who, ticket(confidential=True)) is visible


class TestEditing:
    @pytest.mark.parametrize("status", [Status.OPEN, Status.IN_PROGRESS])
    def test_reporter_edits_while_active(self, status: Status) -> None:
        assert policy.can_edit_content(ALICE, ticket(status))

    @pytest.mark.parametrize("status", [Status.RESOLVED, Status.CLOSED])
    def test_reporter_cannot_edit_once_done(self, status: Status) -> None:
        assert not policy.can_edit_content(ALICE, ticket(status))

    def test_other_member_cannot_edit(self) -> None:
        assert not policy.can_edit_content(BOB, ticket())

    def test_triager_edits_anything(self) -> None:
        assert policy.can_edit_content(TARA, ticket(Status.CLOSED, reporter="bob"))

    def test_agent_never_edits_even_for_triager(self) -> None:
        assert not policy.can_edit_content(TARA_AGENT, ticket())


class TestTransitions:
    def test_reporter_can_only_withdraw_active_ticket(self) -> None:
        assert policy.allowed_transitions(ALICE, ticket(Status.OPEN)) == {Status.CLOSED}

    def test_reporter_can_reopen_done_ticket(self) -> None:
        assert policy.allowed_transitions(ALICE, ticket(Status.RESOLVED)) == {Status.OPEN}

    def test_other_member_has_no_transitions(self) -> None:
        assert policy.allowed_transitions(BOB, ticket()) == frozenset()

    def test_triager_any_transition_except_current(self) -> None:
        assert policy.allowed_transitions(TARA, ticket(Status.OPEN)) == set(Status) - {Status.OPEN}

    def test_agent_has_no_transitions(self) -> None:
        assert policy.allowed_transitions(TARA_AGENT, ticket()) == frozenset()


class TestOperations:
    @pytest.mark.parametrize("op", [Operation.LIST, Operation.GET, Operation.CREATE])
    def test_agent_allowed_operations(self, op: Operation) -> None:
        policy.ensure_operation_allowed(ALICE_AGENT, op)

    @pytest.mark.parametrize("op", [Operation.UPDATE, Operation.COMMENT])
    def test_agent_blocked_operations(self, op: Operation) -> None:
        with pytest.raises(Forbidden):
            policy.ensure_operation_allowed(TARA_AGENT, op)

    def test_scopes_enforced_when_present(self) -> None:
        read_only = Principal(user_id="alice", role=Role.MEMBER, scopes=frozenset({"tickets:read"}))
        policy.ensure_operation_allowed(read_only, Operation.LIST)
        with pytest.raises(Forbidden, match="tickets:write"):
            policy.ensure_operation_allowed(read_only, Operation.CREATE)

    def test_assign_is_triager_only(self) -> None:
        assert policy.can_assign(TARA) and policy.can_assign(ADAM)
        assert not policy.can_assign(ALICE)
        assert not policy.can_assign(TARA_AGENT)
