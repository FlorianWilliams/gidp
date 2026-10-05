"""Section 11.4 says there is a fundamental trade-off. This module measures it.

    "Agents SHOULD minimise projections while preserving sufficient retrieval
    quality. This is a fundamental trade-off: more specific projections
    improve retrieval and increase inference risk; less specific projections
    do the reverse. GIDP 0.1 does not prescribe an optimum."

The specification asserts this without showing it, and the shape of the curve
decides whether the advice is useful. To run it:

    python -m baselines.projection

The finding is that coarsening does not reduce a publisher's exposure so much
as move it: a vaguer projection discloses less to the index and is retrieved
by more querents, each of whom opens a session and probes. Total exposure is
therefore U-shaped, it has a computable minimum for a given population, and
at the coarse end it is *worse* than publishing precisely.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from math import log2
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SECTORS = (
    "enterprise_software",
    "climate_hardware",
    "medtech",
    "logistics",
    "fintech",
    "industrial",
    "consumer",
    "energy",
)
CITIES = {
    "paris": "fr",
    "lyon": "fr",
    "toulouse": "fr",
    "nantes": "fr",
    "berlin": "de",
    "munich": "de",
    "hamburg": "de",
    "cologne": "de",
    "milan": "it",
    "rome": "it",
    "turin": "it",
    "bologna": "it",
    "madrid": "es",
    "barcelona": "es",
    "valencia": "es",
    "seville": "es",
    "amsterdam": "nl",
    "rotterdam": "nl",
    "utrecht": "nl",
    "eindhoven": "nl",
}
SIZE_BUCKETS = tuple(range(6))
DIRECTIONS = ("acquire", "divest")

#: What a publisher risks, before anyone reads anything.
PRIOR_BITS = log2(len(SECTORS)) + log2(len(CITIES)) + log2(len(SIZE_BUCKETS)) + 1.0

#: Measured: the private facts an honest six-claim session gives
#: up to its counterparty, from `baselines.mechanisms.gidp_honest` with the two
#: existence bits removed, since being in the index already conceded those.
SESSION_BITS = 2.30


@dataclass(frozen=True)
class Interest:
    sector: str
    city: str
    size: int
    direction: str


@dataclass(frozen=True)
class Level:
    name: str
    #: bits the projection concedes to anyone who can read the index
    projection_bits: float
    #: how a candidate is judged retrievable at this coarseness
    matches: object


def population(count: int = 400, seed: int = 3) -> list[Interest]:
    rng = random.Random(seed)
    return [
        Interest(
            rng.choice(SECTORS),
            rng.choice(list(CITIES)),
            rng.choice(SIZE_BUCKETS),
            rng.choice(DIRECTIONS),
        )
        for _ in range(count)
    ]


def queries(count: int = 300, seed: int = 5) -> list[Interest]:
    """The other side of the index.

    A publisher is not read by one querent. It is read by everyone whose
    query its projection answers, and that is the quantity a coarsening
    decision moves.
    """
    rng = random.Random(seed)
    return [
        Interest(
            rng.choice(SECTORS),
            rng.choice(list(CITIES)),
            rng.choice(SIZE_BUCKETS),
            rng.choice(DIRECTIONS),
        )
        for _ in range(count)
    ]


#: The private facts behind a projection, from `baselines.scenario`: a
#: valuation threshold and a categorical condition. Exposure saturates here,
#: because no number of sessions extracts more than exists.
PRIVATE_BITS = 7.94


def _opposite(direction: str) -> str:
    return "divest" if direction == "acquire" else "acquire"


def truly_relevant(candidate: Interest, query: Interest) -> bool:
    """What a querent wants: same sector, same country, adjacent
    size, opposite direction."""
    return (
        candidate.sector == query.sector
        and CITIES[candidate.city] == CITIES[query.city]
        and abs(candidate.size - query.size) <= 1
        and candidate.direction == _opposite(query.direction)
    )


def resolving(level: Level) -> Level:
    """The same publisher, read by a provider that understands the vocabulary.

    `InMemoryProvider` matches retrieval attributes by exact token equality:
    a publisher that said `munich` is never returned to a querent that said
    `germany`. That is not a property of the protocol (Section 12 leaves
    retrieval to the provider and Section 5 puts domain ontologies out of
    scope), but it is a property of every number this harness produces, so
    the alternative has to be measured instead of assumed away.

    This variant resolves both sides of the geography to the coarsest common
    level before comparing, which is the cheapest thing a provider can do
    that deserves to be called semantic: no embeddings, no ontology, one
    hierarchy.
    """

    def matches(c: Interest, q: Interest) -> bool:
        return (
            (
                c.sector == q.sector
                and CITIES[c.city] == CITIES[q.city]
                and abs(c.size - q.size) <= 1
                and c.direction == _opposite(q.direction)
            )
            if level is LEVELS[0]
            else level.matches(c, q)
        )

    return Level(level.name + "  + resolving provider", level.projection_bits, matches)


LEVELS = (
    Level(
        "L0  everything, exactly",
        PRIOR_BITS,
        lambda c, q: (
            c.sector == q.sector
            and c.city == q.city
            and abs(c.size - q.size) <= 1
            and c.direction == _opposite(q.direction)
        ),
    ),
    Level(
        "L1  city generalised to country",
        log2(len(SECTORS)) + log2(5) + log2(len(SIZE_BUCKETS)) + 1.0,
        lambda c, q: (
            c.sector == q.sector
            and CITIES[c.city] == CITIES[q.city]
            and abs(c.size - q.size) <= 1
            and c.direction == _opposite(q.direction)
        ),
    ),
    Level(
        "L2  + size bucketed coarsely",
        log2(len(SECTORS)) + log2(5) + log2(2) + 1.0,
        lambda c, q: (
            c.sector == q.sector
            and CITIES[c.city] == CITIES[q.city]
            and (c.size // 3) == (q.size // 3)
            and c.direction == _opposite(q.direction)
        ),
    ),
    Level(
        "L3  + direction made symmetric",
        log2(len(SECTORS)) + log2(5) + log2(2),
        lambda c, q: (
            c.sector == q.sector
            and CITIES[c.city] == CITIES[q.city]
            and (c.size // 3) == (q.size // 3)
        ),
    ),
    Level(
        "L4  sector and category only",
        log2(len(SECTORS)),
        lambda c, q: c.sector == q.sector,
    ),
)


def _measure(level, people, asks, matchable):
    found = retrievals = 0
    for q in asks:
        retrieved = [c for c in people if level.matches(c, q)]
        found += sum(1 for c in retrieved if truly_relevant(c, q))
        retrievals += len(retrieved)
    recall = found / matchable if matchable else 0.0
    sessions = retrievals / len(people)
    drained = min(1.0, sessions * SESSION_BITS / PRIVATE_BITS)
    return recall, sessions, drained


def main() -> None:
    people = population(2_000)
    asks = queries(300)
    truth = {id(q): [c for c in people if truly_relevant(c, q)] for q in asks}
    matchable = sum(len(v) for v in truth.values())

    print("=" * 98)
    print("Section 11.4: the projection trade-off, measured")
    print("=" * 98)
    print()
    print(
        f"{len(people)} published interests, {len(asks)} querents searching the index,"
    )
    print(f"{matchable} genuine matches to be found across every query.")
    print()
    print(
        f"A publisher concedes bits to the index by publishing, and "
        f"{SESSION_BITS:.2f} more to"
    )
    print(
        f"each querent that opens a session. It has {PRIVATE_BITS:.2f} bits of private"
    )
    print("facts to lose in total, so the session column saturates: past a certain")
    print("number of counterparties there is nothing left to take.")
    print()
    print(
        f"{'coarsening':<32} {'index':>7} {'recall':>8} "
        f"{'sessions/publisher':>20} {'private facts lost':>20}"
    )
    print("-" * 98)

    rows = []
    for level in LEVELS:
        recall, sessions, drained = _measure(level, people, asks, matchable)
        rows.append((level, recall, sessions, drained))
        print(
            f"{level.name:<32} {level.projection_bits:>6.2f}b {recall:>8.0%} "
            f"{sessions:>20.1f} {drained:>19.0%}"
        )

    print()
    print("=" * 98)
    print("What the curve says")
    print("=" * 98)
    print()

    usable = [r for r in rows if r[1] >= 0.8 and r[3] < 1.0]
    print("Both ends are bad, and they are bad for different reasons.")
    print()
    print(
        f"At the precise end, {rows[0][0].name.strip()} concedes the most to the index"
    )
    print(
        f"and finds only {rows[0][1]:.0%} of the matches available to it. That is the"
    )
    print("result Section 11.4 does not lead a reader to expect: an over-precise")
    print("projection is risky and is also *retrieved less*, because it only")
    print("answers querents who happened to describe the target in the same terms.")
    print("Precision in a projection does not mean accuracy; it means a narrower agreement")
    print("about vocabulary, and a querent who says `germany` never meets a")
    print("publisher who said `munich`.")
    print()
    print(
        f"At the vague end, {rows[-1][0].name.strip()} concedes the least "
        f"({rows[-1][0].projection_bits:.2f} bits)"
    )
    print(
        f"and is retrieved {rows[-1][2]:.0f} times per publisher. At "
        f"{SESSION_BITS:.2f} bits a session that is"
    )
    print("total extraction: the publisher keeps nothing, and it kept nothing by")
    print("following the advice to minimise. The index disclosure it saved is the")
    print("cheapest part of what it had.")
    print()
    if usable:
        band = ", ".join(r[0].name.strip().split("  ")[0] for r in usable)
        print(f"What is left is a band ({band}) where recall is high and the")
        print("publisher is not drained. That band is the stopping rule Section 11.4")
        print("is missing. It is not a constant: it is wherever the marginal session")
        print("costs more than the marginal index disclosure saves, which depends")
        print("on how crowded the index is.")
    resolved = resolving(LEVELS[0])
    r_recall, r_sessions, r_drained = _measure(resolved, people, asks, matchable)
    print()
    print("-" * 98)
    print(
        f"{resolved.name:<32} {resolved.projection_bits:>6.2f}b {r_recall:>8.0%} "
        f"{r_sessions:>20.1f} {r_drained:>19.0%}"
    )
    print("-" * 98)
    print()
    print("That last row is the same precise publisher, read by a provider that")
    print("resolves a city to its country before comparing: one hierarchy, no")
    print(
        f"embeddings, no ontology. Recall goes from {rows[0][1]:.0%} to {r_recall:.0%} "
        f"without the"
    )
    print("publisher changing anything it publishes.")
    print()
    print("This relocates the problem. The low recall of a precise projection is")
    print("a fact about a provider that compares strings, and not about")
    print("projections. Coarsening is the publisher's way of compensating for")
    print("a provider that cannot resolve vocabulary, and it compensates by")
    print("disclosing less precisely to an index, which is the one thing the")
    print("publisher should not have to trade for retrieval. Where a provider")
    print("resolves, recall stops arguing for coarsening at all, and the only")
    print("pressure left is the one that argues against it: sessions.")
    print()
    print("A publishing Agent cannot compute its own")
    print("optimum, because the quantity that decides it (how many other")
    print("publishers this projection will be confused with, and how many querents")
    print("will therefore arrive) is visible only to the Discovery Provider.")
    print("Section 12 gives a provider no way to tell it, and a provider that")
    print("returned the size of the matching set would be helping an adversary")
    print("calibrate at the same time. That is a real open engineering question")
    print("and it is recorded as one instead of being patched.")


if __name__ == "__main__":
    main()
