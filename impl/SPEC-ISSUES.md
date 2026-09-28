# Specification issues found while implementing

Every ambiguity met while writing this implementation is logged here **before**
being resolved in code, per the working rule of the implementation plan. An
implementation that found nothing would mean the implementer stopped reading
carefully.

Each entry states what the specification says, what a reader cannot determine
from it, what this implementation decided, and whether GIDP 0.1 should change.

**Status: twenty of twenty-one were applied to GIDP 0.1 on 23 September 2026**, before the
specification was frozen for publication. S-22 to S-26 were found by the first
external review, on 25 September, and applied the same day — still before
publication, which is why they belong to 0.1 rather than to a later version. The entries are kept because the
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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 17.2 now states that the transitions apply to both Agents' views and that an Agent discharges only the requests it sent.

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Appendix C.1 now reports five dimensions evaluated and three compatible, matching what it narrates — and matching what `examples/cross_border.py` prints.

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 14.6 now defines both counts, counts each claim key once, excludes `conditionally_compatible` from `compatible_dimensions`, and states the identity `compatible + open_conditions = evaluated`.

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** **The rule changed.** Section 15.2 now requires every claim to have resolved `compatible` or `conditionally_compatible`; `declined`, `unknown`, `requires_disclosure` and `requires_principal_approval` all prevent qualification, and a requester may re-ask a claim to unblock it. `test_declined_result_prevents_qualification` guards it.

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 11.1 now says `endpoint` and `projection_id` SHOULD be unlinkable across providers, with the cross-reference to 24.2.

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 14.4 now says explicitly that an Agent holding no value answers `declined`, and why the vocabulary has no "not applicable".

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

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 14.1 now states that the initiator cannot distinguish a depth-mismatch close from any other `unsupported` close, and that signalling the reason would itself be a disclosure.

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
**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 14.2 now defines `within` as overlap for range-valued private attributes, and notes the inference consequence.


---

## S-09 — The privacy property is per sender, and the specification does not say so

**Found.** 2026-09-23, by the end-to-end scenario test, on its first run.

**Spec.** Sections 9.1 and 10.1 say a `local` attribute "MUST NOT be
transmitted through GIDP". Section 15.4 illustrates a private threshold answered
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

---

## S-12 — Coarsening is presented as an inference control and is not one

**Found.** 2026-09-23, by the comparative harness (`baselines/mitigations.py`),
which was built to test a different claim entirely.

**Spec.** Section 15.4 illustrates a private threshold answered
`conditionally_compatible` without being transmitted. Section 15.5 permits
replacing a truthful answer "in order to limit inference (coarsening,
randomised response within these bounds, privacy budgets)". Section 24.3 lists
"bucketed or randomised responses" among the mitigations against probing.

**The defect.** The default policy — coarsen when the truthful answer would
have been affirmative and the attribute is evaluation-only — maps one
deterministic answer onto another. `compatible` becomes
`conditionally_compatible`; `incompatible` stays `incompatible`. The two
truths still produce two distinguishable answers, so a querent's partition of
the responder's possible values is *identical* to the partition it would have
obtained from a plainly truthful oracle. Measured over an adaptive querent at
budgets of 4, 8, 16 and 64 claims, the two policies leak the same number of
bits in every cell, to the last decimal.

Coarsening does exactly what Section 15.4 was written for: it keeps `80M` off
the wire. It does nothing whatever for Section 15.5's stated purpose. Since
15.5 and 24.3 both present it as an inference control, an implementer who
follows the specification will believe they have a mitigation in place and
will have none.

The sweep also disposes of the two obvious repairs. Coarsening *every* local
answer leaks nothing and qualifies every counterparty, including those that
should have been refused. Declining every local answer leaks nothing and
qualifies none. Randomising half the local answers holds an adversary to
3.04 bits at a budget of 8 where a deterministic policy has already given up
7.94 — and gives up 7.94 itself by a budget of 16, because the adversary
re-asks, while costing 39 points of true-negative rate.

**Decided here.** Nothing in the code changes: the default policy is correct
for what it is for, and the alternatives are worse. The harness, its sweep and
`tests/test_baselines.py` are the record.

**Spec should change.** Yes, and it is the kind of change that matters more
than an object-model fix, because it corrects a claim a reader would otherwise
rely on.

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 15.4 now states
that coarsening protects the value and not the inference, and why. Section
15.5 no longer attributes an inference-limiting purpose to the permitted
replacements, and says that the question is answered in 24.3. Section 24.3 now
states that the only mitigation in GIDP 0.1 which bounds adaptive inference is
a bound on the number of claims, names that bound's known weakness, and points
at the measurements. See `../spec/alternatives.md`.

---

## S-13 — A claim whose operator does not fit the value crashes the responder

**Found.** 2026-09-23, by `tests/test_properties.py` on its first run, at the
first generated example. No hand-written test had produced a claim whose
operator did not match the shape of the private value, because no author
writes one.

**Spec.** Section 14.2 defines the operators and the fields of a claim. It
says nothing about what a responder does when the operator does not fit the
value it holds.

**The defect.** `intersects` against a range raised `TypeError: unhashable
type: 'dict'`; `within` against a label or a list raised `TypeError: '<' not
supported between instances of 'str' and 'int'`. Three lines of generated
input, three uncaught exceptions in the evaluation core.

It is worse than an ordinary crash. The responder's behaviour becomes a
function of the *shape* of its own private value — a querent that sends
`within` and receives an error, rather than an answer, has learned that the
attribute is not numeric, which is information the Disclosure Policy never
authorised. And a responder that can be made to fail by a well-formed message
with an ill-fitting operator can be made to fail by anyone: the same message
is a denial of service.

**Decided here.** `_apply` returns "cannot determine" on any shape mismatch,
which the vocabulary already renders as `unknown`. The fix is four lines; the
reason it matters is the paragraph above.

**Spec should change.** Yes. An implementer's first instinct is to reject a
mismatched claim as malformed, and that instinct produces both failures.

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 14.2 now requires
`unknown` on a shape mismatch, forbids treating it as a malformed message,
forbids failing, and states both reasons.

---

## S-14 — The A2A binding sketch does not match the mechanism it sketches

**Found.** 2026-09-23, by writing the binding against the published
Agent2Agent 1.0 specification instead of from memory.

**Spec.** Section 22.2 showed an Agent Card fragment with
`capabilities.extensions` entries carrying `uri`, `description` and
`required`, citing "specification §4.6".

**Three errors and an omission.** `AgentCapabilities` is §4.4.3 and
`AgentExtension` is §4.4.4, not §4.6. `AgentExtension` has a fourth field,
`params`, which is where a GIDP implementation would naturally declare the
profiles it supports. And the sketch said nothing about **activation**: in
A2A, declaring an extension in the Agent Card does not turn it on. A client
sends the `A2A-Extensions` header listing the URIs it intends to activate and
the responder echoes the subset it actually activated. An extension that was
not echoed is not in force.

The omission is the substantive one. Activation is the point at which a GIDP
exchange can be refused before any GIDP object exists, and therefore before
any Disclosure Policy has been consulted — which is the earliest and cheapest
refusal available to a responder, and Section 22.2 did not tell an
implementer it was there.

**The question the sketch did not raise.** Layered on A2A there are two
negotiations. A2A activation asks *do you speak GIDP*; Section 14.1's
`features` ask *which optional GIDP features are in force*. Neither implies
the other, and the obvious implementation error is to assume a feature is
available because the extension was activated. `tests/test_a2a_binding.py`
holds a case where a peer activates the extension and supports no optional
feature at all.

**Decided here.** `gidp/bindings/a2a.py` implements declaration, the
activation round trip and carriage in `metadata` under URI-prefixed keys,
with round-trip tests over every object a real session puts on the wire.
Writing it also showed that `REQUEST_TYPES`, `RESPONSE_TYPES` and
`ONE_WAY_TYPES` do not between them enumerate every transmitted object —
`SessionClose` and `DiscoveryProjection` are in none of them — so a binding
that trusts those tuples silently cannot carry two object types.

**Spec should change.** Yes, editorially but concretely: a sketch that cites
the wrong section and omits the handshake is worse than no sketch, because a
reader will copy it.

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 22.2 now cites
§4.4.3 and §4.4.4, includes `params`, describes the activation round trip and
what a non-echo means, states the `metadata` carriage convention and why a
GIDP object does not belong in a Part, warns that the two negotiations are
independent, and notes that an unallocated URI is an interoperability
question rather than a detail.

---

## S-15 — `requires_principal_approval` is normative and unreachable

**Found.** 2026-09-23, by a coverage pass over the closed vocabularies: of 89
values, twenty are referenced nowhere outside their own definition.

**Spec.** Section 15.1 lists `requires_principal_approval` as a compatibility
result meaning "answering requires a per-instance Principal decision that is
pending", and Section 15.2 makes it one of the results that prevent a session
from qualifying.

**The defect.** Nothing can produce it. Gates — including
`principal_approval` — are properties of the Disclosure Policy and govern
disclosure and consent, and Section 15.4 is emphatic that answering a claim is
not disclosing. So within GIDP 0.1's own model there is no construct under
which answering a claim requires a Principal decision, the result is
unreachable by construction, and Section 15.2's rule about it is vacuous.
Three enumerations carry a "pending principal approval" token; two are
reachable and this one is not.

**Decided here.** Removed from the result vocabulary. A closed vocabulary that
nothing can produce is not a harmless spare part: it is an interoperability
obligation on every implementer, for a case none of them can reach.

**Spec should change.** Yes. Removing it also makes Section 15.2 say something.

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Removed from the Section
15.1 table and from the Section 15.2 blocking list. If a deployment shows that
a Principal should approve *answers* and not only disclosures, a future
version can reintroduce it with the construct that produces it — noting that
such a rule must remain simulatable in the sense of Section 24.3, since a
decision keyed to the responder's own values is a channel.

---

## S-16 — An enumeration for outcomes the specification says it does not define

**Found.** 2026-09-23, same coverage pass. All five members unused.

**Spec.** Section 15.3 says operational outcomes — `unsupported`,
`unauthorized`, `expired`, `rate_limited`, `temporarily_unavailable` — "belong
to the transport binding, not to the GIDP object set: a binding conveys them
through its own error mechanism, and GIDP defines no object for them."

**The defect.** The implementation shipped a closed `OperationalOutcome`
enumeration anyway, contradicting the sentence it was implementing. Nothing
used it, which is what a vocabulary looks like when the specification was
right and the code disagreed.

**Decided here.** Removed. The tokens stay in Section 15.3's prose, where they
name what a binding conveys.

**Spec should change.** Only to close the door: Section 15.3 now adds that GIDP
defines no enumeration for them either, so that the next implementer does not
repeat this.

**Resolution — applied to GIDP 0.1 on 2026-09-23.**

---

## S-17 — A gated consent could be asked for and never answered

**Found.** 2026-09-23, by the coverage tool: `ConsentStatus.DECLINED` and
`IdentityStatus.GRANTED` were reached by nothing, which turned out not to be a
documentation gap.

**Spec.** Section 14 requires every request-type object to be answered by
exactly one terminal response, with a provisional response explicitly not
discharging the request. Section 17.2's table has both branches:
`CONSENT_PENDING` goes to `CONSENTED` on a grant and back to `QUALIFIED` on a
refusal.

**The defect, in the implementation.** The Agent could emit
`pending_principal_approval` and had no method by which the Principal's
answer ever arrived. A gated consent therefore stayed provisional for the life
of the session, the request was never discharged, and the refusal branch of
17.2 was unreachable. The `principal_approval` gate — the mechanism the
specification offers for the most sensitive attributes — could ask a human a
question and could not hear the reply. The same held for a gated disclosure.

That no test noticed is the interesting part. The conformance suite checked
that a provisional response does not discharge a request, which passed, and
nothing checked that anything ever does.

**Decided here.** `Agent.principal_answers_consent` and
`Agent.principal_answers_disclosure` emit the terminal response on either
branch, with a refusal carrying no scope and a refused disclosure being
`declined` like any other (Section 14.4, so a refusal by the Principal is
indistinguishable from a refusal by the policy).

**Spec should change.** Marginally, and in one place only: Section 14.5 should
say that the Principal's decision arrives as the terminal response to the
original request, because an implementer reading 14.5 alone will build what
this implementation built.

**Resolution — applied to GIDP 0.1 on 2026-09-23.**

---

## S-18 — `retention` was advice wearing the word "limit"

**Found.** 2026-09-23, by instructing a lead that had been listed as
promising and left uninvestigated: XACML's obligation model.

**Spec.** Section 10.7 said a disclosure request "SHOULD state retention
expectations" and that purpose restrictions enforced by the recipient are
future work. Section 25.4 said "recipients SHOULD honour them."

**The defect.** Two SHOULDs facing each other. A requester may state
`session_only` and keep the value for ever without breaching anything, and a
discloser reading the field has no more assurance than if the field were
absent. The field travels on the wire, appears in the object model, and
carries no obligation — which is a worse position than not defining it,
because a Principal shown "retention: session_only" by an implementation will
reasonably believe something enforces it.

XACML made this distinction twenty years ago and resolved it the only way a
protocol can. An *obligation* is an operation the enforcement point must carry
out; *advice* may be safely ignored; and a conforming enforcement point must
**deny access outright** when it cannot discharge an obligation attached to a
permit. The lever is not enforcement, which no policy language has — it is
that failing to discharge makes the implementation non-conformant rather than
merely disappointing.

**Decided here.** An Agent declares the retention modes it can discharge and
refuses to *state* one outside that set, defaulting to `session_only` for an
implementation that keeps a session in memory and nothing after it. An Agent
that can discharge none omits the field, leaving the responder free to decline,
which is the safe outcome.

**Spec should change.** Yes. A limit nothing turns on should not be called a
limit.

**Resolution — applied to GIDP 0.1 on 2026-09-23.** Section 10.7 now forbids
stating a retention the requester cannot discharge and requires omission
instead; Section 25.4's "recipients SHOULD honour them" becomes a MUST for a
recipient that stated one. The specification also says plainly that GIDP cannot
verify discharge and does not pretend to.

---

## S-19 — `approval_required` authority was obeyed for consent and ignored for disclosure

**Found.** 2026-09-24, while testing whether `AuthorityValue.approval_required`
and `Gate.principal_approval` were redundant. They are not — they are
different axes — but the implementation consulted only one of them on the
path that matters.

**Spec.** Section 16.2: "Where a level is `approval_required`, the
corresponding `ConsentResponse` or `DisclosureResponse` MUST be
`pending_principal_approval`." Section 10.6 adds that authority states whether
an Agent may perform a *category* of action while the Disclosure Policy states
what may be disclosed *per attribute*, and that a disclosure happens only if
both permit.

**The defect.** `handle_disclosure_request` checked `DISCLOSE` only for
`false`, then deferred entirely to the attribute's gate. A Principal who set
`DISCLOSE: approval_required` — "ask me before disclosing anything" — was
obeyed for attributes that happened to carry `principal_approval` and silently
ignored for every attribute that carried no gate of its own. The consent path
had it right; the disclosure path did not. The reference implementation was
therefore violating a MUST of the section it implements, on the axis a
Principal is most likely to care about.

The two mechanisms look redundant, which is probably why this survived: both
say "ask the human". They are not. Authority is per category of action and
belongs to the delegation; the gate is per attribute and belongs to the
policy. Either alone leaves a case uncovered, and an implementer who reads
them as alternatives will implement one.

**Decided here.** `approval_required` on `DISCLOSE` returns
`pending_principal_approval` regardless of the attribute's gate, unless the
Principal has pre-approved that attribute.

**Spec should change.** No — the specification was already correct and
explicit. This is an implementation defect, recorded because the register
should show what the code got wrong as well as what the text did, and because
the near-redundancy that produced it is worth naming for the next implementer.

**Resolution — applied to the reference implementation on 2026-09-24**, with a
conformance test and a mutation that fails without it.

---

## S-20 — A required field the specification never asked for

**Found.** 2026-09-24, by Flo, in one sentence: if `interest_class` does
nothing, why keep it? The right answer turned out not to be the one I was
preparing.

**Spec.** Section 8 recognises four classes of Conditional Interest and says
they "differ in what is hidden, not in protocol mechanics", requiring a
conforming implementation to be able to *represent* all four. Section 23.2's
first criterion repeats that, adding that the class is never transmitted "so
this criterion is verified by local inspection".

**The defect, and it is the implementation's.** The specification never
defines a field. It asks that four *situations* be expressible — which they
are, through the Disclosure Policy, since what distinguishes them is which
attribute is local and which is disclosable. The reference implementation
invented a required `interest_class` attribute, made every Principal populate
it, and then read it nowhere. A required field that no behaviour consults is a
tax on every implementer, and two implementations given one will eventually
disagree about what it means.

The conformance criterion was worse. "Verified by local inspection" is not a
criterion; it is a note saying nobody checked. The first version of the test
proved that assigning a Python attribute stores it.

**Decided here.** The field and its enumeration are removed. The four classes
stay in Section 8, as prose, where a taxonomy that guides thinking belongs.

**Spec should change.** Yes, twice. Section 8 now says plainly that no field
carries the classification and why. Criterion 1 is now executable: express the
four situations, run a session for each, and check that they differ only in
their Disclosure Policies while producing the same sequence of protocol
objects — which is also the criterion that carries the horizontality claim of
Appendix F.2, and which had been resting on inspection.

**Resolution — applied to GIDP 0.1 on 2026-09-24.**

---

## S-21 — Two values at different levels of one hierarchy resolve `incompatible`

**Found.** 2026-09-24, on the first end-to-end run of the demo branch, by the
part of the chain no unit test covers: two participants authored separately.

**Spec.** Section 14.2 defines `intersects` as set intersection. Section 21
lets a profile define attribute vocabularies.

**The defect.** A claim asking `geography intersects ["germany"]`, answered by
a responder holding `["munich"]`, resolves `incompatible`. That is truthful —
the sets are disjoint — and wrong, since both parties mean the same place. The
result is a **false negative asserted as a certainty**, and Section 15.2 makes
it block qualification, so a session between two compatible Principals ends
because they named one thing at two granularities.

`unknown` would have been survivable; `incompatible` is not, and the
difference matters: one invites another claim, the other ends the session.

Every unit test in this suite missed it because every test authors both sides
at once and therefore uses one vocabulary by construction. The four worked
domains have the same blind spot, which is exactly what Appendix F.2 warns its
own threshold cannot remove, and it took two independently written profiles to
show it.

**First answer, and it was wrong.** Section 14.2 was made to require a profile
to fix the level of every attribute. That works and it is brittle: it demands
agreement between parties who have never met, which is what a horizontal
protocol is supposed to avoid, and it fails the moment someone writes a
conforming interest at a different granularity.

The second instinct — put an interpreter at the operator — is worse. An
operator that resolves `munich` against `germany` *inside a session* has to see
the claims, and possibly the values behind them, which reinstates the
confidential intermediary this protocol exists to remove.

**Decided here, and it is smaller than both.** A claim is always resolved by
the party that holds the value, so only that party's own values need placing in
a hierarchy. A Standing Interest may carry, per attribute, a mapping from each
value to the value that contains it; the responder answers `compatible` when an
asked value is anything a held value is part of, `unknown` when the asked value
lies below a held one — a German company has not said which city it is in —
and `incompatible` otherwise. Nothing is negotiated, nothing is shared, the
hierarchy never leaves the Standing Interest, and a responder that declares
none keeps set semantics and the false negative with them.

The rule does not widen disclosure: `compatible` to `europe` says what was
asked and not which city, and `unknown` in place of `incompatible` says
strictly less.

**Spec should change.** Yes, and differently from the first attempt.

**Resolution — applied to GIDP 0.1 on 2026-09-24.** Section 14.2 states the
three-way rule and its asymmetry, notes that the hierarchy is never
transmitted, and contrasts it with Section 12.4: a provider resolves for the
whole index because it sees only projections, while inside a session only the
responder can, because only the responder may see its own value.

---

## S-22 — A consent the session needed could not be asked for

**Found.** 2026-09-25, by the first external review of the specification
(T02), read without the code. Confirmed against the code by a test written
before the fix, which also found a second defect the review had not.

**Spec.** Section 10.2 makes the `consent` gate require a granted
`ConsentResponse`. Section 17.2, which forbids any transition it does not list,
allowed `ConsentRequest` only from `QUALIFIED` or `CONSENTED`.

**The defect.** An attribute classified `session/consent` that qualification
needs is a cycle: it cannot be disclosed without consent, and consent cannot be
asked before qualification. No implementation can resolve that without
inventing a transition.

The test for it found a worse one next to it. `QUALIFIED` + `DisclosureRequest`
led to `DISCLOSURE_PENDING`, whose terminal answer led to `PROBING` —
unconditionally. A qualified session that asked one more question was no
longer qualified, could not qualify again because the Opportunity had already
been produced, and could never reach a `Handoff`. Every worked domain stopped
before asking anything after qualification, so none of them met it.

**Decided.** A disclosure or a consent is a request made *within* a stage of
the session, not a stage of its own: its answer returns the session to the
stage it was asked in. `ConsentRequest` with `action: disclose_attributes` may
be sent from `PROBING`; a grant there opens the gate and leaves the session in
`PROBING`. Every other consent action — identity, contact, handoff — stays
behind qualification, which now enforces Section 5 by an explicit rule rather
than by an absent row. `DisclosureRequest` is permitted from `CONSENTED`.
`granted_if_reciprocal` and `granted_if_verified` stay pending, as Section 14
already said and the table contradicted; the implementation had followed
Section 14.

**Resolution — applied to GIDP 0.1 on 2026-09-25.** Sections 14.5 and 17.2.

---

## S-23 — A required field that the Disclosure Policy forbids

**Found.** 2026-09-25, external review (T03). The test found that it was not
only a contradiction in the text but a live leak in the code.

**Spec.** Section 19.1 classifies the dependency lists like any other
attribute. Section 14.6 required every Agent to put every dependency it holds
in the Opportunity's `contingent_on`.

**The defect.** A dependency classified `evaluation_only` or `never` either
had to be transmitted or the field left incomplete, and the text chose
neither. The implementation chose transmission, silently: the default class of
an unlisted attribute is `evaluation_only`, and `contingent_on` copied
`conditional_on` verbatim, so **by default a private dependency went on the
wire**.

Two further gaps surfaced while fixing it. The implementation could not express
`never` at all — every local attribute was evaluation-only. And Section 14.6
required a `Handoff` to carry the contingency forward while Section 14.7 gave
the Handoff no field to carry it in.

**Decided.** A required field does not outrank the policy. A learned
dependency travels as named. A held one travels by name only if the policy
permits `conditional_on` at the session's depth when the Opportunity is built;
otherwise the single token `undisclosed` says the Opportunity is contingent
without saying on what — a derived result, which is what `evaluation_only`
permits. A `never` dependency leaves no trace, because a flag that exists only
because of it is a result produced from it. A claim on a `never` attribute is
declined. The Handoff carries `contingent_on` under the same rule.

**Resolution — applied to GIDP 0.1 on 2026-09-25.** Sections 10.3, 14.6, 14.7.

---

## S-24 — A result named its dimension, not its question

**Found.** 2026-09-25, external review (T04). The tests showed it qualifying
sessions it should have closed.

**Spec.** Section 14.2 identified a claim by its `key`, and Section 15.2 said
results are "keyed by claim key and the most recent answer stands".

**The defect.** A key is a dimension; a claim is a proposition. Asked whether
a value lay in two different ranges, the responder answered `incompatible`
then `compatible`, and the second overwrote the first: the session
**qualified** on a dimension that had failed. The same overwrite ran across
directions — a proposition one side declined was erased by the other side's
compatible answer on the same key — and within one request, where two claims
on one key collapsed into one entry.

**Decided.** Every claim carries a `claim_id`, and a result belongs to the
proposition it answers, identified by that id and the direction. Asking again
adds a proposition; replacing one takes an explicit `supersedes` naming claims
of the same sender. A proposition answered `incompatible` cannot be withdrawn:
a known contradiction closes the session, and a requester allowed to withdraw
it and ask a neighbouring value would have bisection — the attack of Section
24.3 — as a supported feature. The counts of Section 14.6 are per dimension
over the standing propositions, which keeps their identity intact.

The JSON Schema publishes `claim_id` as required even though the in-process
constructor lets the Agent fill it, because the schema describes the wire.

**Resolution — applied to GIDP 0.1 on 2026-09-25.** Sections 14.2, 14.3,
14.6, 15.2.

---

## S-25 — A qualifying answer could stand over a ruled-out claim

**Found.** 2026-09-25, external review (T01).

**Spec.** Section 15.5 let a responder replace *either* truthful answer with
`conditionally_compatible`. Section 15.2 counts `conditionally_compatible` as
qualifying.

**The defect.** A responder whose own evaluation said `incompatible` could
answer `conditionally_compatible`, and with one genuinely compatible dimension
elsewhere the session reached an Opportunity on a dimension the responder knew
had failed. The default Agent never did this — it coarsened only true answers —
but the library function every profile would call allowed it, and so did the
text. Separately, nothing said what an Opportunity asserts, and the obvious
reading — that the Principals are compatible — is false even without coarsening:
dimension-by-dimension claims cannot see that two sides agree on every
dimension and on no whole configuration.

**Decided.** Coarsening is asymmetric: `compatible` may become
`conditionally_compatible`, `unknown` or `declined`; `incompatible` may become
only `unknown` or `declined`. And Section 14.6 now states what an Opportunity
asserts — no standing proposition met a contradiction its responder knew of —
and what it does not, with the counterexample, and tells a profile that needs
joint satisfiability to ask for the combination as one claim.

**Resolution — applied to GIDP 0.1 on 2026-09-25.** Sections 14.6, 15.2, 15.5.

---

## S-26 — Residues of resolved issues, and other editorial faults

**Found.** 2026-09-25, external review (section 4 of its report).

Two of these are faults in this file's own process rather than in the
specification. S-15 removed `requires_principal_approval` from the result
vocabulary and was marked resolved while Section 14 still listed it as a
provisional response. S-16 removed the enumeration of operational outcomes and
was marked resolved while Section 26 still listed them among the closed
vocabularies to register. Closing an issue now means searching the whole
document for what it removed, not editing the paragraph it was found in.

The others, corrected on the same day: the fallback of Section 15.3 assumed a
close reason for every operational outcome, and there are fewer; Section 14.8
gave an empty `features` intersection as a reason to refuse although the
bilateral core needs no feature; Section 22.2 justified carrying GIDP objects
in A2A `metadata` by claiming a Part is for humans, which is false — A2A Parts
carry structured data — and the real reason is Section 6.10; Section 2
referred to an Appendix H that does not exist; Section 20's reference to an
`evidence_ref` named a field no section defines; Section 12 required a
provider to stop returning a withdrawn projection both on acceptance and within
a published latency; the preamble described the reference implementation as
future; the example Standing Interest carried a `class` field Section 8 says
does not exist; and the example Opportunity omitted the required
`contingent_on`. Also corrected: two sentences broken by the rename to GIDP,
and "those four" after a list of three.

**Resolution — applied to GIDP 0.1 on 2026-09-25.**


---

## S-27 to S-32 — second external review (28 September 2026)

The same reviewer read the corrected text. It confirmed the earlier
corrections and found the following, all applied to GIDP 0.1 before
publication.

**S-27 — Section 3 still promised joint satisfiability.** The terminology
entry defined an Opportunity as a configuration "found potentially jointly
satisfiable", which Section 14.6 now explicitly does not assert. The entry
now points at Section 14.6 instead of contradicting it.

**S-28 — an authority of `false` fell into the pending branch.** Section
14.5 said: granted without a human decision only if the level is `true` and
no gate applies, *otherwise* `pending_principal_approval`. For a level of
`false` that told the counterparty to wait for a decision nobody would be
asked to make, and contradicted Section 18, which already required a
`DISCLOSE` level of `false` to answer `declined`. A refused authority is now
a refusal on the consent path too, in the specification and in
`Agent.handle_consent_request`.

**S-29 — one absolute sentence survived the Section 24.3 correction.**
Section 15.3 still said `declined` "carries no information whatever";
Section 24.3 had just spent a paragraph qualifying exactly that claim. The
sentence now says what is true: constructed to convey nothing about
compatibility to the counterparty, not information-free to every observer.

**S-30 — the Handoff example omitted `contingent_on`.** The field had been
made required (S-25) and the example not updated.

**S-31 — the state table lacked `CompatibilityResponse` from `QUALIFIED`,
and the fate of an emitted Opportunity was undecided.** The reference
implementation already accepted the response (its `COMPATIBILITY` event
covers both directions); the table now says so. The open question the
reviewer posed — what becomes of an Opportunity when a later result is
non-qualifying — is now decided: the Opportunity represents the evaluation
at the moment of the transition, qualification is reached at most once, a
later `incompatible` closes the session and any other result changes
nothing; re-evaluation is a new session, and the disclosure budget, kept per
Standing Interest, carries over.

**S-32 — the initiator could not know the responder's contingencies.** The
Opportunity is emitted by the initiator from its own session view; a
dependency held by the responder under `evaluation_only` was invisible to
it, so the responder received an Opportunity that misstated its own
evaluation — the confidentiality of `contingent_on` (S-25) was fixed, its
bilateral construction was not. `CompatibilityResponse` now carries an
OPTIONAL `contingent_on` under exactly the rule of Section 14.6, the
responder states its communicable contingencies there, and the initiator
merges them.

Also added on the same date, from the review's robustness proposals: a
normative decision order for authorisation checks (new Section 16.3, with
the two rules easiest to get wrong: an authenticated peer is not a network
member, and a late approval is re-checked against the current policy), and
the persistence requirements for the disclosure budget (Section 24.3: no
reset by new session, restart or replica; no double-spend under
concurrency). The review's structural proposals — separating session phase
from pending requests and granted consents, a bilaterally accepted summary
before emission, a fully typed first profile, an implementation-independent
conformance corpus — are recorded in `spec/open-problems.md` for 0.2.

**Resolution — applied to GIDP 0.1 on 2026-09-28.**


---

## S-33 to S-46 — third review round (28 September 2026): the reviewer's fourth pass, and a first fresh reading

Two reports: the reviewer of S-22 to S-32 read the corrected text a third
time and found four raccords; a second reviewer, reading the specification
for the first time, found the rest. All applied to GIDP 0.1 before
publication.

**S-33 — identity could ride `disclose_attributes` (fresh reviewer; the
most serious of the batch).** `reveal_identity` was forbidden before
qualification, but `disclose_attributes` was permitted before it, gated on
`DISCLOSE`, and nothing excluded `principal_identity` from its scope; a
direct `DisclosureRequest` on an identity attribute classified plainly
`session` had the same reading. Section 10.6 now attaches the identity
rules to the nature of the data: an identity attribute travels only under a
`reveal_identity` consent (INTRODUCE, post-qualification), MUST NOT appear
in any other consent scope, and a `DisclosureRequest` naming it without
that consent is `declined`. Enforced in `Agent.handle_consent_request` and
`Agent.handle_disclosure_request`, with the no-gate case tested.

**S-34 — a qualifying result arriving while a request is pending.**
Probing continues during `DISCLOSURE_PENDING`/`CONSENT_PENDING`, but the
transition to `QUALIFIED` was defined only from `PROBING`, so the case had
three defensible readings. Decided: the status neither fires nor lapses
while a request is pending; it fires on the return to `PROBING`, where the
implementation MUST apply it before any further message. `Session.qualify`
defers accordingly.

**S-35 to S-37 — raccords on our own recent fixes.** Section 15.2's
definition of `potentially_compatible` now says its conditions are
conditions of entry and the status is kept thereafter (the freeze of S-31
had not been propagated into the definition); Section 16.3 gains the depth
row (Section 14.1's `declined` could otherwise fall into the approval
branch) and a scope paragraph saying the table governs transmission, not
local evaluation — applied literally it would have refused the very
evaluation `evaluation_only` permits; and Section 14's "MAY close" on a
disagreeing Opportunity recipient is harmonised with Section 14.6's "MUST
close" on a mismatched one.

**S-38 — `within` renamed `overlaps`.** The operator's semantics were
overlap, stated in its own definition; its name suggested containment. An
operator rename is free before publication and breaking after it. Renamed
in the specification, the vocabulary, the schemas and every example.

**S-39 to S-46 — propagation and honesty.** The A2A binding no longer
claims `metadata` keeps objects "out of the prompt by construction" — the
container frames, the implementation enforces. The Section 14.6 example
showed an identity granted at the instant of qualification, before it
could be requested. Section 14.6 now carries the fresh reviewer's
within-one-dimension example — ceiling 80, floor 90, both `compatible`
with 50–100 both ways, no common price — and requires (MUST, was MAY) a
profile to state the minimum claims before its Opportunities carry
operational meaning; absent that, an Opportunity is a screening result.
Conformance criterion 1's broken sentence is rewritten (invariants across
the four situations, not identical traces; the interdependent case is
conditional on the optional feature), and criterion 3 adds the budget
ledger to its inputs, since a shared budget and randomised refusals make a
lone session's replay underdetermined. Section 26's closure now names its
two profile-extensible vocabularies instead of contradicting them.
Appendix A's `class` field, which Section 8 spends a paragraph refusing to
define, is removed. C.1's Opportunity proposed a minority investment
nobody had authorised; A's mandate now includes it. Three "MUST NOT infer"
are rephrased to bind what a result means in the protocol rather than
legislate statistics. And three sentences are softened to what is true:
the introduction's "the only way to be found is to announce"
(confidential islands exist — Section 1.1 describes them), the claim that
neighbouring protocols "all assume" capability discovery (PAP's mandates
carry search and disclosure scopes), and "[RANI2026] solves the passive
case" (it treats one, under its own model).

**Also added:** `projection_ref` (OPTIONAL) on `SessionOpen` — the routing
key without which an endpoint representing several Standing Interests
cannot know which interest a session is about; and the negotiation
boundary stated operationally in Section 14.3: a claim is a test of a
hypothesis, not a position, and a recipient MUST NOT treat it, or its
pattern, as an offer or an indication of availability.

Found while testing: one conformance test asserted a private value's
digits were absent from a serialisation that included `expires_at`, so it
failed whenever the clock's microseconds contained "80" — the source of
two phantom failures. It now excludes the timestamp.

**Resolution — applied to GIDP 0.1 on 2026-09-28.**
