# GIDP 0.1 — reference implementation

Reference implementation of the **Graduated Interest Disclosure Protocol**,
draft 0.1. The specification is in `../spec/GIDP-0.1.md`; the open problems and
design rationale are in `../spec/open-problems.md`.

This code exists to test the specification, not to ship a product.

## What it does

The bilateral core under the `core` profile: the object model of Section 14
with request/response correlation, the session state machine exactly as the
normative table of Section 17.2 gives it, the Disclosure Policy engine
(surface × gate, session depth, `evaluation_only` values that never leave the
Agent), the result vocabulary with the truthfulness rule of Section 15.5,
Discovery Projection derivation under the content rule, and an in-memory
Discovery Provider.

## What it deliberately does not do

Multi-party discovery, any transport binding, and **any cryptography at all**.
GIDP 0.1 requires none of these, and a toy version of any of them would
misrepresent what the protocol guarantees.

**This implementation provides no confidentiality** against a malicious peer
beyond what the policy layer withholds, and none at all against a malicious
operator of the process. What it demonstrates is that the protocol's
information flows are implementable and internally consistent.

## Verify it yourself

Nothing here asks to be taken on trust. The suite runs in seconds and the
mutation check in about a minute.

Python 3.11 or newer is required: the code uses `datetime.UTC`, which arrived
in 3.11, and a 3.10 interpreter does not even collect the tests.
`.python-version` pins 3.13, the oldest line still receiving bug fixes. On
macOS the signed installer from python.org is the shortest route that asks you
to trust nothing you cannot check; on Linux, your distribution's package.

```
cd impl
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Then, in order of what each one tells you:

```
pytest -q                          # 171 passed
ruff check .                       # All checks passed!
mypy gidp                          # Success
python tools/mutation_check.py     # 25 mutations, 25 killed
```

The mutation check is the one worth your minute. It breaks the implementation
in nineteen deliberate ways, each one corresponding to a normative clause, and
asserts that the suite notices. A test that passes for the wrong reason is
invisible to `pytest` and obvious here — which is how S-18 was caught, after
passing green for a week for an unrelated reason.

Until someone ran `pip install -e .` on a machine that was not the author's,
this package had never been built: the tests import the tree in place, so a
packaging fault stayed invisible. It is fixed, and the lesson generalises —
run the four commands above rather than believing this paragraph.

## Run the examples

```
python examples/cross_border.py           # Appendix C.1, with transcript
python examples/executive_succession.py   # Appendix C.2, a different domain
python examples/partnership.py            # Appendix C.3, dependency primitives
python examples/co_investment.py          # Appendix C.5, a contingent Opportunity
python examples/limits.py                 # four cases chosen because they break
python examples/probing.py                # the attack of Section 24.3, measured
python tools/emit_schema.py schema        # JSON Schema for every object
```

The suite is in four parts. `test_conformance.py` has one test per criterion of
Section 23.2, named after it, so a third party can run it against their own
implementation. `test_scenario.py` replays a whole session and asserts the
property the protocol exists for: **no Agent transmits its own
evaluation-only values** — a per-sender property, and the nuance is worth
reading. `test_horizontality.py` checks Appendix F.2 mechanically: the four
materially different domains must use the same objects, operators and results,
differing only in vocabulary and policy. Four is the threshold the
specification set for itself and it is now met — but all four were written by
the same hand, which is exactly how a shared blind spot survives. The test
that matters is a domain profile written by someone else. `test_limits.py` is
the other half: four cases chosen because they should *fail*, and they do —
see `../spec/LIMITS.md`. `baselines/` runs the same case through four existing
mechanisms and sweeps this implementation's answering policies against query
budgets, measuring leakage identically for each; it is what `../spec/alternatives.md`
rests on, and it is what found S-12, S-13 and S-14.

`baselines/sybil.py` measures what a query budget is worth against an
adversary that mints identities; `baselines/projection.py` measures the
Section 11.4 trade-off and finds it non-monotone;
`tests/test_properties.py` generates Standing Interests nobody designed and
checks the invariants against them, which is the closest a single
implementation can come to the real check — a second implementation written
by somebody else. `gidp/bindings/a2a.py` is the Section 22.2 binding written
against the published A2A 1.0 mechanism rather than from memory. `test_schema.py` validates every
object of both sessions against freshly generated schemas, so the schema
cannot drift from the code.

`examples/probing.py` implements the open problem the specification states:
an adversarial querent locating a private threshold it is never told. It ships
here on purpose. An implementer choosing a query budget deserves a measured
number, and a weakness the authors demonstrate themselves is one nobody has to
publish as a finding against the protocol.

## Issues found in the specification

`SPEC-ISSUES.md` logs every ambiguity met while writing this code, before it
was resolved here. That file is the point of the exercise.

## Licence

Apache-2.0.
