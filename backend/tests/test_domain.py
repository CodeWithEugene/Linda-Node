from datetime import datetime, timezone

from backend.app.domain import canonical, digest, transition


class Case:
    state = "ASSESSED"
    version = 1
    updated_at = datetime.now(timezone.utc)


def test_canonical_digest_is_key_order_independent():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    assert canonical({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_state_machine_rejects_illegal_transition():
    case = Case()
    try:
        transition(case, "APPROVED")
    except ValueError as exc:
        assert "illegal transition" in str(exc)
    else:
        raise AssertionError("illegal transition was accepted")
