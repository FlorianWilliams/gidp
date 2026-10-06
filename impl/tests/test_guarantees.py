"""The two disclosure controls, tested against what they promise.

Each test states a guarantee and checks it exhaustively on a small domain,
against an oracle that does not share the control's code: it rebuilds a
responder holding each candidate value and replays the same claims through
the real Agent. A control that is wrong about what an answer reveals, for
whatever reason, disagrees with the oracle. Tests of reported cases are in
`test_release_review.py`; these are the properties those cases violated
(see `VERIFICATION.md`).

Shapes covered: integers, decimals, thresholds, ranges, labels, lists, and
the four dependency primitives; operators: all four core operators.
"""

from __future__ import annotations

import random
import sys
from math import log2
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_conformance import _interest  # noqa: E402

from gidp.agent import Agent  # noqa: E402
from gidp.auditing import (  # noqa: E402
    BitBudget,
    GranularityLattice,
    LatticeDomainError,
)
from gidp.evaluation import DEPENDENCY_KEYS  # noqa: E402
from gidp.objects import (  # noqa: E402
    AuthoritySpec,
    Claim,
    CompatibilityResponse,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from gidp.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    ConsentAction,
    Feature,
    Surface,
)

OPERATORS = tuple(ClaimOperator)
KEY = "x"


def _holding(key: str, value: Any) -> StandingInterest:
    if key in DEPENDENCY_KEYS:
        interest = ConditionalInterest(action="consider", **{key: list(value)})
    else:
        interest = ConditionalInterest(action="consider", conditions={key: value})
    return StandingInterest(
        id="local:si",
        principal_ref="local:p",
        interest=interest,
        disclosure_policy=DisclosurePolicy(
            attributes={key: DisclosureClass(surface=Surface.LOCAL)}
        ),
        authority=AuthoritySpec(
            levels={Authority.PROBE: AuthorityValue.TRUE}, evidence_ref="urn:demo"
        ),
    )


def _transcript(key: str, value: Any, audit, claims: list[Claim]) -> tuple:
    """Every answer a responder holding `value` gives to `claims`, in order."""
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=_holding(key, value),
              disclosure_audit=audit, query_budget=1_000_000)
    opened = a.open_session("s", purpose="test", features=[Feature.DEPENDENCY_PRIMITIVES])
    a.confirm_accept(b.handle_session_open(opened))
    out = []
    for claim in claims:
        response = b.handle_compatibility_request(a.ask([claim.model_copy()]))
        assert isinstance(response, CompatibilityResponse)
        out.append(response.results[0].result)
    return tuple(out)


def _shapes(top: int) -> list[Any]:
    """Every question shape over 0..top-1: bands, open bands, points,
    lists, and a decimal point."""
    shapes: list[Any] = [{"min": lo, "max": hi} for lo in range(top) for hi in range(lo, top)]
    shapes += [{"min": v} for v in range(top)] + [{"max": v} for v in range(top)]
    shapes += list(range(top)) + [[v] for v in range(top)] + [top / 2 + 0.5]
    return shapes


# -- the lattice: resolution is one cell, for every shape the value can take ---


WIDTH, TOP = 4, 12


def _cell(v: int) -> int:
    return v // WIDTH


LATTICE_VALUES = {
    "scalar": ([v for v in range(TOP)], lambda v: (_cell(v),)),
    "threshold": ([{"min": v} for v in range(TOP)], lambda v: (_cell(v["min"]),)),
    "range": (
        [{"min": lo, "max": hi} for lo in range(TOP) for hi in range(lo, TOP)],
        lambda v: (_cell(v["min"]), _cell(v["max"])),
    ),
}


@pytest.mark.parametrize("shape", sorted(LATTICE_VALUES))
def test_no_question_distinguishes_values_in_the_same_cells(shape):
    """Guarantee: under a lattice, two values whose bounds fall in the same
    cells receive identical answers to every question, under every
    operator. The lattice decides what is admissible; nothing is filtered
    by the test."""
    values, cells_of = LATTICE_VALUES[shape]
    claims = [Claim(key=KEY, operator=op, value=s) for op in OPERATORS for s in _shapes(TOP)]
    seen: dict[tuple, set[tuple]] = {}
    for value in values:
        lattice = GranularityLattice(widths={KEY: WIDTH})
        seen.setdefault(cells_of(value), set()).add(_transcript(KEY, value, lattice, claims))
    assert all(len(t) == 1 for t in seen.values())


@pytest.mark.parametrize("value", [39.5, {"min": 39.5}, {"min": 20, "max": 39.5}, [1.5], True])
def test_a_value_the_lattice_cannot_cover_raises_on_every_question(value):
    """Guarantee: a value outside the lattice's integer domain is a
    configuration error, raised whatever is asked, never answered."""
    lattice = GranularityLattice(widths={KEY: WIDTH})
    for operator in OPERATORS:
        for shape in _shapes(TOP)[::7]:
            with pytest.raises(LatticeDomainError):
                _transcript(KEY, value, lattice,
                            [Claim(key=KEY, operator=operator, value=shape)])


# -- the budget: what is revealed never exceeds it, and is what it records ----


def _sequences(claims: list[Claim], n: int, seed: int) -> list[list[Claim]]:
    rng = random.Random(seed)
    out = [list(claims)]
    for _ in range(n):
        order = list(claims)
        rng.shuffle(order)
        out.append(order)
    return out


BUDGET_CASES = {
    "threshold": (KEY, [{"min": v} for v in range(8)],
                  [s for s in _shapes(8) if isinstance(s, dict)]),
    "scalar": (KEY, list(range(8)), _shapes(8)),
    "label": (KEY, ["a", "b", "c", "d"], ["a", "b", "c", "d", ["a", "b"], ["c"]]),
    "list": (KEY, [["a"], ["b"], ["a", "b"], ["c"]],
             [["a"], ["b"], ["c"], ["a", "c"], "a"]),
    **{
        key: (key, [["cap-1"], ["cap-2"], ["cap-3"], ["cap-1", "cap-2"]],
              [["cap-1"], ["cap-2"], ["cap-3"], ["cap-1", "cap-3"]])
        for key in DEPENDENCY_KEYS
    },
}


@pytest.mark.parametrize("case", sorted(BUDGET_CASES))
@pytest.mark.parametrize("bits", [0.0, 1.0, 2.0])
def test_the_budget_holds_and_records_what_is_revealed(case, bits):
    """Guarantee: whatever sequence of claims is asked, what the answers
    reveal about the value, computed by the oracle, never exceeds the
    budget, and equals what the budget records as disclosed."""
    key, prior, shapes = BUDGET_CASES[case]
    claims = [Claim(key=key, operator=op, value=s) for op in OPERATORS for s in shapes]
    total = log2(len(prior))
    for sequence in _sequences(claims, n=3, seed=len(case)):
        budgets = {i: BitBudget(priors={key: tuple(prior)}, budget_bits=bits)
                   for i in range(len(prior))}
        transcripts = {i: _transcript(key, prior[i], budgets[i], sequence)
                       for i in range(len(prior))}
        for i in range(len(prior)):
            consistent = [j for j in transcripts if transcripts[j] == transcripts[i]]
            revealed = total - log2(len(consistent))
            assert revealed <= bits + 1e-9, (case, prior[i], revealed)
            assert budgets[i].disclosed(key) == pytest.approx(revealed), (case, prior[i])


# -- consent: nothing a session grants reaches another session ---------------


def _blank_peer() -> Agent:
    """A peer holding nothing private, so that any value it names is a
    question and never its own (Section 14.3)."""
    return Agent(ref="agent:c", standing_interest=_interest(
        interest=ConditionalInterest(action="consider",
                                     conditions={"domain": ["enterprise_software"]}),
        disclosure_policy=DisclosurePolicy(
            attributes={"domain": DisclosureClass(surface=Surface.DISCOVERY)}),
    ))


def _probe_new_session(b: Agent, attributes: list[str]) -> tuple:
    """What brand-new peers obtain from `b`: one disclosure request and one
    claim naming the held value, per attribute."""
    out = []
    for n, attribute in enumerate(attributes):
        # A session per attribute: a provisional answer would otherwise hold
        # the direction's slot (Section 17.2) and block the next request.
        c = _blank_peer()
        c.confirm_accept(b.handle_session_open(c.open_session(f"s-new-{n}", purpose="test")))
        response = b.handle_disclosure_request(c.request_disclosure(attribute, purpose="q"))
        out.append((attribute, response.status, response.value))
        c.session.record_disclosure(response)
        held = b.standing_interest.interest.conditions[attribute]
        answer = b.handle_compatibility_request(
            c.ask([Claim(key=attribute, operator=ClaimOperator.EQUALS, value=held)])
        )
        out.append((attribute, answer.results[0].result))
    return tuple(out)


def test_a_new_session_obtains_exactly_what_a_fresh_agent_would_give():
    """Guarantee (Section 14.5): consent is scoped to a session. After a
    session in which consents were granted, identity included, a new peer
    obtains from the same Agent instance exactly what it would obtain from
    an Agent that never held a session."""
    from test_review_findings import _identity_revealed_pair

    a, b = _identity_revealed_pair()
    response = b.handle_consent_request(
        a.request_consent(ConsentAction.DISCLOSE_ATTRIBUTES, ["open_attribute", "identity"])
    )
    a.record_consent(response)
    b.session.record_consent(response, discharge=False)
    attributes = sorted(b.standing_interest.interest.conditions)
    fresh = Agent(ref="agent:b", standing_interest=b.standing_interest.model_copy(deep=True))
    assert _probe_new_session(b, attributes) == _probe_new_session(fresh, attributes)


# -- PROBE approval: nothing is answered before the Principal decides --------


def test_nothing_is_answered_while_probe_awaits_approval():
    """Guarantee (Section 16.3): with PROBE `approval_required`, no claim of
    any shape, on any attribute, receives an answer before the Principal
    decides; the request is held and nothing is emitted."""
    held = _holding(KEY, 5).model_copy(deep=True)
    held.authority.levels[Authority.PROBE] = AuthorityValue.APPROVAL_REQUIRED
    a = Agent(ref="agent:a", standing_interest=_interest())
    b = Agent(ref="agent:b", standing_interest=held)
    a.confirm_accept(b.handle_session_open(a.open_session("s-p", purpose="test")))
    for operator in OPERATORS:
        for shape in _shapes(8):
            request = a.ask([Claim(key=KEY, operator=operator, value=shape)])
            assert b.handle_compatibility_request(request) is None
    assert not any(entry.event == "claim_answered" for entry in b.audit)
