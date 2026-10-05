"""Every object a session produces validates against the generated schema.

GIDP 0.2 must publish a normative JSON Schema. Generating it from the models
is only useful if the schema accepts what a conforming session emits,
so this replays two complete sessions and validates every object on the wire
against the schema file that `tools/emit_schema.py` writes.

This is the test that would catch a schema drifting from the code, which is
the usual fate of a hand-maintained schema and the reason 0.1 publishes none.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

jsonschema = pytest.importorskip("jsonschema")

import executive_succession as succession  # noqa: E402
from test_scenario import _run as run_cross_border  # noqa: E402


@pytest.fixture(scope="module")
def schema_dir(tmp_path_factory) -> Path:
    """Generate the schemas fresh, so the test cannot pass on a stale file."""
    target = tmp_path_factory.mktemp("schema")
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "emit_schema.py"), str(target)],
        check=True,
        capture_output=True,
    )
    return target


def _validate(message, schema_dir: Path) -> None:
    path = schema_dir / f"{type(message).__name__}.schema.json"
    assert path.exists(), f"no schema generated for {type(message).__name__}"
    schema = json.loads(path.read_text(encoding="utf-8"))
    jsonschema.validate(
        instance=message.model_dump(mode="json", exclude_none=True), schema=schema
    )


def test_every_object_of_the_transaction_session_validates(schema_dir):
    _, _, wire = run_cross_border()
    assert wire.transcript
    for _, message in wire.transcript:
        _validate(message, schema_dir)


def test_every_object_of_the_succession_session_validates(schema_dir):
    _, _, wire = succession.run(verbose=False)
    assert wire.transcript
    for _, message in wire.transcript:
        _validate(message, schema_dir)


def test_the_schema_rejects_an_object_missing_a_required_field(schema_dir):
    schema = json.loads(
        (schema_dir / "SessionOpen.schema.json").read_text(encoding="utf-8")
    )
    incomplete = {"type": "SessionOpen", "version": "gidp/0.1"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=incomplete, schema=schema)


def test_the_schema_rejects_a_value_outside_a_closed_vocabulary(schema_dir):
    schema = json.loads(
        (schema_dir / "SessionClose.schema.json").read_text(encoding="utf-8")
    )
    bad = {
        "type": "SessionClose",
        "version": "gidp/0.1",
        "session_id": "s",
        "expires_at": "2026-09-23T12:00:00Z",
        "reason": "maybe_later",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=schema)


def test_every_field_the_specification_requires_is_required(schema_dir):
    """E-09: the first export left `type` and `version` optional because the
    code gives them defaults. The schema must say what the specification
    says, and the mirror table must name only fields that exist."""
    sys.path.insert(0, str(ROOT / "tools"))
    from emit_schema import SPEC_REQUIRED

    for name, fields in SPEC_REQUIRED.items():
        schema = json.loads((schema_dir / f"{name}.schema.json").read_text())
        for field in fields:
            assert field in schema["properties"], f"{name}.{field} is not a property"
            assert field in schema["required"], f"{name}.{field} is not required"


def test_a_message_without_its_type_is_rejected(schema_dir):
    _, _, wire = run_cross_border()
    _, message = wire.transcript[0]
    instance = message.model_dump(mode="json", exclude_none=True)
    del instance["type"]
    schema = json.loads(
        (schema_dir / f"{type(message).__name__}.schema.json").read_text()
    )
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=schema)


def test_the_committed_schemas_are_current(schema_dir):
    for path in sorted(schema_dir.glob("*.json")):
        committed = ROOT / "schema" / path.name
        assert json.loads(committed.read_text()) == json.loads(path.read_text()), (
            f"{path.name} is stale: run tools/emit_schema.py schema/"
        )
