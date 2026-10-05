"""Closed vocabularies of GIDP 0.1.

Section 26 of the specification freezes these vocabularies for version 0.1:
an implementation MUST NOT add values to them. Defining them once, here, as
enumerations means the freeze is enforced by the type system and does not
depend on prose. The two intended extension points, domain profiles and future
versions of the specification, live outside this module.

Every name below is spelled as the specification spells it.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

#: Object version token: the protocol's acronym in lower case (GIDP 0.1
#: Section 14).
VERSION: Final = "gidp/0.1"

PROFILE_CORE = "core"


class Surface(str, Enum):
    """Where an attribute, or a coarsened derivative of it, may appear.

    Section 10.1. Totally ordered from most to least exposed. Note the
    consequence, which is a frequent source of confusion: an attribute
    classified ``session`` is *more* sensitive than one classified
    ``network``, because fewer places may carry it.
    """

    PUBLIC = "public"
    DISCOVERY = "discovery"
    NETWORK = "network"
    SESSION = "session"
    LOCAL = "local"

    @property
    def depth(self) -> int:
        """Position in the ordering; larger means less exposed, i.e. deeper."""
        return _SURFACE_DEPTH[self]

    def deeper_than(self, other: Surface) -> bool:
        return self.depth > other.depth


_SURFACE_DEPTH = {
    Surface.PUBLIC: 0,
    Surface.DISCOVERY: 1,
    Surface.NETWORK: 2,
    Surface.SESSION: 3,
    Surface.LOCAL: 4,
}

#: Values ``max_depth`` may take in SessionOpen / SessionAccept (Section 14.1).
#: ``local`` is never permitted: local attributes are never transmitted.
PERMITTED_SESSION_DEPTHS = (Surface.NETWORK, Surface.SESSION)


class Gate(str, Enum):
    """A condition that must hold before an attribute is disclosed (10.2)."""

    NONE = "none"
    CONSENT = "consent"
    PRINCIPAL_APPROVAL = "principal_approval"


class ClaimResult(str, Enum):
    """Per-claim results (Section 15.1).

    ``CONDITIONALLY_COMPATIBLE`` and ``UNKNOWN`` are non-committal by
    definition: they assert neither that the claim holds nor that it fails,
    which is what makes the coarsening rule of 15.5 truthful.
    """

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    CONDITIONALLY_COMPATIBLE = "conditionally_compatible"
    UNKNOWN = "unknown"
    REQUIRES_DISCLOSURE = "requires_disclosure"
    DECLINED = "declined"


#: The results a responder may substitute for a truthful answer in order to
#: limit inference (Section 15.5). These are the *only* permitted deviations.
PERMITTED_COARSENINGS = (
    ClaimResult.CONDITIONALLY_COMPATIBLE,
    ClaimResult.UNKNOWN,
    ClaimResult.DECLINED,
)


class SessionStatus(str, Enum):
    """Session status (Section 15.2)."""

    OPEN = "open"
    POTENTIALLY_COMPATIBLE = "potentially_compatible"
    INCOMPATIBLE = "incompatible"
    CLOSED = "closed"


class Authority(str, Enum):
    """Authority levels, least to most consequential (Section 16.1)."""

    OBSERVE = "OBSERVE"
    SEARCH = "SEARCH"
    PUBLISH_PROJECTION = "PUBLISH_PROJECTION"
    PROBE = "PROBE"
    DISCLOSE = "DISCLOSE"
    INTRODUCE = "INTRODUCE"
    NEGOTIATE_NONBINDING = "NEGOTIATE_NONBINDING"
    COMMIT = "COMMIT"


class AuthorityValue(str, Enum):
    """Value an authority level may take (Section 16.1)."""

    TRUE = "true"
    FALSE = "false"
    APPROVAL_REQUIRED = "approval_required"


class CloseReason(str, Enum):
    """SessionClose reasons (Section 14.8)."""

    DECLINED = "declined"
    INCOMPATIBLE = "incompatible"
    UNSUPPORTED = "unsupported"
    EXPIRED = "expired"
    COMPLETED = "completed"
    UNSPECIFIED = "unspecified"


class ConsentAction(str, Enum):
    """Actions consent may cover (Section 14.5)."""

    DISCLOSE_ATTRIBUTES = "disclose_attributes"
    REVEAL_IDENTITY = "reveal_identity"
    ESTABLISH_DIRECT_CONTACT = "establish_direct_contact"
    HANDOFF = "handoff"


#: Mapping from a consent action to the authority level that governs it
#: (Section 14.5). ``handoff`` maps to INTRODUCE because a Handoff establishes
#: a direct relationship between the Principals.
CONSENT_ACTION_AUTHORITY = {
    ConsentAction.DISCLOSE_ATTRIBUTES: Authority.DISCLOSE,
    ConsentAction.REVEAL_IDENTITY: Authority.INTRODUCE,
    ConsentAction.ESTABLISH_DIRECT_CONTACT: Authority.INTRODUCE,
    ConsentAction.HANDOFF: Authority.INTRODUCE,
}


class ConsentStatus(str, Enum):
    GRANTED = "granted"
    DECLINED = "declined"
    PENDING_PRINCIPAL_APPROVAL = "pending_principal_approval"


class DisclosureStatus(str, Enum):
    """DisclosureResponse statuses (Section 14.4)."""

    GRANTED = "granted"
    DECLINED = "declined"
    GRANTED_IF_RECIPROCAL = "granted_if_reciprocal"
    GRANTED_IF_VERIFIED = "granted_if_verified"
    PENDING_PRINCIPAL_APPROVAL = "pending_principal_approval"


#: Statuses that make a response *provisional*: the request is not discharged
#: and exactly one further response with the same request_ref must follow
#: (Section 14).
PROVISIONAL_DISCLOSURE_STATUSES = (
    DisclosureStatus.PENDING_PRINCIPAL_APPROVAL,
    DisclosureStatus.GRANTED_IF_RECIPROCAL,
    DisclosureStatus.GRANTED_IF_VERIFIED,
)


class IntendedUse(str, Enum):
    COMPATIBILITY_EVALUATION = "compatibility_evaluation"
    IDENTITY_VERIFICATION = "identity_verification"
    HANDOFF_PREPARATION = "handoff_preparation"


class Retention(str, Enum):
    SESSION_ONLY = "session_only"
    UNTIL_HANDOFF = "until_handoff"
    UNRESTRICTED = "unrestricted"


class NextAction(str, Enum):
    """Values of ``next.permitted`` in a CompatibilityResponse (14.3)."""

    COMPATIBILITY_REQUEST = "compatibility_request"
    DISCLOSURE_REQUEST = "disclosure_request"
    CONSENT_REQUEST = "consent_request"
    HANDOFF = "handoff"
    CLOSE = "close"


class Feature(str, Enum):
    """Optional features declared in SessionOpen (Section 14.1)."""

    DEPENDENCY_PRIMITIVES = "dependency_primitives"
    MULTI_PARTY = "multi_party"


class ClaimOperator(str, Enum):
    """Core claim operators (Section 14.2). Profiles MAY add operators."""

    EQUALS = "equals"
    INTERSECTS = "intersects"
    OVERLAPS = "overlaps"
    COMPATIBLE_WITH = "compatible_with"


class SessionState(str, Enum):
    """States of the session state machine (Section 17.2)."""

    REQUESTED = "REQUESTED"
    PROBING = "PROBING"
    DISCLOSURE_PENDING = "DISCLOSURE_PENDING"
    QUALIFIED = "QUALIFIED"
    CONSENT_PENDING = "CONSENT_PENDING"
    CONSENTED = "CONSENTED"
    HANDED_OFF = "HANDED_OFF"
    CLOSED = "CLOSED"


class IdentityStatus(str, Enum):
    """Per-side identity status carried in an Opportunity (Section 14.6)."""

    NOT_REQUESTED = "not_requested"
    PENDING_PRINCIPAL_APPROVAL = "pending_principal_approval"
    GRANTED = "granted"
    DECLINED = "declined"


class HandoffKind(str, Enum):
    HUMAN = "human"
    WORKFLOW = "workflow"
    PROTOCOL = "protocol"
