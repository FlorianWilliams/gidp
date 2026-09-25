---
title: Graduated Interest Disclosure Protocol (GIDP)
version: 0.1
date: 2026-09-23
status: Experimental — Early Draft / Request for Comments
category: Experimental
---

# Graduated Interest Disclosure Protocol (GIDP) — Draft 0.1

**Status of this document:** experimental, early draft, request for comments. This document is not an Internet-Draft, has not been submitted to any standards body, and claims no endorsement. It follows the structure and editorial conventions of IETF Internet-Drafts ([RFC7322] style; BCP 14 requirement language; separate Security, Privacy and IANA Considerations; normative and informative references) so that it can be converted into one if the work warrants it.
**Category:** Experimental.
**Version:** 0.1. This is the first public draft. It consolidates three earlier internal drafts and incorporates the results of two independent adversarial reviews of the consolidated text.
**Date:** 23 September 2026.
**Author / editor:** {{AUTHOR}}, Independent. Contact: {{CONTACT}}.
**Canonical location:** {{CANONICAL_URL}}. Comments, objections and implementation reports are welcome; see Appendix E.
**Licence:** this document is published under the Creative Commons Attribution 4.0 International licence (CC BY 4.0). The reference implementation, when published, is licensed under Apache License 2.0. The author is aware of no intellectual property rights covering the mechanisms described here and has filed none.
**Intended audience:** agent-platform developers, protocol designers, identity and privacy infrastructure providers, marketplace operators, enterprise software vendors, mechanism-design and privacy researchers.

---

## Abstract

AI agents can increasingly access tools, communicate with other agents, advertise capabilities, execute tasks, hold delegated authority and participate in multi-step workflows. A distinct problem remains when the information required to discover a valuable interaction is itself private and should not be advertised.

A principal may not be actively seeking an outcome, yet may be willing to consider it under specific conditions. An organisation may seek an acquisition, partner, supplier, investor, employee or asset without wishing to reveal the search, its constraints, its identity or its reservation values. A principal may be willing to provide something without publicly offering it. In all these cases, publishing enough information to be found may reveal the very fact the principal wants to keep private.

The Graduated Interest Disclosure Protocol (GIDP) defines a common model for representing such **Conditional Interests** inside a **Standing Interest**, deriving privacy-preserving **Discovery Projections**, retrieving candidate counterparties, evaluating compatibility progressively inside bounded **Compatibility Sessions**, controlling disclosure through explicit **Disclosure Policies**, obtaining **Consent**, and handing qualified **Opportunities** to humans or downstream negotiation systems.

GIDP is a discovery and compatibility layer. It is intended to operate above agent-to-agent communication protocols and alongside identity, authority, payment and negotiation protocols, not to replace them. GIDP 0.1 describes a bilateral core — objects, message semantics, disclosure classes, authority levels and state machines — without yet fixing a normative wire schema, and reserves data-model primitives for multi-party discovery, which remains experimental and non-normative in this version.

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

These cases share one structure:

> A principal has a state transition it may be willing to consider, subject to conditions, and does not wish to publish all or part of that willingness.

The discovery problem is circular. A counterparty cannot find such an interest without information about it, and publishing enough information to make it findable may reveal exactly what the principal wants to keep private. GIDP exists to manage this tension.

GIDP separates four concepts that are often conflated: a **Principal** whose interests are represented; an **Agent** acting under delegated authority; a **Standing Interest** containing conditional interests, constraints, disclosure rules and authority; and a **Discovery Projection**, a deliberately reduced representation that makes a Standing Interest discoverable without publishing it.

The key design question of this draft is not whether private matching can be built inside one application; it can. It is whether the same small set of primitives can support private conditional discovery across materially different domains and independently operated agents. Draft 0.1 is written to make that question testable (Appendix F).

### 1.1 Relationship to prior work (informative)

GIDP is not the first attempt to let two parties find each other without either revealing what it wants. What follows sets out the systems it descends from, so that a reader can judge what, if anything, is left unsolved. Whether the remaining gap warrants a protocol is stated as a hypothesis to be falsified, not as a claim, in Appendix F.

**Double-blind matching.** The core idea is four decades old, and part of it has a cryptographic treatment: a *secret handshake* [SECRET-HANDSHAKE] lets two members of the same group authenticate to each other while a non-member learns nothing — not even that a group was in question. That is the mutual-revelation property of this document, obtained exactly, and it is worth being precise about what it does not cover: the predicate is membership, binary and agreed in advance, whereas the predicate here is a conjunction of conditions neither party has stated and which the session discovers. The cryptography settles the easy half. Baldwin and Gramlich described a cryptographic matchmaking protocol in 1985, in which a mutual interest is revealed only when it is mutual, in both trusted-server and untrusted-server variants [MATCH1985]; the pattern was patented for social matching at the end of the 1990s and has since appeared in consumer matching services [ANON-MATCH]. Its limit is structural: both sides must independently name *the same counterparty or the same item*. GIDP generalises the primitive from "do we both name each other?" to "does my set of conditions admit anything in your set of conditions?", which is what makes it applicable where the counterparty is not known in advance.

**Confidential matching in finance.** A narrow version of this problem has been solved in production for decades, within a single regulated venue. An indication of interest is a non-binding communication of trading interest, used to look for a counterparty without displaying an order; market practice allows fields to be omitted, and the display of such communications is subject to rule [FINRA5210]. That rule exists because the experiment went wrong first: broadcast indications were found to leak the very intentions they were meant to conceal, regulators examined the practice across venues [IOSCO-DARK], and the industry had to publish a taxonomy classifying indications by how much they actually reveal [AFME-IOI]. This is the closest thing to a controlled trial of the idea behind this document, it was run at scale by sophisticated participants, and its failure mode was inference from the signals rather than disclosure of the values — which is the failure mode of Section 24.3. Conditional orders let a large order rest unpublished in a non-displayed venue and "firm up" only when a contra-side match appears [COND-ORDERS] — the human-market precedent for the transition from probing to a qualified Opportunity (Section 17.2). A 1999 patent family describes anonymous, confidential matching of indications followed by human negotiation of final terms [WO0070518]. Three properties distinguish GIDP from these systems: the venue is not trusted with the private values, the matched object is a set of heterogeneous conditions rather than a price and a quantity, and no central operator is required.

**The human staged-disclosure protocol.** Sell-side mergers and acquisitions run a disclosure ladder by hand: an anonymised one-page teaser on a "no-names basis" [TEASER], then a non-disclosure agreement, then a confidential memorandum, then a non-binding indication, then a binding letter of intent. The Discovery Projection (Section 11) is a machine-readable teaser, and the Disclosure Policy (Section 10) is that ladder made explicit and enforceable.

**Cryptographic matching.** Private set intersection [PSI-SLR], private retrieval [PIR-SURVEY] and secure stable matching at scale [SSM-CCS16] provide mechanisms for computing on private inputs, and have been demonstrated on problems of national-registry size. GIDP does not compete with them; it defines the information-flow properties (Sections 10, 15, 25) that such a mechanism would have to satisfy, and leaves the choice of mechanism to the deployment (Section 24.12).

**Agent protocols.** Agent-to-agent communication [A2A], tool and context access [MCP], capability discovery and intent-based agent selection [AIDIP], delegation and mandate protocols [PAP] [AP2], and negotiation protocols [A2CN] [CONCORDIA] all assume that the thing being discovered is a *capability* or that the thing being authorised is a *transaction*. The nearest protocol-level neighbour is Concordia's want registry, in which agents publish what they seek [CONCORDIA]; GIDP differs in that nothing is published. Progressive disclosure of *trust artifacts* between agents has been proposed in [ATN]; GIDP applies the same gate idea to the substance of a principal's interest rather than to credentials.

**What this document adds.** No single mechanism above is new here. What this document proposes is their composition: a conditional interest held privately by an agent and never transmitted; a per-attribute disclosure policy with a class that is usable for local evaluation and never transmissible; a projection designed for retrieval without inversion; a reciprocal, bounded compatibility session with a truthful coarsening rule; and an authority ladder that stops before commitment.

## 2. Conventions and Requirements Language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.

Because GIDP 0.1 is experimental, normative language indicates the intended behaviour of a conforming GIDP 0.1 implementation rather than an established standard.

Sections 3 (Terminology) and 7 (Conceptual Model) are definitional. Requirements are stated in Sections 8 through 26. YAML and JSON fragments, worked examples and **all appendices** are non-normative; Appendices A and B illustrate a possible data model and interface shape and create no requirements, and Appendices E to H are editorial; where a section contains both a normative field list and an example, only the field list is normative. Timestamps in examples use the [RFC3339] format. Identifiers in message fields use `lower_snake_case`; authority levels use `UPPER_SNAKE_CASE`.

## 3. Terminology

This section defines terms. It imposes no requirements; requirements on these objects appear in the body.

**Principal.** The person, organisation, collective, institution, business function, software-controlled entity or other authority whose interests are represented.

**Agent.** A software system that holds, derives, evaluates, communicates or acts upon information on behalf of one or more Principals within the bounds of a Standing Interest. An Agent may be a personal agent, a career or investment agent, an agent resident in a CRM, ATS, ERP or marketplace, a procurement or corporate-development agent, or a broker or intermediary agent.

**Conditional Interest.** A state transition that a Principal may be willing to consider if specified conditions are satisfied. Canonical form: *the Principal is not necessarily seeking X, but authorises the Agent to explore X if conditions C1…Cn hold, without revealing protected information until disclosure conditions D1…Dn are satisfied.* Section 8 defines four classes.

**Standing Interest.** A bounded delegation from a Principal to an Agent: a structured container holding one or more Conditional Interests together with constraints, exclusions, a Disclosure Policy, an Authority specification and validity bounds. A Standing Interest does not imply active demand.

> *Why "standing".* The word is used as in a *standing order* or a *standing instruction*: something registered once, held in place until revoked or expired, and acted upon when its conditions are met. It does not assert that the Principal is passive. A Standing Interest of the confidential-active-demand class (Section 8.2) represents a search that is under way but unpublished; what "standing" denotes in every class is persistence and registration, not absence of urgency.

> *Why not "mandate".* Authorisation and payment protocols in the agent ecosystem use "mandate" for a signed proof that a principal authorised a specific transaction: AP2 defines `IntentMandate`, `CartMandate` and `PaymentMandate`, and adjacent negotiation proposals are drafting a common agent-mandate specification in the same sense. A Standing Interest is the opposite kind of object — it is never transmitted, and it bounds what an Agent may *explore and disclose*, not what it may *pay or commit to*. Section 20 describes how a Standing Interest's Authority may nevertheless be *evidenced* by such an external mandate. For the same reason this specification avoids "intent", which in payment protocols, in agent-discovery drafts and in the decentralised-finance sense denotes an active request for something to be done.

**Disclosure Policy.** The rules attached to a Standing Interest specifying, per attribute, the surface on which the attribute may appear and the gate that must be passed before it is disclosed (Section 10).

**Discovery Projection.** A deliberately reduced, policy-compliant representation derived from a Standing Interest for the purpose of candidate retrieval (Section 11).

**Discovery Provider.** A service or mechanism used to publish, route, search or retrieve Discovery Projections and resolve candidates. It may be centralised, federated, peer-to-peer, community-specific, enterprise-private or privacy-preserving (Section 12).

**Compatibility Session.** A bounded interaction between two Agents (or, experimentally, more) in which they determine whether the Standing Interests they represent may be mutually compatible while applying their Disclosure Policies (Sections 13–17).

**Claim.** A question about one dimension of a Conditional Interest, evaluated within a Compatibility Session and producing exactly one result from the vocabulary of Section 15.

**Counterparty.** Another Principal, or the Agent representing it, participating in a potential Opportunity.

**Authority.** The set of actions an Agent may perform on behalf of a Principal for a given Standing Interest, expressed as levels (Section 16).

**Consent.** A scoped, explicit authorisation to progress a Compatibility Session to a more disclosing stage, given either by the Principal or by an Agent whose Authority for that action is unconditional (Section 14.5, Section 16.2).

**Opportunity.** A candidate configuration of Standing Interests whose conditions have been found potentially jointly satisfiable within a session. An Opportunity is not a contract, does not imply commitment, and does not imply that any Principal has consented to identity disclosure (Section 14.6).

**Handoff.** The transfer of a sufficiently qualified Opportunity to a human, a workflow, a negotiation agent, a transaction protocol or another downstream system (Section 14.7).

## 4. Problem Statement and Scope

### 4.1 Problem statement

Existing agent discovery commonly begins with a capability or a task: *find an agent that can translate this document; find an agent that can book a flight.* The relevant capability can generally be advertised.

GIDP addresses a different class of problem:

> Find another Principal whose private conditions may be compatible with mine, even though neither side wants to publish the information required to establish that compatibility.

Capability is not willingness. A registry can answer "which agent can perform X"; it cannot answer "do the private conditional preferences of the Principals represented by A and B have a mutually acceptable intersection" without either side publishing those preferences. Appendix D contrasts the two problems dimension by dimension.

### 4.2 Scope

GIDP addresses the discovery phase that occurs **before** conventional negotiation. It covers:

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

GIDP 0.1 does **not** attempt to define:

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
the reference implementation and each failed for a structural reason rather
than an implementation one; the companion document *Where this protocol should
not be used* records them in full.

Markets where **publication is a legal obligation** rather than a choice —
public procurement, regulated disclosure — cannot be expressed at all: every
disclosure class in Section 10 is an upper bound on exposure and none is a
lower bound, so an Agent that publishes nothing is conformant while its
Principal is in breach. Markets whose interests reduce to **one comparable
dimension**, or that **perish faster than a human answers**, are served worse
by this protocol than by a sealed-bid mechanism: the other conditions are what
make a threshold worth hiding, not what hides it, and a `principal_approval`
gate that cannot run in the time available is a gate in name only. Contexts of
**structural asymmetry**, where one side runs many sessions and the other runs
few, invert the protection: the strong side spends the same disclosure
repeatedly while each weak counterparty spends a scarce one, and per-counterparty
controls do not see the aggregate. And markets that must **establish identity
before any substantive exchange**, such as sanctions-screened or KYC-gated
ones, are incompatible with the ordering of Section 17.2, which reaches
identity only through qualification; that ordering is enforced by the state
machine and a domain profile may not reverse it (Section 21).

## 6. Design Principles

These principles motivate the requirements of later sections; where a principle and a requirement overlap, the requirement governs.

### 6.1 Local secrets, global discovery
Sensitive knowledge stays under the control of the Agent or system that legitimately possesses it. Global discovery operates on reduced signals rather than complete Standing Interests.

### 6.2 Data minimisation
Information is not disclosed merely because it is useful for matching. Information *usable for evaluation* is distinguished from information *revealable to a counterparty*.

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

The fundamental relationship is:

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

An Agent may represent multiple Standing Interests. An intermediary Agent may represent Standing Interests from multiple Principals, provided each Standing Interest retains its own authority and disclosure boundaries. Principals may be persons, organisations, business functions, institutions or software; personal Principals are first-class, and the same session may connect person ↔ person, person ↔ organisation or organisation ↔ organisation.

The object of GIDP discovery is therefore not an Agent. It is a **potentially compatible Standing Interest represented by an Agent**.

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

These dimensions are conceptual. In the Standing Interest representation of Section 9 they map as follows: HAVE and PROVIDE → `provides` and positional attributes; WANT and WOULD CONSIDER → `interest`; IF → `conditions` and `private_conditions`; REQUIRE → `requires`; EXCLUDE → `excludes`; WILL DISCLOSE → `disclosure_policy`; AUTHORISE → `authority`. Not every Standing Interest populates every dimension.

## 8. Conditional Interest Model

GIDP 0.1 recognises four classes of Conditional Interest. They differ in what is hidden, not in protocol mechanics; a conforming implementation MUST be able to represent all four with the same objects.

### 8.1 Passive conditional demand
*I am not seeking X, but I would consider X if conditions C hold.* Example: an executive who would consider a CEO role in B2B software above a private scale threshold. Established analogue: the "passive candidate" in executive search, and the owner of an unlisted asset holding an implicit option.

### 8.2 Confidential active demand
*I am seeking X, but I do not want potential counterparties or the market to know that I am seeking X.* Example: a corporation exploring acquisition targets without signalling an acquisition programme; a board exploring CEO succession without a public search. Established analogue: buy-side deal criteria circulated privately, and the indication of interest used to query liquidity without displaying an order (Section 1.1).

### 8.3 Private conditional supply
*I can offer X, but I do not want to advertise X publicly.* Example: a startup that would white-label its technology; an owner who would sell an unlisted asset above a private price. Established analogue: the conditional order resting unpublished in a dark pool, and off-market inventory.

### 8.4 Interdependent conditional interest
*I will consider X if another party performs or commits to Y.* Example: an investor who participates only if a qualified lead commits; a buyer who acquires a building only if an anchor tenant signs. Established analogue: conditional co-investment subject to a lead investor, and contingent real-estate transactions. This class uses the dependency primitives of Section 19 and is the entry point to multi-party discovery.

> *There is no field for this.* GIDP defines no attribute carrying the classification, and a conforming implementation is not asked to record one. The four classes are a way of thinking about what is being expressed, and they are expressed entirely through the Disclosure Policy: which attributes are `local`, which reach a `discovery` surface, which need a gate. An Agent's behaviour cannot depend on the class because nothing in the protocol states it, and that is deliberate — a required field that no behaviour reads is a tax on every implementer for the author's convenience, and two implementations given one would eventually disagree about what it means.

## 9. Standing Interest

A Standing Interest SHOULD contain sufficient information for an Agent to determine whether an Opportunity is worth exploring without the complete Standing Interest ever leaving the Agent's trust boundary.

### 9.1 Private by default
A Standing Interest MUST NOT be transmitted through GIDP. Attributes without an explicit Disclosure Policy entry MUST be treated as `evaluation_only` (Section 10).

The requirement binds the holder: an Agent MUST NOT transmit an attribute classified `local` *of the Standing Interest it holds*. It does not and cannot mean that such a value never appears in a session, because a claim carries a candidate value chosen by the querent (Section 14.2); where that guess coincides with the responder's private value, the value is on the wire, put there by the party that does not hold it. What the responder never does is confirm it.

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
    class: confidential_active_demand      # Section 8
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
| `never` | local | — | MUST NOT be transmitted and MUST NOT be used to produce transmitted results. |

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

### 10.7 Purpose and retention
Every disclosure request MUST state its purpose and SHOULD state retention expectations (Section 14.4). Purpose *restrictions* enforced by the recipient are future work.

Retention, however, is not advice. A requester MUST NOT state a retention it is not able to discharge, and an implementation that cannot discharge any retention mode MUST omit the field rather than state one it will ignore — leaving the responder to decline, which is the safe outcome. The distinction is borrowed rather than invented: XACML separates an *obligation*, which an enforcement point must carry out, from *advice*, which it may ignore, and requires a conforming enforcement point to deny access outright when it cannot discharge an obligation attached to a permit [XACML]. A field that a recipient may state and then disregard is advice whatever the specification calls it, and the only lever a protocol has is to make disregarding it non-conformant. GIDP cannot verify discharge and does not pretend to; it can refuse to call something a limit when nothing turns on it.

### 10.8 Irreversibility
Previously disclosed information cannot be recalled from a counterparty. Revocation (Section 17) affects future behaviour, not past disclosures; implementations SHOULD make this visible to Principals when they approve disclosures.

### 10.9 Relationship to Authority
Authority (Section 16) states whether the Agent may perform a *category* of action at all; the Disclosure Policy states what may be disclosed *per attribute*. A disclosure happens only if both permit. When an authority level is `approval_required` and the attribute's gate is `principal_approval`, one Principal decision satisfies both.

## 11. Discovery Projection

Publishing a complete Standing Interest would defeat the purpose of GIDP. An Agent with `PUBLISH_PROJECTION` authority derives one or more Discovery Projections.

### 11.1 Required fields
A `DiscoveryProjection` MUST carry `type`, `version` and `expires_at` (Section 14), `projection_id` (opaque, unique to the publishing Agent), and `endpoint` (the reference by which a candidate's Agent can open a Compatibility Session with the publishing Agent, expressed in binding-specific terms). `type`, `version`, `expires_at`, `projection_id` and `endpoint` are protocol metadata: they are not derived from the Standing Interest and are not subject to the content rule of Section 11.2. `endpoint` and `projection_id` SHOULD nevertheless be unlinkable across providers — a distinct value per projection — because a value that is stable across providers is precisely the correlating identifier Section 24.2 warns about, and deriving distinct projections per provider (Section 11.5) achieves nothing if all of them carry the same endpoint. A projection MUST NOT carry `session_id`, a Principal identifier, or a resolvable reference to the Standing Interest it derives from; `interest_ref`, where present, MUST be opaque and resolvable only by the publishing Agent.

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
Agents SHOULD minimise projections while preserving sufficient retrieval quality. This is a fundamental trade-off: more specific projections improve retrieval and increase inference risk; less specific projections do the reverse. GIDP 0.1 does not prescribe an optimum, and the shape of the curve is worth stating even though the optimum is not, because minimisation past a point reverses. Two effects, both measured on a synthetic index in the reference implementation. An over-precise projection is retrieved *less*, not more: it answers only querents who described the target in the same terms, so a publisher that named a city is never found by a querent that named the country — though that second effect is a property of the provider rather than of the projection, and a provider that resolves one hierarchy removes it entirely (Section 12.4). And a projection coarse enough to be retrieved by everyone is retrieved by everyone — each retrieval being a Compatibility Session with a counterparty that had no business finding this Principal, and each session an opportunity to probe under Section 24.3. Past a certain coarseness the sessions cost a publisher more than the projection saved it. The quantity that decides where that point falls is how many other publishers a given projection will be confused with, which the publishing Agent cannot observe and the Discovery Provider can; Section 12 gives a provider no way to say so, and a provider that reported the size of a matching set would also be helping an adversary calibrate. Coarsening techniques include generalising geography (city → region), bucketing economic ranges, and replacing direction-revealing attributes with symmetric ones (`strategic_transaction` rather than `acquire`). The last has an established precedent: in the equivalent human market, an indication of interest may omit side and price and still attract a counterparty [COND-ORDERS].

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

Exact APIs are not specified in 0.1. `projection_ref` is assigned by the provider and need not equal the `projection_id` the Agent minted (Section 11.1); an Agent MUST be able to withdraw using the `projection_ref` the provider returned. A provider MUST NOT return a projection after accepting its `withdrawProjection`, or after its `expires_at`, and MUST publish a withdrawal latency and MUST stop returning a withdrawn projection within it (Section 25.5); an Agent MUST treat that published latency as the time for which its projection remains retrievable after withdrawal.

### 12.3 Architectures
A provider MAY be: *centralised* (a single index receiving projections and returning candidate references — the simplest architecture for a reference implementation); *federated* (multiple providers — industry registries, professional communities, banks, CRM ecosystems, recruiting or investment networks, regional networks — exchanging or routing projections); *peer-to-peer* (Agents exchanging projections without a central provider; routing is not defined in 0.1); or *privacy-preserving* (private set intersection [PSI-SLR], private information retrieval [PIR-SURVEY], secure multi-party computation, trusted execution environments, encrypted or oblivious indexes, local embeddings with privacy controls). GIDP 0.1 does not prescribe a cryptographic architecture, and does not require that a deployment use a single central provider.

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

A provider SHOULD resolve hierarchical retrieval attributes — a city against its country, a sub-industry against its industry — rather than comparing tokens for equality, and SHOULD publish which hierarchies it resolves so that an Agent knows what its projection will be matched against. This is a recommendation about provider quality, not about the protocol, and it is here because the cost of omitting it falls somewhere unexpected. A provider that compares tokens never returns a publisher who named a city to a querent who named the country, so a publisher that wants to be found compensates by publishing the country instead — coarsening its projection, and conceding a *less precise* attribute to the index, in order to repair a defect in the index. Measured on a synthetic population, resolving one hierarchy raised the recall of a precise projection from 26 % to 100 % with the publisher changing nothing it published. Where a provider resolves, retrieval quality stops arguing for coarsening altogether, and the minimisation advice of Section 11.4 is left with the single consideration it should have had: exposure. GIDP 0.1 defines no vocabulary and no hierarchy (Section 5), and does not need to; it is enough that a provider says what it resolves.

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

**Stage 6 — Consent.** When compatibility has been established, the session yields an `Opportunity` (Section 14.6). Any disclosure gated by `consent` or `principal_approval` — including Principal identity — requires a `ConsentRequest` / `ConsentResponse` exchange (Section 14.5). A potential match MUST NOT automatically reveal Principal identities.

**Stage 7 — Handoff.** After the required consents, Agents MAY reveal identities, introduce Principals, arrange a meeting, transfer the session to a negotiation agent, initiate an authorised negotiation protocol (`Handoff`, Section 14.7), or close without further disclosure. GIDP does not define the resulting agreement.

The five-round pattern of earlier working notes (discovery, compatibility, constraints, intersection, human consent) maps onto Stages 2, 4, 4–5, 6 (Opportunity) and 6 (Consent) respectively.

## 14. Protocol Objects

GIDP 0.1 defines the following object set. For each transmitted object this section lists its **required fields** (normative) and gives an **example** (non-normative). Future drafts SHOULD minimise this set where equivalent semantics can be achieved with fewer primitives, and SHOULD define a normative JSON Schema.

```text
Local, never transmitted:   StandingInterest, DisclosurePolicy
Published to providers:     DiscoveryProjection                     (Section 11)
Session control:            SessionOpen, SessionAccept, SessionClose
Compatibility:              CompatibilityRequest, CompatibilityResponse
Disclosure:                 DisclosureRequest, DisclosureResponse
Consent:                    ConsentRequest, ConsentResponse
Outcome:                    Opportunity, Handoff
```

Every transmitted object MUST carry `type`, `version` (`"gidp/0.1"` — the short token `gidp` is used instead of `gidp` throughout, because `gidp` is the established abbreviation of the IPFS Content Identifier and would be misread in the DID/VC/agent ecosystems this protocol is designed to sit in), `session_id` (`DiscoveryProjection` excepted; in `SessionOpen` the value is the proposed identifier) and `expires_at`. The **request-type** objects are `SessionOpen`, `CompatibilityRequest`, `DisclosureRequest` and `ConsentRequest`. The **response-type** objects are `SessionAccept`, `CompatibilityResponse`, `DisclosureResponse` and `ConsentResponse`. `DiscoveryProjection`, `Opportunity` and `Handoff` are neither. `SessionClose` is neither, but may be sent in place of any response.

Every request-type object MUST carry a `request_id` unique within the session, and every response-type object MUST carry `request_ref` equal to the `request_id` it answers. A `SessionClose` sent in place of a response MUST carry `request_ref`; a `SessionClose` sent on its own MUST NOT.

Every request-type object MUST be answered by exactly one response-type object or by `SessionClose`, with one exception: a **provisional** response, which is a response whose status is `pending_principal_approval` (Sections 14.4, 14.5), a `DisclosureResponse` whose status is `granted_if_reciprocal` or `granted_if_verified`, or a `CompatibilityResponse` carrying at least one per-claim result of `requires_principal_approval` (Section 15.1). A provisional response does not discharge the request; the responder MUST subsequently send exactly one further object of the same response type, carrying the same `request_ref` and a terminal status, or a `SessionClose`. A requester MUST accept that further object although it did not send a second request, and MUST NOT send a duplicate request while a provisional response is outstanding. A responder that cannot obtain a decision, or whose condition is not satisfied, before `expires_at` MUST send a terminal `declined` or a `SessionClose`. For a `granted_if_reciprocal` or `granted_if_verified` response, the terminal response is sent once the requester has reciprocated or supplied the named credential; the requester does not send a second `DisclosureRequest`.

`Opportunity` and `Handoff` are one-way notifications: they are not request-type objects and are not answered by a response-type object. A peer that does not agree with the content of an `Opportunity` MUST NOT act on it and MAY close the session.

### 14.1 SessionOpen / SessionAccept

`SessionOpen` required fields: `session_id` (proposed, opaque), `request_id`, `initiator` (opaque Agent reference), `purpose` (an interest category), `max_depth` (how far into its Disclosure Policy the initiator is willing to go in this session, named by the least exposed surface whose attributes it is prepared to disclose here, in the ordering of Section 10.1: permitted values are `network` and `session`, `session` being the deeper of the two because a `session` attribute is one that may appear nowhere but inside a Compatibility Session; `local` is never a permitted value, since `local` attributes are never transmitted), `profile` (a domain profile identifier, Section 21, or `core`), `features` (subset of `{dependency_primitives, multi_party}`; the bilateral core is implied). Optional: `trust_context` (Section 20).

`SessionAccept` required fields: `session_id`, `request_ref`, `responder`, `max_depth`, `profile`, `features` (the intersection actually supported). If the responder does not accept, it answers `SessionClose`.

The depth in force for the session is the shallower of the two declared values. An Agent MUST NOT send a `DisclosureResponse` with status `granted`, nor a `ConsentResponse` whose `granted_scope` includes an attribute, whose surface is deeper than the session's depth, whatever its own Disclosure Policy would otherwise permit; it MUST answer `declined` instead. An Agent for which the resulting depth makes the session pointless — typically because identity, whose surface is at most `session` (Section 10.6), is out of reach — SHOULD close the session with `reason: unsupported` rather than probing to no purpose. The initiator cannot distinguish that close from any other `unsupported` close, and this document does not provide a way to signal "the depth you offered is too shallow": doing so would tell a counterparty how deep the responder's policy requires it to go, which is itself a disclosure. An initiator that wishes to explore a deeper session opens a new one. Declaring a depth is not an undertaking to disclose anything: the Disclosure Policy and the gates of Section 10.2 apply in full within it.

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
A *claim* is a question about one dimension. Required fields: `key` (attribute or category name, from the core vocabulary or the session's profile), `operator`, `value`. GIDP 0.1 defines the operators `equals`, `intersects` (set overlap), `within` (the asked range, expressed as `{min, max}` or a named bucket from the profile, is compatible with the responder's private value). Where the responder's own value is itself a range — the normal case for a reservation value — `within` is satisfied by **overlap**, not containment: a private range and an asked range are compatible if they intersect at all. Containment would make almost every honest claim incompatible. Implementers should be aware that overlap semantics are also what make the probing of Section 24.3 cheap, since each answer partitions the space, and `compatible_with` (profile-defined predicate). Profiles MAY add operators.

Two values at different levels of the same hierarchy do not intersect as sets. A claim asking `geography intersects ["germany"]`, answered by a responder holding `["munich"]`, would resolve `incompatible` under plain set semantics — formally correct and substantively false, since Munich is in Germany. Section 15.2 makes that result block, so a session between two compatible Principals would end because they named one thing at two granularities. This is not a problem a shared vocabulary has to solve, and requiring one would mean requiring agreement between parties who have never met.

It is solved where evaluation already happens. A Standing Interest MAY place its own values in a hierarchy — for an attribute, a mapping from each value to the value that contains it. The responder then resolves a set-valued claim as follows, and the asymmetry is the substance of the rule:

- the claim is `compatible` if any asked value is one of the responder's held values **or anything a held value is part of**: holding `munich` answers `compatible` to `germany` and to `europe`, because it is true of Munich that it is in Germany;
- the claim is `unknown` if any asked value lies *below* a held value: a responder holding `germany`, asked about `munich`, has not said which German city it means and MUST NOT assert that the claim is false;
- the claim is `incompatible` otherwise: holding `munich`, asked about `madrid` or about `berlin`, the responder's values do contradict it.

The hierarchy is part of the Standing Interest and therefore never transmitted (Section 9.1). Nothing is negotiated, nothing is shared, and no third party is consulted: because a claim is always resolved by the party that holds the value, only that party's own values need placing. A responder that places none of its values gets set semantics and the false negative with them, which is the cost of not declaring one.

Two consequences worth stating. The rule does not widen disclosure: answering `compatible` to `europe` tells the querent what it asked and not which city, and answering `unknown` where the old reading said `incompatible` tells it strictly less. And a Discovery Provider faces the same problem one layer up with a different remedy (Section 12.4): it resolves hierarchies for the whole index because it sees only projections and queries, while inside a session only the responder can, because only the responder may see its own value.

An operator may not fit the shape of the value a responder holds: `within` names an interval but the responder's value is a label or a list, or `intersects` names a set but the responder's value is a range. A responder MUST answer `unknown` in that case. It MUST NOT treat the mismatch as a malformed message, and MUST NOT fail. Two reasons, and the second is the operative one. Failing on some shapes and answering on others makes the responder's behaviour a function of the shape of its own private value, which is an inference channel in the sense of Section 24.3. And a responder that can be made to fail by a well-formed message with an ill-fitting operator can be made to fail by anybody, which turns a claim into a denial of service. A requester learns nothing from `unknown` beyond what Section 15.1 already permits it to learn.

### 14.3 CompatibilityRequest / CompatibilityResponse

`CompatibilityRequest` required fields: `claims` (non-empty list), `allowed_results` (subset of the per-claim result vocabulary of Section 15.1 that the requester is prepared to receive; MUST include `declined`). A request MUST NOT contain the requester's own private values; it asks whether the responder is compatible with a class.

`CompatibilityResponse` required fields: `request_ref`, `results` (one entry per claim, each a result from Section 15.1 and a member of `allowed_results`, or `declined`), `session_status` (Section 15.2), `next` (`permitted`: subset of `{compatibility_request, disclosure_request, consent_request, handoff, close}`; `requires`: attribute keys whose disclosure would allow a `requires_disclosure` result to be resolved, MAY be empty).

```yaml
type: CompatibilityRequest
version: "gidp/0.1"
session_id: "opaque-session-id"
request_id: "r-2"
claims:
  - {key: domain,                       operator: compatible_with, value: enterprise_software}
  - {key: geography,                    operator: intersects,      value: [europe]}
  - {key: transaction_value,            operator: within,          value: {min: 50000000, max: 100000000}}
allowed_results: [compatible, incompatible, conditionally_compatible, unknown, requires_disclosure, declined]
expires_at: "2026-09-21T12:00:00Z"
```

```yaml
type: CompatibilityResponse
version: "gidp/0.1"
session_id: "opaque-session-id"
request_ref: "r-2"
results:
  - {key: domain,            result: compatible}
  - {key: geography,         result: compatible}
  - {key: transaction_value, result: conditionally_compatible}
session_status: open
next:
  permitted: [compatibility_request, disclosure_request, close]
  requires:  [transaction_structure_class]
expires_at: "2026-09-21T12:15:00Z"
```

### 14.4 DisclosureRequest / DisclosureResponse

`DisclosureRequest` required fields: `request_id`, `attribute`, `purpose` (free text or profile code), `requested_surface` (`session` or `network`), `intended_use` (`compatibility_evaluation`, `identity_verification`, `handoff_preparation`, or profile-defined). Optional: `retention` (`session_only`, `until_handoff`, `unrestricted`; SHOULD be present), `reciprocal` (`true` means the requester will grant the same attribute at the same surface if asked).

`DisclosureResponse` required fields: `request_ref`, `attribute`, `status` (`granted`, `declined`, `granted_if_reciprocal`, `granted_if_verified`, `pending_principal_approval`). When `granted`, the response carries `value` at the granted surface; when `granted_if_verified`, it MUST carry `verification_required`, a non-empty list of credential or attestation classes the requester must supply, expressed as opaque, binding-specific references (Section 20). `granted_if_reciprocal` means the value will be released once the requester has released the same attribute; `granted_if_verified` means it will be released once the requester has supplied a credential the responder names in `verification_required` (Section 20). A `declined` response MUST NOT indicate whether the attribute exists or what its value is. It follows, and is stated here because every implementer hesitates at this point, that an Agent which simply holds no value for the attribute also answers `declined`: the vocabulary deliberately has no way to say "not applicable", because saying it would answer the question the refusal exists to withhold.

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

Consent MUST be scoped to a session and an action. Consent to reveal identity MUST NOT be interpreted as consent to transact. A `ConsentResponse` with status `granted` MAY be issued by the Agent without a per-instance human decision only if the Standing Interest's Authority for the corresponding level (Section 16) is `true` — `disclose_attributes` corresponds to `DISCLOSE`, `reveal_identity` and `establish_direct_contact` to `INTRODUCE`, and `handoff` to `INTRODUCE` as well, since a Handoff establishes a direct relationship between the Principals — **and** no attribute in scope carries the gate `principal_approval`; otherwise the Agent MUST answer `pending_principal_approval` until the Principal decides.

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

Where the response is `pending_principal_approval`, the Principal's eventual decision arrives as the terminal response to the *original* request, carrying its `request_ref`, and either `granted` or `declined`; the provisional response did not discharge the request and only this one does (Section 14). A Principal who never answers leaves the request outstanding until the request's `expires_at`, which is the honest outcome and is why that field is required. An implementation that emits the provisional response and provides no path to the terminal one has built a gate that can ask a question and cannot hear the answer.

### 14.6 Opportunity

An `Opportunity` is produced exactly on the transition to `session_status: potentially_compatible`, that is on the state transition `PROBING → QUALIFIED` (Section 17.2). The session initiator emits it; the responder, on receiving an `Opportunity` whose content does not match its own evaluation, MUST NOT act on it and MUST close the session with `reason: unspecified` rather than correcting it in place. Required fields: `structure` (profile-defined description of the candidate state transition), `evaluated_dimensions`, `compatible_dimensions`, `open_conditions`, `contingent_on`, `identity_status` (per side: `not_requested`, `pending_principal_approval`, `granted`, `declined`).

The two counts are defined as follows, because both Agents are expected to hold the same Opportunity and cannot do so if each counts differently. `evaluated_dimensions` is the number of distinct claim keys that have a result in this session, counting each key once regardless of how often it was asked. `compatible_dimensions` is the number of those whose most recent result is `compatible`; a `conditionally_compatible` result is **not** counted as compatible. `open_conditions` lists the claim keys whose most recent result is `conditionally_compatible`, so that `compatible_dimensions` plus the length of `open_conditions` equals `evaluated_dimensions` in any session that qualifies (Section 15.2).

`contingent_on` lists the dependencies named in either side's `conditional_on` (Section 19.1) that the session has not resolved, and an Agent MUST populate it with every such dependency it holds or has learned of. A bilateral session can *record* a dependency; it cannot satisfy one, because the party the dependency names is not in the session. Without this field an interdependent Conditional Interest (Section 8.4) produces an Opportunity indistinguishable from an unconditional one — a follower's participation, contingent on a lead investor who does not exist, would read as an assembled round. A non-empty `contingent_on` means the Opportunity is contingent on something outside it, a Handoff MUST carry it forward, and a recipient MUST NOT treat the Opportunity as complete while it is non-empty. Discovering the missing party is multi-party discovery, which Section 19.2 marks experimental.

```yaml
type: Opportunity
version: "gidp/0.1"
session_id: "opaque-session-id"
structure: "minority investment + distribution agreement"
evaluated_dimensions: 5
compatible_dimensions: 3
open_conditions: [valuation_class, management_condition]
identity_status: {initiator: granted, responder: pending_principal_approval}
expires_at: "2026-09-28T00:00:00Z"
```

### 14.7 Handoff

Required fields: `target` (an object whose `kind` is `human`, `workflow` or `protocol`, with `protocol_ref` REQUIRED when `kind` is `protocol`), `authorized_scope` (subset of authority levels of Section 16 that the handing Agent carries into the target, never including `COMMIT` in GIDP 0.1), `requires_principal_presence` (boolean).

A Handoff ends GIDP's responsibility for the interaction. Where `target.kind` is `protocol`, `protocol_ref` identifies the negotiation or agreement protocol that takes over; A2A's negotiation patterns and the mandate objects being specified jointly by [A2CN] and [CONCORDIA] are the intended targets, and a GIDP binding to a negotiation protocol SHOULD map `authorized_scope` onto that protocol's own authority object rather than restating it. A Handoff MUST NOT be construed as conferring authority the handing Agent does not hold (Section 16.2), and the receiving protocol's authority object, not the Handoff, governs what may be committed.

```yaml
type: Handoff
version: "gidp/0.1"
session_id: "opaque-session-id"
target: {kind: protocol, protocol_ref: "negotiation-protocol-uri"}
authorized_scope: [NEGOTIATE_NONBINDING]
requires_principal_presence: true
expires_at: "2026-09-28T00:00:00Z"
```

### 14.8 SessionClose

Required fields: `reason` from `{declined, incompatible, unsupported, expired, completed, unspecified}`. `unsupported` is used when the session cannot proceed for a structural reason rather than a substantive one — the declared `profile` is not implemented, or the `features` intersection is empty (Section 21). An Agent MUST be able to close with `unspecified` and MUST NOT be required to give any other reason.

## 15. Compatibility Semantics and Result Vocabulary

### 15.1 Per-claim results
A response to a claim MUST use exactly one of:

| Result | Meaning |
|---|---|
| `compatible` | The responder's Standing Interest is consistent with the claim. |
| `incompatible` | It is not. |
| `conditionally_compatible` | The responder answers neither `compatible` nor `incompatible`: the claim is not ruled out, subject to conditions the responder does not disclose at this stage. It is not an assertion that the claim holds, and a requester MUST NOT read it as one. |
| `unknown` | The responder answers neither `compatible` nor `incompatible` and names no disclosure that would resolve the claim. It MAY be used because the responder cannot determine the answer, or because it elects not to determine it (Section 15.5); a requester MUST NOT infer the responder's epistemic state from it. |
| `requires_disclosure` | The responder could determine the answer if the requester disclosed the attributes listed in `next.requires`. |
| `declined` | The responder refuses to answer this claim; no reason is implied. |

### 15.2 Session status
`session_status` MUST be one of:

| Status | Meaning |
|---|---|
| `open` | The session is under way and the conditions for `potentially_compatible` are not met, while no claim has resolved `incompatible`. This covers a session in which nothing has yet been evaluated, one with an unresolved entry in `next.requires`, and one in which claims remain `unknown` or awaiting a Principal decision. |
| `potentially_compatible` | Every claim sent in the session has resolved to `compatible` or `conditionally_compatible`; at least one has resolved `compatible`; and no entry in `next.requires` remains unresolved. This status is reached at most once per session, and an `Opportunity` is produced on reaching it (Section 14.6). |
| `incompatible` | At least one claim has resolved `incompatible` and neither side has a disclosure that could change it. |
| `closed` | The session is closed (Section 14.8). |

It maps onto the state machine of Section 17.2: `open` ↔ `PROBING`/`DISCLOSURE_PENDING`; `potentially_compatible` ↔ `QUALIFIED` and later states; `incompatible` and `closed` ↔ `CLOSED`. A `potentially_compatible` status asserts the absence of a known obstacle; it does not assert that the Principals are compatible.

A `declined`, `unknown` or `requires_disclosure` result therefore prevents qualification, and this is deliberate: `declined` carries no information whatever (Section 18), so an Opportunity that counted it as neutral would rest on silence. A requester that wants to qualify despite such a result asks the claim again — results are keyed by claim key and the most recent answer stands — or accepts that the session does not qualify. An implementation MUST NOT produce an `Opportunity` from a session in which any claim's most recent result is one of those four.

### 15.3 Operational outcomes
Operational outcomes — `unsupported`, `unauthorized`, `expired`, `rate_limited`, `temporarily_unavailable` — belong to the transport binding, not to the GIDP object set: a binding conveys them through its own error mechanism, and GIDP defines no object for them. They are named here because they are observable by a peer and therefore part of the protocol's information flow; GIDP 0.1 defines no enumeration for them, and an implementation that ships one has added a closed vocabulary this document does not impose. An operational outcome is not a compatibility result and MUST NOT be used to encode one (Section 18); a peer that receives one MUST NOT infer anything about the responder's Standing Interest from it. An implementation that has no binding-level error mechanism available MUST use `SessionClose` with the matching `reason` instead.

### 15.4 Local evaluation
A claim MAY be evaluated locally against `evaluation_only` values without exposing them. Example: Agent A privately knows `maximum_valuation = 80M`; asked whether a transaction `within {50M, 100M}` is compatible, it may answer `conditionally_compatible` without exposing `80M`.

Note what the querent nevertheless learns. A coarsened answer asserts nothing (Section 15.1), but it does tell the querent that the range it named is not ruled out, and a querent that names its own candidate value learns the same about that value. This is not a defect of the example; it is the inference channel of Section 24.3 seen from the asking end, and it is why a responder's protection lies in the abuse controls of that section rather than in the vocabulary alone.

Coarsening protects the **value**, not the **inference**, and the distinction is load-bearing. Replacing one truthful result with `conditionally_compatible` whenever the truthful result would have been affirmative substitutes one deterministic answer for another: a querent that knows the policy partitions the responder's possible values exactly as it would have under a plainly truthful answer, and learns precisely as much. Measured over an adaptive querent, a deterministic coarsening reduces extracted information by nothing at all. It remains necessary — it is what keeps `80M` off the wire — and it is not an inference control. Section 24.3 states what is.

### 15.5 Truthfulness and coarsening
A responder MUST NOT answer `compatible` where its values make the claim false, and MUST NOT answer `incompatible` where its values make the claim true. A responder MAY replace either truthful answer with `conditionally_compatible`, `unknown` or `declined`. These are the only permitted deviations from the truthful answer. Whether a given pattern of replacement limits inference is a separate question, answered in Section 24.3 and not by this section: a deterministic replacement conveys the same information as the answer it replaces, and a replacement that conveys nothing also discriminates nothing.

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

`NEGOTIATE_NONBINDING` is deliberately outside the Compatibility Session. Earlier working drafts of this protocol left it ambiguous whether non-binding structures could be proposed *inside* a session; this draft settles the question: they cannot. A Compatibility Session establishes whether two Principals should be talking, using the result vocabulary of Section 15 and nothing else; proposing terms, even non-binding ones, is negotiation and takes place after a Handoff (Section 14.7), under whatever protocol the Handoff targets. The level is retained in the GIDP ladder because a Principal must be able to express, in the Standing Interest, whether its Agent may carry that authority forward at all — not because GIDP carries the negotiation.

### 16.2 Invariant
Implementations MAY use a different authorisation model internally. They MUST preserve the following invariant:

> An Agent MUST NOT perform an action at one authority level on the strength of holding a lower one, and MUST NOT perform, or represent to a counterparty that it may perform, a binding commitment on the strength of any GIDP authority. An Agent MUST NOT request or accept an action from its counterparty on the sole ground that the counterparty has previously performed actions of that kind.

Non-inference is necessary but not sufficient. Where an Agent asserts an authority level to a counterparty, that assertion MUST be capable of being evidenced by a referenceable delegation artefact — a signed delegation mandate, delegation credential, token-exchange result or equivalent issued under the Principal's control and verifiable by the relying party (Section 20) — and a relying party MUST be able to request that evidence before acting on the assertion. An implementation that cannot produce such an artefact MUST represent the level as unevidenced, and a counterparty MUST be free to treat an unevidenced assertion as absent.

This requirement is not merely hygienic. Under the doctrine of apparent authority, a principal may be bound by conduct that leads a counterparty reasonably to believe its agent was authorised, and commentators have begun to argue that the doctrine applies to AI agents acting in commerce [DEMOTT2026]. A protocol in which authority is asserted but never evidenced would systematically manufacture exactly the observable conduct on which such a belief is built. Requiring evidence, and requiring that its absence be visible, is how GIDP keeps exploration from silently becoming authority.

Trust in a counterparty (Section 20) does not imply authority of that counterparty. Where a level is `approval_required`, the corresponding `ConsentResponse` or `DisclosureResponse` MUST be `pending_principal_approval` until the Principal decides (Section 14.5).

### 16.3 Levels of human control (non-normative)
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

The transitions apply to **both** Agents' views of the session: a responder's state moves on the request it receives and on the response it sends, exactly as the requester's does. Discharging, however, is one-sided — an Agent discharges only the requests it sent itself (Section 14), because the `request_id` belongs to the sender. An implementation that conflates the two will reject its own peer's traffic.

| From | Event | To | Side effect |
|---|---|---|---|
| — | `SessionOpen` sent or received | `REQUESTED` | — |
| `REQUESTED` | `SessionAccept` | `PROBING` | Session depth and profile fixed (Section 14.1) |
| `REQUESTED` | `SessionClose` | `CLOSED` | — |
| `PROBING` | `CompatibilityRequest` / `CompatibilityResponse` | `PROBING` | `session_status` updated (Section 15.2) |
| `PROBING` | `DisclosureRequest` | `DISCLOSURE_PENDING` | — |
| `DISCLOSURE_PENDING` | `DisclosureResponse` with status `granted`, `declined`, `granted_if_reciprocal` or `granted_if_verified` | `PROBING` | A conditional status leaves the attribute undisclosed until its condition is met |
| `DISCLOSURE_PENDING` | `DisclosureResponse` with status `pending_principal_approval` | `DISCLOSURE_PENDING` | Provisional response; the request is not discharged (Section 14) |
| `DISCLOSURE_PENDING` | terminal `DisclosureResponse` following a provisional one | `PROBING` | — |
| `PROBING` | `session_status` reaches `potentially_compatible` | `QUALIFIED` | The session initiator produces the `Opportunity` (Section 14.6) |
| `PROBING`, `DISCLOSURE_PENDING` or `QUALIFIED` | `session_status` reaches `incompatible` | `CLOSED` | Either Agent sends `SessionClose` with `reason: incompatible` |
| `DISCLOSURE_PENDING`, `CONSENT_PENDING` or `CONSENTED` | `CompatibilityRequest` / `CompatibilityResponse` | unchanged | Probing continues alongside a pending request |
| `QUALIFIED` | `CompatibilityRequest` / `DisclosureRequest` | `QUALIFIED` / `DISCLOSURE_PENDING` | Probing may continue after qualification |
| `QUALIFIED` | `ConsentRequest` | `CONSENT_PENDING` | — |
| `CONSENT_PENDING` | `ConsentResponse` with status `granted` | `CONSENTED` | The granted scope is in force for this session only |
| `CONSENT_PENDING` | `ConsentResponse` with status `declined` | `QUALIFIED` | — |
| `CONSENT_PENDING` | `ConsentResponse` with status `pending_principal_approval` | `CONSENT_PENDING` | Provisional response; the request is not discharged |
| `CONSENTED` | `ConsentRequest` | `CONSENT_PENDING` | Consent is per action and per scope |
| `QUALIFIED` or `CONSENTED` | `Handoff` | `HANDED_OFF` | A recipient that receives a `Handoff` in any earlier state MUST close the session with `reason: unsupported` |
| `HANDED_OFF` | `SessionClose` | `CLOSED` | `reason: completed` |
| any state | `SessionClose`, or expiry of the session | `CLOSED` | `CLOSED` carries the close reason; expiry uses `reason: expired` |

A `declined` `DisclosureResponse` returns the session to `PROBING`; it does not close it. `CLOSED` is terminal: an Agent MUST NOT reopen a closed session, and a new interaction requires a new `session_id`.

## 18. Error and Non-Disclosure Semantics

Errors require special care because they can become privacy oracles. An implementation MUST distinguish operational outcomes (Section 15.3) from compatibility results (Section 15.1) and MUST NOT use the former to convey the latter.

A responder MAY answer `declined` rather than `incompatible` whenever distinguishing "incompatible" from "not authorised to evaluate" or "not willing to disclose" would leak protected information; a requester MUST NOT infer incompatibility from `declined`. A refusal that follows from the responder's own Authority or Disclosure Policy — for example a `DisclosureRequest` received by an Agent whose `DISCLOSE` level is `false` — MUST be reported as `declined`, never as the operational outcome `unauthorized`, which is reserved for the transport and session layer (rejecting a message the peer was not entitled to send at all). Failure to progress MUST NOT convey *why* a compatibility test failed unless the Disclosure Policy explicitly permits that information. Response timing SHOULD NOT vary systematically with the value of a protected attribute (Section 24.7).

## 19. Dependency Primitives and Multi-Party Discovery (Experimental)

### 19.1 Dependency primitives (core)
A Standing Interest MAY carry four generic relationship lists: `provides` (what the Principal can bring), `requires` (what it needs from others), `conditional_on` (events or commitments that must hold), `excludes` (counterparties, structures or conditions ruled out). They are part of the core Standing Interest model and MAY be used in bilateral sessions (e.g. `requires: capability X` ↔ `provides: capability X`, Appendix C.3). Only `excludes` MUST be supported by every implementation; the other three MUST be supported by implementations that declare the `dependency_primitives` feature (Section 14.1).

None of the four is self-enforcing, and `excludes` is the one where that matters. An Agent that declares `excludes: X` has recorded a disqualifying property; it has not caused anything to test for it. A counterparty that never asks never learns, and a session in which nobody asked can qualify and produce an Opportunity between two parties one of which excludes a property the other has. This is the same shape as the contingency gap of Section 14.6, and it is left as a duty on the Agent rather than a mechanism: an Agent holding `excludes` SHOULD ask the corresponding claim before qualifying, and an Opportunity asserts nothing about exclusions no claim tested.

Nor is `excludes` the negation of `requires`. *Requires X* says the Principal needs X present; *excludes X* says X is disqualifying whoever supplies it. The negation of the first is "does not need X", which is not the second, and a profile that collapses them will produce Opportunities its Principal would refuse.

The four names are **reserved claim keys**: a claim (Section 14.2) naming one of them is resolved against the corresponding list rather than against the Conditional Interest's conditions, which is what makes the bilateral use above reachable. The Disclosure Policy classifies them like any other attribute (Section 10), and the expected pattern is asymmetric, deliberately so. What a Principal *provides* is ordinarily disclosable — it is what makes it findable at all. What it *requires* is the mirror image of what it lacks, and a capability gap admitted to a prospective partner is admitted to a prospective competitor; a Principal will therefore commonly classify `requires` as `evaluation_only`, so that "do you require X?" is answered truthfully but coarsened (Section 15.5) while "do you provide X?" is answered plainly.

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

Some claims depend on facts that should be verifiable without being fully disclosed: accredited-investor status, revenue range, professional qualification, authorisation to represent an organisation, ownership of an asset, geographic eligibility, available financing. An implementation MUST be able to carry references to external identity, credential, attestation, selective-disclosure and delegated-authority systems — selective disclosure of signed claims [RFC9901] [BBS], verifiable-credential proofs [VC-DI], delegated authority obtained by token exchange [RFC8693], workload and agent identity [WIMSE-AI], and external transaction-authorisation objects of the kind noted in Section 3 — carried in `SessionOpen.trust_context` and in `DisclosureResponse.verification_required` as opaque, binding-specific references. This document defines no identity system of its own, and an implementation MUST NOT require one specific external system as a condition of interoperating.

One such system is already published rather than prospective. GNAP [GNAP], a Standards Track RFC, defines how a piece of software negotiates delegated authority with an authorisation server and how the result is conveyed, covering both access to resources and subject information. Its grant is negotiated and continuable rather than a fixed scope string, which is the shape Section 16's ladder needs, and it is the natural referent for the `evidence_ref` that Section 16.2 requires. GIDP neither profiles it nor depends on it; naming it is meant to save an implementer the search.

Which external systems supply persistent agent identity, ownership, delegation chains, attestations, reputation and revocation is outside this specification. This is a real gap rather than a deferred detail: a GIDP deployment cannot enforce Section 16.2 without at least one such system, and none of them is yet dominant. Sections 20 and 24.5 state what GIDP requires of whichever system is chosen; the choice itself belongs to the binding and the deployment.

## 21. Extensions and Domain Profiles

GIDP Core avoids embedding vertical concepts. A *domain profile* MAY define vocabularies (claim keys, categories, buckets), validation rules, credential requirements, compatibility dimensions, regulatory constraints, additional claim operators and Handoff semantics for domains such as employment and executive recruiting, M&A, investment and co-investment, real estate, commercial partnerships, joint ventures, licensing, procurement, private expertise, research collaboration, financing, insurance, philanthropy and business succession.

A profile MUST NOT weaken the core privacy and authority semantics of Sections 10, 15.5, 16 and 24. A session uses exactly one profile, declared in `SessionOpen` and confirmed in `SessionAccept` (Section 14.1). A responder that does not implement the declared profile, or that shares no declared feature with the initiator where the initiator requires one, MUST answer `SessionClose` with `reason: unsupported` (Section 14.8) and MUST NOT propose an alternative profile in that response; richer extension negotiation is future work.

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
        "uri": "{{CANONICAL_URL}}/extensions/conditional-interest-discovery/0.1",
        "description": "Graduated Interest Disclosure 0.1",
        "required": false,
        "params": { "profiles": ["core"] }
      }
    ]
  }
}
```

`required` is false deliberately. An Agent that made GIDP mandatory would refuse every counterparty that speaks plain A2A, which is the opposite of what a discovery protocol is for.

Declaring an extension does not activate it. A client that intends to use one sends the `A2A-Extensions` header carrying a comma-separated list of extension URIs, and the responder echoes back the subset it actually activated; an extension that was not echoed is not in force, whatever the Agent Card says. This matters for GIDP more than for most extensions, because it is the point at which an exchange can be refused before any GIDP object exists, and therefore before any Disclosure Policy has been consulted.

GIDP objects are then carried in the `metadata` map of A2A's core structures, under keys prefixed by the extension URI — A2A's own convention, which keeps extensions from colliding and leaves core types unmodified. A GIDP object is not content for a human to read, so it belongs in `metadata` rather than in a message Part.

Note that two negotiations are now in play and neither subsumes the other. A2A activation answers *does this peer speak GIDP at all*; the `features` of Section 14.1 answer *which optional GIDP features are in force for this session*, and Section 14.1 requires `SessionAccept` to carry the intersection actually supported rather than an echo. A peer may activate the extension and support no optional feature whatever. An implementation that derives one from the other will be wrong in the direction that matters, by assuming a feature is in force because the extension was activated.

The extension URI above is illustrative: GIDP 0.1 allocates no URI and registers nothing (Section 26), and two deployments that pick different URIs will not interoperate — which is an argument for allocating one before there are two. The binding itself is not defined here. Whether GIDP is ultimately an A2A extension, a separate protocol or a reusable application profile is an open governance question (Appendix E). A worked mapping, with round-trip tests against every object that crosses a wire, is in the reference implementation under `impl/gidp/bindings/a2a.py`.

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

Capability registries and intent-based agent selection answer *which Agent can perform X*; authorisation and payment protocols establish *that an Agent is permitted to perform an action or payment*; negotiation protocols govern *what Agents may propose or accept once they are negotiating*. GIDP addresses the stage before all three: *whether two Principals should be negotiating at all*, without publishing the information that would normally make that discoverable.

## 23. Interoperability and Conformance

### 23.1 Interoperability
A GIDP implementation SHOULD allow Agents from independent vendors or platforms to participate. Interoperability in 0.1 requires agreement on: object semantics and required fields (Section 14); disclosure surfaces and gates (Section 10); the result vocabulary (Section 15); authority level names (Section 16); expiry and close semantics (Sections 14.8, 17); the profile identifier (Section 21).

### 23.2 Conformance criteria
An implementation claiming **GIDP Core 0.1** conformance MUST:

1. express all four situations of Section 8 and run a session for each, with the four differing only in their Disclosure Policies and producing the same sequence of protocol objects. "Verified by local inspection" is not a conformance criterion; this one is executable, and it is the criterion that carries the horizontality claim of Appendix F.2 of an implementation's Standing Interest representation, not on the wire;
2. never transmit a Standing Interest, a Disclosure Policy, or any attribute of surface `local` (Sections 9.1, 10);
3. enforce Disclosure Policies and Authority outside unconstrained model behaviour, such that for any transmitted object the decision to transmit it is reproducible from the Standing Interest, the Disclosure Policy and the session state alone (Section 6.10, Section 24.10);
4. generate Discovery Projections that satisfy the required fields and the content rule of Section 11.1 and 11.2;
5. support at least one Discovery Provider mechanism through which a projection can be published, updated, withdrawn and retrieved, with withdrawal observable within the provider's published latency (Section 12.2), and never treat retrieval as compatibility, consent or agreement;
6. implement the session objects of Section 14 with their required fields, the result vocabulary of Section 15 and the state machine of Section 17.2;
7. respect the truthfulness bounds of Section 15.5;
8. allow an Agent to decline any claim and close any session with `reason: unspecified`;
9. before disclosing an attribute whose gate is `consent`, require a `ConsentResponse` with status `granted` covering it; before disclosing an attribute whose gate is `principal_approval`, require a per-instance Principal decision, conveyed by a terminal `DisclosureResponse` or `ConsentResponse` following a provisional `pending_principal_approval` (Sections 10.2, 14, 14.5);
10. implement the authority levels of Section 16 with `COMMIT` fixed to `false` and preserve the invariant of Section 16.2;
11. on suspension, revocation, expiry or supersession of a Standing Interest, withdraw or update every projection derived from it, and close every open session derived from it unless the Principal has directed otherwise (Sections 9.2, 17.1);
12. emit a `Handoff` with the fields of Section 14.7 when the Principal or an Agent with the corresponding authority directs it, and treat the session as terminal thereafter;
13. implement the closed vocabularies of Section 26 without extension.

Conformance to criteria 6 and 13 is testable against transmitted objects; criterion 3 is testable by replaying a session against a stated Standing Interest and Disclosure Policy and checking that the same objects are produced.

**Deployment requirements.** Separately from the criteria above, which concern interoperability, a deployment of GIDP MUST publish a deployment-specific privacy and probing threat model stating how it bounds inference through repeated claims (Sections 15.6, 24, 24.3). This is a condition of responsible deployment, not of protocol conformance, and it is stated once here rather than repeatedly in the body.

Implementations MAY omit the `dependency_primitives` and `multi_party` features.

### 23.3 Reference implementation goals (non-normative)
A minimal reference implementation demonstrates: two independently running Agents; several local Standing Interests per Agent; Discovery Projections; a Discovery Provider or equivalent; candidate retrieval; a structured Compatibility Session; at least one locally evaluated `evaluation_only` condition on each side; progressive disclosure; consent; identity reveal or Handoff; revocation of a projection; and logs showing that `local` attributes were never transmitted. A stronger implementation pairs one personal Agent with one enterprise-style Agent and shows that the Opportunity could not have been discovered from public capability metadata alone. A multi-party demonstration is optional.

## 24. Security Considerations

Security and privacy are core protocol concerns here rather than a closing section: the protocol's purpose is to carry information whose disclosure is the harm. A deployment publishes a threat model covering the threats below; that requirement is stated in Section 23.2 under *Deployment requirements*. This section follows the guidance of [RFC3552].

### 24.1 Harvesting and enumeration of interests
An attacker attempts to enumerate latent sellers, candidates, investors, buyers or strategic interests. Mitigations: Section 12.5 provider controls; coarse candidate sets; no bulk export.

### 24.2 Identity inference and correlation
An attacker combines projection metadata with external information, or correlates projections across providers, to infer the Principal. Mitigations: projection minimisation (Section 11.4); avoidance of stable identifiers and unnecessary metadata; distinct projections per provider (Section 11.5); symmetric attributes.

### 24.3 Constraint extraction by probing
An attacker uses repeated claims to approximate a hidden reservation value (`within {50M,60M}? compatible — {60M,70M}? compatible — {70M,80M}? compatible — {80M,90M}? incompatible`). Even though the threshold is never transmitted, it has effectively been disclosed. Implementations SHOULD apply, within the bounds of Section 15.5: query budgets; rate limits; minimum claim granularity (bucket width); bucketed or randomised responses; session-level privacy budgets; trust tiers; authenticated counterparties; query history and coordinated-probing detection across identities; refusal policies; delayed responses; disclosure accounting; local policy engines. GIDP 0.1 does not define a universal privacy-budget algorithm.

There is an older literature on exactly this decision and it was not consulted when this section was first written. *Query auditing* asks whether to answer or deny a query given the history of queries already answered, and [KMN2005] establishes the result that matters here: **denials leak**. An auditor that decides to deny based on the data it is protecting tells an attacker something by denying, and the paper's worked example recovers a database exactly from one answer and one refusal. Their repair is *simulatable auditing*: the decision to answer or deny must depend only on the queries asked and the answers already given, never on the data and never on the answer being withheld. An attacker who can reproduce the decision learns nothing from it.

Read against that, the coarsening illustrated in Section 15.4 is not simulatable. It replaces an answer *when the truthful answer would have been affirmative*, so the choice to coarsen is itself a function of the secret, and it carries the same bit the answer would have carried. That is the general reason behind the measurement reported below, and it generalises: within this protocol, any rule for coarsening or declining that consults the responder's own values is a channel of the same width as the answer it replaces. A responder that wishes to conceal must decide from the claim sequence alone — which is what a query budget does, and is why a budget is the only mitigation in the sweep that bounds anything.

The same literature tempers the ambition. Deciding auditability is computationally hard in general: [KMN2005] reports the offline maximum sum and maximum max auditing problems to be NP-hard, with related Boolean formulations coNP-hard. A universal, efficient auditor is not a thing this specification should expect anyone to supply.

Not all of those mitigations do the same work, and saying so is more useful than listing them. Measured against an adaptive querent that asks whichever claim best splits its remaining hypotheses and re-asks it when the answer was uninformative: a deterministic coarsening of the kind illustrated in Section 15.4 bounds nothing, because it relabels answers without merging them; a randomised response delays the querent and does not bound it, since repetition recovers what randomisation hid, and it costs discrimination, since a coarsened refusal reads as a maybe; and a policy that answers `conditionally_compatible` or `declined` to every claim over a private attribute leaks nothing and qualifies either everyone or no one. **The unit is the mistake.** A budget counted in claims cannot separate the two populations, and the reason is arithmetic rather than adversarial: an honest counterparty asking whether its ceiling clears a threshold asks one question over a wide band and learns a fraction of a bit, while a probing counterparty asks a narrowing sequence in which each question costs a full bit *by construction*, because that is what a bisection is. Counted in questions the two overlap. Counted in information they are not the same population.

A responder can therefore budget what it discloses rather than what it answers, and the mechanism for doing so is the one [KMN2005] prescribes. The responder keeps the posterior an observer would hold — the set of values still consistent with every answer it has given — and before answering a new claim asks what that posterior would become **under every answer it might give**, refusing if the worst case would cross its budget. Taking the worst case is what keeps the decision independent of the value: it depends only on the claims asked and the answers already given, so an observer can reproduce it and a refusal carries no information about what is being protected. A responder that refused because of its own value would be the leak it was trying to prevent.

Three properties follow, and they are why this is the mitigation to implement first. It needs no identity, no third party and nothing carried between sessions but the responder's own record, so **Section 24.4 does not defeat it**: the posterior is the responder's, and it does not matter who asks or under how many names. It cannot be evaded by disguising the sequence, because the accounting is over information rather than over pattern. And it is automatic, which none of the other mitigations in this section are.

Measured over a five-bit threshold, a two-bit budget holds a probing counterparty to under one bit while serving most honest counterparties; the ones it refuses are those asking narrow bands, which is correct rather than unfortunate, since a precise question is precisely what is expensive. Implementations SHOULD budget disclosure per attribute in this way, and SHOULD publish nothing about the budget's state, which an observer can compute for itself.

A second control composes with it and has the opposite shape. A profile MAY require every claim's bounds to fall on a lattice of a defined width. Because a private bound is tested at the *edge* of the band asked, constraining the width of a band achieves nothing while constraining where edges may fall caps the resolution outright at `log2(range / width)`, whatever number of claims is asked. It holds no state, so honest traffic does not deplete it and an adversary cannot drain it, and its cost falls on precision rather than on service: a counterparty rounds its question to the lattice and is answered. Measured on a five-bit threshold, a lattice a fifth of the range wide holds a probing counterparty to under half the secret while answering every honest counterparty, where a budget holding it lower refuses one in eight. Neither dominates the other; a deployment chooses which cost it prefers, or composes both.

One deployment practice belongs beside it, because it is nearly free and is not otherwise obvious. A bound on the *rate* rather than the total makes extraction take time, and a private value that is revised over that time is a moving target: what an adversary narrows between revisions, it loses at the next one. Measured against this document's own evaluator, the surviving uncertainty settles at roughly `2d / (2^r − 1)` candidate values, where `r` is the claims answered per period and `d` is how far the value moves in one. The shape of that expression is the useful part and it is not encouraging in the obvious direction: the protection is *exponential* in the rate allowed and only *linear* in how fast the value moves, so halving the rate is worth far more than doubling the drift, and against a competent adversary a slow drift buys almost nothing. Where it does earn its place is against an adversary that does not model the movement at all: such an adversary does not end up uncertain, it ends up confident and wrong, which is a worse position to act from. A Principal that re-authors its Standing Interest when its validity expires (Section 9.2) is therefore taking a privacy measure and not merely keeping records tidy. None of this is a bound the protocol provides; all of it is a bound a deployment can choose. Rate limits, granularity floors and session budgets are all forms of it. Its known weakness is that a budget keyed to a counterparty does not bound an asker that faces many counterparties, and a budget keyed to the asker requires a persistent identity this protocol deliberately does not carry. The measurements behind this paragraph, and the mechanism comparison they come from, are in the companion document *Why not use an existing mechanism?*; they are reproducible from the reference implementation.

This threat has a formal treatment. [RANI2026] formalises *behavioural privacy leakage* in agentic negotiation — the inference of private constraints from negotiation dynamics rather than from disclosed values — and mitigates it with a phase-adaptive randomised policy achieving (ε,δ)-differential privacy while preserving convergence. That work models a **passive** adversary observing traces, and explicitly leaves adaptive and active adversaries to future work. GIDP's adversary is the active case: a counterparty that *chooses* the next claim in order to narrow a threshold, against an oracle that is obliged by Section 15.5 to answer truthfully or not at all.

> **Open problem — adaptive probing of a truthful compatibility oracle.**
>
> Let a responder hold a private constraint set *C* over attributes of a Standing Interest. A querent submits claims *q₁, q₂, …* adaptively: each *qᵢ* may depend on every answer received so far. The responder answers under Section 15.5, which permits exactly three behaviours per claim — the truthful result, a coarsening of it (`conditionally_compatible` or `unknown`), or `declined` — and forbids any answer that asserts what the responder's values contradict.
>
> A mechanism is a (possibly randomised) responder policy. Two quantities are in tension. **Leakage** is what an adaptive querent learns about *C* after *k* claims, measured as the reduction in the uncertainty set of *C*, or in the differential-privacy sense of [RANI2026] extended to an adaptive adversary. **Utility** is the probability that a session between two genuinely compatible Principals reaches `potentially_compatible` (Section 15.2) within a bounded number of claims.
>
> The open problem is to exhibit a responder policy, or prove that none exists, that bounds leakage under adaptive querying while keeping utility above a usable threshold — with three properties that distinguish it from the solved cases: the adversary chooses its queries rather than observing a trace, the responder must remain truthful in the sense of Section 15.5 rather than free to lie, and the bound must hold across sessions and identities, since an adversary may split its budget over many Sybil counterparties (Section 24.4).
>
> Three neighbouring results do not settle it. [RANI2026] bounds leakage from *observed negotiation dynamics* against a passive adversary and explicitly leaves adaptive adversaries to future work. Differentially private query mechanisms bound leakage under adaptive querying but assume the responder may return a perturbed answer, which Section 15.5 forbids where the perturbation would assert a falsehood. Private set intersection and secure computation hide the responder's inputs from the querent but not the information carried by the *result*, which is the leak in question.
>
> GIDP 0.1 states this as the protocol's principal research question rather than pretending to solve it, and treats the abuse controls above as engineering mitigations, not guarantees. Section 15.6 states the corresponding protocol-level consequence: a result vocabulary and its abuse controls cannot be specified independently of each other. Candidate directions, none of them validated, are discussed in the companion document (Appendix E); contributions and refutations are both welcome.

### 24.4 Sybil agents
An attacker operates many Agents or Principals to bypass query limits or obtain different disclosure views. Identity, credential, reputation, staking, economic or membership mechanisms MAY be used.

This threat and the mitigation of Section 24.3 cancel each other, and the cancellation is measurable rather than theoretical. A query budget keyed to the counterparty bounds only the product of the budget and the number of counterparties an attacker can mint: in the reference implementation's worked case, an allowance of two claims per counterparty and four identities extracts exactly what an allowance of eight and one identity extracts, because nothing in this protocol connects the two. That is not an oversight in the budget design. It follows from the same property that keeps a responder from profiling its counterparties — opaque endpoints — seen from the other side: an Agent that cannot recognise who it is talking to cannot recognise that it is being enumerated.

A cap on the responder's *total* answered claims, to anyone, over the life of a Standing Interest, cannot be diluted by identities and does bound. Its price is that it cannot distinguish the populations it is rationing, and where the cap should sit is a computation rather than a guess. An honest session costs one claim per attribute it asks about; an extraction costs one bisection per *private* attribute, which is logarithmic in the number of values that attribute may take. A separating cap exists when the second exceeds the first, so the window opens as the secret grows and closes as it shrinks: over 41 candidate values and a five-claim session there is no separating cap at all, while over 128 there is, and over a thousand the window is wide. A deployment that wants its budget to mean something computes that ratio for its own attributes rather than inheriting a number. Deployments SHOULD state which of the two they have chosen and at what level; GIDP 0.1 defines neither, and an implementer should not read Sections 24.3 and 24.4 together as describing a solved problem.

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
Depending on sensitivity and deployment model, implementations MAY use local evaluation, trusted intermediaries under contractual or technical controls, trusted execution environments, private set intersection (where compatibility is set intersection) [PSI-SLR], secure multi-party computation — including the privacy-preserving stable-matching constructions that have been demonstrated at national-registry scale [SSM-CCS16] — zero-knowledge proofs (e.g. "threshold satisfied" without revealing threshold or value), encrypted indexes, privacy-preserving retrieval [PIR-SURVEY] or attestations. No single technique is likely to fit all Standing Interest types; the protocol specifies desired information-flow properties before standardising a mechanism.

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

This document requests no IANA actions, and deliberately avoids creating facts that would require them: identifiers in examples are opaque strings, no URN namespace identifier is used or requested, no media type is registered, and no URI is allocated for the transport binding sketched in Section 22.2.

Should this work be pursued as an Internet-Draft, it would require, at minimum: a URN namespace identifier or an equivalent identifier scheme for projections and sessions; a media type for each transport binding; and registries for the closed vocabularies this draft defines — disclosure surfaces (Section 10.1), gates (Section 10.2), per-claim results (Section 15.1), session statuses (Section 15.2), operational outcomes (Section 15.3), authority levels and their permitted values (Section 16.1), consent actions (Section 14.5), disclosure statuses and the `intended_use` and `retention` vocabularies (Section 14.4), the `next.permitted` vocabulary (Section 14.3), `identity_status` values (Section 14.6), `Handoff` target kinds (Section 14.7), close reasons (Section 14.8), session features (Section 14.1) and profile identifiers (Section 21).

Those vocabularies are **closed in 0.1**: an implementation MUST NOT add values to them. The two deliberate extension points are domain profiles, which are identified rather than enumerated and which MAY define claim keys, claim operators (Section 14.2), retrieval attributes (Section 11.1) and `relation` values within the profile's own namespace, and future versions of this document.

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
  interest:
    class: enum[passive_conditional_demand, confidential_active_demand,
                private_conditional_supply, interdependent_conditional_interest]
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
*Principal A*, a French software company, privately authorises its Agent to explore expansion into Germany through acquisition, majority investment, distribution or joint venture. Its budget is `evaluation_only`.

*Principal B*, a German software company, is not for sale. Its Agent is nevertheless authorised to explore strategic transactions if the counterparty provides access to France, the founder remains operationally involved, and a private valuation threshold is met.

*Discovery.* A projects `strategic_transaction · enterprise_software · europe`; B projects `strategic_transaction · enterprise_software · cross_border`. Neither projection states buy or sell.

*Session.* After `SessionOpen`/`SessionAccept` (profile `core`, depth `session`), the claims resolve as: geography `compatible`; market access `compatible` (B `requires: market_access_france`, A `provides` it, disclosed at surface `session`); transaction structures `compatible`; valuation class `conditionally_compatible`; management condition `conditionally_compatible`. Neither side learns the other's valuation boundary.

*Opportunity.* Every claim resolved `compatible` or `conditionally_compatible` and nothing remains in `next.requires`, so `session_status` becomes `potentially_compatible`, the session enters `QUALIFIED`, and an Opportunity `minority investment + distribution agreement` is produced: five dimensions evaluated, three `compatible`, `open_conditions: [valuation_class, management_condition]` — the two that resolved `conditionally_compatible` — and `identity_status: {initiator: not_requested, responder: not_requested}`.

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

**Privacy.** How should re-identification risk of projections be measured? How should query privacy budgets work within the bounds of Section 15.5? Which cryptographic profiles are practical? How can behavioural leakage be bounded? The open problem stated in Section 24.3 — bounding what an *adaptive* querent can learn from a truthful compatibility oracle while keeping that oracle useful for discovery — is the question on which the authors most want contributions; [RANI2026] solves the passive case and explicitly leaves the active one open.

**Trust and authority.** How should Agents prove authority for a specific Standing Interest? How should Principals be verified without unnecessary identity disclosure? How should reputation work without enabling surveillance? How should GIDP reference external delegated-authority credentials? At what point does identity become necessary?

**Multi-party.** How are dependencies discovered without combinatorial explosion? How are coalitions scored? How is information shared when members have different Disclosure Policies? How are circular conditions handled? When should a partial coalition be revealed?

**Governance.** Should GIDP become an A2A extension, a separate protocol or a reusable application profile? Which parts should be standardised versus left to Discovery Providers? What namespace and versioning model? If GIDP gains adoption, what governance structure preserves neutrality?

**How to comment.** The canonical location of this document is {{CANONICAL_URL}}. Objections, corrections, implementation reports and refutations should go to the issue tracker there, or to {{CONTACT}}. Every substantive comment received will be answered in public and, where it changes the text, recorded in the revision history with attribution. A companion document at the same location, *Open Problems and Design Rationale*, carries the non-normative material that does not belong in a specification: the mapping from this document's requirements to existing cryptographic and identity mechanisms, the candidate directions for the open problem of Section 24.3, and the reasoning behind choices this text states without arguing.

**Five questions for reviewers.**

1. Is private reciprocal Standing Interest discovery a distinct protocol problem, or should it be absorbed into existing agent discovery?
2. Is the Standing Interest / Discovery Projection distinction, with the surface/gate disclosure model, sufficient to support useful discovery without unacceptable leakage?
3. Are `provides`, `requires`, `conditional_on` and `excludes` adequate foundations for future multi-party discovery?
4. Which parts of GIDP should be standardised, and which should remain implementation-specific to Discovery Providers?
5. Where does the abstraction fail when applied across executive recruiting, M&A, investment, real estate and commercial partnerships?

## Appendix F — Standardisation Strategy and Evaluation Criteria

### F.1 Strategy
The sequence adopted is publication of the specification first, reference implementation immediately after. A reference implementation of the bilateral core accompanies this draft at the canonical location, together with the conformance suite of Section 23.2 and a demonstration of the probing attack of Section 24.3. The purpose of Draft 0.1 is not premature formal standardisation but to name the problem, fix terminology, distinguish GIDP from adjacent layers, enable independent implementations and attract technical criticism. Expected progression:

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
GIDP should not become a protocol layer merely because the abstraction is appealing. A strong validation would run the same core implementation across at least four domains while changing primarily vocabularies and validation rules, keeping Standing Interest, Disclosure Policy, Discovery Projection, candidate retrieval, compatibility, progressive disclosure, authority, consent and Handoff substantially common. If most core logic must be rewritten per market, GIDP is better treated as a design pattern or a family of vertical protocols.


**Status at publication.** Four domains have been run against a single
implementation of the core: a cross-border corporate transaction, an executive
succession between a person and an organisation, a commercial partnership
using the dependency primitives, and a co-investment carrying an interdependent
interest. They share every object, every claim operator and every result value;
what differs between them is the claim vocabulary, which values each Principal
classifies as evaluation-only, and which authority levels each grants. The
reference implementation checks this mechanically rather than asserting it, so
a fifth domain that needed an object of its own would fail the check rather
than pass unnoticed.

This meets the threshold this document set for itself, and it is worth being
precise about what it does not establish. All four were written by the same
author, from the same understanding of the protocol, which is exactly the
circumstance in which a shared blind spot survives. The test that matters is a
domain profile written by someone else.

### F.3 Evaluation criteria
The proposal should be considered successful only if experiments show that: (1) Principals possess economically meaningful conditional interests they do not want to publish; (2) useful candidate retrieval is possible from reduced projections; (3) progressive disclosure preserves materially more privacy than marketplace publication; (4) Agents can evaluate meaningful compatibility without revealing all constraints; (5) the same core primitives work across multiple markets; (6) the protocol reuses rather than duplicates existing transport and negotiation infrastructure; (7) abuse controls prevent trivial Standing Interest harvesting; (8) the discovery layer produces Opportunities that would otherwise be difficult to surface. If these do not hold, GIDP should be narrowed, redesigned or abandoned.

### F.4 Core architectural hypothesis
*A sufficiently general primitive exists for Agents to discover compatibility between private, conditional, unpublished interests of their Principals, and that primitive is distinct enough from capability discovery and negotiation to justify interoperable protocol semantics.* Draft 0.1 is intended to test that hypothesis, not to assume it.

### F.5 Boundary of what this specification standardises
Candidates for open standardisation: Conditional Interest semantics; Standing Interest, Disclosure Policy and Discovery Projection models; session, compatibility, disclosure and consent objects; Opportunity and Handoff representations; authority levels; profile mechanism; threat model; transport bindings; reference SDK; conformance tests. Intentionally outside the standard: ranking and routing algorithms, matching models, trust scores and reputation systems, market-making and liquidity management, cross-market inference, outcome prediction, pricing, operator-specific anti-abuse systems and commercial relationships. This separation permits interoperable infrastructure while leaving room for competing implementations.

## Appendix G — Acknowledgements

This draft was substantially improved by two independent adversarial reviews of the consolidated text, which identified defects in the object model, the result vocabulary and the conformance criteria that the author had not seen. Errors that remain are the author's.

Acknowledgements of external reviewers will be added as comments arrive.
