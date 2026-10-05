"""Run the same scenario through five mechanisms and print the comparison.

    python -m baselines.compare

The claim under test is the one the specification makes in prose and had
never verified: that the existing mechanisms do not cover this case. The
result is not a clean win, and the table is printed as it comes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.measure import COUNTERPARTY, OPERATOR, PUBLIC  # noqa: E402
from baselines.mechanisms import MECHANISMS  # noqa: E402
from baselines.scenario import FACTS  # noqa: E402

LINE = "=" * 100
RULE = "-" * 100
TOTAL = sum(f.total_bits for f in FACTS)


def main() -> None:
    outcomes = [m() for m in MECHANISMS]

    print(LINE)
    print("The same question, five mechanisms")
    print(LINE)
    print()
    print("A French company would acquire a German one. The German company is")
    print("not for sale but would consider a transaction above a valuation floor")
    print("it will not state, with a management condition it will not state.")
    print()
    print(
        f"Total private information at stake: {TOTAL:.2f} bits across "
        f"{len(FACTS)} facts."
    )
    print("Leakage is measured identically for every mechanism: the reduction of")
    print("an observer's hypothesis space, in bits. See baselines/measure.py.")
    print()

    print(RULE)
    print(
        f"{'Mechanism':<30} {'Verdict':<14} {'Q':>3} "
        f"{'→counterpty':>12} {'→operator':>10} {'→public':>9}"
    )
    print(RULE)
    for o in outcomes:
        print(
            f"{o.name:<30} {o.verdict:<14} {o.queries:>3} "
            f"{o.ledger.total(COUNTERPARTY):>11.2f}b "
            f"{o.ledger.total(OPERATOR):>9.2f}b "
            f"{o.ledger.total(PUBLIC):>8.2f}b"
        )
    print(RULE)
    print()

    print(RULE)
    print("What each one cannot do")
    print(RULE)
    for o in outcomes:
        print(f"\n{o.name}")
        print(
            f"  presupposes the parties already found each other: "
            f"{'yes' if o.presupposes_rendezvous else 'no'}"
        )
        print(f"  a third party ends up holding both secrets: {o.third_party or 'no'}")
        if o.cannot:
            for item in o.cannot:
                print(f"  cannot: {item}")
        else:
            print("  cannot: nothing in this scenario")
        if o.remark:
            for line in _wrap(o.remark, 92):
                print(f"  {line}")

    print()
    print(LINE)
    print("Reading the table")
    print(LINE)
    print()

    broker, listing, sealed, psi, honest, probing = outcomes

    def cp(outcome) -> float:
        return outcome.ledger.total(COUNTERPARTY)

    print("Against a counterparty that asks what it needs and stops, GIDP gives up")
    print(
        f"{cp(honest):.2f} bits where an ideal sealed comparison gives up {cp(sealed):.2f} and a"
    )
    print(
        f"trusted intermediary {cp(broker):.2f}. Those three are close, and the closeness"
    )
    print("matters: the bit count does not separate them.")
    print()
    print(
        f"The intermediary leaks {broker.ledger.total(OPERATOR):.2f} bits of a possible {TOTAL:.2f} to a third"
    )
    print("party: everything, exactly and permanently, and again for every pair it")
    print("serves. That column is the one GIDP empties, and emptying it is all")
    print("that GIDP buys.")
    print()
    print(
        f"The listing leaks {listing.ledger.total(PUBLIC):.2f} bits to an unbounded and permanent"
    )
    print("audience. That number is of a different kind from the others,")
    print("whatever its size, and for a company that is not for sale it is")
    print("the only number that matters.")
    print()
    print(
        f"Private set intersection leaks the least at {cp(psi):.2f} bits and cannot decide"
    )
    print("the case: the binding conditions here are a threshold and a condition,")
    print("and neither is set membership. The sealed comparison decides it and cannot find the")
    print("counterparty in the first place. Both presuppose the rendezvous that is")
    print("the real problem.")
    print()
    print(
        f"Against a probing counterparty GIDP gives up {cp(probing):.2f} bits in "
        f"{probing.queries} queries,"
    )
    print(
        f"{100 * cp(probing) / TOTAL:.0f}% of everything at stake, more than the intermediary leaks to"
    )
    print("the counterparty, and the intermediary at least knows who it is trusting.")
    print("That is Section 24.3 with a number attached, and it is the strongest")
    print("argument against deploying this protocol as it stands.")
    print()
    print("So the claim the specification makes in prose survives, but narrowly and")
    print("not in the form it was written. GIDP is the only one of the five that")
    print("performs discovery, decides the case, and leaves no third party holding")
    print("both secrets. It is not the most private mechanism here. It is the only")
    print("one that is private *and* has no one to trust, and it holds that only")
    print("for as long as the counterparty's questions are bounded.")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}".strip()
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    main()
