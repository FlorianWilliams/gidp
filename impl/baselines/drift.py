"""Does a secret that moves defeat an attacker that is throttled?

A budget that refills does not separate an adversary from a customer: the
adversary empties the bucket exactly as fast, and the window between the two
is the one `separability.py` already computes. What a rate *does* change is
that extraction now takes time, and a private value that changes over that
time is a moving target.

This measures whether that helps, against the real evaluator, and it is
written to be able to say no.

    python -m baselines.drift

Two adversaries. One knows the value drifts and widens its hypothesis space
each period before narrowing it again. One does not, and keeps narrowing on
answers that have gone stale. The second question turns out to be the more
interesting one: a defence that leaves an attacker *wrong* is worth more than
one that leaves it merely uncertain.
"""

from __future__ import annotations

import random
import sys
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


def _answer(floor: int, threshold: int) -> ClaimResult:
    claim = Claim(
        key="valuation_floor",
        operator=ClaimOperator.WITHIN,
        value={"min": threshold, "max": threshold},
    )
    return next(iter(_ask(b_interest(valuation_floor=floor), claim, POLICY, False)))


def _consistent(candidate: int, threshold: int, observed: ClaimResult) -> bool:
    return _answer(candidate, threshold) is observed


def _widen(alive: set[int], steps: int) -> set[int]:
    """A value that may have moved is a hypothesis space that must grow."""
    out: set[int] = set()
    for value in alive:
        for delta in range(-steps, steps + 1):
            moved = value + delta * STEP
            if GRID[0] <= moved <= GRID[-1]:
                out.add(moved)
    return out


def run(
    periods: int, per_period: int, drift_steps: int, aware: bool, seed: int = 11
) -> tuple[float, bool]:
    """Returns the bits the adversary holds at the end, and whether its best
    guess is actually right."""
    rng = random.Random(seed)
    floor = 45_000_000
    alive = set(GRID)

    for _ in range(periods):
        if drift_steps:
            floor += rng.randint(-drift_steps, drift_steps) * STEP
            floor = min(max(floor, GRID[0]), GRID[-1])
            if aware:
                alive = _widen(alive, drift_steps)

        for _ in range(per_period):
            if len(alive) <= 1:
                break
            ordered = sorted(alive)
            threshold = ordered[(len(ordered) - 1) // 2]
            observed = _answer(floor, threshold)
            narrowed = {v for v in alive if _consistent(v, threshold, observed)}
            # A naive adversary can narrow to nothing once its beliefs are
            # stale. It does not notice; it simply has no hypotheses left.
            alive = narrowed or alive

    bits = log2(len(GRID)) - log2(max(len(alive), 1))
    best = min(alive, key=lambda v: abs(v - floor)) if alive else None
    correct = best == floor and len(alive) == 1
    return bits, correct


def main() -> None:
    total = log2(len(GRID))
    print("=" * 94)
    print("A moving secret against a throttled adversary")
    print("=" * 94)
    print()
    print(f"The floor is one of {len(GRID)} values, {total:.2f} bits. The adversary is")
    print("allowed a few questions per period and the value drifts between")
    print("periods. Twelve periods — a year, if a period is a month.")
    print()
    print(
        f"{'questions/period':>17} {'drift/period':>14} "
        f"{'adversary aware':>17} {'adversary naive':>17}"
    )
    print("-" * 94)

    for per_period in (1, 2, 4):
        for drift in (0, 1, 4):
            aware_bits, _ = run(12, per_period, drift, aware=True)
            naive_bits, naive_right = run(12, per_period, drift, aware=False)
            naive = f"{naive_bits:.2f}b " + ("(right)" if naive_right else "(WRONG)")
            print(f"{per_period:>17} {drift:>14} {aware_bits:>15.2f}b {naive:>17}")

    print()
    print("=" * 94)
    print("What this says")
    print("=" * 94)
    print()
    print("Read the `drift 0` rows first: with a static secret the throttle only")
    print("delays. Twelve periods at one question each is twelve questions, and")
    print("twelve questions are more than this secret is worth. A rate buys time")
    print("and nothing else, which is what the arithmetic said before the")
    print("simulation ran.")
    print()
    print("Drift changes the shape rather than the amount. An adversary that")
    print("knows the value moves must widen its hypotheses every period, and")
    print("what it narrows it loses again; the residue is the fixed point of")
    print("those two operations and it does not go to zero. The formula is")
    print("2d / (2^r - 1) candidates surviving, which is exponential in the")
    print("questions allowed and only linear in the drift: halving the rate is")
    print("worth far more than doubling how fast the secret moves.")
    print()
    print("The naive column is the one worth taking away. An adversary that")
    print("keeps narrowing on answers that have gone stale does not end up")
    print("uncertain, it ends up confident and wrong — and an adversary acting")
    print("on a wrong valuation floor is in a worse position than one that")
    print("knows it does not know. Nothing in this protocol produces that")
    print("effect; a Principal who revises its thresholds does.")
    print()
    print("So time is not the separator it looked like. It is a way of making")
    print("the throttle mean something: a rate low enough that extraction takes")
    print("longer than the secret stays true. That is a deployment property,")
    print("not a protocol one, and Section 9.2's validity window is where a")
    print("Standing Interest already says how long it is good for.")


if __name__ == "__main__":
    main()
