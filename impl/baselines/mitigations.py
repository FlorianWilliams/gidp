"""Do the specification's anti-inference levers work?

Section 15.5 gives a responder three moves: answer truthfully, coarsen to
`conditionally_compatible`, or decline. Section 24.3 says an adaptive
querent can still locate a threshold, and Section 24.4 says a query budget
helps. None of that had ever been measured.

    python -m baselines.mitigations

The harness sweeps answering policies against query budgets and reports two
numbers per cell: how much a probing counterparty extracts, and whether the
protocol can still tell a compatible counterparty from an incompatible one.
The second number stops the exercise from being trivial: a
responder that answers `conditionally_compatible` to everything leaks
nothing and qualifies everyone.

On randomised policies: a candidate value survives if it *could* have
produced the observed answer, so a policy is written as the set of answers
it admits instead of the one it gives. That is the possibilistic posterior,
which is the correct one to use against an adversary that knows the policy.
"""

from __future__ import annotations

import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.mechanisms import HONEST_CLAIMS  # noqa: E402
from baselines.scenario import (  # noqa: E402
    A_ACCEPTS_MANAGEMENT,
    A_BUDGET_CEILING,
    MANAGEMENT_OPTIONS,
    VALUATION_GRID,
    b_interest,
)
from gidp.evaluation import LocalEvaluation, evaluate_claim  # noqa: E402
from gidp.objects import Claim  # noqa: E402
from gidp.vocab import ClaimOperator, ClaimResult  # noqa: E402

Policy = Callable[[LocalEvaluation, bool], set[ClaimResult]]

QUALIFYING = {ClaimResult.COMPATIBLE, ClaimResult.CONDITIONALLY_COMPATIBLE}

#: How many times the adversary will re-ask a question that stopped narrowing
#: its hypothesis space before abandoning that fact. Repetition is pointless
#: against a deterministic policy and is how a randomised one is
#: defeated, so the number has to be greater than one and finite.
PATIENCE = 12


# --------------------------------------------------------------------------
# Policies, each written as the set of answers it admits
# --------------------------------------------------------------------------


def _truthful(evaluation: LocalEvaluation) -> ClaimResult:
    if evaluation.truth is None:
        return ClaimResult.UNKNOWN
    return ClaimResult.COMPATIBLE if evaluation.truth else ClaimResult.INCOMPATIBLE


def default_policy(evaluation: LocalEvaluation, over_budget: bool) -> set[ClaimResult]:
    """What `gidp/agent.py` does today: coarsen an affirmative local answer."""
    if over_budget:
        return {ClaimResult.DECLINED}
    if evaluation.evaluation_only and evaluation.truth is True:
        return {ClaimResult.CONDITIONALLY_COMPATIBLE}
    return {_truthful(evaluation)}


def coarsen_all_local(
    evaluation: LocalEvaluation, over_budget: bool
) -> set[ClaimResult]:
    """Coarsen every local answer, affirmative or not."""
    if over_budget:
        return {ClaimResult.DECLINED}
    if evaluation.evaluation_only:
        return {ClaimResult.CONDITIONALLY_COMPATIBLE}
    return {_truthful(evaluation)}


def decline_local(evaluation: LocalEvaluation, over_budget: bool) -> set[ClaimResult]:
    """Refuse to answer on local attributes at all."""
    if over_budget or evaluation.evaluation_only:
        return {ClaimResult.DECLINED}
    return {_truthful(evaluation)}


def randomised(evaluation: LocalEvaluation, over_budget: bool) -> set[ClaimResult]:
    """Coarsen a local answer half the time.

    The shape of [RANI2026]'s mitigation, transplanted: keep the truthful
    answer sometimes so the oracle still discriminates, coarsen it sometimes
    so no single answer is conclusive.
    """
    if over_budget:
        return {ClaimResult.DECLINED}
    if evaluation.evaluation_only:
        return {_truthful(evaluation), ClaimResult.CONDITIONALLY_COMPATIBLE}
    return {_truthful(evaluation)}


POLICIES: dict[str, Policy] = {
    "truthful (no coarsening)": lambda e, b: (
        {ClaimResult.DECLINED} if b else {_truthful(e)}
    ),
    "default (spec 15.4)": default_policy,
    "randomised 50%": randomised,
    "coarsen all local": coarsen_all_local,
    "decline all local": decline_local,
}


# --------------------------------------------------------------------------
# Simulatability, in the sense of [KMN2005]
# --------------------------------------------------------------------------


def decision_of(
    evaluation: LocalEvaluation, policy: Policy, over_budget: bool = False
) -> str:
    """Which of the three moves of Section 15.5 the policy took.

    The answer a policy gives and the *decision* to give it are different
    objects, and only the second is at issue here. A truthful oracle leaks
    through its answers, which is what it is for. What [KMN2005] forbids is a
    decision (to withhold, to blur) that is itself computed from the data
    being protected, because then the choice carries the datum.
    """
    admissible = policy(evaluation, over_budget)
    if len(admissible) > 1:
        return "randomised"
    answer = next(iter(admissible))
    if answer is ClaimResult.DECLINED:
        return "decline"
    if answer is _truthful(evaluation):
        return "truthful"
    return "coarsen"


def is_simulatable(policy: Policy, claim: Claim, candidates) -> bool:
    """Is the policy's decision independent of the private value?

    An attacker that knows the policy can reproduce a simulatable decision
    without the data, so the decision tells it nothing. A decision that
    differs between two candidate values is a channel as wide as the
    answer it was supposed to replace.
    """
    decisions = {
        decision_of(evaluate_claim(build(), claim), policy) for build in candidates
    }
    return len(decisions) == 1


def simulatability_report() -> dict[str, bool]:
    """Every policy in the sweep, classified."""
    claim = Claim(
        key="valuation_floor",
        operator=ClaimOperator.OVERLAPS,
        value={"min": 40_000_000, "max": 60_000_000},
    )
    candidates = [
        (lambda v=v: b_interest(valuation_floor=v))
        for v in (0, 45_000_000, 200_000_000)
    ]
    return {
        name: is_simulatable(policy, claim, candidates)
        for name, policy in POLICIES.items()
    }


# --------------------------------------------------------------------------
# The probing counterparty
# --------------------------------------------------------------------------


def _ask(interest, claim: Claim, policy: Policy, over_budget: bool) -> set[ClaimResult]:
    return policy(evaluate_claim(interest, claim), over_budget)


def _observed(admissible: set[ClaimResult], rng: random.Random) -> ClaimResult:
    return rng.choice(sorted(admissible, key=lambda r: r.value))


@dataclass
class Cell:
    leaked_bits: float
    accuracy: float
    queries_used: int


def probe(policy: Policy, budget: int, seed: int = 7) -> tuple[float, int]:
    """A posterior-driven adversary, distinct from a bisection.

    At each step it asks the question that best splits whichever fact it is
    least sure of, and filters the candidate set by what could have produced
    the answer it saw. By design, an uninformative
    answer costs it a query and nothing else; it will re-ask the same
    question when that is still the best split, which is how a randomised
    policy is defeated; and it never needs to know the policy's internals,
    only what answers the policy admits.
    """
    rng = random.Random(seed)
    true_interest = b_interest()
    floors = set(VALUATION_GRID)
    mgmts = set(MANAGEMENT_OPTIONS)
    asked = 0
    barren_floor = barren_mgmt = 0
    floor_stuck = mgmt_stuck = False

    while asked < budget and (len(floors) > 1 or len(mgmts) > 1):
        if floor_stuck and mgmt_stuck:
            break
        floor_bits = log2(len(floors)) if floors else 0.0
        mgmt_bits = log2(len(mgmts)) if mgmts else 0.0

        on_floor = floor_bits >= mgmt_bits and len(floors) > 1 and not floor_stuck
        on_mgmt = len(mgmts) > 1 and not mgmt_stuck
        if not on_floor and not on_mgmt:
            if len(floors) > 1 and not floor_stuck:
                on_floor = True
            else:
                break

        if on_floor:
            ordered = sorted(floors)
            # The threshold that halves the surviving candidates. Asking the
            # median *candidate* instead of the midpoint of the range is what
            # keeps every query informative; getting this wrong makes the
            # adversary re-ask a question that no longer splits anything.
            threshold = ordered[(len(ordered) - 1) // 2]
            claim = Claim(
                key="valuation_floor",
                operator=ClaimOperator.OVERLAPS,
                value={"min": threshold, "max": threshold},
            )
            observed = _observed(_ask(true_interest, claim, policy, False), rng)
            asked += 1
            narrowed = {
                v
                for v in floors
                if observed in _ask(b_interest(valuation_floor=v), claim, policy, False)
            }
            barren_floor = barren_floor + 1 if narrowed == floors else 0
            floors = narrowed
            floor_stuck = barren_floor >= PATIENCE
        else:
            option = sorted(mgmts)[len(mgmts) // 2]
            claim = Claim(
                key="management_condition", operator=ClaimOperator.EQUALS, value=option
            )
            observed = _observed(_ask(true_interest, claim, policy, False), rng)
            asked += 1
            narrowed = {
                m
                for m in mgmts
                if observed
                in _ask(b_interest(management_condition=m), claim, policy, False)
            }
            barren_mgmt = barren_mgmt + 1 if narrowed == mgmts else 0
            mgmts = narrowed
            mgmt_stuck = barren_mgmt >= PATIENCE

    bits = (log2(len(VALUATION_GRID)) - log2(len(floors))) + (
        log2(len(MANAGEMENT_OPTIONS)) - log2(len(mgmts))
    )
    return bits, asked


def discrimination(policy: Policy, budget: int, seed: int = 7) -> tuple[float, float]:
    """Can an honest session still separate compatible from incompatible?

    Returns (true positive rate, true negative rate). Plain accuracy is
    useless here: most counterparties in the prior are incompatible, so a
    policy that qualifies nobody scores 79% while being worthless. A policy
    is useful only when both rates are high.
    """
    rng = random.Random(seed)
    tp = fn = tn = fp = 0
    for floor in VALUATION_GRID[::2]:
        for mgmt in MANAGEMENT_OPTIONS:
            interest = b_interest(valuation_floor=floor, management_condition=mgmt)
            results = [
                _observed(_ask(interest, claim, policy, index >= budget), rng)
                for index, claim in enumerate(HONEST_CLAIMS)
            ]
            qualified = all(r in QUALIFYING for r in results)
            expected = floor <= A_BUDGET_CEILING and mgmt in A_ACCEPTS_MANAGEMENT
            if expected and qualified:
                tp += 1
            elif expected:
                fn += 1
            elif qualified:
                fp += 1
            else:
                tn += 1
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    return tpr, tnr


def main() -> None:
    budgets = (4, 8, 16, 32, 64)
    print("=" * 96)
    print("Do the anti-inference levers work?")
    print("=" * 96)
    print()
    print("Left: bits a posterior-driven adversary extracts about the valuation")
    print("floor and the management condition, out of 7.94 available.")
    print("Right: true positive rate / true negative rate of an honest session,")
    print("swept across every counterparty in the prior. Both must be high for a")
    print("policy to be worth anything; either alone is trivially achievable.")
    print()
    simulatable = simulatability_report()
    header = f"{'policy':<26}{'simulatable':>13}" + "".join(
        f"{f'budget {b}':>20}" for b in budgets
    )
    print(header)
    print("-" * len(header))
    rows = {}
    for name, policy in POLICIES.items():
        row = f"{name:<26}{'yes' if simulatable[name] else 'NO':>13}"
        for budget in budgets:
            bits, _ = probe(policy, budget)
            tpr, tnr = discrimination(policy, budget)
            row += f"{bits:>8.2f}b {tpr:>4.0%}/{tnr:<4.0%}"
            rows[(name, budget)] = (bits, tpr, tnr)
        print(row)
    print()
    print("=" * 96)
    print("What the sweep says")
    print("=" * 96)
    print()

    d_bits, d_tpr, d_tnr = rows[("default (spec 15.4)", 64)]
    d8 = rows[("default (spec 15.4)", 8)][0]
    t8 = rows[("truthful (no coarsening)", 8)][0]
    c_bits, c_tpr, c_tnr = rows[("coarsen all local", 64)]
    dec = rows[("decline all local", 64)]
    r_bits, r_tpr, r_tnr = rows[("randomised 50%", 64)]

    print("The column that explains the rest is the second one. A decision to")
    print("coarsen or decline is *simulatable* when an attacker who knows the")
    print("policy can reproduce it without the data [KMN2005]; a decision that")
    print("consults the responder's own values carries those values, whatever it")
    print("then says. Exactly one policy in this sweep fails that test, and it is")
    print("the one the specification illustrates: Section 15.4 coarsens when the")
    print("truthful answer would have been affirmative, so the choice to coarsen")
    print("is the affirmative answer, spelled differently. That is the general")
    print("reason behind the identical rows below, and it is a 2005 result and")
    print("not a property of this implementation.")
    print()
    print("The coarsening of Section 15.4 buys a factor but no bound. At a budget")
    print(f"of eight it holds the adversary to {d8:.2f} bits where a purely truthful")
    print(
        f"oracle gives up {t8:.2f}; at an unbounded budget it gives up {d_bits:.2f} all the"
    )
    print(
        f"same, while keeping {d_tpr:.0%}/{d_tnr:.0%}. The only thing standing between a"
    )
    print("counterparty and the private value is how many questions it may ask.")
    print()
    print(
        f"Coarsening every local answer leaks {c_bits:.2f} bits and scores "
        f"{c_tpr:.0%}/{c_tnr:.0%}:"
    )
    print("it qualifies everyone, including every counterparty that should have")
    print("been refused. Declining every local answer leaks nothing either and")
    print(
        f"scores {dec[1]:.0%}/{dec[2]:.0%}: it qualifies no one. Neither is a mitigation;"
    )
    print("both are the oracle switched off, which is Section 24.3's remark about")
    print("discrimination turned into a measurement.")
    print()
    print(f"Randomising half the local answers leaks {r_bits:.2f} bits at an unbounded")
    print(
        f"budget and scores {r_tpr:.0%}/{r_tnr:.0%}. It survives one question and not"
    )
    print("repetition: the adversary here re-asks whichever question still splits")
    print("its hypothesis space, and a coin flipped often enough stops hiding")
    print("anything. [RANI2026]'s policy is randomised against a passive observer")
    print("of traces; this is the adaptive adversary the paper leaves open, and")
    print("transplanting the shape of the mitigation is not enough.")
    print()
    print("The query budget is the only lever in this sweep that bounds anything,")
    print("and the L-3 limit case already showed it cannot be keyed to a")
    print("counterparty when one side faces many. A budget keyed to the asker")
    print("needs an identity the design chooses not to carry.")
    print()
    print("None of this makes the protocol unusable. It makes the open problem")
    print("of Section 24.3 concrete: the levers the specification offers trade")
    print("leakage against discrimination along a curve, and no point on that")
    print("curve is both private and useful without a bound on how many times")
    print("the question may be asked.")


if __name__ == "__main__":
    main()
