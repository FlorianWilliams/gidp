# Changelog — Conditional Interest Discovery

This file records versions of the **specification**. It is not the git log:
git records every edit, this records the versions a reader may cite.

## Versioning rules

**Document version** (`0.1`, `0.1.1`, `0.2`…) and **wire version token**
(`cidisc/0.1`, carried by every transmitted object) are separate numbers and
move at different speeds.

- The **wire token** changes only when the object model changes in a way that
  breaks interoperability. All `0.1.x` revisions of the document share the
  token `cidisc/0.1`: an implementer must not have to redeploy for an
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

## 0.1 — unreleased

First public draft, under the name *Conditional Interest Discovery*.

Consolidates three earlier internal drafts written under a former working
name, and incorporates two independent adversarial reviews of the consolidated
text and twelve issues found while writing the reference implementation
(`impl/SPEC-ISSUES.md`).

The last of those, S-12, is worth naming here because it changes what the
document claims rather than what it specifies. A comparative harness built to
test the protocol against existing mechanisms showed that the coarsening
illustrated in Section 15.4 provides no protection against inference: it
relabels one deterministic answer as another, and an adaptive querent's
partition of the responder's possible values is unchanged. Sections 15.4, 15.5
and 24.3 were corrected before publication, and Section 24.3 now states that
the only mitigation in CID 0.1 which bounds adaptive inference is a bound on
the number of claims. The measurements are in `spec/alternatives.md`.

Everything before the first publication is absorbed into this version: there
is no history to preserve until a reader can cite one. From the day 0.1 is
published, the rules above apply.
