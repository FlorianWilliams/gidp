"""The reference implementation runs the conformance corpus it publishes.

Each scenario in `conformance/scenarios/` is implementation-independent
JSON; `corpus_runner` is this implementation's interpreter for it. An
independent implementation writes its own interpreter and runs the same
files -- that, not this suite, is the test the corpus exists for. This
test guarantees the weaker, necessary property: the corpus and the
reference implementation agree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from corpus_runner import run_scenario, scenarios  # noqa: E402


@pytest.mark.parametrize("path", scenarios(), ids=lambda p: p.stem)
def test_corpus_scenario(path):
    run_scenario(path)


def test_the_corpus_is_not_empty():
    assert len(scenarios()) >= 12
