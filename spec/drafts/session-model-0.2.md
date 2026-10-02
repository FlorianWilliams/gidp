# The session model in three axes (0.2 draft, revision 2)

Status: draft for GIDP 0.2. The 0.1 state machine (specification, Section
17.2) remains normative until 0.2 is published; this document is the
redesign every review of 0.1 converged on, revised after two independent
reviews of its first version. The reference implementation runs on this
model with the 0.1 states kept as a derived view: the suite and the
conformance corpus pass unchanged, with the same refusal texts. That
property is this draft's **non-regression evidence** — it validates the
refactoring, not yet any new 0.2 semantics, and the distinction is the
reviews' own framing.

## The diagnosis

0.1 encoded three different things in one state. `DISCLOSURE_PENDING` was
simultaneously *where the session is* and *what is in flight*;
`CONSENTED` was a phase that actually recorded a fact about consents; and
the rules that made it work were patches with their own defect numbers:
the return-to-stage bookkeeping (S-22), the deferred qualification
recomputed at the return (S-34, S-47), the narrowed `open`-while-pending
rule (S-50), the grant-before-qualification exception. Each patch was
correct; their number was the finding.

## The model

A session, per side, is three axes. **The unit of each axis is stated
exactly, because the reviews showed "per side and per direction" admits
two readings:**

**Phase** — one per side per session, never duplicated by direction. The
monotonic life:

```text
REQUESTED → EXPLORING → QUALIFIED → HANDED_OFF
     └──────────┴───────────┴──────────┴────→ CLOSED
```

Four transitions move it: `SessionAccept`, the qualification transition
(at most once), `Handoff` (with its granted consent, Section 14.7), and
closing. Nothing else does; in particular, a disclosure or a consent
request never moves it.

**Pending** — keyed **per direction**: one slot for the request this side
*sent*, one for the request it *received*, each empty or holding one
disclosure or one consent. The directions are independent, which Section
17.2 already required ("per direction of request") and the one-slot
reading of revision 1 broke: an Agent whose own consent awaits the peer
Principal's decision can still receive, and answer, a disclosure the peer
asks meanwhile. Within one direction, at most one request is in flight at
a time — 0.1's concurrency rule, explicit and kept.

A terminal response clears **the matching pending request**, identified
by direction and `request_ref`, and correlation is checked before
clearing: a delayed duplicate of an earlier response names a request
already discharged, is refused, and must not clear the wait a newer
request opened. A provisional response leaves the request in flight. An
expired or post-close response produces no effect on any axis.

**Evaluation and consents** — standing propositions and their results,
**the requests this side has sent that have no answer yet** (an
unanswered claim — held for a PROBE approval, say, Section 16.3 — is an
unresolved proposition and blocks qualification; its expiry discharges
the request without ever becoming a result), the peer's last reported
`session_status`, the profile's required dimensions, dependencies, and
the granted consents. Consents are held by the Agent, outside the
session object, under an explicit ownership contract: a grant is indexed
by **session, granting side, action and scope** — two sessions sharing an
action/scope pair share nothing — and carries one metadatum the
projection needs, *whether the phase was QUALIFIED when the grant was
recorded*. That historical fact is distinct from the grant's effective
authorisation: revoking the authorisation (no wire message does, in 0.1
or here; a Principal withdraws it locally) does not erase the fact, and
every act of use re-runs the decision order of Section 16.3 regardless.
The convention for the metadatum is fixed: the phase is read **before the
grant is processed**, so a pre-qualification grant that unblocks a
deferred qualification never becomes retrospectively post-qualification.

## Admission versus effect

The table below describes the **effects of admitted events on each
axis**. It does not replace the admission guards: the refusals of Section
17.2 — an event in a phase that does not admit it, a second request in an
occupied direction, anything after `CLOSED` — apply before any row is
read. A combination such as a pending request in a closed session is
unreachable because closing clears the pending axis and `CLOSED` admits
nothing that would reopen it.

| Event | Phase | Pending | Evaluation / consents |
|---|---|---|---|
| `SessionOpen` / `SessionAccept` | advances | — | — |
| `CompatibilityRequest` sent | — | — | records an unanswered question (blocks qualification) |
| `CompatibilityResponse` received | — | — | resolves it; records propositions, peer status, contingencies |
| `DisclosureRequest` | — | opens its direction's slot (refused if occupied) | — |
| `DisclosureResponse` terminal | — | clears the matching slot (correlation checked first) | gate bookkeeping |
| `DisclosureResponse` provisional | — | stays | — |
| `ConsentRequest` | — | opens its direction's slot (action rules of 14.5 apply) | — |
| `ConsentResponse` granted | — | clears matching | records the grant, with the phase-at-grant metadatum |
| `ConsentResponse` declined / provisional | — | clears matching / stays | — |
| qualification conditions met | EXPLORING→QUALIFIED | requires both slots empty | status becomes kept |
| `incompatible` recorded | →CLOSED, pending or not | cleared by closing | **observable effect: `SessionClose(reason: incompatible)` is emitted** (Section 17.2) |
| `Handoff` | QUALIFIED→HANDED_OFF, both slots empty, its consent granted | — | — |
| `SessionClose` / session expiry | →CLOSED | cleared | a Principal decision still in flight outside the session produces nothing on any axis when it lands |

## Qualification is a determined event

"Recomputed whenever consulted" was revision 1's wording and both reviews
refused it, rightly. The rule: **after every event that changes the
evaluation axis or empties a pending slot, and before emitting any
further message, the Agent re-evaluates the entry conditions of Section
15.2.** They are evaluated over the propositions standing at that moment
(nothing met mid-wait is remembered, S-47), they include the absence of
unanswered questions of our own, and the bilateral test is exactly the
mechanism 0.1 provides — this side's local conditions *and the last
`session_status` the responder reported* (Section 14.6, S-56); an Agent
never reads the peer's private conditions. Where the conditions hold, the
transition fires once, the status becomes kept, and the **initiator**
emits the single Opportunity, all before any further message.

## Two kinds of deadline

Session expiry and request deadline are different events and the reviews
found revision 1 conflating them. A **session** that expires closes
(`reason: expired`), clearing the pending axis. A **request** whose
`expires_at` passes without a terminal response is discharged on the
requester's side — the wait ends, nothing becomes a result — while the
responder's duties are unchanged from Section 14: a responder that cannot
decide in time sends a terminal `declined` or closes; silently dropping a
held request is the one outcome that is not conformant, except on the
PROBE approval path (Section 16.3, S-51), where expiry *is* the defined
terminal outcome and the requester learns nothing from it. Requests held
for a Principal's decision live in a correlation-and-deadline record on
the evaluation axis, not in the pending slots: no third pending kind
exists or is needed.

## The deadlock the concurrency rule keeps

With directions independent, one real blocking case remains, and it is
kept knowingly: A's consent request awaits B's Principal, and *A itself*
now needs a disclosure from B before deciding whether to pursue — A's own
sent-slot is occupied. The recovery path is 0.1's: the responder
terminates the consent (`declined`), the disclosure proceeds, the consent
is asked again. 0.1 gives the requester no autonomous cancellation, and
this draft adds none. The cost is accepted for 0.2; relaxing a direction's
slot into a set is possible in this model and deliberately withheld until
the corpus has met an independent implementation.

## The 0.1 view, for the wire

The 0.1 state names remain meaningful — the corpus and the published text
use them — as a projection. It is **deterministic and many-to-one**, and
the property claimed for it is not injectivity but **preservation of 0.1's
observable behaviour**: every 0.1 transition, refusal and emission is
reproduced.

```text
state = CLOSED | HANDED_OFF | REQUESTED            (phase, verbatim)
      | DISCLOSURE_PENDING | CONSENT_PENDING      (a view reports its own
                                                   sent slot first, then
                                                   the received one)
      | CONSENTED   (QUALIFIED + a grant whose phase-at-grant was QUALIFIED)
      | QUALIFIED   (phase QUALIFIED otherwise)
      | PROBING     (EXPLORING, both slots empty)
```

The projection needs exactly one datum beyond the current axes — the
phase-at-grant metadatum above. Current phase plus currently effective
consents do not suffice, and the two traces that prove it (the same grant
before versus after qualification, converging to identical axes) are the
first review's; the metadatum is the minimal memory that separates them.

## Deliberately out of this draft, with their places reserved

The bilaterally *accepted summary* before emission (the full mechanism
behind S-56's status gate) is the next piece of the 0.2 session work. It
layers on this model as an **object, not an axis**, and its storage is
reserved now: an evaluation-revision counter on the evaluation axis, and
the accepted summary recorded beside the grants, referenced by the
Opportunity. Distributed qualification — two sides agreeing on *the same*
evaluation rather than each on its own — remains open until then, which
is the second review's point 5 and is acknowledged rather than solved
here. Relaxing one-request-per-direction is the other deferral, above.
