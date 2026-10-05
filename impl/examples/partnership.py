"""Appendix C.3: a commercial partnership, using dependency primitives.

The third domain, and the first to use the dependency primitives of Section
19.1, `provides` and `requires`, bilaterally. Section 19.1 says only
`excludes` must be supported by every implementation; the other three require
the `dependency_primitives` feature, so this example is also the one that
exercises feature negotiation (Section 14.1).

The shape is a common one: two
companies whose partnership would work, and who will never find out,
because neither will tell the other what it lacks. Admitting a capability gap
to a potential partner is admitting it to a potential competitor.

    python examples/partnership.py
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
# A logistics platform: strong in Germany, no customs clearance capability.
# The gap is the secret: it is what a competitor would attack.
# --------------------------------------------------------------------------

logistics = StandingInterest(
    id="local:si-logistics",
    principal_ref="local:principal-logistics",
    interest=ConditionalInterest(
        action="consider_commercial_partnership",
        object="distribution_partnership",
        conditions={
            "domain": ["logistics"],
            "geography": ["germany", "austria"],
            "integration_surface": ["rest_api", "mcp"],
            # The gap, and the reason it stays local: telling a prospective
            # partner what you cannot do tells a prospective competitor too.
            "capability_gap": "customs_clearance_eu_uk",
            "margin_floor": {"min": 0.18},
            "principal_name": "A logistics platform",
        },
        provides=["last_mile_germany", "warehouse_network_dach"],
        requires=["customs_clearance_eu_uk"],
        excludes=["exclusive_arrangements"],
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "domain": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "integration_surface": DisclosureClass(surface=Surface.SESSION),
            # What I can bring is disclosable: it is what makes me findable.
            "provides": DisclosureClass(surface=Surface.SESSION),
            # What I need is the mirror of what I lack, so it stays home.
            "requires": DisclosureClass(surface=Surface.LOCAL),
            "excludes": DisclosureClass(surface=Surface.SESSION),
            "capability_gap": DisclosureClass(surface=Surface.LOCAL),
            "margin_floor": DisclosureClass(surface=Surface.LOCAL),
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
            Authority.INTRODUCE: AuthorityValue.TRUE,
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.TRUE,
        },
        evidence_ref="urn:example:delegation:logistics-2026-09",
    ),
    validity=Validity(expires_at=_in(120)),
)


# --------------------------------------------------------------------------
# A customs brokerage: has that capability, needs the network.
# --------------------------------------------------------------------------

brokerage = StandingInterest(
    id="local:si-brokerage",
    principal_ref="local:principal-brokerage",
    interest=ConditionalInterest(
        action="consider_commercial_partnership",
        object="distribution_partnership",
        conditions={
            "domain": ["logistics"],
            "geography": ["germany", "netherlands"],
            "integration_surface": ["rest_api", "mcp", "sftp"],
            "capability_gap": "last_mile_germany",
            "margin_floor": {"min": 0.12},
            "principal_name": "A customs brokerage",
        },
        provides=["customs_clearance_eu_uk", "bonded_warehousing"],
        requires=["last_mile_germany"],
        excludes=["white_label_only"],
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "domain": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "integration_surface": DisclosureClass(surface=Surface.SESSION),
            # What I can bring is disclosable: it is what makes me findable.
            "provides": DisclosureClass(surface=Surface.SESSION),
            # What I need is the mirror of what I lack, so it stays home.
            "requires": DisclosureClass(surface=Surface.LOCAL),
            "excludes": DisclosureClass(surface=Surface.SESSION),
            "capability_gap": DisclosureClass(surface=Surface.LOCAL),
            "margin_floor": DisclosureClass(surface=Surface.LOCAL),
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
            Authority.INTRODUCE: AuthorityValue.TRUE,
            Authority.NEGOTIATE_NONBINDING: AuthorityValue.TRUE,
        },
        evidence_ref="urn:example:delegation:brokerage-2026-09",
    ),
    validity=Validity(expires_at=_in(120)),
)


def _claims_for(mine: StandingInterest) -> list[Claim]:
    """Ask whether the counterparty provides what I require, and conversely.

    Section 19.1 used bilaterally: `requires: X` on one side meets
    `provides: X` on the other. Note that the *gap* itself is never named on
    the wire as a gap: the claim asks about a capability, and only the
    asker's own Standing Interest records that it is missing.
    """
    claims = [
        Claim(key="domain", operator=ClaimOperator.INTERSECTS, value=["logistics"]),
        Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["germany"]),
        Claim(
            key="integration_surface",
            operator=ClaimOperator.INTERSECTS,
            value=["rest_api", "mcp"],
        ),
    ]
    for capability in mine.interest.requires:
        claims.append(
            Claim(key="provides", operator=ClaimOperator.INTERSECTS, value=[capability])
        )
    # And the mirror question, which comes back coarsened: does the other
    # side need something I happen to have? Its `requires` is evaluation-only.
    for capability in mine.interest.provides[:1]:
        claims.append(
            Claim(key="requires", operator=ClaimOperator.INTERSECTS, value=[capability])
        )
    return claims


def run(verbose: bool = True) -> tuple[Agent, Agent, Wire]:
    wire = Wire()
    a = Agent(
        ref="agent:opaque:logistics",
        standing_interest=logistics,
        pre_approved={"principal_name"},
    )
    b = Agent(
        ref="agent:opaque:brokerage",
        standing_interest=brokerage,
        pre_approved={"principal_name"},
    )

    opened = wire.send(
        "Logis.",
        a.open_session(
            "partnership-1",
            purpose="commercial_partnership",
            features=[Feature.DEPENDENCY_PRIMITIVES],
        ),
    )
    accept = wire.send("Broker", b.handle_session_open(opened))
    a.confirm_accept(accept)

    if verbose:
        show("A -> B", opened)
        show("B -> A", accept)
        say(
            "",
            f"features in force: "
            f"{', '.join(f.value for f in a.session.features) or 'core only'}",
        )

    request = wire.send("Logis.", a.ask(_claims_for(logistics)))
    response = wire.send("Broker", b.handle_compatibility_request(request))
    a.receive_compatibility_response(response)
    if verbose:
        show("A -> B", request)
        show("B -> A", response)

    b.session.qualify()
    opportunity = None
    if a.session.qualify():
        opportunity = a.session.build_opportunity(
            structure="distribution partnership: last mile x customs clearance",
            expires_at=_in(21),
            identity_status={
                "initiator": IdentityStatus.NOT_REQUESTED,
                "responder": IdentityStatus.NOT_REQUESTED,
            },
        )
        wire.send("Logis.", opportunity)
        if verbose:
            show("A -> B", opportunity)

    creq = wire.send(
        "Logis.", a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
    )
    cresp = wire.send("Broker", b.handle_consent_request(creq))
    a.session.record_consent(cresp)
    b.session.record_consent(cresp, discharge=False)

    hreq = wire.send(
        "Logis.",
        a.request_consent(ConsentAction.HANDOFF, ["https://example.org/negotiation/v1"]),
    )
    hresp = wire.send("Broker", b.handle_consent_request(hreq))
    a.record_consent(hresp)
    b.session.record_consent(hresp, discharge=False)
    if hresp.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
        hterm = wire.send("Broker", b.principal_answers_consent(hreq, granted=True))
        a.record_consent(hterm)
        b.session.record_consent(hterm, discharge=False)
    handoff = wire.send("Logis.", a.handoff("https://example.org/negotiation/v1"))
    b.session.record_handoff(handoff)
    a.session.close(CloseReason.COMPLETED)
    b.session.close(CloseReason.COMPLETED)
    return a, b, wire


def main() -> None:
    print(LINE)
    print("Appendix C.3: commercial partnership, with dependency primitives")
    print(LINE)
    print()
    say("", "Each side lacks what the other has. Neither will say so:")
    say("", "a capability gap admitted to a partner is admitted to a rival.")
    print()

    a, b, wire = run(verbose=True)

    print()
    print(LINE)
    print("What the dependency primitives did")
    print(LINE)
    say(
        "Logis.",
        f"requires {logistics.interest.requires}; "
        f"provides {logistics.interest.provides}",
    )
    say(
        "Broker",
        f"requires {brokerage.interest.requires}; "
        f"provides {brokerage.interest.provides}",
    )
    say("", "the match is exact and neither side named its own gap on the wire:")
    for name, _unused in (("Logis.", logistics), ("Broker", brokerage)):
        say(name, "never transmitted: capability_gap, margin_floor")

    print()
    print(LINE)
    print("Horizontality (Appendix F.2), third domain")
    print(LINE)
    say("", f"{len(wire.transcript)} objects, all from the GIDP 0.1 core set")
    say("", "the only novelty is the declared feature: dependency_primitives,")
    say("", "which adds claim keys and no objects, operators or states")


if __name__ == "__main__":
    main()
