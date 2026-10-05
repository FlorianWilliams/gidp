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


def _grant_handoff(a: Agent, b: Agent, target: str) -> None:
    request = a.request_consent(ConsentAction.HANDOFF, [target])
    response = b.handle_consent_request(request)
    if response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
        response = b.principal_answers_consent(request, granted=True)
    a.record_consent(response)
    b.session.record_consent(response, discharge=False)


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

    # A grant before qualification opens a gate and is not a stage of the
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
    _grant_handoff(a, b, "urn:example:negotiation")
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
    response = _exchange(a, b, [Claim(key="threshold", operator=ClaimOperator.OVERLAPS,
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
    _grant_handoff(a, b, "urn:example:negotiation")
    handoff = a.handoff("urn:example:negotiation")
    assert handoff.contingent_on == ["undisclosed"]
    assert "board_vote_on_divestment" not in handoff.model_dump_json()


# ---------------------------------------------------------------------------
# Second review (28 September 2026) -- SPEC-ISSUES.md S-27 to S-32
# ---------------------------------------------------------------------------


def _responder_dependent_pair(conditional_on_class: DisclosureClass | None):
    """The reviewer's case: the *responder* holds the dependency.

    The initiator builds the Opportunity from its own session view; before
    Section 14.3 carried `contingent_on`, nothing told it the responder's
    evaluation was contingent, and the responder received an Opportunity
    that did not match its own evaluation.
    """
    attributes = {"domain": DisclosureClass(surface=Surface.DISCOVERY)}
    if conditional_on_class is not None:
        attributes["conditional_on"] = conditional_on_class
    follower = _interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={"domain": ["enterprise_software"]},
            conditional_on=["anchor_investor_commitment"],
        ),
        disclosure_policy=DisclosurePolicy(attributes=attributes),
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=follower)
    opened = a.open_session("s-resp-dep", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    response = _exchange(
        a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                     value=["enterprise_software"])]
    )
    assert b.session.qualify() is True
    assert a.session.qualify() is True
    opportunity = a.session.build_opportunity(
        structure="x", expires_at=_soon(), identity_status={}
    )
    return response, opportunity


def test_a_responders_withheld_dependency_reaches_the_opportunity():
    """S-32: B's evaluation_only dependency, unknown to A, must still mark
    the Opportunity as contingent, as `undisclosed`, never by name."""
    response, opportunity = _responder_dependent_pair(None)
    assert response.contingent_on == ["undisclosed"]
    assert opportunity.contingent_on == ["undisclosed"]
    assert "anchor_investor_commitment" not in opportunity.model_dump_json()


def test_a_responders_transmittable_dependency_travels_by_name():
    response, opportunity = _responder_dependent_pair(
        DisclosureClass(surface=Surface.SESSION)
    )
    assert response.contingent_on == ["anchor_investor_commitment"]
    assert opportunity.contingent_on == ["anchor_investor_commitment"]


def test_a_responders_never_dependency_leaves_no_trace():
    response, opportunity = _responder_dependent_pair(_never())
    assert response.contingent_on == []
    assert opportunity.contingent_on == []
    assert "anchor_investor_commitment" not in opportunity.model_dump_json()


def test_consent_under_a_false_authority_is_declined_not_pending():
    """S-28: a refused authority is a refusal. `pending_principal_approval`
    would tell the counterparty to wait for a decision nobody will make."""
    from gidp.objects import AuthoritySpec
    from gidp.vocab import Authority, AuthorityValue

    no_introduce = _interest(
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
                # INTRODUCE unset: defaults to FALSE (Section 16.1)
            }
        )
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=no_introduce)
    opened = a.open_session("s-auth-false", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    _qualify_both(a, b)
    request = a.request_consent(ConsentAction.REVEAL_IDENTITY, scope=["identity"])
    response = b.handle_consent_request(request)
    assert response.status is ConsentStatus.DECLINED
    assert response.granted_scope == []


def test_an_approval_required_authority_still_answers_pending():
    """The other branch of Section 14.5 is unchanged by S-28."""
    from gidp.objects import AuthoritySpec
    from gidp.vocab import Authority, AuthorityValue

    approval = _interest(
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
                Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
            }
        )
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=approval)
    opened = a.open_session("s-auth-appr", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    _qualify_both(a, b)
    request = a.request_consent(ConsentAction.REVEAL_IDENTITY, scope=["identity"])
    response = b.handle_consent_request(request)
    assert response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL


def test_probing_after_qualification_does_not_revise_the_opportunity():
    """S-31: the Opportunity is the evaluation at the moment of the
    transition. A later non-qualifying result leaves the session QUALIFIED
    and produces no second Opportunity; re-evaluation is a new session."""
    a, b = _pair()
    _qualify_both(a, b)
    opportunity = a.session.build_opportunity(
        structure="x", expires_at=_soon(), identity_status={}
    )
    # A later claim on a value B does not hold qualifies nothing.
    response = _exchange(
        a, b, [Claim(key="jurisdiction", operator=ClaimOperator.INTERSECTS,
                     value=["antarctica"])]
    )
    assert response.results[0].result is not ClaimResult.COMPATIBLE
    assert a.session.state is SessionState.QUALIFIED
    assert b.session.state is SessionState.QUALIFIED
    assert a.session.qualify() is False, "qualification is reached at most once"
    assert b.session.qualify() is False
    again = a.session.build_opportunity(
        structure="x", expires_at=_soon(), identity_status={}
    )
    assert again.evaluated_dimensions >= opportunity.evaluated_dimensions
    # The emitted Opportunity is the one built at the transition; the session
    # keeps recording, but nothing re-emits (qualify() gates emission).


def test_a_compatibility_response_may_be_received_from_qualified():
    """S-31: the spec table lacked the line; the machine must accept it."""
    a, b = _pair()
    _qualify_both(a, b)
    request = a.ask([Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    response = b.handle_compatibility_request(request)
    a.receive_compatibility_response(response, request)  # must not raise
    assert a.session.state is SessionState.QUALIFIED


# ---------------------------------------------------------------------------
# Third round: second reviewer's fresh reading (28 September 2026),
# SPEC-ISSUES.md S-33 to S-38
# ---------------------------------------------------------------------------


def _identity_pair(gate: Gate = Gate.CONSENT) -> tuple[Agent, Agent]:
    """B holds `principal_identity` at surface session, under `gate`."""
    holder = _interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={
                "domain": ["enterprise_software"],
                "principal_identity": "Acme GmbH",
            },
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                "domain": DisclosureClass(surface=Surface.DISCOVERY),
                "principal_identity": DisclosureClass(
                    surface=Surface.SESSION, gate=gate
                ),
            }
        ),
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=holder)
    opened = a.open_session("s-identity", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    return a, b


def test_identity_cannot_ride_disclose_attributes_before_qualification():
    """S-33: `disclose_attributes` MAY precede qualification and is gated on
    DISCLOSE; a scope smuggling `principal_identity` through it would do,
    before qualification, what `reveal_identity` holds until after it."""
    a, b = _identity_pair()
    request = a.request_consent(
        ConsentAction.DISCLOSE_ATTRIBUTES, scope=["principal_identity"]
    )
    response = b.handle_consent_request(request)
    assert response.status is ConsentStatus.DECLINED
    assert response.granted_scope == []


def test_a_disclosure_request_on_identity_is_declined_without_reveal_consent():
    """S-33: the rule attaches to the data, whatever the message. The class
    here is `session` with no gate, the reviewer's sharpest case, in which
    nothing but the identity rule itself stands between the request and the
    value."""
    a, b = _identity_pair(gate=Gate.NONE)
    _qualify_both(a, b)
    request = a.request_disclosure("principal_identity", purpose="handoff")
    response = b.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.DECLINED
    assert "Acme" not in response.model_dump_json()


def test_identity_travels_after_a_reveal_identity_consent():
    """The counterpart: the same disclosure succeeds under the right action."""
    a, b = _identity_pair()
    _qualify_both(a, b)
    consent = a.request_consent(
        ConsentAction.REVEAL_IDENTITY, scope=["principal_identity"]
    )
    granted = b.handle_consent_request(consent)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    request = a.request_disclosure("principal_identity", purpose="handoff")
    response = b.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.GRANTED


def test_qualification_reached_while_a_disclosure_is_pending_defers():
    """S-34: the qualifying result can arrive during DISCLOSURE_PENDING; the
    transition neither fires there nor lapses; it fires on the return to
    PROBING."""
    a, b = _pair()
    # A disclosure request is outstanding...
    request = a.request_disclosure("open_attribute", purpose="qualify")
    assert a.session.state is SessionState.DISCLOSURE_PENDING
    # ...when the qualifying exchange completes.
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    # Section 17.2: while the request is pending, the status is not yet
    # reported qualifying; it is recomputed on the return to PROBING.
    assert a.session.status() is SessionStatus.OPEN
    assert a.session.qualify() is False, "must not fire while pending"
    assert a.session.state is SessionState.DISCLOSURE_PENDING
    # The terminal response returns the session to PROBING...
    response = b.handle_disclosure_request(request)
    a.session.record_disclosure(response)
    assert a.session.state is SessionState.PROBING
    # ...where the transition fires, once.
    assert a.session.qualify() is True
    assert a.session.state is SessionState.QUALIFIED
    assert a.session.qualify() is False


def test_a_result_arriving_during_the_wait_counts_at_the_return():
    """The reviewer's sequence: qualifying at step 2, `unknown` at
    step 3 during the same wait. The session must NOT qualify at step 4,
    because the conditions are recomputed over the propositions then
    standing instead of being remembered from mid-wait."""
    a, b = _pair()
    request = a.request_disclosure("open_attribute", purpose="qualify")
    # Step 2: a qualifying exchange completes during the wait.
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    # Step 3: during the same wait, a further claim resolves unknown.
    unresolved = _exchange(
        a, b, [Claim(key="jurisdiction", operator=ClaimOperator.INTERSECTS,
                     value=["antarctica"])]
    )
    assert unresolved.results[0].result is ClaimResult.UNKNOWN
    # Step 4: the terminal response returns the session to PROBING.
    response = b.handle_disclosure_request(request)
    a.session.record_disclosure(response)
    assert a.session.state is SessionState.PROBING
    assert a.session.status() is SessionStatus.OPEN
    assert a.session.qualify() is False, (
        "an unresolved proposition standing at the return prevents "
        "qualification (Sections 15.2, 17.2)"
    )


def test_status_is_kept_after_qualification():
    """S-35, now in the code as well as the text: a later `unknown` does
    not drop `session_status` back to `open`."""
    a, b = _pair()
    _qualify_both(a, b)
    _exchange(a, b, [Claim(key="jurisdiction", operator=ClaimOperator.INTERSECTS,
                           value=["antarctica"])])
    assert a.session.status() is SessionStatus.POTENTIALLY_COMPATIBLE
    assert b.session.status() is SessionStatus.POTENTIALLY_COMPATIBLE


def test_an_identity_claim_is_declined_without_reveal_consent():
    """S-48: `compatible` to `principal_identity equals X` confirms the
    identity without any DisclosureResponse carrying it."""
    a, b = _identity_pair(gate=Gate.NONE)
    response = _exchange(
        a, b, [Claim(key="principal_identity", operator=ClaimOperator.EQUALS,
                     value="Acme GmbH")]
    )
    assert response.results[0].result is ClaimResult.DECLINED


def test_an_identity_claim_is_answerable_after_reveal_consent():
    a, b = _identity_pair(gate=Gate.NONE)
    _qualify_both(a, b)
    consent = a.request_consent(
        ConsentAction.REVEAL_IDENTITY, scope=["principal_identity"]
    )
    granted = b.handle_consent_request(consent)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    response = _exchange(
        a, b, [Claim(key="principal_identity", operator=ClaimOperator.EQUALS,
                     value="Acme GmbH")]
    )
    assert response.results[0].result is ClaimResult.COMPATIBLE


# ---------------------------------------------------------------------------
# Fresh reviewer, second reading (28 September 2026) -- S-49 to S-55
# ---------------------------------------------------------------------------


def test_a_profile_requirement_blocks_qualification_until_examined():
    """S-49 (trace 1): a profile requiring role and location blocks the
    transition after a compatible answer on role alone."""
    a, b = _pair()
    a.session.required_dimensions = {"domain", "jurisdiction"}
    b.session.required_dimensions = {"domain", "jurisdiction"}
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    assert a.session.status() is SessionStatus.OPEN
    assert a.session.qualify() is False, (
        "a required dimension nobody examined blocks qualification (15.2)"
    )


def test_an_incompatible_during_a_wait_is_not_held_back():
    """S-50 (trace 3): the narrow `open` rule does not delay a known
    contradiction -- `incompatible` overrides mid-wait."""
    a, b = _pair()
    a.request_disclosure("open_attribute", purpose="qualify")
    assert a.session.state is SessionState.DISCLOSURE_PENDING
    response = _exchange(
        a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                     value=["something_else_entirely"])]
    )
    assert response.results[0].result is ClaimResult.INCOMPATIBLE
    assert a.session.status() is SessionStatus.INCOMPATIBLE, (
        "an incompatible recorded during a wait is reported at once (17.2)"
    )


def test_the_kept_status_survives_a_pending_consent():
    """S-50 (trace 2): QUALIFIED -> CONSENT_PENDING is the normal path and
    does not drop the kept status back to open."""
    a, b = _pair()
    _qualify_both(a, b)
    a.request_consent(ConsentAction.REVEAL_IDENTITY, scope=["identity"])
    assert a.session.state is SessionState.CONSENT_PENDING
    assert a.session.status() is SessionStatus.POTENTIALLY_COMPATIBLE


# ---------------------------------------------------------------------------
# Fresh reviewer, third reading points applied same day: S-56 to S-58
# ---------------------------------------------------------------------------


def test_the_initiator_does_not_emit_while_the_responder_reports_open():
    """S-56: qualification is the conjunction of both sides' entry
    conditions, reported through session_status. The reviewer's sequence:
    A's one question qualifies A's view, but B's profile requires a
    dimension nobody examined, so B reports `open` and A must not emit."""
    a, b = _pair()
    b.session.required_dimensions = {"domain", "open_attribute"}
    response = _exchange(
        a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                     value=["enterprise_software"])]
    )
    assert response.session_status is SessionStatus.OPEN
    assert a.session.qualify() is False, (
        "the responder's reported status gates the initiator (Section 14.6)"
    )
    assert a.session.state is SessionState.PROBING, (
        "the gate holds the TRANSITION, not only the emission: no "
        "QUALIFIED-without-Opportunity intermediate state exists"
    )
    with pytest.raises(ProtocolError, match="before qualification"):
        a.request_consent(ConsentAction.REVEAL_IDENTITY, ["open_attribute"])
    # The examining claim arrives; B's next report qualifies; A may emit.
    response = _exchange(
        a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                     value="value")]
    )
    assert response.session_status is SessionStatus.POTENTIALLY_COMPATIBLE
    assert b.session.qualify() is True
    assert a.session.qualify() is True


def test_a_handoff_without_its_consent_is_refused():
    """S-58: being in CONSENTED establishes nothing about *this* action."""
    a, b = _pair()
    _qualify_both(a, b)
    # A consent exists, for something else.
    consent = a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["open_attribute"])
    granted = b.handle_consent_request(consent)
    a.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    with pytest.raises(ProtocolError, match="handoff"):
        a.handoff("urn:example:negotiation")


def test_a_handoff_consent_covers_only_its_named_target():
    a, b = _pair()
    _qualify_both(a, b)
    _grant_handoff(a, b, "urn:example:negotiation")
    with pytest.raises(ProtocolError, match="handoff"):
        a.handoff("urn:example:other-target")
    assert a.handoff("urn:example:negotiation").target.protocol_ref == (
        "urn:example:negotiation"
    )


def test_a_pre_qualification_grant_does_not_preload_consented():
    """A consent granted before qualification opens a gate (10.2); it must
    not make the session read CONSENTED once qualification is later
    reached. CONSENTED is a post-qualification grant, and a remembered
    earlier one does not count."""
    a, b = _consent_gated_pair()
    request = a.request_consent(
        ConsentAction.DISCLOSE_ATTRIBUTES, scope=["data_room"]
    )
    granted = b.handle_consent_request(request)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    assert a.session.state is SessionState.PROBING

    _qualify_both(a, b)
    assert a.session.state is SessionState.QUALIFIED, (
        "the earlier gate-opening grant must not surface as CONSENTED"
    )
    assert b.session.state is SessionState.QUALIFIED


# ---------------------------------------------------------------------------
# Reviews of the 0.2 session-model draft (2 October 2026)
# ---------------------------------------------------------------------------


def test_directions_are_independent_waits():
    """Both draft reviews, same trace: A's consent awaits B's Principal;
    B may still ask A for a disclosure meanwhile. Section 17.2 holds state
    per direction, and the pending axis now does too."""
    from gidp.objects import AuthoritySpec
    from gidp.vocab import Authority, AuthorityValue

    approval = _interest(
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
                Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
            }
        )
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=approval)
    a.confirm_accept(b.handle_session_open(a.open_session("s-x", purpose="t")))
    _qualify_both(a, b)

    # A asks a consent; B's Principal is thinking.
    consent = a.request_consent(ConsentAction.REVEAL_IDENTITY, scope=["identity"])
    provisional = b.handle_consent_request(consent)
    assert provisional.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL
    a.session.record_consent(provisional)
    b.session.record_consent(provisional, discharge=False)

    # Meanwhile B asks A for a disclosure in the reverse direction, which
    # a single shared wait slot would wrongly refuse.
    request = b.request_disclosure("open_attribute", purpose="meanwhile")
    response = a.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.GRANTED
    b.session.record_disclosure(response)

    # The Principal's decision still lands where it was awaited.
    terminal = b.principal_answers_consent(consent, granted=True)
    a.session.record_consent(terminal)
    b.session.record_consent(terminal, discharge=False)
    assert a.session.state is SessionState.CONSENTED


def test_an_unanswered_question_blocks_qualification():
    """A claim held for a PROBE approval (S-51) is an unresolved
    proposition: no Opportunity over it. Expiry discharges the request
    without making it a result."""
    a, b = _pair()
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    # A second question leaves A's side; B holds it (no response yet).
    a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                 value="value")])
    assert a.session.status() is SessionStatus.OPEN
    assert a.session.qualify() is False, (
        "an Opportunity must not be emitted while our own question is "
        "unanswered"
    )


def test_a_delayed_duplicate_response_cannot_clear_a_newer_wait():
    """Second draft review: a terminal response clears the MATCHING
    request. A replayed answer to D1 must not clear the wait D2 opened."""
    a, b = _pair()
    d1 = a.request_disclosure("open_attribute", purpose="first")
    r1 = b.handle_disclosure_request(d1)
    a.session.record_disclosure(r1)
    d2 = a.request_disclosure("open_attribute", purpose="second")
    with pytest.raises(ProtocolError, match="unknown request"):
        a.session.record_disclosure(r1)  # the delayed duplicate
    assert a.session.state is SessionState.DISCLOSURE_PENDING, (
        "D2's wait survives the replayed answer to D1"
    )
    r2 = b.handle_disclosure_request(d2)
    a.session.record_disclosure(r2)
    assert a.session.state is SessionState.PROBING


def test_one_request_in_flight_per_direction():
    """Within one direction, a second disclosure or consent cannot be
    opened while the first is in flight (17.2, the explicit concurrency
    rule). Independence across directions does not mean none within one."""
    a, b = _pair()
    a.request_disclosure("open_attribute", purpose="first")
    with pytest.raises(ProtocolError, match="no transition"):
        a.request_disclosure("domain", purpose="second")
    with pytest.raises(ProtocolError, match="no transition"):
        a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["domain"])


# ---------------------------------------------------------------------------
# Second round on the session-model draft (3 October 2026)
# ---------------------------------------------------------------------------


def test_the_directional_projection_is_faithful():
    """R1's trace: A's sent consent is provisional, a received disclosure
    is simultaneously provisional, then the consent is declined. The
    directional views must read PROBING (A->B) and DISCLOSURE_PENDING
    (B->A); the aggregate is display only and never drives admission."""
    from gidp.objects import ConsentResponse
    from gidp.session import RECEIVED, SENT

    a, _ = _pair()
    consent = a.request_consent(
        ConsentAction.DISCLOSE_ATTRIBUTES, ["open_attribute"]
    )
    a.session.record_consent(
        ConsentResponse(
            session_id=a.session.session_id,
            request_ref=consent.request_id,
            status=ConsentStatus.PENDING_PRINCIPAL_APPROVAL,
            expires_at=_soon(),
        )
    )
    a.session.begin_disclosure(RECEIVED)  # B's request arrives meanwhile
    a.session.record_consent(
        ConsentResponse(
            session_id=a.session.session_id,
            request_ref=consent.request_id,
            status=ConsentStatus.DECLINED,
            expires_at=_soon(),
        )
    )
    assert a.session.state_of(SENT) is SessionState.PROBING
    assert a.session.state_of(RECEIVED) is SessionState.DISCLOSURE_PENDING


def test_a_grant_in_one_direction_does_not_consent_the_other():
    from gidp.session import RECEIVED, SENT

    a, b = _pair()
    _qualify_both(a, b)
    consent = a.request_consent(ConsentAction.REVEAL_IDENTITY, ["open_attribute"])
    granted = b.handle_consent_request(consent)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    assert a.session.state_of(SENT) is SessionState.CONSENTED
    assert a.session.state_of(RECEIVED) is SessionState.QUALIFIED
    assert b.session.state_of(RECEIVED) is SessionState.CONSENTED
    assert b.session.state_of(SENT) is SessionState.QUALIFIED


def test_an_expired_wait_frees_the_session_without_closing_it():
    """The decided 0.2 deadline semantics: the requester's expired consent
    wait is discharged, the session stays open, a late terminal is
    refused by correlation, and a new request is admissible."""
    a, b = _pair()
    _qualify_both(a, b)
    consent = a.request_consent(ConsentAction.REVEAL_IDENTITY, ["identity"])
    provisional = b.handle_consent_request(consent)
    assert provisional.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL
    a.session.expire_request(consent.request_id)
    assert a.session.state is SessionState.QUALIFIED
    with pytest.raises(ProtocolError, match="no transition"):
        # The late terminal names a wait that no longer exists.
        a.session.record_consent(provisional)
    # A new request in the freed direction is admissible.
    a.request_disclosure("open_attribute", purpose="after-expiry")


def test_an_expired_question_blocks_until_superseded():
    """The decided fate of an expired unanswered claim: the proposition
    remains unresolved and blocks qualification; the 0.2 extension lets
    its own sender supersede it, which restores the path."""
    a, b = _pair()
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    held = a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                        value="value")])
    claim_id = held.claims[0].claim_id
    a.session.expire_request(held.request_id, claim_ids=[claim_id])
    # B received and holds the question: its own view records it
    # unanswered too (Section 16.3), and must not qualify over it.
    b.session.note_unanswered("received", [claim_id])
    assert a.session.qualify() is False, (
        "an expired unanswered question still blocks qualification"
    )
    assert b.session.qualify() is False, (
        "the holder does not qualify over a question it is sitting on"
    )
    # Recovery in the same session: supersede the expired claim.
    _exchange(a, b, [Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                           value="value", supersedes=[claim_id])])
    assert a.session.qualify() is True


# ---------------------------------------------------------------------------
# Fourth round on the session-model draft: the Handoff collision
# ---------------------------------------------------------------------------


def _handoff_ready() -> tuple[Agent, Agent]:
    a, b = _pair()
    _qualify_both(a, b)
    _grant_handoff(a, b, "urn:example:negotiation")
    return a, b


def test_the_handoff_collision_is_decided_by_the_recipient():
    """Both reviewers' race, resolved by 0.1's own recipient rule: B's
    request is in transit when A emits; B, whose sent slot is occupied,
    refuses and closes unsupported; the close also ends B's wait, and A
    moves HANDED_OFF -> CLOSED on receiving it. Emission is not a
    bilateral acceptance of the transfer."""
    from gidp.vocab import CloseReason

    a, b = _handoff_ready()
    # Step 2: B's request leaves, but is NOT yet delivered to A.
    b.request_disclosure("open_attribute", purpose="in-transit")
    # Step 3: A's local views are quiescent; A emits.
    handoff = a.handoff("urn:example:negotiation")
    assert a.session.state is SessionState.HANDED_OFF
    # Step 4: B receives the Handoff with its sent slot occupied.
    with pytest.raises(ProtocolError, match="unsupported"):
        b.session.record_handoff(handoff)
    b.session.close(CloseReason.UNSUPPORTED)
    assert b.session.state is SessionState.CLOSED
    # Step 5: the emitter moves HANDED_OFF -> CLOSED on the close.
    a.session.close(CloseReason.UNSUPPORTED)
    assert a.session.state is SessionState.CLOSED


def test_the_barrier_counts_an_unanswered_own_question():
    """The local guard covers active CompatibilityRequests as well as the
    two pending slots: our own question without a terminal blocks the
    emission."""
    a, b = _handoff_ready()
    a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                 value="value")])
    with pytest.raises(ProtocolError, match="quiescence"):
        a.handoff("urn:example:negotiation")


def test_the_barrier_counts_a_held_received_question():
    from gidp.session import RECEIVED

    a, b = _handoff_ready()
    a.session.note_unanswered(RECEIVED, ["q-held"])
    with pytest.raises(ProtocolError, match="quiescence"):
        a.handoff("urn:example:negotiation")


def test_an_expired_unsuperseded_proposition_does_not_block_a_handoff():
    """An evaluation fact is not an active request: the barrier counts
    requests, and the expired question already blocked qualification
    where it mattered."""

    a, b = _handoff_ready()
    # A post-qualification question expires unanswered.
    held = a.ask([Claim(key="open_attribute", operator=ClaimOperator.EQUALS,
                        value="value")])
    a.session.expire_request(held.request_id,
                             claim_ids=[held.claims[0].claim_id])
    assert a.session.unanswered, "the evaluation fact stands"
    a.handoff("urn:example:negotiation")
    assert a.session.state is SessionState.HANDED_OFF


# ---------------------------------------------------------------------------
# E-01, E-02 — found by the first independent clean-room implementation
# (TypeScript, from the published text alone, October 2026). Its audit
# reproduced both against its own code; replayed against the reference,
# both reproduced here too, and both tests failed before the fix.
# ---------------------------------------------------------------------------


def test_a_requester_cannot_send_its_own_private_value():
    """E-01, Section 14.3: a request MUST NOT contain the requester's own
    private values. Refused before emission, and nothing is recorded."""
    a, b = _pair()
    with pytest.raises(ProtocolError, match="14.3"):
        a.ask([Claim(key="threshold", operator=ClaimOperator.OVERLAPS,
                     value={"min": 0, "max": 80})])
    assert not a.session.unanswered
    # A hypothesis the requester does not hold travels normally.
    response = _exchange(a, b, [Claim(key="threshold", operator=ClaimOperator.OVERLAPS,
                                      value={"min": 50, "max": 60})])
    assert response.results


def test_a_requester_cannot_send_its_own_private_dependency():
    """E-01, Sections 14.3 and 19.1: the four reserved lists are the
    requester's values like any other (the evaluator's own case)."""
    a = Agent(ref="agent:a", standing_interest=_interest(
        interest=ConditionalInterest(
            action="consider",
            conditions={"domain": ["enterprise_software"]},
            conditional_on=["anchor_commitment"],
        )
    ))
    b = Agent(ref="agent:b", standing_interest=_interest())
    a.confirm_accept(b.handle_session_open(a.open_session("s-e1", purpose="test")))
    with pytest.raises(ProtocolError, match="14.3"):
        a.ask([Claim(key="conditional_on", operator=ClaimOperator.INTERSECTS,
                     value=["anchor_commitment"])])
    # A dependency the requester does not itself hold may be asked about.
    _exchange(a, b, [Claim(key="conditional_on", operator=ClaimOperator.INTERSECTS,
                           value=["other_dependency"])])


def _identity_revealed_pair() -> tuple[Agent, Agent]:
    from gidp.objects import AuthoritySpec, StandingInterest
    from gidp.vocab import Authority, AuthorityValue

    def interest(identity: str) -> StandingInterest:
        base = _interest()
        conditions = dict(base.interest.conditions, principal_identity=identity)
        # Releasable at session depth once its consent is granted: the
        # policy alone would let it go, so only authority can stop it.
        policy = DisclosurePolicy(attributes={
            **base.disclosure_policy.attributes,
            "principal_identity": DisclosureClass(surface=Surface.SESSION),
        })
        return base.model_copy(update={
            "interest": base.interest.model_copy(update={"conditions": conditions}),
            "disclosure_policy": policy,
            "authority": AuthoritySpec(levels={
                **base.authority.levels,
                Authority.INTRODUCE: AuthorityValue.TRUE,
            }),
        })

    a = Agent(ref="agent:a", standing_interest=interest("Borealis SA"))
    b = Agent(ref="agent:b", standing_interest=interest("Acme GmbH"))
    a.confirm_accept(b.handle_session_open(a.open_session("s-e2", purpose="test")))
    _qualify_both(a, b)
    request = a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_identity"])
    response = b.handle_consent_request(request)
    assert response.status is ConsentStatus.GRANTED
    a.record_consent(response)
    b.session.record_consent(response, discharge=False)
    return a, b


def test_identity_confirmation_rereads_introduce_at_every_use():
    """E-02, Sections 10.6 and 16.3: a consent opens a possibility and
    waives no other row. Once the Principal withdraws INTRODUCE, a claim
    that would confirm the identity is declined, granted consent or not."""
    from gidp.vocab import Authority, AuthorityValue

    a, b = _identity_revealed_pair()
    b.standing_interest.authority.levels[Authority.INTRODUCE] = AuthorityValue.FALSE
    response = _exchange(a, b, [Claim(key="principal_identity",
                                      operator=ClaimOperator.EQUALS,
                                      value="Acme GmbH")])
    assert [o.result for o in response.results] == [ClaimResult.DECLINED]


def test_identity_disclosure_rereads_introduce_at_every_use():
    """E-02, the second door: the DisclosureResponse path re-reads it too."""
    from gidp.vocab import Authority, AuthorityValue

    a, b = _identity_revealed_pair()
    granted = b.handle_disclosure_request(
        a.request_disclosure("principal_identity", purpose="introduce")
    )
    assert granted.status is DisclosureStatus.GRANTED  # the gate is open
    a.session.record_disclosure(granted)
    b.standing_interest.authority.levels[Authority.INTRODUCE] = AuthorityValue.FALSE
    response = b.handle_disclosure_request(
        a.request_disclosure("principal_identity", purpose="introduce")
    )
    assert response.status is DisclosureStatus.DECLINED
    assert "Acme" not in response.model_dump_json()
