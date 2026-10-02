"""The profile manifest format, its validator, and the contrasted pair.

The pair is the point (FORMAT.md): one narrow and numeric
(co-investment), one relational and asymmetric (executive-succession),
both instances of the same manifest format, both driving the same core
through the same machinery. If both hold, verticals multiply without new
protocol work; that is the horizontality claim made testable.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_conformance import _interest  # noqa: E402

from gidp.agent import Agent  # noqa: E402
from gidp.objects import Claim, ConditionalInterest, DisclosurePolicy  # noqa: E402
from gidp.vocab import ClaimOperator, SessionStatus  # noqa: E402
from tools.validate_profile import validate_manifest  # noqa: E402

PROFILES = Path(__file__).resolve().parents[2] / "profiles"
MANIFESTS = sorted(PROFILES.glob("*.profile.json"))


def _load(name: str) -> dict:
    return json.loads((PROFILES / name).read_text())


# -- the pair validates -----------------------------------------------------


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.stem)
def test_published_manifest_is_valid(path):
    assert validate_manifest(json.loads(path.read_text())) == []


def test_the_pair_is_contrasted_on_purpose():
    """One narrow and numeric, one relational and asymmetric -- the same
    format carries both, which is the claim."""
    assert len(MANIFESTS) >= 2
    co = _load("co-investment-0.1.profile.json")
    succ = _load("executive-succession-0.1.profile.json")
    subjects = {a["subject"] for a in succ["attributes"].values()}
    assert "side_dependent" in subjects, "the asymmetric instance is asymmetric"
    assert "side_dependent" not in {
        a["subject"] for a in co["attributes"].values()
    }, "the narrow instance is not"
    assert any(a.get("identifying") for a in succ["attributes"].values())


# -- the validator refuses what would weaken the core -----------------------


def _co() -> dict:
    return copy.deepcopy(_load("co-investment-0.1.profile.json"))


def _expect_finding(manifest: dict, needle: str) -> None:
    findings = validate_manifest(manifest)
    assert any(needle in f for f in findings), (needle, findings)


def test_an_unknown_top_level_field_is_refused():
    broken = _co()
    broken["surfaces"] = ["public_plus"]
    _expect_finding(broken, "unknown top-level field")


def test_an_unnamespaced_extension_is_refused():
    broken = _co()
    broken["extensions"]["intended_use"] = ["dd_preparation"]
    _expect_finding(broken, "not namespaced")


def test_an_undeclared_operator_is_refused():
    broken = _co()
    broken["attributes"]["sector"]["operators"] = ["fuzzy_match"]
    _expect_finding(broken, "neither a core operator")


def test_a_retrievable_identifying_attribute_is_refused():
    broken = _load("executive-succession-0.1.profile.json")
    broken["attributes"]["principal_identity"]["retrieval"] = True
    _expect_finding(broken, "MUST NOT be retrievable")


def test_identity_in_required_dimensions_is_refused():
    broken = _load("executive-succession-0.1.profile.json")
    broken["qualification"]["required_dimensions"].append("principal_identity")
    _expect_finding(broken, "cannot require identity")


def test_an_undeclared_required_dimension_is_refused():
    broken = _co()
    broken["qualification"]["required_dimensions"].append("vibes")
    _expect_finding(broken, "not a declared attribute")


def test_a_budget_scope_cannot_be_changed():
    broken = _co()
    broken["budget"]["scope"] = "per_session"
    _expect_finding(broken, "cannot change it")


def test_a_predicate_without_its_test_is_refused():
    broken = _co()
    broken["qualification"]["joint_predicates"][0].pop("semantics")
    _expect_finding(broken, "predicate's test must be stated")


def test_generality_is_required_where_it_decides_answers():
    broken = _co()
    broken["attributes"]["geography"].pop("general_value_means")
    _expect_finding(broken, "general_value_means is required")


# -- a manifest drives the core ---------------------------------------------

OPERATORS = {
    "equals": ClaimOperator.EQUALS,
    "intersects": ClaimOperator.INTERSECTS,
    "overlaps": ClaimOperator.OVERLAPS,
}

SAMPLE_VALUES = {
    "gidp.profile.co-investment": {
        "sector": ["ai_infrastructure", "enterprise_software"],
        "geography": ["europe"],
        "ticket_eur": {"min": 100000, "max": 500000},
        "lead_commitment_eur": {"min": 1000000, "max": 50000000},
        "stage": ["seed", "series_a"],
    },
    "gidp.profile.executive-succession": {
        "role": ["ceo"],
        "sector": ["b2b_software"],
        "company_arr_eur": {"min": 10000000, "max": 80000000},
        "location": ["paris", "london"],
        "timing": ["within_6_months", "exploratory"],
    },
}

PROBE_CLAIMS = {
    "gidp.profile.co-investment": [
        ("sector", "intersects", ["ai_infrastructure"]),
        ("geography", "intersects", ["france", "europe"]),
        ("ticket_eur", "overlaps", {"min": 200000, "max": 400000}),
        ("lead_commitment_eur", "overlaps", {"min": 1000000, "max": 5000000}),
    ],
    "gidp.profile.executive-succession": [
        ("role", "intersects", ["ceo"]),
        ("sector", "intersects", ["b2b_software", "fintech"]),
        ("company_arr_eur", "overlaps", {"min": 20000000, "max": 60000000}),
        ("location", "intersects", ["paris"]),
    ],
}


def _agent_from_manifest(name: str, manifest: dict) -> Agent:
    """Configure an Agent from the manifest alone.

    The manifest types meanings and marks retrievability; the Disclosure
    Policy remains the Principal's (FORMAT.md). The sample Principal here
    follows the obvious mapping: retrievable attributes at `discovery`,
    everything else left to the default class, `evaluation_only` -- which
    is why numeric ranges answer `conditionally_compatible` (coarsened,
    Section 15.5) while open descriptors answer `compatible`.
    """
    from gidp.objects import DisclosureClass
    from gidp.vocab import Surface

    profile_id = manifest["profile"]["id"]
    policy = {
        key: DisclosureClass(surface=Surface.DISCOVERY)
        for key, spec in manifest["attributes"].items()
        if spec.get("retrieval")
    }
    agent = Agent(
        ref=f"agent:{name}",
        standing_interest=_interest(
            interest=ConditionalInterest(
                action="consider",
                conditions=dict(SAMPLE_VALUES[profile_id]),
            ),
            disclosure_policy=DisclosurePolicy(attributes=policy),
        ),
    )
    return agent


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.stem)
def test_a_manifest_drives_a_session_through_the_same_core(path):
    """The same machinery, configured only by the manifest: required
    dimensions block qualification until each has been examined, then the
    session qualifies -- for both instances, with no profile-specific
    code anywhere in this test."""
    manifest = json.loads(path.read_text())
    profile_id = manifest["profile"]["id"]
    required = manifest["qualification"]["required_dimensions"]

    a = _agent_from_manifest("A", manifest)
    b = _agent_from_manifest("B", manifest)
    opened = a.open_session(f"s-{profile_id}", purpose=profile_id)
    a.confirm_accept(b.handle_session_open(opened))
    for agent in (a, b):
        agent.session.required_dimensions = set(required)

    claims = PROBE_CLAIMS[profile_id]
    assert {key for key, _, _ in claims} == set(required)

    for i, (key, operator, value) in enumerate(claims):
        spec = manifest["attributes"][key]
        assert operator in spec["operators"], (
            f"the probe uses only operators the manifest permits for {key}"
        )
        request = a.ask([Claim(key=key, operator=OPERATORS[operator], value=value)])
        response = b.handle_compatibility_request(request)
        a.receive_compatibility_response(response, request)
        last = i == len(claims) - 1
        assert (response.session_status is SessionStatus.POTENTIALLY_COMPATIBLE) is last, (
            f"{profile_id}: after {key}, qualification is "
            f"{'reached' if last else 'blocked -- a required dimension is unexamined'}"
        )
        assert a.session.qualify() is last

    opportunity = a.session.build_opportunity(
        structure=manifest["qualification"]["opportunity_meaning"][:40],
        expires_at=__import__("test_review_findings").__dict__["_soon"](),
        identity_status={},
    )
    assert opportunity.evaluated_dimensions == len(required)
