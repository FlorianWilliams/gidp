---
title: Conditional Interest Discovery — Open Problems and Design Rationale
version: 0.1
date: 2026-09-23
status: Non-normative companion to CID 0.1
---

# Open Problems and Design Rationale

**Status:** non-normative companion to *Conditional Interest Discovery (CID) Protocol — Draft 0.1*. Nothing here is a requirement. Where this document and the specification disagree, the specification is authoritative.
**Author:** {{AUTHOR}}, Independent. Contact: {{CONTACT}}.
**Canonical location:** {{CANONICAL_URL}}.
**Licence:** CC BY 4.0.
**Date:** 23 September 2026.

This document exists because a specification should state requirements, not argue for unproven solutions. It carries three things that do not belong in the normative text: the mapping from CID's requirements to mechanisms that already exist, so that a reader can see the protocol is not asking for new cryptography; the open problem the protocol runs into, stated for people who might solve it; and the reasoning behind choices the specification makes without justifying.

---

## Part I — The open problem

### 1. Why a compatibility oracle leaks

CID's compatibility semantics rest on an oracle. One Agent asks whether a claim holds against the other's private constraints; the other answers from the vocabulary of Section 15.1 without disclosing the values behind the answer. Section 15.4 gives the canonical illustration: an Agent privately holding `maximum_valuation = 80M`, asked whether a transaction within `{50M, 100M}` is compatible, answers `conditionally_compatible` and never transmits the threshold.

The threshold is nevertheless learnable. A querent who asks about `{50M, 60M}`, then `{60M, 70M}`, then `{70M, 80M}`, then `{80M, 90M}` and observes the last answer change has located the boundary without a single value crossing the wire. Section 24.3 names this; the point worth stating plainly is that **it is not an implementation defect but a property of any useful oracle**. An oracle that never leaks is an oracle that never discriminates, and an oracle that never discriminates cannot support discovery. The design question is therefore not how to eliminate leakage but how to bound what an adversary can extract per unit of effort, while leaving enough signal for honest counterparties to find each other.

### 2. The problem, stated

Let a responder hold a private constraint set *C*. A querent submits claims adaptively, each chosen in light of every answer so far. The responder answers under the truthfulness rule of Section 15.5: the truthful result, a coarsening of it (`conditionally_compatible` or `unknown`), or `declined` — never an answer its values contradict.

A mechanism is a responder policy, possibly randomised. **Leakage** is what an adaptive querent learns about *C* after *k* claims. **Utility** is the probability that two genuinely compatible Principals reach `potentially_compatible` within a bounded number of claims.

*Exhibit a policy, or prove none exists, that bounds leakage under adaptive querying while keeping utility above a usable threshold.*

Three features distinguish this from cases that are solved. The adversary **chooses** its queries rather than observing a trace. The responder must remain **truthful** in the above sense rather than free to lie — a constraint imposed by the protocol's purpose, since a peer that may assert falsehoods cannot be relied on for anything. And the bound must hold **across sessions and identities**, because an adversary can split its query budget over many counterparties it controls (Section 24.4).

### 3. What the neighbouring literature does and does not settle

[RANI2026] formalises behavioural privacy leakage in agentic negotiation and mitigates it with a phase-adaptive randomised policy achieving (ε,δ)-differential privacy with almost-sure convergence, reducing adversarial inference accuracy by 43–50 % while preserving utility. Its adversary is **passive**: it trains predictors on observed negotiation traces. The paper states that adaptive adversaries are future work. That is exactly our adversary.

Differentially private query mechanisms bound leakage under adaptive querying, which is their standard threat model, but they assume the mechanism may return a perturbed answer. CID's truthfulness rule forbids perturbation that asserts a falsehood. The two are reconcilable only in one direction: the responder may always retreat to `conditionally_compatible`, `unknown` or `declined`, so randomisation is available over the *coarsening* choice but not over the substantive answer. Whether that restricted randomisation is sufficient to obtain a meaningful bound is, as far as the author can establish, unstudied.

Private set intersection, secure multi-party computation and zero-knowledge range proofs hide the responder's inputs. They do not hide what the *result* reveals, and the result is the leak. A protocol that computes compatibility under MPC and returns `compatible` has leaked exactly as much as one that computes it locally and returns `compatible`. This is worth stating because "just use PSI" is the most common first reaction, and it addresses a different threat.

### 4. Candidate directions, none validated

These are offered so that a reader can attack them, not because any is believed to work. Three of the five have since been measured against an adaptive querent, and the measurements are in the companion document *Why not use an existing mechanism?*; where a direction has been tested, the result is stated with it rather than left for the reader to find.

**Simulatable answering.** *The one direction here with a pedigree rather than an invention, and it arrived late.* [KMN2005] shows that in query auditing a denial leaks whenever the decision to deny consults the data, and repairs it by requiring the decision to depend only on the queries asked and the answers already given — so that an attacker can reproduce the decision and learns nothing from it. Applied here it is a constraint rather than a mechanism, and a sharp one: no rule for coarsening or declining may consult the responder's own values. That disqualifies the coarsening of Section 15.4 outright, explains why it measured identically to answering plainly, and leaves exactly the family of policies that key off the claim sequence — of which a query budget is the simplest member. What it does *not* do is bound what the answers themselves reveal, which is the harder half of the problem and remains open. The same literature reports the general auditing problem to be NP-hard, which is a reason to expect deployment-specific auditors rather than a universal one.

**Minimum granularity.** Require every claim to be expressed over buckets no finer than a profile-defined width. Bounds the resolution of any single probe, and is cheap. It does not bound what repeated probing at that granularity yields, and it degrades utility precisely where precision matters — a valuation bucket wide enough to be safe may be too wide to be informative.

**Budgets with accounting.** *The only direction here that bounded anything under measurement, and the one whose objection is hardest.* Treat each session as drawing on a privacy budget, and account across sessions per counterparty. The natural objection is Sybil identities; the natural answer is to attach budgets to verified organisations rather than agents, which imports an identity requirement the protocol otherwise avoids and excludes the pseudonymous participant the design is partly for.

**Randomised coarsening.** Extend [RANI2026]'s phase-adaptive approach to the coarsening choice: answer truthfully with a probability that varies with position in the session, retreating to `conditionally_compatible` otherwise. Preserves truthfulness by construction, since the fallback asserts nothing false. **Measured, and it does not bound.** Answering a local claim truthfully half the time and coarsening it otherwise holds an adaptive querent to 3.04 bits of 7.94 at a budget of eight claims, where a deterministic policy has already conceded everything — and concedes everything itself by sixteen, because the querent simply re-asks the question that still splits its hypotheses. It also costs thirty-nine points of true-negative rate: a coarsened refusal reads as a maybe, so the session qualifies counterparties it should have turned away. Randomisation buys queries, not a bound, and it buys them with discrimination. A phase-adaptive schedule may buy more of them; it will not change the shape of the result, because the weakness is repetition rather than the constant. Remaining open questions: whether a bound survives when the adversary knows the policy, and whether the resulting session still converges for honest pairs.

**Reciprocity as a cost.** This one is native to CID and, in the author's view, the most promising. Sessions are reciprocal by design: both sides ask, both sides answer. A responder may condition further answers on the querent having answered symmetric claims — the `reciprocal` flag of Section 14.4 already carries the idea for disclosure. Probing then costs the prober information about its own constraints, which changes the economics without any cryptography. The weakness is the adversary with nothing to protect: an attacker probing on behalf of no genuine interest can answer anything, so reciprocity must be combined with something that makes a fabricated Standing Interest costly.

**Economic cost.** Bond, meter or otherwise price querying, and burn the bond on detected abuse. Converts an inference problem into a pricing problem. Two hard parts: the abuse criterion must be evaluable without disclosing session content, which is not obviously possible; and pricing risks excluding the low-volume honest participant while a funded adversary simply pays.

### 5. What would count as progress

A bound, however loose, on leakage under adaptive querying for any non-trivial responder policy satisfying Section 15.5. A proof that no such policy exists above a given utility threshold, which would be equally valuable and would force the protocol to abandon the truthful-oracle design. A first empirical characterisation now exists and is not progress so much as a floor: against the reference implementation's default policy, a competent adversary recovers a valuation threshold to a five-million-euro granularity and a categorical condition exactly, in seventeen claims, which is sixty-five per cent of everything private in the scenario. Progress would be a characterisation, on realistic constraint distributions rather than one worked case, of how many claims a competent adversary needs to locate a threshold to a given precision — which would at least tell implementers what query budgets to set.

---

## Part II — Mechanism mapping

The specification names properties, not mechanisms, deliberately: a protocol that mandates a cryptographic construction ages with it. But a reader is entitled to know that the properties are achievable with things that already exist. Each row below states a requirement of CID 0.1 and the existing mechanism that can satisfy it. None of this is normative, and no implementation is obliged to use any of it.

| CID requirement | Existing mechanism | Status |
|---|---|---|
| Disclose an attribute of a signed credential without disclosing the rest (§10, §20) | SD-JWT selective disclosure | RFC 9901 |
| The same, with unlinkability across presentations | BBS signatures; W3C Data Integrity BBS cryptosuites | IRTF CFRG draft; W3C CRD, Sep 2026 |
| Prove a verified attribute (accreditation, revenue band, authorisation to represent) without identity (§20) | W3C Verifiable Credentials with Data Integrity proofs | W3C Recommendation, May 2025 |
| Evidence an asserted authority level by a referenceable delegation artefact (§16.2) | OAuth 2.0 Token Exchange with actor/delegation chain; attenuated capability tokens (UCAN, Biscuit); agent-specific delegation drafts | RFC 8693; deployed OSS; IETF drafts |
| Persistent agent identity across trust domains (§20) | SPIFFE/WIMSE workload identity; DID; vendor agent identities | Standards and GA products |
| Learn that a revoked Standing Interest's projections must go (§17.1), across parties | Shared signals and continuous access evaluation | OpenID SSF/CAEP |
| Answer a compatibility claim without either side learning the other's set (§24.12) | Private set intersection, where compatibility is set intersection | Mature; readiness evaluated 2026 |
| Retrieve candidates from a provider without the provider learning the query (§12.3) | Private information retrieval | Active research; 2026 survey |
| Prove a threshold is satisfied without revealing threshold or value (§24.12) | Zero-knowledge range proofs; demonstrated for on-device negotiation | Research, 2026 |
| Compute a matching over private preferences (§19, multi-party) | Secure stable matching at scale; privacy-preserving cycle and chain clearing | CCS 2016; SMPC literature 2020–2024 |
| Enforce disclosure policy outside unconstrained model behaviour (§24.10) | Information-flow control applied to LLM agents | Research, 2026 |
| Reduce re-identification risk of a projection (§11.6) | k-anonymity and its descendants, applied to the projection population | Classical |

Two cautions. First, several of these compose badly: a BBS-based unlinkable presentation and a per-counterparty disclosure policy both want to control linkage and may fight. Second, a mechanism's existence is not a deployment: the honest statement is that CID asks for nothing that has not been built, not that an implementer will find these easy to assemble.

---

## Part III — Design rationale

**Why surface × gate rather than a ladder of levels.** Earlier drafts used an ordered list of disclosure levels. It collapsed two independent questions: *where may this attribute appear* and *what must happen before it does*. An attribute can be perfectly publishable in a private registry yet require the Principal's per-instance approval; a ladder forces those into one dimension and produces either too many levels or the wrong ones. Splitting them gives a small closed vocabulary on each axis and makes the local-only classes expressible without a special case.

**Why `evaluation_only` exists.** Without a class that is usable for local evaluation and never transmissible, every constraint that participates in compatibility must eventually be disclosable, and the protocol becomes a staged disclosure mechanism rather than a private one. `evaluation_only` is what makes it possible to answer a claim truthfully about a value the counterparty will never see. It is also, for the same reason, where the leakage of Part I originates: the class is the design's centre and its principal weakness.

**Why there is no cryptography in the core.** The question is fair and the answer is not "it would be too hard". Three reasons, in order of weight.

The leak this protocol has is in the *result*, not in the computation. Private set intersection and secure two-party computation hide a responder's inputs from a querent; neither hides what the output implies, and Section 24.3's threat is a querent that learns a threshold from a sequence of outputs it was entitled to receive. Adding a cryptographic layer would therefore protect the half that is not at risk while leaving the half that is, and — this is the part that decides it — it would advertise a guarantee at exactly the point where none exists. A protocol that says "secure comparison" invites a reader to stop worrying about repeated querying, which is the only thing they should be worrying about.

Second, the measured comparison in the companion document shows what the cryptographic mechanisms actually supply and what they presuppose. An ideal sealed comparison answers one agreed predicate between two parties who have already found each other; it cannot discover a counterparty, cannot agree the predicate without naming the dimensions, and cannot report which dimensions are open rather than a single bit. Those three are the work this protocol does. Cryptography is not a substitute for it and this document is not a substitute for cryptography.

Third, adoption. A discovery layer that requires a pairing library, a trusted setup or a circuit compiler is not implemented by the CRM, the ATS or the corporate development team whose data makes it useful. CID is meant to be implementable over an existing agent transport in an afternoon, and the measured cost of that choice is stated rather than hidden.

None of this forbids composition, and Section 24 already permits it. A deployment worried about what a Discovery Provider observes can retrieve through private information retrieval; a single categorical claim can be resolved by a secret handshake [SECRET-HANDSHAKE] or a set intersection instead of by the responder's own evaluation; a threshold claim can be delegated to a secure comparison. That last possibility is the interesting one and it is not in 0.1: a profile in which a claim's *evaluation* is bound to a cryptographic mechanism, with CID supplying what those mechanisms have no story for — who is authorised to ask, which predicate is worth evaluating, what happens to the answer, and where the human is. Framed that way CID is not an alternative to the cryptographic literature but the governance around it, and an implementation that demonstrated one such claim would be worth more than a chapter of argument.

**Why authority stops before commitment.** Not caution for its own sake. A protocol that can commit needs a legal theory of when the commitment binds, a dispute mechanism and an identity requirement, and each of those would have to be settled before anything could ship. Stopping at the point where a human or another protocol takes over keeps CID's scope small enough to specify, and lets it compose with payment and negotiation protocols rather than competing with them. `COMMIT` exists in the ladder, fixed to `false`, so that the boundary is explicit on the wire rather than implicit in prose.

**Why "interest" and not "intent" or "mandate".** Both were taken, and taken for near-opposite meanings. In the agent ecosystem a *mandate* is a signed proof of authority to commit or pay; in payment protocols and in decentralised finance an *intent* is an active order someone wants executed. A Standing Interest is neither: never transmitted, and asserting no active demand. Using either word would have cost more in confusion than any familiarity it bought.

**Why there is no wire schema in 0.1.** A normative JSON Schema fixes decisions that implementation experience should make — required versus optional, extension points, error taxonomy. Publishing one before a reference implementation exists would produce a schema that is wrong in ways nobody can yet see, and that implementers then have to live with. 0.2 carries it.

**Why the projection is non-invertible by design rather than by proof.** Section 11.6 states non-invertibility as a design objective, not a guarantee, and that is deliberate honesty. Whether a population of projections permits re-identification depends on the population, not on the protocol; the same projection is safe among ten thousand peers and identifying among five. A protocol cannot promise what only a deployment can measure — and measuring it is one of the open engineering questions.

**Why sessions are reciprocal.** An asymmetric protocol, where one side asks and the other answers, is a surveillance instrument with extra steps. Reciprocity is what makes the structure defensible, and as Part I notes, it is also the most promising lever against probing.

---

## Part IV — Open engineering questions

**How does a publisher choose its projection granularity?** Section 11.4 tells an Agent to minimise and does not say when to stop, and measurement shows the advice reverses past a point: a projection coarse enough to be retrieved by every querent costs more in sessions than it saved at the index, while an over-precise one is retrieved less because it only answers querents who used the same vocabulary. The quantity that locates the optimum — how many other publishers this projection will be confused with — is visible to the Discovery Provider and not to the publisher. A provider that reported the size of a matching set would let a publisher calibrate, and would let an adversary calibrate too. Whether there is a form of that signal which helps the first and not the second is open.

**Which budget, and who states it?** A budget keyed to the counterparty bounds nothing against an adversary that mints counterparties; a cap on a responder's total answered claims bounds, and cannot tell an honest counterparty from an adversary while doing so. In the worked case those two populations are not separable by any threshold, because a complete extraction costs seven answered claims and an honest session costs six. Either the protocol carries something that distinguishes them — which means identity, which the design avoids — or deployments ration openly and say so.


These are the questions implementation should answer, restated compactly from Appendix E of the specification. How much of a Standing Interest should be structured rather than natural language, and how should fuzzy conditions be represented? What is the minimum useful projection, and how should projections be indexed without building the searchable database of sensitive interests the protocol exists to avoid? Where should compatibility be evaluated — locally, peer to peer, in a trusted execution environment, under secure computation? How should an Agent prove authority for a specific Standing Interest without disclosing the Principal? How should multi-party dependency discovery avoid combinatorial explosion, and when may a partial coalition be revealed? And the governance question that will be forced early: should CID be an extension of an agent-to-agent protocol, a protocol in its own right, or a reusable application profile?

## Part V — What would falsify this work

Appendix F of the specification states the core hypothesis: that a sufficiently general primitive exists for agents to discover compatibility between private, conditional, unpublished interests, and that it is distinct enough from capability discovery and negotiation to justify interoperable semantics.

The strongest falsification would be a demonstration that each vertical needs a materially different state machine, disclosure model and compatibility model — in which case CID is a useful pattern and not a protocol layer, and should be said to be one. The second would be a showing that the leakage of Part I cannot be bounded at usable utility, which would make the truthful-oracle design untenable regardless of how good the vocabulary is. The third, more mundane and more likely, is that principals turn out not to hold economically meaningful conditional interests they are willing to formalise — that the latent supply is a story rather than a fact.

The author would rather learn any of these from a reviewer in 2026 than from a failed deployment in 2028.

---

## References

Full bibliographic details for every work cited here are in Section 27 of the specification. The references used above are [RANI2026], [RFC9901], [BBS], [VC-DI], [RFC8693], [WIMSE-AI], [PSI-SLR], [PIR-SURVEY], [SSM-CCS16] and [FLOWSEAL].
