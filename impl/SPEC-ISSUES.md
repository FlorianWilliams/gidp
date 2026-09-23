# Specification issues found while implementing

Every ambiguity met while writing this implementation is logged here **before**
being resolved in code, per the working rule of the implementation plan. An
implementation that found nothing would mean the implementer stopped reading
carefully.

Each entry states what the specification says, what a reader cannot determine
from it, what this implementation decided, and whether CID 0.1 should change.

**Status: all eight were applied to CID 0.1 on 23 September 2026**, before the
specification was frozen for publication. The entries are kept because the
record of what an implementation found is worth more than a clean file: it is
the evidence that the draft was tested rather than merely written.

---

## S-01 — Whose state machine advances on whose request?

**Spec.** Section 14 correlates a request with its response through
`request_id` / `request_ref`. Section 17.2 says the state is held "per session
and per direction of request", and gives one transition table.

**Ambiguity.** When B sends a `DisclosureRequest` and A answers, both sides
move from `PROBING` to `DISCLOSURE_PENDING` and back — but only B has a
request to discharge, because the `request_id` is B's. The table does not
distinguish the two roles, so an implementer must invent the distinction.

**Decided here.** `Session.record_disclosure(..., discharge=False)` on the
responder's own view: the state moves, nothing is discharged. Same for consent.

**Spec should change.** Yes, minor: state in 17.2 that a side discharges only
the requests it sent, and that the transitions apply to both views.

**Resolution — applied to CID 0.1 on 2026-09-23.** Section 17.2 now states that the transitions apply to both Agents' views and that an Agent discharges only the requests it sent.

---

## S-02 — Appendix C.1 is internally inconsistent

**Spec.** The worked example narrates five claim resolutions — geography,
market access, transaction structures, valuation class, management condition —
and then reports an Opportunity with `evaluated_dimensions: 12` and
`compatible_dimensions: 10`.

**Ambiguity.** Five narrated, twelve reported. A reader cannot tell whether
"dimension" means "claim" or something coarser.

**Decided here.** `evaluated_dimensions` counts claims resolved in the session;
the example accordingly reports 5 and 3.

**Spec should change.** Yes: either narrate twelve claims or report five.

**Resolution — applied to CID 0.1 on 2026-09-23.** Appendix C.1 now reports five dimensions evaluated and three compatible, matching what it narrates — and matching what `examples/cross_border.py` prints.

---

## S-03 — `evaluated_dimensions` and `compatible_dimensions` are undefined

**Spec.** Section 14.6 lists both as required fields of an Opportunity and
defines neither.

**Ambiguity.** Is a `conditionally_compatible` claim evaluated? Is it
compatible? Two implementations will disagree on the same session, and the
Opportunity is the object both sides are supposed to hold identically.

**Decided here.** `evaluated` counts every claim with a result; `compatible`
counts only `compatible`. `conditionally_compatible` and `unknown` therefore
appear in `open_conditions` and not in `compatible_dimensions`.

**Spec should change.** Yes: define both in 14.6.

**Resolution — applied to CID 0.1 on 2026-09-23.** Section 14.6 now defines both counts, counts each claim key once, excludes `conditionally_compatible` from `compatible_dimensions`, and states the identity `compatible + open_conditions = evaluated`.

---

## S-04 — Is a `declined` claim "resolved" for the purpose of qualifying?

**Spec.** Section 15.2 makes `potentially_compatible` require that "every claim
sent in the session has resolved", that at least one resolved `compatible`, and
that none resolved `incompatible`, `unknown` or `requires_principal_approval`.
`declined` appears in neither list.

**Ambiguity.** A session in which one claim is `compatible` and nine are
`declined` qualifies under the letter of 15.2 and produces an Opportunity. That
is almost certainly not intended: `declined` carries no information at all
(Section 18 insists on exactly that), so treating it as neutral lets an
Opportunity rest on silence.

**Decided here.** Followed the letter: `declined` does not block. Flagged as
the most substantive issue found.

**Spec should change.** Yes, and this one is not cosmetic. Either add
`declined` to the blocking list, or require a minimum proportion of
`compatible` results.

**Resolution — applied to CID 0.1 on 2026-09-23.** **The rule changed.** Section 15.2 now requires every claim to have resolved `compatible` or `conditionally_compatible`; `declined`, `unknown`, `requires_disclosure` and `requires_principal_approval` all prevent qualification, and a requester may re-ask a claim to unblock it. `test_declined_result_prevents_qualification` guards it.

---

## S-05 — A projection must carry an endpoint, which is a stable identifier

**Spec.** Section 11.1 requires `endpoint`. Section 11.5 recommends distinct
projections per provider, and Section 24.2 warns against stable identifiers
because they let an observer correlate projections across providers.

**Ambiguity.** An endpoint that identifies the Agent is exactly the stable
identifier 24.2 warns about; distinct projections per provider achieve nothing
if all of them carry the same endpoint.

**Decided here.** The example uses one endpoint per Agent, which is the naive
reading, and this note records the cost.

**Spec should change.** Yes: 11.1 should say the endpoint SHOULD be
per-projection or otherwise unlinkable across providers, or 24.2 should
acknowledge the exception.

**Resolution — applied to CID 0.1 on 2026-09-23.** Section 11.1 now says `endpoint` and `projection_id` SHOULD be unlinkable across providers, with the cross-reference to 24.2.

---

## S-06 — Absence of a value and refusal to disclose are the same message

**Spec.** Section 14.4: "A `declined` response MUST NOT indicate whether the
attribute exists or what its value is."

**Ambiguity.** An Agent that simply does not hold the attribute must therefore
answer `declined`, which is correct for privacy and means the vocabulary has no
way to say "not applicable". A requester cannot distinguish "refused" from
"nothing there", which is by design but is never stated.

**Decided here.** Absence is reported as `declined`.

**Spec should change.** Editorial only: say so explicitly in 14.4, because
every implementer will hesitate here.

**Resolution — applied to CID 0.1 on 2026-09-23.** Section 14.4 now says explicitly that an Agent holding no value answers `declined`, and why the vocabulary has no "not applicable".

---

## S-07 — A depth mismatch has no message

**Spec.** Section 14.1 makes the session depth the shallower of the two
declared values; a responder for which the resulting depth makes the session
pointless SHOULD close with `reason: unsupported`.

**Ambiguity.** `SHOULD` leaves the other side waiting, and no field carries
"the depth you offered is too shallow for me". The initiator learns nothing and
may retry identically.

**Decided here.** Not exercised; the example uses matching depths.

**Spec should change.** Probably: either make the close a MUST, or accept the
cost and say the initiator cannot distinguish this close from any other.

**Resolution — applied to CID 0.1 on 2026-09-23.** Section 14.1 now states that the initiator cannot distinguish a depth-mismatch close from any other `unsupported` close, and that signalling the reason would itself be a disclosure.

---

## S-08 — Claim operators have no defined semantics for partial knowledge

**Spec.** Section 14.2 defines `within` as "value inside a range or bucket".

**Ambiguity.** When the responder's own value is itself a range — which is the
normal case for a reservation value — "inside" is undefined: overlap,
containment, or midpoint?

**Decided here.** Overlap, because containment would make almost every honest
claim incompatible. The choice is visible in `evaluation._within` and it is the
choice that makes the probing attack of `examples/probing.py` work as cheaply
as it does.

**Spec should change.** Yes: define the comparison for range-valued private
attributes, and note the inference consequence of whichever is chosen.
**Resolution — applied to CID 0.1 on 2026-09-23.** Section 14.2 now defines `within` as overlap for range-valued private attributes, and notes the inference consequence.


---

## S-09 — The privacy property is per sender, and the specification does not say so

**Found.** 2026-09-23, by the end-to-end scenario test, on its first run.

**Spec.** Sections 9.1 and 10.1 say a `local` attribute "MUST NOT be
transmitted through CID". Section 15.4 illustrates a private threshold answered
without being transmitted.

**Ambiguity.** Read naively — and the first version of `tests/test_scenario.py`
read it that way — this says the value never appears on the wire. It cannot
mean that. A claim carries a *candidate* value chosen by the querent: asking
"is `founder_operational` compatible?" necessarily puts that string in the
request. If the responder happens to hold exactly that value, the string is on
the wire, put there by the party that does not hold it.

The guarantee is therefore **per sender**: the holder of a `local` value never
transmits it. A reader who expects the stronger property will believe the
protocol broken the first time they see a claim echo a private value, and a
reviewer looking for a soft target will read it as a leak.

**Decided here.** The test asserts the per-sender property, and a second test
makes the nuance explicit rather than leaving it implicit.

**Spec should change.** Yes, editorial but load-bearing: Section 9.1 should say
that an Agent MUST NOT transmit a `local` attribute *of the Standing Interest
it holds*, and Section 15.4 should note that a querent may name a candidate
value, that a coarsened answer asserts nothing about it, and that the querent
nevertheless learns its guess is not ruled out — which is the inference channel
of Section 24.3, seen from the other end.

---

## S-10 — The dependency primitives are not addressable by a claim

**Found.** 2026-09-23, while implementing the third domain
(`examples/partnership.py`), which is the first to use them.

**Spec.** Section 19.1 defines `provides`, `requires`, `conditional_on` and
`excludes` as four generic relationship lists a Standing Interest MAY carry,
usable bilaterally, and gives the example `requires: capability X` meeting
`provides: capability X`.

**Ambiguity.** It never says *how*. A claim names a key (Section 14.2) and the
responder resolves it against its Standing Interest — but the four primitives
are lists on the Conditional Interest, not entries among its conditions, so a
claim naming `provides` resolves to nothing and comes back `unknown`. The
bilateral use the section describes is unreachable as written. Nor does the
specification say whether the Disclosure Policy applies to them.

It matters more than it looks, because the asymmetry is where the value is.
What an Agent *provides* is ordinarily disclosable — it is what makes it
findable. What it *requires* is the mirror image of what it lacks, and a
capability gap admitted to a prospective partner is admitted to a prospective
competitor. A protocol that cannot express that difference cannot serve the
partnership case at all.

**Decided here.** The four are treated as reserved claim keys, resolved from
the Conditional Interest's lists, and classified by the Disclosure Policy like
any other attribute. In the example `provides` is `session` and `requires` is
`local`, so "do you provide X?" answers `compatible` while "do you require Y?"
answers `conditionally_compatible` — truthful, and the gap stays home.

**Spec should change.** Yes. Section 19.1 should state that the four are
reserved claim keys, that the Disclosure Policy classifies them like any
attribute, and should note the provides/requires asymmetry as the expected
pattern rather than leaving each implementer to discover it.

---

## S-11 — An interdependent interest produces an Opportunity that hides its own contingency

**Found.** 2026-09-23, by the fourth domain (`examples/co_investment.py`), the
first to use an interdependent Conditional Interest.

**Spec.** Section 8.4 defines the interdependent class — *I will consider X if
another party performs or commits to Y* — and says it uses the dependency
primitives of Section 19 and is the entry point to multi-party discovery.
Section 14.6 defines the Opportunity's fields, and Section 15.2 the conditions
under which a session qualifies.

**Ambiguity, and it is not small.** A bilateral session between a follower and
a company can qualify with every claim `compatible` or
`conditionally_compatible` — including the claim that asks the follower
whether it has a `conditional_on` dependency, which answers `compatible`
because it truthfully does. The resulting Opportunity carried no trace of that
dependency: `open_conditions` is defined from claim *results*, and a
dependency that is truthfully confirmed is not an open condition. The
Opportunity therefore read as an assembled round when it was a participation
contingent on a lead investor who did not exist.

Nothing in the specification was violated. That is what makes it serious: two
conforming implementations produce an object that misleads a human, and the
protocol's own state machine is satisfied.

**Decided here.** The Opportunity gains a required field, `contingent_on`,
listing the dependencies the session has not resolved. A non-empty value means
the Opportunity is contingent on something outside it.

**Spec should change.** Yes, and it did: Section 14.6 now requires
`contingent_on`, requires an Agent to populate it with every unresolved
dependency it holds or learns of, requires a Handoff to carry it forward, and
forbids a recipient from treating the Opportunity as complete while it is
non-empty. This is a change to the object model, made before publication and
therefore absorbed into 0.1 (see `../spec/CHANGELOG.md`); after publication it
would have required 0.2.
