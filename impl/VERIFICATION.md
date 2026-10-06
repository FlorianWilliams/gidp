# How this implementation is verified

This page lists what the reference implementation promises, how each
promise is tested, and the rules adopted after reviews of the published
releases found defects that the tests in place had not caught
(`SPEC-ISSUES.md`, P-01 to P-09). The rules are there so that the same kind
of defect is not found a second time by a reviewer.

## The layers, and what each one cannot see

| Layer | Where | What it catches | What it cannot see |
|---|---|---|---|
| Regression tests | `tests/test_review_findings.py`, `tests/test_release_review.py` | The exact case a review reported | The neighbouring case nobody reported (P-03 fixed, P-05 found next) |
| Guarantee tests | `tests/test_guarantees.py` | A promise broken by any question of any shape, on a small domain | Shapes and domains the test does not enumerate (P-07 escaped a test written for integers only) |
| Mutation check | `tools/mutation_check.py` | A line of code no test defends | Behaviour that is missing or in the wrong place (P-06) |
| Conformance corpus | `conformance/` on `0.2-dev` | Divergence between implementations on fixed scenarios | Anything the scenarios do not exercise |
| Measurements | `baselines/` | How much a given strategy extracts | Other strategies; and the shipped mechanism, if the harness models it instead of calling it (P-08) |
| External review | reports, `SPEC-ISSUES.md` | Contradictions in the text (reading); defects in the code (running it) | What the reviewers share as blind spots; every review so far was by a language model |

No layer is sufficient alone, and the defects found after publication each
passed through all the layers that existed at the time.

## The guarantees and their tests

Each guarantee is tested against an oracle that does not share the code of
the control it checks: for every candidate value, a responder holding that
value is rebuilt and the same claims are replayed through the real Agent.

| Guarantee | Specification | Test in `test_guarantees.py` | Defects it would have caught |
|---|---|---|---|
| Under a lattice, two values whose bounds fall in the same cells receive the same answers to every question, under every operator | 24.3 | `test_no_question_distinguishes_values_in_the_same_cells` (scalars, thresholds, ranges) | P-03, P-05 |
| A value the lattice cannot cover raises, on every question | 24.3 | `test_a_value_the_lattice_cannot_cover_raises_on_every_question` | P-07 |
| What any sequence of answers reveals never exceeds the budget, and equals what the budget records | 24.3 | `test_the_budget_holds_and_records_what_is_revealed` (thresholds, scalars, labels, lists, the four dependency primitives; budgets of 0, 1 and 2 bits) | P-06 |
| A new session obtains from an Agent exactly what it would obtain from an Agent that never held a session | 14.5 | `test_a_new_session_obtains_exactly_what_a_fresh_agent_would_give` | P-01 |
| Under PROBE `approval_required`, nothing is answered before the Principal decides | 16.3 | `test_nothing_is_answered_while_probe_awaits_approval` | P-02 |

Each row was checked by restoring the defective code and confirming that
the test fails.

## Rules

1. **State the guarantee before fixing the case.** A reported defect is a
   counterexample to a promise. Write the promise as a property, test it
   on a domain small enough to enumerate, and consider the fix done when
   the property holds. Fixing the reported case alone left the next case
   open (P-03, then P-05).
2. **Enumerate shapes as well as values.** Every guarantee test covers
   integers, decimals, booleans, thresholds, ranges, labels, lists and the
   dependency primitives, under every core operator. A test inherits the
   assumptions of whoever wrote it, and the shapes left out are where the
   next defect is (P-07).
3. **Test against an oracle, never against the control's own arithmetic.**
   A control that computes what an answer reveals can be wrong about where
   the value lives; checking it with its own computation repeats the error
   (P-06). The oracle replays the claims through the real Agent.
4. **Default to refusal for shapes a control does not understand.** A check
   written for bands that lets every other shape through fails open (P-03).
   A control admits what it can bound and declines the rest.
5. **Decide from the claims, never from the value; raise when the value is
   outside what the control covers.** A refusal that happens only for
   some values tells the querent which (Section 24.3). A configuration the
   control cannot honour is an error to fix before deployment.
6. **Measure the shipped mechanism.** A harness calls the controls in
   `gidp/`, never a copy of their rules (P-08).
7. **Separate a guarantee from a measurement.** A guarantee is the worst case
   over every strategy (the budget, the cell). A measurement is what one
   strategy obtained, on one hypothesis space under one prior, and is
   reported with all three (P-04, P-09). Bits measure the reduction of a
   hypothesis space; they do not measure economic risk or
   re-identification.
8. **Read mutation results for what they are.** All mutations caught means
   the existing code is defended. It says nothing about code that should
   exist and does not.
9. **Record before fixing, on every branch.** Each finding is entered in
   `SPEC-ISSUES.md` with a test that failed before the fix, and the fix is
   carried to every maintained branch with its own test run.
10. **Ask reviewers to break guarantees with code.** Reading the text finds
    contradictions; running the code against a stated promise finds
    implementation defects. The brief below is the one to give.
11. **Batch changes to the text.** Defects in the implementation are fixed
    as found. Changes to the specification's text are collected in
    `spec/drafts/` for the next minor version; a patch version is issued
    only when a published sentence is false.

## Brief for a reviewer

> Clone the repository at a tag and run the tests. Then take each
> guarantee listed in `impl/VERIFICATION.md` and in Sections 14.5, 16.3 and
> 24.3 of the specification, and try to break it with code: write the
> smallest script that makes the implementation violate it. Try shapes the
> tests do not enumerate (other value types, operators, attributes stored
> elsewhere, values outside a declared domain), sequences of claims across
> sessions and identities, and the measurement harness against the shipped
> controls. Report each violation with its script. Say which guarantees you
> tried and could not break.

## Before a release

- Full test suite, `ruff`, `mypy`, and the mutation check, on every branch.
- The guarantee tests, plus a check that each still fails when its defect
  is restored (the mutation check does this for the controls).
- Every figure quoted in the documents reproduced from `baselines/`, with
  its strategy, hypothesis space and prior.
- The specification's normative keywords counted before and after any
  edit to its text.
