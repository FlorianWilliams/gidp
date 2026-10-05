"""The profile manifest format, its validator, and the contrasted pair.

The pair is the purpose (FORMAT.md): one narrow and numeric
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
from gidp.profile import apply_qualification  # noqa: E402
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
    """One narrow and numeric, one relational and asymmetric: the claim is
    that the same format carries both."""
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
        "equity_pct": {"min": 2, "max": 8},
    },
}

PROBE_CLAIMS = {
    "gidp.profile.co-investment": [
        ("sector", "intersects", ["ai_infrastructure"]),
        ("geography", "intersects", ["france", "europe"]),
        ("ticket_eur", "overlaps", {"min": 200000, "max": 400000}),
        ("lead_commitment_eur", "overlaps", {"min": 1000000, "max": 5000000}),
        ("stage", "intersects", ["seed"]),
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


PREDICATE_CANDIDATES = {
    "gidp.profile.co-investment": 300000,
    "gidp.profile.executive-succession": 5,
}


def _exchange(asker: Agent, answerer: Agent, claim: Claim):
    request = asker.ask([claim])
    response = answerer.handle_compatibility_request(request)
    asker.receive_compatibility_response(response, request)
    return response


def _manifest_session(manifest: dict) -> tuple[Agent, Agent]:
    a = _agent_from_manifest("A", manifest)
    b = _agent_from_manifest("B", manifest)
    profile_id = manifest["profile"]["id"]
    a.confirm_accept(b.handle_session_open(a.open_session(f"s-{profile_id}", purpose=profile_id)))
    for agent in (a, b):
        apply_qualification(agent.session, manifest)
    return a, b


def _predicate_claim(manifest: dict) -> Claim:
    wire = manifest["qualification"]["joint_predicates"][0]["wire"]
    return Claim(
        key=wire["key"],
        operator=ClaimOperator(wire["operator"]),
        value=PREDICATE_CANDIDATES[manifest["profile"]["id"]],
    )


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.stem)
def test_a_manifest_drives_a_session_through_the_same_core(path):
    """The same machinery, configured only by the manifest: required
    dimensions block qualification until each has been examined, the joint
    predicate blocks it until both directions have accepted one candidate,
    then the session qualifies, for both instances, with no
    profile-specific code anywhere in this test or in the core."""
    manifest = json.loads(path.read_text())
    profile_id = manifest["profile"]["id"]
    required = manifest["qualification"]["required_dimensions"]
    a, b = _manifest_session(manifest)

    claims = PROBE_CLAIMS[profile_id]
    assert {key for key, _, _ in claims} == set(required)

    for key, operator, value in claims:
        assert operator in manifest["attributes"][key]["operators"], (
            f"the probe uses only operators the manifest permits for {key}"
        )
        response = _exchange(a, b, Claim(key=key, operator=OPERATORS[operator], value=value))
        assert response.session_status is SessionStatus.OPEN, (
            f"{profile_id}: after {key}, qualification is blocked -- a required "
            "dimension is unexamined, or the joint predicate does not hold yet"
        )
        assert a.session.qualify() is False

    # The joint predicate, in its wire form: B tests the candidate against
    # A's private value, then A against B's; only the second answer can
    # carry B's positive status, since 0.1 has no status-refresh message.
    predicate = _predicate_claim(manifest)
    response = _exchange(b, a, predicate)
    assert [o.result.value for o in response.results] == ["compatible"]
    # One direction proves nothing, in either view: A's (which also lacks
    # B's positive report) and B's own, which has everything else.
    assert a.session.qualify() is False
    assert b.session.status() is SessionStatus.OPEN, "one direction proves nothing"
    response = _exchange(a, b, predicate)
    assert [o.result.value for o in response.results] == ["compatible"]
    assert response.session_status is SessionStatus.POTENTIALLY_COMPATIBLE
    assert b.session.qualify() is True
    assert a.session.qualify() is True

    opportunity = a.session.build_opportunity(
        structure=manifest["qualification"]["opportunity_meaning"][:40],
        expires_at=__import__("test_review_findings").__dict__["_soon"](),
        identity_status={},
    )
    assert opportunity.evaluated_dimensions == len(set(required) | {predicate.key})


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.stem)
def test_a_candidate_one_side_refuses_does_not_satisfy_the_predicate(path):
    """The trap the predicate exists for: each private range overlaps an
    asked band, yet no single amount suits both. A candidate outside one
    side's range is answered incompatible and does not qualify."""
    manifest = json.loads(path.read_text())
    profile_id = manifest["profile"]["id"]
    a, b = _manifest_session(manifest)
    for key, operator, value in PROBE_CLAIMS[profile_id]:
        _exchange(a, b, Claim(key=key, operator=OPERATORS[operator], value=value))
    wire = manifest["qualification"]["joint_predicates"][0]["wire"]
    outside = SAMPLE_VALUES[profile_id][wire["key"]]["max"] + manifest["budget"][
        "granularity"
    ][wire["key"]]["min_bucket_width"]
    response = _exchange(b, a, Claim(key=wire["key"],
                                     operator=ClaimOperator(wire["operator"]),
                                     value=outside))
    assert [o.result.value for o in response.results] == ["incompatible"]
    assert a.session.qualify() is False


def test_a_predicate_without_its_wire_form_is_refused():
    broken = _co()
    broken["qualification"]["joint_predicates"][0].pop("wire")
    _expect_finding(broken, "predicate's test must be stated")


def test_a_wire_form_must_use_the_predicate_attribute_and_its_operator():
    broken = _co()
    broken["qualification"]["joint_predicates"][0]["wire"]["key"] = "sector"
    _expect_finding(broken, "not among the attributes")
    broken = _co()
    broken["qualification"]["joint_predicates"][0]["wire"]["operator"] = "equals"
    _expect_finding(broken, "is not an operator of")


def test_a_bit_budget_needs_a_finite_domain():
    broken = _co()
    broken["budget"].pop("domain")
    _expect_finding(broken, "no posterior can be computed")


def test_a_domain_must_fall_on_the_lattice():
    broken = _co()
    broken["budget"]["domain"]["ticket_eur"]["min"] = 10000
    _expect_finding(broken, "must fall on the lattice")


def test_a_budget_larger_than_its_domain_never_binds():
    broken = _co()
    broken["budget"]["bits_per_attribute"]["ticket_eur"] = 12
    _expect_finding(broken, "would never bind")
