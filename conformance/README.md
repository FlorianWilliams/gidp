# GIDP Conformance Corpus (0.2 draft)

This directory is the conformance corpus the reviewers of 0.1 asked for: a
set of scenarios an implementation can be tested against **without importing
the reference implementation's classes**. Each scenario is a JSON file
stating an initial state, a sequence of stimuli, and what a conforming
implementation must and must not do in response. The reference
implementation runs the whole corpus in its own test suite
(`impl/tests/test_corpus.py`); an independent implementation passes the
corpus by writing its own interpreter for the small grammar below.

The corpus tests observable behaviour — messages, statuses, refusals,
state — not internal representation. A scenario never asks how a Standing
Interest is stored, only what crosses the wire and what an Agent refuses to
do. Where the specification leaves a choice to a binding (delivery,
deduplication, timeouts), the corpus does not test it.

## Scenario grammar

Every scenario file has four parts.

**`setup`** declares the two parties in implementation-neutral terms. Each
role (`A` opens the session; `B` responds) gives: `conditions` (attribute →
private value), `policy` (attribute → class, written `surface`,
`surface/gate`, `evaluation_only` or `never`; an attribute absent from
`policy` has the default class, `evaluation_only`), `authority` (level →
`true` / `false` / `approval_required`; unset levels are `false`),
and optionally `conditional_on` (declared dependencies),
`required_dimensions` (the profile's minimum qualification coverage),
`pre_approved` (attributes the Principal has approved in advance).

**`steps`** is the ordered exchange. Each step is one of:

| Step | Meaning |
|---|---|
| `{"open": {"purpose", "max_depth"?}}` | A opens, B accepts. |
| `{"ask": {"from", "claims": [...]}, "expect_results": [{claim_id, result}], "expect_status"?, "forbid_substrings"?}` | A claims batch; the other side answers. `expect_results` matches each named claim's result; `expect_status` matches the reported `session_status`; `forbid_substrings` must not appear anywhere in the serialised response. |
| `{"request_disclosure": {"from", "attribute", "purpose"}, "expect_disclosure"?, "forbid_substrings"?}` | `expect_disclosure` is the response status (`granted`, `declined`, `pending_principal_approval`, ...). |
| `{"request_consent": {"from", "action", "scope"}, "expect_consent"?, "expect_error"?}` | `expect_error: true` means the *sender's own implementation* must refuse to send (e.g. consent to `reveal_identity` before qualification). |
| `{"principal_answers": {"role", "granted"}}` | The named role's Principal answers the outstanding consent. |
| `{"qualify": {"role", "expect"}}` | The role attempts the qualification transition; `expect` is whether it fires. |
| `{"state": {"role", "expect"}}` / `{"status": {"role", "expect"}}` | Assert the session state / the locally computed `session_status`. |
| `{"opportunity": {"role", "expect_contingent_on"?, "forbid_substrings"?}}` | The role builds its Opportunity; assertions apply to the serialised object. |
| `{"handoff": {"from", "target", "expect_error"?}}` | `expect_error: true` means the implementation must refuse to emit. |

Matching is **partial**: fields a step does not name are unconstrained.
`forbid_substrings` is the negative space — the corpus's way of saying a
private value must leave no trace, whatever the object's other content.

**`notes`** ties the scenario to the sections of `spec/GIDP-0.1.md` it
exercises.

**`spec`** lists those section numbers, so a failure points somewhere.

## What passing means

Passing the corpus means the implementation makes the same *decisions* the
specification requires on these paths. It does not certify privacy (Section
24 is explicit about what cannot be certified), does not cover binding
duties (delivery, replay, timeouts), and does not replace the deployment
threat model required by Section 23.2. An implementation that passes has
not finished; one that fails has a precise place to look.

## Status

Draft for GIDP 0.2. The scenarios encode 0.1 behaviour as corrected through
S-64 (`impl/SPEC-ISSUES.md`); they are expected to survive 0.2's structural
work unchanged, because they assert decisions, not state names.
