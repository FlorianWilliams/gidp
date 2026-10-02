# The session model in three axes (0.2 draft, revision 5)

Status: draft for GIDP 0.2. The 0.1 state machine (specification, Section
17.2) remains normative until 0.2 is published. The reference
implementation runs on this model with the 0.1 states kept as derived
views; reproducing 0.1's observable behaviour — every transition, refusal
and emission — is the model's **objective**, and the conformance corpus is
its **current verification**. Three rules in this revision are new 0.2
semantics rather than 0.1 equivalence, and are marked as such where they
appear: the deadline semantics, the supersession of an expired claim,
and the Handoff quiescence barrier.

## The model

A session, per side, is three axes.

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
disclosure or one consent. The directions are independent (Section 17.2
holds state per direction of request): an Agent whose own consent awaits
the peer Principal's decision can still receive, and answer, a disclosure
the peer asks meanwhile. Within one direction, at most one request is in
flight at a time.

A terminal response clears **the matching pending request**, identified
by direction and `request_ref`, and correlation is checked before
clearing: a delayed duplicate of an earlier response names a request
already discharged, is refused, and does not clear the wait a newer
request opened. A provisional response leaves the request in flight. A
response received after the session closed, or after its request's
expiry, produces no effect on any axis.

**Evaluation and consents** — standing propositions and their results, in
*both directions as locally known* (the responder records the
propositions it receives and the results it emits, exactly as the
requester records what it sent and received); **unanswered propositions**
(below); the peer's last reported `session_status`; the profile's
required dimensions; dependencies; and the granted consents.

Consents are held by the Agent, outside the session object, under an
explicit ownership contract: a grant is indexed by **session, direction,
action and scope** — two sessions sharing an action/scope pair share
nothing, and a grant in one directional view does not alter the other's
projection. Each grant carries one metadatum the projection needs:
*whether the phase was QUALIFIED when the grant was recorded*, the phase
being read **before the grant is processed**, so a pre-qualification
grant that unblocks a deferred qualification never becomes
retrospectively post-qualification. That historical fact is distinct from
the grant's effective authorisation: withdrawing the authorisation (no
wire message does; a Principal withdraws it locally) does not erase the
fact, and every act of use re-runs the decision order of Section 16.3
regardless.

## Admission versus effect

The table describes the **effects of admitted events on each axis**. It
does not replace the admission guards: the refusals of Section 17.2 — an
event in a phase that does not admit it, a second request in an occupied
direction, anything after `CLOSED` — apply before any row is read, **and
admission always reads the axes and the direction, never a projected
state**. A pending request in a closed session is unreachable: closing
clears the pending axis and `CLOSED` admits nothing that would reopen it.

| Event | Phase | Pending | Evaluation / consents |
|---|---|---|---|
| `SessionOpen` / `SessionAccept` | advances | — | — |
| `CompatibilityRequest` sent | — | — | records an unanswered question of ours |
| `CompatibilityRequest` received | — | — | records the received propositions; held for a PROBE approval (Section 16.3), they are recorded unanswered with the request's deadline |
| `CompatibilityResponse` sent | — | — | records the results this side emitted; a locally produced `incompatible` reaches the incompatible row below directly |
| `CompatibilityResponse` received | — | — | resolves our question; records results, peer status, contingencies |
| `DisclosureRequest` | — | opens its direction's slot (refused if occupied) | — |
| `DisclosureResponse` terminal | — | clears the matching slot (correlation first) | gate bookkeeping |
| `DisclosureResponse` provisional | — | stays | — |
| `ConsentRequest` | — | opens its direction's slot (action rules of 14.5) | — |
| `ConsentResponse` granted | — | clears matching | records the grant, with its direction and phase-at-grant metadatum |
| `ConsentResponse` declined / provisional | — | clears matching / stays | — |
| qualification conditions met | EXPLORING→QUALIFIED | requires both slots empty | status becomes kept |
| `incompatible` recorded — received *or locally produced* | →CLOSED, pending or not | cleared by closing | observable effect: `SessionClose(reason: incompatible)` is emitted (Section 17.2) |
| request expiry (see *Deadlines*) | — | clears the expired wait | an expired question's propositions remain unanswered |
| `Handoff` | QUALIFIED→HANDED_OFF, **both directions quiescent** (0.2 semantics, below), its consent granted | — | — |
| `SessionClose` / session expiry | →CLOSED | cleared | a Principal decision still in flight outside the session produces nothing on any axis when it lands |

## Unanswered propositions

A claim stands without a result in two cases: a question of ours whose
request has no terminal yet (or expired without one), and a question we
received and hold for a PROBE approval — **CompatibilityRequests held for
a PROBE approval are the only human waits outside the pending slots**;
provisional disclosures and consents keep their slot *and* their
approval tracking. Held and expired questions live in a
correlation-and-deadline record on the evaluation axis, per direction,
on both sides.

An unanswered proposition blocks qualification on every side that knows
of it: a question that went unanswered must not make a session
qualifiable, and expiring an awkward question is not a qualification
tactic. **0.2 semantics:** the sender of an expired, unanswered claim MAY
supersede it — Section 14.2 extended to exactly this case — which is
the in-session recovery; superseding an `incompatible` result remains
forbidden. The rule rests on its operational invariants, not on any
claim that a non-answer is information-free (it is not: silence and its
timing can leak, as Section 24.7 acknowledges, and a terminal received
after expiry was refused by the machine yet read by the Agent):
supersession removes no recorded `incompatible`, refunds and resets no
disclosure budget, and leaves the responder's contradiction-closing
duty intact. Without supersession, the proposition blocks for the life
of the session and recovery is a new session against the same budget.

## Qualification: roles, trigger, and emission order

Four things, defined separately because conflating them is circular:

- **Local conditions.** Each side evaluates the entry conditions of
  Section 15.2 over the propositions *it* knows, in both directions,
  its profile's required dimensions included. No side ever reads the
  peer's private conditions.
- **The status a side reports.** A responder whose local conditions hold
  reports `potentially_compatible` in its next `CompatibilityResponse`.
  This needs nothing from the peer: it is how the first positive status
  enters the session.
- **The responder's transition** follows its local conditions alone.
- **The initiator's transition, kept status and emission are one
  event**, conditioned together on its local conditions *and* the
  responder's last reported status being `potentially_compatible`
  (Section 14.6). While the responder's last report is `open`, the
  initiator remains in `EXPLORING` whatever its local conditions: it is
  not `QUALIFIED` without an Opportunity, no post-qualification action
  (an identity request, say) is admissible, and its unique transition is
  not consumed. When a later response carries the responder's positive
  status, the next re-evaluation fires transition and emission together.

**Trigger:** after every event that changes the evaluation axis or
empties a pending slot, and before emitting any further message, a side
re-evaluates its qualification conditions — local ones, plus the
responder's last reported status on the initiator's side — over the
propositions standing at that moment; nothing met mid-wait is
remembered. Where they hold, the transition fires once and the status
becomes kept.

**Emission order:** when a locally prepared terminal response is what
empties the last slot and enables qualification, the observable order is
fixed — the triggering terminal response first, then the Opportunity,
then any further message. The re-evaluation obligation never reorders
those two.

## Deadlines

Session expiry and request deadline are different events. A **session**
that expires closes (`reason: expired`), clearing the pending axis. For a
**request** whose `expires_at` passes with no terminal received:

- **0.2 semantics, stated as such:** the requester's wait is discharged
  without closing the session — the 0.1 table knows no exit from a
  pending state on expiry, and 0.1 itself is in tension here with
  Section 14.5's bounded wait; 0.2 resolves the tension in favour of the
  session's survival. A terminal sent in time but received after expiry
  names a discharged request and is refused by correlation.
- The responder's duties are unchanged from Section 14: decide in time,
  send a terminal `declined`, or close. Silently dropping a held request
  is non-conformant — except on the PROBE approval path (Section 16.3),
  where expiry is the defined terminal outcome and the requester learns
  nothing from it beyond the absence of an answer, which stays on the
  evaluation axis as an unanswered proposition.

## The Handoff quiescence barrier (0.2 semantics, stated as such)

The 0.1 table, read per direction, admits `CONSENTED → HANDED_OFF` in
one directional view while the other direction holds a pending
disclosure. 0.2 adds a barrier and declares it — and declares its
**scope: a local guard**, nothing more. A `Handoff` may be emitted only
when, *in the emitter's local knowledge*, both pending slots are empty
and no CompatibilityRequest is active in either direction — an own
question still undischarged, or a received question held unanswered. An
expired-but-unsuperseded proposition is an evaluation fact, not an
active request, and does not block. A Handoff ends GIDP's
responsibility for the interaction (Section 14.7), and an unresolved
wait should not cross that boundary; requiring local quiescence is the
honest alternative to defining the fate of an orphaned wait on the far
side. This is a deliberate coupling between directions; admission of
requests remains per direction.

A local guard cannot see a request in transit, so **emission is not a
bilateral acceptance of the transfer**, and the collision is defined:
when a Handoff arrives while the recipient's own request is still in
flight, the recipient's directional view is not `QUALIFIED` or
`CONSENTED`, and 0.1's own recipient rule decides — it closes the
session with `reason: unsupported`, which also ends its wait, and the
emitter moves `HANDED_OFF → CLOSED` on receiving that close (the
transition exists in the 0.1 table). A request that reaches a session
already `HANDED_OFF` is not processed and expires at its sender.
Recovery from the race is a new session against the same budget. A
deployment that wants a *guaranteed* absence of requests in transit
needs coordination this document does not provide — an
admission-closing exchange confirming both sides ready — and no local
inspection of registers can substitute for it.

## The bounded wait the concurrency rule keeps

One blocking case remains within a single direction and is kept
knowingly: A's consent request awaits B's Principal while A itself needs
a disclosure from B before deciding whether to pursue. It is a *bounded
wait*, not a deadlock — every exit is finite — and the exits are
distinct: the responder terminates the consent (`declined`), the request
expires (above), or the requester closes the session. The requester has
no autonomous cancellation and this draft adds none; expiry is a
deadline, not a second recovery mechanism. Relaxing a direction's slot
into a set is possible in this model and deliberately withheld until the
corpus has met an independent implementation.

## The 0.1 views, for the wire

The faithful 0.1 projection is **per directional view**, as Section 17.2
defines state: `state(direction)` reads that direction's pending slot,
and `CONSENTED` reads only that direction's post-qualification grants.
An aggregated single state (own sent slot first, then received) exists
for display and MUST NOT drive admission: it changes which direction it
represents when a slot empties, and is therefore the faithful projection
of no continuously followed view.

```text
state(d) = CLOSED | HANDED_OFF | REQUESTED        (phase, verbatim)
         | DISCLOSURE_PENDING | CONSENT_PENDING  (direction d's slot)
         | CONSENTED   (QUALIFIED + a grant of direction d whose
                        phase-at-grant was QUALIFIED)
         | QUALIFIED   (phase QUALIFIED otherwise)
         | PROBING     (EXPLORING, slot d empty)
```

The projection is deterministic and many-to-one; the property claimed is
preservation of 0.1's observable behaviour **outside the three
explicitly marked 0.2 semantic changes**, with the corpus as the
current check. It needs exactly one datum beyond the current axes — the
per-grant phase-at-grant metadatum — because the current phase plus the
currently effective consents cannot distinguish a grant made before
qualification from one made after.

## Deliberately out of this draft, with their places reserved

The bilaterally *accepted summary* before emission layers on this model
as an **object, not an axis**; its storage is reserved — an
evaluation-revision counter on the evaluation axis, the accepted summary
recorded beside the grants, referenced by the Opportunity. Distributed
qualification (two sides agreeing on *the same* evaluation rather than
each on its own) remains open until that object exists. Relaxing
one-request-per-direction is the other deferral, above.
