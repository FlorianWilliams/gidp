"""Local evaluation of claims, and the truthfulness rule (Sections 15.1-15.5).

The whole point of the protocol lives in this module: a claim is evaluated
against values that never leave the Agent, and only a result from the closed
vocabulary of Section 15.1 crosses the wire.

Section 15.5 states the rule that makes the result meaningful and, as the
companion note argues, is also the reason the oracle leaks:

    A responder MUST NOT answer `compatible` where its values make the claim
    false, and MUST NOT answer `incompatible` where its values make the claim
    true. A responder MAY replace either truthful answer with
    `conditionally_compatible`, `unknown` or `declined` in order to limit
    inference. These are the only permitted deviations.

``coarsen`` below implements exactly that and nothing more: it can never turn
a false claim into `compatible`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .objects import Claim, StandingInterest
from .vocab import ClaimOperator, ClaimResult, Surface


class Truthfulness(Exception):
    """Raised when code attempts an answer Section 15.5 forbids."""


@dataclass(frozen=True)
class LocalEvaluation:
    """What the Agent knows privately, before deciding what to say."""

    #: The truthful answer, or None when the Agent cannot determine one.
    truth: bool | None
    #: Attribute the Agent consulted, for the audit trail (Section 25.3).
    attribute: str | None
    #: True when the attribute consulted is evaluation-only, i.e. the value
    #: that produced this answer may never be transmitted (Section 15.4).
    evaluation_only: bool


#: The dependency primitives of Section 19.1. They are reserved claim keys:
#: they live on the Conditional Interest as lists rather than among its
#: conditions, so a claim naming one is resolved from there. Only ``excludes``
#: must be supported by every implementation; the other three require the
#: ``dependency_primitives`` feature (Section 14.1).
DEPENDENCY_KEYS = ("provides", "requires", "conditional_on", "excludes")


def evaluate_claim(
    standing_interest: StandingInterest, claim: Claim
) -> LocalEvaluation:
    """Evaluate one claim against private values.

    Returns the *truth*, not the answer. Choosing what to say is
    ``choose_result`` below, and keeping the two apart is what makes the
    truthfulness rule checkable.
    """
    if claim.key in DEPENDENCY_KEYS:
        return _evaluate_dependency(standing_interest, claim)

    value = standing_interest.value_of(claim.key)
    cls = standing_interest.class_of(claim.key)
    evaluation_only = cls.surface is Surface.LOCAL

    if value is None:
        return LocalEvaluation(None, claim.key, evaluation_only)

    truth = _apply(claim.operator, value, claim.value)
    return LocalEvaluation(truth, claim.key, evaluation_only)


def _evaluate_dependency(
    standing_interest: StandingInterest, claim: Claim
) -> LocalEvaluation:
    """Resolve a claim naming a dependency primitive (Section 19.1).

    The asymmetry is the interesting part and it is deliberate. What an Agent
    *provides* is ordinarily disclosable — it is what makes a partnership
    findable. What it *requires* is the mirror image of what it lacks, and a
    capability gap admitted to a prospective partner is admitted to a
    prospective competitor, so a Principal will usually classify `requires`
    as evaluation-only and let the answer be coarsened.
    """
    held = list(getattr(standing_interest.interest, claim.key, []))
    cls = standing_interest.class_of(claim.key)
    evaluation_only = cls.surface is Surface.LOCAL

    if not held:
        # Nothing held: the Agent cannot determine the answer, and Section
        # 14.4's reasoning applies -- silence must not reveal absence.
        return LocalEvaluation(None, claim.key, evaluation_only)

    truth = _apply(claim.operator, held, claim.value)
    return LocalEvaluation(truth, claim.key, evaluation_only)


def _apply(operator: ClaimOperator, private: Any, asked: Any) -> bool | None:
    if operator is ClaimOperator.EQUALS:
        return private == asked

    if operator is ClaimOperator.INTERSECTS:
        left = private if isinstance(private, (list, set, tuple)) else [private]
        right = asked if isinstance(asked, (list, set, tuple)) else [asked]
        return bool(set(left) & set(right))

    if operator is ClaimOperator.WITHIN:
        # The canonical example of Section 15.4: a private threshold answered
        # against an asked range, without the threshold being transmitted.
        return _within(private, asked)

    if operator is ClaimOperator.COMPATIBLE_WITH:
        # Profile-defined predicate. The core profile has none, so the honest
        # answer is that the Agent cannot determine it.
        return None

    raise ValueError(f"unknown operator {operator!r}")


def _within(private: Any, asked: Any) -> bool | None:
    """Is a private value or range compatible with the asked range?

    ``asked`` is ``{"min": x, "max": y}`` or a named bucket the profile
    resolves. A private *bound* (``{"max": 80_000_000}``) is compatible with
    an asked range when the ranges overlap at all -- which is why a single
    probe cannot locate the bound, and a sequence of them can.
    """
    if not isinstance(asked, dict):
        return None

    a_min = asked.get("min")
    a_max = asked.get("max")

    if isinstance(private, dict):
        p_min = private.get("min")
        p_max = private.get("max")
    else:
        p_min = p_max = private

    if a_min is not None and p_max is not None and p_max < a_min:
        return False
    if a_max is not None and p_min is not None and p_min > a_max:
        return False
    return True


def choose_result(
    evaluation: LocalEvaluation,
    *,
    coarsen: bool = False,
    decline: bool = False,
    resolvable_by_disclosure: bool = False,
) -> ClaimResult:
    """Choose what to answer, within the bounds of Section 15.5.

    ``coarsen`` and ``decline`` are the inference-limiting levers an
    implementation may pull. Neither can produce an answer that asserts what
    the Agent's values contradict, because the truthful branches are the only
    ones that can return ``compatible`` or ``incompatible``.
    """
    if decline:
        return ClaimResult.DECLINED

    if evaluation.truth is None:
        if resolvable_by_disclosure:
            return ClaimResult.REQUIRES_DISCLOSURE
        return ClaimResult.UNKNOWN

    if coarsen:
        # Permitted: replaces *either* truthful answer, asserts neither.
        return ClaimResult.CONDITIONALLY_COMPATIBLE

    return ClaimResult.COMPATIBLE if evaluation.truth else ClaimResult.INCOMPATIBLE


def assert_truthful(evaluation: LocalEvaluation, answered: ClaimResult) -> None:
    """Check an answer against Section 15.5. Used by the conformance suite.

    This is the check a reviewer would write first, so the implementation
    ships it rather than waiting to be asked.
    """
    if answered is ClaimResult.COMPATIBLE and evaluation.truth is False:
        raise Truthfulness(
            "answered 'compatible' where private values make the claim false (15.5)"
        )
    if answered is ClaimResult.INCOMPATIBLE and evaluation.truth is True:
        raise Truthfulness(
            "answered 'incompatible' where private values make the claim true (15.5)"
        )
