"""Validate a GIDP profile manifest (`profiles/FORMAT.md`).

    python tools/validate_profile.py ../profiles/co-investment-0.1.profile.json

The validator is dependency-free on purpose: a registry or venue that
gates the opening of a vertical on a valid manifest should not need this
repository's stack to run the gate. It enforces the structural shape of
`profiles/manifest.schema.json` and the cross-field rules a schema cannot
express — the rules that keep a profile from weakening the core:

- a manifest extends nothing but the two permitted extension points, and
  both only under its own namespace;
- an identifying attribute is never retrievable and never required for
  qualification (identity cannot precede the qualification it would gate);
- every name a manifest uses — required dimensions, predicate ranges,
  granularity, budgets — is an attribute it declares;
- every operator is a core operator or one the manifest itself declares;
- every joint predicate states its wire form, and every budgeted attribute
  a finite domain on its lattice, so that two implementers compute the
  same thing.

Exit code 0 and no output means valid; otherwise one finding per line.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

CORE_OPERATORS = {"equals", "intersects", "overlaps", "compatible_with"}
SUBJECTS = {"fact", "preference", "requirement", "side_dependent"}
TYPES = {"string", "number", "integer", "boolean", "money", "enum", "set", "range"}
GENERALITY = {"approximate_knowledge", "accepted_set"}
GENERAL_TYPES = {"string", "enum", "set", "range", "money"}
ABSENT = {"unknown", "declined"}
COMPUTABLE = {"exchanged_claims", "private_evaluation"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$")
VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+$")

TOP_KEYS = {"manifest", "profile", "attributes", "qualification", "budget", "extensions"}
PROFILE_KEYS = {"id", "version", "wire", "title", "description"}
ATTR_KEYS = {
    "subject", "subject_note", "type", "unit", "values", "bounds",
    "bounds_exclusive", "general_value_means", "operators", "absent_means",
    "identifying", "retrieval", "description",
}
QUAL_KEYS = {"required_dimensions", "joint_predicates", "opportunity_meaning"}
PREDICATE_KEYS = {"name", "over", "semantics", "computable_from", "wire"}
WIRE_KEYS = {"key", "operator", "value", "satisfied_when"}
VALUE_FORMS = {"point", "range"}
SATISFACTION = {"both_directions", "one_direction"}
ORDERED_TYPES = {"number", "integer", "money", "range"}
BUDGET_KEYS = {"granularity", "domain", "prior", "bits_per_attribute", "scope"}
EXT_KEYS = {"intended_use", "operators"}


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Return the list of findings; empty means the manifest is valid."""
    errors: list[str] = []
    e = errors.append

    if not isinstance(manifest, dict):
        return ["manifest: not an object"]
    for key in manifest:
        if key not in TOP_KEYS:
            e(f"unknown top-level field {key!r}: a manifest extends nothing "
              "but the permitted extension points")
    for key in ("manifest", "profile", "attributes", "qualification"):
        if key not in manifest:
            e(f"missing required field {key!r}")
    if errors:
        return errors

    if manifest["manifest"] != "gidp-profile/0.1":
        e(f"manifest token {manifest['manifest']!r}: expected 'gidp-profile/0.1'")

    profile = manifest["profile"]
    for key in profile:
        if key not in PROFILE_KEYS:
            e(f"profile: unknown field {key!r}")
    for key in PROFILE_KEYS:
        if key not in profile:
            e(f"profile: missing field {key!r}")
    profile_id = profile.get("id", "")
    if profile_id and not ID_PATTERN.match(profile_id):
        e(f"profile.id {profile_id!r}: must be a namespaced, dotted, "
          "lower-case identifier")
    if "version" in profile and not VERSION_PATTERN.match(str(profile["version"])):
        e(f"profile.version {profile['version']!r}: expected MAJOR.MINOR; "
          "a published version is immutable, a changed convention is a new one")
    if profile.get("wire") != "gidp/0.1":
        e(f"profile.wire {profile.get('wire')!r}: this format binds to 'gidp/0.1'")

    extensions = manifest.get("extensions", {})
    for key in extensions:
        if key not in EXT_KEYS:
            e(f"extensions: unknown extension point {key!r} — intended_use "
              "and operators are the only two the specification grants "
              "(Section 26)")
    namespace = f"{profile_id}:"
    for point in EXT_KEYS:
        for value in extensions.get(point, []):
            if not str(value).startswith(namespace):
                e(f"extensions.{point}: {value!r} is not namespaced under "
                  f"{namespace!r}")
    profile_operators = {
        v[len(namespace):] if str(v).startswith(namespace) else str(v)
        for v in extensions.get("operators", [])
    }
    allowed_operators = CORE_OPERATORS | set(extensions.get("operators", [])) | profile_operators

    attributes = manifest["attributes"]
    if not isinstance(attributes, dict) or not attributes:
        e("attributes: at least one attribute must be declared")
        return errors
    identifying: set[str] = set()
    for key, attr in attributes.items():
        where = f"attributes.{key}"
        for field in attr:
            if field not in ATTR_KEYS:
                e(f"{where}: unknown field {field!r}")
        subject = attr.get("subject")
        if subject not in SUBJECTS:
            e(f"{where}.subject: {subject!r} is not one of {sorted(SUBJECTS)}")
        if subject == "side_dependent" and not attr.get("subject_note"):
            e(f"{where}: side_dependent requires a subject_note saying what "
              "the value means on each side")
        typ = attr.get("type")
        if typ not in TYPES:
            e(f"{where}.type: {typ!r} is not one of {sorted(TYPES)}")
        if typ in {"money", "range"} and not attr.get("unit"):
            e(f"{where}: type {typ!r} requires a unit")
        if typ in {"enum", "set"} and not attr.get("values"):
            e(f"{where}: type {typ!r} requires values")
        if typ in GENERAL_TYPES and attr.get("general_value_means") not in GENERALITY:
            e(f"{where}: general_value_means is required for type {typ!r} "
              "(approximate_knowledge or accepted_set — the distinction "
              "decides how a narrower claim is answered)")
        for op in attr.get("operators", []) or [None]:
            if op is None:
                e(f"{where}: at least one operator is required")
            elif op not in allowed_operators:
                e(f"{where}.operators: {op!r} is neither a core operator "
                  f"({sorted(CORE_OPERATORS)}) nor declared under "
                  "extensions.operators")
        if attr.get("absent_means") is not None and attr["absent_means"] not in ABSENT:
            e(f"{where}.absent_means: {attr['absent_means']!r} is not one of "
              f"{sorted(ABSENT)}")
        if attr.get("identifying"):
            identifying.add(key)
            if attr.get("retrieval"):
                e(f"{where}: an identifying attribute MUST NOT be retrievable "
                  "(specification Section 10.6)")
    if "principal_identity" in attributes and "principal_identity" not in identifying:
        e("attributes.principal_identity: must be marked identifying "
          "(specification Section 10.6)")

    qualification = manifest["qualification"]
    for field in qualification:
        if field not in QUAL_KEYS:
            e(f"qualification: unknown field {field!r}")
    required = qualification.get("required_dimensions", [])
    if not required:
        e("qualification.required_dimensions: a profile that requires "
          "nothing gives its Opportunities no meaning beyond a screen")
    for dim in required:
        if dim not in attributes:
            e(f"qualification.required_dimensions: {dim!r} is not a declared "
              "attribute")
        if dim in identifying:
            e(f"qualification.required_dimensions: {dim!r} is identifying — "
              "qualification cannot require identity, which cannot precede it")
    if not qualification.get("opportunity_meaning"):
        e("qualification.opportunity_meaning: required — one sentence saying "
          "what a qualified Opportunity asserts under this profile")
    for i, predicate in enumerate(qualification.get("joint_predicates", [])):
        where = f"qualification.joint_predicates[{i}]"
        for field in predicate:
            if field not in PREDICATE_KEYS:
                e(f"{where}: unknown field {field!r}")
        for field in PREDICATE_KEYS:
            if not predicate.get(field):
                e(f"{where}: missing {field!r} — naming compatible_with is "
                  "not enough, the predicate's test must be stated")
        for attr in predicate.get("over", []):
            if attr not in attributes:
                e(f"{where}.over: {attr!r} is not a declared attribute")
        if predicate.get("computable_from") not in COMPUTABLE:
            e(f"{where}.computable_from: expected one of {sorted(COMPUTABLE)}")
        # E-11: a predicate two implementers cannot put on the wire the same
        # way is a predicate they cannot agree on.
        wire = predicate.get("wire")
        if isinstance(wire, dict):
            for field in wire:
                if field not in WIRE_KEYS:
                    e(f"{where}.wire: unknown field {field!r}")
            key = wire.get("key")
            if key not in predicate.get("over", []):
                e(f"{where}.wire.key: {key!r} is not among the attributes the "
                  "predicate ranges over")
            elif key in attributes and wire.get("operator") not in attributes[key].get(
                "operators", []
            ):
                e(f"{where}.wire.operator: {wire.get('operator')!r} is not an "
                  f"operator of {key!r}")
            if wire.get("value") not in VALUE_FORMS:
                e(f"{where}.wire.value: expected one of {sorted(VALUE_FORMS)}")
            elif (
                wire["value"] == "point"
                and key in attributes
                and attributes[key].get("type") not in ORDERED_TYPES
            ):
                e(f"{where}.wire.value: a point candidate needs an ordered "
                  f"attribute, and {key!r} is not one")
            if wire.get("satisfied_when") not in SATISFACTION:
                e(f"{where}.wire.satisfied_when: expected one of "
                  f"{sorted(SATISFACTION)}")

    budget = manifest.get("budget", {})
    for field in budget:
        if field not in BUDGET_KEYS:
            e(f"budget: unknown field {field!r}")
    if budget and budget.get("scope", "per_standing_interest") != "per_standing_interest":
        e("budget.scope: the budget's scope is per_standing_interest and a "
          "manifest cannot change it (specification Section 24.3)")
    for section in ("granularity", "domain", "bits_per_attribute"):
        for key in budget.get(section, {}):
            if key not in attributes:
                e(f"budget.{section}: {key!r} is not a declared attribute")
    if budget.get("prior", "uniform") != "uniform":
        e("budget.prior: only 'uniform' is defined by this format version")
    # E-12: a bit budget is a bound on a posterior, and a posterior needs a
    # finite public hypothesis space. The lattice gives it: cells of
    # min_bucket_width, edges on its multiples (origin 0), between the
    # domain's bounds.
    for key, bits in budget.get("bits_per_attribute", {}).items():
        width = budget.get("granularity", {}).get(key, {}).get("min_bucket_width")
        domain = budget.get("domain", {}).get(key)
        if not width:
            e(f"budget.bits_per_attribute.{key}: needs a granularity, the "
              "lattice the hypothesis space is cut on")
            continue
        if not isinstance(domain, dict) or "min" not in domain or "max" not in domain:
            e(f"budget.bits_per_attribute.{key}: needs a domain {{min, max}} -- "
              "without a finite hypothesis space no posterior can be computed")
            continue
        low, high = domain["min"], domain["max"]
        if not low < high:
            e(f"budget.domain.{key}: min must be below max")
            continue
        if low % width or high % width:
            e(f"budget.domain.{key}: bounds must fall on the lattice "
              f"(multiples of {width})")
            continue
        cells = (high - low) // width
        if bits > math.log2(cells):
            e(f"budget.bits_per_attribute.{key}: {bits} bits exceeds the "
              f"{math.log2(cells):.2f} bits the domain holds; the budget "
              "would never bind")

    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    status = 0
    for arg in argv:
        path = Path(arg)
        try:
            manifest = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"{path}: unreadable ({exc})")
            status = 1
            continue
        findings = validate_manifest(manifest)
        for finding in findings:
            print(f"{path}: {finding}")
        if findings:
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
