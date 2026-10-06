"""The bound-utility frontier, measured.

Section 24.3's open problem used to be "is there a bound". There is one, and
the question became "is there a better one": a policy that holds an adversary
as low while refusing fewer honest counterparties. That question is answered
by measurement: two numbers per policy, on axes everyone agrees on,
so that any proposal can be dropped in and compared.

    python -m baselines.frontier

Axes. Leak: bits a probing counterparty extracts about the threshold,
lower better. Service: honest counterparties served out of forty, higher
better. A policy is dominated when another leaks no more and serves no fewer.

Four families are measured, including one from `open-problems.md` that had
never been tried.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.auditing import GRID, STEP, TOTAL_BITS, _answer_of  # noqa: E402
from baselines.scenario import b_interest  # noqa: E402
from gidp.auditing import GranularityLattice  # noqa: E402
from gidp.objects import Claim  # noqa: E402
from gidp.vocab import ClaimOperator, ClaimResult  # noqa: E402

FLOOR = 45_000_000
HONEST = 40


def _lattice_admits(width: int, claim: Claim) -> bool:
    lattice = GranularityLattice(widths={"valuation_floor": width})
    return lattice.admits(claim, b_interest(valuation_floor=FLOOR))


def _cell_question(edge: int) -> Claim:
    """Is the threshold below `edge`? Asked as a band of whole cells,
    which is the only form the lattice admits (P-05): everything up to the
    last value of the cell before `edge`."""
    return Claim(
        key="valuation_floor",
        operator=ClaimOperator.OVERLAPS,
        value={"max": edge - 1},
    )


@dataclass
class Policy:
    """A responder's rule for what it will answer."""

    name: str
    answered: int = 0
    posterior: set[int] = field(default_factory=lambda: set(GRID))

    def admits(self, claim: Claim) -> bool:
        return True

    def record(self, claim: Claim, answer: ClaimResult) -> None:
        self.answered += 1
        self.posterior = {
            v for v in self.posterior if _answer_of(v, claim) is answer
        } or self.posterior


@dataclass
class QuestionBudget(Policy):
    """The one every earlier measurement here used."""

    limit: int = 8

    def admits(self, claim: Claim) -> bool:
        return self.answered < self.limit


@dataclass
class BitBudget(Policy):
    """Refuse when the worst case would cross a budget of disclosure."""

    budget: float = 2.0

    def admits(self, claim: Claim) -> bool:
        for answer in (
            ClaimResult.COMPATIBLE,
            ClaimResult.CONDITIONALLY_COMPATIBLE,
            ClaimResult.INCOMPATIBLE,
        ):
            after = {v for v in self.posterior if _answer_of(v, claim) is answer}
            if after and TOTAL_BITS - log2(len(after)) > self.budget:
                return False
        return True


@dataclass
class GranularityFloor(Policy):
    """`open-problems.md`'s minimum granularity, finally measured.

    A bound is probed at the edge of whatever band is asked, so constraining
    the *width* of a band achieves nothing: the edge is still wherever the
    querent puts it. Constraining where the edges may fall is different: if
    every bound must be a multiple of w, no sequence of questions locates the
    value more precisely than w, however many are asked.

    It holds no state at all, which is its main property: honest
    traffic does not deplete it, and it cannot be drained.
    """

    width: int = 20_000_000

    def admits(self, claim: Claim) -> bool:
        # The library's control, not a model of it (P-08): what is measured
        # here is what an Agent configured with this width would decline.
        return _lattice_admits(self.width, claim)


@dataclass
class Both(BitBudget):
    """A stateless floor for the hard bound, a budget for the rest."""

    width: int = 20_000_000

    def admits(self, claim: Claim) -> bool:
        if not _lattice_admits(self.width, claim):
            return False
        return super().admits(claim)


# ---------------------------------------------------------------------------


def _probe(policy: Policy, attempts: int = 40) -> float:
    """An adversary that respects whatever the policy allows.

    It bisects on the finest lattice the policy will answer on, which is the
    fair way to measure a granularity floor: an adversary does not keep
    asking questions it knows will be refused.
    """
    lattice = getattr(policy, "width", STEP)
    alive = {v for v in GRID}
    for _ in range(attempts):
        if len(alive) <= 1:
            break
        ordered = sorted(alive)
        raw = ordered[(len(ordered) - 1) // 2]
        threshold = (raw // lattice) * lattice
        if hasattr(policy, "width"):
            # Under a lattice the only admissible question is a band of whole
            # cells: "is the threshold at or below the cell ending here?"
            claim = _cell_question(threshold + lattice)
        else:
            claim = Claim(
                key="valuation_floor",
                operator=ClaimOperator.OVERLAPS,
                value={"min": threshold, "max": threshold},
            )
        if not policy.admits(claim):
            break
        answer = _answer_of(FLOOR, claim)
        policy.record(claim, answer)
        narrowed = {v for v in alive if _answer_of(v, claim) is answer}
        if narrowed == alive:
            break  # this question buys nothing; stop
        alive = narrowed
    return TOTAL_BITS - log2(max(len(alive), 1))


def _serve(policy: Policy, seed: int = 5) -> int:
    """Forty counterparties, each asking once whether its ceiling clears."""
    rng = random.Random(seed)
    lattice = getattr(policy, "width", STEP)
    served = 0
    for _ in range(HONEST):
        ceiling = rng.choice(GRID[8:])
        # A customer rounds to fit: everything up to the last value of the
        # cell its ceiling falls in.
        edge = (ceiling // lattice + 1) * lattice
        claim = Claim(
            key="valuation_floor",
            operator=ClaimOperator.OVERLAPS,
            value={"min": 0, "max": edge - 1},
        )
        if policy.admits(claim):
            policy.record(claim, _answer_of(FLOOR, claim))
            served += 1
    return served


def measure(build) -> tuple[float, int]:
    return _probe(build()), _serve(build())


def main() -> None:
    print("=" * 88)
    print("The bound-utility frontier")
    print("=" * 88)
    print()
    print(f"A {TOTAL_BITS:.2f}-bit threshold. Leak: what a probing counterparty")
    print(
        f"extracts. Service: how many of {HONEST} honest counterparties are answered."
    )
    print()

    candidates: list[tuple[str, float, int]] = []
    candidates.append(("no defence", *measure(lambda: Policy("none"))))
    for limit in (2, 4, 8):
        candidates.append(
            (
                f"questions <= {limit}",
                *measure(lambda n=limit: QuestionBudget("q", limit=n)),
            )
        )
    for budget in (1.0, 2.0, 3.0):
        candidates.append(
            (
                f"bits <= {budget:.0f}",
                *measure(lambda b=budget: BitBudget("b", budget=b)),
            )
        )
    for width in (10, 20, 40):
        candidates.append(
            (
                f"granularity {width}M",
                *measure(lambda w=width: GranularityFloor("g", width=w * 1_000_000)),
            )
        )
    for width, budget in ((20, 3.0), (40, 3.0)):
        candidates.append(
            (
                f"granularity {width}M + bits <= {budget:.0f}",
                *measure(
                    lambda w=width, b=budget: Both("x", budget=b, width=w * 1_000_000)
                ),
            )
        )

    print(f"{'policy':<34} {'leak':>8} {'service':>9} {'':>4}")
    print("-" * 88)
    for name, leak, served in candidates:
        dominated = any(
            other_leak <= leak
            and other_served >= served
            and (other_leak < leak or other_served > served)
            for other_name, other_leak, other_served in candidates
            if other_name != name
        )
        mark = "" if not dominated else "dominated"
        print(f"{name:<34} {leak:>7.2f}b {served:>6}/{HONEST} {mark:>12}")

    print()
    print("=" * 88)
    print("Reading it")
    print("=" * 88)
    print()
    best = [
        c
        for c in candidates
        if not any(
            o[1] <= c[1] and o[2] >= c[2] and (o[1] < c[1] or o[2] > c[2])
            for o in candidates
            if o[0] != c[0]
        )
    ]
    print("On the frontier:")
    for name, leak, served in sorted(best, key=lambda c: c[1]):
        print(f"  {name:<34} {leak:>6.2f}b  {served}/{HONEST}")
    print()
    print("The granularity floor is the main result here, and it had")
    print("never been measured. It holds no state, so honest traffic does not")
    print("deplete it and an adversary cannot drain it; and because a bound is")
    print("probed at the edge of whatever band is asked, constraining where the")
    print("edges may fall caps the resolution at one cell however many questions")
    print("are asked. What a cell is worth depends on how many possible values it")
    print("holds: about log2(cells) bits when they are spread evenly, all of it")
    print("when a cell holds one. Its cost is that a customer must")
    print("round its question to the lattice, which is a real loss of precision")
    print("but not a refusal.")
    print()
    print("This table is an instrument for comparing policies. A policy that lands")
    print("below and to the right of everything here is an improvement, and")
    print("adding one is a subclass and a line.")


if __name__ == "__main__":
    main()
