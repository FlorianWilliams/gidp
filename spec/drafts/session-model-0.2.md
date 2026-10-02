# The session model in three axes (0.2 draft)

Status: draft for GIDP 0.2. The 0.1 state machine (specification, Section
17.2) remains normative until 0.2 is published; this document is the
redesign every review of 0.1 converged on, and the reference
implementation already runs on it — with the 0.1 states kept as a derived
view, so that the wire, the conformance corpus and the 0.1 text remain
exactly satisfied. That is the design's acceptance test: nothing
observable changed, and the patches disappeared.

## The diagnosis

0.1 encoded three different things in one state. `DISCLOSURE_PENDING` was
simultaneously *where the session is* and *what is in flight*;
`CONSENTED` was a phase that actually recorded a fact about consents;
and the rules that made it work were patches with their own section
numbers: the `return to the state it was asked from` bookkeeping (S-22),
the deferred qualification recomputed at the return (S-34, S-47), the
narrowed `open`-while-pending rule (S-50), the grant-before-qualification
exception. Each patch was correct; their number was the finding.

## The model

A session, per side and per direction of request, is three independent
axes:

**Phase** — the monotonic life:

```text
REQUESTED → EXPLORING → QUALIFIED → HANDED_OFF
     └──────────┴───────────┴──────────┴────→ CLOSED
```

Four transitions move it: `SessionAccept` (REQUESTED→EXPLORING), the
qualification transition (EXPLORING→QUALIFIED, at most once), `Handoff`
(QUALIFIED→HANDED_OFF, with its granted consent), and closing. Nothing
else does. In particular, a disclosure or a consent request never moves
the phase.

**Pending** — the request in flight: empty, one disclosure, or one
consent. At most one at a time per side's view, which is 0.1's implicit
concurrency rule made explicit and kept deliberately (the reviews judged
tighter concurrency reasonable for this stage). A request opens it; the
terminal response clears it; a provisional response leaves it in flight.

**Evaluation and consents** — standing propositions and their results,
the peer's last reported status, the profile's required dimensions,
dependencies, and the set of granted consents (per action and scope, held
by the Agent). `session_status` is computed from this axis, with two
reads from the others: a non-empty pending axis reports `open`
pre-qualification, and the kept status after qualification reads the
phase.

## Each event states its effect per axis

| Event | Phase | Pending | Evaluation / consents |
|---|---|---|---|
| `SessionOpen` / `SessionAccept` | advances | — | — |
| `CompatibilityRequest` / `Response` | — | — | records propositions, peer status, contingencies |
| `DisclosureRequest` | — | opens (refused if occupied) | — |
| `DisclosureResponse` terminal | — | clears | gate bookkeeping |
| `DisclosureResponse` provisional | — | stays | — |
| `ConsentRequest` | — | opens (action rules of 14.5 apply) | — |
| `ConsentResponse` granted | — | clears | records the grant (post-qualification grants surface as CONSENTED in the 0.1 view) |
| `ConsentResponse` declined / provisional | — | clears / stays | — |
| qualification condition met | EXPLORING→QUALIFIED iff pending empty, both sides' entry conditions hold | — | status becomes kept |
| `incompatible` recorded | →CLOSED, pending or not | cleared by closing | — |
| `Handoff` | QUALIFIED→HANDED_OFF iff pending empty and its consent granted | — | — |
| `SessionClose` / expiry | →CLOSED | cleared | — |

## What the patches become

- *Return-to-stage (S-22)*: nothing to state. The phase never left the
  stage, so the answer has nothing to restore.
- *Deferred qualification (S-34, S-47)*: nothing to state separately.
  Qualification requires the pending axis empty and recomputes the entry
  conditions whenever consulted; a condition met mid-wait is simply not
  yet consulted from a firing position, and at the return it is
  recomputed over the propositions then standing.
- *The narrowed `open` rule (S-50)*: structural. `incompatible` is read
  from the evaluation axis before anything else; the kept status reads
  the phase; only the not-yet-qualified, pending-occupied case reads
  `open`.
- *Grant before qualification (10.2)*: a grant records a fact on the
  consent axis. Whether the 0.1 view calls the session CONSENTED depends
  on the phase at the moment of the grant — a fact about two axes, not a
  fifth state.

## The 0.1 view, for the wire

The 0.1 state names remain meaningful — the corpus and the published
text use them — as a projection:

```text
state = CLOSED | HANDED_OFF | REQUESTED            (phase, verbatim)
      | DISCLOSURE_PENDING | CONSENT_PENDING       (pending axis)
      | CONSENTED   (QUALIFIED + post-qualification grant)
      | QUALIFIED   (phase QUALIFIED otherwise)
      | PROBING     (EXPLORING, nothing pending)
```

The projection is total and injective enough for the wire: every 0.1
transition is reproduced, every 0.1 refusal is reproduced (same error
texts), and the 0.1 conformance corpus passes unchanged — which was the
corpus's stated design goal and is this draft's evidence.

## Deliberately out of this draft

The bilaterally *accepted summary* before emission (the full mechanism
behind 0.1's S-56 status gate) is the next piece of the 0.2 session
work, layered on this model: it adds an object, not an axis. Relaxing
the one-pending-at-a-time rule is possible in this model (pending
becomes a set) and deliberately not done: the corpus should first meet
an independent implementation under the simple rule.
