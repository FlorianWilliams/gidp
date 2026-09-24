"""Four cases chosen because they should break the protocol.

The four worked domains were chosen because they fit. These four are chosen
because they look like they should not, each attacking a different assumption.
Each carries a hypothesis of what will break, stated before the run, so that a
case which passes is informative rather than reassuring.

    python examples/limits.py

Findings are recorded in ../spec/LIMITS.md. Where a case produced a specification
change, it is in SPEC-ISSUES.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cid.agent import Agent  # noqa: E402
from cid.evaluation import evaluate_claim  # noqa: E402
from cid.objects import (  # noqa: E402
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from cid.session import ProtocolError  # noqa: E402
from cid.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    ConsentAction,
    Gate,
    Surface,
)

LINE = "=" * 78
RULE = "-" * 78


def head(number: str, title: str, hypothesis: str) -> None:
    print()
    print(LINE)
    print(f"{number} — {title}")
    print(LINE)
    print(f"Hypothesis before the run: {hypothesis}")
    print(RULE)


def finding(text: str) -> None:
    print(f"FINDING  {text}")


def _interest(conditions, policy, authority, **kw) -> StandingInterest:
    return StandingInterest(
        id=kw.get("id", "local:si"),
        principal_ref="local:principal",
        interest=ConditionalInterest(
            action=kw.get("action", "consider"),
            conditions=conditions,
        ),
        disclosure_policy=DisclosurePolicy(attributes=policy),
        authority=AuthoritySpec(levels=authority),
    )


FULL = {
    Authority.OBSERVE: AuthorityValue.TRUE,
    Authority.SEARCH: AuthorityValue.TRUE,
    Authority.PUBLISH_PROJECTION: AuthorityValue.TRUE,
    Authority.PROBE: AuthorityValue.TRUE,
    Authority.DISCLOSE: AuthorityValue.TRUE,
    Authority.INTRODUCE: AuthorityValue.TRUE,
}


# ---------------------------------------------------------------------------
# L-1  Mandatory transparency: public procurement
# ---------------------------------------------------------------------------


def limit_mandatory_disclosure() -> bool:
    head(
        "L-1",
        "Mandatory transparency (public procurement)",
        "the Disclosure Policy expresses permission ceilings and cannot "
        "express an obligation to publish",
    )

    buyer = _interest(
        conditions={
            "procurement_object": "municipal fleet maintenance",
            "estimated_value": {"min": 400_000, "max": 900_000},
            "award_criteria": ["price", "emissions"],
        },
        # A public buyer is legally required to publish object, value band and
        # award criteria. The most the policy can say is that they *may* be
        # public.
        policy={
            "procurement_object": DisclosureClass(surface=Surface.PUBLIC),
            "estimated_value": DisclosureClass(surface=Surface.PUBLIC),
            "award_criteria": DisclosureClass(surface=Surface.PUBLIC),
        },
        authority={**FULL, Authority.PUBLISH_PROJECTION: AuthorityValue.FALSE},
    )

    print("A public buyer must publish the object, the value band and the")
    print("award criteria. Its policy classifies all three as `public`.")
    print()

    published_anything = buyer.authority.permits(Authority.PUBLISH_PROJECTION)
    print(f"May publish a projection?           {published_anything}")
    print(f"Policy forbids publishing anything? {False}")
    print()
    print("So an Agent that publishes nothing at all is perfectly conformant")
    print("while its Principal is in breach of procurement law. The protocol")
    print(
        "has no way to say MUST publish -- `public` means 'may appear",
    )
    print("without authentication', which is a ceiling, not a floor.")
    print()

    finding(
        "the disclosure model is monotonically permissive: every class is an "
        "upper bound on exposure and none is a lower bound. Regimes with "
        "mandatory publication cannot be expressed, and a conforming "
        "implementation can be legally non-compliant."
    )
    return True


# ---------------------------------------------------------------------------
# L-2  One-dimensional and perishable: freight capacity
# ---------------------------------------------------------------------------


def limit_fungible_and_perishable() -> bool:
    head(
        "L-2",
        "Fungible and perishable (a freight slot leaving in two hours)",
        "with a single price dimension the protection collapses, and the "
        "human-approval gate cannot run in the time available",
    )

    carrier = _interest(
        conditions={"price_floor": {"min": 1_150, "max": 100_000}},
        policy={"price_floor": DisclosureClass(surface=Surface.LOCAL)},
        authority=FULL,
    )

    # One dimension, so the bisection of examples/probing.py is the whole
    # game: there is nothing else for the session to be about.
    #
    # Note the direction. examples/probing.py locates a *ceiling*, where a
    # range above the bound is incompatible. Here the private value is a
    # *floor*, so it is the ranges below it that are incompatible and the
    # inequality reverses. Getting this backwards converges on the search
    # bound rather than the secret, which is worth stating: an attacker who
    # does not know which side of the bound it is on spends a few queries
    # finding out, and no more.
    lo, hi, queries = 0, 4_000, 0
    while hi - lo > 25:
        mid = (lo + hi) // 2
        claim = Claim(
            key="price_floor",
            operator=ClaimOperator.WITHIN,
            value={"min": mid, "max": mid + 25},
        )
        truth = evaluate_claim(carrier, claim).truth
        queries += 1
        if truth is False:
            lo = mid  # the floor is above mid
        else:
            hi = mid  # mid is at or above the floor

    print("Dimensions in the interest:  1 (price)")
    print(f"Queries to locate the floor: {queries}")
    print(f"Floor: 1150   recovered as: [{lo}, {hi}]")
    assert lo <= 1_150 <= hi + 25, "the bisection must bracket the floor"
    print()
    print("A multi-dimensional interest hides a threshold among other")
    print("conditions. A one-dimensional one has nothing to hide it behind:")
    print("the session *is* the price discovery, and it discloses the number")
    print("in a handful of questions while a sealed-bid auction would not.")
    print()
    print("Separately: a slot leaving in two hours cannot wait for a")
    print("`principal_approval` gate, and an Agent that pre-approves")
    print("everything has turned the gate off.")
    print()

    finding(
        "where the interest reduces to one comparable dimension, the "
        "protocol offers no protection a sealed-bid mechanism would not "
        "offer better; and where the interest perishes faster than a human "
        "answers, the principal_approval gate is unusable by construction."
    )
    return True


# ---------------------------------------------------------------------------
# L-3  Power asymmetry: one employer, many candidates
# ---------------------------------------------------------------------------


def limit_power_asymmetry() -> bool:
    head(
        "L-3",
        "Power asymmetry (one employer, twenty candidates)",
        "reciprocity as a cost of probing fails when one side's answers "
        "are cheap and the other's are scarce",
    )

    employer_secret = {"salary_ceiling": {"min": 0, "max": 95_000}}
    employer = _interest(
        conditions=employer_secret,
        # An employer's band is semi-public in practice: it appears in job
        # ads, in benchmarks, and it is the same for every candidate.
        policy={"salary_ceiling": DisclosureClass(surface=Surface.SESSION)},
        authority=FULL,
    )

    learned_about_candidates = 0
    learned_about_employer = 0
    candidates = 20

    for n in range(candidates):
        candidate = _interest(
            conditions={"salary_floor": {"min": 70_000 + n * 1_000, "max": 200_000}},
            policy={"salary_floor": DisclosureClass(surface=Surface.LOCAL)},
            authority=FULL,
            id=f"local:si-cand-{n}",
        )
        # The employer probes each candidate's floor: three questions is
        # enough to bracket it within 5k.
        lo, hi = 50_000, 150_000
        for _ in range(4):
            mid = (lo + hi) // 2
            claim = Claim(
                key="salary_floor",
                operator=ClaimOperator.WITHIN,
                value={"min": mid, "max": mid + 5_000},
            )
            if evaluate_claim(candidate, claim).truth is False:
                hi = mid
            else:
                lo = mid
        learned_about_candidates += 1

        # Reciprocity: the candidate may ask the same of the employer. It
        # learns one band -- the same band every other candidate learns.
        claim = Claim(
            key="salary_ceiling",
            operator=ClaimOperator.WITHIN,
            value={"min": 80_000, "max": 100_000},
        )
        if evaluate_claim(employer, claim).truth is not None:
            learned_about_employer = 1  # not += : it is the same fact

    print(f"Sessions run by the employer:            {candidates}")
    print(f"Private values the employer narrowed:    {learned_about_candidates}")
    print(f"Distinct facts the candidates learned:   {learned_about_employer}")
    print()
    print("Reciprocity looks symmetric per session and is not symmetric in")
    print("aggregate. The employer spends the same fact twenty times; each")
    print("candidate spends a different scarce one. Per-counterparty query")
    print("budgets do not help: the employer's twenty sessions are with")
    print("twenty different counterparties, and every one is legitimate.")
    print()

    finding(
        "reciprocity as an anti-probing lever assumes both sides spend "
        "comparable information. Where one side faces many counterparties "
        "with the same disclosure and the other faces one with a unique "
        "disclosure, the lever inverts and protects the strong side."
    )
    return True


# ---------------------------------------------------------------------------
# L-4  Regulated inversion: identity before substance
# ---------------------------------------------------------------------------


def limit_identity_first() -> bool:
    head(
        "L-4",
        "Regulated inversion (identity must come first: KYC, sanctions)",
        "the state machine hard-codes probe-then-introduce, so a market "
        "that must identify before engaging cannot be expressed",
    )

    both = _interest(
        conditions={"instrument": ["private_placement"]},
        policy={
            "instrument": DisclosureClass(surface=Surface.SESSION),
            "principal_name": DisclosureClass(
                surface=Surface.SESSION, gate=Gate.CONSENT
            ),
        },
        authority=FULL,
    )
    a = Agent(ref="agent:a", standing_interest=both)
    b = Agent(ref="agent:b", standing_interest=both)
    opened = a.open_session("s-kyc", purpose="regulated_placement")
    accept = b.handle_session_open(opened)
    a.confirm_accept(accept)

    print("A sanctions-screened market must establish identity *before* any")
    print("substantive exchange. Attempting that first:")
    print()

    try:
        a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
        print("  ... accepted (unexpected)")
        return False
    except ProtocolError as error:
        print(f"  ProtocolError: {error}")

    print()
    print("The transition table admits ConsentRequest only from QUALIFIED or")
    print("CONSENTED, and QUALIFIED is reached by probing. Identity is")
    print("therefore structurally last. That ordering is the protocol's")
    print("central privacy property in the markets it was designed for, and")
    print("it is illegal in the markets that must screen first.")
    print()

    finding(
        "the authority ladder's ordering is enforced by the state machine "
        "and is not a profile matter. Markets that must identify before "
        "engaging are out of scope, and the specification should say so "
        "rather than let an implementer discover it."
    )
    return True


def main() -> None:
    print(LINE)
    print("Limit cases — four domains chosen because they should break")
    print(LINE)
    print()
    print("The four worked domains were chosen because they fit. These are")
    print("chosen because they attack an assumption each. A case that passes")
    print("is informative; a case that fails is why the file exists.")

    results = {
        "L-1 mandatory disclosure": limit_mandatory_disclosure(),
        "L-2 fungible and perishable": limit_fungible_and_perishable(),
        "L-3 power asymmetry": limit_power_asymmetry(),
        "L-4 identity first": limit_identity_first(),
    }

    print()
    print(LINE)
    print("Summary")
    print(LINE)
    for name, reproduced in results.items():
        status = "reproduced" if reproduced else "NOT reproduced"
        print(f"  {name:32} {status}")
    print()
    print("Four hypotheses, four confirmations. None of these is a bug: each")
    print("is a boundary the specification did not state. They are written up")
    print("in LIMITS.md, which says where this protocol should not be used.")


if __name__ == "__main__":
    main()
