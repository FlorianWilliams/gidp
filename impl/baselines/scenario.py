"""One scenario, five mechanisms.

The scenario is Appendix C.1 reduced to what the comparison needs: a French
company privately authorised to explore a German acquisition, and a German
company that is *not for sale* but would consider a transaction if three
conditions hold — one of which is a valuation floor it will not state, and
one a management condition it will not state either.

The reduction matters and is stated here rather than buried. Each private
fact is a point drawn from a finite prior, because a mechanism-independent
leakage measure needs a countable hypothesis space (see `measure.py`). The
valuation floor is modelled as a bound `{"min": v}` — "not below v" — which
is how Section 15.4's illustration behaves and how the L-2 limit case probes
it. Nothing else about the scenario is simplified.

The fact that matters most is the first one, and it is the one most
comparisons forget: **whether B has any such interest at all.** For a company
that is not for sale, that single bit is the whole secret. A mechanism that
requires B to announce it has already lost, whatever it does afterwards.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from baselines.measure import Fact
from gidp.objects import (
    AuthoritySpec,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
    Validity,
)
from gidp.vocab import Authority, AuthorityValue, Gate, Surface

# --------------------------------------------------------------------------
# Priors
# --------------------------------------------------------------------------

#: Plausible valuations for a company of this size, in 5M steps. An observer
#: who starts here knows nothing beyond "somewhere in this band".
VALUATION_GRID: tuple[int, ...] = tuple(range(0, 205_000_000, 5_000_000))

#: The management conditions a seller of this kind plausibly attaches.
MANAGEMENT_OPTIONS: tuple[str, ...] = (
    "founder_operational",
    "founder_exits",
    "founder_advisory",
    "management_retained",
    "management_replaced",
    "no_condition",
)

B_VALUATION_FLOOR = 45_000_000
B_MANAGEMENT = "founder_operational"
A_BUDGET_CEILING = 120_000_000

FACTS: tuple[Fact, ...] = (
    Fact("B", "exists", True, (True, False)),
    Fact("B", "valuation_floor", B_VALUATION_FLOOR, VALUATION_GRID),
    Fact("B", "management_condition", B_MANAGEMENT, MANAGEMENT_OPTIONS),
    Fact("A", "exists", True, (True, False)),
    Fact("A", "budget_ceiling", A_BUDGET_CEILING, VALUATION_GRID),
)

B_EXISTS = ("B", "exists")
B_FLOOR = ("B", "valuation_floor")
B_MGMT = ("B", "management_condition")
A_EXISTS = ("A", "exists")
A_BUDGET = ("A", "budget_ceiling")

#: The categorical dimensions both sides are willing to have matched. These
#: are the only ones a set-based mechanism can touch at all.
A_CATEGORICAL: dict[str, list[str]] = {
    "domain": ["enterprise_software"],
    "geography": ["europe", "germany"],
    "transaction_structures": [
        "acquisition",
        "majority_investment",
        "distribution",
        "joint_venture",
    ],
    "market_access_offered": ["france"],
}

B_CATEGORICAL: dict[str, list[str]] = {
    "domain": ["enterprise_software"],
    "geography": ["europe", "germany"],
    "transaction_structures": ["majority_investment", "distribution"],
    "market_access_required": ["france"],
}


def _in(days: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


def b_interest(
    valuation_floor: int = B_VALUATION_FLOOR,
    management_condition: str = B_MANAGEMENT,
) -> StandingInterest:
    """B's Standing Interest, parameterised by its two private values.

    Parameterising it is what makes the leakage measurement exact rather
    than modelled: to know what a candidate value would have leaked, the
    harness rebuilds the interest with that value and asks the real
    implementation what it would have answered.
    """
    return StandingInterest(
        id="local:si-b",
        principal_ref="local:principal-b",
        interest=ConditionalInterest(
            action="consider_strategic_transaction",
            object="own_company",
            conditions={
                "domain": B_CATEGORICAL["domain"],
                "geography": B_CATEGORICAL["geography"],
                "transaction_structures": B_CATEGORICAL["transaction_structures"],
                "market_access": "france",
                "valuation_floor": {"min": valuation_floor},
                "management_condition": management_condition,
                "principal_name": "Principal B",
            },
            requires=["market_access_france"],
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                "domain": DisclosureClass(surface=Surface.DISCOVERY),
                "geography": DisclosureClass(surface=Surface.DISCOVERY),
                "transaction_structures": DisclosureClass(surface=Surface.SESSION),
                "market_access": DisclosureClass(surface=Surface.SESSION),
                "valuation_floor": DisclosureClass(surface=Surface.LOCAL),
                "management_condition": DisclosureClass(surface=Surface.LOCAL),
                "principal_name": DisclosureClass(
                    surface=Surface.SESSION, gate=Gate.PRINCIPAL_APPROVAL
                ),
            }
        ),
        authority=AuthoritySpec(
            levels={
                Authority.OBSERVE: AuthorityValue.TRUE,
                Authority.SEARCH: AuthorityValue.TRUE,
                Authority.PUBLISH_PROJECTION: AuthorityValue.TRUE,
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
                Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
            },
            evidence_ref="urn:example:delegation:b-2026-09",
        ),
        validity=Validity(expires_at=_in(90)),
    )


def truly_compatible(
    valuation_floor: int = B_VALUATION_FLOOR,
    management_condition: str = B_MANAGEMENT,
    budget_ceiling: int = A_BUDGET_CEILING,
) -> bool:
    """The ground truth the mechanisms are trying to discover.

    A and B are worth introducing when the categorical dimensions intersect,
    A can reach B's floor, and A can live with B's management condition.
    """
    structures = set(A_CATEGORICAL["transaction_structures"]) & set(
        B_CATEGORICAL["transaction_structures"]
    )
    market = set(A_CATEGORICAL["market_access_offered"]) & set(
        B_CATEGORICAL["market_access_required"]
    )
    domains = set(A_CATEGORICAL["domain"]) & set(B_CATEGORICAL["domain"])
    return bool(
        structures
        and market
        and domains
        and budget_ceiling >= valuation_floor
        and management_condition in ("founder_operational", "founder_advisory")
    )


#: What A is prepared to accept on the management dimension. Used by the
#: mechanisms that can express it at all.
A_ACCEPTS_MANAGEMENT: tuple[str, ...] = ("founder_operational", "founder_advisory")
