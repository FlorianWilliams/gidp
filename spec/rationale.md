# GIDP — Design Rationale

This document holds the *why* behind rules whose *what* lives in
`GIDP-0.1.md`. The specification states obligations; this file records the
arguments, the histories and the worked failures that produced them, so that
the normative text can stay short without the reasoning being lost. The
defect log — what external reviews and the reference implementation found,
and how each finding was resolved — is `impl/SPEC-ISSUES.md`; the
experimental record — setups, distributions, metrics and the numbers the
specification cites — is `alternatives.md`; the questions still open, with
the positions 0.1 takes, are `open-problems.md`.

A rule in the specification never depends on this file. If a passage here
appears to add an obligation the specification does not state, the
specification is right and this file has a bug.

## The name, and the version token

The protocol was drafted under two earlier names. *Private Mandate
Discovery* fell because "mandate" had, by 2026, acquired a precise meaning
in the agent-payments ecosystem — a signed proof that a principal authorised
a specific transaction (AP2's `IntentMandate` and `CartMandate`, and the
mandate objects specified by A2CN and Concordia) — which is close to the
opposite of an interest that is *not yet* authorisation for anything.
*Conditional Interest Discovery* fell on its contraction: `cid` is the
established abbreviation of the IPFS Content Identifier, and the DID/VC and
agent ecosystems this protocol is designed to sit in use content identifiers
constantly; a wire token `cid/0.1` would be misread in exactly the layer
where it must not be. The protocol was renamed rather than carry the
collision, and the wire token is the current acronym in lower case:
`gidp/0.1`. The general lesson was that a protocol name must survive its
own abbreviation inside the layer it will inhabit.

## Why a disclosure or a consent returns the session to the state it was asked from

Section 17.2 states that a disclosure or a consent is a request made
*within* a stage of the session, not a stage of its own. Before this was
stated, the state machine read naturally as: `DISCLOSURE_PENDING` resolves
to `PROBING`. Under that reading, a disclosure asked *after* qualification
returned a qualified session to `PROBING` — from which no `Handoff` is
reachable and no second `Opportunity` may be produced, since qualification
is reached at most once. One more question could therefore un-qualify a
session, silently and permanently. The `return to the state it was asked
from` rule exists to close that path, and the related rule — that a
qualifying status reached *while* a request is pending fires only on the
return to `PROBING`, recomputed over the propositions then standing — exists
because the alternative gave one sequence of messages three defensible
readings.

## Why NEGOTIATE_NONBINDING is outside the session

Early working drafts left it ambiguous whether non-binding structures could
be proposed inside a Compatibility Session. The ambiguity was settled
against: a session establishes whether two Principals should be talking,
using the result vocabulary of Section 15 and nothing else, and proposing
terms — even non-binding ones — is negotiation, which happens after a
Handoff under whatever protocol the Handoff targets. The authority level is
retained in the ladder anyway, because a Principal must be able to express
in the Standing Interest whether its Agent may carry that authority forward
at all. The operational form of the boundary is Section 14.3's rule that a
claim is a test of a hypothesis, not a position.

The five-round pattern of the earliest working notes — discovery,
compatibility, constraints, intersection, human consent — survives in the
conceptual stages of Section 13 (Stages 2, 4, 4–5, 6 and 6 respectively);
the object model replaced the rounds, not the sequence.

## Why retention borrows XACML's obligation/advice distinction

Section 10.7 requires a requester not to state a retention it cannot
discharge, and an implementation that can discharge none to omit the field.
The distinction doing the work is XACML's: an *obligation* is something an
enforcement point must carry out, and a conforming XACML enforcement point
must deny access outright when it cannot discharge an obligation attached
to a permit; *advice* it may ignore. A field that a recipient may state and
then disregard is advice whatever the specification calls it, and the only
lever a protocol has is to make disregarding it non-conformant. GIDP cannot
verify discharge and does not pretend to; what it can do is refuse to call
something a limit when nothing turns on it — hence the omission rule, which
leaves the responder to decline, the safe outcome.

## The minimisation curve, and who can see its deciding quantity

Section 11.4 advises minimising projections and warns that minimisation
past a point reverses. The fuller argument, measured on a synthetic index
(`alternatives.md`): an over-precise projection is retrieved *less*, not
more, because it answers only querents who described the target in the same
terms — though that effect is a property of a token-comparing provider, and
a provider that resolves one hierarchy removes it entirely (Section 12.4).
A projection coarse enough to be retrieved by everyone is retrieved by
everyone, and each retrieval is a session with a counterparty that had no
business finding this Principal — an opportunity to probe under Section
24.3. Past a certain coarseness the sessions cost the publisher more than
the projection saved it. The quantity that decides where that point falls
is how many other publishers a given projection will be confused with —
observable to the Discovery Provider, unobservable to the publishing Agent.
Section 12 deliberately gives a provider no way to report it: a provider
that told publishers the size of a matching set would also be calibrating
an adversary.

The related provider recommendation (Section 12.4, hierarchy resolution)
has its cost fall somewhere unexpected: a token-comparing provider never
returns a publisher who named a city to a querent who named the country, so
the publisher compensates by publishing the country instead — conceding a
*less precise* attribute to the index in order to repair a defect in the
index. Resolving hierarchies removes the incentive; the measured effect on
recall is in `alternatives.md`.

## Why the cryptographic neighbours settle only half the problem

Secret handshakes and the 1985 matchmaking constructions (Section 1.1)
obtain mutual revelation exactly — but for a predicate that is agreed in
advance: membership, or naming the same counterparty. The half they settle
is the half where both sides already know what question they are jointly
answering. GIDP's predicate is a conjunction of conditions neither party
has stated, discovered by the session itself; that discovery, conducted
under disclosure control, is the half the cryptography does not settle, and
it is the half this document specifies. Where the predicate *can* be fixed
in advance, a profile is free to use the cryptographic tools (Section
24.12).
