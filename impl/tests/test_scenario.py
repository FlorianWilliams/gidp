"""The Appendix C.1 scenario, replayed as a test.

The example prints a transcript for a human; this replays the same exchange
and asserts the property the whole protocol exists for: **an Agent never
transmits a value classified `local`**, across a complete session, in any
object, in any field.

Note the shape of that claim, which the first version of this test got wrong
and which is worth stating precisely. The guarantee is *per sender*: it is not
that the string never appears on the wire, because a querent may name a
candidate value in a claim — asking "is `founder_operational` compatible?"
necessarily puts that string in the request. What the protocol guarantees is
that the *holder* of the value never sends it. See SPEC-ISSUES.md S-09.

A reviewer who reads nothing else should read this test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from cross_border import _in, a_interest, b_interest  # noqa: E402

from cid.agent import Agent  # noqa: E402
from cid.objects import Claim  # noqa: E402
from cid.transport import Wire  # noqa: E402
from cid.vocab import (  # noqa: E402
    ClaimOperator,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    IdentityStatus,
    SessionState,
    SessionStatus,
    Surface,
)


def _run() -> tuple[Agent, Agent, Wire]:
    wire = Wire()
    a = Agent(
        ref="agent:opaque:a",
        standing_interest=a_interest,
        pre_approved={"principal_name"},
    )
    b = Agent(
        ref="agent:opaque:b",
        standing_interest=b_interest,
        pre_approved={"principal_name"},
    )

    opened = wire.send("A", a.open_session("s-c1", purpose="strategic_transaction"))
    accept = wire.send("B", b.handle_session_open(opened))
    a.confirm_accept(accept)

    claims = [
        Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["germany"]),
        Claim(
            key="transaction_structures",
            operator=ClaimOperator.INTERSECTS,
            value=["majority_investment", "distribution"],
        ),
        Claim(key="market_access", operator=ClaimOperator.EQUALS, value="france"),
        Claim(
            key="valuation_class",
            operator=ClaimOperator.WITHIN,
            value={"min": 50_000_000, "max": 100_000_000},
        ),
        Claim(
            key="management_condition",
            operator=ClaimOperator.EQUALS,
            value="founder_operational",
        ),
    ]
    request = wire.send("A", a.ask(claims))
    response = wire.send("B", b.handle_compatibility_request(request))
    a.receive_compatibility_response(response)

    dreq = wire.send("B", b.request_disclosure("market_access", "confirm access"))
    dresp = wire.send("A", a.handle_disclosure_request(dreq))
    b.session.record_disclosure(dresp)

    b.session.qualify()
    assert a.session.qualify() is True
    opportunity = a.session.build_opportunity(
        structure="minority investment + distribution agreement",
        expires_at=_in(7),
        identity_status={
            "initiator": IdentityStatus.NOT_REQUESTED,
            "responder": IdentityStatus.NOT_REQUESTED,
        },
    )
    wire.send("A", opportunity)

    creq = wire.send(
        "A", a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
    )
    cresp = wire.send("B", b.handle_consent_request(creq))
    a.session.record_consent(cresp)
    b.session.record_consent(cresp, discharge=False)
    assert cresp.status is ConsentStatus.GRANTED

    handoff = wire.send("A", a.handoff("https://example.org/negotiation/v1"))
    b.session.record_handoff(handoff)
    a.session.close(CloseReason.COMPLETED)
    b.session.close(CloseReason.COMPLETED)
    return a, b, wire


def test_no_agent_transmits_its_own_evaluation_only_values():
    """The core claim of the protocol, tested across a whole session."""
    _, _, wire = _run()
    sent = {
        sender: json.dumps(
            [m.model_dump(mode="json") for s, m in wire.transcript if s == sender]
        )
        for sender in ("A", "B")
    }

    for sender, interest in (("A", a_interest), ("B", b_interest)):
        for key, value in interest.interest.conditions.items():
            if interest.class_of(key).surface is not Surface.LOCAL:
                continue
            for fragment in _fragments(value):
                assert fragment not in sent[sender], (
                    f"{sender} transmitted {key}={fragment!r}, which its own "
                    "Disclosure Policy classifies evaluation-only"
                )


def test_a_querent_may_name_a_value_the_holder_never_confirms():
    """The nuance the previous test rests on, made explicit.

    A asks whether `founder_operational` is compatible. That string is on the
    wire because A put it there. B answers `conditionally_compatible`, which
    asserts nothing, and never transmits its own value. A learns that its guess
    is not ruled out -- which is exactly the inference channel of Section 24.3.
    """
    _, _, wire = _run()
    asked = json.dumps(
        [m.model_dump(mode="json") for s, m in wire.transcript if s == "A"]
    )
    answered = json.dumps(
        [m.model_dump(mode="json") for s, m in wire.transcript if s == "B"]
    )
    assert "founder_operational" in asked
    assert "founder_operational" not in answered


def _fragments(value) -> list[str]:
    if isinstance(value, dict):
        return [str(v) for v in value.values()]
    return [str(value)]


def test_direction_is_never_stated():
    """Neither side says whether it is buying or selling."""
    _, _, wire = _run()
    on_the_wire = json.dumps(
        [message.model_dump(mode="json") for _, message in wire.transcript]
    ).lower()
    for word in (
        "acquire",
        "for_sale",
        "consider_strategic_transaction",
        "explore_strategic_transaction",
        "own_company",
    ):
        assert word not in on_the_wire


def test_the_session_qualifies_with_the_counts_of_appendix_c1():
    a, b, wire = _run()
    opportunity = next(m for _, m in wire.transcript if m.type == "Opportunity")
    assert opportunity.evaluated_dimensions == 5
    assert opportunity.compatible_dimensions == 3
    assert sorted(opportunity.open_conditions) == [
        "management_condition",
        "valuation_class",
    ]
    assert a.session.state is SessionState.CLOSED
    assert b.session.state is SessionState.CLOSED
    assert a.session.close_reason is CloseReason.COMPLETED
    assert wire.unanswered() == {}


def test_status_is_reported_consistently_by_both_sides():
    a, b, _ = _run()
    assert a.session.status() is SessionStatus.CLOSED
    assert b.session.status() is SessionStatus.CLOSED
