"""A closed vocabulary is an obligation on every implementer.

Each value is something an implementation must be able to receive and handle,
so a value nothing reaches is either a gap in the demonstration or a value
that should not be normative. This test does not forbid either — it forbids
the third case, where nobody decided.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from vocabulary_coverage import (  # noqa: E402
    KEPT_WITHOUT_A_DEMONSTRATION,
    coverage,
    undemonstrated,
    unreferenced,
)


def test_every_unreached_value_has_a_reason_written_down():
    undocumented = [
        key for key in unreferenced() if key not in KEPT_WITHOUT_A_DEMONSTRATION
    ]
    assert not undocumented, (
        "these closed-vocabulary values are reached by nothing and nobody said "
        f"why they stay: {undocumented}. Remove them, exercise them, or add a "
        "line to KEPT_WITHOUT_A_DEMONSTRATION."
    )


def test_the_register_does_not_outlive_what_it_registers():
    """A reason for a value that is now exercised is stale documentation."""
    reached = {key for key, where in coverage().items() if where}
    stale = sorted(reached & set(KEPT_WITHOUT_A_DEMONSTRATION))
    assert not stale, f"registered as undemonstrated but now reached: {stale}"


def test_the_undemonstrated_surface_does_not_grow_silently():
    """A ratchet, not a target. If this number rises, something was added to a
    closed vocabulary without a domain that needs it."""
    # 38 -> 41 on 25 September 2026: three values reached by nothing
    # (unreferenced 11 -> 8) became reached by the review-finding tests.
    # They moved up one level; none moved down.
    assert len(undemonstrated()) <= 41
    assert len(unreferenced()) <= 8
