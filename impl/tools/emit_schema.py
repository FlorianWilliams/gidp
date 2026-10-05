"""Emit JSON Schema for every transmitted object.

GIDP 0.2 must publish a normative JSON Schema (Appendix F.1). Generating it
from working code, instead of writing it by hand, means the required fields
have been exercised by an implementation before they are frozen.

    python tools/emit_schema.py schema/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp import objects  # noqa: E402

TRANSMITTED = (
    objects.DiscoveryProjection,
    objects.SessionOpen,
    objects.SessionAccept,
    objects.CompatibilityRequest,
    objects.CompatibilityResponse,
    objects.DisclosureRequest,
    objects.DisclosureResponse,
    objects.ConsentRequest,
    objects.ConsentResponse,
    objects.Opportunity,
    objects.Handoff,
    objects.SessionClose,
)


#: Section 14's envelope: every transmitted object carries these, the
#: DiscoveryProjection excepted for `session_id` (Section 11.1).
ENVELOPE = ("type", "version", "session_id", "expires_at")

#: The required fields the specification lists per object (Sections 11.1,
#: 14.1-14.8), mirrored here because a field with a default in the code is
#: not "required" to pydantic, which is how the first export omitted
#: `type` and `version` everywhere (E-09). `test_schema` checks that every
#: name below is a property of its object, so this table cannot drift into
#: naming fields that do not exist.
SPEC_REQUIRED: dict[str, tuple[str, ...]] = {
    "DiscoveryProjection": ("type", "version", "expires_at", "projection_id", "endpoint"),
    "SessionOpen": ENVELOPE + (
        "request_id", "initiator", "purpose", "max_depth", "profile", "features",
    ),
    "SessionAccept": ENVELOPE + (
        "request_ref", "responder", "max_depth", "profile", "features",
    ),
    "CompatibilityRequest": ENVELOPE + ("request_id", "claims", "allowed_results"),
    "CompatibilityResponse": ENVELOPE + (
        "request_ref", "results", "session_status", "next",
    ),
    "DisclosureRequest": ENVELOPE + (
        "request_id", "attribute", "purpose", "requested_surface", "intended_use",
    ),
    "DisclosureResponse": ENVELOPE + ("request_ref", "attribute", "status"),
    "ConsentRequest": ENVELOPE + (
        "request_id", "action", "scope", "reciprocal", "binding_commitment",
    ),
    "ConsentResponse": ENVELOPE + ("request_ref", "status", "granted_scope"),
    "Opportunity": ENVELOPE + (
        "structure", "evaluated_dimensions", "compatible_dimensions",
        "open_conditions", "contingent_on", "identity_status",
    ),
    "Handoff": ENVELOPE + (
        "target", "authorized_scope", "requires_principal_presence", "contingent_on",
    ),
    "SessionClose": ENVELOPE + ("reason",),
}


def schema_for(model: type) -> dict:
    schema = model.model_json_schema()
    schema["$id"] = f"urn:example:gidp:0.1:{model.__name__}"
    required = set(schema.get("required", [])) | set(SPEC_REQUIRED[model.__name__])
    schema["required"] = sorted(required)
    return schema


def main(out: str = "schema") -> None:
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    for model in TRANSMITTED:
        schema = schema_for(model)
        path = target / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
