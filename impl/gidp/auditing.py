"""Deciding what not to answer (Section 24.3).

Section 15.5 says what a responder may say. This says what it should decline
to be asked, which the specification recommends and leaves to the
implementation. Both controls here are *simulatable* in the sense of
[KMN2005]: the decision to refuse depends only on the claims asked and the
answers already given, never on the value being protected, so an observer can
reproduce it and learns nothing from being refused. A control that consulted
the value would be the leak it was built to prevent.

The two have opposite shapes and neither dominates the other, which is why
both are here.

`GranularityLattice` constrains where a claim's bounds may fall: a band
must be a union of whole cells of the lattice. It holds no
state, so honest traffic never depletes it and an adversary cannot drain it,
and it needs nothing declared about the attribute beyond a width. Because a
private bound is tested at the *edge* of the band asked, this caps the
resolution at one cell for any number of claims. What that resolution is
worth depends on how many possible values a cell holds: about
`log2(number of cells)` bits when they are spread evenly, all of it when a
cell holds one (P-09). The cells cover integers in the attribute's unit,
and a constrained attribute holding anything else raises (P-07). Its cost
is precision: a counterparty rounds its question and is answered.

`BitBudget` caps how much the responder will concede in total. It is tighter
and it is shared: honest counterparties spend it too, and once spent the
responder goes quiet. It also needs the deployment to declare what values an
attribute may take, because "how much was conceded" has no meaning without
knowing what was possible.

Measured against each other in `baselines/frontier.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log2
from typing import Any, Protocol

from .evaluation import DEPENDENCY_KEYS
from .objects import Claim, StandingInterest
from .vocab import ClaimOperator, ClaimResult


class DisclosureAudit(Protocol):
    """What an Agent consults before answering a claim."""

    def admits(self, claim: Claim, interest: StandingInterest) -> bool:
        """May this claim be answered at all?"""

    def record(
        self, claim: Claim, interest: StandingInterest, result: ClaimResult
    ) -> None:
        """Note what was answered, for whatever the control keeps."""


class LatticeDomainError(ValueError):
    """A lattice-constrained attribute holds something other than integers.

    The cells `[k*w, (k+1)*w - 1]` cover the integers and nothing between
    them: a private 39.5 answers `incompatible` to both [20, 39] and
    [40, 59], which places it to within one unit (P-07). The lattice is
    therefore defined over integers in the attribute's unit (cents, euros,
    people), and holding anything else under it is a configuration error.
    It is raised, never answered: a `declined` that depended on the value
    would be the leak the control exists to prevent, so the deployment fails
    loudly instead, on every claim, whatever is asked.
    """


def _require_integers(key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        parts: list[Any] = [v for v in value.values() if v is not None]
    elif isinstance(value, list | tuple | set):
        parts = list(value)
    else:
        parts = [value]
    for part in parts:
        if isinstance(part, bool) or not isinstance(part, int):
            raise LatticeDomainError(
                f"{key!r} is under a granularity lattice and must hold integers "
                f"in its unit; it holds {type(part).__name__}"
            )


@dataclass
class GranularityLattice:
    """Claim bounds must fall on a lattice, per attribute.

    A width of zero, or an attribute absent from the mapping, means no
    constraint. Nothing is kept between claims.
    """

    widths: dict[str, int] = field(default_factory=dict)

    def admits(self, claim: Claim, interest: StandingInterest) -> bool:
        width = self.widths.get(claim.key, 0)
        if not width:
            return True
        _require_integers(claim.key, interest.value_of(claim.key))
        # The lattice cuts the attribute into cells [k*width, (k+1)*width - 1].
        # An answer may distinguish cells and nothing finer, so the only
        # admissible question is an `overlaps` band made of whole cells.
        # Everything else names something narrower than a cell: `equals`
        # tests a value exactly (P-03, P-05), a scalar or a list names
        # points, and two inclusive bands that share an edge, such as
        # [20, 40] and [40, 60], isolate the edge between them (P-05).
        if claim.operator is not ClaimOperator.OVERLAPS:
            return False
        value = claim.value
        if not isinstance(value, dict) or not set(value) <= {"min", "max"}:
            return False
        low, high = value.get("min"), value.get("max")
        if low is None and high is None:
            return False
        if low is not None and not (isinstance(low, int) and low % width == 0):
            return False
        if high is not None and not (
            isinstance(high, int) and (high + 1) % width == 0
        ):
            return False
        return low is None or high is None or low <= high

    def record(
        self, claim: Claim, interest: StandingInterest, result: ClaimResult
    ) -> None:
        return None


@dataclass
class BitBudget:
    """Cap the information conceded about an attribute.

    ``priors`` gives, per attribute, the values it might hold, in the
    shape the attribute holds them. A threshold stored as
    ``{"min": 45_000_000}`` needs a prior of such mappings, not of bare
    integers: a prior in the wrong shape makes every candidate answer alike,
    which the worst-case rule reads as a maximally informative claim and
    refuses. Everything still looks safe and nothing is ever answered; the
    failure is silent, so it is worth knowing about.

    Candidates are tracked by their position in the prior, not by their
    value, so a value of any shape works, hashable or not.

    The responder keeps the subset still consistent with what it has answered
    (an observer holds the same subset, so it is not a secret)
    and refuses a claim whose *worst case over the answers it might give*
    would cross the budget. Taking the worst case is what keeps the decision
    independent of the value.
    """

    priors: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    budget_bits: float = 2.0
    #: attribute -> indices into its prior that remain consistent.
    posterior: dict[str, set[int]] = field(default_factory=dict)

    def _alive(self, key: str) -> set[int]:
        if key not in self.posterior:
            self.posterior[key] = set(range(len(self.priors.get(key, ()))))
        return self.posterior[key]

    @staticmethod
    def _as_if(interest: StandingInterest, key: str, value: Any) -> StandingInterest:
        """The interest as it would be if `key` held `value`, written where
        the evaluator reads it. The dependency primitives live in their own
        lists, outside `conditions` (Section 19.1); a candidate written into
        `conditions` would never replace the real value, every candidate
        would answer alike, and the budget would count nothing (P-06)."""
        candidate = interest.model_copy(deep=True)
        if key in DEPENDENCY_KEYS:
            setattr(candidate.interest, key, list(value))
        else:
            candidate.interest.conditions[key] = value
        return candidate

    def _answer_for(
        self, interest: StandingInterest, key: str, index: int, claim: Claim
    ) -> ClaimResult:
        from .evaluation import choose_result, evaluate_claim

        value = self.priors[key][index]
        evaluation = evaluate_claim(self._as_if(interest, key, value), claim)
        coarsen = evaluation.evaluation_only and evaluation.truth is True
        return choose_result(evaluation, coarsen=coarsen)

    def disclosed(self, key: str) -> float:
        prior = self.priors.get(key, ())
        if not prior:
            return 0.0
        return log2(len(prior)) - log2(max(len(self._alive(key)), 1))

    def admits(self, claim: Claim, interest: StandingInterest) -> bool:
        prior = self.priors.get(claim.key)
        if not prior:
            return True
        alive = self._alive(claim.key)
        total = log2(len(prior))
        outcomes: dict[ClaimResult, set[int]] = {}
        for index in alive:
            outcomes.setdefault(
                self._answer_for(interest, claim.key, index, claim), set()
            ).add(index)
        for surviving in outcomes.values():
            if total - log2(len(surviving)) > self.budget_bits:
                return False
        return True

    def record(
        self, claim: Claim, interest: StandingInterest, result: ClaimResult
    ) -> None:
        if claim.key not in self.priors:
            return
        alive = self._alive(claim.key)
        narrowed = {
            index
            for index in alive
            if self._answer_for(interest, claim.key, index, claim) is result
        }
        if narrowed:
            self.posterior[claim.key] = narrowed
