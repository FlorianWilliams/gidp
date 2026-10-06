"""Defects found by the first review of the published release (6 October
2026), by reviewers who ran the code. SPEC-ISSUES.md P-01 to P-03 and P-05.

Each test reproduces the reviewer's case and failed before its fix.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_conformance import _interest  # noqa: E402

from gidp.agent import Agent  # noqa: E402
from gidp.auditing import GranularityLattice  # noqa: E402
from gidp.objects import (  # noqa: E402
    AuthoritySpec,
    Claim,
    CompatibilityResponse,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    SessionClose,
    StandingInterest,
)
from gidp.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    ClaimResult,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    DisclosureStatus,
    Gate,
    Surface,
)

# -- P-01: consent is scoped to a session ------------------------------------


def _gated() -> StandingInterest:
    return _interest(
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


def test_a_consent_does_not_follow_the_agent_into_a_new_session():
    """Section 14.5: consent MUST be scoped to a session. B grants A a
    consent-gated attribute; a later session with C, served by the same
    Agent instance, must not inherit the grant."""
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_gated())
    a.confirm_accept(b.handle_session_open(a.open_session("s-ab", purpose="test")))
    consent = a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["data_room"])
    granted = b.handle_consent_request(consent)
    assert granted.status is ConsentStatus.GRANTED
    a.session.record_consent(granted)
    b.session.record_consent(granted, discharge=False)
    first = b.handle_disclosure_request(a.request_disclosure("data_room", purpose="q"))
    assert first.status is DisclosureStatus.GRANTED

    c = Agent(ref="agent:c", standing_interest=_interest())
    c.confirm_accept(b.handle_session_open(c.open_session("s-cb", purpose="test")))
    second = b.handle_disclosure_request(c.request_disclosure("data_room", purpose="q"))
    assert second.status is not DisclosureStatus.GRANTED
    assert second.value is None


# -- P-02: PROBE approval_required holds the request -------------------------


def _probe_needs_approval() -> StandingInterest:
    base = _interest()
    return base.model_copy(update={
        "authority": AuthoritySpec(
            levels={**base.authority.levels,
                    Authority.PROBE: AuthorityValue.APPROVAL_REQUIRED},
            evidence_ref=base.authority.evidence_ref,
        )
    })


def _held_pair():
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_probe_needs_approval())
    a.confirm_accept(b.handle_session_open(a.open_session("s-p", purpose="test")))
    request = a.ask([Claim(key="threshold", operator=ClaimOperator.OVERLAPS,
                           value={"min": 50, "max": 60})])
    return a, b, request


def test_probe_approval_required_holds_the_answer():
    """Section 16.3: no provisional response exists for PROBE; the Agent
    holds the request until its Principal decides, and sends nothing."""
    _, b, request = _held_pair()
    assert b.handle_compatibility_request(request) is None
    assert not any(e.event == "claim_answered" for e in b.audit)


def test_an_approved_probe_is_answered_terminally():
    a, b, request = _held_pair()
    b.handle_compatibility_request(request)
    response = b.principal_answers_probe(request, approved=True)
    assert isinstance(response, CompatibilityResponse)
    a.receive_compatibility_response(response, request)
    assert response.results[0].result is not ClaimResult.DECLINED


def test_a_refused_probe_closes_declined():
    _, b, request = _held_pair()
    b.handle_compatibility_request(request)
    response = b.principal_answers_probe(request, approved=False)
    assert isinstance(response, SessionClose)
    assert response.reason is CloseReason.DECLINED


def test_a_late_approval_rereads_authority():
    """Section 16.3: an approval cannot resurrect what the authority in force
    now refuses."""
    _, b, request = _held_pair()
    b.handle_compatibility_request(request)
    b.standing_interest.authority.levels[Authority.PROBE] = AuthorityValue.FALSE
    response = b.principal_answers_probe(request, approved=True)
    assert isinstance(response, SessionClose)


# -- P-03: the lattice holds only bands --------------------------------------


def _scalar_interest() -> StandingInterest:
    return StandingInterest(
        id="local:si",
        principal_ref="local:p",
        interest=ConditionalInterest(action="consider", conditions={"headcount": 45}),
        disclosure_policy=DisclosurePolicy(
            attributes={"headcount": DisclosureClass(surface=Surface.LOCAL)}
        ),
        authority=AuthoritySpec(
            levels={Authority.PROBE: AuthorityValue.TRUE}, evidence_ref="urn:demo"
        ),
    )


def _lattice_result(operator: ClaimOperator, value) -> ClaimResult:
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_scalar_interest(),
              disclosure_audit=GranularityLattice(widths={"headcount": 20}))
    a.confirm_accept(b.handle_session_open(a.open_session("s-l", purpose="test")))
    response = b.handle_compatibility_request(
        a.ask([Claim(key="headcount", operator=operator, value=value)])
    )
    assert isinstance(response, CompatibilityResponse)
    return response.results[0].result


def test_the_lattice_declines_a_point_question():
    """`equals 45` on a width of 20 used to pass the lattice and test the
    value exactly."""
    assert _lattice_result(ClaimOperator.EQUALS, 45) is ClaimResult.DECLINED
    assert _lattice_result(ClaimOperator.INTERSECTS, [45]) is ClaimResult.DECLINED
    # The lattice's own rule, whatever the evaluator would make of the shape.
    assert _lattice_result(ClaimOperator.OVERLAPS, 45) is ClaimResult.DECLINED
    assert _lattice_result(ClaimOperator.OVERLAPS, [45]) is ClaimResult.DECLINED


def test_the_lattice_still_answers_a_band_on_the_lattice():
    result = _lattice_result(ClaimOperator.OVERLAPS, {"min": 40, "max": 59})
    assert result is not ClaimResult.DECLINED


# -- P-05: a band is made of whole cells --------------------------------------


def test_the_lattice_declines_equals_on_a_band():
    """`equals {"min": 40}` has bounds on the lattice and used to pass,
    confirming a private threshold of exactly 40."""
    assert _lattice_result(ClaimOperator.EQUALS, {"min": 40}) is ClaimResult.DECLINED


def test_bands_sharing_an_edge_are_declined():
    """[20, 40] and [40, 60] both answered would isolate 40."""
    for band in ({"min": 20, "max": 40}, {"min": 40, "max": 60}, {"min": 40, "max": 40}):
        assert _lattice_result(ClaimOperator.OVERLAPS, band) is ClaimResult.DECLINED


def _answers(value, width: int, claims: list[tuple]) -> tuple:
    interest = StandingInterest(
        id="local:si",
        principal_ref="local:p",
        interest=ConditionalInterest(action="consider", conditions={"x": value}),
        disclosure_policy=DisclosurePolicy(
            attributes={"x": DisclosureClass(surface=Surface.LOCAL)}
        ),
        authority=AuthoritySpec(
            levels={Authority.PROBE: AuthorityValue.TRUE}, evidence_ref="urn:demo"
        ),
    )
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=interest, query_budget=100_000,
              disclosure_audit=GranularityLattice(widths={"x": width}))
    a.confirm_accept(b.handle_session_open(a.open_session("s-x", purpose="test")))
    out = []
    for operator, operand in claims:
        response = b.handle_compatibility_request(
            a.ask([Claim(key="x", operator=operator, value=operand)])
        )
        assert isinstance(response, CompatibilityResponse)
        out.append(response.results[0].result)
    return tuple(out)


def test_no_question_resolves_finer_than_a_cell():
    """Every band, point and threshold over a small range, with every core
    operator, is put to the lattice, which decides what to answer. Whatever
    it admits, two values in the same cell must receive identical answers,
    for a scalar and for a threshold. This is the property the lattice
    claims; P-03 and P-05 were both counterexamples to it."""
    width, top = 4, 12
    shapes = [{"min": lo, "max": hi} for lo in range(top) for hi in range(lo, top)]
    shapes += [{"min": v} for v in range(top)] + [{"max": v} for v in range(top)]
    shapes += list(range(top)) + [[v] for v in range(top)]
    claims = [
        (operator, shape)
        for operator in (ClaimOperator.OVERLAPS, ClaimOperator.EQUALS,
                         ClaimOperator.INTERSECTS)
        for shape in shapes
    ]
    for kind in (lambda v: v, lambda v: {"min": v}):
        by_cell: dict[int, set[tuple]] = {}
        for v in range(top):
            by_cell.setdefault(v // width, set()).add(_answers(kind(v), width, claims))
        assert all(len(answers) == 1 for answers in by_cell.values())
