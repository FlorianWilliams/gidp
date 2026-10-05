"""The A2A binding of Section 22.2, exercised against the real mechanism.

Section 22.2 is a sketch and says so. Writing it against the published
Agent2Agent specification rather than from memory turned up three things the
sketch had wrong or missing, all recorded in `../../SPEC-ISSUES.md` as S-14,
and one question the sketch does not raise at all.

What A2A actually provides, as of its version 1.0:

*Declaration.* An agent advertises an extension in its Agent Card, under
`capabilities.extensions`, as an `AgentExtension` object with four fields:
`uri`, `description`, `required` and `params`. The sketch omitted `params`
and cited the wrong section.

*Activation.* Declaration is not activation. A client that intends to use an
extension sends the `A2A-Extensions` header carrying a comma-separated list
of extension URIs, and the server echoes back the ones it activated. An
extension nobody activated is not in force, whatever the Agent Card says.
The sketch did not mention this at all, which matters because it is the step
at which a GIDP exchange can be refused before a single GIDP object exists.

*Carriage.* Extension data travels in the `metadata` map of A2A's core
structures, under keys prefixed by the extension URI, so that extensions
cannot collide and core types are never modified.

The question the sketch does not raise: GIDP has its own negotiation.
Section 14.1 has `SessionOpen` propose features and `SessionAccept` return
the intersection actually supported. Layered on A2A there are now two
handshakes, and they are not redundant — the A2A one asks *do you speak GIDP
at all*, the GIDP one asks *which of GIDP's optional features are in force for
this session*. Conflating them is the obvious implementation mistake, and
the second is not derivable from the first: a peer may activate the
extension and still decline every optional feature.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..objects import (
    ONE_WAY_TYPES,
    REQUEST_TYPES,
    RESPONSE_TYPES,
    DiscoveryProjection,
    SessionClose,
    TransmittedObject,
)

#: Illustrative and unallocated: GIDP 0.1 mints no URI (Section 26). A real
#: deployment substitutes its own, and two deployments that choose different
#: URIs do not interoperate, which is a reason to allocate one before there
#: are two.
EXTENSION_URI = "https://gidp.dev/extensions/gidp/0.1"

#: A2A carries extension data under URI-prefixed keys in `metadata`.
OBJECT_KEY = f"{EXTENSION_URI}/object"

#: The activation header of the A2A extension mechanism.
ACTIVATION_HEADER = "A2A-Extensions"

# SessionClose and DiscoveryProjection are neither requests nor responses --
# a close discharges an outstanding request or stands alone (Section 14), and
# a projection travels to a provider rather than to a peer -- so the object
# module's three tuples do not enumerate every object that crosses a wire.
# A binding has to, or it silently cannot carry them.
_BY_TYPE = {
    model.model_fields["type"].default: model
    for model in (
        *REQUEST_TYPES,
        *RESPONSE_TYPES,
        *ONE_WAY_TYPES,
        SessionClose,
        DiscoveryProjection,
    )
}


class BindingError(Exception):
    """The message does not carry a GIDP object under this extension."""


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------


def agent_extension(
    description: str = "Graduated Interest Disclosure 0.1",
    required: bool = False,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The `AgentExtension` entry for an Agent Card's `capabilities.extensions`.

    `required` stays false: an agent that made GIDP mandatory would refuse
    every counterparty that speaks plain A2A, which is the opposite of what
    a discovery protocol is for.
    """
    entry: dict[str, Any] = {
        "uri": EXTENSION_URI,
        "description": description,
        "required": required,
    }
    if params is not None:
        entry["params"] = params
    return entry


def agent_card_capabilities(**kwargs: Any) -> dict[str, Any]:
    return {"extensions": [agent_extension(**kwargs)]}


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------


def activation_header(uris: Iterable[str] = (EXTENSION_URI,)) -> dict[str, str]:
    return {ACTIVATION_HEADER: ", ".join(uris)}


def parse_activation(headers: dict[str, str]) -> list[str]:
    """Read an activation header, case-insensitively as HTTP requires."""
    for name, value in headers.items():
        if name.lower() == ACTIVATION_HEADER.lower():
            return [uri.strip() for uri in value.split(",") if uri.strip()]
    return []


def echo_activation(headers: dict[str, str]) -> dict[str, str]:
    """What a responder that supports GIDP returns.

    It echoes only what it actually activated, which is the whole point of
    the round trip: a client cannot assume its request was honoured.
    """
    requested = parse_activation(headers)
    return activation_header([EXTENSION_URI]) if EXTENSION_URI in requested else {}


def is_active(response_headers: dict[str, str]) -> bool:
    return EXTENSION_URI in parse_activation(response_headers)


# ---------------------------------------------------------------------------
# Carriage
# ---------------------------------------------------------------------------


def to_message(obj: TransmittedObject, role: str = "agent") -> dict[str, Any]:
    """Wrap a GIDP object in an A2A Message.

    The object goes in `metadata` under a URI-prefixed key, not in a Part:
    A2A's own guidance is that an extension adds attributes to the metadata
    map rather than modifying core types, and a GIDP object is not content
    for a human to read.
    """
    return {
        "role": role,
        "parts": [],
        "metadata": {OBJECT_KEY: obj.model_dump(mode="json", exclude_none=True)},
    }


def from_message(message: dict[str, Any]) -> TransmittedObject:
    metadata = message.get("metadata") or {}
    payload = metadata.get(OBJECT_KEY)
    if payload is None:
        raise BindingError(
            f"no GIDP object under {OBJECT_KEY}; the extension may be declared "
            "but not activated"
        )
    kind = payload.get("type")
    model = _BY_TYPE.get(kind)
    if model is None:
        raise BindingError(f"unknown GIDP object type {kind!r}")
    return model.model_validate(payload)
