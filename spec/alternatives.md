---
title: Conditional Interest Discovery — Why not use an existing mechanism?
version: 0.1
date: 2026-09-23
status: Non-normative companion to CID 0.1
---

# Why not use an existing mechanism?

**{{AUTHOR}}, Independent · {{CONTACT}} · {{CANONICAL_URL}} · CC BY 4.0 · non-normative**

The first objection to any new protocol is that something already does the
job. For this one the candidates are obvious: hire an intermediary, publish a
listing, run a secure comparison, compute a private set intersection. The
specification answered that objection in prose, with a table of requirements
mapped to mechanisms. Prose written by the author of the protocol is worth
nothing as evidence.

This document replaces it with a measurement. Four existing mechanisms and
this protocol are given the same case, the same private facts and the same
yardstick, and the results are printed as they came. They are reproducible:
`impl/baselines/`, run with `python -m baselines.compare` and
`python -m baselines.mitigations`, and guarded by `impl/tests/test_baselines.py`.

The conclusion is that the specification's claim survives, but narrowly, in a
weaker form than it was written, and at the cost of a defect in the
specification itself, which is recorded at the end.

## The case, and what is being measured

A French software company is privately authorised to explore an acquisition in
Germany. A German software company is **not for sale**, but would consider a
transaction if the counterparty brings access to France, the founder stays
involved, and a valuation floor is met. The floor and the management condition
are never to be stated. Neither company ever says "we want to buy" or "we
might sell".

Five facts are private: whether each side has any such interest at all, the
German company's valuation floor, its management condition, and the French
company's budget ceiling. Each is modelled as a point drawn from a finite
prior — a grid of valuations in five-million steps, six plausible management
conditions, a yes or no on existence — which totals **15.30 bits**.

Leakage is the reduction of an observer's hypothesis space, in bits: zero
means the observer learned nothing, 15.30 means it learned everything. The
posterior is computed by enumeration rather than estimated, and the harness
refuses to run if any observation rules out the true value, because a model
that narrows past the truth flatters every mechanism it describes.

Three audiences are counted separately, and the distinction matters more than
the totals. What a counterparty learns is spent deliberately, once. What an
operator learns accumulates over every pair it serves. What the public learns
is permanent and its audience is unbounded.

## The table

| Mechanism | Verdict | Questions | → counterparty | → operator | → public |
|---|---|---|---|---|---|
| Trusted intermediary | introduce | 1 | 4.66 b | **15.30 b** | 0 |
| Public listing | introduce | 1 | 6.62 b | 0 | **5.62 b** |
| Ideal sealed comparison | introduce | 1 | 4.66 b | 0 | 0 |
| Private set intersection | **cannot decide** | 1 | 2.00 b | 0 | 0 |
| CID, honest counterparty | introduce | 6 | 4.30 b | 0 | 0 |
| CID, probing counterparty | introduce | 17 | **9.94 b** | 0 | 0 |

Read the first three rows together. Against a counterparty that asks what it
needs and stops, the three mechanisms that decide the case leak roughly the
same amount to that counterparty: 4.30, 4.66, 4.66 bits. What separates them
is not the bit count, and a comparison that stopped at the first column would
be measuring nothing.

**The intermediary** learns everything, exactly, permanently, and again for
every pair it serves. This is the status quo — the banker, the headhunter, the
corporate development team — and it works, which is why any protocol that
cannot beat it on something is pointless. It is beaten on exactly one thing,
and that is the second column.

**The listing** leaks less in total than the intermediary, and for a company
that is not for sale it is the worst of the five, because the audience is
unbounded and the disclosure cannot be withdrawn. The existence of the
interest is one bit, and it is the only bit that mattered.

**The ideal sealed comparison** — a secure two-party computation of an agreed
predicate, modelled at its theoretical best — is the honest winner on leakage
among the mechanisms that decide the case. Anyone who needs a single yes or no
and has already found their counterparty should use it rather than this
protocol. It cannot find the counterparty, it cannot agree the predicate
without naming the dimensions, it cannot report which dimensions are open
rather than a single bit, and it cannot answer conditionally so that a near
miss can be repaired.

**Private set intersection** leaks the least of all, 2.00 bits, and cannot
decide the case: the binding conditions here are a threshold and a condition,
not set membership. Leaking nothing about a question you cannot ask is not a
privacy property.

**CID** is the only one of the five that performs discovery, decides the case,
and leaves no third party holding both secrets. That is the whole of what it
buys, and it is narrower than the specification's prose implied.

## What it costs

The last row is the one that matters. Against a counterparty that spends
questions instead of asking once, the same protocol with the same answering
policy gives up 9.94 bits in seventeen questions — sixty-five per cent of
everything at stake, and more than the intermediary discloses to the
counterparty. The intermediary at least knows who it is trusting.

That is Section 24.3 of the specification with a number attached, and it is
the strongest argument against deploying this protocol as it stands.

## Do the protocol's own defences work?

Section 15.5 gives a responder three moves: answer truthfully, coarsen to
`conditionally_compatible`, or decline. The specification presents coarsening
as an inference-limiting lever. It was never measured. Sweeping answering
policies against query budgets, with an adversary that asks whichever question
best splits its remaining hypotheses and re-asks it when the answer was
uninformative:

| Answering policy | budget 4 | budget 8 | budget 16 | budget 64 |
|---|---|---|---|---|
| Truthful, no coarsening | 3.30 b · 0 % / 100 % | 7.94 b · 100 % / 100 % | 7.94 b · 100 % / 100 % | 7.94 b · 100 % / 100 % |
| **Coarsen affirmative local answers (§15.4)** | **3.30 b** · 0 % / 100 % | **7.94 b** · 100 % / 100 % | **7.94 b** · 100 % / 100 % | **7.94 b** · 100 % / 100 % |
| Randomise half the local answers | 1.90 b · 0 % / 100 % | 3.04 b · 100 % / 61 % | 7.94 b · 100 % / 61 % | 7.94 b · 100 % / 61 % |
| Coarsen every local answer | 0 b · 0 % / 100 % | 0 b · 100 % / 0 % | 0 b · 100 % / 0 % | 0 b · 100 % / 0 % |
| Decline every local answer | 0 b · 0 % / 100 % | 0 b · 0 % / 100 % | 0 b · 0 % / 100 % | 0 b · 0 % / 100 % |

Left of each cell: bits extracted about the valuation floor and the management
condition, out of 7.94. Right: the true positive and true negative rates of an
honest session, swept across every counterparty in the prior. Both rates must
be high for a policy to be worth anything; either alone is trivial.

Four findings, in descending order of how uncomfortable they are.

**The coarsening of Section 15.4 stops no inference at all.** Its row is
identical to the plainly truthful row in every cell. The reason is structural
rather than empirical: coarsening an affirmative answer replaces one
deterministic result with another, so the adversary's partition of the
hypothesis space is unchanged and the relabelling costs it nothing. The lever
protects the *value* from being transmitted, which is real and is what
Section 15.4 was written for, and it provides no protection against inference,
which is what Sections 15.5 and 24.3 imply it provides. That is a defect in the
specification, recorded as S-12 in `impl/SPEC-ISSUES.md` and corrected in the
text before publication.

**The two extreme policies leak nothing and are worthless.** Coarsening every
local answer qualifies every counterparty, including all those that should have
been refused; declining every local answer qualifies none. Section 24.3's
remark that an oracle which never leaks never discriminates is no longer a
remark.

**Randomisation delays and does not bound.** Answering a local claim truthfully
half the time and coarsening it the other half holds the adversary to 3.04 bits
at a budget of eight, where a deterministic policy has already given up
everything — and at a budget of sixteen it has given up everything too, because
a coin flipped often enough stops hiding anything and the adversary here
re-asks. It also costs thirty-nine points of true negative rate: a coarsened
refusal reads as a maybe, so the session qualifies counterparties it should
have turned away. [RANI2026]'s randomised policy is designed against a passive
observer of traces; transplanting its shape against an adaptive querent does
not work, which is consistent with that paper leaving the adaptive adversary
open.

**The query budget is the only lever in the sweep that bounds anything.** It is
also the lever the L-3 limit case showed cannot be keyed to a counterparty when
one side faces many, and a budget keyed to the asker would need the persistent
identity this design deliberately does not carry.

## What this changes

Nothing in the object model, the state machine or the authority ladder. One
thing in the text: the specification no longer describes coarsening as an
inference-limiting measure, and Section 24.3 now says plainly that the only
mechanism in CID 0.1 which bounds adaptive inference is a bound on the number
of claims, with its known weakness named.

And one thing in the argument. The claim is no longer that existing mechanisms
cannot do this. It is that each of them gives up exactly one thing CID keeps —
the intermediary gives up having no one to trust, the listing gives up privacy
altogether, the sealed comparison and the set intersection give up discovery —
and that CID keeps all of them only for as long as the counterparty's questions
are bounded. Whether that bound can be made principled rather than arbitrary is
the open problem of `open-problems.md`, and this document is the first
measurement of how much rests on it.

## Three further measurements

The harness built for this comparison turned out to answer three more
questions the specification had asserted rather than shown. They are
summarised here because they belong to the same argument; the detail is in
`impl/baselines/` and in the specification sections they corrected.

**A query budget does not survive Sybil identities, and the cap that does
cannot tell its customers from its attackers.** Section 24.3 offers query
budgets as the defence against probing and Section 24.4 acknowledges that an
attacker may mint counterparties to get around them. Measured, the two cancel
exactly: an allowance of two claims per counterparty with four identities
extracts precisely what an allowance of eight with one identity extracts. A
cap on the responder's *total* answered claims cannot be diluted that way and
does bound — but a complete extraction costs seven answered claims here and an
honest session costs six, so no threshold separates the two populations. A
deployment is rationing, not defending, and should say which.

**Minimising a projection reverses past a point.** Section 11.4 calls the
trade-off fundamental and frames it as retrieval quality against inference
risk. On a synthetic index of two thousand publishers and three hundred
querents, an over-precise projection is retrieved *less* — it answers only
querents who described the target in the same words, so naming a city hides
you from someone who named the country — while a projection coarse enough to
be retrieved by everyone is retrieved by everyone, and at a session's worth of
inference per retrieval the publisher is drained completely. The usable band
is narrow, and the quantity that locates it is visible to the Discovery
Provider rather than to the publisher.

**The implementation crashed on the first input nobody designed.** Property
tests over generated Standing Interests found, at their first example, that a
claim whose operator does not fit the shape of the private value raised an
uncaught exception rather than answering `unknown` — which is both a denial of
service available to any counterparty and an inference channel, since the
responder's failure is a function of the shape of its own secret. Section 14.2
now requires `unknown`. Every hand-written test had passed, because an author
writes the claims the protocol was designed for.

None of the three changes what CID does. All three change what the
specification may claim, and the first two narrow the claim in the same
direction the table above does: this protocol's guarantees hold against a
counterparty whose questions are bounded, and CID 0.1 does not contain a
principled way to bound them.
