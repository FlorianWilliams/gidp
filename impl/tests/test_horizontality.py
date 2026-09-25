"""Appendix F.2, the horizontality hypothesis, checked mechanically.

The specification says GIDP should not become a protocol layer merely because
the abstraction is appealing, and states the validation: the same core
implementation across materially different domains, changing primarily
vocabularies and validation rules.

Two domains is not four, so this proves nothing on its own. What it does is
make the claim falsifiable and cheap to re-check: add a third scenario, and if
it needs an object, an operator, a disclosure class, an authority level or a
state that the others did not, this test fails and the hypothesis is in
trouble.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

import co_investment  # noqa: E402
import executive_succession as succession  # noqa: E402
import partnership  # noqa: E402
from test_scenario import _run as run_cross_border  # noqa: E402

from gidp.vocab import ClaimOperator, ClaimResult, Gate, Surface  # noqa: E402


def _all_domains():
    """The four domains Appendix F.2 asks for.

    A corporate transaction, an executive appointment, a commercial
    partnership and a financing — materially different markets, different
    parties, different secrets. If the same objects, operators and results
    carry all four, the horizontality hypothesis has survived its first real
    test. It is not proof: four is the threshold the specification set for
    itself, not a law of nature.
    """
    return {
        "cross-border transaction": run_cross_border()[2],
        "executive succession": succession.run(verbose=False)[2],
        "commercial partnership": partnership.run(verbose=False)[2],
        "co-investment": co_investment.run(verbose=False)[2],
    }


def _vocabulary(wire) -> dict[str, set[str]]:
    """Everything the session used, by kind."""
    used: dict[str, set[str]] = {
        "objects": set(),
        "operators": set(),
        "results": set(),
        "claim_keys": set(),
    }
    for _, message in wire.transcript:
        used["objects"].add(message.type)
        for claim in getattr(message, "claims", []) or []:
            used["operators"].add(claim.operator.value)
            used["claim_keys"].add(claim.key)
        for outcome in getattr(message, "results", []) or []:
            used["results"].add(outcome.result.value)
            used["claim_keys"].add(outcome.key)
    return used


def test_every_domain_uses_the_same_protocol_machinery():
    """The objects, operators and results are shared across every domain.

    A domain that needed an object, an operator or a result of its own would
    be evidence against Appendix F.2, and this test is how we would find out.
    """
    domains = _all_domains()
    reference = _vocabulary(domains["cross-border transaction"])

    for name, wire in domains.items():
        used = _vocabulary(wire)
        assert used["objects"] <= reference["objects"], (
            f"{name} used objects the reference domain did not: "
            f"{used['objects'] - reference['objects']}"
        )
        assert used["operators"] <= reference["operators"], name
        assert used["results"] <= reference["results"], name

    # What differs is the vocabulary, which is what the hypothesis predicts.
    keys = {name: _vocabulary(wire)["claim_keys"] for name, wire in domains.items()}
    assert keys["cross-border transaction"] != keys["executive succession"]
    assert keys["commercial partnership"] != keys["executive succession"]
    assert keys["co-investment"] != keys["commercial partnership"]


def test_no_domain_needed_a_value_outside_the_closed_vocabularies():
    for wire in _all_domains().values():
        used = _vocabulary(wire)
        assert used["operators"] <= {o.value for o in ClaimOperator}
        assert used["results"] <= {r.value for r in ClaimResult}


def test_every_domain_uses_the_core_profile_only():
    """Three domains, one profile: the differences are policy, not protocol."""
    for wire in _all_domains().values():
        for _, message in wire.transcript:
            profile = getattr(message, "profile", None)
            if profile is not None:
                assert profile == "core"


def test_the_difference_between_domains_is_policy_not_protocol():
    """The two Principals differ in what they keep local, not in mechanics."""
    from cross_border import a_interest, b_interest

    domains = {
        "transaction": (a_interest, b_interest),
        "succession": (succession.candidate, succession.board),
        "partnership": (partnership.logistics, partnership.brokerage),
        "co-investment": (co_investment.follower, co_investment.company),
    }
    for name, interests in domains.items():
        for interest in interests:
            for cls in interest.disclosure_policy.attributes.values():
                assert cls.surface in set(Surface), name
                assert cls.gate in set(Gate), name
        # Every domain keeps something evaluation-only: that is the point.
        assert any(
            interest.class_of(key).surface is Surface.LOCAL
            for interest in interests
            for key in interest.interest.conditions
        ), name
