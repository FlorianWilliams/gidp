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

`GranularityLattice` constrains where a claim's bounds may fall. It holds no
state, so honest traffic never depletes it and an adversary cannot drain it,
and it needs nothing declared about the attribute beyond a width. Because a
private bound is tested at the *edge* of the band asked, this caps resolution
at `log2(range / width)` for any number of claims. Its cost is
precision: a counterparty rounds its question and is answered.

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

from .objects import Claim, StandingInterest
from .vocab import ClaimResult


class DisclosureAudit(Protocol):
    """What an Agent consults before answering a claim."""

    def admits(self, claim: Claim, interest: StandingInterest) -> bool:
        """May this claim be answered at all?"""

    def record(
        self, claim: Claim, interest: StandingInterest, result: ClaimResult
    ) -> None:
        """Note what was answered, for whatever the control keeps."""


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
        # Only a band can be held to the lattice. A scalar or a list names
        # points, and `equals 45` confirms 45 exactly whatever the width, so
        # on a constrained attribute every other shape is declined.
        if not isinstance(claim.value, dict):
            return False
        return all(
            isinstance(bound, int) and bound % width == 0
            for bound in (claim.value.get("min"), claim.value.get("max"))
            if bound is not None
        )

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
        candidate = interest.model_copy(deep=True)
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
