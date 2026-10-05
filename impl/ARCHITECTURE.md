# Architecture of the reference implementation

This describes the code, not the protocol. Where the two disagree the
specification wins and the disagreement is a bug logged in `SPEC-ISSUES.md`.

It exists for three readers: someone deciding whether to write a second
implementation, someone deciding which parts to replace for a deployment, and
someone reviewing whether the structure matches what the specification says.

## What this code is

A library, not a service. It has no network, no storage, no scheduler, no user
interface and no identity system. None of those is an oversight; each is a
decision recorded below. What it does have is the whole of the bilateral core
of GIDP 0.1: the objects, the vocabularies, the disclosure engine, the
compatibility semantics, the state machine, and an Agent that puts them
together.

Two Agents in the same process can run a complete discovery, from publishing a
projection to handing a qualified Opportunity to a human. That is the unit the
specification defines, and the unit this code implements.

## Module map

Dependencies point downward only. Nothing below imports from anything above
it, which is what makes the lower layers testable without the upper ones and
replaceable without touching them.

```text
  examples/              four worked domains, a probing attack, four limit cases
  baselines/             measurement harnesses (not part of the protocol)
         │
  gidp/agent.py          the protocol as a usable object: sessions, claims,
         │               disclosures, consents, handoff, the audit trail
         │
  gidp/session.py        the state machine of Section 17.2, the qualification
         │               rule of 15.2, the Opportunity of 14.6
         │
  gidp/policy.py         the disclosure engine (surface x gate x depth) and
  gidp/evaluation.py     the claim evaluator and the truthfulness rule 15.5
  gidp/auditing.py       what a responder declines to be asked (Section 24.3):
         │               the granularity lattice and the bit budget
         │
  gidp/objects.py        every transmitted object, as validated models
         │
  gidp/vocab.py          the closed vocabularies and the wire version token

  gidp/transport.py      a checking wire: correlation rules of Section 14
  gidp/provider.py       an in-memory Discovery Provider (Section 12)
  gidp/bindings/a2a.py   declaration, activation and carriage over A2A
```

`transport.py` and `provider.py` sit beside the stack rather than in it: an
Agent never calls them, which is how a deployment substitutes a real wire and
a real index without the core noticing.

## The flow, mapped to code

The eight stages of Section 13, in the order a session runs them.

| Stage | Code |
|---|---|
| Express a Standing Interest | `objects.StandingInterest` (held, never sent) |
| Derive and publish a projection | `policy.derive_projection` → `provider.publish_projection` |
| Retrieve candidates | `provider.query_candidates` |
| Open a session | `agent.open_session` / `handle_session_open` / `confirm_accept` |
| Probe compatibility | `agent.ask` / `handle_compatibility_request` → `evaluation.evaluate_claim` + `choose_result` |
| Disclose under policy | `agent.request_disclosure` / `handle_disclosure_request` → `policy.evaluate_disclosure` |
| Obtain consent | `agent.request_consent` / `handle_consent_request` / `principal_answers_consent` |
| Qualify and hand off | `session.qualify` → `session.build_opportunity` → `agent.handoff` |

Two separations carry most of the design. `evaluation` computes the *truth*
and `choose_result` decides what to *say*, which is what makes the
truthfulness rule checkable: `assert_truthful`
compares the two. And `policy` decides disclosure from the Standing Interest,
the session depth and the consents, and consults nothing else, which is what
makes a disclosure decision reproducible.

## What a deployment must supply

Five components are absent by design. A demonstration needs the first three; a
product needs all five.

**A transport.** `transport.Wire` enforces Section 14's correlation rules
in-process and carries nothing anywhere. `bindings/a2a.py` maps every object
to and from an A2A message and handles the extension handshake, but nothing
here opens a socket. Supplying this is the smallest of the five.

**Persistence.** Standing Interests, sessions and audit entries live in
memory. Section 25.3 expects an audit trail a Principal can inspect, and
Section 17.1 expects a revoked Standing Interest to stop being discoverable,
neither of which survives a restart here.

**A real Discovery Provider.** `InMemoryProvider` matches retrieval attributes
by exact token equality, which Section 12.4 now recommends against: resolving
one hierarchy raised recall from 26% to 100% in the measurement under
`baselines/projection.py`. A deployment supplies indexing, vocabulary
resolution, abuse controls and a published withdrawal latency.

**Identity and authority evidence.** `AuthoritySpec.evidence_ref` is a string
this code never resolves. Section 16.2 requires authority to be evidenced and
Section 20 says which systems supply it is out of scope; GNAP is the published
candidate. Without this an Agent's claim to represent a Principal is taken on
faith.

**A human surface.** `principal_answers_consent` and
`principal_answers_disclosure` are where a person's decision enters. Something
must ask them, and something must show them what an Opportunity contains
before they act on it.

## Deliberately absent

Multi-party discovery (Section 19.2) is experimental in the specification and
is not implemented: implementing an experimental section here would misrepresent
its status.
There is no cryptography, for the reasons in
`../spec/open-problems.md`. There is no negotiation: Section 16.1 puts even
non-binding proposals after the Handoff, and this code stops at the Handoff.

## The harnesses

`baselines/` is not part of the protocol and a second implementation need not
have it. It measures: `compare.py` runs the same case through four existing
mechanisms and GIDP on one yardstick, `mitigations.py` sweeps answering
policies against query budgets, `sybil.py` measures what a budget is worth
against many identities, `projection.py` measures the Section 11.4 trade-off.
`measure.py` holds the yardstick: leakage as the reduction of an observer's
hypothesis space, computed by enumeration, with an invariant that refuses to
run if an observation rules out the truth.

`tools/` holds three: `emit_schema.py` generates the JSON Schemas from the
models, `vocabulary_coverage.py` reports which closed-vocabulary values nothing
reaches, and `mutation_check.py` breaks the guarantees it lists one at a time
and reports any the tests fail to notice.

## How to extend it

Three points are meant to be replaced, and nothing else is.

A **profile** (Section 21) adds attribute vocabularies and claim keys. Nothing
in the core enumerates attribute names, so a profile is data rather than code.

A **provider** implements the five operations of Section 12.2. `InMemoryProvider`
is the smallest thing that satisfies them; the interface is the class's public
methods.

An **answering policy** decides what to say given the truth.
`agent.Agent._answer` holds the default, and `baselines/mitigations.py` shows
four alternatives and what each costs. A deployment that wants a different one
replaces that method and should check it against `simulatability_report()`
first: a policy whose decision consults the private value carries that value,
whatever it then says.
