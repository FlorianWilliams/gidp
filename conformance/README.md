# GIDP Conformance Corpus (0.2 draft)

This directory is the conformance corpus requested in review of 0.1: a
set of scenarios an implementation can be tested against **without importing
the reference implementation's classes**. Each scenario is a JSON file
stating an initial state, a sequence of stimuli, and what a conforming
implementation must and must not do in response. The reference
implementation runs the whole corpus in its own test suite
(`impl/tests/test_corpus.py`); an independent implementation passes the
corpus by writing its own interpreter for the small grammar below.

The corpus tests observable behaviour (messages, statuses, refusals,
state), not internal representation. A scenario never asks how a Standing
Interest is stored, only what crosses the wire and what an Agent refuses to
do. Where the specification leaves a choice to a binding (delivery,
deduplication, timeouts), the corpus does not test it.

## Scenario grammar

Every scenario file has four parts.

**`setup`** declares the two parties in implementation-neutral terms. Each
role (`A` opens the session; `B` responds) gives: `conditions` (attribute →
private value), `policy` (attribute → class, written `surface`,
`surface/gate`, `evaluation_only` or `never`; an attribute absent from
`policy` has the default class, `evaluation_only`, Section 9.1),
`authority` (level → JSON `true` / `false`, or the string
`approval_required`), and optionally `conditional_on` (declared
dependencies) with `conditional_on_policy` (their class),
`required_dimensions` (the profile's minimum qualification coverage),
`pre_approved` (attributes the Principal has approved in advance).

Unset authority levels are `false`. This is a convention of the
corpus, not a default of the specification (Section 16 states none), and
it is the closed reading: an absence never becomes a delegation. Scenarios
state every level their outcome depends on.

**`steps`** is the ordered exchange. Each step is one of:

| Step | Meaning |
|---|---|
| `{"open": {"purpose", "max_depth"?}}` | A opens, B accepts. |
| `{"ask": {"from", "claims": [...], "hold"?}, "expect_results"?, "expect_status"?, "forbid_substrings"?, "expect_error"?}` | The named side sends a claims batch; the other side answers. `expect_results` matches each named claim's result; `expect_status` matches the reported `session_status`; `forbid_substrings` must not appear anywhere in the serialised response. `hold: true`: the receiver holds the request for a PROBE approval and produces no response. `expect_error: true`: the sender's own implementation must refuse to emit (a claim carrying its own private value, Section 14.3). |
| `{"expire_ask": {}}` | The most recently held ask's `expires_at` passes with no terminal response. |
| `{"request_disclosure": {"from", "attribute", "purpose", "hold"?, "undelivered"?}, "expect_disclosure"?, "forbid_substrings"?}` | `expect_disclosure` is the response status (`granted`, `declined`, `pending_principal_approval`, ...). `hold`: no response yet; `undelivered`: the request has left the sender and not reached the receiver. |
| `{"release_disclosure": {}, "expect_disclosure"?}` | The held disclosure request is now answered. |
| `{"request_consent": {"from", "action", "scope"}, "expect_consent"?, "expect_error"?}` | `expect_error: true` means the *sender's own implementation* must refuse to send (e.g. consent to `reveal_identity` before qualification). |
| `{"principal_answers": {"role", "granted"}}` | The named role's Principal answers the outstanding consent. |
| `{"set_authority": {"role", "level", "value"}}` | The named role's Principal changes a delegation mid-session. Local: nothing is transmitted. |
| `{"qualify": {"role", "expect"}}` | The role's qualification conditions are re-evaluated; `expect` is whether the role is **QUALIFIED after this step**. An implementation that re-evaluates on its own after every event (Section 17.2) may treat the step as a no-op: the assertion is on the state, not on who triggered it. |
| `{"opportunities": {"role", "expect"}}` | The number of Opportunities the role has emitted in the session so far; this is the observable form of "qualification is reached at most once". |
| `{"state": {"role", "expect"}}` / `{"status": {"role", "expect"}}` | Assert the session state / the locally computed `session_status`. `expect` may be a list: any listed value conforms (used where the specification permits more than one outcome). |
| `{"opportunity": {"role", "expect_contingent_on"?, "forbid_substrings"?}}` | The role builds its Opportunity; assertions apply to the serialised object. |
| `{"handoff": {"from", "target", "expect_error"?, "expect_recipient_error"?}}` | `target` is the Section 14.7 object (`{"kind": "protocol", "protocol_ref": …}`); a handoff consent's scope names its `protocol_ref`. `expect_error: true`: the implementation must refuse to emit. `expect_recipient_error: true`: the recipient must refuse it. |

Matching is **partial**: fields a step does not name are unconstrained.
`forbid_substrings` is how the corpus states that a private value must
leave no trace, whatever the object's other content.

**`notes`** ties the scenario to the sections of `spec/GIDP-0.1.md` (or of the 0.2
session-model draft) it exercises.

**`spec`** lists those section numbers, so a failure points somewhere.

## What passing means

Passing the corpus means the implementation makes the same *decisions* the
specification requires on these paths. It does not certify privacy (Section
24 is explicit about what cannot be certified), does not cover binding
duties (delivery, replay, timeouts), and does not replace the deployment
threat model required by Section 23.2. An implementation that passes is
not thereby finished, and one that fails has a precise place to look.

## Status

Draft for GIDP 0.2. The scenarios encode 0.1 behaviour as corrected through
S-64 (`impl/SPEC-ISSUES.md`); they are expected to survive 0.2's structural
work unchanged, because they assert decisions, not state names. Scenarios
14 and 15 test the 0.2 draft's semantics (`spec/drafts/session-model-0.2.md`),
not 0.1.

The first independent implementation (October 2026, E-01 to E-12 in
`impl/SPEC-ISSUES.md`) found six defects in this corpus, all repaired:
string-encoded booleans, Handoff targets written as bare strings, a
`reveal_identity` consent sought over a non-identity attribute, a
post-Handoff state the specification does not impose, an authority
default attributed to the specification, and an undefined `qualify`
step. It also found two defects of the reference implementation, now
scenarios 16 and 17.

## The blind variant

`scenarios-blind/` holds the 0.1 scenarios with every expectation removed
and neutral names, for an implementer who must not see the outcomes. It
is generated, never edited: `python impl/tools/make_blind.py`. The mapping
from blind names to scenarios lives in `blind-map.json`, outside the blind
directory, and is not handed to the implementer.
