"""The mechanism [KMN2005] actually prescribes, applied here.

Everything measured so far tried to bound leakage by counting questions. A
question is the wrong unit. An honest counterparty asks one wide band and
learns almost nothing; an extractor asks a narrowing sequence and learns
everything. Counted in questions those two look alike, which is why no
threshold separated them. Counted in *bits* they do not look alike at all.

Simulatable auditing says the decision to answer or refuse must depend only
on the queries asked and the answers already given — never on the datum being
protected — so that an attacker able to reproduce the decision learns nothing
from a refusal. That is implementable here, exactly, and it is automatic: no
identity, no operator, no human, nothing carried across sessions but the
responder's own record of what it has already said.

The responder keeps the posterior an observer would hold: the set of values
still consistent with everything it has answered. Before answering a new
claim it asks what that posterior would become *under every answer it might
give*, and refuses if the worst case would cross its budget. Taking the worst
case is what keeps the decision independent of the actual value.

    python -m baselines.auditing
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.mitigations import POLICIES, _ask  # noqa: E402
from baselines.scenario import b_interest  # noqa: E402
from gidp.objects import Claim  # noqa: E402
from gidp.vocab import ClaimOperator, ClaimResult  # noqa: E402

STEP = 5_000_000
GRID = tuple(range(0, 205_000_000, STEP))
POLICY = POLICIES["default (spec 15.4)"]
TOTAL_BITS = log2(len(GRID))


def _answer_of(floor: int, claim: Claim) -> ClaimResult:
    return next(iter(_ask(b_interest(valuation_floor=floor), claim, POLICY, False)))


@dataclass
class Auditor:
    """A budget denominated in bits, not in questions.

    `posterior` is what an observer knows, held by the responder so that it
    can see what it is giving away. It is not secret: the observer has it too,
    which is precisely what makes a refusal computed from it uninformative.
    """

    budget_bits: float = 2.0
    posterior: set[int] = field(default_factory=lambda: set(GRID))
    refusals: int = 0
    answers: int = 0

    @property
    def disclosed(self) -> float:
        return TOTAL_BITS - log2(max(len(self.posterior), 1))

    def _would_become(self, claim: Claim, answer: ClaimResult) -> set[int]:
        return {v for v in self.posterior if _answer_of(v, claim) is answer}

    def admits(self, claim: Claim) -> bool:
        """Would answering this cross the budget, under any answer at all?"""
        for answer in (
            ClaimResult.COMPATIBLE,
            ClaimResult.CONDITIONALLY_COMPATIBLE,
            ClaimResult.INCOMPATIBLE,
        ):
            after = self._would_become(claim, answer)
            if not after:
                continue
            if TOTAL_BITS - log2(len(after)) > self.budget_bits:
                return False
        return True

    def ask(self, floor: int, claim: Claim) -> ClaimResult | None:
        if not self.admits(claim):
            self.refusals += 1
            return None
        answer = _answer_of(floor, claim)
        self.posterior = self._would_become(claim, answer) or self.posterior
        self.answers += 1
        return answer


def extractor(auditor: Auditor, floor: int, attempts: int = 40) -> None:
    """Bisect until refused."""
    alive = set(GRID)
    for _ in range(attempts):
        if len(alive) <= 1:
            return
        ordered = sorted(alive)
        threshold = ordered[(len(ordered) - 1) // 2]
        claim = Claim(
            key="valuation_floor",
            operator=ClaimOperator.OVERLAPS,
            value={"min": threshold, "max": threshold},
        )
        answer = auditor.ask(floor, claim)
        if answer is None:
            return
        alive = {v for v in alive if _answer_of(v, claim) is answer}


def honest(auditor: Auditor, floor: int, counterparties: int, seed: int = 5) -> int:
    """Each asks once, about the band it can actually pay."""
    rng = random.Random(seed)
    served = 0
    for _ in range(counterparties):
        ceiling = rng.choice(GRID[8:])
        claim = Claim(
            key="valuation_floor",
            operator=ClaimOperator.OVERLAPS,
            value={"min": 0, "max": ceiling},
        )
        if auditor.ask(floor, claim) is not None:
            served += 1
    return served


def main() -> None:
    floor = 45_000_000
    print("=" * 92)
    print("A budget in bits, audited simulatably")
    print("=" * 92)
    print()
    print(
        f"The floor is one of {len(GRID)} values, {TOTAL_BITS:.2f} bits. The responder"
    )
    print("refuses a claim whose worst-case answer would take an observer past")
    print("its budget. The decision uses only the questions asked and the")
    print("answers already given, so an observer can reproduce it and learns")
    print("nothing from being refused [KMN2005].")
    print()
    print(
        f"{'budget':>8} {'extractor gets':>16} {'its questions':>15} "
        f"{'honest served':>16} {'of':>4}"
    )
    print("-" * 92)

    for budget in (1.0, 2.0, 3.0, 4.0, 5.36):
        attacker = Auditor(budget_bits=budget)
        extractor(attacker, floor)

        customers = Auditor(budget_bits=budget)
        served = honest(customers, floor, counterparties=40)

        print(
            f"{budget:>8.2f} {attacker.disclosed:>15.2f}b "
            f"{attacker.answers:>15} {served:>16} {40:>4}"
        )

    print()
    print("=" * 92)
    print("Why the unit was the whole problem")
    print("=" * 92)
    print()
    print("An honest counterparty asks whether its ceiling clears the floor.")
    print("That is one question over a wide band and it costs a fraction of a")
    print("bit, so forty of them cost about what two of them cost. An extractor")
    print("asks a narrowing sequence, and each question costs a full bit by")
    print("construction — that is what bisection *is*. Counted in questions the")
    print("two populations overlap and no threshold separates them, which is")
    print("what every earlier measurement here reported. Counted in bits they")
    print("are not the same population at all.")
    print()
    print("The refusal is also honest in the technical sense. It is computed")
    print("from what the observer already knows, never from the value, so it")
    print("cannot be read as a signal about the value. An auditor that refused")
    print("because of the datum would be the leak it was built to stop, which")
    print("is the 2005 result this implements rather than rediscovers.")
    print()
    print("What it does not do: stop an adversary that accepts the budget and")
    print("takes what it buys. A budget of two bits gives away two bits, to")
    print("everyone, for ever. It bounds; it does not protect.")


if __name__ == "__main__":
    main()
