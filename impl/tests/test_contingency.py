"""Section 14.6: an Opportunity must show what it depends on.

The fourth domain found that a bilateral session can qualify while the whole
interest hangs on a third party who is not in the session, and that the
Opportunity carried no trace of it. See SPEC-ISSUES.md S-11.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

import co_investment  # noqa: E402
from test_scenario import _run as run_cross_border  # noqa: E402


def test_an_interdependent_interest_produces_a_contingent_opportunity():
    _, _, wire = co_investment.run(verbose=False)
    opportunity = next(m for _, m in wire.transcript if m.type == "Opportunity")
    assert opportunity.contingent_on == ["qualified_lead_committed"], (
        "the Opportunity must say what it depends on, or it reads as an "
        "assembled round (Section 14.6)"
    )


def test_both_sides_learn_the_dependency():
    """The follower holds it; the company learns it from the answer."""
    company, follower, _ = co_investment.run(verbose=False)
    assert "qualified_lead_committed" in follower.session.unresolved_dependencies
    assert "qualified_lead_committed" in company.session.unresolved_dependencies


def test_a_session_without_dependencies_is_not_contingent():
    _, _, wire = run_cross_border()
    opportunity = next(m for _, m in wire.transcript if m.type == "Opportunity")
    assert opportunity.contingent_on == []


def test_the_counts_identity_still_holds():
    """Adding contingency must not disturb Section 14.6's arithmetic."""
    _, _, wire = co_investment.run(verbose=False)
    opportunity = next(m for _, m in wire.transcript if m.type == "Opportunity")
    assert (
        opportunity.compatible_dimensions + len(opportunity.open_conditions)
        == opportunity.evaluated_dimensions
    )
