"""Generate the blind corpus from the conformance corpus.

    python impl/tools/make_blind.py

`conformance/scenarios-blind/` is generated, never edited by hand. Each
scenario named in `conformance/blind-map.json` is copied under a neutral
name with every expectation removed (`expect*`, `forbid_*`, comments,
notes, section references) so that an implementer sees stimuli only and
reports what its implementation did. The mapping file stays outside the
blind directory: scenario names describe outcomes, and leak them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2] / "conformance"
SOURCE = ROOT / "scenarios"
TARGET = ROOT / "scenarios-blind"
MAP = ROOT / "blind-map.json"

STRIPPED_TOP = {"notes", "spec", "_comment"}


def _is_expectation(key: str) -> bool:
    return key.startswith(("expect", "forbid_")) or key == "_comment"


def blind(scenario: dict[str, Any], name: str) -> dict[str, Any]:
    steps = []
    for step in scenario["steps"]:
        kind = next(iter(step))
        body = step[kind]
        if isinstance(body, dict):
            body = {k: v for k, v in body.items() if not _is_expectation(k)}
        steps.append({kind: body})
    out = {k: v for k, v in scenario.items() if k not in STRIPPED_TOP | {"steps"}}
    out["scenario"] = name
    out["steps"] = steps
    return out


README = """\
# Blind conformance scenarios

Each file is one scenario: a declarative initial state for two parties and
an ordered sequence of steps. Run the steps against your implementation
and report, step by step, everything observable it did. No expected
outcomes are stated anywhere in these files, and no file carries its own
reporting instruction: this README is the instruction for all of them.
The comparison is performed by the evaluator.

## Setup

`setup` declares the two roles (`A` opens the session; `B` responds), in
implementation-neutral terms:

- `conditions`: attribute -> the private value that side holds.
- `policy`: attribute -> its disclosure class, written `surface`,
  `surface/gate`, `evaluation_only` or `never`. An attribute absent from
  `policy` is `evaluation_only` (Section 9.1).
- `authority`: level -> JSON `true` / `false`, or the string
  `approval_required`. **Unset levels are `false`.** This is a convention
  of these scenarios, not a default of the specification, which states
  none.
- `conditional_on` (optional): declared dependencies of that side's
  interest. `conditional_on_policy` (optional) sets their disclosure class.
- `required_dimensions` (optional): the profile's minimum qualification
  coverage in force for that side.
- `pre_approved` (optional): attributes that side's Principal has
  approved in advance.

## Steps

| Step | What to do |
|---|---|
| `{"open": {"purpose", "max_depth"?}}` | A opens the session, B answers. |
| `{"ask": {"from", "claims": [...], "hold"?}}` | The named side sends the claims batch; the other side processes it. `hold: true` means the receiving side holds the request for a Principal decision and produces no response. |
| `{"expire_ask": {}}` | The most recently held ask's `expires_at` passes with no terminal response ever sent. |
| `{"request_disclosure": {"from", "attribute", "purpose", "hold"?, "undelivered"?}}` | A disclosure request, processed by the other side. `hold: true`: the response is not yet produced. `undelivered: true`: the request leaves the sender and has not reached the other side. |
| `{"release_disclosure": {}}` | The most recently held disclosure request is now answered. |
| `{"request_consent": {"from", "action", "scope"}}` | A consent request, processed by the other side. |
| `{"principal_answers": {"role", "granted"}}` | The named side's Principal decides the outstanding consent. |
| `{"set_authority": {"role", "level", "value"}}` | The named side's Principal changes a delegation mid-session. Nothing is transmitted by this step itself. |
| `{"qualify": {"role"}}` | The named side's qualification conditions are re-evaluated. If your implementation re-evaluates on its own after every event, this step may do nothing. Report whether the side is QUALIFIED after the step, and anything emitted. |
| `{"opportunities": {"role"}}` | Report how many Opportunities the named side has emitted in this session so far. |
| `{"state": {"role"}}` / `{"status": {"role"}}` | Report the named side's session state and its locally computed `session_status`. |
| `{"opportunity": {"role"}}` | The named side builds its Opportunity; report the full serialised object, or the refusal. |
| `{"handoff": {"from", "target"}}` | `target` is the Section 14.7 object. The named side attempts to emit a Handoff to it; the other side processes it. Report emissions, refusals, and both sides' resulting states. |

If your implementation refuses to perform a step -- refuses to send, to
accept, or to act -- that refusal IS the result to report, together with
the rule of the specification you believe requires it. Report also
anything your implementation transmits that the step did not explicitly
ask about.
"""


def main() -> int:
    mapping = json.loads(MAP.read_text())["map"]
    TARGET.mkdir(exist_ok=True)
    expected = {f"{name}.json" for name in mapping} | {"README.md"}
    for stale in TARGET.iterdir():
        if stale.name not in expected:
            stale.unlink()
    for name, source in sorted(mapping.items()):
        scenario = json.loads((SOURCE / f"{source}.json").read_text())
        text = json.dumps(blind(scenario, name), indent=2, ensure_ascii=False)
        for leak in ("expect", "forbid", "notes", source):
            if leak in text:
                print(f"{name}: {leak!r} survived blinding", file=sys.stderr)
                return 1
        (TARGET / f"{name}.json").write_text(text + "\n")
    (TARGET / "README.md").write_text(README)
    print(f"{len(mapping)} blind scenarios written to {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
