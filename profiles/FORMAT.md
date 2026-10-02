# GIDP Profile Manifest Format (0.2 draft)

A domain profile is where GIDP's horizontality claim is kept or broken: the
core organises the exchange, and the profile is what makes an Opportunity
*mean* something in a domain (specification, Sections 14.6, 15.2, 21). This
document defines the **profile manifest** — a machine-readable declaration
of a profile's conventions — so that a profile is data: validatable
automatically, implementable by a party that has never spoken to its
author, and comparable across verticals. `manifest.schema.json` is the
JSON Schema; `impl/tools/validate_profile.py` is the reference validator,
which also enforces the rules a schema alone cannot express.

A registry, venue or community that hosts verticals MAY require a valid
manifest as the condition for opening one. The format is public precisely
so that anyone can write conventions; what no manifest can do is weaken
the core.

## What a manifest is not

A manifest types *meanings*; it never sets *policy*. Which attributes are
`evaluation_only`, which are gated, what the Principal will disclose —
that is the Principal's Disclosure Policy (Section 10), chosen per
Standing Interest, and a profile that tried to demand disclosure would be
asking for exactly what the protocol exists to withhold. The manifest
says what an attribute means and how claims over it are interpreted; each
Principal decides, alone, how far its own values travel.

A manifest also cannot touch the closed vocabularies (Section 26): it has
no field for new results, surfaces, gates, statuses or close reasons, and
the validator rejects unknown fields rather than tolerating them. Its only
extension points are the two the specification grants profiles —
`intended_use` values and claim operators — and both must be namespaced
under the profile's own id.

## The manifest, field by field

**`manifest`** — the format version token, `"gidp-profile/0.1"`.

**`profile`** — identity: `id` (reverse-DNS-style, namespaced, e.g.
`gidp.profile.co-investment`), `version` (immutable once published; a
changed convention is a new version), `wire` (the protocol version the
profile binds to, `"gidp/0.1"`), `title`, `description`.

**`attributes`** — the typed dictionary, one entry per claimable key:

- `subject`: what the value is *about* for the party that holds it —
  `fact` (a property of the Principal or its asset), `preference` (a set
  of configurations the Principal accepts), `requirement` (a condition on
  the counterparty), or `side_dependent` with a mandatory `subject_note`
  (the executive-succession `role` is a fact for the candidate and a
  requirement for the company).
- `type`: `string`, `number`, `integer`, `boolean`, `money`, `enum`,
  `set`, or `range`. `money` and `range` require `unit`; `enum` and `set`
  require `values`; `bounds` (inclusive) are available where ordering
  exists. Interval bounds are **inclusive**; a manifest that needs
  exclusive bounds says so per attribute with `bounds_exclusive`.
- `general_value_means`: `approximate_knowledge` or `accepted_set` — the
  S-53 distinction. Under `approximate_knowledge`, a responder holding
  `germany` answers `unknown` to `munich` (the core's cautious default);
  under `accepted_set` it answers `compatible`, because every German city
  is acceptable. Required for every attribute whose type admits
  generality (`string`, `enum`, `set`, `range`, `money`).
- `operators`: the subset of claim operators valid over this attribute —
  core operators (`equals`, `intersects`, `overlaps`, `compatible_with`)
  or profile operators declared under `extensions.operators`.
- `absent_means`: what a responder holding no value answers — `unknown`
  or `declined` (`declined` is the specification's default for
  disclosure, Section 14.4; claims default to `unknown`).
- `identifying`: `true` marks the attribute as identity-bearing (Section
  10.6): it then travels only under `reveal_identity`, whatever the
  message. `principal_identity`, if declared, MUST be marked.
- `retrieval`: `true` means the attribute may appear in Discovery
  Projections. An identifying attribute MUST NOT be retrievable.

**`qualification`** — what the profile demands before its Opportunities
carry operational meaning (these requirements enter the entry conditions
of specification Section 15.2 directly):

- `required_dimensions`: the attributes a session must have examined.
  Identifying attributes cannot appear here — qualification would then
  require identity, which cannot precede it.
- `joint_predicates`: the combinations where dimension-by-dimension
  overlap misleads (the buyer-at-80/seller-at-90 trap). Each names the
  attributes it ranges over, states its `semantics` in prose, and says
  what it is `computable_from`: `exchanged_claims` (both sides can verify
  it from what the session carried) or `private_evaluation` (each side
  verifies against its own values and answers as one claim). Naming
  `compatible_with` is not enough; the predicate's test must be stated.
- `opportunity_meaning`: one sentence: what a qualified Opportunity
  asserts under this profile, and no more.

**`budget`** — what the profile declares to the information budget of
Section 24.3: per-attribute `granularity` (the minimum bucket width a
claim may name; the lattice of the reference implementation) and
`bits_per_attribute` (the worst-case budget). The scope is always
`per_standing_interest`; the manifest cannot change that.

**`extensions`** — the two permitted extension points, every value
prefixed `"<profile id>:"`.

## Validation

`validate_profile.py` checks the schema and then the cross-field rules:
required dimensions and predicate ranges name declared attributes;
operators are core or declared; identifying attributes are neither
retrievable nor required for qualification; extensions are namespaced;
granularity and budget entries name declared attributes; no unknown
fields anywhere. A manifest that passes can be implemented from this
document and the specification alone — that is the format's conformance
bar, and the two instances in this directory (`co-investment`, narrow and
numeric; `executive-succession`, relational and asymmetric) exist to hold
it: the same core, the same corpus, two verticals, no protocol work
between them.
