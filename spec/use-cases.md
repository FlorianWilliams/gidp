# CID — Illustrative Use Cases

**Status:** informative companion to *CID Draft 0.1*. Non-normative.
**Purpose:** demonstrate that the same protocol primitives apply across materially different domains (the horizontal-layer hypothesis, CID 0.1 Appendix F.2), and give implementers concrete test scenarios.
**Scope note:** this catalogue is deliberately illustrative, not exhaustive. It shows one or two generic cases per domain and does not analyse market attractiveness, wedges or business models.

Each case follows the same template so that the invariant structure is visible:

- **Principal A / Principal B** — who is represented (type only, never identity).
- **Hidden interest** — what neither side wants to publish.
- **Private conditions** — attributes of surface `local` (`evaluation_only` or `never`, CID 0.1 Section 10).
- **Why public discovery fails** — the circularity that CID addresses.
- **CID interaction** — projection → retrieval → compatibility → disclosure → consent → handoff.
- **Resulting Opportunity** — what is handed off, and what was never revealed.

The four classes of Conditional Interest (CID 0.1 Section 8) are abbreviated: **PCD** passive conditional demand, **CAD** confidential active demand, **PCS** private conditional supply, **ICI** interdependent conditional interest.

---

## 1. Passive executive mobility (person ↔ organisation)

**Classes:** A = PCD, B = CAD.
**Principal A:** a senior executive, not looking. **Principal B:** a board considering succession without a public search.
**Hidden interest:** A would consider a CEO role; B would consider replacing its CEO.
**Private conditions:** A — minimum equity, excluded companies, earliest start date. B — timing, board context, current CEO's awareness.
**Why public discovery fails:** A cannot post "open to CEO roles" without signalling to their current employer; B cannot post "CEO search" without destabilising the company.
**CID interaction:** both project `executive_role · b2b_software · europe`; the session confirms role, sector, scale band, geography and that each side's private conditions are satisfiable; identities are revealed only after both Principals approve.
**Resulting Opportunity:** an introduction between two parties who never advertised. Neither equity floor nor succession timing was transmitted.

## 2. Off-market M&A, seller side (organisation ↔ organisation)

**Classes:** A = PCS, B = CAD.
**Principal A:** a founder-led company, not for sale. **Principal B:** an acquirer exploring targets discreetly.
**Hidden interest:** A would sell above a private threshold to a strategic buyer with management retained; B is building a position in a segment.
**Private conditions:** A — minimum valuation, acceptable buyer classes, founder transition terms. B — budget ceiling, strategic rationale, excluded competitors.
**Why public discovery fails:** a "for sale" signal damages A with customers, staff and competitors; an "acquiring" signal raises prices and alerts B's competitors.
**CID interaction:** symmetric projections (`strategic_transaction · enterprise_software · europe`) hide direction; claims test valuation *class* and structure overlap; neither reservation value is transmitted.
**Resulting Opportunity:** a structure ("majority sale with founder retention") and a compatible valuation band, handed to advisers. See CID 0.1 Appendix C.1 for the full walk-through.

## 3. Confidential acquisition interest, buyer side

**Classes:** A = CAD, B = PCD.
**Principal A:** a corporation with an undisclosed acquisition thesis. **Principal B:** a company that "would listen".
**Hidden interest:** A's thesis and budget; B's openness.
**Private conditions:** A — target ARR band, maximum valuation, integration constraints. B — minimum price, buyer type.
**Why public discovery fails:** disclosing the thesis reveals strategy to competitors and moves prices.
**CID interaction:** as case 2, initiated from the buyer side; disclosure requests escalate from structure class to ARR band only after `conditionally_compatible` on valuation class.
**Resulting Opportunity:** a shortlist of two or three counterparties for A, none of which learned A's identity or budget before consent.

## 4. Co-investment (person ↔ organisation, interdependent)

**Class:** A = ICI, B = CAD.
**Principal A:** an angel investor. **Principal B:** a startup raising quietly.
**Hidden interest:** A invests only if a qualified institutional lead commits; B does not want the market to know it is raising.
**Private conditions:** A — ticket size, required referral from a trusted connection, sector list. B — valuation, existing commitments.
**Why public discovery fails:** B cannot announce a round; A cannot broadcast "I follow leads".
**CID interaction:** projections `co-investment · ai · france`; compatibility on sector, stage and ticket class; A's `conditional_on: institutional_lead` is an unmet dependency that either resolves in session (B discloses a lead exists, at class `session`) or triggers dependency-driven expansion (CID 0.1 Section 19.2).
**Resulting Opportunity:** a conditional commitment, contingent on the lead, handed to the parties.

## 5. Commercial partnership / licensing (organisation ↔ organisation, enterprise agents)

**Classes:** A = CAD, B = PCS.
**Principal A:** an enterprise whose CRM-resident agent knows deals are being lost for lack of capability X. **Principal B:** a startup that has X and lacks distribution.
**Hidden interest:** A's product gap; B's willingness to white-label.
**Private conditions:** A — commercial thresholds, lost-deal figures, roadmap. B — minimum contract value, exclusivity limits.
**Why public discovery fails:** A will not publish a product weakness; B will not signal it needs a partner.
**CID interaction:** projections expose capability *classes* (`requires: capability X` / `provides: capability X`) without motives; session confirms structure overlap (licensing, white-label) and threshold satisfiability.
**Resulting Opportunity:** a licensing or white-label discussion that neither party would have initiated publicly. Illustrates that participants need not be personal agents: an agent embedded in enterprise software already holds the relevant private state.

## 6. Procurement / supplier switching (organisation ↔ organisation)

**Classes:** A = PCD, B = PCS.
**Principal A:** an organisation under contract until 2028, not running an RFP. **Principal B:** a supplier with unadvertised spare capacity.
**Hidden interest:** A would switch if integration, cost and risk thresholds are met; B would serve a new client above a size threshold.
**Private conditions:** A — current pricing, contract terms, switching-cost ceiling. B — capacity, floor price.
**Why public discovery fails:** an RFP signals dissatisfaction to the incumbent; advertised spare capacity weakens B's pricing.
**CID interaction:** projections `supplier_relationship · category · region`; claims test volume class, integration class and timing window; cost thresholds stay `evaluation_only`.
**Resulting Opportunity:** a qualified pre-RFP conversation.

## 7. Off-market real estate (person ↔ person, or multi-party)

**Classes:** bilateral A = PCS, B = PCD; multi-party adds ICI.
**Principal A:** an owner who is not listing. **Principal B:** a buyer with a Standing Interest ("garden, under 20 minutes from X, below a private budget").
**Hidden interest:** A would sell above a private price; B is not actively searching.
**Private conditions:** A — floor price, timing. B — budget ceiling, must-haves.
**Why public discovery fails:** listing commits A publicly; B's conditions are too idiosyncratic and private for portals.
**CID interaction:** projections `residential_property · region · size band`; price *class* tested in session; identities and address at consent. In the multi-party variant (CID 0.1 Appendix C.4) a buyer's `requires: financing, occupancy` and a bank's and tenant's `provides … conditional_on …` form a potentially satisfiable coalition that no bilateral pair could close.
**Resulting Opportunity:** a private viewing, or a feasible coalition for a commercial asset.

## 8. Private expertise (person ↔ organisation)

**Classes:** A = PCS, B = CAD.
**Principal A:** an expert who does not consult publicly. **Principal B:** a company that needs discreet advice on a sensitive project.
**Hidden interest:** A would advise under narrow conditions (topic, conflict-of-interest limits, rate); B cannot reveal the project.
**Private conditions:** A — excluded clients, rate floor. B — project nature, timeline.
**Why public discovery fails:** expert-network listings expose A's availability; a public request exposes B's project.
**CID interaction:** projections `advisory · domain · language`; conflict-of-interest exclusions evaluated locally against a disclosed counterparty *class* before identity is revealed.
**Resulting Opportunity:** a scoped advisory engagement.

---

## 9. What these cases have in common

Across all eight cases, the protocol mechanics are identical and only the vocabulary changes:

| Invariant | Person cases | Organisation cases |
|---|---|---|
| Standing Interest with `evaluation_only` conditions | equity floor, budget ceiling, excluded employers | reservation value, thresholds, lost-deal data |
| Discovery Projection that hides direction and identity | `executive_role · sector · region` | `strategic_transaction · domain · region` |
| Coarse candidate retrieval | provider, community, network | registry, CRM ecosystem, bank |
| Compatibility on classes, not values | scale band, ticket class | valuation class, volume class |
| Progressive disclosure with stated purpose | timing, start date | structure class, ARR band |
| Consent before identity | `session/principal_approval` gate | `session/principal_approval` gate (per Standing Interest) |
| Handoff | introduction, meeting | advisers, negotiation protocol |

This is the property CID 0.1 Appendix F.2 asks implementers to test: if the same implementation, with swapped vocabularies, runs cases 1, 2, 5 and 7, the horizontal-layer hypothesis survives. If each case needs a different state machine or disclosure model, it does not.

## 10. What a good demonstration must show

A demonstration that "agent A needs a Python developer and agent B knows one" is capability matching and proves nothing about CID. A convincing demonstration has two independently controlled Agents, each holding several Standing Interests, at least one genuinely private constraint on each side, no public listing from which the Opportunity could have been found, staged retrieval, a compatibility result without secret disclosure, an explicit consent step, minimal disclosure, and an Opportunity at the end. See CID 0.1 Section 23.3.
