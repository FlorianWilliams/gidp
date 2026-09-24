"""Appendix C.1 of CID 0.1, end to end, printing the full transcript.

*Principal A*, a French software company, privately authorises its Agent to
explore expansion into Germany. *Principal B*, a German software company, is
not for sale, but its Agent is authorised to explore a strategic transaction
if the counterparty provides access to France, the founder stays operationally
involved, and a private valuation threshold is met.

Neither company ever states "we want to buy" or "we might sell". Run it:

    python -m examples.cross_border
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cid.agent import Agent  # noqa: E402
from cid.objects import (  # noqa: E402
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
    Validity,
)
from cid.policy import RetrievalAttribute, derive_projection  # noqa: E402
from cid.provider import InMemoryProvider  # noqa: E402
from cid.transport import Wire  # noqa: E402
from cid.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    Gate,
    IdentityStatus,
    Surface,
)

LINE = "-" * 78


def _in(days: int = 30) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


def say(who: str, what: str) -> None:
    print(f"{who:>10} | {what}")


def show(direction: str, message) -> None:
    fields = message.model_dump(exclude_none=True, mode="json")
    fields.pop("version", None)
    fields.pop("expires_at", None)
    fields.pop("session_id", None)
    kind = fields.pop("type")
    print(f"{direction:>10} | {kind}: {fields}")


# --------------------------------------------------------------------------
# The two Standing Interests. Neither is ever transmitted (Section 9.1).
# --------------------------------------------------------------------------

a_interest = StandingInterest(
    id="local:si-a",
    principal_ref="local:principal-a",
    interest=ConditionalInterest(
        action="explore_strategic_transaction",
        object="german_enterprise_software",
        structures=[
            "acquisition",
            "majority_investment",
            "distribution",
            "joint_venture",
        ],
        conditions={
            "domain": ["enterprise_software"],
            "geography": ["europe", "germany"],
            "transaction_structures": [
                "acquisition",
                "majority_investment",
                "distribution",
                "joint_venture",
            ],
            "market_access": "france",
            "budget_ceiling": {"max": 120_000_000},
            "principal_name": "Principal A",
        },
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "domain": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "transaction_structures": DisclosureClass(surface=Surface.SESSION),
            "market_access": DisclosureClass(surface=Surface.SESSION),
            # The budget never leaves the Agent: it is evaluation-only.
            "budget_ceiling": DisclosureClass(surface=Surface.LOCAL),
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
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.TRUE,
        },
        evidence_ref="urn:example:delegation:a-2026-09",
    ),
    validity=Validity(expires_at=_in(90)),
)

b_interest = StandingInterest(
    id="local:si-b",
    principal_ref="local:principal-b",
    interest=ConditionalInterest(
        action="consider_strategic_transaction",
        object="own_company",
        conditions={
            "domain": ["enterprise_software"],
            "geography": ["europe", "germany"],
            "transaction_structures": ["majority_investment", "distribution"],
            "market_access": "france",
            # Private: a valuation floor and a management condition, both of
            # which are answered without ever being transmitted.
            "valuation_class": {"min": 45_000_000, "max": 80_000_000},
            "management_condition": "founder_operational",
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
            "valuation_class": DisclosureClass(surface=Surface.LOCAL),
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
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.TRUE,
        },
        evidence_ref="urn:example:delegation:b-2026-09",
    ),
    validity=Validity(expires_at=_in(90)),
)


def main() -> None:
    a = Agent(
        ref="agent:opaque:a",
        standing_interest=a_interest,
        pre_approved={"principal_name"},
    )
    b = Agent(
        ref="agent:opaque:b",
        standing_interest=b_interest,
        pre_approved={"principal_name"},
    )

    print(LINE)
    print("Stage 1-2  Projection and candidate retrieval (Sections 11, 12)")
    print(LINE)

    wire = Wire()
    provider = InMemoryProvider()
    symmetric = RetrievalAttribute(
        "relation", None, lambda _: ["complementary_counterparty"]
    )
    b_projection = derive_projection(
        b_interest,
        projection_id="opaque-projection-b",
        endpoint="agent:opaque:b",
        expires_at=_in(30),
        interest_ref="opaque-ref-b",
        attributes=[
            RetrievalAttribute("categories", None, lambda _: ["strategic_transaction"]),
            RetrievalAttribute("domains", "domain", lambda v: list(v)),
            RetrievalAttribute("geographies", "geography", lambda v: ["europe"]),
            symmetric,
        ],
    )
    provider.publish_projection(b_projection)
    published = b_projection.model_dump(
        include={"categories", "domains", "geographies", "relation"}, mode="json"
    )
    say("B", f"published a projection: {published}")
    say("", "note what is absent: identity, direction, valuation, the exclusions")

    query = derive_projection(
        a_interest,
        projection_id="opaque-query-a",
        endpoint="agent:opaque:a",
        expires_at=_in(1),
        interest_ref=None,
        attributes=[
            RetrievalAttribute("categories", None, lambda _: ["strategic_transaction"]),
            RetrievalAttribute("domains", "domain", lambda v: list(v)),
            RetrievalAttribute("geographies", "geography", lambda v: ["europe"]),
            symmetric,
        ],
    )
    hits = provider.query_candidates(query)
    say("A", f"retrieved {len(hits)} candidate(s): {hits}")
    say("A", f"resolved endpoint: {provider.resolve_candidate(hits[0])}")
    print()
    say("", "retrieval is not compatibility, consent or agreement (Section 11.6)")

    print()
    print(LINE)
    print("Stage 3  Session initiation (Section 14.1)")
    print(LINE)

    open_msg = wire.send(
        "A", a.open_session("opaque-session-1", purpose="strategic_transaction")
    )
    show("A -> B", open_msg)
    accept = wire.send("B", b.handle_session_open(open_msg))
    show("B -> A", accept)
    a.confirm_accept(accept)
    say("", f"depth in force: {a.session.max_depth.value}")

    print()
    print(LINE)
    print("Stage 4  Compatibility probing (Sections 14.2, 15)")
    print(LINE)

    claims = [
        Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["germany"]),
        Claim(
            key="transaction_structures",
            operator=ClaimOperator.INTERSECTS,
            value=["majority_investment", "distribution"],
        ),
        Claim(key="market_access", operator=ClaimOperator.EQUALS, value="france"),
        Claim(
            key="valuation_class",
            operator=ClaimOperator.WITHIN,
            value={"min": 50_000_000, "max": 100_000_000},
        ),
        Claim(
            key="management_condition",
            operator=ClaimOperator.EQUALS,
            value="founder_operational",
        ),
    ]
    request = wire.send("A", a.ask(claims))
    show("A -> B", request)
    response = wire.send("B", b.handle_compatibility_request(request))
    show("B -> A", response)
    a.receive_compatibility_response(response)

    say("", "B answered two claims from values it never transmitted:")
    say("", "  valuation_class and management_condition are evaluation-only,")
    say("", "  so the truthful answer was coarsened (Sections 15.4, 15.5)")

    print()
    print(LINE)
    print("Stage 5  Progressive disclosure (Section 14.4)")
    print(LINE)

    dreq = wire.send(
        "B",
        b.request_disclosure(
            "market_access", "confirm the France access B requires", reciprocal=True
        ),
    )
    show("B -> A", dreq)
    dresp = wire.send("A", a.handle_disclosure_request(dreq))
    show("A -> B", dresp)
    b.session.record_disclosure(dresp)

    print()
    print(LINE)
    print("Stage 6  Opportunity (Section 14.6)")
    print(LINE)

    say("A", f"session_status = {a.session.status().value}")
    b.session.qualify()
    if a.session.qualify():
        opportunity = a.session.build_opportunity(
            structure="minority investment + distribution agreement",
            expires_at=_in(7),
            identity_status={
                "initiator": IdentityStatus.NOT_REQUESTED,
                "responder": IdentityStatus.NOT_REQUESTED,
            },
        )
        wire.send("A", opportunity)
        show("A -> B", opportunity)

    print()
    print(LINE)
    print("Stage 7  Consent to reveal identity (Section 14.5)")
    print(LINE)

    creq = wire.send(
        "A", a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
    )
    show("A -> B", creq)
    cresp = wire.send("B", b.handle_consent_request(creq))
    show("B -> A", cresp)
    a.session.record_consent(cresp)
    b.session.record_consent(cresp, discharge=False)
    if cresp.status is ConsentStatus.GRANTED:
        say("", "identity is gated by principal_approval on both sides;")
        say("", "the Principal decided, so the Agent could answer terminally")

    print()
    print(LINE)
    print("Stage 8  Handoff (Section 14.7)")
    print(LINE)

    handoff = wire.send(
        "A", a.handoff(protocol_ref="https://example.org/negotiation/v1")
    )
    show("A -> B", handoff)
    b.session.record_handoff(handoff)
    a.session.close(CloseReason.COMPLETED)
    b.session.close(CloseReason.COMPLETED)
    say("", "CID's responsibility ends here; terms are never proposed in-session")

    print()
    print(LINE)
    print("What never crossed the wire")
    print(LINE)
    for name, interest in (("A", a_interest), ("B", b_interest)):
        local = [
            key
            for key in interest.interest.conditions
            if interest.class_of(key).surface is Surface.LOCAL
        ]
        say(name, f"evaluation-only attributes: {', '.join(local) or 'none'}")
    say("", "and neither side ever stated a direction: buy or sell")

    print()
    print(LINE)
    print("What the wire checked (Section 14)")
    print(LINE)
    say("", f"{len(wire.transcript)} objects carried between the two Agents")
    unanswered = wire.unanswered()
    say("", f"requests left unanswered: {len(unanswered)}")
    assert not unanswered, (
        "every request must be answered by exactly one response or a "
        f"SessionClose (Section 14); left open: {unanswered}"
    )
    say("", "every request/response pair correlated, no request answered twice,")
    say("", "no Agent answered its own request, no object outside the 0.1 set")

    print()
    print(LINE)
    print("A's local audit trail (Section 25.3)")
    print(LINE)
    for entry in a.audit:
        say(entry.event, entry.detail)


if __name__ == "__main__":
    main()
