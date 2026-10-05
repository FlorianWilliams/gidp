# GIDP Profile Manifest Format (0.2 draft)

A domain profile is where GIDP's horizontality claim is kept or broken: the
core organises the exchange, and the profile is what makes an Opportunity
*mean* something in a domain (specification, Sections 14.6, 15.2, 21). This
document defines the **profile manifest**, a machine-readable declaration
of a profile's conventions, so that a profile is data: validatable
automatically, implementable by a party that has never spoken to its
author, and comparable across verticals. `manifest.schema.json` is the
JSON Schema; `impl/tools/validate_profile.py` is the reference validator,
which also enforces the rules a schema alone cannot express.

A registry, venue or community that hosts verticals MAY require a valid
manifest as the condition for opening one. The format is public so
that anyone can write conventions; what no manifest can do is weaken
the core.

## What a manifest is not

A manifest types *meanings*; it never sets *policy*. Which attributes are
`evaluation_only`, which are gated and what the Principal will disclose
belong to the Principal's Disclosure Policy (Section 10), chosen per
Standing Interest, and a profile that tried to demand disclosure would be
asking for what the protocol exists to withhold. The manifest
says what an attribute means and how claims over it are interpreted; each
Principal alone decides how far its own values travel.

A manifest also cannot touch the closed vocabularies (Section 26): it has
no field for new results, surfaces, gates, statuses or close reasons, and
the validator rejects unknown fields. Its only
extension points are the two the specification grants profiles
(`intended_use` values and claim operators), and both must be namespaced
under the profile's own id.

## The manifest, field by field

**`manifest`**: the format version token, `"gidp-profile/0.1"`.

**`profile`**: identity: `id` (reverse-DNS-style, namespaced, e.g.
`gidp.profile.co-investment`), `version` (immutable once published; a
changed convention is a new version), `wire` (the protocol version the
profile binds to, `"gidp/0.1"`), `title`, `description`.

**`attributes`**: the typed dictionary, one entry per claimable key:

- `subject`: what the value is *about* for the party that holds it, one
  of `fact` (a property of the Principal or its asset), `preference` (a set
  of configurations the Principal accepts), `requirement` (a condition on
  the counterparty), or `side_dependent` with a mandatory `subject_note`
  (the executive-succession `role` is a fact for the candidate and a
  requirement for the company).
- `type`: `string`, `number`, `integer`, `boolean`, `money`, `enum`,
  `set`, or `range`. `money` and `range` require `unit`; `enum` and `set`
  require `values`; `bounds` (inclusive) are available where ordering
  exists. Interval bounds are inclusive; a manifest that needs
  exclusive bounds says so per attribute with `bounds_exclusive`.
- `general_value_means`: `approximate_knowledge` or `accepted_set` (the
  S-53 distinction). Under `approximate_knowledge`, a responder holding
  `germany` answers `unknown` to `munich` (the core's cautious default);
  under `accepted_set` it answers `compatible`, because every German city
  is acceptable. Required for every attribute whose type admits
  generality (`string`, `enum`, `set`, `range`, `money`).
- `operators`: the subset of claim operators valid over this attribute,
  either core operators (`equals`, `intersects`, `overlaps`, `compatible_with`)
  or profile operators declared under `extensions.operators`.
- `absent_means`: what a responder holding no value answers, either
  `unknown` or `declined` (`declined` is the specification's default for
  disclosure, Section 14.4; claims default to `unknown`).
- `identifying`: `true` marks the attribute as identity-bearing (Section
  10.6): it then travels only under `reveal_identity`, whatever the
  message. `principal_identity`, if declared, MUST be marked.
- `retrieval`: `true` means the attribute may appear in Discovery
  Projections. An identifying attribute MUST NOT be retrievable.

**`qualification`**: what the profile demands before its Opportunities
carry operational meaning (these requirements enter the entry conditions
of specification Section 15.2 directly):

- `required_dimensions`: the attributes a session must have examined.
  Identifying attributes cannot appear here: qualification would then
  require identity, which cannot precede it.
- `joint_predicates`: the combinations where dimension-by-dimension
  overlap misleads (the buyer-at-80/seller-at-90 trap). Each names the
  attributes it ranges over, states its `semantics` in prose, and says
  what it is `computable_from`: `exchanged_claims` (both sides can verify
  it from what the session carried) or `private_evaluation` (each side
  verifies against its own values and answers as one claim). Naming
  `compatible_with` is not enough; the predicate's test must be stated.
  Each predicate also states its `wire` form, because two implementers
  who agree on what a predicate means but not on how it travels cannot
  agree on whether it held (E-11):
  - `key` and `operator`: the claims that carry it (an attribute the
    predicate ranges over, with one of that attribute's operators);
  - `value`: either `point`, where the claim names one candidate value and
    the responder answers whether that value satisfies its own private
    value (for a range, whether the point lies inside it, bounds
    inclusive), or `range`, where the claim names a band under the
    operator's ordinary meaning;
  - `satisfied_when`: either `both_directions`, where the predicate holds
    when each side has answered `compatible` to the *same* value, asked in
    each direction, both propositions still standing, or `one_direction`,
    where one standing `compatible` suffices.

  `conditionally_compatible` does not satisfy a predicate: a coarsened
  answer withholds the fact the predicate exists to establish. A
  responder that wants it to hold answers truthfully, which Section 15.5
  always permits. A candidate value is a hypothesis chosen on the lattice,
  never either side's private bound (Section 14.3). Every declared joint
  predicate enters the entry conditions: a session qualifies only when all
  of them hold. The reference implementation reads both
  `required_dimensions` and the predicates' wire forms from the manifest
  (`impl/gidp/profile.py`) with no vertical-specific code.
- `opportunity_meaning`: one sentence stating what a qualified Opportunity
  asserts under this profile, and no more.

**`budget`**: what the profile declares to the information budget of
Section 24.3. A bit budget bounds a posterior, and a posterior needs a
hypothesis space and a prior; a manifest that gives only a number of bits
gives nothing two implementations can compute alike (E-12). So, per
budgeted attribute:

- `granularity.<attr>.min_bucket_width`: the lattice. Claim bounds fall
  on integer multiples of the width (origin 0) and a band is at least one
  cell wide; constraining where edges may fall, not only how wide a band
  is, is what caps resolution (Section 24.3).
- `domain.<attr>`: `{min, max}`, on the lattice; the finite public
  hypothesis space is the cells between them. A Principal whose value lies
  outside the domain is outside what the budget protects, and its Agent
  should decline claims on that attribute rather than answer them.
- `prior`: `uniform` over the cells, the only prior this format version
  defines.
- `bits_per_attribute.<attr>`: the worst-case budget, cumulative over the
  Standing Interest: before answering, the responder computes the
  posterior under every answer it might give and declines if the worst
  case would leave fewer than `cells / 2^bits` candidates. It must not
  exceed the information the domain holds, `log2(cells)`, or it would
  never bind.

The scope is always `per_standing_interest`; the manifest cannot change
that. What the budget does not bound (correlations between attributes,
timing, outside knowledge) it does not claim to bound (Section 24.3).

**`extensions`**: the two permitted extension points, every value
prefixed `"<profile id>:"`.

## Validation

`validate_profile.py` checks the schema and then the cross-field rules:
required dimensions and predicate ranges name declared attributes;
operators are core or declared; identifying attributes are neither
retrievable nor required for qualification; extensions are namespaced;
every joint predicate has a wire form over its own attributes and
operators; every bit budget has a lattice and a domain on it, and asks no
more bits than the domain holds; granularity and budget entries name
declared attributes; no unknown fields anywhere. A manifest that passes
can be implemented from this document and the specification alone. That
is the format's conformance bar, and the two instances in this directory
(`co-investment`, narrow and numeric; `executive-succession`, relational
and asymmetric) exist to hold it: the same core and the same corpus serve
two verticals, with no protocol work between them.

The first independent implementation (October 2026) implemented the
co-investment instance from this document and the specification alone,
and found the bar was not met: `ticket_meets` had no wire form, the
budget had no hypothesis space, and `opportunity_meaning` promised a
stage check the required dimensions did not require and an attestation no
claim can carry. The format and both instances were corrected
(`impl/SPEC-ISSUES.md`, E-10 to E-12) and are now held to that bar.
