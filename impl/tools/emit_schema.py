"""Emit JSON Schema for every transmitted object.

GIDP 0.2 must publish a normative JSON Schema (Appendix F.1). Generating it
from working code rather than writing it by hand means the required fields
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


def main(out: str = "schema") -> None:
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    for model in TRANSMITTED:
        schema = model.model_json_schema()
        schema["$id"] = f"urn:example:gidp:0.1:{model.__name__}"
        path = target / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
