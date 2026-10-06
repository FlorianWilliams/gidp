# Changelog — Graduated Interest Disclosure

This file records versions of the **specification**. It is not the git log:
git records every edit; this file records the versions a reader may cite.

## Versioning rules

**Document version** (`0.1`, `0.1.1`, `0.2`…) and **wire version token**
(`gidp/0.1`, carried by every transmitted object) are separate numbers and
move at different speeds.

- The **wire token** changes only when the object model changes in a way that
  breaks interoperability. All `0.1.x` revisions of the document share the
  token `gidp/0.1`: an implementer must not have to redeploy for an
  editorial correction.
- A **patch release** (`0.1.1`) carries corrections that change no conforming
  implementation's behaviour, and says so explicitly.
- A **minor release** (`0.2`) carries behaviour changes, batched. They are not
  shipped one at a time: an implementer cannot follow a moving target, and a
  specification that changes every fortnight loses the credibility it is
  published to earn.
- `impl/SPEC-ISSUES.md` is the errata pipeline between releases.

Each published version keeps a stable URL of the form `/spec/0.1/` that never
changes, and is tagged in git (`v0.1`). A citation needs an immutable address,
which a commit that can be rewritten does not provide. If the draft is ever
submitted as an Internet-Draft, the IETF datatracker archives each revision
(`-00`, `-01`…) immutably and supplies this for free.

The reference implementation carries its own version and declares which
specification version it implements; the two do not advance together.

## 0.1 — 5 October 2026

First public draft, under the name *Graduated Interest Disclosure*.

Consolidates three earlier internal drafts written under the working name
*Conditional Interest Discovery*, abandoned before publication because its
contraction collides with IPFS content identifiers inside the same layer, and incorporates two independent adversarial reviews of the consolidated
text, and sixty-four issues (`impl/SPEC-ISSUES.md`, S-01 to S-64): twenty-one
found while writing the reference implementation; five found by the first
external review of the specification, read without the code; six by the
second, which re-read the corrected text; fourteen by the third round, which
comprised the same reviewer's third pass and a second reviewer's first, fresh
reading; two by the first reviewer's fourth pass; seven by the second
reviewer's second reading; and nine by a third fresh reading. Every review before publication, adversarial or external, was carried out by a large language model given the text without its history; human review begins with publication.

Three of the first external review's findings were normative contradictions that
no implementation could satisfy without inventing behaviour: a consent the
session needed could not be asked for (S-22), a required field forced the
transmission of a dependency the Disclosure Policy protected (S-23), and a
result named its dimension rather than its question, which let a session
qualify on a dimension that had failed (S-24). Writing a test for each
before fixing it showed two of them to be live defects of the reference
implementation, not only of the text. They were corrected in both before
publication, which is why they belong to 0.1 and not to a 0.2.

The second review confirmed the corrections and found what they had missed.
Most of it was propagation: sentences elsewhere in the document still
asserting what a corrected section no longer asserts (S-27, S-29, S-30). It
also found a consent path that told a counterparty to wait on an authority
that had been refused (S-28), a missing line in the state table together with
the undecided fate of an emitted Opportunity, now decided as frozen at
qualification (S-31), and the one real design gap of the batch: the
initiator emits the Opportunity but cannot know the responder's protected
contingencies, so `CompatibilityResponse` now carries them in communicable
form and the initiator merges them (S-32). The same date added the decision
order for authorisation checks (Section 16.3) and the persistence
requirements for the disclosure budget (Section 24.3). The review's
structural proposals are recorded in `open-problems.md` for 0.2.

The third round's sharpest findings came from fresh eyes: an identity
attribute could ride `disclose_attributes` before qualification, so the
identity rules now attach to the data rather than the message (S-33); a
qualifying result arriving while a request was pending had three
defensible readings, now one (S-34); the operator `within` tested overlap
and said containment, renamed `overlaps` while a rename is still free
(S-38); and the buyer-at-80 / seller-at-90 example now sits in Section
14.6, with profile minimum coverage a MUST, because a qualification built
from overlap claims is a screen and the document should not let a reader
believe otherwise. `SessionOpen` gains an OPTIONAL `projection_ref`. The
rest is propagation and corrections of overclaiming; the full account is in
SPEC-ISSUES.

The first reviewer's fourth pass closed the round with two consistency fixes (S-47, S-48): a deferred
qualification is recomputed at the return to PROBING rather than
remembered from mid-wait (fixing this surfaced that the status-kept
rule of S-35 had existed only in prose), and a claim on an identity
attribute is declined without reveal_identity consent, closing a third
route to identity before qualification after the two S-33 closed. The reviewer then judged the version fit to
stabilise and submit to implementers.

The fresh reviewer's second reading (S-49 to S-55) withdrew its earlier
criticisms and asked for consistency between the new rules: a profile's
minimum claims now enter Section 15.2's entry conditions directly; the
pending-open rule is narrowed to a not-yet-qualified,
incompatibility-free session; PROBE under approval_required waits
locally and answers terminally, with no provisional answer;
"reciprocal" is defined as sequential exchange, initiator first, expiry
as explicit failure; a profile may type a general value as an accepted
set; projection routing is closed end to end; and the
all-conditionally-compatible policy of Section 24.3 is named as a
non-conforming comparator. Both reviewers now converge on the same two
next steps: the editorial pass, and implementers.

The editorial pass followed as a set of targeted edits: the
histories of corrected failures, the naming history, the borrowed
XACML distinction and the measured-curve narratives moved to a new
`rationale.md`, leaving one-line traces where the argument depended
on the reasoning; the specification's experimental figures now cite
`alternatives.md` and their own populations; the one full statement of
the capability-discovery distinction is Appendix D. The three-document
shape the reviewers asked for (specification, design rationale,
experimental record) now exists as GIDP-0.1.md, rationale.md and
alternatives.md. Deeper shortening is held over to the 0.2
edition: with the substance frozen, each further compression is pure
risk against no deadline.

A third fresh reading re-derived much of the deferred programme (the
expected behaviour of a good reader meeting a document that states its
own limits, and the reason Section 7 now points such a reader at
open-problems.md) and contributed three real changes (S-56 to S-64):
qualification is bilateral over the wire, the initiator emitting only
when the responder's reported status qualifies, which is the local
confirmation three reviewers independently asked for at zero new
objects; a session is explicitly about one candidate configuration,
which is what an incompatible refutes; and a Handoff requires a granted
consent naming its target, CONSENTED alone establishing nothing about
that action. It also added six local consistency fixes, including the dangling reference
and the too-broad pending rule that this week's own fixes had left.

One of the twenty-one issues found while writing the reference implementation, S-12, is recorded separately here because it changes what
the document claims and leaves what it specifies unchanged. A comparative harness built to
test the protocol against existing mechanisms showed that the coarsening
illustrated in Section 15.4 provides no protection against inference: it
relabels one deterministic answer as another, and an adaptive querent's
partition of the responder's possible values is unchanged. Sections 15.4, 15.5
and 24.3 were corrected before publication, and Section 24.3 now names the two
controls that do bound adaptive inference: a granularity lattice, which caps
the resolution of any answer, and an information budget, which refuses a claim
whose worst-case answer would cost more bits than the budget allows. The error
was to count claims: an honest question over a wide band costs a
fraction of a bit, while a bisecting question costs a full bit by
construction, so a budget denominated in questions cannot separate the two.
The measurements are in `spec/alternatives.md`.

Everything before the first publication is absorbed into this version: there
is no history to preserve until a reader can cite one. From the day 0.1 is
published, the rules above apply.
