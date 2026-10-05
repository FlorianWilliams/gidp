"""Adversarial probing of a truthful compatibility oracle (Section 24.3).

This example implements the attack the specification names as its open
problem, and measures it. It ships with the protocol on purpose: an
implementer setting a query budget deserves a measured number to set it by,
and a weakness the authors demonstrate themselves is one nobody has to publish
as a finding against us.

The responder here does nothing wrong. It answers truthfully or declines, it
never transmits its threshold, and every answer is permitted by Section 15.5.
The threshold leaks anyway, because an oracle that discriminates is an oracle
that informs.

    python -m examples.probing
"""

from __future__ import annotations

import sys
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
)
from gidp.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ClaimOperator,
    ClaimResult,
    Surface,
)

SECRET_THRESHOLD = 80_000_000
LINE = "-" * 78


def build_responder(budget: int) -> Agent:
    """An honest responder with a private maximum valuation."""
    interest = StandingInterest(
        id="local:si-target",
        principal_ref="local:principal-target",
        interest=ConditionalInterest(
            action="consider_strategic_transaction",
            conditions={"valuation_class": {"min": 0, "max": SECRET_THRESHOLD}},
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                # Evaluation-only: usable locally, never transmitted (9.1).
                "valuation_class": DisclosureClass(surface=Surface.LOCAL)
            }
        ),
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.DISCLOSE: AuthorityValue.TRUE,
            }
        ),
    )
    return Agent(
        ref="agent:opaque:target", standing_interest=interest, query_budget=budget
    )


def probe(attacker: Agent, target: Agent, low: int, high: int) -> ClaimResult:
    """Ask one claim: is a transaction within [low, high] compatible?"""
    request = attacker.ask(
        [
            Claim(
                key="valuation_class",
                operator=ClaimOperator.OVERLAPS,
                value={"min": low, "max": high},
            )
        ]
    )
    response = target.handle_compatibility_request(request)
    attacker.receive_compatibility_response(response)
    return response.results[0].result


def bisect(attacker: Agent, target: Agent, lo: int, hi: int, precision: int) -> tuple:
    """Locate the private bound by bisection, reporting every query."""
    queries = 0
    trace: list[str] = []

    while hi - lo > precision:
        mid = (lo + hi) // 2
        # A range strictly above the bound is incompatible; one that overlaps
        # it is not. That single bit per query is all the attacker needs.
        result = probe(attacker, target, mid, mid + precision)
        queries += 1
        trace.append(
            f"  [{mid / 1e6:7.1f}M .. {(mid + precision) / 1e6:7.1f}M] -> {result.value}"
        )
        if result is ClaimResult.DECLINED:
            trace.append("  budget exhausted; the responder stopped answering")
            break
        if result is ClaimResult.INCOMPATIBLE:
            hi = mid
        else:
            lo = mid

    return lo, hi, queries, trace


def main() -> None:
    precision = 1_000_000

    print(LINE)
    print("Adversarial probing of a truthful compatibility oracle")
    print(LINE)
    print()
    print("The responder holds a private maximum valuation and will never")
    print("transmit it. Every answer below is truthful under Section 15.5.")
    print()

    for budget in (100, 5):
        target = build_responder(budget)
        attacker_interest = StandingInterest(
            id="local:si-attacker",
            principal_ref="local:principal-attacker",
            interest=ConditionalInterest(
                action="probe",
            ),
            authority=AuthoritySpec(levels={Authority.PROBE: AuthorityValue.TRUE}),
        )
        attacker = Agent(
            ref="agent:opaque:attacker", standing_interest=attacker_interest
        )
        opened = attacker.open_session("probe-session", purpose="strategic_transaction")
        accept = target.handle_session_open(opened)
        attacker.confirm_accept(accept)

        lo, hi, queries, trace = bisect(attacker, target, 0, 200_000_000, precision)

        print(f"query budget = {budget}")
        for line in trace[:6]:
            print(line)
        if len(trace) > 6:
            print(f"  ... {len(trace) - 6} further queries")
        print()
        print(f"  queries used:      {queries}")
        print(f"  secret threshold:  {SECRET_THRESHOLD / 1e6:.1f}M")
        print(f"  attacker's belief: between {lo / 1e6:.1f}M and {hi / 1e6:.1f}M")
        error = min(abs(lo - SECRET_THRESHOLD), abs(hi - SECRET_THRESHOLD))
        print(f"  error:             {error / 1e6:.1f}M")
        print()

    print(LINE)
    print("What this shows")
    print(LINE)
    print("A value that is never transmitted is located to within a bucket in a")
    print("handful of queries. A budget low enough to stop the attacker also")
    print("stops an honest counterparty from resolving a real question: the")
    print("two are the same lever. Section 24.3 states the open problem; this")
    print("is what it costs, and why the abuse controls of 12.5 and 24.3 are")
    print("engineering mitigations and not guarantees.")


if __name__ == "__main__":
    main()
