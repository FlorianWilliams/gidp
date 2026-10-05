"""The reference implementation runs the conformance corpus it publishes.

Each scenario in `conformance/scenarios/` is implementation-independent
JSON; `corpus_runner` is this implementation's interpreter for it. An
independent implementation writes its own interpreter and runs the same
files; that run, and not this suite, is the test the corpus exists for. This
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


def test_the_blind_corpus_is_current_and_leaks_nothing():
    """`scenarios-blind/` is generated from the corpus (tools/make_blind.py):
    a scenario edited without regenerating would hand an implementer stale
    stimuli, and an expectation surviving the blinding would hand it the
    answer."""
    import json

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from make_blind import MAP, SOURCE, TARGET, blind

    mapping = json.loads(MAP.read_text())["map"]
    for name, source in mapping.items():
        expected = blind(json.loads((SOURCE / f"{source}.json").read_text()), name)
        committed = json.loads((TARGET / f"{name}.json").read_text())
        assert committed == expected, f"{name} is stale: run tools/make_blind.py"
        text = json.dumps(committed)
        assert "expect" not in text and "forbid" not in text and source not in text
