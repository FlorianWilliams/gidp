"""Protocol objects of GIDP 0.1, Section 14, plus the local objects of 9-11.

Field names follow the specification exactly. Required fields are required
here; where the specification leaves a field optional it is optional here.

Two conventions worth stating because they are enforced below:

* Every transmitted object carries ``type``, ``version`` and ``expires_at``,
  and every object except ``DiscoveryProjection`` carries ``session_id``.
* Request-type objects carry ``request_id``; response-type objects carry
  ``request_ref``. The sets are named in Section 14 and are reproduced in
  ``REQUEST_TYPES`` / ``RESPONSE_TYPES`` at the end of this module.

The Standing Interest and the Disclosure Policy are *not* transmitted. They
are modelled here because the Agent needs them, and modelling them in the same
place makes it obvious which objects may cross the wire and which may not:
only subclasses of ``TransmittedObject`` may.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .vocab import (
    VERSION,
    Authority,
    AuthorityValue,
    ClaimOperator,
    ClaimResult,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    DisclosureStatus,
    Feature,
    Gate,
    HandoffKind,
    IdentityStatus,
    IntendedUse,
    NextAction,
    Retention,
    SessionStatus,
    Surface,
)


class Strict(BaseModel):
    """Base model: unknown fields are an error rather than silently dropped.

    An implementation that accepts unknown fields cannot detect a peer using a
    vocabulary GIDP 0.1 froze (Section 26), so extra fields are forbidden.
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)


# --------------------------------------------------------------------------
# Local objects: never transmitted (Sections 9, 10, 11)
# --------------------------------------------------------------------------


class DisclosureClass(Strict):
    """A (surface, gate) pair assigned to one attribute (Section 10.3)."""

    surface: Surface
    gate: Gate = Gate.NONE

    def __str__(self) -> str:  # "session/principal_approval", "discovery"
        if self.gate is Gate.NONE:
            return self.surface.value
        return f"{self.surface.value}/{self.gate.value}"

    @property
    def transmittable(self) -> bool:
        return self.surface is not Surface.LOCAL


#: An attribute with no explicit policy entry is treated as evaluation-only,
#: i.e. usable for local evaluation and never transmitted (Section 9.1).
EVALUATION_ONLY = DisclosureClass(surface=Surface.LOCAL, gate=Gate.NONE)


class DisclosurePolicy(Strict):
    """Per-attribute disclosure rules (Section 10). Local, never transmitted."""

    attributes: dict[str, DisclosureClass] = Field(default_factory=dict)
    #: Section 9.1: this is the only permitted default.
    default: Literal["evaluation_only"] = "evaluation_only"

    def class_for(self, attribute: str) -> DisclosureClass:
        return self.attributes.get(attribute, EVALUATION_ONLY)


class ConditionalInterest(Strict):
    """Section 8. Held inside a Standing Interest; never transmitted."""

    action: str
    object: str | None = None
    structures: list[str] = Field(default_factory=list)
    #: Attribute name -> value. Whether a value may leave the Agent is decided
    #: by the Disclosure Policy, never by this object.
    conditions: dict[str, Any] = Field(default_factory=dict)
    #: Attribute -> {child: parent}. The hierarchy this Principal's own values
    #: belong to, used to answer a claim expressed at a different level
    #: (Section 14.2). It lives inside the Standing Interest, so it is never
    #: transmitted and needs no agreement with anyone: evaluation happens on
    #: the responder's side, so only the responder's own values need placing.
    taxonomies: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Dependency primitives (Section 19.1). Only `excludes` must be supported
    # by every implementation; the rest require the dependency_primitives
    # feature.
    provides: list[str] = Field(default_factory=list)
    requires: list[str] = Field(default_factory=list)
    conditional_on: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)


class AuthoritySpec(Strict):
    """Authority levels for one Standing Interest (Section 16.1)."""

    levels: dict[Authority, AuthorityValue] = Field(default_factory=dict)
    #: Section 16.2: an asserted level must be capable of being evidenced by a
    #: referenceable delegation artefact. ``None`` means unevidenced, and a
    #: counterparty is free to treat an unevidenced assertion as absent.
    evidence_ref: str | None = None

    @model_validator(mode="after")
    def _commit_is_false(self) -> AuthoritySpec:
        value = self.levels.get(Authority.COMMIT, AuthorityValue.FALSE)
        if value is not AuthorityValue.FALSE:
            raise ValueError(
                f"COMMIT MUST be false in GIDP 0.1 (Section 16.1); got {value.value!r}"
            )
        self.levels[Authority.COMMIT] = AuthorityValue.FALSE
        return self

    def value(self, level: Authority) -> AuthorityValue:
        return self.levels.get(level, AuthorityValue.FALSE)

    def permits(self, level: Authority) -> bool:
        return self.value(level) is AuthorityValue.TRUE

    def needs_approval(self, level: Authority) -> bool:
        return self.value(level) is AuthorityValue.APPROVAL_REQUIRED


class Validity(Strict):
    not_before: datetime | None = None
    expires_at: datetime | None = None


class StandingInterest(Strict):
    """The delegation container (Section 9). MUST NOT be transmitted."""

    id: str
    version: int = 1
    principal_ref: str
    interest: ConditionalInterest
    disclosure_policy: DisclosurePolicy = Field(default_factory=DisclosurePolicy)
    authority: AuthoritySpec = Field(default_factory=AuthoritySpec)
    validity: Validity = Field(default_factory=Validity)
    #: Set when the interest was inferred rather than authored, and cleared by
    #: the Principal's confirmation (Section 9.4).
    confirmed_by_principal: bool = True

    def value_of(self, attribute: str) -> Any:
        return self.interest.conditions.get(attribute)

    def class_of(self, attribute: str) -> DisclosureClass:
        return self.disclosure_policy.class_for(attribute)


# --------------------------------------------------------------------------
# Transmitted objects (Section 14)
# --------------------------------------------------------------------------


class TransmittedObject(Strict):
    """Anything that may cross the wire.

    Section 14: every transmitted object carries ``type``, ``version`` and
    ``expires_at``; every one except DiscoveryProjection carries
    ``session_id``.
    """

    version: Literal["gidp/0.1"] = VERSION
    expires_at: datetime


class SessionScoped(TransmittedObject):
    session_id: str


class Request(SessionScoped):
    """Request-type object: carries a session-unique ``request_id``."""

    request_id: str


class Response(SessionScoped):
    """Response-type object: carries the ``request_ref`` it answers."""

    request_ref: str


class DiscoveryProjection(TransmittedObject):
    """Section 11. The only object published to a Discovery Provider.

    ``type``, ``version``, ``expires_at``, ``projection_id`` and ``endpoint``
    are protocol metadata: they are not derived from the Standing Interest and
    are not subject to the content rule of Section 11.2.
    """

    type: Literal["DiscoveryProjection"] = "DiscoveryProjection"
    projection_id: str
    endpoint: str
    #: Opaque, resolvable only by the publishing Agent (Section 11.1).
    interest_ref: str | None = None
    categories: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    geographies: list[str] = Field(default_factory=list)
    #: Symmetric role; the core profile defines only
    #: ``complementary_counterparty``, which asserts nothing about direction.
    relation: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _at_least_one_retrieval_attribute(self) -> DiscoveryProjection:
        if not (self.categories or self.domains or self.geographies or self.relation):
            raise ValueError(
                "a projection MUST carry at least one retrieval attribute "
                "(Section 11.1)"
            )
        return self


class SessionOpen(Request):
    type: Literal["SessionOpen"] = "SessionOpen"
    initiator: str
    purpose: str
    #: How far into its Disclosure Policy the initiator will go in this
    #: session, named by the least exposed surface it will disclose here.
    max_depth: Surface
    profile: str
    features: list[Feature] = Field(default_factory=list)
    trust_context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _depth_is_permitted(self) -> SessionOpen:
        if self.max_depth not in (Surface.NETWORK, Surface.SESSION):
            raise ValueError(
                "max_depth MUST be 'network' or 'session' (Section 14.1); "
                f"got {self.max_depth.value!r}"
            )
        return self


class SessionAccept(Response):
    type: Literal["SessionAccept"] = "SessionAccept"
    responder: str
    max_depth: Surface
    profile: str
    features: list[Feature] = Field(default_factory=list)


class Claim(Strict):
    """One question about one dimension (Section 14.2)."""

    key: str
    operator: ClaimOperator
    value: Any


class ClaimOutcome(Strict):
    key: str
    result: ClaimResult


class CompatibilityRequest(Request):
    type: Literal["CompatibilityRequest"] = "CompatibilityRequest"
    claims: list[Claim]
    allowed_results: list[ClaimResult] = Field(default_factory=list)


class NextBlock(Strict):
    permitted: list[NextAction] = Field(default_factory=list)
    #: Attribute keys whose disclosure would resolve a requires_disclosure
    #: result. MAY be empty.
    requires: list[str] = Field(default_factory=list)


class CompatibilityResponse(Response):
    type: Literal["CompatibilityResponse"] = "CompatibilityResponse"
    results: list[ClaimOutcome]
    session_status: SessionStatus
    next: NextBlock = Field(default_factory=NextBlock)


class DisclosureRequest(Request):
    type: Literal["DisclosureRequest"] = "DisclosureRequest"
    attribute: str
    purpose: str
    requested_surface: Surface
    intended_use: IntendedUse
    retention: Retention | None = None
    reciprocal: bool = False


class DisclosureResponse(Response):
    type: Literal["DisclosureResponse"] = "DisclosureResponse"
    attribute: str
    status: DisclosureStatus
    value: Any | None = None
    #: Required when status is granted_if_verified (Section 14.4).
    verification_required: list[str] | None = None

    @model_validator(mode="after")
    def _status_consistency(self) -> DisclosureResponse:
        if self.status is DisclosureStatus.GRANTED and self.value is None:
            raise ValueError("a granted DisclosureResponse carries a value (14.4)")
        if self.status is not DisclosureStatus.GRANTED and self.value is not None:
            raise ValueError(
                "only a granted DisclosureResponse carries a value (14.4); "
                f"status was {self.status.value!r}"
            )
        if self.status is DisclosureStatus.GRANTED_IF_VERIFIED and not (
            self.verification_required
        ):
            raise ValueError(
                "granted_if_verified MUST carry a non-empty "
                "verification_required (Section 14.4)"
            )
        return self


class ConsentRequest(Request):
    type: Literal["ConsentRequest"] = "ConsentRequest"
    action: ConsentAction
    scope: list[str] = Field(default_factory=list)
    reciprocal: bool = False
    #: MUST be false in GIDP 0.1. The field is required rather than omitted so
    #: that the absence of commitment is explicit on the wire (Section 14.5).
    binding_commitment: Literal[False] = False


class ConsentResponse(Response):
    type: Literal["ConsentResponse"] = "ConsentResponse"
    status: ConsentStatus
    granted_scope: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _scope_empty_unless_granted(self) -> ConsentResponse:
        if self.status is not ConsentStatus.GRANTED and self.granted_scope:
            raise ValueError(
                "granted_scope is empty when consent is not granted (14.5)"
            )
        return self


class Opportunity(SessionScoped):
    """One-way notification produced on PROBING -> QUALIFIED (Section 14.6)."""

    type: Literal["Opportunity"] = "Opportunity"
    structure: str
    evaluated_dimensions: int
    compatible_dimensions: int
    #: Claim keys whose most recent result is conditionally_compatible.
    open_conditions: list[str] = Field(default_factory=list)
    #: Dependencies named in either side's `conditional_on` that the session
    #: did not resolve (Section 14.6). A non-empty list means the Opportunity
    #: is contingent on something outside it -- typically a third party that
    #: bilateral discovery cannot find.
    contingent_on: list[str] = Field(default_factory=list)
    identity_status: dict[str, IdentityStatus] = Field(default_factory=dict)


class HandoffTarget(Strict):
    kind: HandoffKind
    protocol_ref: str | None = None

    @model_validator(mode="after")
    def _protocol_ref_required(self) -> HandoffTarget:
        if self.kind is HandoffKind.PROTOCOL and not self.protocol_ref:
            raise ValueError("protocol_ref is REQUIRED when kind is 'protocol' (14.7)")
        return self


class Handoff(SessionScoped):
    """One-way notification; ends GIDP's responsibility (Section 14.7)."""

    type: Literal["Handoff"] = "Handoff"
    target: HandoffTarget
    authorized_scope: list[Authority] = Field(default_factory=list)
    requires_principal_presence: bool = True

    @model_validator(mode="after")
    def _never_commit(self) -> Handoff:
        if Authority.COMMIT in self.authorized_scope:
            raise ValueError(
                "authorized_scope never includes COMMIT in GIDP 0.1 (Section 14.7)"
            )
        return self


class SessionClose(SessionScoped):
    """Section 14.8. Carries request_ref only when sent in place of a response."""

    type: Literal["SessionClose"] = "SessionClose"
    reason: CloseReason
    request_ref: str | None = None


REQUEST_TYPES = (SessionOpen, CompatibilityRequest, DisclosureRequest, ConsentRequest)
RESPONSE_TYPES = (
    SessionAccept,
    CompatibilityResponse,
    DisclosureResponse,
    ConsentResponse,
)
ONE_WAY_TYPES = (Opportunity, Handoff)

AnyMessage = Annotated[
    SessionOpen
    | SessionAccept
    | CompatibilityRequest
    | CompatibilityResponse
    | DisclosureRequest
    | DisclosureResponse
    | ConsentRequest
    | ConsentResponse
    | Opportunity
    | Handoff
    | SessionClose,
    Field(discriminator="type"),
]
