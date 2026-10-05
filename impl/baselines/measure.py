"""A single yardstick, so that five mechanisms can be compared at all.

Every claim of the form "you could not do this with what already exists"
needs two things a prose table cannot give: a definition of what leaks, and
the same definition applied to every mechanism including ours.

The model. Each private fact is a point drawn from a finite prior: a
grid of candidate valuations, a set of possible management conditions, a
yes/no on whether the interest exists at all. An observer's knowledge after
seeing a mechanism run is the subset of that prior still consistent with
everything the observer saw. Leakage is the reduction, in bits:

    bits = log2(|prior|) - log2(|posterior|)

Zero means the observer learned nothing; log2(|prior|) means it learned the
value exactly. The measure is exact, not estimated, because the
posterior is computed by enumerating the prior and keeping the candidates
that would have produced the observed behaviour.

Why this and not differential privacy. An (ε,δ) bound describes a
mechanism; this describes a run. We want to compare mechanisms whose
internals have nothing in common (a broker that is told everything, an
ideal secure computation, a hashed set intersection, our own session), and
the only thing they share is what an observer ends up knowing.

Who observes. Three audiences, and the distinction matters more than the
bit counts: what a counterparty learns is spent by choice, what an
operator learns accumulates over every pair it serves, and what the public
learns is permanent and unbounded in audience.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from math import log2
from typing import Any

COUNTERPARTY = "counterparty"
OPERATOR = "operator"
PUBLIC = "public"
AUDIENCES = (COUNTERPARTY, OPERATOR, PUBLIC)


@dataclass(frozen=True)
class Fact:
    """One private fact, its true value, and the prior over it."""

    owner: str
    name: str
    true_value: Any
    prior: tuple[Any, ...]

    def __post_init__(self) -> None:
        if self.true_value not in self.prior:
            raise ValueError(f"{self.name}: true value is not in its own prior")

    @property
    def key(self) -> tuple[str, str]:
        return (self.owner, self.name)

    @property
    def total_bits(self) -> float:
        return log2(len(self.prior))


@dataclass
class Ledger:
    """What each audience knows about each fact, as the run proceeds."""

    facts: dict[tuple[str, str], Fact]
    posterior: dict[str, dict[tuple[str, str], set]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @classmethod
    def over(cls, facts: Iterable[Fact]) -> Ledger:
        indexed = {f.key: f for f in facts}
        return cls(
            facts=indexed,
            posterior={
                audience: {key: set(f.prior) for key, f in indexed.items()}
                for audience in AUDIENCES
            },
        )

    # -- the two ways knowledge changes ------------------------------------

    def observe(
        self,
        audience: str,
        key: tuple[str, str],
        consistent: Callable[[Any], bool],
        note: str = "",
    ) -> None:
        """The audience saw something. Keep only candidates that explain it."""
        surviving = {v for v in self.posterior[audience][key] if consistent(v)}
        # The invariant that keeps the harness correct: whatever an observer
        # deduces, the truth must remain among the candidates. A predicate
        # that eliminates it is a bug in the model of the mechanism, and
        # silently narrowing past the truth would flatter every result.
        if self.facts[key].true_value not in surviving:
            raise AssertionError(
                f"{key}: the observation rules out the true value; the "
                "harness is wrong, not the mechanism"
            )
        self.posterior[audience][key] = surviving
        if note:
            self.notes.append(f"{audience} <- {key[0]}.{key[1]}: {note}")

    def reveal(self, audience: str, key: tuple[str, str], note: str = "") -> None:
        """The audience was told."""
        self.posterior[audience][key] = {self.facts[key].true_value}
        if note:
            self.notes.append(f"{audience} <- {key[0]}.{key[1]}: {note}")

    # -- reading it back ---------------------------------------------------

    def bits(self, audience: str, key: tuple[str, str]) -> float:
        fact = self.facts[key]
        return fact.total_bits - log2(len(self.posterior[audience][key]))

    def total(self, audience: str) -> float:
        return sum(self.bits(audience, key) for key in self.facts)

    def by_fact(self, audience: str) -> dict[str, float]:
        return {
            f"{key[0]}.{key[1]}": round(self.bits(audience, key), 2)
            for key in self.facts
        }

    def exact(self, audience: str) -> list[str]:
        """Facts this audience now knows exactly."""
        return [
            f"{key[0]}.{key[1]}"
            for key in self.facts
            if len(self.posterior[audience][key]) == 1
        ]
