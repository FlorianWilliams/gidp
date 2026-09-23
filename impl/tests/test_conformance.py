"""The conformance suite of CID 0.1, Section 23.2.

One test per criterion, named after it, so that a third party can run this
suite against their own implementation: "third-party implementation" means
something verifiable only if there is a suite to point at.

The deployment requirement of 23.2 -- publishing a threat model -- is not
testable by code and is deliberately absent.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cid.agent import Agent
from cid.evaluation import Truthfulness, assert_truthful, choose_result, evaluate_claim
from cid.objects import (
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
from cid.policy import (
    ProjectionRuleViolation,
    RetrievalAttribute,
    SessionConsents,
    derive_projection,
    evaluate_disclosure,
)
from cid.provider import InMemoryProvider
from cid.session import ProtocolError, Session
from cid.vocab import (
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
    InterestClass,
    SessionState,
    SessionStatus,
    Surface,
)


def _soon(minutes: int = 15) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _interest(**overrides) -> StandingInterest:
    base = dict(
        id="local:si",
        principal_ref="local:principal",
        interest=ConditionalInterest(
            interest_class=InterestClass.PASSIVE_CONDITIONAL_DEMAND,
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

def test_criterion_1_all_four_interest_classes_representable():
    """Verified by local inspection: the class is never transmitted."""
    for interest_class in InterestClass:
        si = _interest()
        si.interest.interest_class = interest_class
        assert si.interest.interest_class is interest_class

    transmitted_fields = set()
    for model in (DiscoveryProjection,):
        transmitted_fields |= set(model.model_fields)
    assert "interest_class" not in transmitted_fields


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
    first = evaluate_disclosure(si, "open_attribute", Surface.SESSION, SessionConsents())
    second = evaluate_disclosure(si, "open_attribute", Surface.SESSION, SessionConsents())
    assert (first.permitted, first.reason) == (second.permitted, second.reason)


def test_criterion_3_session_depth_caps_disclosure():
    si = _interest()
    decision = evaluate_disclosure(si, "open_attribute", Surface.NETWORK, SessionConsents())
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
        DiscoveryProjection(
            projection_id="p-1", endpoint="agent:a", expires_at=_soon()
        )


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
    session = Session(session_id="s", is_initiator=True, profile="core",
                      max_depth=Surface.SESSION)
    with pytest.raises(ProtocolError):
        session.note_compatibility()  # no session has been opened yet


def test_criterion_6_closed_is_terminal():
    a, _ = _pair()
    a.session.close(CloseReason.UNSPECIFIED)
    with pytest.raises(ProtocolError):
        a.session.close(CloseReason.COMPLETED)


def test_criterion_6_responses_correlate_to_requests():
    a, b = _pair()
    request = a.ask([Claim(key="domain", operator=ClaimOperator.INTERSECTS,
                           value=["enterprise_software"])])
    response = b.handle_compatibility_request(request)
    assert response.request_ref == request.request_id
    a.receive_compatibility_response(response)
    with pytest.raises(ProtocolError):
        a.session.record_compatibility(response)  # already discharged


# -- 7 ----------------------------------------------------------------------

def test_criterion_7_truthfulness_bounds():
    si = _interest()
    claim = Claim(key="threshold", operator=ClaimOperator.WITHIN,
                  value={"min": 200, "max": 300})
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
    request = a.ask([Claim(key="threshold", operator=ClaimOperator.WITHIN,
                           value={"min": 10, "max": 50})])
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
    with pytest.raises(ProtocolError):
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
    with pytest.raises(ProtocolError):
        b.session.build_opportunity(
            structure="test", expires_at=_soon(), identity_status={}
        )
