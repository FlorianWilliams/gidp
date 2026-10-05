"""Which closed-vocabulary values does anything actually reach?

    python tools/vocabulary_coverage.py

A closed vocabulary is an interoperability obligation: every value in it is
something every implementer must handle. A value that no worked domain
reaches is therefore one of two things, and the specification should say
which — a gap in the demonstration, or a value that should not be normative
in 0.1. This tool makes the question answerable instead of rhetorical, and
`tests/test_vocabulary_coverage.py` makes it answerable again tomorrow.

It found S-15 and S-16.
"""

from __future__ import annotations

import re
import sys
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gidp.vocab as vocab  # noqa: E402

#: Values nothing reaches, each with the reason it is nonetheless kept. A
#: value absent from this register and absent from the code is a value the
#: next release should remove or demonstrate; the test fails until someone
#: has written a line here saying which.
KEPT_WITHOUT_A_DEMONSTRATION = {
    "CloseReason.EXPIRED": "reachable when a Standing Interest or session outlives its validity; "
    "no example waits long enough to show it",
    "Feature.MULTI_PARTY": "Section 19.2 is experimental and this implementation does not "
    "implement it: an experimental section is not demonstrated",
    "HandoffKind.WORKFLOW": "a handoff target that is neither a human nor a protocol; plausible "
    "and unexercised",
    "IdentityStatus.DECLINED": "an Opportunity whose counterparty refused identity; the worked "
    "domains consent",
    "IdentityStatus.PENDING_PRINCIPAL_APPROVAL": "the provisional case of Section 14, on the identity axis",
    "IntendedUse.HANDOFF_PREPARATION": "declared purpose for a disclosure sought after qualification",
    "IntendedUse.IDENTITY_VERIFICATION": "declared purpose for a disclosure sought to verify a counterparty",
    "Retention.UNTIL_HANDOFF": "between session-only and unrestricted; unexercised",
}

BUCKETS = {
    "core": sorted(ROOT.joinpath("gidp").rglob("*.py")),
    "examples": sorted(ROOT.joinpath("examples").glob("*.py")),
    "tests": sorted(ROOT.joinpath("tests").glob("*.py")),
    "baselines": sorted(ROOT.joinpath("baselines").glob("*.py")),
}


def _members() -> dict[str, tuple[str, str, object]]:
    found = {}
    for name in dir(vocab):
        obj = getattr(vocab, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, Enum)
            and obj.__module__ == vocab.__name__
        ):
            for member in obj:
                found[f"{obj.__name__}.{member.name}"] = (
                    obj.__name__,
                    member.name,
                    member.value,
                )
    return found


def coverage() -> dict[str, list[str]]:
    """value -> the buckets that reference it, excluding its own definition."""
    vocab_source = ROOT.joinpath("gidp/vocab.py").read_text()
    sources = {
        bucket: "\n".join(p.read_text() for p in paths)
        for bucket, paths in BUCKETS.items()
    }
    sources["core"] = sources["core"].replace(vocab_source, "")

    result = {}
    for key, (cls, member, value) in _members().items():
        where = [
            bucket
            for bucket, text in sources.items()
            if re.search(rf"\b{cls}\.{member}\b", text)
            or re.search(rf'"{re.escape(str(value))}"', text)
        ]
        result[key] = where
    return result


def unreferenced() -> list[str]:
    return sorted(key for key, where in coverage().items() if not where)


def undemonstrated() -> list[str]:
    """Referenced only where the protocol is defined or tested, never by a
    worked domain."""
    return sorted(
        key
        for key, where in coverage().items()
        if where and set(where) <= {"core", "tests"}
    )


def main() -> int:
    seen = coverage()
    print(f"{'value':<48} {'reached by'}")
    print("-" * 96)
    for key in sorted(seen):
        print(f"{key:<48} {', '.join(seen[key]) or 'NOTHING'}")

    missing = unreferenced()
    undocumented = [k for k in missing if k not in KEPT_WITHOUT_A_DEMONSTRATION]
    print()
    print(
        f"{len(seen)} values; {len(missing)} reached by nothing; "
        f"{len(undemonstrated())} never reached by a worked domain."
    )
    if undocumented:
        print()
        print(
            "Reached by nothing and unregistered — remove, or write down why they stay:"
        )
        for key in undocumented:
            print(f"  {key}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
