"""Checks the wire enforces the correlation rules of Section 14."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cid.agent import Agent
from cid.objects import Claim, SessionClose
from cid.transport import Wire, WireError
from cid.vocab import ClaimOperator, CloseReason, DisclosureStatus

from test_conformance import _interest, _soon  # noqa: E402


def _wired() -> tuple[Agent, Agent, Wire]:
    wire = Wire()
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_interest())
    opened = wire.send("A", a.open_session("s-w", purpose="test"))
    accept = wire.send("B", b.handle_session_open(opened))
    a.confirm_accept(accept)
    return a, b, wire


def test_a_conforming_exchange_leaves_nothing_outstanding():
    a, b, wire = _wired()
    request = wire.send(
        "A",
        a.ask([Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                     value=["enterprise_software"])]),
    )
    response = wire.send("B", b.handle_compatibility_request(request))
    a.receive_compatibility_response(response)
    assert wire.unanswered() == {}
    assert "CompatibilityResponse" in wire.render()


def test_a_provisional_response_does_not_discharge_the_request():
    """Section 14: pending_principal_approval is provisional."""
    a, b, wire = _wired()
    request = wire.send("A", a.request_disclosure("identity", "introduce"))
    response = wire.send("B", b.handle_disclosure_request(request))
    assert response.status is DisclosureStatus.PENDING_PRINCIPAL_APPROVAL
    assert request.request_id in wire.unanswered()


def test_answering_an_unknown_request_is_rejected():
    a, b, wire = _wired()
    request = a.ask([Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["x"])])  # never put on the wire
    response = b.handle_compatibility_request(request)
    with pytest.raises(WireError):
        wire.send("B", response)


def test_a_close_in_place_of_a_response_discharges_the_request():
    a, b, wire = _wired()
    request = wire.send("A", a.request_disclosure("open_attribute", "test"))
    wire.send(
        "B",
        SessionClose(
            session_id="s-w",
            reason=CloseReason.UNSPECIFIED,
            request_ref=request.request_id,
            expires_at=_soon(),
        ),
    )
    assert wire.unanswered() == {}
