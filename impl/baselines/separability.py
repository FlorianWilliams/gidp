"""When does a budget separate an adversary from a customer?

The Sybil demonstration reported that no cap both stopped the attacker and
served the honest counterparty. That was true of the caps it tried, in the
scenario it used, and stating it as a general result would be exactly the kind
of claim this project keeps refusing to accept from itself.

The quantity that decides it is a ratio. An honest session costs one claim per
attribute it cares about. An extraction costs one bisection per *private*
attribute, which is logarithmic in how many values that attribute could take.
A separating budget exists when the second is larger than the first, and the
gap widens with the size of what is being protected.

    python -m baselines.separability
"""

from __future__ import annotations

import sys
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.mitigations import POLICIES, _ask  # noqa: E402
from baselines.scenario import b_interest  # noqa: E402
from gidp.objects import Claim  # noqa: E402
from gidp.vocab import ClaimOperator  # noqa: E402


def extraction_cost(candidates: int, step: int = 5_000_000) -> int:
    """Questions a posterior-driven adversary needs to resolve one threshold.

    Measured against the real evaluator rather than assumed to be log2: a
    bisection over a grid does not always land on a power of two, and the
    demonstration's five-question extraction was one such case.
    """
    policy = POLICIES["default (spec 15.4)"]
    grid = tuple(range(0, candidates * step, step))
    alive = set(grid)
    asked = 0
    while len(alive) > 1 and asked < 64:
        ordered = sorted(alive)
        threshold = ordered[(len(ordered) - 1) // 2]
        claim = Claim(
            key="valuation_floor",
            operator=ClaimOperator.OVERLAPS,
            value={"min": threshold, "max": threshold},
        )
        truth = _ask(b_interest(), claim, policy, False)
        observed = next(iter(truth))
        asked += 1
        alive = {
            v
            for v in alive
            if observed in _ask(b_interest(valuation_floor=v), claim, policy, False)
        }
    return asked


def main() -> None:
    print("=" * 92)
    print("When a budget separates an adversary from a customer")
    print("=" * 92)
    print()
    print("An honest session asks one claim per attribute it cares about. An")
    print("extraction bisects each private attribute. A cap separates them when")
    print("it can sit strictly between the two.")
    print()
    print(
        f"{'private values':>15} {'bits':>6} {'extraction':>12} "
        f"{'honest (5 attrs)':>18} {'separating caps':>18}"
    )
    print("-" * 92)

    for candidates in (8, 16, 41, 128, 512, 2048):
        cost = extraction_cost(candidates)
        honest = 5
        window = [c for c in range(1, cost + 2) if honest <= c < cost]
        shown = f"{window[0]}–{window[-1]}" if window else "none"
        print(
            f"{candidates:>15} {log2(candidates):>6.2f} {cost:>12} "
            f"{honest:>18} {shown:>18}"
        )

    print()
    print("The demonstration used 41 values and an honest session of five")
    print("claims, which is the narrowest case in this table and the reason it")
    print("looked hopeless. It is not a general result: the window opens as")
    print("soon as the secret is worth more than the session that asks about it.")
    print()

    print("=" * 92)
    print("Several private attributes")
    print("=" * 92)
    print()
    print("Each private attribute must be bisected separately, so extraction")
    print("grows with how much is being protected while an honest session does")
    print("not — it asks each attribute once whether it is private or not.")
    print()
    print(f"{'private attrs':>14} {'extraction':>12} {'honest':>9} {'window':>12}")
    print("-" * 92)
    unit = extraction_cost(41)
    for private in (1, 2, 3, 5):
        cost = unit * private
        honest = 5 + private
        window = max(0, cost - honest)
        print(
            f"{private:>14} {cost:>12} {honest:>9} "
            f"{(str(honest) + '–' + str(cost - 1)) if window else 'none':>12}"
        )

    print()
    print("=" * 92)
    print("What this does not fix")
    print("=" * 92)
    print()
    print("A window is not a guarantee. An adversary that stays inside the cap")
    print("gets whatever the cap buys, every time, and an adversary patient")
    print("enough to return tomorrow gets it again unless the cap is a rate")
    print("rather than a total. What the window does say is that the budget is")
    print("a real instrument rather than a gesture, and that its setting is a")
    print("computation rather than a guess: it sits between what a customer")
    print("needs and what the secret costs.")


if __name__ == "__main__":
    main()
