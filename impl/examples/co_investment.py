"""Appendix C.5: co-investment — an interdependent conditional interest.

The fourth domain, and the one that presses on the boundary of GIDP 0.1.

The interest here is class 4 (Section 8.4): *I will consider X if another
party performs or commits to Y*. A family office will follow a round, but only
if a credible lead commits first. That dependency is real, it is the whole
substance of the interest, and the third party does not exist yet.

GIDP 0.1 is bilateral. It can *record* the dependency and carry it forward
honestly; it cannot discover the third party, which is what the experimental
multi-party section is for. Running the case anyway is the point: it shows
exactly where the bilateral core stops, and it found a gap in the
specification while doing so (SPEC-ISSUES.md S-11).

    python examples/co_investment.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp.agent import Agent  # noqa: E402
from gidp.objects import (  # noqa: E402
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
    Validity,
)
from gidp.transport import Wire  # noqa: E402
from gidp.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    Feature,
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
    for key in ("version", "expires_at", "session_id"):
        fields.pop(key, None)
    kind = fields.pop("type")
    print(f"{direction:>10} | {kind}: {fields}")


# --------------------------------------------------------------------------
# The family office: will follow, never lead. The ticket and the appetite
# stay home -- naming either invites being anchored in a negotiation.
# --------------------------------------------------------------------------

follower = StandingInterest(
    id="local:si-follower",
    principal_ref="local:principal-follower",
    interest=ConditionalInterest(
        action="consider_co_investment",
        object="series_b_round",
        conditions={
            "sector": ["climate_hardware", "industrial_software"],
            "stage": ["series_b"],
            "geography": ["france", "germany", "benelux"],
            "ticket": {"min": 2_000_000, "max": 5_000_000},
            "valuation_ceiling": {"max": 90_000_000},
            "principal_name": "A family office",
        },
        # The whole interest hangs on this, and no bilateral session can
        # resolve it: the lead does not exist yet.
        conditional_on=["qualified_lead_committed"],
        excludes=["cap_table_with_strategic_investor"],
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "sector": DisclosureClass(surface=Surface.DISCOVERY),
            "stage": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "ticket": DisclosureClass(surface=Surface.LOCAL),
            "valuation_ceiling": DisclosureClass(surface=Surface.LOCAL),
            # The dependency itself is disclosable: a follower saying "I need
            # a lead" gives nothing away, and hiding it would waste everyone's
            # time.
            "conditional_on": DisclosureClass(surface=Surface.SESSION),
            "excludes": DisclosureClass(surface=Surface.SESSION),
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
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.FALSE,
        },
        evidence_ref="urn:example:delegation:follower-2026-09",
    ),
    validity=Validity(expires_at=_in(180)),
)


# --------------------------------------------------------------------------
# The company raising: needs to know whether a round is assemblable at all,
# before it commits to running one. Its runway is the secret.
# --------------------------------------------------------------------------

company = StandingInterest(
    id="local:si-company",
    principal_ref="local:principal-company",
    interest=ConditionalInterest(
        action="explore_round_feasibility",
        object="series_b_round",
        conditions={
            "sector": ["climate_hardware"],
            "stage": ["series_b"],
            "geography": ["france"],
            "ticket": {"min": 1_000_000, "max": 8_000_000},
            "valuation_ceiling": {"min": 70_000_000, "max": 110_000_000},
            # Never transmitted: how long the company can wait. A counterparty
            # who learned this would price it.
            "runway_months": 7,
            "principal_name": "A climate hardware company",
        },
        provides=["qualified_lead_committed"],
        excludes=["cap_table_with_strategic_investor"],
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "sector": DisclosureClass(surface=Surface.DISCOVERY),
            "stage": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "ticket": DisclosureClass(surface=Surface.SESSION),
            "valuation_ceiling": DisclosureClass(surface=Surface.LOCAL),
            "runway_months": DisclosureClass(surface=Surface.LOCAL),
            "provides": DisclosureClass(surface=Surface.SESSION),
            "excludes": DisclosureClass(surface=Surface.SESSION),
            "principal_name": DisclosureClass(
                surface=Surface.SESSION, gate=Gate.PRINCIPAL_APPROVAL
            ),
        }
    ),
    authority=AuthoritySpec(
        levels={
            Authority.OBSERVE: AuthorityValue.TRUE,
            Authority.SEARCH: AuthorityValue.TRUE,
            Authority.PUBLISH_PROJECTION: AuthorityValue.FALSE,
            Authority.PROBE: AuthorityValue.TRUE,
            Authority.DISCLOSE: AuthorityValue.TRUE,
            Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.FALSE,
        },
        evidence_ref="urn:example:delegation:company-2026-09",
    ),
    validity=Validity(expires_at=_in(60)),
)


CLAIMS = [
    Claim(key="sector", operator=ClaimOperator.INTERSECTS, value=["climate_hardware"]),
    Claim(key="stage", operator=ClaimOperator.INTERSECTS, value=["series_b"]),
    Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["france"]),
    Claim(
        key="ticket",
        operator=ClaimOperator.OVERLAPS,
        value={"min": 1_000_000, "max": 8_000_000},
    ),
    Claim(
        key="valuation_ceiling",
        operator=ClaimOperator.OVERLAPS,
        value={"min": 70_000_000, "max": 110_000_000},
    ),
    # The dependency, asked plainly. The follower answers that it has one,
    # which tells the company the round is contingent, not assembled.
    Claim(
        key="conditional_on",
        operator=ClaimOperator.INTERSECTS,
        value=["qualified_lead_committed"],
    ),
]


def run(verbose: bool = True) -> tuple[Agent, Agent, Wire]:
    wire = Wire()
    co = Agent(
        ref="agent:opaque:company",
        standing_interest=company,
        pre_approved={"principal_name"},
    )
    fo = Agent(
        ref="agent:opaque:follower",
        standing_interest=follower,
        pre_approved={"principal_name"},
    )

    opened = wire.send(
        "Company",
        co.open_session(
            "coinvest-1",
            purpose="co_investment",
            features=[Feature.DEPENDENCY_PRIMITIVES],
        ),
    )
    accept = wire.send("Office", fo.handle_session_open(opened))
    co.confirm_accept(accept)

    request = wire.send("Company", co.ask(CLAIMS))
    response = wire.send("Office", fo.handle_compatibility_request(request))
    co.receive_compatibility_response(response, request)
    if verbose:
        show("Co -> Of", request)
        show("Of -> Co", response)

    fo.session.qualify()
    opportunity = None
    if co.session.qualify():
        opportunity = co.session.build_opportunity(
            structure="series B participation, contingent on a lead",
            expires_at=_in(30),
            identity_status={
                "initiator": IdentityStatus.NOT_REQUESTED,
                "responder": IdentityStatus.NOT_REQUESTED,
            },
        )
        wire.send("Company", opportunity)
        if verbose:
            show("Co -> Of", opportunity)

    creq = wire.send(
        "Company", co.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
    )
    cresp = wire.send("Office", fo.handle_consent_request(creq))
    co.session.record_consent(cresp)
    fo.session.record_consent(cresp, discharge=False)

    # NEGOTIATE_NONBINDING is false on both sides: the handoff goes to a human,
    # not to a negotiation protocol. Section 16.1 is explicit that proposing
    # terms, even non-binding ones, happens after a Handoff and never inside.
    hreq = wire.send(
        "Company",
        co.request_consent(ConsentAction.HANDOFF, ["https://example.org/human-review/v1"]),
    )
    hresp = wire.send("Office", fo.handle_consent_request(hreq))
    co.record_consent(hresp)
    fo.session.record_consent(hresp, discharge=False)
    if hresp.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
        hterm = wire.send("Office", fo.principal_answers_consent(hreq, granted=True))
        co.record_consent(hterm)
        fo.session.record_consent(hterm, discharge=False)
    handoff = wire.send("Company", co.handoff("https://example.org/human-review/v1"))
    fo.session.record_handoff(handoff)
    co.session.close(CloseReason.COMPLETED)
    fo.session.close(CloseReason.COMPLETED)
    return co, fo, wire


def main() -> None:
    print(LINE)
    print("Appendix C.5 — co-investment, an interdependent conditional interest")
    print(LINE)
    print()
    say("", "The family office will follow but never lead. Its whole interest")
    say("", "hangs on a third party who does not exist yet.")
    print()

    co, fo, wire = run(verbose=True)

    print()
    print(LINE)
    print("Where the bilateral core stops")
    print(LINE)
    say("Office", f"conditional_on: {follower.interest.conditional_on}")
    say("", "the session qualified, and the Opportunity is *contingent*: the")
    say("", "dependency is recorded and carried forward, not resolved.")
    say("", "finding the lead is multi-party discovery (Section 19.2),")
    say("", "which GIDP 0.1 marks experimental and this code does not implement.")
    say("", "the honest output is a qualified but contingent Opportunity,")
    say("", "handed to a human rather than to a negotiation protocol.")

    print()
    print(LINE)
    print("What stayed private")
    print(LINE)
    for name, interest in (("Office", follower), ("Company", company)):
        local = [
            key
            for key in list(interest.interest.conditions)
            if interest.class_of(key).surface is Surface.LOCAL
        ]
        say(name, f"never transmitted: {', '.join(local)}")
    say("", "the company's runway above all: a counterparty who learned it")
    say("", "would price it, and that is the asymmetry the protocol removes")


if __name__ == "__main__":
    main()
