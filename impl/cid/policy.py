"""The Disclosure Policy engine (Sections 10, 11, 14.1).

This module is deliberately separable from everything else: given a Standing
Interest, a session depth and a request, it decides what may leave the Agent,
and it decides it the same way every time. Conformance criterion 3 of Section
23.2 -- that the decision to transmit an object be reproducible from the
Standing Interest, the Disclosure Policy and the session state alone -- is
testable precisely because nothing here consults anything else.

Nothing in this module asks a model, a network or a clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .objects import DisclosureClass, DiscoveryProjection, StandingInterest
from .vocab import Gate, Surface


def effective_depth(initiator: Surface, responder: Surface) -> Surface:
    """The depth in force for a session: the shallower of the two (14.1)."""
    return initiator if initiator.depth <= responder.depth else responder


@dataclass(frozen=True)
class DisclosureDecision:
    """Why an attribute may or may not be disclosed. Explanations are for the
    local audit trail (Section 25.3), never for the counterparty: telling a
    peer *why* it was refused is itself a disclosure (Section 18)."""

    permitted: bool
    reason: str
    needs_consent: bool = False
    needs_principal_approval: bool = False


@dataclass
class SessionConsents:
    """Consent granted by this side, in this session (Section 10.2)."""

    granted_attributes: set[str] = field(default_factory=set)
    approved_attributes: set[str] = field(default_factory=set)

    def has_consent(self, attribute: str) -> bool:
        return attribute in self.granted_attributes

    def has_principal_approval(self, attribute: str) -> bool:
        return attribute in self.approved_attributes


def evaluate_disclosure(
    standing_interest: StandingInterest,
    attribute: str,
    session_depth: Surface,
    consents: SessionConsents,
) -> DisclosureDecision:
    """Decide whether ``attribute`` may be disclosed in this session.

    The order of the tests matters and follows the specification: the surface
    decides whether the attribute may be transmitted at all (10.1), the session
    depth caps how deep either side agreed to go (14.1), and the gate decides
    what must have happened first (10.2).
    """
    cls: DisclosureClass = standing_interest.class_of(attribute)

    if cls.surface is Surface.LOCAL:
        return DisclosureDecision(
            False,
            "attribute is evaluation-only and MUST NOT be transmitted (9.1, 10.1)",
        )

    if cls.surface.deeper_than(session_depth):
        return DisclosureDecision(
            False,
            f"attribute surface {cls.surface.value!r} is deeper than the session "
            f"depth {session_depth.value!r} (14.1)",
        )

    if cls.gate is Gate.CONSENT and not consents.has_consent(attribute):
        return DisclosureDecision(
            False,
            "gate 'consent' is not satisfied for this session (10.2)",
            needs_consent=True,
        )

    if cls.gate is Gate.PRINCIPAL_APPROVAL and not consents.has_principal_approval(
        attribute
    ):
        return DisclosureDecision(
            False,
            "gate 'principal_approval' requires a per-instance decision (10.2)",
            needs_principal_approval=True,
        )

    return DisclosureDecision(True, f"permitted at {cls}")


# --------------------------------------------------------------------------
# Discovery Projection derivation (Section 11)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalAttribute:
    """One retrieval attribute of a projection, and where it comes from.

    ``coarsen`` implements Section 11.4: generalise geography, bucket economic
    ranges, replace direction-revealing attributes with symmetric ones. It is
    supplied by the profile or the deployment, never by this module, because
    the right coarsening depends on the population being hidden in.
    """

    projection_field: str
    source_attribute: str | None
    coarsen: Callable[[Any], list[str]]


class ProjectionRuleViolation(Exception):
    """Raised when a derivation would breach the content rule of 11.2."""


def derive_projection(
    standing_interest: StandingInterest,
    *,
    projection_id: str,
    endpoint: str,
    expires_at,
    interest_ref: str | None,
    attributes: Iterable[RetrievalAttribute],
    inside_trust_domain: bool = False,
) -> DiscoveryProjection:
    """Derive a projection, enforcing the content rule as it goes.

    Section 11.2: a projection submitted to a provider outside any authorised
    trust domain MUST contain only attributes, or explicitly policied
    derivatives, of surface ``public`` or ``discovery``; inside an authorised
    trust domain it MAY additionally contain ``network`` attributes. A
    projection MUST NOT contain Principal identity.

    Rather than filter silently, a source attribute whose class forbids
    publication raises: silent filtering hides a policy error from the author
    of the policy, which is exactly how an interest leaks in production.
    """
    permitted = {Surface.PUBLIC, Surface.DISCOVERY}
    if inside_trust_domain:
        permitted.add(Surface.NETWORK)

    fields: dict[str, list[str]] = {
        "categories": [],
        "domains": [],
        "geographies": [],
        "relation": [],
    }

    for attr in attributes:
        if attr.projection_field not in fields:
            raise ProjectionRuleViolation(
                f"{attr.projection_field!r} is not a core-profile retrieval "
                "attribute (Section 11.1)"
            )
        if attr.source_attribute is None:
            fields[attr.projection_field].extend(attr.coarsen(None))
            continue

        cls = standing_interest.class_of(attr.source_attribute)
        if cls.surface not in permitted:
            raise ProjectionRuleViolation(
                f"{attr.source_attribute!r} is classified {cls} and may not be "
                f"published to this provider (Section 11.2)"
            )
        value = standing_interest.value_of(attr.source_attribute)
        fields[attr.projection_field].extend(attr.coarsen(value))

    if interest_ref is not None and interest_ref == standing_interest.id:
        raise ProjectionRuleViolation(
            "interest_ref MUST be opaque and resolvable only by the publishing "
            "Agent (Section 11.1); the Standing Interest id is not opaque"
        )

    return DiscoveryProjection(
        projection_id=projection_id,
        endpoint=endpoint,
        interest_ref=interest_ref,
        expires_at=expires_at,
        **fields,
    )
