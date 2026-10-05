"""Read a profile manifest's qualification rules into the core.

A manifest (profiles/FORMAT.md) is data. What the core needs from it to
decide qualification is two things: the dimensions a session must have
examined, and the joint predicates that must hold. Nothing here is
specific to any vertical; a profile that needed code here would be a
profile that had weakened the core.
"""

from __future__ import annotations

from typing import Any

from .session import JointPredicate, Session


def joint_predicates(manifest: dict[str, Any]) -> list[JointPredicate]:
    return [
        JointPredicate(
            name=entry["name"],
            key=entry["wire"]["key"],
            operator=entry["wire"]["operator"],
            value_form=entry["wire"]["value"],
            satisfied_when=entry["wire"]["satisfied_when"],
        )
        for entry in manifest["qualification"].get("joint_predicates", [])
    ]


def apply_qualification(session: Session, manifest: dict[str, Any]) -> None:
    """Put a manifest's qualification rules in force for one session."""
    qualification = manifest["qualification"]
    session.required_dimensions = set(qualification["required_dimensions"])
    session.joint_predicates = joint_predicates(manifest)
