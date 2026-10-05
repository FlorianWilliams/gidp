---
title: Graduated Interest Disclosure — Open Problems and Design Rationale
version: 0.1
date: 2026-09-23
status: Non-normative companion to GIDP 0.1
---

# Open Problems and Design Rationale

**Status:** non-normative companion to *Graduated Interest Disclosure Protocol (GIDP) — Draft 0.1*. Nothing here is a requirement. Where this document and the specification disagree, the specification is authoritative.
**Author:** {{AUTHOR}}, Independent. Contact: {{CONTACT}}.
**Canonical location:** {{CANONICAL_URL}}.
**Licence:** CC BY 4.0.
**Date:** 23 September 2026.

This document exists because a specification should state requirements, not argue for unproven solutions. It carries three things that do not belong in the normative text: the mapping from GIDP's requirements to mechanisms that already exist, so that a reader can see the protocol is not asking for new cryptography; the open problem the protocol runs into, stated for people who might solve it; and the reasoning behind choices the specification makes without justifying.

---

## Part I — The open problem

### 1. Why a compatibility oracle leaks

GIDP's compatibility semantics rest on an oracle. One Agent asks whether a claim holds against the other's private constraints; the other answers from the vocabulary of Section 15.1 without disclosing the values behind the answer. Section 15.4 gives the canonical illustration: an Agent privately holding `maximum_valuation = 80M`, asked whether a transaction within `{50M, 100M}` is compatible, answers `conditionally_compatible` and never transmits the threshold.

The threshold is nevertheless learnable. A querent who asks about `{50M, 60M}`, then `{60M, 70M}`, then `{70M, 80M}`, then `{80M, 90M}` and observes the last answer change has located the boundary without a single value crossing the wire. Section 24.3 names this; the point worth stating plainly is that **it is not an implementation defect but a property of any useful oracle**. An oracle that never leaks is an oracle that never discriminates, and an oracle that never discriminates cannot support discovery. The design question is therefore not how to eliminate leakage but how to bound what an adversary can extract per unit of effort, while leaving enough signal for honest counterparties to find each other.

### 2. The problem, stated

Let a responder hold a private constraint set *C*. A querent submits claims adaptively, each chosen in light of every answer so far. The responder answers under the truthfulness rule of Section 15.5: the truthful result, a coarsening of it (`conditionally_compatible` or `unknown`), or `declined` — never an answer its values contradict.

A mechanism is a responder policy, possibly randomised. **Leakage** is what an adaptive querent learns about *C* after *k* claims. **Utility** is the probability that two genuinely compatible Principals reach `potentially_compatible` within a bounded number of claims.

*Exhibit a policy, or prove none exists, that bounds leakage under adaptive querying while keeping utility above a usable threshold.*

Three features distinguish this from cases that are solved. The adversary **chooses** its queries rather than observing a trace. The responder must remain **truthful** in the above sense rather than free to lie — a constraint imposed by the protocol's purpose, since a peer that may assert falsehoods cannot be relied on for anything. And the bound must hold **across sessions and identities**, because an adversary can split its query budget over many counterparties it controls (Section 24.4).

### 3. What the neighbouring literature does and does not settle

[RANI2026] formalises behavioural privacy leakage in agentic negotiation and mitigates it with a phase-adaptive randomised policy achieving (ε,δ)-differential privacy with almost-sure convergence, reducing adversarial inference accuracy by 43–50 % while preserving utility. Its adversary is **passive**: it trains predictors on observed negotiation traces. The paper states that adaptive adversaries are future work. That is exactly our adversary.

Differentially private query mechanisms bound leakage under adaptive querying, which is their standard threat model, but they assume the mechanism may return a perturbed answer. GIDP's truthfulness rule forbids perturbation that asserts a falsehood. The two are reconcilable only in one direction: the responder may always retreat to `conditionally_compatible`, `unknown` or `declined`, so randomisation is available over the *coarsening* choice but not over the substantive answer. Whether that restricted randomisation is sufficient to obtain a meaningful bound is, as far as the author can establish, unstudied.

Private set intersection, secure multi-party computation and zero-knowledge range proofs hide the responder's inputs. They do not hide what the *result* reveals, and the result is the leak. A protocol that computes compatibility under MPC and returns `compatible` has leaked exactly as much as one that computes it locally and returns `compatible`. This is worth stating because "just use PSI" is the most common first reaction, and it addresses a different threat.

### 4. Candidate directions, none validated

These are offered so that a reader can attack them, not because any is believed to work. Three of the five have since been measured against an adaptive querent, and the measurements are in the companion document *Why not use an existing mechanism?*; where a direction has been tested, the result is stated with it rather than left for the reader to find.

**Simulatable answering — now implemented, and the open problem is narrower for it.** *Update.* The direction below was written as a constraint with no mechanism attached. It has one. A responder that budgets in bits rather than in claims, and decides each refusal from the worst case over the answers it might give, bounds an adaptive querent without identity, without an operator and without anything carried between sessions. What remains open is the utility half, which is where the original statement put the difficulty and where it still is: the bound costs honest counterparties that ask narrow questions, and whether a policy exists that achieves the same bound while serving more of them is not answered here. The problem has moved from *is there a bound* to *what is the best bound-utility frontier*, which is a better problem to have.

**Simulatable answering.** *The one direction here with a pedigree rather than an invention, and it arrived late.* [KMN2005] shows that in query auditing a denial leaks whenever the decision to deny consults the data, and repairs it by requiring the decision to depend only on the queries asked and the answers already given — so that an attacker can reproduce the decision and learns nothing from it. Applied here it is a constraint rather than a mechanism, and a sharp one: no rule for coarsening or declining may consult the responder's own values. That disqualifies the coarsening of Section 15.4 outright, explains why it measured identically to answering plainly, and leaves exactly the family of policies that key off the claim sequence — of which a query budget is the simplest member. What it does *not* do is bound what the answers themselves reveal, which is the harder half of the problem and remains open. The same literature reports the general auditing problem to be NP-hard, which is a reason to expect deployment-specific auditors rather than a universal one.

**A rate rather than a total, against a moving value.** *Measured, and weaker than it sounds.* A refilling budget does not separate an adversary from a customer — the adversary empties the bucket just as fast, and the window between them is the one computed in `impl/baselines/separability.py`. What it changes is that extraction takes time, and a value revised over that time is a moving target. The residue settles at about `2d / (2^r − 1)` candidates, exponential in the rate allowed and linear in the movement, so at one claim per period and a drift of four steps a five-bit secret keeps three bits, while at four claims per period it keeps none whatever the drift. The direction worth noting is the other one: an adversary that does not model the movement narrows onto stale answers and finishes confident and wrong rather than uncertain. Neither effect is something to rely on, and both are deployment choices rather than protocol ones.

**Minimum granularity.** *Measured, and the earlier dismissal of it was wrong.* Require every claim's bounds to fall on a lattice of profile-defined width. The first version of this entry said it bounds a single probe and not what repeated probing yields; that is false, and the reason is the same detail that makes a bound probeable at all. A private bound is tested at the *edge* of whatever band is asked, so constraining a band's width achieves nothing — the edge is wherever the querent puts it — but constraining where edges may fall caps the resolution outright, at `log2(range / width)`, however many questions are asked.

Two properties make it the most practical entry in this list. It holds **no state**: honest traffic does not deplete it and an adversary cannot drain it, which is exactly the failure mode of every budget. And it needs no identity, no operator and no memory of who asked. On the frontier measured in `impl/baselines/frontier.py` it is the only policy that bounds while serving *every* honest counterparty — a 40M lattice over a 200M band holds a prober to 2.36 of 5.36 bits with forty counterparties out of forty answered, where a two-bit budget holds it to 0.97 and refuses five of them.

The cost is real and is not a refusal: a customer must round its question to the lattice, so it loses precision rather than service. Which of the two costs a deployment prefers is a deployment question, and combining them — a lattice for the hard cap, a budget beneath it — is a third point on the frontier rather than a strict improvement on either.

**Budgets with accounting.** *The only direction here that bounded anything under measurement, and the one whose objection is hardest.* Treat each session as drawing on a privacy budget, and account across sessions per counterparty. The natural objection is Sybil identities; the natural answer is to attach budgets to verified organisations rather than agents, which imports an identity requirement the protocol otherwise avoids and excludes the pseudonymous participant the design is partly for.

**Randomised coarsening.** Extend [RANI2026]'s phase-adaptive approach to the coarsening choice: answer truthfully with a probability that varies with position in the session, retreating to `conditionally_compatible` otherwise. Preserves truthfulness by construction, since the fallback asserts nothing false. **Measured, and it does not bound.** Answering a local claim truthfully half the time and coarsening it otherwise holds an adaptive querent to 3.04 bits of 7.94 at a budget of eight claims, where a deterministic policy has already conceded everything — and concedes everything itself by sixteen, because the querent simply re-asks the question that still splits its hypotheses. It also costs thirty-nine points of true-negative rate: a coarsened refusal reads as a maybe, so the session qualifies counterparties it should have turned away. Randomisation buys queries, not a bound, and it buys them with discrimination. A phase-adaptive schedule may buy more of them; it will not change the shape of the result, because the weakness is repetition rather than the constant. Remaining open questions: whether a bound survives when the adversary knows the policy, and whether the resulting session still converges for honest pairs.

**Reciprocity as a cost.** This one is native to GIDP and, in the author's view, the most promising. Sessions are reciprocal by design: both sides ask, both sides answer. A responder may condition further answers on the querent having answered symmetric claims — the `reciprocal` flag of Section 14.4 already carries the idea for disclosure. Probing then costs the prober information about its own constraints, which changes the economics without any cryptography. The weakness is the adversary with nothing to protect: an attacker probing on behalf of no genuine interest can answer anything, so reciprocity must be combined with something that makes a fabricated Standing Interest costly.

**Economic cost.** Bond, meter or otherwise price querying, and burn the bond on detected abuse. Converts an inference problem into a pricing problem. Two hard parts: the abuse criterion must be evaluable without disclosing session content, which is not obviously possible; and pricing risks excluding the low-volume honest participant while a funded adversary simply pays.

### 5. What would count as progress

A bound, however loose, on leakage under adaptive querying for any non-trivial responder policy satisfying Section 15.5. A proof that no such policy exists above a given utility threshold, which would be equally valuable and would force the protocol to abandon the truthful-oracle design. A first empirical characterisation now exists and is not progress so much as a floor: against the reference implementation's default policy, a competent adversary recovers a valuation threshold to a five-million-euro granularity and a categorical condition exactly, in seventeen claims, which is sixty-five per cent of everything private in the scenario. Progress would be a characterisation, on realistic constraint distributions rather than one worked case, of how many claims a competent adversary needs to locate a threshold to a given precision — which would at least tell implementers what query budgets to set.

---

## Part II — Mechanism mapping

The specification names properties, not mechanisms, deliberately: a protocol that mandates a cryptographic construction ages with it. But a reader is entitled to know that the properties are achievable with things that already exist. Each row below states a requirement of GIDP 0.1 and the existing mechanism that can satisfy it. None of this is normative, and no implementation is obliged to use any of it.

| GIDP requirement | Existing mechanism | Status |
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

Two cautions. First, several of these compose badly: a BBS-based unlinkable presentation and a per-counterparty disclosure policy both want to control linkage and may fight. Second, a mechanism's existence is not a deployment: the honest statement is that GIDP asks for nothing that has not been built, not that an implementer will find these easy to assemble.

---

## Part III — Design rationale

**Why surface × gate rather than a ladder of levels.** Earlier drafts used an ordered list of disclosure levels. It collapsed two independent questions: *where may this attribute appear* and *what must happen before it does*. An attribute can be perfectly publishable in a private registry yet require the Principal's per-instance approval; a ladder forces those into one dimension and produces either too many levels or the wrong ones. Splitting them gives a small closed vocabulary on each axis and makes the local-only classes expressible without a special case.

**Why `evaluation_only` exists.** Without a class that is usable for local evaluation and never transmissible, every constraint that participates in compatibility must eventually be disclosable, and the protocol becomes a staged disclosure mechanism rather than a private one. `evaluation_only` is what makes it possible to answer a claim truthfully about a value the counterparty will never see. It is also, for the same reason, where the leakage of Part I originates: the class is the design's centre and its principal weakness.

**Why there is no cryptography in the core.** The question is fair and the answer is not "it would be too hard". Three reasons, in order of weight.

The leak this protocol has is in the *result*, not in the computation. Private set intersection and secure two-party computation hide a responder's inputs from a querent; neither hides what the output implies, and Section 24.3's threat is a querent that learns a threshold from a sequence of outputs it was entitled to receive. Adding a cryptographic layer would therefore protect the half that is not at risk while leaving the half that is, and — this is the part that decides it — it would advertise a guarantee at exactly the point where none exists. A protocol that says "secure comparison" invites a reader to stop worrying about repeated querying, which is the only thing they should be worrying about.

Second, the measured comparison in the companion document shows what the cryptographic mechanisms actually supply and what they presuppose. An ideal sealed comparison answers one agreed predicate between two parties who have already found each other; it cannot discover a counterparty, cannot agree the predicate without naming the dimensions, and cannot report which dimensions are open rather than a single bit. Those three are the work this protocol does. Cryptography is not a substitute for it and this document is not a substitute for cryptography.

Third, adoption. A discovery layer that requires a pairing library, a trusted setup or a circuit compiler is not implemented by the CRM, the ATS or the corporate development team whose data makes it useful. GIDP is meant to be implementable over an existing agent transport in an afternoon, and the measured cost of that choice is stated rather than hidden.

None of this forbids composition, and Section 24 already permits it. A deployment worried about what a Discovery Provider observes can retrieve through private information retrieval; a single categorical claim can be resolved by a secret handshake [SECRET-HANDSHAKE] or a set intersection instead of by the responder's own evaluation; a threshold claim can be delegated to a secure comparison. That last possibility is the interesting one and it is not in 0.1: a profile in which a claim's *evaluation* is bound to a cryptographic mechanism, with GIDP supplying what those mechanisms have no story for — who is authorised to ask, which predicate is worth evaluating, what happens to the answer, and where the human is. Framed that way GIDP is not an alternative to the cryptographic literature but the governance around it, and an implementation that demonstrated one such claim would be worth more than a chapter of argument.

**Why authority stops before commitment.** Not caution for its own sake. A protocol that can commit needs a legal theory of when the commitment binds, a dispute mechanism and an identity requirement, and each of those would have to be settled before anything could ship. Stopping at the point where a human or another protocol takes over keeps GIDP's scope small enough to specify, and lets it compose with payment and negotiation protocols rather than competing with them. `COMMIT` exists in the ladder, fixed to `false`, so that the boundary is explicit on the wire rather than implicit in prose.

**Why "interest" and not "intent" or "mandate".** Both were taken, and taken for near-opposite meanings. In the agent ecosystem a *mandate* is a signed proof of authority to commit or pay; in payment protocols and in decentralised finance an *intent* is an active order someone wants executed. A Standing Interest is neither: never transmitted, and asserting no active demand. Using either word would have cost more in confusion than any familiarity it bought.

**Why there is no wire schema in 0.1.** A normative JSON Schema fixes decisions that implementation experience should make — required versus optional, extension points, error taxonomy. Publishing one before a reference implementation exists would produce a schema that is wrong in ways nobody can yet see, and that implementers then have to live with. 0.2 carries it.

**Why the projection is non-invertible by design rather than by proof.** Section 11.6 states non-invertibility as a design objective, not a guarantee, and that is deliberate honesty. Whether a population of projections permits re-identification depends on the population, not on the protocol; the same projection is safe among ten thousand peers and identifying among five. A protocol cannot promise what only a deployment can measure — and measuring it is one of the open engineering questions.

**Why sessions are reciprocal.** An asymmetric protocol, where one side asks and the other answers, is a surveillance instrument with extra steps. Reciprocity is what makes the structure defensible, and as Part I notes, it is also the most promising lever against probing.

---

## Part IV — Open engineering questions

**How does a publisher choose its projection granularity?** Section 11.4 tells an Agent to minimise and does not say when to stop, and measurement shows the advice reverses past a point: a projection coarse enough to be retrieved by every querent costs more in sessions than it saved at the index, while an over-precise one is retrieved less because it only answers querents who used the same vocabulary. The quantity that locates the optimum — how many other publishers this projection will be confused with — is visible to the Discovery Provider and not to the publisher. A provider that reported the size of a matching set would let a publisher calibrate, and would let an adversary calibrate too. Whether there is a form of that signal which helps the first and not the second is open.

**Which budget, and who states it?** The first half of this question is answered, and the answer changed its unit. A budget counted in claims cannot separate an honest counterparty from a probing one, because an honest wide question costs a fraction of a bit and a bisecting one a full bit by construction; a budget counted in information can, and deciding it from the worst case over possible answers keeps each refusal independent of the protected value (specification, Section 24.3). Three things remain open. Whether the frontier between the leakage bound and the number of honest counterparties served, measured so far by sweeping policies, is optimal — the question is a linear programme over a finite domain and can be settled by solving it rather than by sampling. Whether a budget kept per Standing Interest composes across attributes that are correlated with one another, since a bound on each attribute is not a bound on the principal they jointly identify. And the budget's other face: a global budget is a commons, and an adversary who cannot extract the secret can still spend the budget and deny service to honest counterparties. The secret is kept; availability is not, and a deployment should say which it prefers.


### Raised by the first external review (25 September 2026)

The review found four contradictions and an ambiguity, corrected before publication (`impl/SPEC-ISSUES.md`, S-22 to S-26). What follows is what it raised that is not a contradiction: questions a second implementation will meet, recorded with the position 0.1 takes so that the position can be challenged.

**Audiences are not only sizes (review T07).** The surfaces of Section 10.1 are totally ordered, but a trust domain and an authenticated session peer are different sets of recipients, not a larger and a smaller one. 0.1's position: a `network` restriction continues to apply inside a session, and a session's `max_depth` confers no network membership. Open: whether `network/consent` is meaningful at all when the consent of Section 14.5 is scoped to a session and a projection is addressed to a registry; a profile may need a publication-approval mechanism, or the combination should be reserved to sessions.

**A value is a fact, a preference or a set of acceptable configurations (T08).** "Germany" held by a responder may mean it does not know which city, or that every German city is acceptable. Section 14.2's hierarchy rule answers `unknown` to "Munich" in both cases, which is right for the first and needlessly cautious for the second. 0.1 does not distinguish them; a profile used for interoperability must say, for each attribute, which of the three it is, and define keys, types, units, bounds and predicates. Whether the core should carry that distinction is open.

**Authority, evidence and anonymity (T09).** An authority level set to `false` is a refusal, not an approval pending; and the levels of Section 16.1 are distinct permissions rather than a ladder in which a higher level implies the lower ones — both are 0.1's reading and should be stated more plainly in the text. Open: what a delegation proof reveals, to whom and through which exchange, when the protocol also seeks exploration without identity. Four properties are easily conflated and are not the same — the truth of a local evaluation, the authenticity of an Agent, the Principal's authorisation, and the sincerity of an economic interest — and conformance to this document attests none of the last three.

**Reciprocity is a condition, not a fair exchange (T10).** Two `granted_if_reciprocal` responses can expire without an exchange, and the first side to release can then receive a close. 0.1 describes a condition and a deadline; it does not provide atomic or fair exchange and must not be read as providing it. A profile that needs a stronger guarantee must bring a mechanism — a trusted third party or a fair-exchange protocol — and say so.

**Conventions a binding must own (T11).** Each of these is legitimately left to a binding, and each needs a named owner: how an endpoint representing several interests routes a session to the one a projection advertised, without exposing it; how several Conditional Interests in one Standing Interest combine — alternatives, conjunctions, shared conditions; one rule for the lifetime of a session and of an active consent, and for late responses; deduplication and idempotence, since one logical response is not one network delivery; which results and consents lapse when a Standing Interest is superseded mid-session (Section 17.1); what systems a stated retention covers — copies, logs, downstream systems; which components are inside a deployment's trust boundary when an Agent uses a remote model, memory, tools or observability; how a credential named in `verification_required` is supplied; and whether `features` should distinguish what is offered from what is required.

**Scope choices stated too absolutely (T12).** Section 11.1 forbids a `relation` value that reveals the direction of a transaction; as a maximum-discretion default that is defensible, as a universal rule it denies a Principal the choice to reveal direction for better retrieval, and it does not stop direction being inferred from another attribute. Section 23.2 asks the four interest classes of Section 8 to produce the same sequence of objects; horizontality is better tested on invariants — the same disclosure, authority and session rules — than on identical traces, since domains legitimately ask different questions in different orders. The boundary with negotiation needs one more sentence: describing a candidate scenario to test its feasibility is not making an offer, and the non-binding scope of the `structure` an Opportunity carries should be stated rather than inferred from the object's name. And the exclusions of Section 5 would read better sorted into three kinds: out of scope, not supported by the current profile, and probably unprofitable. None of these is legal advice.

**Testing flow control outside the model (T06).** Section 6.10 places policy enforcement outside the model; the conformance test of Section 23.2 checks reproducibility, and a leak can be perfectly reproducible. A stronger test varies one `never` attribute and checks that no covered output changes, and for `evaluation_only` checks that only explicitly permitted declassifications occur — including through the choice of questions, free text and side outputs, since two individually permitted messages can encode a secret by which one is chosen. Such tests raise confidence without proving absence. The reference implementation has the first half — a claim on a `never` attribute is declined and a `never` dependency leaves no trace — and not yet the variation test.

### The 0.2 programme, from the second review (28 September 2026)

The second review confirmed the first round of corrections, found six more defects — applied to 0.1, `impl/SPEC-ISSUES.md` S-27 to S-32 — and proposed the structural work that should not be done by patching. Recorded here as the shape of 0.2, in the reviewer's priority order, with which we concur:

**Separate what one state currently encodes.** A session has a phase (opening, exploring, qualified, handed off, closed), a set of pending requests, and a set of granted consents; the current machine encodes all three in one state, and the `_RETURN` bookkeeping of Section 17.2 is the patch that proves it. Each event should state separately its effect on the phase, the pending set, the consent set and the evaluation.

**Make qualification bilateral over a named result.** 0.1's minimal fix (S-32) lets the responder's contingencies reach the Opportunity; the full mechanism is an accepted summary — each side contributes its communicable results and contingencies, one summary is proposed with a revision reference, both accept it, the Opportunity cites it. Acceptance means the summary suffices for the next step; it is neither consent to identity nor commitment.

**One narrow profile, fully typed.** For each attribute: fact, preference or acceptable set; type, unit, temporality; interval and set semantics; permitted operators; the meaning of absence; the minimum claims a session must have asked before its Opportunities qualify — including a joint predicate where dimension-by-dimension tests mislead (Section 14.6).

**A privacy perimeter beyond one process.** 0.1 states the persistence requirements (Section 24.3); 0.2 owes their realisation — durable ledgers, replica coordination, derived attributes through the same control — and an explicit account of the LLM's controlled outputs: chosen questions, free text and tool calls, not only disclosed values. Structured codes for reasons and requests narrow the channels that resist control.

**A conformance corpus that does not import the reference classes.** Messages plus permitted initial state in, permitted and forbidden responses and effects out. Priority scenarios: consent before qualification; a dependency known only to the responder; revocation during an approval; the same message twice; a response after expiry; concurrent questions; restart; a nearly spent budget under two concurrent requests.

The test the whole programme answers to: someone who did not design GIDP implements a profile, passes the scenarios and explains their decisions from the published documents alone.

### From the first fresh reading (28 September 2026)

A second reviewer, reading 0.1 with no history, confirmed the 0.2 programme from the outside — the state machine's overloads, the typed profile, the external conformance corpus, the second implementation — and added questions the programme should absorb:

**Reciprocity needs operational semantics.** Two `granted_if_reciprocal` responses deadlock if both wait; if one releases first, the other can stop. The core must say who begins, what satisfies the condition, and how the wait ends — or say plainly that it offers sequential exchange with assumed risk for the first revealer, and leave fairness to a profile mechanism.

**A permission matrix rather than an implicit scale.** Audience, exchange context, permitted operation (evaluate vs transmit) and required approval are four dimensions; the surface ladder encodes them in one. 0.1 patches the worst conflicts (Sections 14.1, 16.3); 0.2 should consider making the matrix explicit, even keeping the current names.

**Requests are disclosures too.** The chosen attribute, the sequence of thresholds, `purpose`, `next.requires`, `Opportunity.structure` — each can be derived from a secret without containing its value. Output control should be symmetric across requests, responses and notifications, and should say which derivations of private data are permitted, not only that raw values must not appear.

**The budget's knowledge model.** A set of candidate values is not a probability distribution, and "bits learned" names several different measures; correlations across attributes, external knowledge (projections, prior disclosures, public data) and the register's scope — the same secret held by several Standing Interests that are not replicas of one object — all remain outside the current model. The honest next step is the narrow experimental profile: one numeric threshold, restricted operators, and a precise statement of what is bounded.

**What a consent authorises, per action.** A scope of attribute keys fits a disclosure; a transfer needs more: the receiving system beyond a target reference, the set of information carried, a duration or terminating event. 0.1 binds a `handoff` consent to its named target and no further; 0.2 should give each action its own consent content, and a transfer consent should reference the exact proposed transfer it approves.

**A visible trust boundary.** The peer cannot verify that announced constraints are the Principal's, that evaluation is correct, that secrets are protected or that stated retention is honoured — normal for a protocol, but worth one short table: per actor (honest agent, malicious agent, curious provider, malicious provider, model host, intermediary, handoff recipient), what the recipient verifies, what the local implementation ensures, and what rests on trust in the operator. A delegation proof shows authorisation; it shows neither sincerity nor truth.

**What a stated anonymity choice forbids, and for whom.** Forbidding identity before qualification and direction in `relation` is the maximum-discretion profile's policy; a Principal who wants to reveal that it is a buyer while hiding its ceiling, or its name while hiding its conditions, is not thereby outside controlled disclosure. 0.2 should separate the limits of the anonymous profile from the limits of the architecture.

These are the questions implementation should answer, restated compactly from Appendix E of the specification. How much of a Standing Interest should be structured rather than natural language, and how should fuzzy conditions be represented? What is the minimum useful projection, and how should projections be indexed without building the searchable database of sensitive interests the protocol exists to avoid? Where should compatibility be evaluated — locally, peer to peer, in a trusted execution environment, under secure computation? How should an Agent prove authority for a specific Standing Interest without disclosing the Principal? How should multi-party dependency discovery avoid combinatorial explosion, and when may a partial coalition be revealed? And the governance question that will be forced early: should GIDP be an extension of an agent-to-agent protocol, a protocol in its own right, or a reusable application profile?

### From the first independent implementation (October 2026)

The test the 0.2 programme set itself — someone who did not design GIDP implements a profile, passes the scenarios and explains their decisions from the published documents alone — was run once. An implementer with no access to the reference code or to this document wrote a TypeScript implementation of the bilateral core and of the co-investment profile from the specification, the schemas and the profile format, keeping a journal in which every decision the text did not determine was recorded, with its citation, before it was made; it then ran the blind corpus once, without expected outcomes. Compared afterwards with the full corpus, the blind pass met 77 of 80 expectations, and none of the three misses was a misreading of the specification: two were corpus defects, one a corpus expectation stronger than the text. The run also found two defects in the reference implementation and ten in the corpus, the schemas, the profile format and its instance, all since corrected (`impl/SPEC-ISSUES.md`, E-01 to E-12). Its journal recorded 21 decisions; those that are gaps in the specification rather than legitimate implementer choices are below, with the reading the implementer took, so that 0.2 can confirm or overturn it.

**What may `reveal_identity` name?** Section 10.6 forbids an identity attribute under any other action; it does not say whether `reveal_identity` may name an attribute that is not an identity, and the core has no complete catalogue of identifying keys. The implementer first refused such a request, then withdrew the refusal as unsupported by the text. 0.2 should say whether the scope of `reveal_identity` is restricted to identifying attributes — a profile declares them (`identifying` in the manifest format) — and what a request naming another attribute is answered.

**Is a `SessionOpen` held under PROBE `approval_required`?** Section 16.3's decision order applies to any request received; its PROBE explanation speaks only of claims. Holding the open until the Principal decides and accepting it at once are both readable. The implementer held it. 0.2 should say which.

**Who sets a session's lifetime?** `expires_at` is on every object, but no text says whether the value on `SessionOpen` bounds the response to it or the session, whether `SessionAccept` may shorten or extend it, or what later messages do to it. The implementer took the minimum of the two. Section 17.2's "expiry of the session" needs a defined source.

**Concordance of an Opportunity that adds contingencies.** Section 14.6 requires the responder to close on an Opportunity that does not match its evaluation; an initiator may also add contingencies of its own that the responder learns for the first time from the Opportunity. The implementer read "match" as inclusion of everything the responder knew, additions allowed. This is the accepted-summary question again (above), met from the other side: until the summary exists, 0.2 should state the inclusion rule.

**Partial consent.** `granted_scope` may be narrower than requested; the text says nothing about how a responder chooses the narrowing, nor whether a request mixing attributes that need a Principal decision with attributes that do not is answered in parts. The implementer narrowed to the authorisable attributes and held the rest for the Principal.

**The status refresh.** Section 14.6 says plainly that 0.1 has no status-refresh message; the implementer met the consequence — an initiator whose view qualifies waits for a response that happens to carry the responder's positive report — and independently re-derived the rule the 0.2 session-model draft adopts (the initiator's transition, kept status and emission are one event, gated on the responder's last report), without having seen the draft. The convergence is evidence for the rule; the missing refresh remains a cost of 0.1, paid in an extra round trip.

**Budgets need a model, not a number.** The profile's bit budgets could not be computed without a hypothesis space and a prior, and the implementer refused budgeted claims rather than guess one. The profile format now requires both (`profiles/FORMAT.md`), which settles interoperability of the computation; whether the uniform prior over a lattice is the right model remains the open question of Part IV.

## Part V — What would falsify this work

Appendix F of the specification states the core hypothesis: that a sufficiently general primitive exists for agents to discover compatibility between private, conditional, unpublished interests, and that it is distinct enough from capability discovery and negotiation to justify interoperable semantics.

The strongest falsification would be a demonstration that each vertical needs a materially different state machine, disclosure model and compatibility model — in which case GIDP is a useful pattern and not a protocol layer, and should be said to be one. The second would be a showing that the leakage of Part I cannot be bounded at usable utility, which would make the truthful-oracle design untenable regardless of how good the vocabulary is. The third, more mundane and more likely, is that principals turn out not to hold economically meaningful conditional interests they are willing to formalise — that the latent supply is a story rather than a fact.

The author would rather learn any of these from a reviewer in 2026 than from a failed deployment in 2028.

---

## References

Full bibliographic details for every work cited here are in Section 27 of the specification. The references used above are [RANI2026], [RFC9901], [BBS], [VC-DI], [RFC8693], [WIMSE-AI], [PSI-SLR], [PIR-SURVEY], [SSM-CCS16] and [FLOWSEAL].
