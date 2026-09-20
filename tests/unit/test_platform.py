"""Unit tests for platform utilities."""

from relay.platform.ids import generate_id, validate_id_prefix


def test_generate_prefixed_ulids() -> None:
    run_id = generate_id("run")
    assert run_id.startswith("run_")
    assert validate_id_prefix(run_id, "run")

    msg_id = generate_id("message")
    assert msg_id.startswith("msg_")
    assert validate_id_prefix(msg_id, "message")

    tkt_id = generate_id("ticket")
    assert tkt_id.startswith("tkt_")
    assert validate_id_prefix(tkt_id, "ticket")
