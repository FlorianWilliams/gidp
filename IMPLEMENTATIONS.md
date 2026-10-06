# Implementation status

This page records the known implementations of GIDP 0.1, in the spirit of
RFC 7942: what exists, who wrote it, how far it goes, and what it showed
about the specification. It is not an endorsement and not a conformance
certificate. Implementers are invited to add theirs.

## Reference implementation (Python)

Location: `impl/` in this repository. Licence: Apache 2.0.
Author: the specification's author.

Coverage: the bilateral core (every transmitted object, the session state
machine of Section 17.2, the disclosure engine, consents, the Opportunity
and the Handoff), plus discovery projections, the dependency primitives,
an A2A binding, four worked domains, a probing attack and four limit cases. It tests the
specification and has no authority over it: where the two disagree, the
disagreement is logged in `impl/SPEC-ISSUES.md` and the text is fixed.

## Independent clean-room implementation (TypeScript), October 2026

Implementer: a large language model (GPT-6 Astra Max), run in a fresh
session with no access to the reference code, to the companion documents
or to any outside source, under an evaluation protocol designed to make
silent invention visible. The code is not published; this entry reports
the method and the results.

Given: the specification, the exported schemas, the profile manifest
format and one profile instance (co-investment), and a set of thirteen
conformance scenarios stripped of their expected outcomes. Required: an
implementation of the bilateral core configured by that profile; a
journal in which every choice the text did not determine was recorded,
with the passage that failed to determine it, before the code that made
the choice; then a single run of the blind scenarios, with any correction
made after seeing them journalled separately. The journal declares two
exceptions to the rule of recording before coding: one choice was coded
before its entry was written, though before it was used, and one check
was written without an entry and withdrawn after the blind run exposed it.

Results, compared afterwards with the full scenarios:

- The blind run met 77 of 80 expected outcomes, and 79 after its
  journalled corrections. None of the misses was a misreading of the
  specification: two came from defects in the scenarios, one from a
  scenario expecting more than the text requires.
- The journal recorded 21 decisions the text left open. Most are
  legitimate implementer choices (storage, clocks, binding conventions);
  seven are gaps in the specification and are recorded for 0.2 in
  `spec/open-problems.md`.
- Unprompted, the implementer arrived at the qualification rule the 0.2
  session-model draft adopts (the initiator's transition gated on the
  responder's last reported status) without having seen the draft.
- Its audit of its own code also found two defects in this reference
  implementation, which the text already forbade, and one in the exported
  schemas. All three are corrected in this release (`impl/SPEC-ISSUES.md`,
  E-01, E-02, E-09).

What this does not show: that two implementations by different people
interoperate on the wire (the second implementation was run against the
scenarios, not against the first), that the specification is complete,
or that a model-written implementation substitutes for a human one. The
next step is the same test run by a human implementer, or by a model of
another family, against the published scenarios.

The conformance scenarios, their blind variant and the profile format are
developed on the 0.2 branch of this repository (`0.2-dev`).
