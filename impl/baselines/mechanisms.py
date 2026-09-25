"""Five ways to answer the same question, instrumented identically.

Four of them exist already and are what a reviewer will propose instead of
this protocol. The fifth is this protocol. Each is given the same scenario,
the same facts, and the same yardstick, and each reports three things: what
it concluded, what it leaked and to whom, and what it structurally cannot
express.

The last column is the one that decides the argument. A mechanism that leaks
nothing about a question it cannot ask has not protected anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from baselines.measure import COUNTERPARTY, OPERATOR, PUBLIC, Ledger
from baselines.scenario import (
    A_ACCEPTS_MANAGEMENT,
    A_BUDGET,
    A_BUDGET_CEILING,
    A_CATEGORICAL,
    A_EXISTS,
    B_CATEGORICAL,
    B_EXISTS,
    B_FLOOR,
    B_MGMT,
    FACTS,
    MANAGEMENT_OPTIONS,
    b_interest,
    truly_compatible,
)
from gidp.evaluation import choose_result, evaluate_claim
from gidp.objects import Claim
from gidp.vocab import ClaimOperator, ClaimResult

#: The ground truth every mechanism is trying to reach.
TRUTH = truly_compatible()


@dataclass
class Outcome:
    name: str
    verdict: str
    correct: bool | None
    queries: int
    ledger: Ledger
    presupposes_rendezvous: bool
    third_party: str | None
    cannot: list[str] = field(default_factory=list)
    remark: str = ""


def _ledger() -> Ledger:
    return Ledger.over(FACTS)


def _answer(interest, claim: Claim, over_budget: bool = False) -> ClaimResult:
    """The default answering policy of `gidp/agent.py`, reused verbatim."""
    evaluation = evaluate_claim(interest, claim)
    if over_budget:
        return choose_result(evaluation, decline=True)
    coarsen = evaluation.evaluation_only and evaluation.truth is True
    return choose_result(evaluation, coarsen=coarsen)


# ---------------------------------------------------------------------------
# 1. The status quo: a trusted intermediary
# ---------------------------------------------------------------------------


def trusted_broker() -> Outcome:
    """A banker, a headhunter, a corporate development team.

    Both sides tell one party everything and that party decides. This is what
    the market does today, it works, and any protocol that cannot beat it on
    something is pointless.
    """
    ledger = _ledger()
    for key in (B_EXISTS, B_FLOOR, B_MGMT, A_EXISTS, A_BUDGET):
        ledger.reveal(OPERATOR, key, "disclosed in full to the intermediary")

    # The introduction itself is informative: being introduced means the
    # other side cleared your conditions.
    if TRUTH:
        ledger.reveal(COUNTERPARTY, B_EXISTS, "revealed by the introduction")
        ledger.reveal(COUNTERPARTY, A_EXISTS, "revealed by the introduction")
        ledger.observe(
            COUNTERPARTY,
            B_FLOOR,
            lambda v: v <= A_BUDGET_CEILING,
            "the introduction implies the floor is within budget",
        )
        ledger.observe(
            COUNTERPARTY,
            B_MGMT,
            lambda m: m in A_ACCEPTS_MANAGEMENT,
            "the introduction implies an acceptable condition",
        )
        ledger.observe(
            COUNTERPARTY,
            A_BUDGET,
            lambda b: b >= 45_000_000,
            "the introduction implies the budget clears the floor",
        )

    return Outcome(
        name="Trusted intermediary",
        verdict="introduce" if TRUTH else "no match",
        correct=True,
        queries=1,
        ledger=ledger,
        presupposes_rendezvous=False,
        third_party="the intermediary, exactly and permanently, for every pair it serves",
        cannot=[],
        remark=(
            "Expresses everything and decides correctly. Its whole cost is in "
            "one place: someone else ends up knowing both sides' secrets, and "
            "keeps knowing them."
        ),
    )


# ---------------------------------------------------------------------------
# 2. Publishing: the listing, the teaser, the job board
# ---------------------------------------------------------------------------


def public_posting() -> Outcome:
    """B states its conditions publicly and waits.

    Cheap, no intermediary, and it destroys the premise: a company that is
    not for sale cannot announce the conditions under which it would be.
    """
    ledger = _ledger()
    ledger.reveal(PUBLIC, B_EXISTS, "a listing exists, therefore the interest exists")
    ledger.observe(
        PUBLIC,
        B_FLOOR,
        lambda v: 40_000_000 <= v <= 85_000_000,
        "the published asking band",
    )
    ledger.reveal(PUBLIC, B_MGMT, "listings state the management condition")
    # A approaches B, so B learns A exists; A published nothing.
    ledger.reveal(COUNTERPARTY, A_EXISTS, "the approach reveals the buyer's interest")
    ledger.reveal(COUNTERPARTY, B_EXISTS, "the listing is public")
    ledger.observe(COUNTERPARTY, B_FLOOR, lambda v: 40_000_000 <= v <= 85_000_000, "")
    ledger.reveal(COUNTERPARTY, B_MGMT, "")

    return Outcome(
        name="Public listing",
        verdict="introduce" if TRUTH else "no match",
        correct=True,
        queries=1,
        ledger=ledger,
        presupposes_rendezvous=False,
        third_party=None,
        cannot=[
            "keeping the existence of the interest private",
            "withdrawing what has been published",
            "bounding the audience",
        ],
        remark=(
            "No third party holds the secrets because there are no secrets "
            "left. Everything leaked here is permanent and its audience is "
            "unbounded, which no bit count conveys."
        ),
    )


# ---------------------------------------------------------------------------
# 3. The strongest cryptographic baseline: one-shot secure comparison
# ---------------------------------------------------------------------------


def sealed_one_shot() -> Outcome:
    """An ideal secure two-party computation of an agreed predicate.

    Modelled at its theoretical best: both sides learn the output bit and
    nothing else. On leakage this is the mechanism to beat, and on the
    scenario's tracked facts it wins. What it cannot do is everything before
    and around the bit.
    """
    ledger = _ledger()
    # Agreeing a predicate and connecting to compute it reveals that each
    # side has an interest. There is no anonymous way to co-compute.
    ledger.reveal(
        COUNTERPARTY, B_EXISTS, "you cannot co-compute with someone anonymously"
    )
    ledger.reveal(COUNTERPARTY, A_EXISTS, "likewise")

    # Both observe one bit. The marginal posterior of each fact is its
    # projection of the joint set of assignments consistent with that bit.
    def consistent_floor(v: int) -> bool:
        return any(
            truly_compatible(v, m, A_BUDGET_CEILING) is TRUTH
            for m in MANAGEMENT_OPTIONS
        )

    def consistent_mgmt(m: str) -> bool:
        return truly_compatible(45_000_000, m, A_BUDGET_CEILING) is TRUTH

    def consistent_budget(b: int) -> bool:
        return truly_compatible(45_000_000, "founder_operational", b) is TRUTH

    ledger.observe(COUNTERPARTY, B_FLOOR, consistent_floor, "implied by the output bit")
    ledger.observe(COUNTERPARTY, B_MGMT, consistent_mgmt, "implied by the output bit")
    ledger.observe(
        COUNTERPARTY, A_BUDGET, consistent_budget, "implied by the output bit"
    )

    return Outcome(
        name="Ideal sealed comparison",
        verdict="introduce" if TRUTH else "no match",
        correct=True,
        queries=1,
        ledger=ledger,
        presupposes_rendezvous=True,
        third_party=None,
        cannot=[
            "finding the counterparty in the first place",
            "agreeing the predicate without stating the dimensions",
            "reporting which dimensions are open rather than a single bit",
            "answering conditionally, so that a near miss can be repaired",
        ],
        remark=(
            "The honest winner on leakage, and it answers a question the "
            "parties must already have found each other to ask. It settles a "
            "comparison; it does not perform discovery."
        ),
    )


# ---------------------------------------------------------------------------
# 4. Private set intersection over the categorical dimensions
# ---------------------------------------------------------------------------


def private_set_intersection() -> Outcome:
    """Real intersection of the categorical attributes, honestly scored.

    The information profile of an ideal PSI: both sides learn the exact
    intersection of the sets they submitted, and nothing about the rest.
    """
    ledger = _ledger()
    ledger.reveal(COUNTERPARTY, B_EXISTS, "participation reveals the interest")
    ledger.reveal(COUNTERPARTY, A_EXISTS, "participation reveals the interest")

    intersection = {
        key: sorted(set(A_CATEGORICAL.get(key, [])) & set(B_CATEGORICAL.get(key, [])))
        for key in ("domain", "geography", "transaction_structures")
    }
    # The binding conditions are a threshold and a categorical *condition*,
    # not set membership. Neither can enter the computation.
    return Outcome(
        name="Private set intersection",
        verdict="cannot decide",
        correct=None,
        queries=1,
        ledger=ledger,
        presupposes_rendezvous=True,
        third_party=None,
        cannot=[
            "thresholds and ranges, which are the binding conditions here",
            "conditional answers",
            "deciding the case at all",
        ],
        remark=(
            f"Computes {intersection} and stops. It leaks least of all on the "
            "tracked facts, for the reason that it cannot address any of them: "
            "leaking nothing about a question you cannot ask is not privacy."
        ),
    )


# ---------------------------------------------------------------------------
# 5. GIDP, run honestly, and run adversarially
# ---------------------------------------------------------------------------

HONEST_CLAIMS = [
    Claim(
        key="domain", operator=ClaimOperator.INTERSECTS, value=["enterprise_software"]
    ),
    Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["germany"]),
    Claim(
        key="transaction_structures",
        operator=ClaimOperator.INTERSECTS,
        value=["acquisition", "majority_investment", "distribution", "joint_venture"],
    ),
    Claim(key="market_access", operator=ClaimOperator.EQUALS, value="france"),
    Claim(
        key="valuation_floor",
        operator=ClaimOperator.WITHIN,
        value={"min": 0, "max": A_BUDGET_CEILING},
    ),
    # A can live with either of two conditions, so it asks for both rather
    # than guessing one -- an honest querent states its whole acceptance set.
    Claim(
        key="management_condition",
        operator=ClaimOperator.INTERSECTS,
        value=["founder_operational", "founder_advisory"],
    ),
]


def _replay(ledger: Ledger, claims: list[Claim], note: str) -> None:
    """Filter each candidate by what it would have answered."""
    true_interest = b_interest()
    for claim in claims:
        observed = _answer(true_interest, claim)
        if claim.key == "valuation_floor":
            ledger.observe(
                COUNTERPARTY,
                B_FLOOR,
                lambda v, c=claim, o=observed: (
                    _answer(b_interest(valuation_floor=v), c) is o
                ),
                note,
            )
        elif claim.key == "management_condition":
            ledger.observe(
                COUNTERPARTY,
                B_MGMT,
                lambda m, c=claim, o=observed: (
                    _answer(b_interest(management_condition=m), c) is o
                ),
                note,
            )


def cid_honest() -> Outcome:
    """A counterparty that asks what it needs and stops."""
    ledger = _ledger()
    # Identity is consented only after qualification, so the counterparty
    # learns who it is talking to. The provider that held the projection
    # learned that *an* interest exists behind an opaque endpoint, which is
    # not the same fact and is therefore not scored here -- see the remark.
    ledger.reveal(COUNTERPARTY, B_EXISTS, "identity consented after qualification")
    ledger.reveal(COUNTERPARTY, A_EXISTS, "likewise")
    _replay(ledger, HONEST_CLAIMS, "answered in session")

    return Outcome(
        name="GIDP, honest counterparty",
        verdict="introduce" if TRUTH else "no match",
        correct=True,
        queries=len(HONEST_CLAIMS),
        ledger=ledger,
        presupposes_rendezvous=False,
        third_party=None,
        cannot=[
            "bounding what an adaptive counterparty extracts (Section 24.3)",
        ],
        remark=(
            "The provider held an unattributed projection, so it learned that "
            "an interest exists without learning whose. That is a weaker fact "
            "than the one scored here and it is not nothing: Section 24.2 is "
            "where it is discussed."
        ),
    )


def cid_adversarial(budget: int = 40) -> Outcome:
    """The same protocol against a counterparty that probes.

    This is the number that matters. A comparison that reported only the
    honest run would be measuring our own good intentions.
    """
    ledger = _ledger()
    ledger.reveal(COUNTERPARTY, B_EXISTS, "identity consented after qualification")
    ledger.reveal(COUNTERPARTY, A_EXISTS, "likewise")

    claims = list(HONEST_CLAIMS)
    lo, hi = 0, 200_000_000
    while hi - lo > 5_000_000 and len(claims) < budget:
        mid = ((lo + hi) // 2 // 5_000_000) * 5_000_000
        claims.append(
            Claim(
                key="valuation_floor",
                operator=ClaimOperator.WITHIN,
                value={"min": mid, "max": mid + 5_000_000},
            )
        )
        if _answer(b_interest(), claims[-1]) is ClaimResult.INCOMPATIBLE:
            lo = mid + 5_000_000
        else:
            hi = mid
    for option in MANAGEMENT_OPTIONS:
        if len(claims) >= budget:
            break
        claims.append(
            Claim(
                key="management_condition", operator=ClaimOperator.EQUALS, value=option
            )
        )

    _replay(ledger, claims, "answered in session")
    return Outcome(
        name="GIDP, probing counterparty",
        verdict="introduce" if TRUTH else "no match",
        correct=True,
        queries=len(claims),
        ledger=ledger,
        presupposes_rendezvous=False,
        third_party=None,
        cannot=["bounding what an adaptive counterparty extracts (Section 24.3)"],
        remark=(
            "Same protocol, same policy, a counterparty that spends queries "
            "instead of asking once. The gap between this row and the honest "
            "one is the open problem, measured."
        ),
    )


MECHANISMS = (
    trusted_broker,
    public_posting,
    sealed_one_shot,
    private_set_intersection,
    cid_honest,
    cid_adversarial,
)
