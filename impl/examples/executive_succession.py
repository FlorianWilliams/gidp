"""Appendix C.2: executive succession, person <-> organisation.

This example exists to test Appendix F.2, the horizontality hypothesis, which
is the claim the publication puts at risk:

    A strong validation would run the same core implementation across at least
    four domains while changing primarily vocabularies and validation rules,
    keeping Standing Interest, Disclosure Policy, Discovery Projection,
    candidate retrieval, compatibility, progressive disclosure, authority,
    consent and Handoff substantially unchanged.

What matters in this file is what is *not* in it. There is no new
object, no new claim operator, no new disclosure class, no new authority level
and no new state. Compared with `cross_border.py`, a cross-border corporate
transaction, the only differences are the claim keys, the values, and which
attributes the two Principals choose to keep evaluation-only.

A domain where that stopped being true would be evidence against the protocol,
and `tests/test_horizontality.py` checks it mechanically instead of relying on
this paragraph.

    python examples/executive_succession.py
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
# The candidate: not looking, would consider under conditions (class 1).
# --------------------------------------------------------------------------

candidate = StandingInterest(
    id="local:si-candidate",
    principal_ref="local:principal-candidate",
    interest=ConditionalInterest(
        action="consider_executive_role",
        object="chief_executive",
        conditions={
            "role": ["ceo"],
            "sector": ["b2b_software"],
            "geography": ["paris", "london"],
            "company_scale": {"min": 20_000_000},
            # Never transmitted: the two things that would end a career if
            # they reached the wrong desk.
            "equity_floor": {"min": 1_500_000},
            "current_employer_constraint": "no_direct_competitor_of_incumbent",
            "principal_name": "A candidate",
        },
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "role": DisclosureClass(surface=Surface.DISCOVERY),
            "sector": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "company_scale": DisclosureClass(surface=Surface.SESSION),
            "equity_floor": DisclosureClass(surface=Surface.LOCAL),
            "current_employer_constraint": DisclosureClass(surface=Surface.LOCAL),
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
            # A candidate in post does not let an agent reveal who they are.
            Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
        },
        evidence_ref="urn:example:delegation:candidate-2026-09",
    ),
    validity=Validity(expires_at=_in(180)),
)


# --------------------------------------------------------------------------
# The board: searching, and the search itself is the secret (class 2).
# --------------------------------------------------------------------------

board = StandingInterest(
    id="local:si-board",
    principal_ref="local:principal-board",
    interest=ConditionalInterest(
        action="explore_executive_succession",
        object="chief_executive",
        conditions={
            "role": ["ceo"],
            "sector": ["b2b_software"],
            "geography": ["paris"],
            "company_scale": {"min": 45_000_000, "max": 60_000_000},
            # Never transmitted: that the incumbent is leaving, and when.
            "succession_timing": "within_two_quarters",
            "board_context": "incumbent_departure_unannounced",
            "equity_envelope": {"min": 800_000, "max": 2_500_000},
            "principal_name": "A listed company",
        },
    ),
    disclosure_policy=DisclosurePolicy(
        attributes={
            "role": DisclosureClass(surface=Surface.DISCOVERY),
            "sector": DisclosureClass(surface=Surface.DISCOVERY),
            "geography": DisclosureClass(surface=Surface.DISCOVERY),
            "company_scale": DisclosureClass(surface=Surface.SESSION),
            "succession_timing": DisclosureClass(surface=Surface.LOCAL),
            "board_context": DisclosureClass(surface=Surface.LOCAL),
            "equity_envelope": DisclosureClass(surface=Surface.LOCAL),
            "principal_name": DisclosureClass(
                surface=Surface.SESSION, gate=Gate.PRINCIPAL_APPROVAL
            ),
        }
    ),
    authority=AuthoritySpec(
        levels={
            Authority.OBSERVE: AuthorityValue.TRUE,
            Authority.SEARCH: AuthorityValue.TRUE,
            Authority.PUBLISH_PROJECTION: AuthorityValue.FALSE,  # publishes nothing
            Authority.PROBE: AuthorityValue.TRUE,
            Authority.DISCLOSE: AuthorityValue.TRUE,
            Authority.INTRODUCE: AuthorityValue.APPROVAL_REQUIRED,
        },
        evidence_ref="urn:example:delegation:board-2026-09",
    ),
    validity=Validity(expires_at=_in(120)),
)


CLAIMS = [
    Claim(key="role", operator=ClaimOperator.INTERSECTS, value=["ceo"]),
    Claim(key="sector", operator=ClaimOperator.INTERSECTS, value=["b2b_software"]),
    Claim(key="geography", operator=ClaimOperator.INTERSECTS, value=["paris"]),
    Claim(
        key="company_scale",
        operator=ClaimOperator.OVERLAPS,
        value={"min": 40_000_000, "max": 80_000_000},
    ),
    # The board probes the candidate's equity expectation without naming its
    # own envelope; the candidate answers from a value it never transmits.
    Claim(
        key="equity_floor",
        operator=ClaimOperator.OVERLAPS,
        value={"min": 800_000, "max": 2_500_000},
    ),
]


def run(verbose: bool = True) -> tuple[Agent, Agent, Wire]:
    wire = Wire()
    # The board initiates: it is the side that is searching, and the
    # side that must not publish a projection to do so.
    b = Agent(
        ref="agent:opaque:board",
        standing_interest=board,
        pre_approved={"principal_name"},
    )
    c = Agent(
        ref="agent:opaque:candidate",
        standing_interest=candidate,
        pre_approved={"principal_name"},
    )

    opened = wire.send(
        "Board", b.open_session("succession-1", purpose="executive_role")
    )
    accept = wire.send("Cand.", c.handle_session_open(opened))
    b.confirm_accept(accept)

    request = wire.send("Board", b.ask(CLAIMS))
    response = wire.send("Cand.", c.handle_compatibility_request(request))
    b.receive_compatibility_response(response)

    if verbose:
        show("B -> C", request)
        show("C -> B", response)

    c.session.qualify()
    qualified = b.session.qualify()
    opportunity = None
    if qualified:
        opportunity = b.session.build_opportunity(
            structure="executive succession, Paris, B2B software",
            expires_at=_in(14),
            identity_status={
                "initiator": IdentityStatus.NOT_REQUESTED,
                "responder": IdentityStatus.NOT_REQUESTED,
            },
        )
        wire.send("Board", opportunity)
        if verbose:
            show("B -> C", opportunity)

    creq = wire.send(
        "Board", b.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])
    )
    cresp = wire.send("Cand.", c.handle_consent_request(creq))
    b.session.record_consent(cresp)
    c.session.record_consent(cresp, discharge=False)
    if verbose:
        show("C -> B", cresp)

    hreq = wire.send(
        "Board",
        b.request_consent(ConsentAction.HANDOFF, ["https://example.org/introduction/v1"]),
    )
    hresp = wire.send("Cand.", c.handle_consent_request(hreq))
    b.record_consent(hresp)
    c.session.record_consent(hresp, discharge=False)
    if hresp.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
        hterm = wire.send("Cand.", c.principal_answers_consent(hreq, granted=True))
        b.record_consent(hterm)
        c.session.record_consent(hterm, discharge=False)
    handoff = wire.send("Board", b.handoff("https://example.org/introduction/v1"))
    c.session.record_handoff(handoff)
    b.session.close(CloseReason.COMPLETED)
    c.session.close(CloseReason.COMPLETED)
    return b, c, wire


def main() -> None:
    print(LINE)
    print("Appendix C.2: executive succession (person <-> organisation)")
    print(LINE)
    print()
    say("", "The candidate is not looking. The board's search is itself the")
    say("", "secret: it holds PUBLISH_PROJECTION = false and publishes nothing.")
    print()

    b, c, wire = run(verbose=True)

    print()
    print(LINE)
    print("What stayed private")
    print(LINE)
    for name, interest in (("Cand.", candidate), ("Board", board)):
        local = [
            key
            for key in interest.interest.conditions
            if interest.class_of(key).surface is Surface.LOCAL
        ]
        say(name, f"never transmitted: {', '.join(local)}")
    say("", "the candidate's employer never learns a conversation happened,")
    say("", "and the incumbent's departure was never mentioned on the wire")

    print()
    print(LINE)
    print("Horizontality (Appendix F.2)")
    print(LINE)
    say("", f"{len(wire.transcript)} objects, all from the GIDP 0.1 core set")
    say("", "no new object, operator, disclosure class, authority level or state")
    say("", "compared with the cross-border transaction in cross_border.py")
    say("", "what changed: claim keys, values, and what each side keeps local")


if __name__ == "__main__":
    main()
