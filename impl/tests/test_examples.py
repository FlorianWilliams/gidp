"""Every example runs, end to end, including the part that prints.

The suite exercised each example's `run()` and never its `main()`. A blind
rename broke `co_investment.main()` and 109 tests passed, which is the exact
shape of a gap worth closing: the examples are the specification's worked
appendices, a reader will run them, and a reader is the only thing that was
checking them.
"""

from __future__ import annotations

import importlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES.parent))
sys.path.insert(0, str(EXAMPLES))

NAMES = sorted(p.stem for p in EXAMPLES.glob("*.py") if not p.stem.startswith("_"))


def test_the_example_list_is_not_empty():
    assert len(NAMES) >= 6, f"only found {NAMES}; the parametrisation is vacuous"


@pytest.mark.parametrize("name", NAMES)
def test_every_example_runs_and_prints_something(name):
    module = importlib.import_module(name)
    assert hasattr(module, "main"), f"{name} has no main()"
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        module.main()
    output = buffer.getvalue()
    assert len(output.splitlines()) > 10, (
        f"{name}.main() printed {len(output.splitlines())} lines; it is meant "
        "to be read"
    )
