# Disclosure controls (0.2 draft, revision 1)

Status: draft for GIDP 0.2. Section 24.3 of GIDP 0.1.2 remains normative
until 0.2 is published. This draft collects what the reviews of the
published releases found in the two controls that section recommends, the
information budget and the granularity lattice, and proposes the rules 0.2
should state. It is the place where further findings about these controls
are recorded, so that they reach the specification together, in one
revision.

## What the reviews found

Every finding below was reproduced against the reference implementation
before it was fixed, and each has a regression test. The entries are in
`impl/SPEC-ISSUES.md`.

| Entry | Control | Finding | Where it was wrong |
|---|---|---|---|
| E-12 | budget | A number of bits with no hypothesis space or prior cannot be computed alike by two implementations | profile format |
| P-03 | lattice | A point question (`equals 45`) passed a check written for bands | implementation |
| P-04 | budget | "Under one bit" was one strategy's result; the guarantee is the budget | text |
| P-05 | lattice | Two inclusive bands sharing an edge isolate it; `equals` on a band confirms it | text and implementation |
| P-06 | budget | Candidates were simulated where the evaluator never reads the dependency primitives, so a zero-bit budget answered | implementation |
| P-07 | lattice | Integer cells leave gaps for decimals, which locate a value to one unit | text and implementation |
| P-08 | both | The measurement harness modelled the lattice instead of calling it | measurement |
| P-09 | lattice | `log2(range / width)` bounds resolution and was read as information | text |

None required a change to the wire.

## The principle both controls rest on

A decision to answer or decline must depend only on the claims asked and
the answers already given, never on the value being protected
([KMN2005]; Section 24.3). The 0.1 text states it for the budget. Two
consequences are not stated, and P-06 and P-07 came from them.

**A configuration error is raised, never answered.** When a control cannot
apply to the value it guards (a decimal under an integer lattice, a value
outside a declared domain), any answer the Agent gives depends on that
value, a `declined` included. The reference implementation raises
`LatticeDomainError` on every claim in that case. The Agent fails before
the session can learn anything; the deployment is wrong, and says so.

This contradicts `profiles/FORMAT.md` as written, which tells an Agent
whose value lies outside a budget's domain to decline claims on that
attribute. A refusal that happens only when the value is out of range
tells the querent that it is. 0.2 should replace that sentence with the
rule above, or make the domain total (below).

**The decision procedure and the answer procedure must be the same
function.** A budget computes what each possible answer would reveal by
evaluating the claim against every candidate value. If that evaluation
differs from the one that produces the answer, in where it reads the
value, how it coarsens or which operator semantics it uses, the budget
measures something other than what is disclosed. P-06 is the instance.
The rule for 0.2: the budget's candidate evaluation is the responder's
own evaluation with the value substituted where it is read, for every
attribute the evaluator can read, the dependency primitives of Section
19.1 included.

## The lattice

**Cells.** A lattice of width `w` cuts an attribute into cells
`[k*w, (k+1)*w - 1]`, origin 0, over integers in the attribute's declared
unit. The profile declares the unit (cents, euros, people, days); an
attribute whose values are not integers in a declared unit cannot carry a
lattice. A decimal quantity is expressed in a finer integer unit
(cents for euros), which is the usual practice for money and costs
nothing.

**Admissible claims.** On a lattice attribute, the only admissible claim is
`overlaps` with a band made of whole cells: a lower bound that is a
multiple of `w` or absent, an upper bound one below a multiple of `w` or
absent, and at least one of the two present. Every other operator and
every other shape is declined. This is the rule the reference
implementation applies since P-05, and a property test checks it over
every question and every value of a small range: two values in the same
cell receive the same answers.

**Domain.** A profile declares the domain of every lattice attribute. 0.2
should make the domain total: the first and last cells are open-ended, so
that every integer falls in exactly one cell and no value can be outside
it. The question of what to do with an out-of-domain value then does not
arise.

**What the lattice bounds.** It bounds *resolution*: no sequence of
admissible claims distinguishes two values in the same cell. It does not
by itself bound *information*. If the possible values of an attribute are
spread unevenly over the cells, identifying a cell reveals more about the
values it holds alone (P-09: on the measured grid of 41 thresholds, the
last cell holds one, and one answer identifies it). The worst-case leak of
a lattice is `log2(N) - log2(m)` bits, where `N` is the number of possible
values and `m` the fewest any cell holds. It equals `log2(cells)` only when
every cell holds the same mass. 0.2 should state the bound in that form,
and a profile that relies on the lattice should declare a prior under
which the cells carry equal mass; the format's `uniform` prior over cells
does exactly that.

**Joint predicates.** A joint predicate (profile format, `wire`) asks
whether one candidate value suits both sides, and the candidate is a
point. Under the rule above a point is never admissible, so a profile
cannot today put a lattice on an attribute that a joint predicate tests.
Two ways out:

- *Points against ranges only.* When the protected value is a range (the
  manifest's `type: range`, such as an investable ticket), a point claim on
  a lattice edge tests whether the range reaches that edge, which is one
  cell of resolution on each bound. The lattice would admit a point on a
  multiple of `w` for `range` attributes and keep refusing it for scalar
  ones, where it confirms the value exactly. The rule depends on the
  declared type, never on the value, so it stays simulatable.
- *Cells as candidates.* The predicate asks whether both sides accept some
  value in a given cell. The semantics are coarser (two ranges that meet
  only inside one cell would qualify), and the predicate would no longer
  certify a single common amount.

This draft proposes the first. It keeps the predicate's meaning and needs
one sentence in the format.

## The budget

**Scope.** The budget applies to every attribute the evaluator can read,
under the substitution rule above. For the dependency primitives the
hypothesis space is a finite set of candidate lists that the profile
declares, in the same way it declares a numeric domain. The profile
format currently declares domains for numeric attributes only; 0.2 should
add an enumerated domain for list- and label-valued attributes.

**The guarantee.** The budget bounds, per attribute and per Standing
Interest, the worst-case reduction of the declared hypothesis space under
the declared prior. That is the statement 0.2 should make, and the only
number it should attach to the budget is the budget (P-04).
Results of a particular attack are measurements and belong in the
companion documents, labelled with the strategy that produced them.

**What it does not bound.** Correlations between attributes, timing,
knowledge the querent holds from elsewhere, and anything outside the
declared hypothesis space. The 0.1 text says so; 0.2 should keep it next to
the guarantee and not in a separate section.

**Persistence.** The 0.1 requirements stand unchanged: one ledger per
Standing Interest, surviving new sessions, restarts and replicas, with
concurrent requests reserved against the same balance.

## Composing the two

The lattice is stateless and cannot be drained; the budget is stateful and
tighter. Composed, the lattice decides which claims are admissible and the
budget, computed over the lattice's cells, decides how many of them are
answered. Measured with the shipped controls (P-08), a 20M lattice under a
three-bit budget holds the probing strategy to 1.77 bits of 5.36 and
answers forty honest counterparties out of forty, which improves on the
lattice alone; a two-bit budget alone leaks less (0.97 bits) and refuses
five. The composition is the configuration 0.2 should describe first.

## Measurement discipline

Every figure about these controls states its hypothesis space, its prior
and the adversary's strategy, and distinguishes a guarantee (the worst
case over all strategies, which is the budget or the cell structure) from
a measurement (what one strategy obtained). Measurements call the
controls the library ships, never a model of them (P-08); a test fails if
the two diverge. Bits measure the reduction of a hypothesis space chosen
for an experiment. They do not measure economic risk or
re-identification by cross-referencing, and the companion documents say
so where they cite them.

## Proposed changes for 0.2

1. Section 24.3: state the simulatability principle as a requirement on
   both controls, including that a control which cannot apply to the
   value it guards raises a configuration error and does not answer.
2. Section 24.3: define the lattice over integers in a declared unit, with
   total domains, whole-cell bands as the only admissible claims, and the
   worst-case bound `log2(N) - log2(m)`.
3. Section 24.3: define the budget's candidate evaluation as the
   responder's own evaluation, over every attribute it reads, with the
   guarantee stated as the budget.
4. Profile format: a `unit` required for every lattice attribute; total
   domains; enumerated domains for list- and label-valued attributes;
   points admissible on lattice edges for `range` attributes only.
5. Conformance: the cell property test and the zero-bit budget test become
   conformance scenarios, runnable against any implementation.

## Open questions

- Correlated attributes. Both controls work per attribute; a querent who
  learns about two correlated attributes learns more than either budget
  records. Whether 0.2 should offer a joint budget, or only say that it
  does not, is open.
- Non-uniform priors. A profile may know that values cluster. A budget
  computed under a uniform prior then understates what an answer reveals
  about the dense region. Whether the format should allow declared priors,
  and how two implementations would agree on one, is open.
- Coarsening. Section 15.4's coarsening is not simulatable (Section 24.3).
  Whether 0.2 should forbid it on budgeted attributes, where the budget
  already governs what is conceded, is open.

## What the reference implementation does today

On `master` (implementation 0.1.2) and on this branch: the lattice admits
whole-cell `overlaps` bands only and raises on non-integer values; the
budget substitutes candidates where the evaluator reads them, dependency
primitives included; `baselines/frontier.py` calls the shipped lattice.
Not yet implemented: total domains, enumerated domains, points for `range`
attributes under a lattice, and the two conformance scenarios.
