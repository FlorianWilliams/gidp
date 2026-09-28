"""The two controls of Section 24.3, in the core rather than in a harness.

`baselines/` measured them and the measurement lives there. These check the
properties a conforming implementation must have: that a refusal is a
`declined` like any other, that the decision never consults the protected
value, and that each control bounds the thing it claims to bound.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp.agent import Agent
from gidp.auditing import BitBudget, GranularityLattice
from gidp.objects import (
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from gidp.vocab import Authority, AuthorityValue, ClaimResult, Surface

GRID = tuple({"min": v} for v in range(0, 205_000_000, 5_000_000))


def _interest(floor: int = 45_000_000) -> StandingInterest:
    return StandingInterest(
        id="local:si",
        principal_ref="local:p",
        interest=ConditionalInterest(
            action="consider", conditions={"valuation_floor": {"min": floor}}
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={"valuation_floor": DisclosureClass(surface=Surface.LOCAL)}
        ),
        authority=AuthoritySpec(
            levels={Authority.PROBE: AuthorityValue.TRUE},
            evidence_ref="urn:demo",
        ),
    )


def _pair(audit=None) -> tuple[Agent, Agent]:
    a = Agent(ref="agent:a", standing_interest=_interest())
    # A high query budget so these tests measure the audit and not the
    # unrelated per-session cap of Section 24.3's other lever.
    b = Agent(
        ref="agent:b",
        standing_interest=_interest(),
        disclosure_audit=audit,
        query_budget=10_000,
    )
    opened = a.open_session("s", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))
    return a, b


def _ask(a: Agent, b: Agent, bounds: dict) -> ClaimResult:
    request = a.ask([Claim(key="valuation_floor", operator="overlaps", value=bounds)])
    return b.handle_compatibility_request(request).results[0].result


# -- the lattice -----------------------------------------------------------


def test_a_claim_off_the_lattice_is_declined():
    a, b = _pair(GranularityLattice(widths={"valuation_floor": 20_000_000}))
    assert _ask(a, b, {"min": 0, "max": 55_000_000}) is ClaimResult.DECLINED


def test_a_claim_on_the_lattice_is_answered():
    a, b = _pair(GranularityLattice(widths={"valuation_floor": 20_000_000}))
    assert _ask(a, b, {"min": 0, "max": 60_000_000}) is not ClaimResult.DECLINED


def test_the_lattice_keeps_nothing_between_claims():
    """Its whole interest: honest traffic cannot deplete it."""
    lattice = GranularityLattice(widths={"valuation_floor": 20_000_000})
    a, b = _pair(lattice)
    for _ in range(50):
        assert _ask(a, b, {"min": 0, "max": 60_000_000}) is not ClaimResult.DECLINED


# -- the bit budget --------------------------------------------------------


def test_the_budget_stops_a_bisection():
    budget = BitBudget(priors={"valuation_floor": GRID}, budget_bits=1.0)
    a, b = _pair(budget)
    results = [
        _ask(a, b, {"min": t, "max": t})
        for t in (100_000_000, 50_000_000, 25_000_000, 60_000_000)
    ]
    assert ClaimResult.DECLINED in results
    assert budget.disclosed("valuation_floor") <= 1.0


def test_the_budget_is_spent_by_anyone_not_only_an_adversary():
    """A commons, and the specification says so rather than hiding it.

    The claim here is the honest one — does my ceiling clear your floor —
    over a wide band. It is cheap, and cheap is not free.
    """
    budget = BitBudget(priors={"valuation_floor": GRID}, budget_bits=2.0)
    a, b = _pair(budget)
    assert _ask(a, b, {"min": 0, "max": 100_000_000}) is not ClaimResult.DECLINED
    assert budget.disclosed("valuation_floor") > 0


def test_the_decision_never_consults_the_protected_value():
    """Simulatability: the same claim must be admitted or refused alike
    whatever the responder happens to hold."""
    claim = Claim(
        key="valuation_floor",
        operator="overlaps",
        value={"min": 60_000_000, "max": 60_000_000},
    )
    decisions = set()
    for floor in (0, 45_000_000, 200_000_000):
        budget = BitBudget(priors={"valuation_floor": GRID}, budget_bits=1.0)
        decisions.add(budget.admits(claim, _interest(floor)))
    assert len(decisions) == 1


def test_an_attribute_with_no_prior_is_not_audited():
    """The budget needs to know what was possible; without that it abstains
    rather than guessing."""
    budget = BitBudget(priors={}, budget_bits=0.0)
    a, b = _pair(budget)
    assert _ask(a, b, {"min": 0, "max": 60_000_000}) is not ClaimResult.DECLINED


def test_no_audit_means_no_bound():
    """Stated so that the default is not mistaken for a defence."""
    a, b = _pair(None)
    for t in (100_000_000, 50_000_000, 25_000_000):
        assert _ask(a, b, {"min": t, "max": t}) is not ClaimResult.DECLINED


def test_the_worst_case_rule_is_conservative_and_that_is_the_price():
    """A question whose *unlikely* answer would be very informative is
    refused, even though the answer it would actually get is cheap.

    Asking whether the floor is below 180M of a 200M band is almost certainly
    answered yes, which narrows little — but if it were answered no, four
    candidates would remain. Simulatability forbids conditioning on which
    answer would be given, so the worst case decides. This is not a defect;
    it is what makes a refusal uninformative, and it is why a budget refuses
    some honest counterparties.
    """
    budget = BitBudget(priors={"valuation_floor": GRID}, budget_bits=2.0)
    a, b = _pair(budget)
    assert _ask(a, b, {"min": 0, "max": 180_000_000}) is ClaimResult.DECLINED
    assert budget.disclosed("valuation_floor") == 0.0, (
        "a refused claim must cost nothing, or the refusal would be a channel"
    )


def test_a_prior_in_the_wrong_shape_refuses_everything_silently():
    """The trap worth a test: a prior of bare integers against an attribute
    that holds a bound makes every candidate answer alike, which the
    worst-case rule reads as maximally informative. Nothing is answered and
    nothing looks wrong."""
    wrong = BitBudget(
        priors={"valuation_floor": tuple(range(0, 205_000_000, 5_000_000))},
        budget_bits=2.0,
    )
    a, b = _pair(wrong)
    assert _ask(a, b, {"min": 100_000_000, "max": 100_000_000}) is ClaimResult.DECLINED

    right = BitBudget(priors={"valuation_floor": GRID}, budget_bits=2.0)
    c, d = _pair(right)
    assert (
        _ask(c, d, {"min": 100_000_000, "max": 100_000_000}) is not ClaimResult.DECLINED
    )
