"""The conformance suite of GIDP 0.1, Section 23.2.

One test per criterion, named after it, so that a third party can run this
suite against their own implementation: "third-party implementation" means
something verifiable only if there is a suite to point at.

The deployment requirement of 23.2 -- publishing a threat model -- is not
testable by code and is deliberately absent.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp.agent import Agent
from gidp.evaluation import Truthfulness, assert_truthful, choose_result, evaluate_claim
from gidp.objects import (
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    DiscoveryProjection,
    Handoff,
    HandoffTarget,
    SessionClose,
    StandingInterest,
    TransmittedObject,
)
from gidp.policy import (
    ProjectionRuleViolation,
    RetrievalAttribute,
    SessionConsents,
    derive_projection,
    evaluate_disclosure,
)
from gidp.provider import InMemoryProvider
from gidp.session import ProtocolError, Session
from gidp.vocab import (
    Authority,
    AuthorityValue,
    ClaimOperator,
    ClaimResult,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    DisclosureStatus,
    Gate,
    HandoffKind,
    SessionState,
    SessionStatus,
    Surface,
)


def _soon(minutes: int = 15) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutes)


def _interest(**overrides) -> StandingInterest:
    base = dict(
        id="local:si",
        principal_ref="local:principal",
        interest=ConditionalInterest(
            action="consider",
            conditions={
                "domain": ["enterprise_software"],
                "threshold": {"min": 0, "max": 80},
                "identity": "Principal",
                "open_attribute": "value",
            },
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                "domain": DisclosureClass(surface=Surface.DISCOVERY),
                "threshold": DisclosureClass(surface=Surface.LOCAL),
                "identity": DisclosureClass(
                    surface=Surface.SESSION, gate=Gate.PRINCIPAL_APPROVAL
                ),
                "open_attribute": DisclosureClass(surface=Surface.SESSION),
            }
        ),
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
                Authority.PUBLISH_PROJECTION: AuthorityValue.TRUE,
                Authority.INTRODUCE: AuthorityValue.TRUE,
                Authority.NEGOTIATE_NONBINDING: AuthorityValue.TRUE,
            }
        ),
    )
    base.update(overrides)
    return StandingInterest(**base)


def _pair() -> tuple[Agent, Agent]:
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_interest())
    opened = a.open_session("s-1", purpose="test")
    accept = b.handle_session_open(opened)
    a.confirm_accept(accept)
    return a, b


# -- 1 ----------------------------------------------------------------------


def test_criterion_1_the_four_situations_of_section_8_all_run():
    """Section 23.2, criterion 1, made testable.

    The criterion says a conforming implementation must be able to represent
    all four classes of Conditional Interest, and the specification adds that
    they differ in *what is hidden*, not in protocol mechanics. The earlier
    reading of this — verified "by local inspection", then by a field on the
    object — was the wrong one twice over: the protocol defines no such field,
    and inspection is not verification.

    What the criterion actually promises is that the same machinery serves all
    four situations and that the difference between them is policy. So build
    the four, run each, and check both halves.
    """
    from gidp.transport import Wire

    # The four classes of Section 8, expressed the way the section defines
    # them: by which attribute is local and which is disclosable.
    situations = {
        "passive conditional demand": {
            "criteria": Surface.DISCOVERY,
            "threshold": Surface.LOCAL,
        },
        "confidential active demand": {
            "criteria": Surface.SESSION,
            "threshold": Surface.LOCAL,
        },
        "private conditional supply": {
            "criteria": Surface.DISCOVERY,
            "threshold": Surface.SESSION,
        },
        "interdependent interest": {
            "criteria": Surface.SESSION,
            "threshold": Surface.SESSION,
        },
    }

    shapes = {}
    for name, surfaces in situations.items():
        si = _interest()
        si.disclosure_policy.attributes["domain"] = DisclosureClass(
            surface=surfaces["criteria"]
        )
        si.disclosure_policy.attributes["threshold"] = DisclosureClass(
            surface=surfaces["threshold"]
        )

        wire = Wire()
        a = Agent(ref="agent:a", standing_interest=_interest())
        b = Agent(ref="agent:b", standing_interest=si)
        opened = wire.send("A", a.open_session("s-1", purpose="test"))
        a.confirm_accept(wire.send("B", b.handle_session_open(opened)))
        request = wire.send(
            "A",
            a.ask(
                [
                    Claim(
                        key="domain",
                        operator=ClaimOperator.INTERSECTS,
                        value=["enterprise_software"],
                    )
                ]
            ),
        )
        response = wire.send("B", b.handle_compatibility_request(request))
        a.receive_compatibility_response(response, request)

        assert wire.transcript, f"{name} sent nothing"
        shapes[name] = tuple(type(m).__name__ for _s, m in wire.transcript)

    # One machinery, four situations: the object sequence is identical and
    # only the policies differ. If a future change made a situation need its
    # own message flow, the criterion would be false and this would say so.
    assert len(set(shapes.values())) == 1, (
        f"the four situations produced different protocol shapes: {shapes}"
    )


# -- 2 ----------------------------------------------------------------------


def test_criterion_2_local_objects_are_not_transmittable():
    """No local object may be a transmitted object, and no local attribute
    may be disclosed (Sections 9.1, 10)."""
    for local_model in (StandingInterest, DisclosurePolicy, ConditionalInterest):
        assert not issubclass(local_model, TransmittedObject)

    decision = evaluate_disclosure(
        _interest(), "threshold", Surface.SESSION, SessionConsents()
    )
    assert decision.permitted is False
    assert "evaluation-only" in decision.reason


def test_criterion_2_unpoliced_attribute_defaults_to_evaluation_only():
    si = _interest()
    assert si.class_of("never_mentioned").surface is Surface.LOCAL


# -- 3 ----------------------------------------------------------------------


def test_criterion_3_disclosure_decisions_are_reproducible():
    """Replaying the same Standing Interest, policy and session state must
    produce the same decision. The policy engine consults nothing else."""
    si = _interest()
    first = evaluate_disclosure(
        si, "open_attribute", Surface.SESSION, SessionConsents()
    )
    second = evaluate_disclosure(
        si, "open_attribute", Surface.SESSION, SessionConsents()
    )
    assert (first.permitted, first.reason) == (second.permitted, second.reason)


def test_criterion_3_session_depth_caps_disclosure():
    si = _interest()
    decision = evaluate_disclosure(
        si, "open_attribute", Surface.NETWORK, SessionConsents()
    )
    assert decision.permitted is False
    assert "deeper than the session depth" in decision.reason


# -- 4 ----------------------------------------------------------------------


def test_criterion_4_projection_content_rule_is_enforced():
    si = _interest()
    with pytest.raises(ProjectionRuleViolation):
        derive_projection(
            si,
            projection_id="p-1",
            endpoint="agent:a",
            expires_at=_soon(),
            interest_ref="opaque",
            attributes=[RetrievalAttribute("domains", "identity", lambda v: [str(v)])],
        )


def test_criterion_4_projection_requires_a_retrieval_attribute():
    with pytest.raises(ValidationError):
        DiscoveryProjection(projection_id="p-1", endpoint="agent:a", expires_at=_soon())


# -- 5 ----------------------------------------------------------------------


def test_criterion_5_provider_withdrawal_is_observable():
    si = _interest()
    provider = InMemoryProvider()
    projection = derive_projection(
        si,
        projection_id="p-1",
        endpoint="agent:a",
        expires_at=_soon(60),
        interest_ref="opaque",
        attributes=[RetrievalAttribute("domains", "domain", lambda v: list(v))],
    )
    ref = provider.publish_projection(projection)
    assert provider.query_candidates(projection) == [ref]
    assert provider.withdraw_projection(ref) == "withdrawn"
    assert provider.query_candidates(projection) == []
    assert provider.resolve_candidate(ref) is None


# -- 6 ----------------------------------------------------------------------


def test_criterion_6_state_machine_rejects_undefined_transitions():
    session = Session(
        session_id="s", is_initiator=True, profile="core", max_depth=Surface.SESSION
    )
    with pytest.raises(ProtocolError, match="no transition"):
        session.note_compatibility()  # no session has been opened yet


def test_criterion_6_closed_is_terminal():
    a, _ = _pair()
    a.session.close(CloseReason.UNSPECIFIED)
    with pytest.raises(ProtocolError, match="CLOSED is terminal"):
        a.session.close(CloseReason.COMPLETED)


def test_criterion_6_responses_correlate_to_requests():
    a, b = _pair()
    request = a.ask(
        [
            Claim(
                key="domain",
                operator=ClaimOperator.INTERSECTS,
                value=["enterprise_software"],
            )
        ]
    )
    response = b.handle_compatibility_request(request)
    assert response.request_ref == request.request_id
    a.receive_compatibility_response(response)
    with pytest.raises(ProtocolError, match="unknown request"):
        a.session.record_compatibility(response)  # already discharged


# -- 7 ----------------------------------------------------------------------


def test_criterion_7_truthfulness_bounds():
    si = _interest()
    claim = Claim(
        key="threshold", operator=ClaimOperator.WITHIN, value={"min": 200, "max": 300}
    )
    evaluation = evaluate_claim(si, claim)
    assert evaluation.truth is False

    # Permitted: the truthful answer, or a coarsening that asserts nothing.
    assert_truthful(evaluation, choose_result(evaluation))
    assert_truthful(evaluation, choose_result(evaluation, coarsen=True))
    assert_truthful(evaluation, choose_result(evaluation, decline=True))

    # Forbidden: asserting what the private values contradict.
    with pytest.raises(Truthfulness):
        assert_truthful(evaluation, ClaimResult.COMPATIBLE)


def test_criterion_7_evaluation_only_values_are_never_returned():
    a, b = _pair()
    request = a.ask(
        [
            Claim(
                key="threshold",
                operator=ClaimOperator.WITHIN,
                value={"min": 10, "max": 50},
            )
        ]
    )
    response = b.handle_compatibility_request(request)
    serialised = response.model_dump_json()
    assert "80" not in serialised
    assert response.results[0].result is ClaimResult.CONDITIONALLY_COMPATIBLE


# -- 8 ----------------------------------------------------------------------


def test_criterion_8_any_claim_may_be_declined_and_any_session_closed():
    si = _interest()
    evaluation = evaluate_claim(
        si, Claim(key="domain", operator=ClaimOperator.INTERSECTS, value=["x"])
    )
    assert choose_result(evaluation, decline=True) is ClaimResult.DECLINED

    a, _ = _pair()
    a.session.close(CloseReason.UNSPECIFIED)
    assert a.session.state is SessionState.CLOSED


# -- 9 ----------------------------------------------------------------------


def test_criterion_9_principal_approval_gate_is_not_satisfied_by_agent_authority():
    a, b = _pair()
    request = a.request_disclosure("identity", "introduce")
    response = b.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.PENDING_PRINCIPAL_APPROVAL
    assert response.value is None


def test_criterion_9_consent_is_provisional_until_the_principal_decides():
    a, b = _pair()
    b.session.results["domain"] = ClaimResult.COMPATIBLE
    b.session.qualify()
    a.session.results["domain"] = ClaimResult.COMPATIBLE
    a.session.qualify()
    consent = a.request_consent(ConsentAction.REVEAL_IDENTITY, ["identity"])
    response = b.handle_consent_request(consent)
    assert response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL
    assert response.granted_scope == []


# -- 10 ---------------------------------------------------------------------


def test_criterion_10_commit_is_false():
    with pytest.raises(ValidationError):
        AuthoritySpec(levels={Authority.COMMIT: AuthorityValue.TRUE})
    assert AuthoritySpec().value(Authority.COMMIT) is AuthorityValue.FALSE


def test_criterion_10_no_authority_is_inferred_from_a_lower_one():
    spec = AuthoritySpec(levels={Authority.PROBE: AuthorityValue.TRUE})
    assert spec.permits(Authority.PROBE) is True
    assert spec.permits(Authority.DISCLOSE) is False
    assert spec.permits(Authority.INTRODUCE) is False


def test_criterion_10_disclose_false_is_reported_as_declined_not_unauthorized():
    """Section 18: an authority refusal is a compatibility-layer 'declined'."""
    si = _interest()
    si.authority.levels[Authority.DISCLOSE] = AuthorityValue.FALSE
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=si)
    opened = a.open_session("s-2", purpose="test")
    accept = b.handle_session_open(opened)
    a.confirm_accept(accept)
    request = a.request_disclosure("open_attribute", "test")
    response = b.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.DECLINED


# -- 11 ---------------------------------------------------------------------


def test_criterion_11_withdrawal_follows_revocation():
    """A revoked Standing Interest's projections must go (Section 17.1)."""
    si = _interest()
    provider = InMemoryProvider()
    projection = derive_projection(
        si,
        projection_id="p-1",
        endpoint="agent:a",
        expires_at=_soon(60),
        interest_ref="opaque",
        attributes=[RetrievalAttribute("domains", "domain", lambda v: list(v))],
    )
    ref = provider.publish_projection(projection)
    provider.withdraw_projection(ref)  # the Agent's obligation on revocation
    assert provider.query_candidates(projection) == []


# -- 12 ---------------------------------------------------------------------


def test_criterion_12_handoff_never_carries_commit():
    with pytest.raises(ValidationError):
        Handoff(
            session_id="s",
            target=HandoffTarget(kind=HandoffKind.HUMAN),
            authorized_scope=[Authority.COMMIT],
            expires_at=_soon(),
        )


def test_criterion_12_handoff_requires_protocol_ref_for_a_protocol_target():
    with pytest.raises(ValidationError):
        HandoffTarget(kind=HandoffKind.PROTOCOL)


def test_criterion_12_handoff_is_terminal():
    a, b = _pair()
    a.session.results["domain"] = ClaimResult.COMPATIBLE
    a.session.qualify()
    handoff = a.handoff("https://example.org/negotiation/v1")
    assert a.session.state is SessionState.HANDED_OFF
    a.session.close(CloseReason.COMPLETED)
    assert a.session.state is SessionState.CLOSED
    assert handoff.requires_principal_presence is True


def test_criterion_12_handoff_before_qualification_is_refused():
    a, b = _pair()
    handoff = Handoff(
        session_id=a.session.session_id,
        target=HandoffTarget(kind=HandoffKind.HUMAN),
        expires_at=_soon(),
    )
    with pytest.raises(ProtocolError, match="unsupported"):
        b.session.record_handoff(handoff)


# -- 13 ---------------------------------------------------------------------


def test_criterion_13_vocabularies_are_closed():
    with pytest.raises(ValidationError):
        SessionClose(session_id="s", reason="maybe_later", expires_at=_soon())
    with pytest.raises(ValueError):
        Surface("semi_public")


def test_criterion_13_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        SessionClose(
            session_id="s",
            reason=CloseReason.UNSPECIFIED,
            expires_at=_soon(),
            extra_field="not in the specification",
        )


# -- 15.2, as revised ------------------------------------------------------


def test_declined_result_prevents_qualification():
    """Section 15.2 as revised: an Opportunity never rests on silence.

    This test exists because the first implementation of 15.2 followed the
    letter of the earlier text, under which a session of nine `declined`
    results and one `compatible` qualified. See SPEC-ISSUES.md S-04.
    """
    a, _ = _pair()
    a.session.results["domain"] = ClaimResult.COMPATIBLE
    a.session.results["threshold"] = ClaimResult.DECLINED
    assert a.session.status() is not SessionStatus.POTENTIALLY_COMPATIBLE
    assert a.session.qualify() is False

    # Re-asking the declined claim and getting an answer unblocks it.
    a.session.results["threshold"] = ClaimResult.CONDITIONALLY_COMPATIBLE
    assert a.session.status() is SessionStatus.POTENTIALLY_COMPATIBLE
    assert a.session.qualify() is True


def test_opportunity_counts_are_consistent():
    """14.6: compatible_dimensions + len(open_conditions) == evaluated."""
    a, _ = _pair()
    a.session.results["domain"] = ClaimResult.COMPATIBLE
    a.session.results["threshold"] = ClaimResult.CONDITIONALLY_COMPATIBLE
    a.session.qualify()
    opportunity = a.session.build_opportunity(
        structure="test", expires_at=_soon(), identity_status={}
    )
    assert opportunity.evaluated_dimensions == 2
    assert opportunity.compatible_dimensions == 1
    assert opportunity.open_conditions == ["threshold"]
    assert (
        opportunity.compatible_dimensions + len(opportunity.open_conditions)
        == opportunity.evaluated_dimensions
    )


def test_only_the_initiator_emits_the_opportunity():
    _, b = _pair()
    b.session.results["domain"] = ClaimResult.COMPATIBLE
    b.session.qualify()
    with pytest.raises(ProtocolError, match="initiator emits"):
        b.session.build_opportunity(
            structure="test", expires_at=_soon(), identity_status={}
        )


# -- the Principal's decision reaches the wire ------------------------------


def test_a_principal_may_refuse_consent_and_the_request_is_discharged():
    """The `principal_approval` gate is only a gate if a refusal is possible.

    Found by the vocabulary coverage pass: `ConsentStatus.DECLINED` had the
    transition of Section 17.2 behind it and no way for an Agent to reach it,
    so a gated consent stayed provisional for the life of the session and the
    request was never discharged (Section 14).
    """
    from gidp.transport import Wire
    from gidp.vocab import ConsentStatus, SessionState

    a, b = _pair()
    a.session.state = SessionState.QUALIFIED
    b.session.state = SessionState.QUALIFIED

    wire = Wire()
    request = wire.send(
        "A", a.request_consent(ConsentAction.REVEAL_IDENTITY, ["identity"])
    )
    provisional = wire.send("B", b.handle_consent_request(request))
    assert provisional.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL
    assert wire.unanswered(), "a provisional response must not discharge (14)"
    a.session.record_consent(provisional)
    b.session.record_consent(provisional, discharge=False)

    refusal = wire.send("B", b.principal_answers_consent(request, granted=False))
    assert refusal.status is ConsentStatus.DECLINED
    assert refusal.granted_scope == []
    a.session.record_consent(refusal)
    b.session.record_consent(refusal, discharge=False)

    assert not wire.unanswered(), "the terminal response discharges the request"
    assert a.session.state is SessionState.QUALIFIED


def test_a_principal_may_refuse_a_disclosure_and_it_looks_like_any_refusal():
    """Section 14.4: a refusal says nothing about the attribute."""
    from gidp.vocab import DisclosureStatus

    a, b = _pair()
    request = a.request_disclosure("identity", purpose="test")
    response = b.principal_answers_disclosure(request, granted=False)
    assert response.status is DisclosureStatus.DECLINED
    assert response.value is None


def test_an_opportunity_records_that_identity_was_actually_granted():
    """`IdentityStatus.GRANTED` is the normal end of a consented session and
    no worked domain reached it: the examples all stop at `not_requested`.
    A status nothing ever sets is a status no reader can trust."""
    from gidp.vocab import ConsentStatus, IdentityStatus, SessionState

    a, b = _pair()
    a.session.state = SessionState.QUALIFIED
    b.session.state = SessionState.QUALIFIED
    request = a.request_consent(ConsentAction.REVEAL_IDENTITY, ["identity"])
    provisional = b.handle_consent_request(request)
    a.session.record_consent(provisional)
    b.session.record_consent(provisional, discharge=False)
    granted = b.principal_answers_consent(request, granted=True)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)

    a.session.qualify()
    opportunity = a.session.build_opportunity(
        structure="introduction",
        expires_at=_soon(),
        identity_status={
            "initiator": IdentityStatus.NOT_REQUESTED,
            "responder": IdentityStatus.GRANTED,
        },
    )
    assert opportunity.identity_status["responder"] is IdentityStatus.GRANTED


def test_a_stated_retention_is_an_obligation_not_advice():
    """Section 10.7, after XACML: an enforcement point that cannot discharge
    an obligation must not proceed as though it had.

    Before this rule the `retention` field was two SHOULDs facing each other
    — state it, honour it — which is advice whatever it is called.
    """
    from gidp.vocab import Retention

    a, _ = _pair()
    assert a.dischargeable_retention == {Retention.SESSION_ONLY}
    permitted = a.request_disclosure(
        "open_attribute", purpose="test", retention=Retention.SESSION_ONLY
    )
    assert permitted.retention is Retention.SESSION_ONLY

    # A fresh session: a second DisclosureRequest on the same one is refused
    # by the state machine, which would let this test pass for a reason that
    # has nothing to do with retention. The mutation check found exactly that.
    b, _ = _pair()
    with pytest.raises(ProtocolError, match="discharge retention"):
        b.request_disclosure(
            "open_attribute", purpose="test", retention=Retention.UNRESTRICTED
        )


def test_an_agent_that_can_discharge_nothing_states_nothing():
    """The safe outcome is an omitted field and a responder free to decline,
    not a limit the requester intends to ignore."""
    from gidp.vocab import Retention

    a, _ = _pair()
    a.dischargeable_retention = set()
    request = a.request_disclosure("open_attribute", purpose="test", retention=None)
    assert request.retention is None

    b, _ = _pair()
    b.dischargeable_retention = set()
    with pytest.raises(ProtocolError, match="discharge retention"):
        b.request_disclosure(
            "open_attribute", purpose="test", retention=Retention.SESSION_ONLY
        )


def test_approval_required_authority_is_not_silently_ignored():
    """Section 16.2: where a level is `approval_required`, the response MUST
    be `pending_principal_approval`.

    Authority and the Disclosure Policy are different axes — the first says
    whether the Agent may perform a category of action, the second which
    attributes need a decision. The implementation consulted only the second,
    so a Principal who said "ask me before disclosing anything" was obeyed for
    gated attributes and silently ignored for every other one.
    """
    from gidp.vocab import DisclosureStatus

    interest = _interest()
    interest.authority.levels[Authority.DISCLOSE] = AuthorityValue.APPROVAL_REQUIRED
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=interest)
    opened = a.open_session("s-auth", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))

    # `open_attribute` carries no gate at all: before the fix this disclosed.
    request = a.request_disclosure("open_attribute", purpose="test")
    response = b.handle_disclosure_request(request)
    assert response.status is DisclosureStatus.PENDING_PRINCIPAL_APPROVAL
    assert response.value is None


# -- Section 14.2: values at different levels of one hierarchy --------------


def _geographic(held: list[str]) -> StandingInterest:
    si = _interest()
    si.interest.conditions["geography"] = held
    si.interest.taxonomies["geography"] = {
        "munich": "germany",
        "berlin": "germany",
        "paris": "france",
        "germany": "europe",
        "france": "europe",
    }
    si.disclosure_policy.attributes["geography"] = DisclosureClass(
        surface=Surface.SESSION
    )
    return si


def _ask(held: list[str], asked: list[str]):
    from gidp.evaluation import evaluate_claim

    return evaluate_claim(
        _geographic(held),
        Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=asked),
    ).truth


def test_a_held_value_answers_for_everything_it_is_part_of():
    """Munich is in Germany, and in Europe. Answering `incompatible` to
    either would assert something the responder's values contradict."""
    assert _ask(["munich"], ["germany"]) is True
    assert _ask(["munich"], ["europe"]) is True


def test_a_narrower_question_than_the_value_held_is_undeterminable():
    """The asymmetry. A German company may or may not be in Munich, and it
    has not said which — so `unknown`, never `incompatible`."""
    assert _ask(["germany"], ["munich"]) is None


def test_a_genuine_mismatch_is_still_incompatible():
    """The rule must not turn every negative into an evasion."""
    assert _ask(["munich"], ["madrid"]) is False
    assert _ask(["munich"], ["berlin"]) is False


def test_without_a_taxonomy_the_old_reading_still_applies():
    """A Principal that places none of its values gets set semantics, and
    the false negative with them. Declaring the hierarchy is what fixes it."""
    si = _geographic(["munich"])
    si.interest.taxonomies.clear()
    from gidp.evaluation import evaluate_claim

    assert (
        evaluate_claim(
            si,
            Claim(
                key="geography", operator=ClaimOperator.INTERSECTS, value=["germany"]
            ),
        ).truth
        is False
    )


def test_the_hierarchy_is_never_transmitted():
    """It lives in the Standing Interest, which Section 9.1 keeps home."""
    from gidp.transport import Wire

    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_geographic(["munich"]))
    wire = Wire()
    opened = wire.send("A", a.open_session("s-tax", purpose="test"))
    a.confirm_accept(wire.send("B", b.handle_session_open(opened)))
    request = wire.send(
        "A",
        a.ask(
            [
                Claim(
                    key="geography",
                    operator=ClaimOperator.INTERSECTS,
                    value=["germany"],
                )
            ]
        ),
    )
    wire.send("B", b.handle_compatibility_request(request))
    for _sender, message in wire.transcript:
        assert "munich" not in message.model_dump_json()
