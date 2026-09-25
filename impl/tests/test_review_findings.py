"""Paths the first external review of the specification found unreachable,
contradictory or ambiguous (25 September 2026). SPEC-ISSUES.md S-22 to S-26.

Every test here was written before the fix it checks, and failed first. The
review read the specification without the code; these tests are the
translation of its findings into things the code either does or does not do.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_conformance import _interest, _pair  # noqa: E402

from gidp.agent import Agent  # noqa: E402
from gidp.evaluation import (  # noqa: E402
    LocalEvaluation,
    Truthfulness,
    assert_truthful,
    choose_result,
)
from gidp.objects import (  # noqa: E402
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
)
from gidp.session import ProtocolError  # noqa: E402
from gidp.vocab import (  # noqa: E402
    ClaimOperator,
    ClaimResult,
    ConsentAction,
    ConsentStatus,
    DisclosureStatus,
    Gate,
    SessionState,
    SessionStatus,
    Surface,
)


def _soon(minutes: int = 15):
    from datetime import UTC, datetime, timedelta
    return datetime.now(UTC) + timedelta(minutes=minutes)


def _never() -> DisclosureClass:
    from gidp.objects import NEVER
    return NEVER


def _exchange(asker: Agent, answerer: Agent, claims: list[Claim]):
    request = asker.ask(claims)
    response = answerer.handle_compatibility_request(request)
    asker.receive_compatibility_response(response, request)
    return response


def _qualify_both(a: Agent, b: Agent) -> None:
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    assert b.session.qualify() is True
    assert a.session.qualify() is True


# ---------------------------------------------------------------------------
# S-22 — consent and disclosure paths the state table could not represent
# ---------------------------------------------------------------------------


def _consent_gated_pair() -> tuple[Agent, Agent]:
    """B holds an attribute A must see before anything can qualify."""
    gated = _interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={"domain": ["enterprise_software"], "data_room": "vdr-7"},
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                "domain": DisclosureClass(surface=Surface.DISCOVERY),
                "data_room": DisclosureClass(surface=Surface.SESSION, gate=Gate.CONSENT),
            }
        ),
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=gated)
    opened = a.open_session("s-consent", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    return a, b


def test_consent_to_disclose_can_be_sought_before_qualification():
    """A `session/consent` attribute needed to qualify used to be a cycle:
    no disclosure without consent, no consent before qualification."""
    a, b = _consent_gated_pair()
    assert a.session.state is SessionState.PROBING

    consent = a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["data_room"])
    response = b.handle_consent_request(consent)
    assert response.status is ConsentStatus.GRANTED
    a.session.record_consent(response)
    b.session.record_consent(response, discharge=False)

    # A grant before qualification is a gate being opened, not a stage of the
    # session: both sides are back where they were.
    assert a.session.state is SessionState.PROBING
    assert b.session.state is SessionState.PROBING

    request = a.request_disclosure("data_room", purpose="qualify")
    disclosed = b.handle_disclosure_request(request)
    assert disclosed.status is DisclosureStatus.GRANTED
    assert disclosed.value == "vdr-7"
    a.session.record_disclosure(disclosed)
    assert a.session.state is SessionState.PROBING


def test_only_attribute_consent_may_precede_qualification():
    """Identity, contact and handoff stay after qualification (Section 5)."""
    a, _ = _consent_gated_pair()
    for action in (
        ConsentAction.REVEAL_IDENTITY,
        ConsentAction.ESTABLISH_DIRECT_CONTACT,
        ConsentAction.HANDOFF,
    ):
        with pytest.raises(ProtocolError, match="before qualification"):
            a.request_consent(action, ["identity"])


def test_a_disclosure_after_qualification_does_not_unqualify_the_session():
    """QUALIFIED + DisclosureRequest used to return to PROBING, from which
    no Handoff is reachable and no second Opportunity may be emitted."""
    a, b = _pair()
    _qualify_both(a, b)

    request = a.request_disclosure("open_attribute", purpose="prepare")
    response = b.handle_disclosure_request(request)
    a.session.record_disclosure(response)

    assert a.session.state is SessionState.QUALIFIED
    assert b.session.state is SessionState.QUALIFIED
    a.handoff("urn:example:negotiation")  # reachable
    assert a.session.state is SessionState.HANDED_OFF


def test_a_disclosure_after_consent_keeps_the_consent_in_force():
    a, b = _pair()
    _qualify_both(a, b)
    consent = a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["open_attribute"])
    granted = b.handle_consent_request(consent)
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    assert a.session.state is SessionState.CONSENTED

    request = a.request_disclosure("open_attribute", purpose="prepare")
    response = b.handle_disclosure_request(request)
    a.session.record_disclosure(response)
    assert a.session.state is SessionState.CONSENTED
    assert b.session.state is SessionState.CONSENTED


def test_a_conditional_grant_keeps_the_request_pending():
    """Section 14 calls granted_if_reciprocal provisional; the table used to
    send it back to PROBING and then describe its terminal answer from
    DISCLOSURE_PENDING, a state it had already left."""
    from gidp.objects import DisclosureResponse

    a, _ = _pair()
    request = a.request_disclosure("open_attribute", purpose="x")
    provisional = DisclosureResponse(
        session_id=a.session.session_id, request_ref=request.request_id,
        attribute="open_attribute", status=DisclosureStatus.GRANTED_IF_RECIPROCAL,
        expires_at=_soon(),
    )
    a.session.record_disclosure(provisional)
    assert a.session.state is SessionState.DISCLOSURE_PENDING
    assert request.request_id in a.session.open_requests


# ---------------------------------------------------------------------------
# S-23 — a mandatory output that the Disclosure Policy forbids
# ---------------------------------------------------------------------------


def _dependent_pair(conditional_on_class: DisclosureClass | None):
    attributes = {"domain": DisclosureClass(surface=Surface.DISCOVERY)}
    if conditional_on_class is not None:
        attributes["conditional_on"] = conditional_on_class
    follower = _interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={"domain": ["enterprise_software"]},
            conditional_on=["board_vote_on_divestment"],
        ),
        disclosure_policy=DisclosurePolicy(attributes=attributes),
    )
    a = Agent(ref="agent:a", standing_interest=follower)
    b = Agent(ref="agent:b", standing_interest=_interest())
    opened = a.open_session("s-dep", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    _qualify_both(a, b)
    return a.session.build_opportunity(
        structure="x", expires_at=_soon(), identity_status={}
    )


def test_an_evaluation_only_dependency_does_not_travel_in_the_opportunity():
    """The default class of an unlisted attribute is evaluation_only, and the
    dependency used to be copied verbatim into `contingent_on`."""
    opportunity = _dependent_pair(conditional_on_class=None)
    assert "board_vote_on_divestment" not in opportunity.model_dump_json()
    assert opportunity.contingent_on == ["undisclosed"], (
        "the Opportunity must still say it is contingent, without saying on what"
    )


def test_a_transmittable_dependency_travels_as_before():
    opportunity = _dependent_pair(DisclosureClass(surface=Surface.SESSION))
    assert opportunity.contingent_on == ["board_vote_on_divestment"]


def test_a_never_dependency_leaves_no_trace_at_all():
    """`never` MUST NOT be used to produce transmitted results, and a flag
    that exists only because of it is such a result."""
    opportunity = _dependent_pair(_never())
    assert opportunity.contingent_on == []
    assert "board_vote_on_divestment" not in opportunity.model_dump_json()


def test_a_never_attribute_is_declined_rather_than_evaluated():
    a, b = _pair()
    b.standing_interest.disclosure_policy.attributes["threshold"] = _never()
    response = _exchange(a, b, [Claim(key="threshold", operator=ClaimOperator.WITHIN,
                                      value={"min": 0, "max": 100})])
    assert response.results[0].result is ClaimResult.DECLINED


# ---------------------------------------------------------------------------
# S-24 — a result must identify the proposition, not only the dimension
# ---------------------------------------------------------------------------


def test_two_claims_on_one_key_are_two_propositions():
    """B's threshold is 0..80. The first claim is ruled out, the second is
    not; keyed by dimension, the second overwrote the first and qualified."""
    a, b = _pair()
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="nope")])
    _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="value")])
    assert a.session.status() is SessionStatus.INCOMPATIBLE


def test_two_claims_on_one_key_in_one_request_are_both_kept():
    a, b = _pair()
    response = _exchange(a, b, [
        Claim(key="open_attribute", operator=ClaimOperator.EQUALS, value="value"),
        Claim(key="open_attribute", operator=ClaimOperator.EQUALS, value="nope"),
    ])
    assert [o.result for o in response.results] == [
        ClaimResult.COMPATIBLE, ClaimResult.INCOMPATIBLE,
    ]
    assert len({o.claim_id for o in response.results}) == 2
    assert a.session.status() is SessionStatus.INCOMPATIBLE


def test_results_are_kept_per_direction():
    """B asks first and A declines; A then asks the same dimension and B
    answers compatible. A's view used to keep only the later answer."""
    a, b = _pair()
    request = b.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="value")])
    a.query_budget = 0  # A declines
    b.receive_compatibility_response(a.handle_compatibility_request(request), request)
    _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="value")])
    assert a.session.status() is SessionStatus.OPEN, (
        "a declined proposition in either direction prevents qualification"
    )


def test_a_claim_may_explicitly_supersede_an_earlier_one():
    """The case Section 15.2 describes: a requester that wants to qualify
    despite a refusal asks again, and says which claim it replaces."""
    a, b = _pair()
    b.query_budget = 0  # B declines the first question
    first = _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                                   value="value")])
    assert first.results[0].result is ClaimResult.DECLINED
    b.query_budget = 100
    withdrawn = first.results[0].claim_id
    _exchange(a, b, [
        Claim(key="domain", operator=ClaimOperator.INTERSECTS,
              value=["enterprise_software"]),
        Claim(key="open_attribute", operator=ClaimOperator.EQUALS, value="value",
              supersedes=[withdrawn]),
    ])
    assert a.session.status() is SessionStatus.POTENTIALLY_COMPATIBLE


def test_an_incompatible_result_cannot_be_superseded():
    """A known contradiction ends the session. Letting a requester withdraw
    one would make bisection (Section 24.3) a supported feature."""
    a, b = _pair()
    first = _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                                   value="nope")])
    with pytest.raises(ProtocolError, match="incompatible"):
        a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                     value="value", supersedes=[first.results[0].claim_id])])


def test_a_claim_may_only_supersede_its_own_side():
    a, b = _pair()
    request = b.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="nope")])
    response = a.handle_compatibility_request(request)
    b.receive_compatibility_response(response, request)
    theirs = response.results[0].claim_id
    with pytest.raises(ProtocolError, match="supersede"):
        a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                     value="value", supersedes=[theirs])])


# ---------------------------------------------------------------------------
# S-25 — a qualifying result issued over a local truth of `incompatible`
# ---------------------------------------------------------------------------


def test_conditionally_compatible_cannot_mask_an_incompatible_truth():
    ruled_out = LocalEvaluation(False, "threshold", True)
    assert choose_result(ruled_out, coarsen=True) is ClaimResult.UNKNOWN
    with pytest.raises(Truthfulness, match="conditionally_compatible"):
        assert_truthful(ruled_out, ClaimResult.CONDITIONALLY_COMPATIBLE)


def test_coarsening_a_true_answer_is_still_permitted():
    holds = LocalEvaluation(True, "threshold", True)
    assert choose_result(holds, coarsen=True) is ClaimResult.CONDITIONALLY_COMPATIBLE
    assert_truthful(holds, ClaimResult.CONDITIONALLY_COMPATIBLE)


def test_a_handoff_carries_the_contingency_forward_under_the_same_rule():
    """Section 14.6 required the Handoff to carry `contingent_on`; Section
    14.7 gave it no field to carry it in."""
    attributes = {"domain": DisclosureClass(surface=Surface.DISCOVERY)}
    follower = _interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={"domain": ["enterprise_software"]},
            conditional_on=["board_vote_on_divestment"],
        ),
        disclosure_policy=DisclosurePolicy(attributes=attributes),
    )
    a = Agent(ref="agent:a", standing_interest=follower)
    b = Agent(ref="agent:b", standing_interest=_interest())
    a.confirm_accept(b.handle_session_open(a.open_session("s-h", purpose="t")))
    _qualify_both(a, b)
    handoff = a.handoff("urn:example:negotiation")
    assert handoff.contingent_on == ["undisclosed"]
    assert "board_vote_on_divestment" not in handoff.model_dump_json()
