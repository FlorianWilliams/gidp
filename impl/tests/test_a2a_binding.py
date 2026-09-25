"""Section 22.2 against the published A2A mechanism, not against memory.

The binding is a sketch in the specification and non-normative here too.
What these tests protect is narrower and worth protecting: that the sketch
matches the four fields A2A actually defines, that it does not skip the
activation round trip, and that every GIDP object can in fact be carried.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp.bindings.a2a import (
    ACTIVATION_HEADER,
    EXTENSION_URI,
    OBJECT_KEY,
    BindingError,
    activation_header,
    agent_card_capabilities,
    agent_extension,
    echo_activation,
    from_message,
    is_active,
    parse_activation,
    to_message,
)
from gidp.objects import SessionClose
from gidp.vocab import CloseReason

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))


def _soon():
    return datetime.now(UTC) + timedelta(minutes=10)


# -- declaration ------------------------------------------------------------


def test_the_declaration_uses_the_four_fields_a2a_defines():
    entry = agent_extension(params={"profiles": ["core"]})
    assert set(entry) == {"uri", "description", "required", "params"}
    assert entry["uri"] == EXTENSION_URI


def test_params_is_omitted_rather_than_null_when_unused():
    assert "params" not in agent_extension()


def test_the_extension_is_never_declared_required():
    """An agent that made GIDP mandatory would refuse every plain A2A peer."""
    assert agent_card_capabilities()["extensions"][0]["required"] is False


# -- activation -------------------------------------------------------------


def test_declaration_is_not_activation():
    """The step the specification's sketch omitted entirely."""
    assert echo_activation({}) == {}
    assert not is_active({})


def test_a_client_that_activates_gets_an_echo():
    response = echo_activation(activation_header())
    assert is_active(response)


def test_the_header_is_read_case_insensitively():
    assert parse_activation({"a2a-extensions": EXTENSION_URI}) == [EXTENSION_URI]
    assert parse_activation({ACTIVATION_HEADER: EXTENSION_URI}) == [EXTENSION_URI]


def test_a_peer_may_activate_some_extensions_and_not_this_one():
    headers = {ACTIVATION_HEADER: "https://example.org/other/v1"}
    assert echo_activation(headers) == {}


# -- carriage ---------------------------------------------------------------


def test_a_cid_object_round_trips_through_an_a2a_message():
    close = SessionClose(
        session_id="s-1", reason=CloseReason.COMPLETED, expires_at=_soon()
    )
    message = to_message(close)
    assert OBJECT_KEY in message["metadata"]
    assert message["parts"] == []
    assert from_message(message) == close


def test_every_object_of_a_real_session_round_trips():
    """Not one object: everything a real session puts on the wire."""
    import co_investment

    _, _, wire = co_investment.run(verbose=False)
    sent = [message for _sender, message in wire.transcript]
    assert sent, "the wire recorded nothing; the test would pass vacuously"
    kinds = {type(message).__name__ for message in sent}
    assert len(kinds) >= 6, f"only {kinds} exercised; the test proves little"
    for obj in sent:
        assert from_message(to_message(obj)) == obj


def test_a_message_without_the_extension_key_is_refused():
    with pytest.raises(BindingError):
        from_message({"role": "agent", "parts": [], "metadata": {}})


def test_an_unknown_object_type_is_refused():
    with pytest.raises(BindingError):
        from_message({"metadata": {OBJECT_KEY: {"type": "NotACidObject"}}})


# -- the two handshakes -----------------------------------------------------


def test_activating_the_extension_says_nothing_about_cid_features():
    """Two negotiations, and the second is not derivable from the first.

    A2A activation answers *do you speak GIDP*. Section 14.1 answers *which
    optional GIDP features are in force*. A peer may activate and still
    support no optional feature at all.
    """
    from baselines.scenario import b_interest
    from gidp.agent import Agent
    from gidp.vocab import Feature

    assert is_active(echo_activation(activation_header()))

    initiator = Agent(ref="agent:opaque:a", standing_interest=b_interest())
    responder = Agent(
        ref="agent:opaque:b", standing_interest=b_interest(), supported_features=set()
    )
    opened = initiator.open_session(
        "s", purpose="test", features=[Feature.DEPENDENCY_PRIMITIVES]
    )
    accept = responder.handle_session_open(opened)
    assert Feature.DEPENDENCY_PRIMITIVES in (opened.features or [])
    assert Feature.DEPENDENCY_PRIMITIVES not in (accept.features or [])
