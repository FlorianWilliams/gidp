# Conditional Interest Discovery

**Version 0.1 — draft for review. Wire version token: `cidisc/0.1`.**

Most of what an economy would like to match never gets stated. A company that
would sell at the right price does not announce it. A candidate open to the
right role does not tell their employer. A fund that would follow a credible
lead does not publish the conditions. The interest is real, the conditions are
knowable, and stating them publicly costs more than the match is worth.

Conditional Interest Discovery is an open protocol for that class of interest.
It lets an agent, acting for a principal under an explicit and auditable
delegation, establish whether two parties are worth introducing — without
either side disclosing what it is protecting, and without a central operator
holding both sides' secrets.

The primitive is the **Conditional Interest**: *not necessarily seeking X, but
authorising the Agent to explore X if conditions C1…Cn hold, without revealing
protected information until disclosure conditions D1…Dn are satisfied.* The
protocol defines how such an interest is expressed, what may be exposed and to
whom, what two agents may ask each other, what they must answer truthfully,
and where the exchange stops and a human takes over.

CID is a discovery layer. It does not negotiate, does not settle, does not
custody anything, and does not commit a principal to anything. It hands a
qualified, consented Opportunity to a human or to a downstream protocol, and
stops there.

## What is here

| Path | What it is |
|---|---|
| [`spec/CID-0.1.md`](spec/CID-0.1.md) | The specification. Normative. |
| [`spec/explainer.md`](spec/explainer.md) | One page, for a first reader. |
| [`spec/use-cases.md`](spec/use-cases.md) | Eight cases the protocol is meant to serve. |
| [`spec/open-problems.md`](spec/open-problems.md) | Design rationale, the formal open problem, candidate directions. Non-normative. |
| [`spec/alternatives.md`](spec/alternatives.md) | Why not use a broker, a listing, a secure comparison or a set intersection? Measured, not argued. Non-normative. |
| [`spec/LIMITS.md`](spec/LIMITS.md) | Where this protocol should **not** be used. Non-normative. |
| [`spec/CHANGELOG.md`](spec/CHANGELOG.md) | Versioning policy and history. |
| [`impl/`](impl/) | Reference implementation in Python, with the four worked domains, the probing attack, the limit cases, and the JSON Schemas. |
| [`impl/SPEC-ISSUES.md`](impl/SPEC-ISSUES.md) | Every ambiguity the implementation found in the draft, and what changed because of it. |

Read the explainer first, then the specification. If you are looking for
reasons to reject the design, `spec/LIMITS.md`, `spec/alternatives.md` and
`spec/open-problems.md` are where the weaknesses are written down rather than
hidden — including the measurement showing that one of the specification's own
stated mitigations does not work, and the number saying how much a probing
counterparty can extract.

## Running the implementation

```sh
cd impl
python -m pip install -e .
python -m pytest            # the conformance and scenario suite
python examples/cross_border.py
python examples/probing.py  # what an adversarial querent can extract
python examples/limits.py   # the four cases chosen because they should break
python -m baselines.compare      # the same case through four existing mechanisms
python -m baselines.mitigations  # do the protocol's own defences work?
```

The implementation is the specification's test, not its authority: where the
two disagree, the specification is wrong until it is fixed, and the
disagreement is logged in `impl/SPEC-ISSUES.md`.

## Status and what would help

0.1 is a draft published for review, not a standard. The most useful review is
an attempt to break it: a market it claims to serve and does not, an inference
attack cheaper than the one in `examples/probing.py`, a reading of the
truthfulness rule that permits a lie, or a second implementation that disagrees
with this one.

The bounded-disclosure question in §24.3 of the specification is open: no
result is known that bounds what an *adaptive* querent learns from a truthful
compatibility oracle across a session. Candidate directions are in
`spec/open-problems.md`, including one that the limit cases have since
qualified.

## Licence

Documents under `spec/`, and this README: **CC BY 4.0** — see
[`LICENSE-DOCS.md`](LICENSE-DOCS.md).
Code under `impl/`: **Apache License 2.0** — see [`LICENSE`](LICENSE).

## Contact

{{AUTHOR}}, Independent. {{CONTACT}}.
Canonical location: {{CANONICAL_URL}}.
