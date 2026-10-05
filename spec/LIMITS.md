# Where this protocol should not be used

**Florian Williams · https://gidp.dev · 23 September 2026 · non-normative**

Four domains have been run against a single implementation of the core, and
they work. They were also all chosen because they would. This document is the
other half of that exercise: four cases chosen because they looked like they
would break, each attacking a different assumption, each with a hypothesis
stated before the run.

All four confirmed their hypothesis. None of them is a bug — every one is a
boundary the specification did not state, and stating a boundary is cheaper
than having a reviewer find it. The cases are reproducible:
`impl/examples/limits.py`, and `impl/tests/test_limits.py` keeps them honest.

---

## L-1 · Where the law requires publication

**Attacked:** the premise. **Verdict: out of scope, and the protocol cannot
even express the conflict.**

A public buyer is legally obliged to publish the object of a tender, its value
band and its award criteria. The Disclosure Policy can classify all three as
`public` — and that says they *may* appear without authentication, not that
they must. An Agent holding `PUBLISH_PROJECTION: false` and a policy full of
`public` attributes is perfectly conformant while its Principal is in breach.

The disclosure model is monotonically permissive: every class is an upper
bound on exposure and none is a lower bound. That is a deliberate design — a
protocol whose purpose is to withhold has no business compelling disclosure —
but it means regimes built on mandatory transparency are not merely poorly
served, they cannot be stated in this vocabulary at all.

*A correction to an earlier version of this document, which said the conflict
was inexpressible.* It is inexpressible **here**; it is not inexpressible.
W3C's ODRL Information Model 2.2 has carried the distinction since 2018: a
Permission permits an action, a Prohibition forbids one, and a **Duty**
obligates one, with a Policy attaching obligations by reference. A deployment
that must express "this MUST be published" already has a standard vocabulary
for saying so, and the honest statement of L-1 is therefore not that the
problem is unsolvable but that GIDP's Disclosure Policy is a permission
language and a duty language is a different object, which this protocol does
not attempt and should compose with rather than absorb.

**Consequence.** Public procurement, regulated listing disclosure, and any
market where publication is an obligation rather than a choice are out of
scope. A deployment in such a market needs an obligation layer beside the
protocol; ODRL is the obvious candidate and this document does not propose a
competing one.

---

## L-2 · Where the interest has one dimension, or expires

**Attacked:** the assumption that conditions do not fungibilise, and the
assumption that a human can answer in time. **Verdict: out of scope on both
counts.**

A freight slot leaving in two hours has one real dimension, price. Run the
probing demonstration against a single-dimension interest and it recovers the
private floor in eight queries — the same eight as the multi-dimension case,
because the other dimensions were never what hid the threshold; they were what
made the threshold *worth* hiding. Where price is the only axis, a compatibility
session is price discovery conducted slowly and with worse guarantees than a
sealed-bid auction, which is the mechanism that market already uses.

The second failure is simpler and harder. A `principal_approval` gate means a
human decides. A slot that expires in two hours cannot wait, and an Agent that
pre-approves everything to keep up has switched the gate off while still
claiming it.

*A note on the method, since it cost us a run.* The first version of this case
bisected in the wrong direction and converged on the search bound rather than
the secret: a floor and a ceiling are probed with opposite inequalities. An
attacker who does not know which it faces spends a few queries finding out,
and no more — which is a small result in its own right, and a reminder that a
demonstration can be wrong in the flattering direction.

**Consequence.** Commodity, capacity and spot markets — anything fungible,
one-dimensional or perishable — are out of scope. The protocol's value is in
the breadth of conditions that make an interest hard to state, and it is
exactly nil when there is one number.

---

## L-3 · Where the two sides are not comparably exposed

**Attacked:** reciprocity as a defence against probing — the candidate
direction the companion note calls the most promising. **Verdict: the lever
inverts, and this is the most uncomfortable finding of the four.**

One employer, twenty candidates. The employer probes each candidate's salary
floor: four questions brackets it. Reciprocity lets each candidate ask the
same of the employer, and each learns *the same band* — the employer spends
one fact twenty times, while each candidate spends a scarce and personal one.
After twenty sessions the employer has narrowed twenty private values and
disclosed one.

Per-counterparty query budgets do not help. The employer's twenty sessions are
with twenty different counterparties and every one of them is legitimate; no
budget keyed to a counterparty sees the aggregate. Budgets keyed to the
*asker* would, but nothing in the protocol carries an asker's identity across
sessions, and adding it would require exactly the persistent identity the
design avoids.

**Consequence.** Reciprocity is a real cost only between parties with
comparable exposure — two companies, two funds, two agents with something to
lose. In consumer-facing or employment contexts, where one side runs thousands
of sessions and the other runs three, it protects the strong side. The
companion note's candidate direction is hereby qualified, and the qualification
belongs in it.

---

## L-4 · Where identity must come first

**Attacked:** the ordering of the authority ladder. **Verdict: out of scope,
and structurally so.**

A sanctions-screened or KYC-gated market must establish who it is dealing with
*before* any substantive exchange. Attempt that and the state machine refuses:
`ConsentRequest` is admissible only from `QUALIFIED` or `CONSENTED`, and
`QUALIFIED` is reached by probing. Identity is structurally last.

That ordering is not incidental. It is the protocol's central privacy
property: you learn whether it is worth talking before you learn who you are
talking to. It is also, in a regulated market, the wrong way round — and the
specification presents the ladder as a list of levels without saying that its
order is enforced rather than conventional. A domain profile cannot reorder
it, because profiles may not weaken the core semantics of Sections 10, 15.5,
16 and 24.

**Consequence.** Regulated markets requiring pre-engagement screening are out
of scope for GIDP 0.1. Whether a future version should permit an identity-first
profile is a real question, and it is not a small one: it would invert the
property the whole design exists to provide.

---

## What this adds up to

GIDP is for markets where the conditions are multi-dimensional, the parties are
comparably exposed, publication is a choice rather than an obligation, and
identity can wait. Corporate transactions, executive appointments, commercial
partnerships and private financings sit inside that description. Commodity
markets, consumer-facing asymmetries, regulated disclosure and screened
markets sit outside it.

A protocol that claims everything invites the reviewer to find the one thing
it cannot do. Naming four of them first is cheaper, and more honest about what
the four working domains actually demonstrate.
