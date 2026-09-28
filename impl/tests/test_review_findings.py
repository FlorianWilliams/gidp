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
    the Opportunity as contingent -- as `undisclosed`, never by name."""
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
    """S-33: the rule attaches to the data, not the message. The class here
    is `session` with no gate -- the reviewer's sharpest case, in which
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
    transition neither fires there nor lapses -- it fires on the return to
    PROBING."""
    a, b = _pair()
    # A disclosure request is outstanding...
    request = a.request_disclosure("open_attribute", purpose="qualify")
    assert a.session.state is SessionState.DISCLOSURE_PENDING
    # ...when the qualifying exchange completes.
    _exchange(a, b, [Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    # Section 17.2: while the request is pending, the status is not yet
    # reported qualifying -- it is recomputed on the return to PROBING.
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
    """The reviewer's exact sequence: qualifying at step 2, `unknown` at
    step 3 during the same wait -- the session must NOT qualify at step 4,
    because the conditions are recomputed over the propositions then
    standing, not remembered from mid-wait."""
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
