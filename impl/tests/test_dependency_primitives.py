"""Section 19.1 used bilaterally, and the feature that gates it (14.1)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from cid.agent import Agent  # noqa: E402
from cid.evaluation import DEPENDENCY_KEYS, evaluate_claim  # noqa: E402
from cid.objects import Claim  # noqa: E402
from cid.vocab import ClaimOperator, ClaimResult, Feature  # noqa: E402

import partnership  # noqa: E402


def test_a_claim_may_name_a_dependency_primitive():
    """Section 19.1: `requires: X` on one side meets `provides: X` on the other."""
    claim = Claim(key="provides", operator=ClaimOperator.INTERSECTS,
                  value=["customs_clearance_eu_uk"])
    evaluation = evaluate_claim(partnership.brokerage, claim)
    assert evaluation.truth is True
    assert evaluation.evaluation_only is False  # provides is session-surface


def test_requires_is_answered_but_coarsened():
    """The asymmetry: what you need is the mirror of what you lack."""
    claim = Claim(key="requires", operator=ClaimOperator.INTERSECTS,
                  value=["last_mile_germany"])
    evaluation = evaluate_claim(partnership.brokerage, claim)
    assert evaluation.truth is True
    assert evaluation.evaluation_only is True


def test_all_four_primitives_are_reserved_claim_keys():
    assert set(DEPENDENCY_KEYS) == {
        "provides", "requires", "conditional_on", "excludes"
    }
    for key in DEPENDENCY_KEYS:
        claim = Claim(key=key, operator=ClaimOperator.INTERSECTS, value=["x"])
        # Resolvable without raising, whether or not the list is populated.
        evaluate_claim(partnership.logistics, claim)


def test_an_empty_list_answers_unknown_not_absent():
    """Silence must not reveal absence (the reasoning of Section 14.4)."""
    claim = Claim(key="conditional_on", operator=ClaimOperator.INTERSECTS,
                  value=["anything"])
    evaluation = evaluate_claim(partnership.logistics, claim)
    assert evaluation.truth is None


def test_features_in_force_are_the_intersection_not_an_echo():
    """Section 14.1: SessionAccept carries the features actually supported."""
    a = Agent(ref="a", standing_interest=partnership.logistics)
    b = Agent(ref="b", standing_interest=partnership.brokerage,
              supported_features=set())  # implements the core only
    opened = a.open_session("s-f", purpose="test",
                            features=[Feature.DEPENDENCY_PRIMITIVES])
    accept = b.handle_session_open(opened)
    assert accept.features == []
    a.confirm_accept(accept)
    assert a.session.features == set()


def test_the_partnership_session_qualifies_and_hides_both_gaps():
    a, b, wire = partnership.run(verbose=False)
    opportunity = next(m for _, m in wire.transcript if m.type == "Opportunity")
    assert opportunity.compatible_dimensions == 4
    assert opportunity.open_conditions == ["requires"]

    import json
    on_the_wire = json.dumps(
        [m.model_dump(mode="json") for _, m in wire.transcript]
    )
    assert "capability_gap" not in on_the_wire
    assert "margin_floor" not in on_the_wire
