"""Section 24.4, demonstrated rather than asserted.

The specification says an attacker may operate many Agents or Principals to
bypass query limits, and Section 24.3 offers query budgets as the mitigation
against probing. The mitigation sweep in `mitigations.py` then found that a
budget is the *only* lever that bounds anything. Both statements cannot be
comfortable at once, and neither had been measured.

    python -m baselines.sybil

Two questions. Does a budget keyed to the counterparty bound anything at all
against an adversary that can mint counterparties? And is there any budget
that does — including ones the specification does not currently offer?
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.mitigations import POLICIES, Policy, _ask, _observed  # noqa: E402
from baselines.scenario import (  # noqa: E402
    B_MANAGEMENT as B_TRUE_MGMT,
)
from baselines.scenario import (
    B_VALUATION_FLOOR as B_TRUE_FLOOR,
)
from baselines.scenario import (
    MANAGEMENT_OPTIONS,
    VALUATION_GRID,
    b_interest,
)
from gidp.objects import Claim  # noqa: E402
from gidp.vocab import ClaimOperator, ClaimResult  # noqa: E402


@dataclass
class Oracle:
    """A responder that meters answers, and the two ways it can meter them.

    ``per_counterparty`` is what Section 24.3 offers: each session, with each
    counterparty, gets its own allowance. ``global_budget`` is not in GIDP 0.1
    at all: a cap on what the responder will answer in total, to anyone, over
    the life of the Standing Interest.
    """

    policy: Policy
    per_counterparty: int
    global_budget: int | None = None
    spent: dict[str, int] = field(default_factory=dict)
    spent_total: int = 0

    def over_budget(self, asker: str) -> bool:
        if self.global_budget is not None and self.spent_total >= self.global_budget:
            return True
        return self.spent.get(asker, 0) >= self.per_counterparty

    def charge(self, asker: str) -> None:
        self.spent[asker] = self.spent.get(asker, 0) + 1
        self.spent_total += 1

    def admissible(self, interest, claim: Claim, asker: str) -> set[ClaimResult]:
        return _ask(interest, claim, self.policy, self.over_budget(asker))


@dataclass
class Attack:
    bits: float
    questions_asked: int
    questions_answered: int
    identities_used: int


def probe_with_identities(
    policy: Policy,
    per_counterparty: int,
    identities: int,
    global_budget: int | None = None,
    seed: int = 7,
) -> Attack:
    """One adversary, many faces, one hypothesis space.

    The identities are a costume. The adversary's knowledge is shared across
    them, because nothing in the protocol ties a question asked under one
    opaque endpoint to the same question asked under another.
    """
    rng = random.Random(seed)
    oracle = Oracle(policy, per_counterparty, global_budget)
    true_interest = b_interest()
    floors, mgmts = set(VALUATION_GRID), set(MANAGEMENT_OPTIONS)
    asked = answered = 0
    barren = 0

    for index in range(identities):
        asker = f"agent:opaque:sybil-{index}"
        while not oracle.over_budget(asker) and (len(floors) > 1 or len(mgmts) > 1):
            if barren >= 12:
                break
            floor_bits = log2(len(floors))
            mgmt_bits = log2(len(mgmts))
            if floor_bits >= mgmt_bits and len(floors) > 1:
                threshold = sorted(floors)[(len(floors) - 1) // 2]
                claim = Claim(
                    key="valuation_floor",
                    operator=ClaimOperator.WITHIN,
                    value={"min": threshold, "max": threshold},
                )
            else:
                claim = Claim(
                    key="management_condition",
                    operator=ClaimOperator.EQUALS,
                    value=sorted(mgmts)[len(mgmts) // 2],
                )

            # Freeze the oracle's state before charging for the question.
            # The filter must ask what each candidate would have answered
            # under the *same* budget state that produced the answer seen;
            # reading it back after charging compares against a responder
            # that has already moved on, and eliminates the truth itself.
            over = oracle.over_budget(asker)
            observed = _observed(_ask(true_interest, claim, policy, over), rng)
            oracle.charge(asker)
            asked += 1
            if observed is not ClaimResult.DECLINED:
                answered += 1

            if claim.key == "valuation_floor":
                narrowed = {
                    v
                    for v in floors
                    if observed
                    in _ask(b_interest(valuation_floor=v), claim, policy, over)
                }
                assert B_TRUE_FLOOR in narrowed, "the filter ruled out the truth"
                barren = barren + 1 if narrowed == floors else 0
                floors = narrowed
            else:
                narrowed = {
                    m
                    for m in mgmts
                    if observed
                    in _ask(b_interest(management_condition=m), claim, policy, over)
                }
                assert B_TRUE_MGMT in narrowed, "the filter ruled out the truth"
                barren = barren + 1 if narrowed == mgmts else 0
                mgmts = narrowed

        if len(floors) == 1 and len(mgmts) == 1:
            return Attack(_bits(floors, mgmts), asked, answered, index + 1)

    return Attack(_bits(floors, mgmts), asked, answered, identities)


def _bits(floors: set, mgmts: set) -> float:
    return (log2(len(VALUATION_GRID)) - log2(len(floors))) + (
        log2(len(MANAGEMENT_OPTIONS)) - log2(len(mgmts))
    )


def honest_sessions_served(
    policy: Policy,
    per_counterparty: int,
    global_budget: int | None,
    honest: int = 30,
) -> int:
    """How many genuine counterparties the responder can still serve.

    A global budget is only a mitigation if the cost of it is stated. Each
    honest counterparty asks the six claims of a normal session; once the
    responder has gone silent, the sessions that follow cannot qualify.
    """
    from baselines.mechanisms import HONEST_CLAIMS

    rng = random.Random(11)
    oracle = Oracle(policy, per_counterparty, global_budget)
    interest = b_interest()
    served = 0
    for index in range(honest):
        asker = f"agent:opaque:honest-{index}"
        results = []
        for claim in HONEST_CLAIMS:
            results.append(_observed(oracle.admissible(interest, claim, asker), rng))
            oracle.charge(asker)
        if all(r is not ClaimResult.DECLINED for r in results):
            served += 1
    return served


TOTAL = log2(len(VALUATION_GRID)) + log2(len(MANAGEMENT_OPTIONS))


def main() -> None:
    policy = POLICIES["default (spec 15.4)"]

    print("=" * 92)
    print("Section 24.4: what a budget keyed to the counterparty is worth")
    print("=" * 92)
    print()
    print(f"{TOTAL:.2f} bits are at stake. The responder allows each counterparty a")
    print("fixed number of answered claims. The adversary mints counterparties.")
    print()
    print(
        f"{'budget per counterparty':>24} {'identities':>11} {'asked':>7} "
        f"{'answered':>9} {'bits':>7}"
    )
    print("-" * 92)
    for per in (2, 4, 8):
        for identities in (1, 2, 4, 8, 16):
            attack = probe_with_identities(policy, per, identities)
            print(
                f"{per:>24} {identities:>11} {attack.questions_asked:>7} "
                f"{attack.questions_answered:>9} {attack.bits:>7.2f}"
            )
    print()
    print("The bits track the product, not the budget. A counterparty allowance of")
    print("two, which looks severe, is undone by four identities. Nothing in the")
    print("protocol connects the two, because opaque endpoints are the point: the")
    print("same property that stops a responder profiling its counterparties stops")
    print("it recognising that it is being profiled.")
    print()

    print("=" * 92)
    print("A budget the specification does not offer: capped total disclosure")
    print("=" * 92)
    print()
    print("The responder caps what it will answer in total, to anyone, over the")
    print("life of the Standing Interest. Identities cannot dilute a cap that is")
    print("not keyed to them.")
    print()
    print("An honest session in this scenario costs six claims, so the per-")
    print("counterparty allowance is set to six: the cap below is the only")
    print("thing rationing anything.")
    print()
    print(
        f"{'global cap':>12} {'bits extracted':>16} {'answered':>10} "
        f"{'honest sessions served (of 30)':>32}"
    )
    print("-" * 92)
    for cap in (4, 6, 7, 12, 24, 60, None):
        attack = probe_with_identities(
            policy, per_counterparty=6, identities=64, global_budget=cap
        )
        served = honest_sessions_served(policy, 6, cap)
        label = str(cap) if cap is not None else "none"
        print(
            f"{label:>12} {attack.bits:>15.2f}b {attack.questions_answered:>10} "
            f"{served:>32}"
        )
    print()
    print("It bounds, and the price is not a tuning parameter. The adversary needs")
    print("seven answered claims to take the whole secret. An honest session costs")
    print("six. Any cap generous enough to serve two honest counterparties has")
    print("already paid for a complete extraction, and a cap mean enough to stop")
    print("the extraction serves nobody. There is no setting in between, because")
    print("the responder cannot tell the two populations apart while it answers")
    print("them — which is the same blindness that made the per-counterparty")
    print("budget worthless one table up, arriving from the other direction.")
    print()
    print("=" * 92)
    print("What this adds to the open problem")
    print("=" * 92)
    print()
    print("Section 24.3 names query budgets as the mitigation against probing and")
    print("Section 24.4 names Sybil identities as the way around them. Read")
    print("together they say that GIDP 0.1's only bounding lever is bypassed by a")
    print("threat the same document acknowledges. That is now measured rather")
    print("than implied, and it narrows the open problem usefully: a responder")
    print("policy that bounds adaptive leakage must either meter something other")
    print("than the asker's identity, or accept refusing honest counterparties")
    print("at a rate it cannot distinguish from refusing adversaries.")


if __name__ == "__main__":
    main()
