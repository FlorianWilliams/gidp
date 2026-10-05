---
title: Graduated Interest Disclosure Protocol (GIDP)
version: 0.1
date: 2026-09-28
status: Experimental — Early Draft / Request for Comments
category: Experimental
---

# Graduated Interest Disclosure Protocol (GIDP) — Draft 0.1

**Status of this document:** experimental, early draft, request for comments. This document is not an Internet-Draft, has not been submitted to any standards body, and claims no endorsement. It follows the structure and editorial conventions of IETF Internet-Drafts ([RFC7322] style; BCP 14 requirement language; separate Security, Privacy and IANA Considerations; normative and informative references) so that it can be converted into one if the work warrants it.
**Category:** Experimental.
**Version:** 0.1. This is the first public draft. It consolidates three earlier internal drafts and incorporates the results of two independent adversarial reviews of the consolidated text and of seven external review passes by three independent reviewers, each reading the specification without the reference implementation. All of these reviews were carried out by large language models, each given the text without its drafting history; human review begins with this publication.
**Date:** 28 September 2026.
**Author / editor:** Florian Williams, Independent. Contact: contact@gidp.dev.
**Canonical location:** https://gidp.dev. Comments, objections and implementation reports are welcome; see Appendix E (Open Questions and Request for Comments).
**Licence:** this document is published under the Creative Commons Attribution 4.0 International licence (CC BY 4.0). The reference implementation published alongside it is licensed under the Apache License 2.0. The author is aware of no intellectual property rights covering the mechanisms described here and has filed none.
**Intended audience:** agent-platform developers, protocol designers, identity and privacy infrastructure providers, marketplace operators, enterprise software vendors, mechanism-design and privacy researchers.

---

## Abstract

AI agents can increasingly access tools, communicate with other agents, advertise capabilities, execute tasks, hold delegated authority and participate in multi-step workflows. A distinct problem remains when the information required to discover a valuable interaction is itself private and should not be advertised.

A principal may not be actively seeking an outcome, yet may be willing to consider it under specific conditions. An organisation may seek an acquisition, partner, supplier, investor, employee or asset without wishing to reveal the search, its constraints, its identity or its reservation values. A principal may be willing to provide something without publicly offering it. In all these cases, publishing enough information to be found may reveal the very fact the principal wants to keep private.

The Graduated Interest Disclosure Protocol (GIDP) defines a common model for representing such **Conditional Interests** inside a **Standing Interest**, deriving privacy-preserving **Discovery Projections**, retrieving candidate counterparties, evaluating compatibility progressively inside bounded **Compatibility Sessions**, controlling disclosure through explicit **Disclosure Policies**, obtaining **Consent**, and handing qualified **Opportunities** to humans or downstream negotiation systems.

GIDP is a discovery and compatibility layer. It is intended to operate above agent-to-agent communication protocols and alongside identity, authority, payment and negotiation protocols, without replacing them. GIDP 0.1 describes a bilateral core (objects, message semantics, disclosure classes, authority levels and state machines) without yet fixing a normative wire schema, and reserves data-model primitives for multi-party discovery, which remains experimental and non-normative in this version.

---

## Table of Contents

1. Introduction
2. Conventions and Requirements Language
3. Terminology
4. Problem Statement and Scope
5. Non-Goals
6. Design Principles
7. Conceptual Model
8. Conditional Interest Model
9. Standing Interest
10. Disclosure Policy
11. Discovery Projection
12. Discovery Providers and Candidate Retrieval
13. Protocol Flow
14. Protocol Objects
15. Compatibility Semantics and Result Vocabulary
16. Authority Model
17. Lifecycle and State Machines
18. Error and Non-Disclosure Semantics
19. Dependency Primitives and Multi-Party Discovery (Experimental)
20. Trust, Credentials and Reputation
21. Extensions and Domain Profiles
22. Transport Bindings and Adjacent Layers
23. Interoperability and Conformance
24. Security Considerations
25. Privacy Considerations
26. IANA Considerations
27. References
Appendix A — Minimal Conceptual Schema (non-normative)
Appendix B — Logical Interfaces (non-normative)
Appendix C — Worked Examples (non-normative)
Appendix D — Why GIDP Is Not Capability Discovery (non-normative)
Appendix E — Open Questions and Request for Comments
Appendix F — Standardisation Strategy and Evaluation Criteria
Appendix G — Acknowledgements

---

## 1. Introduction

Most digital discovery systems assume that at least one side of a potential interaction publishes an explicit intent: job listings, candidate profiles, published acquisition criteria, properties for sale, requests for proposals, investment theses, supplier catalogues, professional service listings and, more recently, agent capability registries.

Economically meaningful interests frequently remain unpublished. A senior executive may not be looking for another position but would consider a specific role under private governance, compensation, sector and geographic conditions. A company may not be for sale but would consider an acquisition above a private threshold and subject to management-continuity conditions. A buyer may want to acquire certain businesses without disclosing its strategy, budget or identity. A company may consider licensing a technology, changing suppliers, forming a joint venture or entering a market only if several private constraints are simultaneously satisfied.

What these interests have in common is that they are latent rather than absent. The executive is not on the market, the company is not for sale, the buyer has announced no strategy, and yet each would move if the right counterparty appeared under the right conditions. *Latent* here means held by the principal and stated to its own Agent, but not published; it never means a preference an Agent has inferred and its principal has not adopted (Section 9.4). Such interests are numerous, and almost none of them are discoverable today. Confidential channels exist (closed venues, trusted intermediaries, the mechanisms of Section 1.1), but each is a separate venue with its own operator and its own rules. Outside them, the way to be found is to announce, and announcing is what the principal cannot afford: it costs standing, bargaining position, confidentiality towards employees, partners or markets, and sometimes the option itself. Interactions that fail to happen for this reason were wanted by at least one party, and are lost because that wish could not be stated safely.

These cases share one structure:

> A principal has a state transition it may be willing to consider, subject to conditions, and does not wish to publish all or part of that willingness.

The discovery problem is circular: a counterparty cannot find such an interest without information about it, and publishing enough to be findable may reveal the very information the principal wants to keep private. Hiding an interest is easy, and it is the present state of affairs. This document addresses the other half of the problem:

> How can Agents acting under delegated authority discover and qualify possible interactions between parties whose interests are not necessarily announced, while limiting what each exchange reveals to what has been authorised for the next step, and making explicit the inferences those exchanges permit?

"I would accept X under conditions C" is, on its own, too general to define a problem: it describes every negotiation ever held. What makes the cases above a class of their own is a conjunction of properties: the interest is not necessarily announced, to the public or to the counterparty; the information needed to qualify it is distributed between the parties, so that neither can decide alone; premature disclosure has a cost that does not depend on whether a transaction follows; and the Agent may explore within limits without being able to reveal, or to commit, the rest. GIDP is a set of shared conventions for that conjunction. Neighbouring systems may well be able to represent it; GIDP claims only that a common semantics for it is worth having, and states that claim as a hypothesis to be falsified (Appendix F).

Four distinct things may be protected in such an exploration: the precise values a principal holds (a threshold, a price, a date); the principal's identity; the link between an identity and an interest, which is often the most sensitive of the three; and the inferences an observer can draw from the pattern of exchanges even when no value is ever stated. This document treats them separately. A deployment can protect the first three well and still carry a documented, bounded leak on the fourth (Section 24.3). A reader who does not distinguish them will mistake a measurement in this text for a guarantee.

This document is published beside `open-problems.md`, and a reader who intends to challenge its choices should read the two together. The design questions 0.1 knowingly defers (separating the session's phase from its pending requests, a bilaterally accepted summary before emission, a permission matrix in place of the surface ladder, typed attribute meanings, the composition of information budgets) are recorded there, each with the position taken and what would change it. Where this document states a limit, the limit is usually a decision recorded there with its reasoning.

GIDP separates four concepts that are often conflated: a **Principal** whose interests are represented; an **Agent** acting under delegated authority; a **Standing Interest** containing conditional interests, constraints, disclosure rules and authority; and a **Discovery Projection**, a deliberately reduced representation that makes a Standing Interest discoverable without publishing it.

Private matching can be built inside one application. The central design question of this draft is whether the same small set of primitives can support private conditional discovery across materially different domains and independently operated agents. Draft 0.1 is written to make that question testable (Appendix F).

### 1.1 Relationship to prior work (informative)

GIDP is not the first attempt to let two parties find each other without either revealing what it wants. What follows sets out the systems it descends from, so that a reader can judge what, if anything, is left unsolved. Whether the remaining gap warrants a protocol is stated in Appendix F as a hypothesis to be falsified.

**Double-blind matching.** The core idea is four decades old, and part of it has a cryptographic treatment: a *secret handshake* [SECRET-HANDSHAKE] lets two members of the same group authenticate to each other while a non-member learns nothing, not even that a group was in question. This is the mutual-revelation property of this document, obtained exactly, but within a limit: the predicate there is membership, binary and agreed in advance, whereas the predicate here is a conjunction of conditions neither party has stated and which the session discovers. The cryptography settles the half in which the predicate is agreed in advance. Baldwin and Gramlich described a cryptographic matchmaking protocol in 1985, in which a mutual interest is revealed only when it is mutual, in both trusted-server and untrusted-server variants [MATCH1985]; the pattern was patented for social matching at the end of the 1990s and has since appeared in consumer matching services [ANON-MATCH]. Its limit is structural, since both sides must independently name *the same counterparty or the same item*. GIDP generalises the primitive from "do we both name each other?" to "does my set of conditions admit anything in your set of conditions?", which is what makes it applicable where the counterparty is not known in advance.

**Confidential matching in finance.** A narrow version of this problem has been solved in production for decades, within a single regulated venue. An indication of interest is a non-binding communication of trading interest, used to look for a counterparty without displaying an order; market practice allows fields to be omitted, and the display of such communications is subject to rule [FINRA5210]. That rule exists because broadcast indications were found to leak the very intentions they were meant to conceal, regulators examined the practice across venues [IOSCO-DARK], and the industry had to publish a taxonomy classifying indications by how much they reveal [AFME-IOI]. This is the closest thing to a controlled trial of the idea behind this document. It was run at scale by sophisticated participants, and its failure mode, inference from the signals rather than disclosure of the values, is the failure mode of Section 24.3. Conditional orders let a large order rest unpublished in a non-displayed venue and "firm up" only when a contra-side match appears [COND-ORDERS]; they are the human-market precedent for the transition from probing to a qualified Opportunity (Section 17.2). A 1999 patent family describes anonymous, confidential matching of indications followed by human negotiation of final terms [WO0070518]. GIDP differs from these systems in that the venue is not trusted with the private values, the matched object is a set of heterogeneous conditions instead of a price and a quantity, and no central operator is required.

**The human staged-disclosure protocol.** Sell-side mergers and acquisitions run a disclosure ladder by hand: an anonymised one-page teaser on a "no-names basis" [TEASER], then a non-disclosure agreement, then a confidential memorandum, then a non-binding indication, then a binding letter of intent. The Discovery Projection (Section 11) is a machine-readable teaser, and the Disclosure Policy (Section 10) is that ladder made explicit and enforceable.

**Cryptographic matching.** Private set intersection [PSI-SLR], private retrieval [PIR-SURVEY] and secure stable matching at scale [SSM-CCS16] provide mechanisms for computing on private inputs, and have been demonstrated on problems of national-registry size. GIDP is complementary to them: it defines the information-flow properties (Sections 10, 15, 25) that such a mechanism would have to satisfy, and leaves the choice of mechanism to the deployment (Section 24.12).

**Agent protocols.** Agent-to-agent communication [A2A], tool and context access [MCP], capability discovery and intent-based agent selection [AIDIP], delegation and mandate protocols [PAP] [AP2], and negotiation protocols [A2CN] [CONCORDIA] are built around discovering capabilities or authorising and executing transactions. Their scopes touch this document's edges ([PAP]'s mandates carry search and disclosure scopes, for instance) without providing a shared semantics for interests that are never published. The nearest protocol-level neighbour is Concordia's want registry, in which agents publish what they seek [CONCORDIA]; GIDP differs in that the interest itself is never published: only a deliberately reduced projection is (Section 11), and what a session reveals beyond it is governed step by step (Section 10). Progressive disclosure of *trust artifacts* between agents has been proposed in [ATN]; GIDP applies the same gate idea to the substance of a principal's interest rather than to credentials.

**What this document adds.** No single mechanism above is new here. This document proposes their composition: a conditional interest held privately by an agent and never transmitted; a per-attribute disclosure policy with a class that is usable for local evaluation and never transmissible; a projection designed for retrieval without inversion; a reciprocal, bounded compatibility session with a truthful coarsening rule; and an authority ladder that stops before commitment.

## 2. Conventions and Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.

Because GIDP 0.1 is experimental, normative language indicates the intended behaviour of a conforming GIDP 0.1 implementation rather than an established standard.

Sections 3 (Terminology) and 7 (Conceptual Model) are definitional. Requirements are stated in Sections 8 through 26. YAML and JSON fragments, worked examples and all appendices are non-normative; Appendices A and B illustrate a possible data model and interface shape and create no requirements, and Appendices E to G are editorial; where a section contains both a normative field list and an example, only the field list is normative. Timestamps in examples use the [RFC3339] format. Identifiers in message fields use `lower_snake_case`; authority levels use `UPPER_SNAKE_CASE`.

## 3. Terminology

This section defines terms. It imposes no requirements; requirements on these objects appear in the body.

**Principal.** The person, organisation, collective, institution, business function, software-controlled entity or other authority whose interests are represented.

**Agent.** A software system that holds, derives, evaluates, communicates or acts upon information on behalf of one or more Principals within the bounds of a Standing Interest. An Agent may be a personal agent, a career or investment agent, an agent resident in a CRM, ATS, ERP or marketplace, a procurement or corporate-development agent, or a broker or intermediary agent.

**Conditional Interest.** A state transition that a Principal may be willing to consider if specified conditions are satisfied. Canonical form: *the Principal is not necessarily seeking X, but authorises the Agent to explore X if conditions C1…Cn hold, without revealing protected information until disclosure conditions D1…Dn are satisfied.* Section 8 defines four classes.

**Standing Interest.** A bounded delegation from a Principal to an Agent: a structured container holding one or more Conditional Interests together with constraints, exclusions, a Disclosure Policy, an Authority specification and validity bounds. A Standing Interest does not imply active demand.

> *Why "standing".* The word is used as in a *standing order* or a *standing instruction*: something registered once, held in place until revoked or expired, and acted upon when its conditions are met. It does not assert that the Principal is passive. A Standing Interest of the confidential-active-demand class (Section 8.2) represents a search that is under way but unpublished; in every class, "standing" denotes persistence and registration and says nothing about urgency.

> *Why not "mandate".* Authorisation and payment protocols in the agent ecosystem use "mandate" for a signed proof that a principal authorised a specific transaction: AP2 defines `IntentMandate`, `CartMandate` and `PaymentMandate`, and adjacent negotiation proposals are drafting a common agent-mandate specification in the same sense. A Standing Interest is the opposite kind of object: it is never transmitted, and it bounds what an Agent may *explore and disclose* rather than what it may *pay or commit to*. Section 20 describes how a Standing Interest's Authority may nevertheless be *evidenced* by such an external mandate. For the same reason this specification avoids "intent", which in payment protocols, in agent-discovery drafts and in the decentralised-finance sense denotes an active request for something to be done.

**Disclosure Policy.** The rules attached to a Standing Interest specifying, per attribute, the surface on which the attribute may appear and the gate that must be passed before it is disclosed (Section 10).

**Discovery Projection.** A deliberately reduced, policy-compliant representation derived from a Standing Interest for the purpose of candidate retrieval (Section 11).

**Discovery Provider.** A service or mechanism used to publish, route, search or retrieve Discovery Projections and resolve candidates. It may be centralised, federated, peer-to-peer, community-specific, enterprise-private or privacy-preserving (Section 12).

**Compatibility Session.** A bounded interaction between two Agents (or, experimentally, more) in which they determine whether the Standing Interests they represent may be mutually compatible while applying their Disclosure Policies (Sections 13–17).

**Claim.** A question about one dimension of a Conditional Interest, evaluated within a Compatibility Session and producing exactly one result from the vocabulary of Section 15.

**Counterparty.** Another Principal, or the Agent representing it, participating in a potential Opportunity.

**Authority.** The set of actions an Agent may perform on behalf of a Principal for a given Standing Interest, expressed as levels (Section 16).

**Consent.** A scoped, explicit authorisation to progress a Compatibility Session to a more disclosing stage, given either by the Principal or by an Agent whose Authority for that action is unconditional (Section 14.5, Section 16.2).

**Opportunity.** A candidate configuration of Standing Interests that a session has qualified: every proposition standing at qualification received a qualifying result (Section 14.6). It is a lead worth a conversation and does not establish that the interests are jointly satisfiable; Section 14.6 defines what it asserts. An Opportunity is not a contract, does not imply commitment, and does not imply that any Principal has consented to identity disclosure (Section 14.6).

**Handoff.** The transfer of a sufficiently qualified Opportunity to a human, a workflow, a negotiation agent, a transaction protocol or another downstream system (Section 14.7).

## 4. Problem Statement and Scope

### 4.1 Problem statement

Existing agent discovery commonly begins with a capability or a task: *find an agent that can translate this document; find an agent that can book a flight.* The relevant capability can generally be advertised.

GIDP addresses a different class of problem:

> Find another Principal whose private conditions may be compatible with mine, even though neither side wants to publish the information required to establish that compatibility.

Capability and willingness are different questions. A registry can answer "which agent can perform X"; it cannot answer "do the private conditional preferences of the Principals represented by A and B have a mutually acceptable intersection" without either side publishing those preferences. Appendix D contrasts the two problems dimension by dimension.

### 4.2 Scope

GIDP addresses the discovery phase that occurs before conventional negotiation. It covers:

1. representation of a Conditional Interest inside a Standing Interest;
2. Disclosure Policies attached to that Standing Interest;
3. derivation of safe Discovery Projections;
4. coarse candidate retrieval through Discovery Providers;
5. private or selectively disclosed compatibility evaluation;
6. progressive disclosure as an explicit protocol action;
7. Principal or delegated Consent;
8. Handoff to a human or a downstream protocol;
9. the authority boundaries that apply throughout.

GIDP does not require that any central service possess the complete private state of participating Principals.

## 5. Non-Goals

GIDP 0.1 does not attempt to define:

- a general agent-to-agent transport protocol;
- a tool, data or context access protocol;
- a universal identity system, credential format or reputation system;
- a payment or settlement protocol;
- legally binding electronic contracting;
- a complete negotiation protocol;
- universal domain ontologies for employment, M&A, real estate, investment or other markets;
- a specific exchange or marketplace, or a requirement that one exists;
- centralised storage of Standing Interests;
- a specific AI model or a specific privacy-preserving cryptographic technique;
- a requirement that every human or organisation has one canonical personal agent;
- whether a proposed Opportunity is economically or ethically desirable;
- autonomous binding commitment by Agents.

GIDP may integrate with systems that provide these functions (Sections 20–22).


**Market structures this protocol does not serve.** Four were tested against
the reference implementation, and each failed for a structural reason rather
than an implementation one; the companion document *Where this protocol should
not be used* (`LIMITS.md`) records them in full.

Markets where publication is a legal obligation rather than a choice
(public procurement, regulated disclosure) cannot be expressed at all: every
disclosure class in Section 10 is an upper bound on exposure and none is a
lower bound, so an Agent that publishes nothing is conformant while its
Principal is in breach. Markets whose interests reduce to one comparable
dimension, or that perish faster than a human answers, are served worse
by this protocol than by a sealed-bid mechanism. In the first case it is the
other conditions that make a threshold worth hiding, and they do not hide it;
in the second, a `principal_approval`
gate that cannot run in the time available is only nominal. Contexts of
structural asymmetry, where one side runs many sessions and the other runs
few, invert the protection: the strong side spends the same disclosure
repeatedly while each weak counterparty spends a scarce one, and per-counterparty
controls do not see the aggregate. Finally, markets that must establish identity
before any substantive exchange, such as sanctions-screened or KYC-gated
ones, are incompatible with the ordering of Section 17.2, which reaches
identity only through qualification; that ordering is enforced by the state
machine and a domain profile may not reverse it (Section 21).

## 6. Design Principles

These principles motivate the requirements of later sections; where a principle and a requirement overlap, the requirement governs.

### 6.1 Local secrets, global discovery
Sensitive knowledge stays under the control of the Agent or system that legitimately possesses it. Global discovery operates on reduced signals rather than complete Standing Interests.

### 6.2 Data minimisation
Information is not disclosed only because it is useful for matching. Information *usable for evaluation* is distinguished from information *revealable to a counterparty*.

### 6.3 Progressive disclosure
Information is revealed progressively as confidence, authorisation and mutual interest increase. Discovery, compatibility, identity disclosure, negotiation and commitment are separate stages.

### 6.4 Reciprocal discovery
GIDP is not limited to request-to-provider search. Both sides may hold private constraints, and compatibility may depend on the intersection of both.

### 6.5 Principal-centric, explicit authority
Permission to discover is never permission to disclose identity, negotiate binding terms or commit. Authority is explicit and per-Standing Interest (Section 16).

### 6.6 Transport independence
GIDP is implementable over existing agent communication mechanisms and defines no new transport (Section 22).

### 6.7 Market-structure neutrality
GIDP does not require a single centralised exchange; centralised, federated, peer-to-peer and enterprise-private discovery architectures are all admissible (Section 12.3).

### 6.8 Cross-market primitives
The core describes Conditional Interests generically; vertical vocabularies are extensions (Section 21).

### 6.9 Multi-party compatibility by design
The data model does not make bilateral matching the only representable structure. GIDP 0.1 implements bilateral compatibility as the minimum interoperable core while keeping dependency primitives available for multi-party Opportunities (Section 19).

### 6.10 Policy enforcement outside the model
Where an Agent is driven by a language model, disclosure and authority enforcement are implemented by a deterministic policy layer outside unconstrained model behaviour. The model may reason about a request; the policy layer decides whether protected information may leave the Agent (Section 24.10).

## 7. Conceptual Model

The basic relationship is:

```text
Principal
   │ delegates
   ▼
Standing Interest  (one or more Conditional Interests + policy + authority)
   │ represented by
   ▼
Agent
```

A Principal may hold multiple Standing Interests and use multiple Agents:

```text
                     Principal A
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   Career Agent   Investment Agent   Personal Agent
        │                │                │
   Standing        Standing           Standing
   Interest 1      Interest 2         Interest 3
```

An Agent may represent multiple Standing Interests. An intermediary Agent may represent Standing Interests from multiple Principals, provided each Standing Interest retains its own authority and disclosure boundaries. Principals may be persons, organisations, business functions, institutions or software; personal Principals are first-class, and the same session may connect a person with a person, a person with an organisation, or two organisations.

The object of GIDP discovery is therefore a potentially compatible Standing Interest represented by an Agent, and not the Agent itself.

### 7.1 Conceptual dimensions of a Conditional Interest

```text
I HAVE           assets / capabilities / rights / position
I WANT           outcomes
I WOULD CONSIDER state changes
IF               conditions
I PROVIDE        capabilities / resources / commitments I can bring
I REQUIRE        capabilities / resources / commitments I need from others
I EXCLUDE        counterparties / structures / conditions
I WILL DISCLOSE  according to policy
I AUTHORISE      my Agent to act within bounds
```

These dimensions are conceptual. In the Standing Interest representation of Section 9 HAVE and PROVIDE map to `provides` and positional attributes, WANT and WOULD CONSIDER to `interest`, IF to `conditions` and `private_conditions`, REQUIRE to `requires`, EXCLUDE to `excludes`, WILL DISCLOSE to `disclosure_policy`, and AUTHORISE to `authority`. Not every Standing Interest populates every dimension.

## 8. Conditional Interest Model

GIDP 0.1 recognises four classes of Conditional Interest. They differ in what is hidden and share the same protocol mechanics; a conforming implementation MUST be able to represent all four with the same objects.

### 8.1 Passive conditional demand
*I am not seeking X, but I would consider X if conditions C hold.* Example: an executive who would consider a CEO role in B2B software above a private scale threshold. Established analogue: the "passive candidate" in executive search, and the owner of an unlisted asset holding an implicit option.

### 8.2 Confidential active demand
*I am seeking X, but I do not want potential counterparties or the market to know that I am seeking X.* Example: a corporation exploring acquisition targets without signalling an acquisition programme; a board exploring CEO succession without a public search. Established analogue: buy-side deal criteria circulated privately, and the indication of interest used to query liquidity without displaying an order (Section 1.1).

### 8.3 Private conditional supply
*I can offer X, but I do not want to advertise X publicly.* Example: a startup that would white-label its technology; an owner who would sell an unlisted asset above a private price. Established analogue: the conditional order resting unpublished in a dark pool, and off-market inventory.

### 8.4 Interdependent conditional interest
*I will consider X if another party performs or commits to Y.* Example: an investor who participates only if a qualified lead commits; a buyer who acquires a building only if an anchor tenant signs. Established analogue: conditional co-investment subject to a lead investor, and contingent real-estate transactions. This class uses the dependency primitives of Section 19 and is the entry point to multi-party discovery.

> *There is no field for this.* GIDP defines no attribute carrying the classification, and a conforming implementation is not asked to record one. The four classes are a way of thinking about what is being expressed, and they are expressed entirely through the Disclosure Policy: which attributes are `local`, which reach a `discovery` surface, which need a gate. An Agent's behaviour cannot depend on the class because nothing in the protocol states it. This is intentional: a required field that no behaviour reads would add work for every implementer only for the author's convenience, and two implementations given one would eventually disagree about what it means.

## 9. Standing Interest

A Standing Interest SHOULD contain sufficient information for an Agent to determine whether an Opportunity is worth exploring without the complete Standing Interest ever leaving the Agent's trust boundary.

### 9.1 Private by default
A Standing Interest MUST NOT be transmitted through GIDP. Attributes without an explicit Disclosure Policy entry MUST be treated as `evaluation_only` (Section 10).

The requirement binds the holder: an Agent MUST NOT transmit an attribute classified `local` *of the Standing Interest it holds*. It does not and cannot mean that such a value never appears in a session, because a claim carries a candidate value chosen by the querent (Section 14.2); where that guess coincides with the responder's private value, the value is on the wire, put there by the party that does not hold it. The responder never transmits it on its own initiative. Whether an answer *confirms* a guessed value is a different matter: a truthful `compatible` to an `equals` claim does, and that is inference, bounded (or not) by the controls of Section 24.3, rather than transmission.

### 9.2 Validity
Standing Interests SHOULD support activation, suspension, expiration, revocation and supersession by a new version (Section 17.1). When a Standing Interest is suspended, expired, revoked or superseded, the Agent MUST withdraw or update the projections derived from it (Section 12.2).

### 9.3 Multiple interests
A Principal MAY maintain several independent Standing Interests rather than one universal profile. Separate Standing Interests are RECOMMENDED when interests have different Disclosure Policies or authorities.

### 9.4 Standing Interest formation
Standing Interests may be authored explicitly or inferred from conversation or behaviour. A Standing Interest inferred by an Agent MUST be confirmed by the Principal before the Agent publishes a projection or opens a session for it, unless the Principal has explicitly delegated that authority. The RECOMMENDED pattern is *conversation → inferred preference → explicit confirmation → Standing Interest*.

### 9.5 Illustrative representation (non-normative)

```yaml
standing_interest:
  id: "local:opaque-id"
  version: 3
  principal_ref: "local:principal-id"     # never transmitted

  interest:
    # a confidential active demand (Section 8): a way of reading this
    # interest, not a field — GIDP defines none
    action: consider
    object: strategic_transaction
    structures: [acquisition, majority_investment, joint_venture]

  conditions:                              # evaluable; some disclosable
    target_sector: vertical_saas
    target_geography: [france, dach]
    target_arr: {min: 3000000, max: 15000000}
    transaction_structure_class: control_or_partnership

  private_conditions:                      # evaluable; never disclosed
    maximum_valuation: 80000000

  provides: [market_access_france]
  requires: []
  excludes:
    counterparties: ["[LOCAL SECRET]"]

  strategic_rationale: "[LOCAL SECRET]"    # not even used in evaluation

  disclosure_policy:                       # Section 10
    interest.object:              discovery
    target_geography:             discovery        # generalised in the projection
    target_sector:                discovery        # generalised in the projection
    transaction_structure_class:  session
    target_arr:                   evaluation_only
    maximum_valuation:            evaluation_only
    provides:                     session
    excludes:                     evaluation_only
    strategic_rationale:          never
    principal_identity:           session/principal_approval

  authority:                               # Section 16
    OBSERVE: true
    SEARCH: true
    PUBLISH_PROJECTION: true
    PROBE: true
    DISCLOSE: true
    INTRODUCE: approval_required
    NEGOTIATE_NONBINDING: false
    COMMIT: false

  validity:
    not_before: "2026-09-21T00:00:00Z"
    expires_at: "2027-03-21T00:00:00Z"
```

## 10. Disclosure Policy

A Disclosure Policy assigns each Standing Interest attribute a **disclosure class**. A disclosure class is a pair *(surface, gate)*. An implementation MUST support more expressive policies than a binary public/private flag; at minimum it MUST support the surfaces and gates below.

### 10.1 Surfaces
A surface is the most exposed place an attribute (or a coarsened derivative of it) may appear. Surfaces are totally ordered from most to least exposed:

| Surface | Meaning |
|---|---|
| `public` | May be exposed without authentication. |
| `discovery` | May appear in a Discovery Projection submitted to any Discovery Provider. |
| `network` | May appear in a Discovery Projection submitted to, or be disclosed within, an authorised trust domain (e.g. a private registry or verified community). |
| `session` | May be disclosed to an authenticated peer inside a Compatibility Session. |
| `local` | MUST NOT be transmitted through GIDP. |

### 10.2 Gates
A gate is a condition that must hold before an attribute is disclosed on its surface:

| Gate | Meaning |
|---|---|
| `none` | No additional condition. |
| `consent` | A `ConsentResponse` with status `granted` covering the attribute has been issued by this side for this session (Section 14.5). |
| `principal_approval` | A per-instance decision by the Principal (a human or an explicitly designated approver) for this session. Cannot be satisfied by Agent authority alone. |

### 10.3 Class names
The class is written `surface/gate`; the gate `none` may be omitted. Two `local` classes are distinguished by what the Agent may do with the attribute locally:

| Class | Surface | Gate | Meaning |
|---|---|---|---|
| `public` | public | none | — |
| `discovery` | discovery | none | — |
| `network` | network | none | — |
| `session` | session | none | Disclosable in session on request. |
| `session/consent` | session | consent | Disclosable in session after this side's consent. |
| `session/principal_approval` | session | principal_approval | Disclosable in session after the Principal's per-instance approval. |
| `evaluation_only` | local | — | MAY be used by the holding Agent to evaluate claims; the *result* of such evaluation MAY be transmitted as a coarse result class (Section 15). MUST NOT itself be transmitted. |
| `never` | local | — | MUST NOT be transmitted and MUST NOT be used to produce transmitted results. A claim on it MUST be answered `declined`, and no other object may reflect it, not even as the bare fact that something is being withheld (Section 14.6). |

`discovery`, `network` and `session` surfaces MAY also carry gates (e.g. `network/consent`) but such combinations are not expected to be common.

### 10.4 Coarsening
An attribute of surface `session` MAY contribute a *coarsened derivative* to a Discovery Projection only if the Disclosure Policy explicitly lists that derivative with a `discovery` or `network` class. Without such an entry, no derivative of a `session` or `local` attribute may appear in a projection.

### 10.5 Counterparty-dependent policies
A policy SHOULD be able to depend on properties of the counterparty, such as its trust level, verified attributes or membership (Section 20). Example (non-normative):

```yaml
principal_identity:
  unknown_agent:          never
  verified_agent:         session/principal_approval
  trusted_network_member: session/consent
```

### 10.6 Identity
Principal identity MUST have its own policy entry (`principal_identity`). Its surface MUST NOT be more exposed than `session`. An implementation MUST be able to conduct discovery and compatibility without disclosing identity.

The identity rules attach to the nature of the data, whatever message would carry it. `principal_identity`, and any attribute the session's profile marks as identifying (a legal or natural name, an organisation name, a registration identifier), is disclosed only under a consent whose action is `reveal_identity` (Section 14.5), which requires the `INTRODUCE` authority and cannot precede qualification. It MUST NOT appear in the scope of a `ConsentRequest` whose action is `disclose_attributes`, and a request whose scope names it under any other action MUST be answered `declined`; a `DisclosureRequest` naming an identity attribute MUST likewise be answered `declined` unless a `reveal_identity` consent covering it is in force; and a *claim* on an identity attribute MUST be answered `declined` under the same condition, because `compatible` to `principal_identity equals X` confirms the identity without any `DisclosureResponse` carrying it. Confirmation is thus a third route to disclosure, after the two above, and the same rule closes it. Without this rule the restriction would be nominal: `disclose_attributes` is permitted before qualification (Section 14.5) and is gated on `DISCLOSE`, so a scope that smuggled `principal_identity` through it would do before qualification, under the lesser authority, what `reveal_identity` exists to hold until after it.

### 10.7 Purpose and retention
Every disclosure request MUST state its purpose and SHOULD state retention expectations (Section 14.4). Purpose *restrictions* enforced by the recipient are future work.

Retention, however, is an obligation, not advice. A requester MUST NOT state a retention it is not able to discharge, and an implementation that cannot discharge any retention mode MUST omit the field rather than state one it will ignore; the responder is then left to decline, which is the safe outcome. The obligation/advice distinction is XACML's [XACML], and `rationale.md` explains why it matters here; the rule above is what the obligation requires.

### 10.8 Irreversibility
Previously disclosed information cannot be recalled from a counterparty. Revocation (Section 17) affects future behaviour, not past disclosures; implementations SHOULD make this visible to Principals when they approve disclosures.

### 10.9 Relationship to Authority
Authority (Section 16) states whether the Agent may perform a *category* of action at all; the Disclosure Policy states what may be disclosed *per attribute*. A disclosure happens only if both permit. When an authority level is `approval_required` and the attribute's gate is `principal_approval`, one Principal decision satisfies both.

## 11. Discovery Projection

Publishing a complete Standing Interest would defeat the purpose of GIDP. An Agent with `PUBLISH_PROJECTION` authority derives one or more Discovery Projections.

### 11.1 Required fields
A `DiscoveryProjection` MUST carry `type`, `version` and `expires_at` (Section 14), `projection_id` (opaque, unique to the publishing Agent), and `endpoint` (the reference by which a candidate's Agent can open a Compatibility Session with the publishing Agent, expressed in binding-specific terms). `type`, `version`, `expires_at`, `projection_id` and `endpoint` are protocol metadata: they are not derived from the Standing Interest and are not subject to the content rule of Section 11.2. `endpoint` and `projection_id` SHOULD nevertheless be unlinkable across providers (a distinct value per projection), because a value that is stable across providers is the correlating identifier that Section 24.2 warns about, and deriving distinct projections per provider (Section 11.5) achieves nothing if all of them carry the same endpoint. A projection MUST NOT carry `session_id`, a Principal identifier, or a resolvable reference to the Standing Interest it derives from; `interest_ref`, where present, MUST be opaque and resolvable only by the publishing Agent.

A projection MUST carry at least one retrieval attribute. Retrieval attributes are profile-defined (Section 21); the `core` profile defines `categories` (interest categories), `domains`, `geographies` and `relation`. `relation` states the symmetric role the Principal would occupy with respect to a counterparty, drawn from the profile's vocabulary; the `core` profile defines exactly one value, `complementary_counterparty`, which asserts that a complementary position is sought and asserts nothing about direction. A profile MUST NOT define a relation value that discloses transaction direction.

### 11.2 Content rule
A projection submitted to a Discovery Provider outside any authorised trust domain MUST contain only attributes, or explicitly policied derivatives, of surface `public` or `discovery`. A projection submitted to a provider inside an authorised trust domain MAY additionally contain `network` attributes. A projection MUST NOT contain Principal identity.

### 11.3 Example (non-normative)
From the Standing Interest in Section 9.5:

```yaml
discovery_projection:
  type: DiscoveryProjection
  version: "gidp/0.1"
  projection_id: "opaque-projection-id"
  interest_ref: opaque                  # resolvable only by the publishing Agent
  categories: [strategic_transaction]
  domains: [enterprise_software]       # generalisation of target_sector (policy: discovery)
  geographies: [europe]                # generalisation of target_geography (policy: discovery)
  relation: [complementary_counterparty]
  endpoint: {protocol: "a2a", agent_ref: "opaque-or-resolvable-agent-reference"}
  expires_at: "2026-10-21T00:00:00Z"
```

The projection omits Principal identity, transaction direction (buy vs sell), valuation limits, ARR range, rationale and exclusions.

### 11.4 Minimisation
Agents SHOULD minimise projections while preserving sufficient retrieval quality. This is a trade-off: more specific projections improve retrieval and increase inference risk; less specific projections do the reverse. Past a point, however, minimisation reverses its own effect: a projection coarse enough to be retrieved by everyone is retrieved by everyone, and each retrieval is a session with a counterparty that had no business finding this Principal and an opportunity to probe under Section 24.3. GIDP 0.1 does not prescribe an optimum; the measured shape of the curve, and the reason the deciding quantity is observable to the provider and not to the publisher, are in `alternatives.md` and `rationale.md`. Coarsening techniques include generalising geography (from city to region), bucketing economic ranges, and replacing direction-revealing attributes with symmetric ones (`strategic_transaction` rather than `acquire`). The last has an established precedent: in the equivalent human market, an indication of interest may omit side and price and still attract a counterparty [COND-ORDERS].

### 11.5 Multiple projections
An Agent MAY derive different projections from one Standing Interest for different Discovery Providers or trust contexts.

### 11.6 Non-invertibility and non-faithfulness
Implementations SHOULD design projections so that observing a projection, alone or combined with other projections and external data, does not trivially reconstruct the Standing Interest or identify the Principal; this is a design objective, not a cryptographic guarantee, in GIDP 0.1. A projection is not a complete statement of the Principal's preferences. An Agent MUST NOT emit an `Opportunity` for a candidate before a `CompatibilityResponse` has been received in a session with that candidate, and MUST NOT disclose any attribute to a candidate on the basis of retrieval alone: every disclosure requires the gates of Section 10.2 to be satisfied within a session.

## 12. Discovery Providers and Candidate Retrieval

### 12.1 Agent discovery versus interest discovery
GIDP distinguishes *agent discovery* ("which endpoints support GIDP?") from *Standing Interest discovery* ("which of those endpoints may represent a Standing Interest relevant to this Conditional Interest?"). GIDP SHOULD reuse existing mechanisms for endpoint discovery (Section 22) and defines only the logical Discovery Provider interface for Standing Interest discovery.

### 12.2 Logical operations
A Discovery Provider SHOULD offer operations equivalent to:

```text
publishProjection(projection)                 -> projection_ref
updateProjection(projection_ref, projection)  -> status
withdrawProjection(projection_ref)            -> status
queryCandidates(query_projection, policy)     -> candidate_refs
resolveCandidate(candidate_ref)               -> agent_endpoint
```

Exact APIs are not specified in 0.1. `projection_ref` is assigned by the provider and need not equal the `projection_id` the Agent minted (Section 11.1); an Agent MUST be able to withdraw using the `projection_ref` the provider returned, and a candidate reference returned to a querent MUST carry the `projection_ref` the opening `SessionOpen` should cite (Section 14.1). A provider MUST acknowledge a `withdrawProjection`, MUST publish a withdrawal latency, and MUST stop returning the projection within that latency of the acknowledgement; it MUST NOT return any projection after its `expires_at` (Section 24.6). Acknowledgement and effect are distinct, and only the second protects the Principal; an Agent MUST treat that published latency as the time for which its projection remains retrievable after withdrawal.

### 12.3 Architectures
A provider MAY be: *centralised* (a single index receiving projections and returning candidate references; the simplest architecture for a reference implementation); *federated* (multiple providers exchanging or routing projections: industry registries, professional communities, banks, CRM ecosystems, recruiting or investment networks, regional networks); *peer-to-peer* (Agents exchanging projections without a central provider; routing is not defined in 0.1); or *privacy-preserving* (private set intersection [PSI-SLR], private information retrieval [PIR-SURVEY], secure multi-party computation, trusted execution environments, encrypted or oblivious indexes, local embeddings with privacy controls). GIDP 0.1 does not prescribe a cryptographic architecture, and does not require that a deployment use a single central provider.

### 12.4 Staged retrieval
GIDP is not intended to perform exhaustive pairwise comparison across all participating Agents. Implementations SHOULD use a staged architecture in which cheap, coarse retrieval narrows the candidate set before any Compatibility Session is opened:

```text
all published projections
        │  coarse projection retrieval / routing
        ▼
relevant cohorts or domains
        │  structured or semantic filtering
        ▼
candidate counterparties
        │  private Compatibility Sessions
        ▼
Opportunities
        │  Consent, Handoff, human action
        ▼
```

Each stage is expected to reduce the set by orders of magnitude, so that the number of Compatibility Sessions opened stays small relative to the number of projections published. This document states no target ratios: they depend on the domain, the coarseness of projections and the population served by a given Discovery Provider. Measuring them is one of the evaluation criteria of Appendix F.3.

Retrieval signals may include interest category, coarse geography, industry, capability class, time horizon, non-sensitive economic buckets, verified attributes and domain-specific projection fields.

A provider SHOULD resolve hierarchical retrieval attributes (a city against its country, a sub-industry against its industry) rather than comparing tokens for equality, and SHOULD publish which hierarchies it resolves so that an Agent knows what its projection will be matched against. This is a recommendation about provider quality, not about the protocol, and its omission costs the *publisher*: against a token-comparing provider, a publisher that wants to be found coarsens its projection to repair a defect in the index. Measured on one synthetic population (`alternatives.md`), resolving one hierarchy raised the recall of a precise projection from 26 % to 100 % with the publisher changing nothing; the figures belong to that population, not to providers in general. Where a provider resolves, the minimisation advice of Section 11.4 rests on exposure alone, as it should. The fuller argument is in `rationale.md`. GIDP 0.1 defines no vocabulary and no hierarchy (Section 5), and does not need to, since it is sufficient for a provider to state what it resolves.

A compatibility result is produced only by a `CompatibilityResponse` within a session; an Agent MUST NOT record or report a compatibility result for a candidate with which no session has been opened.

### 12.5 Provider abuse controls
Discovery infrastructure is a high-value target for spam and intelligence gathering. Providers SHOULD implement authenticated publishing, publishing and query quotas, reputation, economic or computational cost, proof of membership, category-specific access, projection expiry, abuse reporting, anomaly detection, Sybil resistance and privacy-preserving logging. A provider MAY return deliberately coarse candidate sets to reduce enumeration risk. A provider MUST NOT expose an endpoint for bulk export of projections unless the relevant Principals have explicitly authorised such exposure.

## 13. Protocol Flow

The GIDP 0.1 bilateral core has eight conceptual stages. Stages 0–2 precede the existence of a session; from Stage 3 onward either Agent MAY close the session at any time without giving a reason (Section 14.8).

```text
Stage 0  Standing Interest formation         (local)
Stage 1  Projection                (local → Discovery Provider)
Stage 2  Candidate retrieval       (Discovery Provider)
Stage 3  Session initiation        (Agent ↔ Agent)
Stage 4  Compatibility probing     (Agent ↔ Agent)
Stage 5  Progressive disclosure    (Agent ↔ Agent, policy-gated)
Stage 6  Consent                   (Principal / delegated)
Stage 7  Handoff                   (to humans or downstream protocol)
```

**Stage 0 — Standing Interest formation.** A Principal or authorised system creates or confirms a Standing Interest (Section 9.4).

**Stage 1 — Projection.** The Agent derives a policy-compliant Discovery Projection (Section 11) and publishes it to one or more Discovery Providers.

**Stage 2 — Candidate retrieval.** The Agent submits a query projection and receives candidate references (Section 12).

**Stage 3 — Session initiation.** The initiating Agent sends a `SessionOpen` to a candidate Agent, which answers with a `SessionAccept` or a `SessionClose` (Section 14.1). An Agent MUST NOT send a claim before it has sent or received a `SessionAccept`.

**Stage 4 — Compatibility probing.** Agents exchange `CompatibilityRequest`s carrying structured claims designed to eliminate incompatible candidates while minimising disclosure (Section 14.3, Section 15). An Agent SHOULD answer from local evaluation without disclosing the underlying value whenever possible.

**Stage 5 — Progressive disclosure.** If compatibility cannot be established from available information, an Agent MAY send a `DisclosureRequest` (Section 14.4). The responding Agent MUST apply the Standing Interest's Disclosure Policy and Authority before answering. A declined disclosure does not end the session.

**Stage 6 — Consent.** When compatibility has been established, the session yields an `Opportunity` (Section 14.6). Any disclosure gated by `consent` or `principal_approval`, including Principal identity, requires a `ConsentRequest` / `ConsentResponse` exchange (Section 14.5). A potential match MUST NOT automatically reveal Principal identities.

**Stage 7 — Handoff.** After the required consents, Agents MAY reveal identities, introduce Principals, arrange a meeting, transfer the session to a negotiation agent, initiate an authorised negotiation protocol (`Handoff`, Section 14.7), or close without further disclosure. GIDP does not define the resulting agreement.

## 14. Protocol Objects

GIDP 0.1 defines the following object set. For each transmitted object this section lists its required fields (normative) and gives an example (non-normative). Future drafts SHOULD minimise this set where equivalent semantics can be achieved with fewer primitives, and SHOULD define a normative JSON Schema.

```text
Local, never transmitted:   StandingInterest, DisclosurePolicy
Published to providers:     DiscoveryProjection                     (Section 11)
Session control:            SessionOpen, SessionAccept, SessionClose
Compatibility:              CompatibilityRequest, CompatibilityResponse
Disclosure:                 DisclosureRequest, DisclosureResponse
Consent:                    ConsentRequest, ConsentResponse
Outcome:                    Opportunity, Handoff
```

Every transmitted object MUST carry `type`, `version` (`"gidp/0.1"`; the token is the protocol's acronym in lower case; its choice is discussed in `rationale.md`), `session_id` (`DiscoveryProjection` excepted; in `SessionOpen` the value is the proposed identifier) and `expires_at`. The **request-type** objects are `SessionOpen`, `CompatibilityRequest`, `DisclosureRequest` and `ConsentRequest`. The **response-type** objects are `SessionAccept`, `CompatibilityResponse`, `DisclosureResponse` and `ConsentResponse`. `DiscoveryProjection`, `Opportunity` and `Handoff` are neither. `SessionClose` is neither, but may be sent in place of any response.

Every request-type object MUST carry a `request_id` unique within the session, and every response-type object MUST carry `request_ref` equal to the `request_id` it answers. A `SessionClose` sent in place of a response MUST carry `request_ref`; a `SessionClose` sent on its own MUST NOT.

Every request-type object MUST be answered by exactly one response-type object or by `SessionClose`, with two exceptions. The first is a request held under the `PROBE` approval path of Section 16.3, which a Principal's silence discharges by its own `expires_at`: expiry is that path's terminal outcome, and no response follows it. The second is a **provisional** response, which is a response whose status is `pending_principal_approval` (Sections 14.4, 14.5), or a `DisclosureResponse` whose status is `granted_if_reciprocal` or `granted_if_verified`. A provisional response does not discharge the request; the responder MUST subsequently send exactly one further object of the same response type, carrying the same `request_ref` and a terminal status, or a `SessionClose`. A requester MUST accept that further object although it did not send a second request, and MUST NOT send a duplicate request while a provisional response is outstanding. A responder that cannot obtain a decision, or whose condition is not satisfied, before `expires_at` MUST send a terminal `declined` or a `SessionClose`. For a `granted_if_reciprocal` or `granted_if_verified` response, the terminal response is sent once the requester has reciprocated or supplied the named credential; the requester does not send a second `DisclosureRequest`.

`Opportunity` and `Handoff` are one-way notifications: they are not request-type objects and are not answered by a response-type object. A peer that does not agree with the content of an `Opportunity` MUST NOT act on it; where the content does not match the peer's own evaluation it MUST close the session (Section 14.6), and in any other disagreement it MAY.

### 14.1 SessionOpen / SessionAccept

`SessionOpen` required fields: `session_id` (proposed, opaque), `request_id`, `initiator` (opaque Agent reference), `purpose` (an interest category), `max_depth` (how far into its Disclosure Policy the initiator is willing to go in this session, named by the least exposed surface whose attributes it is prepared to disclose here, in the ordering of Section 10.1: permitted values are `network` and `session`, `session` being the deeper of the two because a `session` attribute is one that may appear nowhere but inside a Compatibility Session; `local` is never a permitted value, since `local` attributes are never transmitted), `profile` (a domain profile identifier, Section 21, or `core`), `features` (subset of `{dependency_primitives, multi_party}`; the bilateral core is implied). Optional: `trust_context` (Section 20); `projection_ref` (the `projection_ref` under which the responder's projection was retrieved, Section 12.2; opaque to the initiator, resolvable only by the responder's side). An Agent representing several Standing Interests behind one endpoint needs to know which interest a session is about without the opener saying anything more than what it retrieved; `projection_ref` is that routing key, it reveals nothing the projection had not already exposed, and it is bound to the provider that assigned it (Section 12.2): a candidate reference returned by retrieval carries the `projection_ref` to use, and an initiator that retrieved through several providers uses the reference the returning provider gave. A responder that receives a `projection_ref` it cannot resolve (withdrawn, expired, or never its own) answers `SessionClose` with `reason: unsupported`; an endpoint representing several Standing Interests that receives an open *without* one MUST do the same, because an ambiguous open cannot be routed and guessing would answer for an interest the initiator never retrieved.

`SessionAccept` required fields: `session_id`, `request_ref`, `responder`, `max_depth`, `profile`, `features` (the intersection actually supported). If the responder does not accept, it answers `SessionClose`. `features` in `SessionOpen` lists what the initiator offers; the intersection in `SessionAccept` is what is in force; the field marks nothing as *required*, 0.1 provides no way to, and a side that cannot proceed without a feature outside the intersection closes with `reason: unsupported` (Section 14.8).

The depth in force for the session is the shallower of the two declared values. An Agent MUST NOT send a `DisclosureResponse` with status `granted`, nor a `ConsentResponse` whose `granted_scope` includes an attribute, whose surface is deeper than the session's depth, whatever its own Disclosure Policy would otherwise permit; it MUST answer `declined` instead. An Agent for which the resulting depth makes the session pointless SHOULD close the session with `reason: unsupported` rather than probing to no purpose; the typical case is that identity, whose surface is at most `session` (Section 10.6), is out of reach. The initiator cannot distinguish that close from any other `unsupported` close, and this document does not provide a way to signal "the depth you offered is too shallow": doing so would tell a counterparty how deep the responder's policy requires it to go, which is itself a disclosure. An initiator that wishes to explore a deeper session opens a new one. Declaring a depth is not an undertaking to disclose anything: the Disclosure Policy and the gates of Section 10.2 apply in full within it.

```yaml
type: SessionOpen
version: "gidp/0.1"
session_id: "opaque-session-id"
request_id: "r-1"
initiator: "agent:opaque:789"
purpose: strategic_transaction
max_depth: session
profile: core
features: [dependency_primitives]
trust_context: {credentials: ["..."], provider_ref: "..."}
expires_at: "2026-09-21T12:00:00Z"
```

### 14.2 Claims
A *claim* is a question about one dimension. Required fields: `claim_id` (unique among the claims its sender has sent in the session), `key` (attribute or category name, from the core vocabulary or the session's profile), `operator`, `value`. Optional: `supersedes` (a list of `claim_id`s, defined below). GIDP 0.1 defines the operators `equals`, `intersects` (set overlap), `overlaps` (the asked range, expressed as `{min, max}` or a named bucket from the profile, intersects the responder's private value or range) and `compatible_with` (profile-defined predicate). The operator is named for what it tests. Where the responder's own value is itself a range (the normal case for a reservation value), the answer is decided by overlap rather than containment: a private range and an asked range are compatible if they intersect at all, because containment would make almost every good-faith claim incompatible. Implementers should be aware that overlap semantics are also what make the probing of Section 24.3 cheap, since each answer partitions the space. Profiles MAY add operators.

Two values at different levels of the same hierarchy do not intersect as sets. A claim asking `geography intersects ["germany"]`, answered by a responder holding `["munich"]`, would resolve `incompatible` under plain set semantics, which is formally correct and substantively false, since Munich is in Germany. Section 15.2 makes that result block, so a session between two compatible Principals would end because they named one thing at two granularities. The problem does not need a shared vocabulary, and requiring one would mean requiring agreement between parties who have never met.

It is solved at the point where evaluation already happens. A Standing Interest MAY place its own values in a hierarchy: for an attribute, a mapping from each value to the value that contains it. The responder then resolves a set-valued claim as follows, and the asymmetry is the substance of the rule:

- the claim is `compatible` if any asked value is one of the responder's held values or anything a held value is part of: holding `munich` answers `compatible` to `germany` and to `europe`, because it is true of Munich that it is in Germany;
- the claim is `unknown` if any asked value lies *below* a held value: a responder holding `germany`, asked about `munich`, has not said which German city it means and MUST NOT assert that the claim is false;
- the claim is `incompatible` otherwise: holding `munich`, asked about `madrid` or about `berlin`, the responder's values do contradict it.

The hierarchy is part of the Standing Interest and therefore never transmitted (Section 9.1). Nothing is negotiated or shared, and no third party is consulted, because a claim is always resolved by the party that holds the value, only that party's own values need placing. A responder that places none of its values gets set semantics and the false negative with them, which is the cost of not declaring one.

The hierarchy rule presumes one meaning of a general value, *approximate knowledge*: a responder holding `germany` has not said which city, so `unknown` to `munich` is right. A general value can instead mean an *accepted set* (every German city is acceptable), and there `compatible` to `munich` is both true and safe. The core cannot distinguish the two from the value alone, so it defaults to the cautious reading, and a profile that types an attribute's meaning (fact held, set accepted, requirement of the counterparty) MAY direct the responder to answer a narrower claim `compatible` where the accepted-set reading applies. A protocol meant to serve many domains invites one word to cover a property of the Principal, a preference of the Principal and a demand on the counterparty, and the profile is where those meanings are told apart.

The rule does not widen disclosure: answering `compatible` to `europe` tells the querent what it asked and not which city, and answering `unknown` where the old reading said `incompatible` tells it strictly less. A Discovery Provider faces the same problem one layer up with a different remedy (Section 12.4): it resolves hierarchies for the whole index because it sees only projections and queries, while inside a session only the responder can, because only the responder may see its own value.

An operator may not fit the shape of the value a responder holds: `overlaps` names an interval but the responder's value is a label or a list, or `intersects` names a set but the responder's value is a range. A responder MUST answer `unknown` in that case. It MUST NOT treat the mismatch as a malformed message, and MUST NOT fail. Failing on some shapes and answering on others makes the responder's behaviour a function of the shape of its own private value, which is an inference channel in the sense of Section 24.3. The stronger reason is that a responder that can be made to fail by a well-formed message with an ill-fitting operator can be made to fail by anybody, which turns a claim into a denial of service. A requester learns nothing from `unknown` beyond what Section 15.1 already permits it to learn.

A claim is a **proposition**, not a dimension. Two claims on `transaction_value` with different ranges are two questions, each with its own result, and neither replaces the other because they share a key. A result belongs to the proposition it answers, identified by the `claim_id` together with the direction of the request: both Agents number their own claims, so a `claim_id` alone does not identify a proposition across a session in which both ask. A claim's `supersedes` withdraws earlier propositions of the same sender, and it is the only way a result leaves the session. It MAY withdraw a proposition answered `declined`, `unknown`, `requires_disclosure`, `compatible` or `conditionally_compatible`, which is how a requester that met a refusal asks again. It MUST NOT withdraw one answered `incompatible`: a known contradiction ends the session (Sections 15.2, 17.2), and a requester able to withdraw it and ask a neighbouring value instead would have bisection (the attack of Section 24.3) as a supported feature. A responder that receives a `supersedes` naming anything else MUST treat the request as malformed.

### 14.3 CompatibilityRequest / CompatibilityResponse

`CompatibilityRequest` required fields: `claims` (non-empty list), `allowed_results` (subset of the per-claim result vocabulary of Section 15.1 that the requester is prepared to receive; MUST include `declined`). A request MUST NOT contain the requester's own private values; it asks whether the responder is compatible with a class. A claim is a test of a hypothesis, not a position: sending it asserts neither that the sender offers what it names nor that it would accept it, and a recipient MUST NOT treat a claim, or a pattern of claims, as an offer or as an indication of availability. That is the boundary with negotiation (Section 16.1), stated operationally: an object that does carry a position, even a non-binding one, belongs after a Handoff.

`CompatibilityResponse` required fields: `request_ref`, `results` (one entry per claim, each carrying the `claim_id` and `key` of the claim it answers and a result from Section 15.1 that is a member of `allowed_results`, or `declined`), `session_status` (Section 15.2), `next` (`permitted`: subset of `{compatibility_request, disclosure_request, consent_request, handoff, close}`; `requires`: attribute keys whose disclosure would allow a `requires_disclosure` result to be resolved, MAY be empty). An OPTIONAL field `contingent_on` carries the responder's own communicable contingencies, under the rule of Section 14.6: dependencies whose names the responder's Disclosure Policy permits it to transmit travel by name; a dependency the policy withholds travels as the single token `undisclosed`; a `never` dependency leaves no trace. A responder whose evaluation carries a communicable contingency MUST state it in each `CompatibilityResponse` it sends while that contingency stands; a response without the field asserts no communicable contingency. The initiator merges what the responder states into the Opportunity (Section 14.6), which is how a contingency known only to the responder reaches the shared result without being disclosed.

```yaml
type: CompatibilityRequest
version: "gidp/0.1"
session_id: "opaque-session-id"
request_id: "r-2"
claims:
  - {claim_id: r-2.0, key: domain,            operator: compatible_with, value: enterprise_software}
  - {claim_id: r-2.1, key: geography,         operator: intersects,      value: [europe]}
  - {claim_id: r-2.2, key: transaction_value, operator: overlaps,        value: {min: 50000000, max: 100000000}}
allowed_results: [compatible, incompatible, conditionally_compatible, unknown, requires_disclosure, declined]
expires_at: "2026-09-21T12:00:00Z"
```

```yaml
type: CompatibilityResponse
version: "gidp/0.1"
session_id: "opaque-session-id"
request_ref: "r-2"
results:
  - {claim_id: r-2.0, key: domain,            result: compatible}
  - {claim_id: r-2.1, key: geography,         result: compatible}
  - {claim_id: r-2.2, key: transaction_value, result: conditionally_compatible}
session_status: open
next:
  permitted: [compatibility_request, disclosure_request, close]
  requires:  []
expires_at: "2026-09-21T12:15:00Z"
```

### 14.4 DisclosureRequest / DisclosureResponse

`DisclosureRequest` required fields: `request_id`, `attribute`, `purpose` (free text or profile code), `requested_surface` (`session` or `network`), `intended_use` (`compatibility_evaluation`, `identity_verification`, `handoff_preparation`, or profile-defined). Optional: `retention` (`session_only`, `until_handoff`, `unrestricted`; SHOULD be present; `until_handoff` retains until the session's Handoff, passes the value to the receiving context the Handoff names, and falls back to `session_only` when the session closes without one; what any stated retention covers, including copies, caches and derivations, is what the statement covers under Section 10.7), `reciprocal` (`true` means the requester will grant the same attribute at the same surface if asked).

`DisclosureResponse` required fields: `request_ref`, `attribute`, `status` (`granted`, `declined`, `granted_if_reciprocal`, `granted_if_verified`, `pending_principal_approval`). When `granted`, the response carries `value` at the granted surface; when `granted_if_verified`, it MUST carry `verification_required`, a non-empty list of credential or attestation classes the requester must supply, expressed as opaque, binding-specific references (Section 20). `granted_if_reciprocal` means the value will be released once the requester has released the same attribute. The word "reciprocal" names a *condition*. The guarantee is limited to sequential exchange, with the first revealer assuming the risk; it provides neither fairness, nor atomicity, nor simultaneous receipt. Where both sides hold a `granted_if_reciprocal` for the same attribute, the session initiator releases first; a policy unwilling ever to reveal first never satisfies the condition, both responses expire, and the exchange has failed explicitly. For two parties each of whom demands that the other move first, that failure is the designed outcome. A profile that needs a stronger guarantee brings its own mechanism (a trusted third party, or a fair-exchange protocol). `granted_if_verified` means the value will be released once the requester has supplied a credential the responder names in `verification_required` (Section 20). A `declined` response MUST NOT indicate whether the attribute exists or what its value is. It follows that an Agent which holds no value for the attribute also answers `declined`. The vocabulary has no way to say "not applicable", because saying it would answer the question the refusal exists to withhold.

```yaml
type: DisclosureRequest
version: "gidp/0.1"
session_id: "opaque-session-id"
request_id: "r-3"
attribute: transaction_structure_class
purpose: "distinguish acquisition from licensing compatibility"
requested_surface: session
intended_use: compatibility_evaluation
retention: session_only
reciprocal: true
expires_at: "2026-09-21T12:20:00Z"
```

### 14.5 ConsentRequest / ConsentResponse

`ConsentRequest` required fields: `request_id`, `action` (`disclose_attributes`, `reveal_identity`, `establish_direct_contact`, `handoff`), `scope` (list of attribute keys or, for `reveal_identity`, the identity attributes requested), `reciprocal` (whether the requester will grant the same scope), `binding_commitment` (MUST be `false` in GIDP 0.1). The field is required, rather than omitted, so that the absence of commitment is explicit on the wire and so that a later version can define the conditions under which it may be `true`; the same reasoning applies to the `COMMIT` authority level (Section 16.1).

`ConsentResponse` required fields: `request_ref`, `status` (`granted`, `declined`, `pending_principal_approval`), `granted_scope` (MAY be narrower than requested; empty when not granted).

Consent MUST be scoped to a session and an action, and the meaning of `scope` is per action: attribute keys for `disclose_attributes` and `reveal_identity`; the target reference of the proposed transfer for `handoff` (Section 14.7); for `establish_direct_contact`, the channel classes the profile defines, or empty. What a `handoff` consent does not yet carry (the receiving system's identity beyond the target reference, the set of information transferred, a duration) is stated in `open-problems.md`; 0.1 binds the consent to the named target and no further. Consent to reveal identity MUST NOT be interpreted as consent to transact. A `ConsentRequest` whose `action` is `disclose_attributes` MAY be sent before the session qualifies, because an attribute classified `session/consent` can be what qualification needs, and without it that attribute could be neither disclosed before consent nor consented to before qualification; its scope MUST NOT include `principal_identity` or any identifying attribute, whose action is `reveal_identity` whatever the message (Section 10.6). Every other action (`reveal_identity`, `establish_direct_contact`, `handoff`) MUST NOT be requested before qualification; this is where the ordering of Section 5 is enforced rather than implied. A consent granted before qualification opens the gate of Section 10.2 for the attributes in scope; it does not advance the session (Section 17.2). A `ConsentResponse` with status `granted` MAY be issued by the Agent without a per-instance human decision only if the Standing Interest's Authority for the corresponding level (Section 16) is `true` and no attribute in scope carries the gate `principal_approval`. The corresponding level of `disclose_attributes` is `DISCLOSE`; that of `reveal_identity` and `establish_direct_contact` is `INTRODUCE`; and that of `handoff` is `INTRODUCE` as well, since a Handoff establishes a direct relationship between the Principals. Where the corresponding level is `false`, the Agent MUST answer `declined`: a refused authority is a refusal, not an approval pending, and answering `pending_principal_approval` would tell the counterparty to wait for a decision nobody will be asked to make. Section 18 gives the same rule for a `DisclosureRequest` received under a `DISCLOSE` level of `false`. Where the level is `approval_required`, or an attribute in scope carries the gate `principal_approval`, the Agent MUST answer `pending_principal_approval` until the Principal decides.

```yaml
type: ConsentRequest
version: "gidp/0.1"
session_id: "opaque-session-id"
request_id: "r-4"
action: reveal_identity
scope: [principal_name, organisation_name]
reciprocal: true
binding_commitment: false
expires_at: "2026-09-22T00:00:00Z"
```

Where the response is `pending_principal_approval`, the Principal's eventual decision arrives as the terminal response to the *original* request, carrying its `request_ref`, and either `granted` or `declined`; the provisional response did not discharge the request and only this one does (Section 14). A Principal who never answers leaves the request outstanding until the request's `expires_at`, which is the correct outcome and is why that field is required. An implementation that emits the provisional response and provides no path to the terminal one has built a gate that can ask the Principal a question but cannot receive the answer.

### 14.6 Opportunity

An `Opportunity` is produced exactly on the transition to `session_status: potentially_compatible`, that is on the state transition `PROBING → QUALIFIED` (Section 17.2), and represents the evaluation as it stood at that moment: probing MAY continue after qualification, but its results do not revise the Opportunity, and a Principal that wants a revised evaluation opens a new session (Section 17.2). The session initiator emits it, and MUST NOT emit it unless the responder's most recent `CompatibilityResponse` reported `session_status: potentially_compatible`: each side evaluates the entry conditions of Section 15.2 over its own view (its own profile requirements included), so the two statuses can differ, and qualification is their conjunction. The responder's reported status is how it confirms, locally and without disclosing why, that its own required checks are done and no known veto stands; an initiator whose view qualifies while the responder's last report does not continues probing, or waits for the response that changes the report; 0.1 adds no status-refresh message. The initiator MUST populate `contingent_on` with the union of its own communicable contingencies and every contingency the responder stated in a `CompatibilityResponse` (Section 14.3). The initiator cannot know the responder's undisclosed dependencies, so an Opportunity built from the initiator's view alone would misstate the responder's evaluation. The responder, on receiving an `Opportunity` whose content does not match its own evaluation, MUST NOT act on it and MUST close the session with `reason: unspecified` rather than correcting it in place. Required fields: `structure` (profile-defined description of the candidate state transition; as non-binding as the Opportunity that carries it, and not an offer of the structure it names), `evaluated_dimensions`, `compatible_dimensions`, `open_conditions`, `contingent_on`, `identity_status` (per side: `not_requested`, `pending_principal_approval`, `granted`, `declined`).

Both Agents are expected to hold the same Opportunity and cannot do so if each counts differently, so the two counts are defined here. `evaluated_dimensions` is the number of distinct claim keys among the propositions standing in this session, in either direction, counting each key once however many propositions asked about it. `compatible_dimensions` is the number of those on which every standing proposition resolved `compatible`; a `conditionally_compatible` result is not counted as compatible. `open_conditions` lists the claim keys on which a standing proposition resolved `conditionally_compatible`, so that `compatible_dimensions` plus the length of `open_conditions` equals `evaluated_dimensions` in any session that qualifies (Section 15.2).

`contingent_on` lists the dependencies named in either side's `conditional_on` (Section 19.1) that the session has not resolved. A required field does not outrank the Disclosure Policy, so what an Agent may put in it depends on how the dependency reached it. A dependency it *learned* (named by the peer in a claim or a disclosure) is already known to the peer and MUST be listed as named. A dependency it *holds* MUST be listed by name only if its Disclosure Policy permits `conditional_on` to be transmitted at the session's depth, with any gate satisfied, when the Opportunity is produced. If the policy classifies `conditional_on` `evaluation_only`, or its gate is not yet satisfied, the Agent MUST instead include the single token `undisclosed`, which tells the recipient that the Opportunity is contingent without saying on what; the bare fact of contingency is a result derived from an evaluation-only attribute, which is what that class permits. If the policy classifies `conditional_on` `never`, the Agent MUST NOT reflect the dependency in `contingent_on` at all, because a flag that exists only because of a `never` attribute is a transmitted result produced from it (Section 10.3). A Principal who classifies a dependency `never` has chosen that the protocol will not represent it, and its own authority over any Handoff (Section 16) is then where the dependency is enforced. A bilateral session can *record* a dependency; it cannot satisfy one, because the party the dependency names is not in the session. Without this field an interdependent Conditional Interest (Section 8.4) produces an Opportunity indistinguishable from an unconditional one: a follower's participation, contingent on a lead investor who does not exist, would read as an assembled round. A non-empty `contingent_on` means the Opportunity is contingent on something outside it, a Handoff MUST carry it forward, and a recipient MUST NOT treat the Opportunity as complete while it is non-empty. Discovering the missing party is multi-party discovery, which Section 19.2 marks experimental.

**What an Opportunity asserts.** An Opportunity asserts that every proposition standing at the moment of qualification, in either direction, was answered with a qualifying result, and that no qualifying result was issued over a responder's own evaluation of `incompatible` (Section 15.5), and nothing else. It does not assert that conditions no claim tested are satisfied; it does not assert that exclusions nobody asked about are absent (Section 19.1); and it does not assert that the evaluated dimensions are *jointly* satisfiable. Readers are likeliest to assume the last. A Principal who accepts Paris with a permanent contract or London with a consulting mandate, and a counterparty who offers Paris with a consulting mandate, overlap on every dimension taken separately and on no configuration taken whole; claims asked dimension by dimension will qualify them. Overlap semantics (Section 14.2) mislead in the same way within a single dimension. A buyer whose private ceiling is 80 and a seller whose private floor is 90 both answer `compatible` to a claim on the range 50–100, in both directions and however many times it is asked, yet no price satisfies both. A profile that needs joint satisfiability MUST express the combination as one claim (a `compatible_with` predicate over the configuration), and a profile whose domain gives an Opportunity operational meaning MUST state the minimum claims, joint predicates included, that a session must have asked before its Opportunities carry that meaning. Those requirements enter the entry conditions of Section 15.2 directly, so a session under such a profile cannot qualify before meeting them. Naming `compatible_with` does not by itself settle this: the profile must say what its predicate tests (the same candidate configuration on both sides, a predicate computable from the information the session may hold, or a private computation the profile brings); otherwise the buyer-at-80 example above survives the predicate's name. Absent such a profile statement, an Opportunity is only a screening result, a lead worth a conversation. It is not a qualification of the Principals' interests, and a recipient MUST NOT present it as one.

```yaml
type: Opportunity
version: "gidp/0.1"
session_id: "opaque-session-id"
structure: "minority investment + distribution agreement"
evaluated_dimensions: 5
compatible_dimensions: 3
open_conditions: [valuation_class, management_condition]
contingent_on: []
identity_status: {initiator: not_requested, responder: not_requested}
expires_at: "2026-09-28T00:00:00Z"
```

### 14.7 Handoff

Required fields: `target` (an object whose `kind` is `human`, `workflow` or `protocol`, with `protocol_ref` REQUIRED when `kind` is `protocol`), `authorized_scope` (subset of authority levels of Section 16 that the handing Agent carries into the target, never including `COMMIT` in GIDP 0.1), `requires_principal_presence` (boolean), `contingent_on` (as in the Opportunity it follows, under the same rule; Section 14.6 requires the Handoff to carry the contingency forward, and without a field it could not).

A Handoff MUST be preceded, in the same session, by a granted consent whose `action` is `handoff` and whose scope names this Handoff's target: the `protocol_ref` where `target.kind` is `protocol`, a binding-specific target reference otherwise. Being in `CONSENTED` establishes nothing about *this* action: consent is per action and per scope (Section 14.5), and a consent granted for `disclose_attributes` or `reveal_identity` does not authorise a transfer. A recipient that receives a `Handoff` no granted `handoff` consent of this session covers MUST close the session with `reason: unsupported`.

A Handoff ends GIDP's responsibility for the interaction. Where `target.kind` is `protocol`, `protocol_ref` identifies the negotiation or agreement protocol that takes over; A2A's negotiation patterns and the mandate objects being specified jointly by [A2CN] and [CONCORDIA] are the intended targets, and a GIDP binding to a negotiation protocol SHOULD map `authorized_scope` onto that protocol's own authority object rather than restating it. A Handoff MUST NOT be construed as conferring authority the handing Agent does not hold (Section 16.2), and the receiving protocol's authority object, not the Handoff, governs what may be committed.

```yaml
type: Handoff
version: "gidp/0.1"
session_id: "opaque-session-id"
target: {kind: protocol, protocol_ref: "negotiation-protocol-uri"}
authorized_scope: [NEGOTIATE_NONBINDING]
contingent_on: []
requires_principal_presence: true
expires_at: "2026-09-28T00:00:00Z"
```

### 14.8 SessionClose

Required fields: `reason` from `{declined, incompatible, unsupported, expired, completed, unspecified}`. `unsupported` is used when the session cannot proceed for a structural reason rather than a substantive one: the declared `profile` is not implemented, or one side cannot proceed without an optional feature the other does not support (Section 21). An empty `features` intersection is not by itself such a reason: the bilateral core is always in force (Section 14.1), and a session that uses no optional feature needs none. An Agent MUST be able to close with `unspecified` and MUST NOT be required to give any other reason.

## 15. Compatibility Semantics and Result Vocabulary

### 15.1 Per-claim results
A response to a claim MUST use exactly one of:

| Result | Meaning |
|---|---|
| `compatible` | The responder's Standing Interest is consistent with the claim. |
| `incompatible` | It is not. |
| `conditionally_compatible` | The responder answers neither `compatible` nor `incompatible`: the claim is not ruled out, subject to conditions the responder does not disclose at this stage. It is not an assertion that the claim holds, and a requester MUST NOT read it as one. |
| `unknown` | The responder answers neither `compatible` nor `incompatible` and names no disclosure that would resolve the claim. It MAY be used because the responder cannot determine the answer, or because it elects not to determine it (Section 15.5); a requester MUST NOT treat it as stating the responder's epistemic state (the norm binds what the result *means*, not what a requester may privately conclude; Section 24.3). |
| `requires_disclosure` | The responder could determine the answer if the requester disclosed the attributes listed in `next.requires`. |
| `declined` | The responder refuses to answer this claim; no reason is implied. |

### 15.2 Session status
`session_status` MUST be one of:

| Status | Meaning |
|---|---|
| `open` | The session is under way and the conditions for `potentially_compatible` are not met, while no claim has resolved `incompatible`. This covers a session in which nothing has yet been evaluated, one with an unresolved entry in `next.requires`, and one in which claims remain `unknown` or awaiting a Principal decision. |
| `potentially_compatible` | Every proposition standing in the session, in either direction, has resolved to `compatible` or `conditionally_compatible`; at least one has resolved `compatible`; no entry in `next.requires` remains unresolved; and the qualification requirements the session's profile states, where it states any (Section 14.6), are met (a profile requiring role and location to be examined blocks the transition until both have been, however positively the first answered). This status is reached at most once per session, and an `Opportunity` is produced on reaching it (Section 14.6). These are conditions of *entry*: they decide the transition, and once the status is reached it is kept: a result recorded after qualification does not retract it (Section 17.2), and the status asserts what stood at the transition. In a session not yet qualified and free of `incompatible`, the status is not reported while a disclosure or a consent is pending: there it is `open`, and the conditions are recomputed on the return to `PROBING` (Section 17.2), so reaching `potentially_compatible` and producing the Opportunity coincide exactly (Section 14.6); after qualification, a pending request leaves the kept status untouched, and an `incompatible` overrides everything above at any moment. |
| `incompatible` | At least one proposition, in either direction, has resolved `incompatible`. It cannot be withdrawn (Section 14.2). |
| `closed` | The session is closed (Section 14.8). |

It maps onto the state machine of Section 17.2 as follows: `open` corresponds to `PROBING`/`DISCLOSURE_PENDING`/`CONSENT_PENDING` (the last for a `disclose_attributes` consent requested before qualification), `potentially_compatible` to `QUALIFIED` and later states, and `incompatible` and `closed` to `CLOSED`. A `potentially_compatible` status asserts no more than an Opportunity does (Section 14.6): that no proposition standing in the session met a contradiction its responder knew of. It does not assert that the Principals are compatible.

A `declined`, `unknown` or `requires_disclosure` result therefore prevents qualification, and this is intended: `declined` is constructed to convey nothing about compatibility to the counterparty (Section 18), although that does not make it information-free to every observer (Section 24.3). An Opportunity that counted it as neutral would rest on silence. A requester that wants to qualify despite such a result asks again with a claim whose `supersedes` names the one it replaces (Section 14.2), or accepts that the session does not qualify. Asking the same question again *without* superseding adds a proposition; it does not replace one. An implementation MUST NOT produce an `Opportunity` from a session in which any standing proposition's result is one of those three.

### 15.3 Operational outcomes
The operational outcomes (`unsupported`, `unauthorized`, `expired`, `rate_limited`, `temporarily_unavailable`) belong to the transport binding and not to the GIDP object set: a binding conveys them through its own error mechanism, and GIDP defines no object for them. They are named here because they are observable by a peer and therefore part of the protocol's information flow; GIDP 0.1 defines no enumeration for them, and an implementation that ships one has added a closed vocabulary this document does not impose. An operational outcome is not a compatibility result and MUST NOT be used to encode one (Section 18); a peer that receives one MUST NOT treat it as conveying anything about the responder's Standing Interest. The protocol can fix what an outcome is defined to mean, though not what a peer statistically concludes from it (Section 24.3). An implementation that has no binding-level error mechanism available MUST use `SessionClose` instead, with `reason: unsupported` or `reason: expired` where one of them describes the outcome and `reason: unspecified` otherwise; the operational outcomes outnumber the close reasons, and no mapping between them is implied.

### 15.4 Local evaluation
A claim MAY be evaluated locally against `evaluation_only` values without exposing them. Example: Agent A privately knows `maximum_valuation = 80M`; asked whether a transaction `overlaps {50M, 100M}` is compatible, it may answer `conditionally_compatible` without exposing `80M`.

A coarsened answer asserts nothing (Section 15.1), but the querent still learns that the range it named is not ruled out, and a querent that names its own candidate value learns the same about that value. This is not a fault of the example but the inference channel of Section 24.3 seen from the asking end, and it is why a responder's protection lies in the abuse controls of that section rather than in the vocabulary alone.

Coarsening protects the value but not the inference. Replacing one truthful result with `conditionally_compatible` whenever the truthful result would have been affirmative substitutes one deterministic answer for another: a querent that knows the policy partitions the responder's possible values in the same way as it would have under an unmodified truthful answer, and learns as much. Measured over an adaptive querent, a deterministic coarsening does not reduce extracted information at all. It remains necessary, because it is what keeps `80M` off the wire, but it is not an inference control; Section 24.3 states what is.

### 15.5 Truthfulness and coarsening
A responder MUST NOT answer `compatible` where its values make the claim false, and MUST NOT answer `incompatible` where its values make the claim true. A responder MAY replace a truthful `compatible` with `conditionally_compatible`, `unknown` or `declined`, and MAY replace a truthful `incompatible` with `unknown` or `declined`. It MUST NOT replace a truthful `incompatible` with `conditionally_compatible`: that result qualifies (Section 15.2), and issued over a claim the responder knows to be ruled out it would let a session reach an Opportunity on a dimension that has already failed. These are the only permitted deviations from the truthful answer, and the asymmetry is what makes an Opportunity mean what Section 14.6 says it means. Whether a given pattern of replacement limits inference is a separate question, answered in Section 24.3 and not by this section: a deterministic replacement conveys the same information as the answer it replaces, and a replacement that conveys nothing also discriminates nothing.

### 15.6 Inseparability from abuse controls
Because local evaluation lets a peer learn something with every answer, compatibility semantics cannot be separated from probing controls. A deployment states how it bounds inference through repeated claims; that obligation is stated once, in Section 23.2 under *Deployment requirements*, and applies to Sections 24.3 and 24.7.

## 16. Authority Model

### 16.1 Levels
Authority is expressed per Standing Interest and MAY differ between Standing Interests held by the same Agent. GIDP 0.1 defines eight levels, from least to most consequential:

```text
OBSERVE               receive projections and candidate references
SEARCH                query Discovery Providers
PUBLISH_PROJECTION    publish a Discovery Projection
PROBE                 open sessions and answer compatibility claims
DISCLOSE              answer DisclosureRequests within the Disclosure Policy
INTRODUCE             reveal identity / establish direct contact
NEGOTIATE_NONBINDING  propose or discuss non-binding structures, after Handoff only
COMMIT                make a binding commitment (outside GIDP 0.1; MUST be false)
```

Each level takes one of the values `true`, `false`, `approval_required` (a per-instance Principal decision is needed each time). Authority MAY additionally be restricted by counterparty, asset, monetary value, jurisdiction, duration, transaction type or disclosure surface.

`NEGOTIATE_NONBINDING` lies outside the Compatibility Session: non-binding structures MUST NOT be proposed inside one. A Compatibility Session establishes whether two Principals should be talking, using the result vocabulary of Section 15 and nothing else; proposing terms, even non-binding ones, is negotiation and takes place after a Handoff (Section 14.7), under whatever protocol the Handoff targets. The level is retained in the GIDP ladder because a Principal must be able to express, in the Standing Interest, whether its Agent may carry that authority forward at all; GIDP does not carry the negotiation.

### 16.2 Invariant
Implementations MAY use a different authorisation model internally. They MUST preserve the following invariant:

> An Agent MUST NOT perform an action at one authority level on the strength of holding a lower one, and MUST NOT perform, or represent to a counterparty that it may perform, a binding commitment on the strength of any GIDP authority. An Agent MUST NOT request or accept an action from its counterparty on the sole ground that the counterparty has previously performed actions of that kind.

Non-inference is necessary but not sufficient. Where an Agent asserts an authority level to a counterparty, that assertion MUST be capable of being evidenced by a referenceable delegation artefact, and a relying party MUST be able to request that evidence before acting on the assertion. Such an artefact is a signed delegation mandate, delegation credential, token-exchange result or equivalent, issued under the Principal's control and verifiable by the relying party (Section 20). An implementation that cannot produce such an artefact MUST represent the level as unevidenced, and a counterparty MUST be free to treat an unevidenced assertion as absent.

This requirement has a legal motivation as well as a hygienic one. Under the doctrine of apparent authority, a principal may be bound by conduct that leads a counterparty reasonably to believe its agent was authorised, and commentators have begun to argue that the doctrine applies to AI agents acting in commerce [DEMOTT2026]. A protocol in which authority is asserted but never evidenced would systematically produce the observable conduct on which such a belief is built. Requiring evidence, and requiring that its absence be visible, is how GIDP keeps exploration from silently becoming authority.

Trust in a counterparty (Section 20) does not imply authority of that counterparty. Where a level is `approval_required`, the corresponding `ConsentResponse` or `DisclosureResponse` MUST be `pending_principal_approval` until the Principal decides (Section 14.5).

### 16.3 Decision order

Sections 10, 14, 16 and 18 each constrain how a request is answered, and an implementer reading them separately can order the checks differently and reach different answers. The order is therefore fixed. On any request received, an Agent MUST decide in this order, stopping at the first row that applies:

| Check | Consequence |
|---|---|
| Session closed, message expired, or context invalid (unknown session, malformed object) | No new effect; operational outcome at the transport and session layer (Section 15.3) |
| The authority level the action requires is `false` | `declined`: a refusal, never `unauthorized` (Sections 14.5, 18) |
| The recipient is outside the audience the attribute's surface permits (Section 10.1) | `declined` |
| The attribute's surface is deeper than the session's depth (Section 14.1) | `declined`, never `pending_principal_approval`, since no approval can widen a session's depth |
| The authority level is `approval_required`, or a gate requires an approval not yet granted | `pending_principal_approval`, or the consent path of Section 14.5 |
| The gate is satisfied and the Disclosure Policy permits the action | The action is permitted, within the granted scope and no further |

The table governs *transmission*: answering with a value, disclosing, consenting, emitting. Local evaluation is not a row in it: a claim over an `evaluation_only` attribute is evaluated under Sections 15.4 and 15.5, and the audience and depth rows constrain what the answer may carry, not whether the evaluation may happen. Only the class `never` forbids the evaluation itself (Section 10.3).

The approval row resolves differently by category of action, and each category has exactly one path. For `DISCLOSE` and `INTRODUCE`, the wire carries the wait: the provisional `pending_principal_approval` of Sections 14.4 and 14.5, discharged by a terminal response. For `PROBE` (an Agent asked to answer claims while its `PROBE` level is `approval_required`), no provisional response exists and none is added: the Agent holds the request locally until its Principal decides, then answers terminally before the request's `expires_at`; a Principal who has not decided by then leaves the request to expire or the Agent to close, which is the same outcome Section 14.5 gives an unanswered consent. Here silence is the protocol's only wait signal, because a provisional "my Principal is deciding whether I may even answer" would itself disclose the shape of the responder's authority.

This order has consequences that are easy to miss. An authenticated session peer is not thereby a member of any network: a `network` restriction (Section 10.1) continues to apply inside a session, and the audience check refuses a session peer that the surface does not cover, however far the session has advanced. Likewise, an approval that arrives late (a Principal answering a `pending_principal_approval` after the session has moved on) MUST be re-checked against the policy and authority in force at the moment of emission, not those in force when it was requested: the check rows run again, and an approval cannot resurrect an action the current policy refuses. Consent opens a limited possibility and waives no other row.

### 16.4 Levels of human control (non-normative)
GIDP is compatible with different delegation levels:

- *Conservative:* Agent discovers; a human approves every disclosure and identity reveal; humans negotiate.
- *Moderate:* Agent discovers and performs bounded probing; a human approves identity reveal; Agent or human negotiates.
- *Advanced:* Agent discovers, probes, discloses within deterministic policy and negotiates non-binding terms; a human approves commitment outside GIDP.

GIDP 0.1 does not require fully autonomous economic agents.

## 17. Lifecycle and State Machines

### 17.1 Standing Interest lifecycle

```text
DRAFT ──► ACTIVE ──┬──► SUSPENDED ──► ACTIVE
                   ├──► EXPIRED
                   ├──► REVOKED
                   └──► SUPERSEDED   (a new version becomes ACTIVE)
```

A Principal may change thresholds (producing a new version), pause exploration, withdraw a Standing Interest, alter its Disclosure Policy, change Agent or revoke authority. On any transition out of `ACTIVE`, the Agent MUST withdraw or update derived projections (Section 12.2) and MUST close open sessions derived from that Standing Interest, unless the Principal has directed that a session continue under the superseding version. Stale interests create both poor matching and privacy risk.

### 17.2 Session state machine

```text
                SessionOpen
                    │
                    ▼
                REQUESTED ──(SessionClose)──────────────────────────┐
                    │ SessionAccept                                 │
                    ▼                                               │
   ┌───────────► PROBING ◄──────────────┐                           │
   │                │                   │ DisclosureResponse        │
   │                │ DisclosureRequest │ (granted / declined)      │
   │                ▼                   │                           │
   │        DISCLOSURE_PENDING ─────────┘                           │
   │                                                                │
   │  Opportunity produced                                          ▼
   └── PROBING ──► QUALIFIED ──► CONSENT_PENDING ──► CONSENTED ──► CLOSED
                       │              │ (ConsentResponse)     │        ▲
                       │              └───────────────────────┘        │
                       │                        Handoff                │
                       │                    HANDED_OFF ────────────────┘
                       └────────────────────────────────────────────────┘
```

The diagram above is illustrative. The following table is normative; an implementation MUST implement exactly these transitions and no others. The state is held per session and per direction of request: each Agent tracks the state of the requests it has sent, so both Agents may hold an outstanding request at the same time without the session having two conflicting states.

The transitions apply to both Agents' views of the session: a responder's state moves on the request it receives and on the response it sends, just as the requester's does. Discharging, however, is one-sided: an Agent discharges only the requests it sent itself (Section 14), because the `request_id` belongs to the sender. An implementation that conflates the two will reject its own peer's traffic.

| From | Event | To | Side effect |
|---|---|---|---|
| — | `SessionOpen` sent or received | `REQUESTED` | — |
| `REQUESTED` | `SessionAccept` | `PROBING` | Session depth and profile fixed (Section 14.1) |
| `REQUESTED` | `SessionClose` | `CLOSED` | — |
| `PROBING` | `CompatibilityRequest` / `CompatibilityResponse` | `PROBING` | `session_status` updated (Section 15.2) |
| `PROBING`, `QUALIFIED` or `CONSENTED` | `DisclosureRequest` | `DISCLOSURE_PENDING` | The state it was sent from is remembered |
| `DISCLOSURE_PENDING` | `DisclosureResponse` with status `granted` or `declined` | the state the request was sent from | — |
| `DISCLOSURE_PENDING` | `DisclosureResponse` with status `pending_principal_approval`, `granted_if_reciprocal` or `granted_if_verified` | `DISCLOSURE_PENDING` | Provisional response; the request is not discharged (Section 14), and a conditional status leaves the attribute undisclosed until its condition is met |
| `DISCLOSURE_PENDING` | terminal `DisclosureResponse` following a provisional one | the state the request was sent from | — |
| `PROBING` | `session_status` reaches `potentially_compatible` | `QUALIFIED` | The session initiator produces the `Opportunity` (Section 14.6) |
| `PROBING`, `DISCLOSURE_PENDING`, `CONSENT_PENDING`, `QUALIFIED` or `CONSENTED` | `session_status` reaches `incompatible` | `CLOSED` | Either Agent sends `SessionClose` with `reason: incompatible` |
| `DISCLOSURE_PENDING`, `CONSENT_PENDING` or `CONSENTED` | `CompatibilityRequest` / `CompatibilityResponse` | unchanged | Probing continues alongside a pending request |
| `QUALIFIED` | `CompatibilityRequest` / `CompatibilityResponse` | `QUALIFIED` | Probing may continue after qualification; its results do not revise the Opportunity (Section 14.6) |
| `PROBING` | `ConsentRequest` with `action: disclose_attributes` | `CONSENT_PENDING` | The only consent that may precede qualification (Section 14.5) |
| `QUALIFIED` | `ConsentRequest` | `CONSENT_PENDING` | — |
| `CONSENT_PENDING` | `ConsentResponse` with status `granted`, request sent from `QUALIFIED` or `CONSENTED` | `CONSENTED` | The granted scope is in force for this session only |
| `CONSENT_PENDING` | `ConsentResponse` with status `granted`, request sent from `PROBING` | `PROBING` | The gate of Section 10.2 is open for the scope; the session does not advance |
| `CONSENT_PENDING` | `ConsentResponse` with status `declined` | the state the request was sent from | — |
| `CONSENT_PENDING` | `ConsentResponse` with status `pending_principal_approval` | `CONSENT_PENDING` | Provisional response; the request is not discharged |
| `CONSENTED` | `ConsentRequest` | `CONSENT_PENDING` | Consent is per action and per scope |
| `QUALIFIED` or `CONSENTED` | `Handoff` | `HANDED_OFF` | A recipient that receives a `Handoff` in any earlier state MUST close the session with `reason: unsupported` |
| `HANDED_OFF` | `SessionClose` | `CLOSED` | `reason: completed` |
| any state | `SessionClose`, or expiry of the session | `CLOSED` | `CLOSED` carries the close reason; expiry uses `reason: expired` |

Probing may continue while a disclosure or a consent is pending (the table's rows leave the state unchanged), so the result that completes qualification can arrive while the session is in `DISCLOSURE_PENDING` or `CONSENT_PENDING`. The rule is only that nothing qualifying happens mid-wait. In a session not yet qualified and in which no `incompatible` stands, `session_status` remains `open` while a request is pending (Section 15.2), and the transition to `QUALIFIED` is defined only from `PROBING`. An `incompatible` recorded during the wait is not held back: it closes the session by the table's own row, mid-wait included. A wait after qualification (`QUALIFIED → CONSENT_PENDING → CONSENTED` is the normal path) changes nothing: the status was kept at the transition (Section 15.2) and stays `potentially_compatible` throughout. When the pending request's terminal response returns the session to `PROBING`, an implementation MUST recompute the entry conditions of Section 15.2 over the propositions standing *at that moment*, rather than remember a condition met mid-wait, since a further result arriving during the same wait counts too, and an `unknown` recorded at step three undoes a qualification reached at step two. Where the recomputed conditions hold, status, state and Opportunity advance together, before any further message is sent; an implementation that fails to re-evaluate on the return has silently lost the transition.

A disclosure or a consent is a request made *within* a stage of the session, not a stage of its own, so answering it returns the session to the stage it was asked in. (The failure this rule prevents is worked through in `rationale.md`.) Qualification is reached at most once per session. A result recorded after it does not retract the Opportunity, which asserts the evaluation at the moment of the transition (Section 14.6): `incompatible` closes the session by the row above, and any other result leaves it `QUALIFIED`, with the Opportunity standing and no second one produced. An Agent that wants the evaluation redone (because an interest changed, a condition lapsed, or a post-qualification answer altered the picture) opens a new session; the disclosure budget of Section 24.3 is kept per Standing Interest, not per session, so the new session begins with the ledger the old one left (Section 24.3). A session evaluates one candidate configuration (the interaction its `purpose` and profile frame), and its results are propositions about that candidate. This is what justifies the closure rule: an `incompatible` is a known contradiction *of this candidate*, and the session ends because its object is refuted, not because the Principals are. An executive who refuses Paris but would take London has not been rejected; the Paris session has. The alternative is explored either inside one session by asking wider, since a set (`intersects [paris, london]`) or a range is one claim over several possibilities (Section 14.2), or in a new session for the other candidate, against the same per-Standing-Interest budget (Section 24.3), which is also why closure does not hand an adversary a bisection tool: reopening costs it nothing the budget has not already counted. Closing the whole session on one `incompatible` is a 0.1 simplification chosen over partial invalidation, and it is bearable because the candidate a session evaluates is named by its opening rather than discovered by its claims. A `declined` `DisclosureResponse` does not close the session. `CLOSED` is terminal: an Agent MUST NOT reopen a closed session, and a new interaction requires a new `session_id`.

## 18. Error and Non-Disclosure Semantics

Errors require special care because they can become privacy oracles. An implementation MUST distinguish operational outcomes (Section 15.3) from compatibility results (Section 15.1) and MUST NOT use the former to convey the latter.

A responder MAY answer `declined` rather than `incompatible` whenever distinguishing "incompatible" from "not authorised to evaluate" or "not willing to disclose" would leak protected information; a requester MUST NOT treat `declined` as `incompatible`: the norm fixes what the result means in the protocol, and Section 24.3 sets out what an observer may nevertheless conclude. A refusal that follows from the responder's own Authority or Disclosure Policy (for example a `DisclosureRequest` received by an Agent whose `DISCLOSE` level is `false`) MUST be reported as `declined`, never as the operational outcome `unauthorized`, which is reserved for the transport and session layer (rejecting a message the peer was not entitled to send at all). Failure to progress MUST NOT convey *why* a compatibility test failed unless the Disclosure Policy explicitly permits that information. Response timing SHOULD NOT vary systematically with the value of a protected attribute (Section 24.7).

## 19. Dependency Primitives and Multi-Party Discovery (Experimental)

### 19.1 Dependency primitives (core)
A Standing Interest MAY carry four generic relationship lists: `provides` (what the Principal can bring), `requires` (what it needs from others), `conditional_on` (events or commitments that must hold), `excludes` (counterparties, structures or conditions ruled out). They are part of the core Standing Interest model and MAY be used in bilateral sessions (e.g. `requires: capability X` matched against `provides: capability X`, Appendix C.3). Only `excludes` MUST be supported by every implementation; the other three MUST be supported by implementations that declare the `dependency_primitives` feature (Section 14.1).

None of the four is self-enforcing, and this matters most for `excludes`. An Agent that declares `excludes: X` has recorded a disqualifying property; it has not caused anything to test for it. A counterparty that never asks never learns, and a session in which nobody asked can qualify and produce an Opportunity between two parties one of which excludes a property the other has. This is the same shape as the contingency gap of Section 14.6, and it is left as a duty on the Agent rather than a mechanism: an Agent holding `excludes` SHOULD ask the corresponding claim before qualifying, and an Opportunity asserts nothing about exclusions no claim tested.

Nor is `excludes` the negation of `requires`. *Requires X* says the Principal needs X present; *excludes X* says X is disqualifying whoever supplies it. The negation of the first is "does not need X", which is not the second, and a profile that collapses them will produce Opportunities its Principal would refuse.

The four names are **reserved claim keys**: a claim (Section 14.2) naming one of them is resolved against the corresponding list rather than against the Conditional Interest's conditions, which is what makes the bilateral use above reachable. The Disclosure Policy classifies them like any other attribute (Section 10), and the expected pattern is asymmetric. What a Principal *provides* is ordinarily disclosable, since it is what makes the Principal findable at all. What it *requires* is the mirror image of what it lacks, and a capability gap admitted to a prospective partner is admitted to a prospective competitor; a Principal will therefore commonly classify `requires` as `evaluation_only`, so that "do you require X?" is answered truthfully but coarsened (Section 15.5) while "do you provide X?" is answered directly.

Example (non-normative):

```yaml
conditional_interest:
  action: {acquire: "asset_class:commercial_property"}
  requires:
    - {type: financing, amount_min: 7000000}
    - {type: occupancy, percentage_min: 60}
  provides:
    - {type: ownership_transition}
  conditional_on: [financing_confirmed, occupancy_above_60]
  excludes:
    - {counterparty_class: restricted}
```

### 19.2 Multi-party discovery (experimental, non-normative)
Some Opportunities cannot be expressed as a bilateral intersection:

```text
A invests if B acts as lead investor.
C acquires an asset if D commits as anchor tenant.
E joins a company if financing round F closes.
G finances an acquisition if the seller retains 20 %.
```

Such structures form chains (`A willing_if B; B willing_if C; C willing_if A`) in which no bilateral pair necessarily forms a viable transaction while the set may be jointly satisfiable. Implementations that declare the `multi_party` feature MAY experiment with discovering sets `{M1 … Mn}` such that `constraints(M0, M1 … Mn)` are potentially satisfiable. GIDP 0.1 defines no coalition solver, distributed constraint protocol or multi-party privacy model; the data model is designed not to preclude them.

A practical way to avoid combinatorial explosion is *dependency-driven expansion*: expand only when a bilateral candidate reveals an unmet dependency (A matches B on its core interest, but B has an unresolved `requires: financing`; the implementation then searches for a C that `provides: financing` compatible with both). Coalition scoring, disclosure across members with different policies, circular conditions and partial-coalition reveal are open questions (Appendix E).

## 20. Trust, Credentials and Reputation

GIDP 0.1 does not define identity infrastructure. Implementations SHOULD be able to distinguish trust levels of counterparties and let Disclosure Policies depend on them (Section 10.5).

Possible trust inputs: authenticated Agent endpoint; signed Agent metadata; verified organisation or individual; known intermediary; reputation; prior successful interactions; membership of a private registry; economic stake; contractual relationship.

Some claims depend on facts that should be verifiable without being fully disclosed: accredited-investor status, revenue range, professional qualification, authorisation to represent an organisation, ownership of an asset, geographic eligibility, available financing. An implementation MUST be able to carry references to external identity, credential, attestation, selective-disclosure and delegated-authority systems, as opaque, binding-specific references carried in `SessionOpen.trust_context` and in `DisclosureResponse.verification_required`. Such systems include selective disclosure of signed claims [RFC9901] [BBS], verifiable-credential proofs [VC-DI], delegated authority obtained by token exchange [RFC8693], workload and agent identity [WIMSE-AI], and external transaction-authorisation objects of the kind noted in Section 3. This document defines no identity system of its own, and an implementation MUST NOT require one specific external system as a condition of interoperating.

One such system is already published rather than prospective. GNAP [GNAP], a Standards Track RFC, defines how a piece of software negotiates delegated authority with an authorisation server and how the result is conveyed, covering both access to resources and subject information. Its grant is negotiated and continuable rather than a fixed scope string, which is the shape Section 16's ladder needs, and it is the natural referent for the delegation evidence that Section 16.2 requires. GIDP neither profiles it nor depends on it; naming it is meant to save an implementer the search.

Which external systems supply persistent agent identity, ownership, delegation chains, attestations, reputation and revocation is outside this specification. The gap is real: a GIDP deployment cannot enforce Section 16.2 without at least one such system, and none of them is yet dominant. Sections 20 and 24.5 state what GIDP requires of whichever system is chosen; the choice itself belongs to the binding and the deployment.

## 21. Extensions and Domain Profiles

GIDP Core avoids embedding vertical concepts. A *domain profile* MAY define vocabularies (claim keys, categories, buckets), validation rules, credential requirements, compatibility dimensions, regulatory constraints, additional claim operators and Handoff semantics for domains such as employment and executive recruiting, M&A, investment and co-investment, real estate, commercial partnerships, joint ventures, licensing, procurement, private expertise, research collaboration, financing, insurance, philanthropy and business succession.

A profile MUST NOT weaken the core privacy and authority semantics of Sections 10, 15.5, 16 and 24. A session uses exactly one profile, declared in `SessionOpen` and confirmed in `SessionAccept` (Section 14.1). A responder that does not implement the declared profile, or that cannot proceed without a feature outside the intersection of declared features (Section 14.1), MUST answer `SessionClose` with `reason: unsupported` (Section 14.8) and MUST NOT propose an alternative profile in that response; richer extension negotiation is future work.

A core research question is whether approximately the same protocol mechanics survive across domains; if every vertical requires a fundamentally different state machine, disclosure model and compatibility model, GIDP may not warrant a horizontal protocol (Appendix F.2).

## 22. Transport Bindings and Adjacent Layers

### 22.1 Binding requirements
GIDP is transport-independent; bindings MAY be defined separately. A binding MUST NOT require Standing Interests or any `session`/`local` attribute to be published in the host protocol's discovery metadata, and SHOULD NOT redefine the host protocol's transport, authentication, task lifecycle or generic messaging semantics.

### 22.2 A2A binding sketch (non-normative)
The most likely first binding is an extension of an agent-to-agent protocol such as A2A [A2A]. A2A version 1.0 declares extensions in the Agent Card's `capabilities.extensions` array (§4.4.3 `AgentCapabilities`), each entry being an `AgentExtension` (§4.4.4) with the fields `uri`, `description`, `required` and `params`. A GIDP implementation could advertise support as:

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://gidp.dev/extensions/gidp/0.1",
        "description": "Graduated Interest Disclosure 0.1",
        "required": false,
        "params": { "profiles": ["core"] }
      }
    ]
  }
}
```

`required` is false by design. An Agent that made GIDP mandatory would refuse every counterparty that speaks plain A2A, which is the opposite of what a discovery protocol is for.

Declaring an extension does not activate it. A client that intends to use one sends the `A2A-Extensions` header carrying a comma-separated list of extension URIs, and the responder echoes back the subset it actually activated; an extension that was not echoed is not in force, whatever the Agent Card says. This matters for GIDP more than for most extensions, because it is the point at which an exchange can be refused before any GIDP object exists, and therefore before any Disclosure Policy has been consulted.

GIDP objects are then carried in the `metadata` map of A2A's core structures, under keys prefixed by the extension URI, following A2A's own convention, which keeps extensions from colliding and leaves core types unmodified. A2A also allows structured data in a message Part, so the choice is not forced by the data model. It is made because a GIDP object governs the exchange rather than forming its content: a Part is what a receiving agent passes to its model as conversation, and Section 6.10 requires the decisions GIDP objects carry to be made outside the model. Keeping them in `metadata` keeps them out of what A2A frames as conversational content; it does not by itself keep them out of any prompt, since nothing in A2A stops an application from feeding metadata to its model. The separation Section 6.10 requires is enforced by the GIDP implementation; carrying the objects in `metadata` makes that enforcement natural, and is not a substitute for it.

Two negotiations are now in play, and neither subsumes the other. A2A activation answers *does this peer speak GIDP at all*; the `features` of Section 14.1 answer *which optional GIDP features are in force for this session*, and Section 14.1 requires `SessionAccept` to carry the intersection actually supported rather than an echo. A peer may activate the extension and support no optional feature whatever. An implementation that derives one from the other will be wrong in the direction that matters, by assuming a feature is in force because the extension was activated.

The extension URI above is illustrative: GIDP 0.1 allocates no URI and registers nothing (Section 26), and two deployments that pick different URIs will not interoperate, which is an argument for allocating one before there are two. The binding itself is not defined here. Whether GIDP is ultimately an A2A extension, a separate protocol or a reusable application profile is an open governance question (Appendix E). A worked mapping, with round-trip tests against every object that crosses a wire, is in the reference implementation under `impl/gidp/bindings/a2a.py`.

### 22.3 Tool and context protocols
An Agent MAY use a tool/context protocol such as MCP [MCP] to obtain the local context required to construct or evaluate a Standing Interest. That interaction is outside GIDP.

### 22.4 Adjacent layers
A conceptual stack, describing logical responsibilities rather than mandatory implementation layers:

```text
Applications          personal agents / enterprise agents / CRM / ERP / ATS
        │
Graduated Interest Disclosure (GIDP)          ← this document
        │
Negotiation / agreement protocols        (after GIDP Handoff)
        │
Authority / credentials / payments       (referenced, not redefined; Section 20)
        │
Agent-to-agent communication             (transport for GIDP)
        │
Tool / data / context access
```

GIDP addresses the stage before the layers around it: *whether two Principals should be negotiating at all*, without publishing the information that would normally make that discoverable. Appendix D states the distinction from capability discovery once, for the whole document.

## 23. Interoperability and Conformance

### 23.1 Interoperability
A GIDP implementation SHOULD allow Agents from independent vendors or platforms to participate. Interoperability in 0.1 requires agreement on: object semantics and required fields (Section 14); disclosure surfaces and gates (Section 10); the result vocabulary (Section 15); authority level names (Section 16); expiry and close semantics (Sections 14.8, 17); the profile identifier (Section 21).

### 23.2 Conformance criteria
An implementation claiming **GIDP Core 0.1** conformance MUST:

1. express all four situations of Section 8 and run a session for each, the four differing only in their Standing Interests: conditions, Disclosure Policies and, for the interdependent situation, declared dependencies. The sessions need not produce identical object sequences, since different situations legitimately ask different questions; what the criterion demands is that no disclosure, authority or session rule apply differently across the four. The interdependent situation exercises the `dependency_primitives` feature; an implementation that omits that feature (permitted below) demonstrates the other three and says so. "Verified by local inspection" is not a conformance criterion; this one is executable, and it is the criterion that carries the horizontality claim of Appendix F;
2. never transmit a Standing Interest, a Disclosure Policy, or any attribute of surface `local` (Sections 9.1, 10);
3. enforce Disclosure Policies and Authority outside unconstrained model behaviour, such that for any transmitted object the decision to transmit it is reproducible from the Standing Interest, the Disclosure Policy, the session state and the disclosure budget's ledger (Sections 6.10, 24.3, 24.10);
4. generate Discovery Projections that satisfy the required fields and the content rule of Sections 11.1 and 11.2;
5. support at least one Discovery Provider mechanism through which a projection can be published, updated, withdrawn and retrieved, with withdrawal observable within the provider's published latency (Section 12.2), and never treat retrieval as compatibility, consent or agreement;
6. implement the session objects of Section 14 with their required fields, the result vocabulary of Section 15 and the state machine of Section 17.2;
7. respect the truthfulness bounds of Section 15.5;
8. allow an Agent to decline any claim and close any session with `reason: unspecified`;
9. before disclosing an attribute whose gate is `consent`, require a `ConsentResponse` with status `granted` covering it; before disclosing an attribute whose gate is `principal_approval`, require a per-instance Principal decision, conveyed by a terminal `DisclosureResponse` or `ConsentResponse` following a provisional `pending_principal_approval` (Sections 10.2, 14, 14.5);
10. implement the authority levels of Section 16 with `COMMIT` fixed to `false` and preserve the invariant of Section 16.2;
11. on suspension, revocation, expiry or supersession of a Standing Interest, withdraw or update every projection derived from it, and close every open session derived from it unless the Principal has directed otherwise (Sections 9.2, 17.1);
12. emit a `Handoff` with the fields of Section 14.7 when the Principal or an Agent with the corresponding authority directs it, and treat the session as terminal thereafter;
13. implement the closed vocabularies of Section 26 without extension.

Conformance to criteria 6 and 13 is testable against transmitted objects; criterion 3 is testable by checking, for each transmitted object, that its emission satisfies the authorisation invariants given those inputs. Byte-identical replay of a whole session is sufficient evidence where it holds, but is not required: a budget shared across sessions and any randomised refusal policy make a lone session's replay underdetermined without the ledger.

**Deployment requirements.** Separately from the criteria above, which concern interoperability, a deployment of GIDP MUST publish a deployment-specific privacy and probing threat model stating how it bounds inference through repeated claims (Sections 15.6, 24, 24.3). This is a condition of responsible deployment, not of protocol conformance; the body refers to this paragraph instead of repeating it.

Implementations MAY omit the `dependency_primitives` and `multi_party` features.

### 23.3 Reference implementation goals (non-normative)
A minimal reference implementation demonstrates: two independently running Agents; several local Standing Interests per Agent; Discovery Projections; a Discovery Provider or equivalent; candidate retrieval; a structured Compatibility Session; at least one locally evaluated `evaluation_only` condition on each side; progressive disclosure; consent; identity reveal or Handoff; revocation of a projection; and logs showing that `local` attributes were never transmitted. A stronger implementation pairs one personal Agent with one enterprise-style Agent and shows that the Opportunity could not have been discovered from public capability metadata alone. A multi-party demonstration is optional.

## 24. Security Considerations

Security and privacy are core protocol concerns here, since the protocol's purpose is to carry information whose disclosure is the harm. A deployment publishes a threat model covering the threats below; that requirement is stated in Section 23.2 under *Deployment requirements*. This section follows the guidance of [RFC3552].

### 24.1 Harvesting and enumeration of interests
An attacker attempts to enumerate latent sellers, candidates, investors, buyers or strategic interests. Mitigations: Section 12.5 provider controls; coarse candidate sets; no bulk export.

### 24.2 Identity inference and correlation
An attacker combines projection metadata with external information, or correlates projections across providers, to infer the Principal. Mitigations: projection minimisation (Section 11.4); avoidance of stable identifiers and unnecessary metadata; distinct projections per provider (Section 11.5); symmetric attributes.

### 24.3 Constraint extraction by probing
An attacker uses repeated claims to approximate a hidden reservation value (`overlaps {50M,60M}? compatible — {60M,70M}? compatible — {70M,80M}? compatible — {80M,90M}? incompatible`). Even though the threshold is never transmitted, it has effectively been disclosed. Implementations SHOULD apply, within the bounds of Section 15.5: query budgets; rate limits; minimum claim granularity (bucket width); bucketed or randomised responses; session-level privacy budgets; trust tiers; authenticated counterparties; query history and coordinated-probing detection across identities; refusal policies; delayed responses; disclosure accounting; local policy engines. GIDP 0.1 does not define a universal privacy-budget algorithm.

An older literature addresses this decision; it was not consulted when this section was first written. *Query auditing* asks whether to answer or deny a query given the history of queries already answered, and [KMN2005] establishes that denials leak. An auditor that decides to deny based on the data it is protecting tells an attacker something by denying, and the paper's worked example recovers a database exactly from one answer and one refusal. Their repair is *simulatable auditing*: the decision to answer or deny must depend only on the queries asked and the answers already given, never on the data and never on the answer being withheld. An attacker who can reproduce the decision learns nothing from it.

Read against that, the coarsening illustrated in Section 15.4 is not simulatable. It replaces an answer *when the truthful answer would have been affirmative*, so the choice to coarsen is itself a function of the secret, and it carries the same bit the answer would have carried. This explains the measurement reported below, and the point generalises: within this protocol, any rule for coarsening or declining that consults the responder's own values is a channel, and one as wide as the answer it replaces whenever, as here, it relabels answers without merging them. A responder that wishes to conceal must decide from the claims asked and the answers already given, never from its values. The information budget described below does this.

The same literature also limits what can be expected. Deciding auditability is computationally hard in general: [KMN2005] reports the offline maximum sum and maximum max auditing problems to be NP-hard, with related Boolean formulations coNP-hard. This specification should not expect anyone to supply a universal, efficient auditor.

Those mitigations do not all do the same work. Measured against an adaptive querent that asks whichever claim best splits its remaining hypotheses and re-asks it when the answer was uninformative: a deterministic coarsening of the kind illustrated in Section 15.4 bounds nothing, because it relabels answers without merging them; a randomised response delays the querent and does not bound it, since repetition recovers what randomisation hid, and it costs discrimination, since a coarsened refusal reads as a maybe; and a policy that answers `declined` to every claim over a private attribute leaks nothing and qualifies no one. (Its `conditionally_compatible` twin, used as a comparator in the measurements here, is not a conforming policy, because Section 15.5 forbids that answer where the truth is `incompatible`; it appears in the comparison only as a bound.) Claims are the wrong unit: a budget counted in claims cannot separate the two populations, for a reason that is arithmetic rather than adversarial. An honest counterparty asking whether its ceiling clears a threshold asks one question over a wide band and learns a fraction of a bit, while a probing counterparty asks a narrowing sequence in which each question costs a full bit, because that is what a bisection is. The two overlap when counted in questions and are distinct populations when counted in information.

A responder can therefore budget what it discloses rather than what it answers, and the mechanism for doing so is the one [KMN2005] prescribes. The responder keeps the posterior an observer would hold (the set of values still consistent with every answer it has given) and, before answering a new claim, asks what that posterior would become under every answer it might give, refusing if the worst case would cross its budget. Taking the worst case is what keeps the decision independent of the value: it depends only on the claims asked and the answers already given, so an observer can reproduce it and a refusal carries no information about what is being protected beyond what that observer's view of the history already allows. As a consequence, an observer who did not see earlier exchanges (a fresh identity, say, asking after answers given to someone else) can learn from a refusal a distinction the responder had already revealed to another party. It learns nothing the budget had not already been spent on, but "a refusal teaches nothing" holds only relative to a history. The worst case is chosen for this property, and it is not economical: a question that splits 32 candidates 31 to 1 costs a fifth of a bit on average and five bits in the worst case, so a worst-case budget refuses some questions that are cheap on average. How cleanly it separates honest counterparties from probing ones therefore depends on how honest questions are shaped in a domain, and the measurements below hold for the worked distribution of `alternatives.md`, not in general. Were a responder to refuse because of its own value, the refusal would itself be the leak it was meant to prevent.

This is the mitigation to implement first, for the following reasons. It needs no identity, no third party and nothing carried between sessions but the responder's own record, so Section 24.4 does not defeat it, provided the record is kept per Standing Interest rather than per session (a record kept per session is reset by opening another one). The posterior is the responder's, and it does not matter who asks or under how many names. It cannot be evaded by disguising the sequence, because the accounting is over information rather than over pattern. It is also automatic, which none of the other mitigations in this section are.

Measured over a five-bit threshold, a two-bit budget holds a probing counterparty to under one bit while serving most honest counterparties; the ones it refuses are those asking narrow bands, which is correct, since a precise question is the expensive kind. Implementations SHOULD budget disclosure per attribute in this way, and SHOULD publish nothing about the budget's state, which an observer can compute for itself.

A second control composes with it and has the opposite shape. A profile MAY require every claim's bounds to fall on a lattice of a defined width. Because a private bound is tested at the *edge* of the band asked, constraining the width of a band achieves nothing, whereas constraining where edges may fall caps the resolution at `log2(range / width)`, whatever number of claims is asked. It holds no state, so honest traffic does not deplete it and an adversary cannot drain it, and its cost falls on precision rather than on service: a counterparty rounds its question to the lattice and is answered. Measured on a five-bit threshold, a lattice a fifth of the range wide holds a probing counterparty to under half the secret while answering every honest counterparty, where a budget holding it lower refuses one in eight. Neither dominates the other; a deployment chooses which cost it prefers, or composes both.

A related deployment practice is nearly free and not otherwise obvious. A bound on the *rate* rather than the total makes extraction take time, and a private value that is revised over that time is a moving target: what an adversary narrows between revisions, it loses at the next one. Measured against this document's own evaluator, the surviving uncertainty settles at roughly `2d / (2^r − 1)` candidate values, where `r` is the claims answered per period and `d` is how far the value moves in one. The form of that expression cuts against the obvious reading: the protection is *exponential* in the rate allowed and only *linear* in how fast the value moves, so halving the rate is worth far more than doubling the drift, and against a competent adversary a slow drift buys almost nothing. Drift does help against an adversary that does not model the movement at all: such an adversary ends up confident and wrong instead of uncertain, which is a worse position to act from. A Principal that re-authors its Standing Interest when its validity expires (Section 9.2) is therefore taking a privacy measure as well as keeping records tidy. The protocol provides none of these bounds; a deployment can choose any of them. Rate limits, granularity floors and session budgets are all forms of it. Its known weakness is that a budget keyed to a counterparty does not bound an asker that faces many counterparties, and a budget keyed to the asker requires a persistent identity, which this protocol by design does not carry. The measurements behind this paragraph, and the mechanism comparison they come from, are in the companion document *Why not use an existing mechanism?* (`alternatives.md`); they are reproducible from the reference implementation.

This threat has a formal treatment in [RANI2026], which formalises *behavioural privacy leakage* in agentic negotiation (the inference of private constraints from negotiation dynamics rather than from disclosed values) and mitigates it with a phase-adaptive randomised policy achieving (ε,δ)-differential privacy while preserving convergence. That work models a passive adversary observing traces, and explicitly leaves adaptive and active adversaries to future work. GIDP's adversary is the active case: a counterparty that *chooses* the next claim in order to narrow a threshold, against an oracle that is obliged by Section 15.5 to answer truthfully or not at all.

The budget is only as strong as its persistence. It is kept per Standing Interest (not per session, per counterparty or per process), and an implementation MUST NOT allow any of the following to restore spent budget: opening a new session (Section 17.2), a restart or crash of the Agent, or the existence of a copy or replica of the same Standing Interest; replicas share one ledger, or else they are distinct budgets that an adversary sums. Two requests decided concurrently MUST NOT each be admitted against the same remaining balance; the reservation is part of the decision, not of the answer. GIDP 0.1 states these as requirements and leaves their realisation (durable ledgers, replica coordination) to implementations; the reference implementation keeps a single in-process ledger, meets them only within one process, and is on this requirement a demonstration rather than a conforming deployment.

> **Open problem — adaptive probing of a truthful compatibility oracle.**
>
> Let a responder hold a private constraint set *C* over attributes of a Standing Interest. A querent submits claims *q₁, q₂, …* adaptively: each *qᵢ* may depend on every answer received so far. The responder answers under Section 15.5, which permits exactly three behaviours per claim (the truthful result, a coarsening of it to `conditionally_compatible` or `unknown`, or `declined`) and forbids any answer that asserts what the responder's values contradict.
>
> A mechanism is a (possibly randomised) responder policy. Two quantities are in tension. **Leakage** is what an adaptive querent learns about *C* after *k* claims, measured as the reduction in the uncertainty set of *C*, or in the differential-privacy sense of [RANI2026] extended to an adaptive adversary. **Utility** is the probability that a session between two genuinely compatible Principals reaches `potentially_compatible` (Section 15.2) within a bounded number of claims.
>
> The open problem is to exhibit a responder policy, or prove that none exists, that bounds leakage under adaptive querying while keeping utility above a usable threshold, with three properties that distinguish it from the solved cases: the adversary chooses its queries rather than observing a trace, the responder must remain truthful in the sense of Section 15.5 rather than free to lie, and the bound must hold across sessions and identities, since an adversary may split its budget over many Sybil counterparties (Section 24.4).
>
> Three neighbouring results do not settle it. [RANI2026] bounds leakage from *observed negotiation dynamics* against a passive adversary and explicitly leaves adaptive adversaries to future work. Differentially private query mechanisms bound leakage under adaptive querying but assume the responder may return a perturbed answer, which Section 15.5 forbids where the perturbation would assert a falsehood. Private set intersection and secure computation hide the responder's inputs from the querent but not the information carried by the *result*, which is the leak in question.
>
> GIDP 0.1 states this as the protocol's principal research question and does not claim to solve it, and treats the abuse controls above as engineering mitigations, not guarantees. Section 15.6 states the corresponding protocol-level consequence: a result vocabulary and its abuse controls cannot be specified independently of each other. Candidate directions, none of them validated, are discussed in the companion document *Open Problems and Design Rationale* (`open-problems.md`, Part I); contributions and refutations are both welcome.

### 24.4 Sybil agents
An attacker operates many Agents or Principals to bypass query limits or obtain different disclosure views. Identity, credential, reputation, staking, economic or membership mechanisms MAY be used.

This threat and the mitigation of Section 24.3 cancel each other, and the cancellation can be measured. A query budget keyed to the counterparty bounds only the product of the budget and the number of counterparties an attacker can mint: in the worked case of `alternatives.md`, an allowance of two claims per counterparty and four identities extracts exactly what an allowance of eight and one identity extracts, because nothing in this protocol connects the two. The cause lies in the design itself: the property that keeps a responder from profiling its counterparties (opaque endpoints) is the same one, seen from the other side. An Agent that cannot recognise who it is talking to cannot recognise that it is being enumerated.

A cap on the responder's *total* answered claims, to anyone, over the life of a Standing Interest, cannot be diluted by identities and does bound. Its price is that it cannot distinguish the populations it is rationing, and where the cap should sit can be computed. An honest session costs one claim per attribute it asks about; an extraction costs one bisection per *private* attribute, which is logarithmic in the number of values that attribute may take. A separating cap exists when the second exceeds the first, so the window opens as the secret grows and closes as it shrinks: over 41 candidate values and a five-claim session there is no separating cap at all, while over 128 there is, and over a thousand the window is wide. A deployment that wants its budget to mean something computes that ratio for its own attributes instead of inheriting a number. Deployments SHOULD state which of the two they have chosen and at what level; GIDP 0.1 defines neither, and an implementer should not read Sections 24.3 and 24.4 together as describing a solved problem.

### 24.5 Fraudulent projections and unauthorised delegation
Agents may publish fraudulent or low-intent Discovery Projections to harvest information or spam Principals, or claim authority they do not hold. Mitigations: verified authorisation to represent (Section 20); reputation; economic cost; the invariant of Section 16.2.

### 24.6 Replay and stale state
All transmitted objects carry `expires_at` (Section 14) and SHOULD carry replay protection in the binding; revoked Standing Interests MUST NOT remain discoverable (Section 17.1).

### 24.7 Timing and behavioural leakage
Projection creation, withdrawal or response timing may reveal events; acceptance, rejection, counter-proposals and repeated interactions can reveal price thresholds, urgency, preferred counterparties, strategic priorities, willingness to relocate, compensation floors or risk tolerance even when explicit values remain secret. Implementations SHOULD include behavioural leakage in their threat model and MAY use coarser response classes, privacy budgets, randomised response within the bounds of Section 15.5 [RANI2026], minimum uncertainty sets, delayed escalation, trusted brokers or cryptographic threshold proofs.

### 24.8 Unauthorised disclosure
Agents MUST enforce Disclosure Policies before returning protected information; sensitive disclosure actions SHOULD be auditable (Section 25.3).

### 24.9 Compromised Agents
GIDP cannot protect a Principal from an Agent that is fully compromised and holds plaintext access to all of the Principal's secrets. Implementations SHOULD minimise the information and authority available to any single component.

### 24.10 Over-disclosure by model behaviour and prompt injection
An LLM-driven Agent may reveal information not permitted by the formal policy, and counterparties may attempt to manipulate an Agent into ignoring local disclosure or authority rules. Disclosure and authority enforcement MUST be implemented by a deterministic policy layer outside unconstrained model behaviour: the model reasons, the policy layer decides what leaves the Agent. Model-level alignment is not a substitute: information-flow control enforced outside the model has been shown necessary because instruction-level defences do not bound what a model discloses under adversarial input [FLOWSEAL].

### 24.11 Discovery Provider as adversary
A provider sees every projection and query it serves. Implementations SHOULD assume a curious provider, MUST keep every attribute of surface `session` or `local` off providers, MUST keep `network` attributes off providers outside the trust domain, and MAY use the privacy-preserving architectures of Section 12.3 when the provider is not trusted.

### 24.12 Privacy-preserving computation
Depending on sensitivity and deployment model, implementations MAY use local evaluation, trusted intermediaries under contractual or technical controls, trusted execution environments, private set intersection (where compatibility is set intersection) [PSI-SLR], secure multi-party computation (including the privacy-preserving stable-matching constructions that have been demonstrated at national-registry scale [SSM-CCS16]), zero-knowledge proofs (e.g. "threshold satisfied" without revealing threshold or value), encrypted indexes, privacy-preserving retrieval [PIR-SURVEY] or attestations. No single technique is likely to fit all Standing Interest types; the protocol specifies desired information-flow properties before standardising a mechanism. A trusted intermediary under contractual controls differs from the other options above, because it trades away the no-custodian property that distinguishes the core from the venue systems of Section 1.1. Nothing in GIDP forbids the trade (absence of a custodian is an architectural property of the core and not a promise every deployment keeps), but a deployment that makes it MUST say so in its published threat model (Section 23.2).

## 25. Privacy Considerations

This section follows [RFC6973]. GIDP is specifically intended for information that Principals may be unwilling to publish; privacy failures may therefore be more damaging than ordinary search or recommendation errors.

### 25.1 Governing principle
*Reveal the minimum information required to justify the next authorised step.* A compatibility result MUST NOT reveal the underlying private value unless that disclosure is separately authorised.

### 25.2 Data minimisation and purpose
Projections and disclosures are minimised (Sections 6.2, 11.4) and every disclosure request states its purpose (Section 14.4).

### 25.3 Auditability
Principals should be able to understand what their Agents have done. An implementation SHOULD maintain a local audit trail containing: Standing Interest version; projections created; providers contacted; sessions opened; disclosures requested and made, with surface and declared purpose; consent decisions; Handoffs; revocations; policy violations or attempted violations. Auditability MUST NOT require recording `local` attributes in plaintext outside the Agent. Audit logs are themselves highly sensitive and SHOULD be protected accordingly.

### 25.4 Retention
Disclosed values SHOULD carry retention expectations (Section 14.4); a recipient that stated a retention MUST honour it, and MUST NOT state one it cannot honour (Section 10.7); Principals SHOULD be informed that disclosure is irreversible (Section 10.8).

### 25.5 Surveillance risk of discovery infrastructure
A widely used Discovery Provider or trust graph could reveal who is considering what. Federated and privacy-preserving architectures (Section 12.3) reduce this concentration; operators SHOULD publish what they retain, for how long, and the latency within which a withdrawn projection stops being returned (Section 12.2).

## 26. IANA Considerations

This document requests no IANA actions, and is written to avoid creating facts that would require them: identifiers in examples are opaque strings, no URN namespace identifier is used or requested, no media type is registered, and no URI is allocated for the transport binding sketched in Section 22.2.

Should this work be pursued as an Internet-Draft, it would require, at minimum: a URN namespace identifier or an equivalent identifier scheme for projections and sessions; a media type for each transport binding; and registries for each closed vocabulary this draft defines, namely disclosure surfaces (Section 10.1), gates (Section 10.2), per-claim results (Section 15.1), session statuses (Section 15.2), authority levels and their permitted values (Section 16.1), consent actions (Section 14.5), disclosure statuses, the core values of `intended_use` (which profiles may extend) and the `retention` vocabulary (Section 14.4), the `next.permitted` vocabulary (Section 14.3), `identity_status` values (Section 14.6), `Handoff` target kinds (Section 14.7), close reasons (Section 14.8), session features (Section 14.1) and profile identifiers (Section 21).

Those vocabularies are **closed in 0.1**: an implementation MUST NOT add values to them, and the only ones a domain profile may extend are those whose own definitions say so, namely `intended_use` (Section 14.4) and claim operators (Section 14.2), in the profile's namespace. The two intended extension points are domain profiles, which are identified rather than enumerated and which MAY define claim keys, claim operators, `intended_use` values, retrieval attributes (Section 11.1) and `relation` values within the profile's own namespace, and future versions of this document.

## 27. References

### 27.1 Normative references

- **[RFC2119]** Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- **[RFC8174]** Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.

### 27.2 Informative references

*IETF and W3C*

- **[RFC3339]** Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- **[RFC3552]** Rescorla, E. and B. Korver, "Guidelines for Writing RFC Text on Security Considerations", BCP 72, RFC 3552, July 2003.
- **[RFC6973]** Cooper, A., Tschofenig, H., Aboba, B., Peterson, J., Morris, J., Hansen, M., and R. Smith, "Privacy Considerations for Internet Protocols", RFC 6973, July 2013.
- **[RFC7322]** Flanagan, H. and S. Ginoza, "RFC Style Guide", RFC 7322, September 2014.
- **[RFC8693]** Jones, M., Nadalin, A., Campbell, B., Bradley, J., and C. Mortimore, "OAuth 2.0 Token Exchange", RFC 8693, January 2020. <https://www.rfc-editor.org/rfc/rfc8693>
- **[RFC9901]** "Selective Disclosure for JWTs (SD-JWT)", RFC 9901. <https://www.rfc-editor.org/rfc/rfc9901.html>
- **[BBS]** Looker, T., Kalos, V., Whitehead, A., and M. Lodder, "The BBS Signature Scheme", draft-irtf-cfrg-bbs-signatures, IRTF CFRG, work in progress. <https://datatracker.ietf.org/doc/draft-irtf-cfrg-bbs-signatures/>
- **[VC-DI]** W3C, "Verifiable Credential Data Integrity 1.0", W3C Recommendation, 15 May 2025. <https://www.w3.org/TR/vc-data-integrity/>. See also "Data Integrity BBS Cryptosuites v1.0", W3C Candidate Recommendation Draft, 10 September 2026, <https://www.w3.org/TR/vc-di-bbs/>.
- **[WIMSE-AI]** Ni, Y., et al., "AI Agent Identity", draft-ni-wimse-ai-agent-identity, IETF WIMSE, work in progress. <https://datatracker.ietf.org/doc/draft-ni-wimse-ai-agent-identity/>
- **[ATN]** Somoza, E., "Agent Trust Negotiation", draft-somoza-dmsc-atn-agent-trust-negotiation-00, 29 May 2026. Individual Internet-Draft. Proposes a handshake computing the intersection of two agents' declared capabilities and constraints, with a mode in which an initiator presents only the artefacts required for the scope requested; cited in Section 1.1 as the nearest agent-protocol precedent for gated, progressive disclosure. <https://datatracker.ietf.org/doc/html/draft-somoza-dmsc-atn-agent-trust-negotiation-00>
- **[AIDIP]** Cui, Y., Chao, Y., and C. Du, "AI Agent Discovery and Invocation Protocol", draft-cui-ai-agent-discovery-invocation-02, 6 July 2026. Individual Internet-Draft, not endorsed by the IETF; defines capability-based discovery and intent-based agent selection. <https://datatracker.ietf.org/doc/draft-cui-ai-agent-discovery-invocation/>
- **[PAP]** Baur, T., "Principal Agent Protocol", draft-baur-pap-02, 29 June 2026. Individual Internet-Draft, intended status Informational, not adopted by any working group; defines signed Mandates with hierarchical delegation and SD-JWT-based context minimisation. <https://www.ietf.org/archive/id/draft-baur-pap-02.html>

*Agent protocols and industry specifications*

- **[A2A]** "Agent2Agent (A2A) Protocol Specification", version 1.0, released 12 March 2026. Hosted by the Agentic AI Foundation, a Linux Foundation-directed foundation, since 27 August 2026. Extensions are declared in the Agent Card `capabilities.extensions` array (specification §4.6). <https://a2a-protocol.org/latest/specification/>
- **[MCP]** "Model Context Protocol Specification", version 2026-07-28. Project of the Agentic AI Foundation. Authorization is OAuth 2.1-based and optional; the published roadmap (last updated 22 August 2026) lists agent identity and delegation, and progressive discovery of tools, as priority areas. <https://modelcontextprotocol.io/specification/latest> ; <https://modelcontextprotocol.io/development/roadmap>
- **[AP2]** "Agent Payments Protocol (AP2) Specification", V0.1, Google LLC, Apache-2.0. Defines `IntentMandate`, `CartMandate` and `PaymentMandate` as signed authorisations to purchase or pay. <https://ap2-protocol.org/specification/>
- **[A2CN]** "A2CN — Agent-to-Agent Commercial Negotiation", specification v0.2.0, Apache-2.0. Includes mandate verification — cryptographic proof that an agent has authority to commit its organisation — and a session state machine with human-approval thresholds. <https://a2cn.io/> ; <https://github.com/A2CN-protocol/A2CN>
- **[CONCORDIA]** Newton, E., "Concordia Protocol", v0.5.0, 10 May 2026, Apache-2.0. Structured negotiation between autonomous agents; includes a *want registry* in which agents publish what they seek. A joint "Agent Mandate Specification" with [A2CN] was in progress at the time of writing. <https://github.com/eriknewton/concordia-protocol>

*Research*

- **[RANI2026]** Rani, B. (Apple Inc.), "Behavioral Privacy Leakage in Agentic Negotiation: Formalizing and Mitigating Inference Attacks via Randomized Policies", arXiv:2607.06815, 7 July 2026; AI4TCI workshop, ARES 2026. <https://arxiv.org/abs/2607.06815>
- **[FLOWSEAL]** Shim, et al., "Confuse the Model, Control the Flow", arXiv:2609.14003, 2026. Information-flow control enforced outside the model. <https://arxiv.org/abs/2609.14003>
- **[MATCH1985]** Baldwin, R. W. and W. C. Gramlich, "Cryptographic Protocol for Trustable Matchmaking", IEEE Symposium on Security and Privacy, 1985.
- **[ANON-MATCH]** "Anonymous matching", encyclopaedic overview of the technique from Baldwin and Gramlich's 1985 protocol through the 1999 social-matching patent to consumer implementations. Cited for the lineage; the patent number was not independently verified. <https://en.wikipedia.org/wiki/Anonymous_matching>
- **[WO0070518]** "System and method for anonymously and confidentially matching contraparties", WO2000070518A2 (priority 14 May 1999); see also US7475046, "Electronic trading system supporting anonymous negotiation and indications of interest". <https://patents.google.com/patent/WO2000070518A2/en>
- **[SSM-CCS16]** Doerner, J., Evans, D., and A. shelat, "Secure Stable Matching at Scale", ACM CCS 2016. Demonstrates privacy-preserving matching at national-registry scale. <https://eprint.iacr.org/2016/861>
- **[GNAP]** Richer, J., Imbault, F. (eds.), "Grant Negotiation and Authorization Protocol (GNAP)", RFC 9635, IETF, Standards Track, 2024. Negotiated delegation of authority covering both resource access and subject information. <https://www.rfc-editor.org/info/rfc9635/>
- **[SECRET-HANDSHAKE]** Balfanz, D., Durfee, G., Shankar, N., Smetters, D., Staddon, J., Wong, H.-C., "Secret handshakes from pairing-based key agreements", IEEE Symposium on Security and Privacy, 2003. Mutual authentication between members of a group in which a non-member learns nothing. <https://web.cs.ucdavis.edu/~franklin/ecs228/pubs/extra_pubs/secret_handshakes.pdf>
- **[XACML]** "eXtensible Access Control Markup Language (XACML) Version 3.0", OASIS Standard. Cited for the obligation/advice distinction and the requirement that an enforcement point deny access when it cannot discharge an obligation. <https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html>
- **[KMN2005]** Kenthapadi, K., Mishra, N., Nissim, K., "Simulatable auditing", PODS 2005; and "Denials leak information: simulatable auditing", *Journal of Computer and System Sciences*, 2013. Establishes that query denials leak, defines simulatable auditing, and reports NP-hardness for the offline max-sum and max-max auditing problems. <http://theory.stanford.edu/~kngk/papers/SimulatableAuditing.pdf>
- **[ODRL]** "ODRL Information Model 2.2", W3C Recommendation, 15 February 2018. Rule types Permission, Prohibition and Duty; a Policy carries obligations by referencing a Duty. <https://www.w3.org/TR/odrl-model/>
- **[AFME-IOI]** Association for Financial Markets in Europe / Investment Association, "Framework for Indications of Interest". Industry taxonomy classifying indications by the liquidity they represent and therefore by what they reveal. <https://www.afme.eu/>
- **[IOSCO-DARK]** IOSCO Technical Committee, "Principles for Dark Liquidity", Final Report, 2011. <https://www.iosco.org/library/pubdocs/pdf/ioscopd353.pdf>
- **[PSI-SLR]** "Private Set Intersection: a systematic literature review", Computer Science Review, 2023. <https://doi.org/10.1016/j.cosrev.2023.100567>
- **[PIR-SURVEY]** "Private Information Retrieval: a tutorial and survey", IACR ePrint 2026/1135, 2026. <https://eprint.iacr.org/2026/1135>
- **[DEMOTT2026]** DeMott, D., "Agency law and artificial agents", SSRN 6838660, May 2026. On the application of apparent-authority doctrine to AI agents. <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6838660>

*Domain practice*

- **[FINRA5210]** FINRA Rule 5210, "Publication of Transactions and Quotations", governing the display of indications of interest. Indications of interest are non-binding communications of trading interest in which fields including side and price may be omitted.
- **[COND-ORDERS]** Global Trading, "Conditional Orders and Alternative Liquidity Pools", trade-press account of how conditional orders rest unpublished and firm up on a contra-side match. Cited as a description of market practice, not as a rule. <https://www.globaltrading.net/conditional-orders-and-alternative-liquidity-pools-in-asia/>
- **[TEASER]** Corporate Finance Institute, "Investment Teaser". Describes the anonymised, "no-names basis" document used before a non-disclosure agreement in sell-side mergers and acquisitions. <https://corporatefinanceinstitute.com/resources/valuation/what-is-an-investment-teaser>

All URLs were last verified on 21 and 22 September 2026. Individual Internet-Drafts cited above have no standing in the IETF standards process; they are cited as evidence of concurrent work, not as normative material.

---

## Appendix A — Minimal Conceptual Schema (non-normative)

```yaml
version: "gidp/0.1"

standing_interest:                         # local, never transmitted
  id: local_opaque
  version: integer
  principal_ref: local_opaque
  interest:                                # no class field: Section 8
    action: string
    object: string
    structures: []
  conditions: {}                           # evaluable, per-attribute policy
  private_conditions: {}                   # evaluable, evaluation_only by default
  provides: []                             # dependency primitives, Section 19.1
  requires: []
  conditional_on: []
  excludes: []
  disclosure_policy:
    default: evaluation_only               # Section 9.1: this is the only permitted value
    attributes: {attribute: class | {counterparty_property: class}}
    principal_identity: class              # surface <= session
  authority:                               # Section 16
    OBSERVE | SEARCH | PUBLISH_PROJECTION | PROBE | DISCLOSE
    | INTRODUCE | NEGOTIATE_NONBINDING: true | false | approval_required
    COMMIT: false
  validity: {not_before: datetime, expires_at: datetime}

projection:                                # Section 11
  version: "gidp/0.1"
  type: DiscoveryProjection
  projection_id: opaque
  interest_ref: opaque                     # opaque; resolvable only by the publishing Agent
  categories: []
  domains: []
  geographies: []
  relation: []
  attributes: {}                           # further discovery/network-surface attributes
  endpoint: {protocol: string, agent_ref: opaque}
  expires_at: datetime
```

## Appendix B — Logical Interfaces (non-normative)

The Discovery Provider interface is given in Section 12.2. The Compatibility Session interface, expressed as operations over the objects of Section 14:

```text
openSession(candidate, purpose, max_depth, profile, features)   -> SessionAccept | SessionClose
sendCompatibilityRequest(session_id, claims, allowed_results) -> CompatibilityResponse
requestDisclosure(session_id, attribute, purpose, surface)    -> DisclosureResponse
requestConsent(session_id, action, scope)                     -> ConsentResponse
emitOpportunity(session_id)                                   -> Opportunity
handoff(session_id, target, authorized_scope)                 -> status
closeSession(session_id, reason)                              -> status
```

## Appendix C — Worked Examples (non-normative)

### C.1 End-to-end: cross-border strategic transaction
*Principal A*, a French software company, privately authorises its Agent to explore expansion into Germany through acquisition, minority or majority investment, distribution or joint venture. Its budget is `evaluation_only`.

*Principal B*, a German software company, is not for sale. Its Agent is nevertheless authorised to explore strategic transactions if the counterparty provides access to France, the founder remains operationally involved, and a private valuation threshold is met.

*Discovery.* A projects `strategic_transaction · enterprise_software · europe`; B projects `strategic_transaction · enterprise_software · cross_border`. Neither projection states buy or sell.

*Session.* After `SessionOpen`/`SessionAccept` (profile `core`, depth `session`), the claims resolve as: geography `compatible`; market access `compatible` (B `requires: market_access_france`, A `provides` it, disclosed at surface `session`); transaction structures `compatible`; valuation class `conditionally_compatible`; management condition `conditionally_compatible`. Neither side learns the other's valuation boundary.

*Opportunity.* Every claim resolved `compatible` or `conditionally_compatible` and nothing remains in `next.requires`, so `session_status` becomes `potentially_compatible`, the session enters `QUALIFIED`, and an Opportunity `minority investment + distribution agreement` is produced: five dimensions evaluated, three `compatible`, `open_conditions: [valuation_class, management_condition]` (the two that resolved `conditionally_compatible`) and `identity_status: {initiator: not_requested, responder: not_requested}`.

*Consent.* Each Agent sends `ConsentRequest {action: reveal_identity, reciprocal: true}`; both Standing Interests gate identity with `principal_approval`, so each answers a provisional `pending_principal_approval`, and each sends a terminal `granted` carrying the same `request_ref` once its Principal has decided (Section 14).

*Handoff.* `Handoff {target: protocol, authorized_scope: [NEGOTIATE_NONBINDING], requires_principal_presence: true}`; the session closes with `reason: completed`. Neither company ever stated "we want to buy" or "we might sell".

### C.2 Executive succession (person ↔ organisation)
Candidate Standing Interest: `interest: consider executive_role · role: [ceo] · sector: [b2b_software] · company_arr: {min: 20M} · geography: [paris, london] · equity_min: evaluation_only · principal_identity: session/principal_approval`.
Company Standing Interest: `interest: consider executive_succession · role: ceo · sector: b2b_software · location: paris · timing: evaluation_only · board_context: evaluation_only · principal_identity: session/principal_approval`.
Neither side advertises an active search; a provider retrieves the pair from coarse projections; the session establishes category, role, sector, scale bucket, geography and private-condition feasibility; identities are revealed only after both Principals approve.

### C.3 Commercial partnership (organisation ↔ organisation, enterprise agents, bilateral use of dependency primitives)
Enterprise agent: `interest: consider [licensing, white_label, partnership] · requires: [capability_x] · commercial_thresholds: evaluation_only`. Startup agent: `provides: [capability_x] · interest: consider [white_label, licensing] · requires: [distribution_access] · minimum_contract_value: evaluation_only`. Both sessions declare `features: [dependency_primitives]`. The pair is discoverable because reduced projections expose compatible capability classes without publishing the strategic motives (e.g. "74 deals lost for lack of X") or thresholds.

### C.4 Multi-party real estate (experimental)
Buyer: `acquire: commercial_property · requires: financing ≥ 7M, occupancy ≥ 60 %`. Owner: `consider_sale · minimum_price: evaluation_only`. Bank: `provides: financing ≤ 7M · conditional_on: investment_grade_tenant, lease_term ≥ 10y`. Tenant: `provides: occupancy 60 % · conditional_on: renovation_complete, rent_below_private_threshold`. GIDP Core discovers bilateral edges; an implementation with the `multi_party` feature could determine that the four Standing Interests form a potentially satisfiable coalition.

### C.5 Co-investment (interdependent)
`invest: {max: 100k} · conditional_on: institutional_lead ≥ 1M · sector: ai_infrastructure · geography: france · referral: trusted_connection (evaluation_only)`. Discoverable as `co_investment · ai · france`; the dependency on a lead is evaluated in session and, if unmet, may trigger dependency-driven expansion (Section 19.2).

## Appendix D — Why GIDP Is Not Capability Discovery (non-normative)

| Dimension | Capability / agent discovery | GIDP |
|---|---|---|
| Core question | What can this agent do? | What might its Principal consider? |
| Primary object | Agent capability | Standing Interest |
| Information | Skills / services | Preferences / constraints / authority |
| Visibility | Often advertisable | Often confidential |
| Direction | Request → provider | Reciprocal |
| Matching | Capability fit | Conditional compatibility |
| Secrets | Usually incidental | Fundamental |
| Consent | Invocation / task | Progressive disclosure |
| Typical example | Find a translation agent | Find a Principal who may transact only under private conditions |
| Multi-party | Task orchestration | Conditional coalition discovery |

Capability discovery answers *intent → capable agent*. GIDP answers *private preference set ↔ private preference set*. Whether that distinction justifies a durable independent protocol layer, rather than a small extension of an existing discovery system, is an empirical question this draft exists to make testable.

## Appendix E — Open Questions and Request for Comments

**Representation.** How much of a Standing Interest should use structured fields versus natural language, embeddings or domain ontologies? How should probabilistic or fuzzy conditions be represented? How generic can the core vocabulary remain?

**Discovery.** What is the minimum useful Discovery Projection? How should projections be indexed without creating a searchable database of sensitive interests? How should federated discovery and provider selection work? Can discovery operate efficiently without centralised indexes?

**Compatibility execution.** Locally, peer-to-peer, through a trusted broker, in a TEE, through privacy-preserving cryptography, or a combination?

**Privacy.** How should re-identification risk of projections be measured? How should query privacy budgets work within the bounds of Section 15.5? Which cryptographic profiles are practical? How can behavioural leakage be bounded? The open problem stated in Section 24.3 (bounding what an *adaptive* querent can learn from a truthful compatibility oracle while keeping that oracle useful for discovery) is the question on which the authors most want contributions; [RANI2026] treats a particular passive case (bounded leakage from observed negotiation dynamics, under its own model and assumptions) and explicitly leaves the active one open.

**Trust and authority.** How should Agents prove authority for a specific Standing Interest? How should Principals be verified without unnecessary identity disclosure? How should reputation work without enabling surveillance? How should GIDP reference external delegated-authority credentials? At what point does identity become necessary?

**Multi-party.** How are dependencies discovered without combinatorial explosion? How are coalitions scored? How is information shared when members have different Disclosure Policies? How are circular conditions handled? When should a partial coalition be revealed?

**Governance.** Should GIDP become an A2A extension, a separate protocol or a reusable application profile? Which parts should be standardised versus left to Discovery Providers? What namespace and versioning model? If GIDP gains adoption, what governance structure preserves neutrality?

**How to comment.** The canonical location of this document is https://gidp.dev. Objections, corrections, implementation reports and refutations should go to the issue tracker there, or to contact@gidp.dev. Every substantive comment received will be answered in public and, where it changes the text, recorded in the revision history with attribution. A companion document at the same location, *Open Problems and Design Rationale* (`open-problems.md`), carries the non-normative material that does not belong in a specification: the mapping from this document's requirements to existing cryptographic and identity mechanisms, the candidate directions for the open problem of Section 24.3, and the reasoning behind choices this text states without arguing.

**Five questions for reviewers.**

1. Is private reciprocal Standing Interest discovery a distinct protocol problem, or should it be absorbed into existing agent discovery?
2. Is the Standing Interest / Discovery Projection distinction, with the surface/gate disclosure model, sufficient to support useful discovery without unacceptable leakage?
3. Are `provides`, `requires`, `conditional_on` and `excludes` adequate foundations for future multi-party discovery?
4. Which parts of GIDP should be standardised, and which should remain implementation-specific to Discovery Providers?
5. Where does the abstraction fail when applied across executive recruiting, M&A, investment, real estate and commercial partnerships?

## Appendix F — Standardisation Strategy and Evaluation Criteria

### F.1 Strategy
The sequence adopted is publication of the specification first, reference implementation immediately after. A reference implementation of the bilateral core accompanies this draft at the canonical location, together with the conformance suite of Section 23.2 and a demonstration of the probing attack of Section 24.3. Draft 0.1 does not aim at premature formal standardisation; its purpose is to name the problem, fix terminology, distinguish GIDP from adjacent layers, enable independent implementations and attract technical criticism. Expected progression:

```text
Draft 0.1 (request for comments)
  → critique from A2A implementers, agent-framework builders, privacy and
    identity researchers, mechanism-design researchers, enterprise agent teams
  → bilateral reference implementation (personal agent ↔ provider ↔ enterprise agent)
  → cross-market validation on at least four materially different domains
  → Draft 0.2: normative JSON Schema, extension URI, binding, error taxonomy,
    threat model, conformance suite, domain profiles
  → multi-party experimental profile
  → formal standardisation only if justified by multiple implementations
```

### F.2 Horizontal-layer hypothesis
GIDP should not become a protocol layer only because the abstraction is appealing. A strong validation would run the same core implementation across at least four domains while changing primarily vocabularies and validation rules, keeping Standing Interest, Disclosure Policy, Discovery Projection, candidate retrieval, compatibility, progressive disclosure, authority, consent and Handoff substantially common. If most core logic must be rewritten per market, GIDP is better treated as a design pattern or a family of vertical protocols.


**Status at publication.** Four domains have been run against a single
implementation of the core: a cross-border corporate transaction, an executive
succession between a person and an organisation, a commercial partnership
using the dependency primitives, and a co-investment carrying an interdependent
interest. They share every object, every claim operator and every result value;
what differs between them is the claim vocabulary, which values each Principal
classifies as evaluation-only, and which authority levels each grants. The
reference implementation checks this mechanically rather than asserting it, so
a fifth domain that needed an object of its own would fail the check instead
of passing unnoticed.

This meets the threshold this document set for itself, with one limit: all four
were written by the same author, from the same understanding of the protocol,
which is the circumstance in which a shared blind spot survives. The decisive
test is a domain profile written by someone else.

### F.3 Evaluation criteria
The proposal should be considered successful only if experiments show that: (1) Principals possess economically meaningful conditional interests they do not want to publish; (2) useful candidate retrieval is possible from reduced projections; (3) progressive disclosure preserves materially more privacy than marketplace publication; (4) Agents can evaluate meaningful compatibility without revealing all constraints; (5) the same core primitives work across multiple markets; (6) the protocol reuses rather than duplicates existing transport and negotiation infrastructure; (7) abuse controls prevent trivial Standing Interest harvesting; (8) the discovery layer produces Opportunities that would otherwise be difficult to surface. If these do not hold, GIDP should be narrowed, redesigned or abandoned.

### F.4 Core architectural hypothesis
*A sufficiently general primitive exists for Agents to discover compatibility between private, conditional, unpublished interests of their Principals, and that primitive is distinct enough from capability discovery and negotiation to justify interoperable protocol semantics.* Draft 0.1 is intended to test that hypothesis, not to assume it.

### F.5 Boundary of what this specification standardises
Candidates for open standardisation: Conditional Interest semantics; Standing Interest, Disclosure Policy and Discovery Projection models; session, compatibility, disclosure and consent objects; Opportunity and Handoff representations; authority levels; profile mechanism; threat model; transport bindings; reference SDK; conformance tests. Intentionally outside the standard: ranking and routing algorithms, matching models, trust scores and reputation systems, market-making and liquidity management, cross-market inference, outcome prediction, pricing, operator-specific anti-abuse systems and commercial relationships. This separation permits interoperable infrastructure while leaving room for competing implementations.

## Appendix G — Acknowledgements

This draft was substantially improved by two independent adversarial reviews of the consolidated text, carried out, like the later review passes, by large language models given the text alone. They identified defects in the object model, the result vocabulary and the conformance criteria that the author had not seen. Errors that remain are the author's.

Acknowledgements of external reviewers will be added as comments arrive.
