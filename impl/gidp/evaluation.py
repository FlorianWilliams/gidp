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

from collections.abc import Hashable
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
    #: False when the attribute is `never`: it may not produce a transmitted
    #: result at all, so the only admissible answer is `declined` (S-23).
    permitted: bool = True


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
    if not cls.evaluable:
        return LocalEvaluation(None, claim.key, True, permitted=False)

    if value is None:
        return LocalEvaluation(None, claim.key, evaluation_only)

    taxonomy = standing_interest.interest.taxonomies.get(claim.key, {})
    truth = _apply(claim.operator, value, claim.value, taxonomy)
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
    if not cls.evaluable:
        return LocalEvaluation(None, claim.key, True, permitted=False)

    if not held:
        # Nothing held: the Agent cannot determine the answer, and Section
        # 14.4's reasoning applies -- silence must not reveal absence.
        return LocalEvaluation(None, claim.key, evaluation_only)

    truth = _apply(claim.operator, held, claim.value)
    return LocalEvaluation(truth, claim.key, evaluation_only)


def _upward(values: Any, taxonomy: dict[str, str]) -> set:
    """Everything a held value also is: munich is also germany, also europe."""
    out: set = set()
    for value in values:
        current = value
        seen = set()
        while current is not None and current not in seen:
            out.add(current)
            seen.add(current)
            current = taxonomy.get(current)
    return out


def _descends(value: Any, held: set, taxonomy: dict[str, str]) -> bool:
    """Is the asked value somewhere *below* something held?"""
    current = taxonomy.get(value)
    seen = set()
    while current is not None and current not in seen:
        if current in held:
            return True
        seen.add(current)
        current = taxonomy.get(current)
    return False


def _apply(
    operator: ClaimOperator,
    private: Any,
    asked: Any,
    taxonomy: dict[str, str] | None = None,
) -> bool | None:
    """Resolve one operator against one private value.

    Returns ``None`` — "cannot determine" — whenever the operator does not
    fit the shape of the value it is applied to: `within` against a label or
    a list, `intersects` against a range. Section 14.2 does not say what a
    responder does with a shape mismatch, and the first instinct is to treat
    it as a malformed request. That instinct is wrong twice over. A responder
    that raises has been made to behave differently by the *shape* of its own
    private value, which tells the querent something it should not learn; and
    a responder that can be crashed by a well-formed message with an
    ill-fitting operator can be crashed by anyone. `unknown` is the answer
    that discloses nothing and stays available (SPEC-ISSUES S-13).
    """
    if operator is ClaimOperator.EQUALS:
        return private == asked

    if operator is ClaimOperator.INTERSECTS:
        left = private if isinstance(private, (list, set, tuple)) else [private]
        right = asked if isinstance(asked, (list, set, tuple)) else [asked]
        if taxonomy:
            # Asymmetric on purpose, and the asymmetry is the whole point.
            # A responder holding `munich` truthfully answers `compatible` to
            # `germany`, because Munich *is* in Germany. A responder holding
            # `germany`, asked about `munich`, answers `unknown`: a German
            # company may or may not be in Munich and it has not said which.
            # Only the responder's own values are placed in the hierarchy, so
            # nothing is negotiated, nothing is shared and no third party is
            # consulted.
            if not all(isinstance(v, Hashable) for v in (*left, *right)):
                return None
            above = _upward(left, taxonomy)
            if set(right) & above:
                return True
            held = set(left)
            if any(_descends(value, held, taxonomy) for value in right):
                return None
            return False

        if not all(isinstance(v, Hashable) for v in (*left, *right)):
            # A range has no membership to intersect. The honest answer is
            # that this Agent cannot determine one (Section 15.1), not a
            # crash -- see the note on shape mismatches below.
            return None
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
    elif isinstance(private, (int, float)) and not isinstance(private, bool):
        p_min = p_max = private
    else:
        # A list or a label is not a point on the axis the claim names.
        return None

    if not all(
        isinstance(bound, (int, float)) and not isinstance(bound, bool)
        for bound in (a_min, a_max, p_min, p_max)
        if bound is not None
    ):
        return None

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

    Coarsening is asymmetric (S-25). ``conditionally_compatible`` is a
    *qualifying* result: a session can reach an Opportunity on it. Issued over
    a truth of ``incompatible`` it would let a session qualify on a dimension
    the responder knows to be ruled out, so a ruled-out claim coarsens to
    ``unknown`` instead, which prevents qualification and asserts nothing.
    """
    if decline or not evaluation.permitted:
        return ClaimResult.DECLINED

    if evaluation.truth is None:
        if resolvable_by_disclosure:
            return ClaimResult.REQUIRES_DISCLOSURE
        return ClaimResult.UNKNOWN

    if coarsen:
        return (
            ClaimResult.CONDITIONALLY_COMPATIBLE
            if evaluation.truth
            else ClaimResult.UNKNOWN
        )

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
    if answered is ClaimResult.CONDITIONALLY_COMPATIBLE and evaluation.truth is False:
        raise Truthfulness(
            "answered 'conditionally_compatible' where private values rule the "
            "claim out; it is a qualifying result and may only replace "
            "'compatible' (15.5, S-25)"
        )
