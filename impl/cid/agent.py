"""An Agent acting under a Standing Interest (Sections 3, 13-18).

The Agent composes the other modules and adds nothing of its own to the
protocol semantics: evaluation lives in ``evaluation``, what may leave lives
in ``policy``, and what may happen next lives in ``session``. That separation
is what makes conformance criterion 3 testable -- replay the same Standing
Interest, policy and session state, and the same objects come out.

Abuse controls (Section 24.3) are represented by a query budget. It is a
deliberately crude mitigation, and ``examples/probing.py`` measures how crude:
a budget is what an implementer must set, and this implementation exists partly
to give them a number rather than an intuition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Iterable

from .evaluation import LocalEvaluation, choose_result, evaluate_claim
from .objects import (
    Claim,
    ClaimOutcome,
    CompatibilityRequest,
    CompatibilityResponse,
    ConsentRequest,
    ConsentResponse,
    DisclosureRequest,
    DisclosureResponse,
    Handoff,
    HandoffTarget,
    NextBlock,
    SessionAccept,
    SessionClose,
    SessionOpen,
    StandingInterest,
)
from .policy import SessionConsents, effective_depth, evaluate_disclosure
from .session import ProtocolError, Session
from .vocab import (
    PROFILE_CORE,
    Authority,
    AuthorityValue,
    ClaimResult,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    CONSENT_ACTION_AUTHORITY,
    DisclosureStatus,
    Feature,
    Gate,
    HandoffKind,
    IntendedUse,
    NextAction,
    Retention,
    Surface,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _soon(minutes: int = 15) -> datetime:
    return _now() + timedelta(minutes=minutes)


@dataclass
class AuditEntry:
    """One line of the local audit trail (Section 25.3).

    Note what is *not* here: the value of any `local` attribute. Section 25.3
    forbids recording those in plaintext outside the Agent, and an audit trail
    is itself highly sensitive.
    """

    event: str
    detail: str


@dataclass
class Agent:
    """An Agent holding one Standing Interest."""

    ref: str
    standing_interest: StandingInterest
    #: Claims answered in this session, against the budget of Section 24.3.
    query_budget: int = 20
    #: Attributes the Principal has approved in advance, for demonstration
    #: purposes. A real deployment asks a human (Section 10.2).
    pre_approved: set[str] = field(default_factory=set)
    #: Optional features this implementation supports (Section 14.1). The
    #: bilateral core is implied and is never declared. Section 19.1: only
    #: `excludes` must be supported by every implementation; `provides`,
    #: `requires` and `conditional_on` require this feature.
    supported_features: set[Feature] = field(
        default_factory=lambda: {Feature.DEPENDENCY_PRIMITIVES}
    )

    session: Session | None = None
    consents: SessionConsents = field(default_factory=SessionConsents)
    audit: list[AuditEntry] = field(default_factory=list)
    queries_answered: int = 0
    _ids: Any = field(default_factory=lambda: count(1))

    # -- helpers -----------------------------------------------------------

    def _rid(self) -> str:
        return f"r-{next(self._ids)}"

    def _log(self, event: str, detail: str) -> None:
        self.audit.append(AuditEntry(event, detail))

    def _authority(self, level: Authority) -> AuthorityValue:
        return self.standing_interest.authority.value(level)

    # -- session establishment --------------------------------------------

    def open_session(
        self,
        session_id: str,
        purpose: str,
        max_depth: Surface = Surface.SESSION,
        features: Iterable[Feature] = (),
    ) -> SessionOpen:
        if self._authority(Authority.PROBE) is AuthorityValue.FALSE:
            raise ProtocolError("PROBE authority is false; cannot open a session (16)")
        self.session = Session(
            session_id=session_id,
            is_initiator=True,
            profile=PROFILE_CORE,
            max_depth=max_depth,
        )
        message = SessionOpen(
            session_id=session_id,
            request_id=self._rid(),
            initiator=self.ref,
            purpose=purpose,
            max_depth=max_depth,
            profile=PROFILE_CORE,
            features=list(features),
            expires_at=_soon(),
        )
        self.session.open(message)
        self.session.note_dependency(*self.standing_interest.interest.conditional_on)
        self._log("session_open", f"purpose={purpose} max_depth={max_depth.value}")
        return message

    def handle_session_open(self, message: SessionOpen) -> SessionAccept | SessionClose:
        if message.profile != PROFILE_CORE:
            # Section 21: a responder that does not implement the declared
            # profile closes with reason 'unsupported' and does not propose an
            # alternative.
            return SessionClose(
                session_id=message.session_id,
                reason=CloseReason.UNSUPPORTED,
                request_ref=message.request_id,
                expires_at=_soon(),
            )

        depth = effective_depth(message.max_depth, Surface.SESSION)
        # Section 14.1: SessionAccept carries the features actually supported,
        # which is the intersection -- not an echo of what was asked for.
        agreed = sorted(
            set(message.features) & self.supported_features, key=lambda f: f.value
        )
        self.session = Session(
            session_id=message.session_id,
            is_initiator=False,
            profile=PROFILE_CORE,
            max_depth=depth,
            features=set(agreed),
        )
        self.session.open(message)
        accept = SessionAccept(
            session_id=message.session_id,
            request_ref=message.request_id,
            responder=self.ref,
            max_depth=depth,
            profile=PROFILE_CORE,
            features=list(agreed),
            expires_at=_soon(),
        )
        self.session.accept(accept)
        self.session.note_dependency(*self.standing_interest.interest.conditional_on)
        self._log(
            "session_accept",
            f"depth in force={depth.value}; features="
            f"{', '.join(f.value for f in agreed) or 'core only'}",
        )
        return accept

    def confirm_accept(self, accept: SessionAccept) -> None:
        assert self.session is not None
        self.session.max_depth = effective_depth(self.session.max_depth, accept.max_depth)
        self.session.features = set(accept.features)
        self.session.accept(accept)
        self._log("session_confirmed", f"depth in force={self.session.max_depth.value}")

    # -- probing -----------------------------------------------------------

    def ask(self, claims: list[Claim]) -> CompatibilityRequest:
        assert self.session is not None
        request = CompatibilityRequest(
            session_id=self.session.session_id,
            request_id=self._rid(),
            claims=claims,
            allowed_results=list(ClaimResult),
            expires_at=_soon(),
        )
        self.session.register_request(request.request_id, request.type)
        self._log("compatibility_request", ", ".join(c.key for c in claims))
        return request

    def handle_compatibility_request(
        self, request: CompatibilityRequest
    ) -> CompatibilityResponse | SessionClose:
        assert self.session is not None

        if self._authority(Authority.PROBE) is AuthorityValue.FALSE:
            return SessionClose(
                session_id=self.session.session_id,
                reason=CloseReason.DECLINED,
                request_ref=request.request_id,
                expires_at=_soon(),
            )

        self.session.note_compatibility()
        outcomes: list[ClaimOutcome] = []
        requires: list[str] = []

        for claim in request.claims:
            self.queries_answered += 1
            over_budget = self.queries_answered > self.query_budget
            evaluation = evaluate_claim(self.standing_interest, claim)
            result = self._answer(evaluation, over_budget=over_budget)
            outcomes.append(ClaimOutcome(key=claim.key, result=result))
            if claim.key == "conditional_on" and result is ClaimResult.COMPATIBLE:
                # The responder has confirmed it holds this dependency. The
                # session cannot resolve it, so it travels with the
                # Opportunity (Section 14.6).
                values = claim.value if isinstance(claim.value, list) else [claim.value]
                self.session.note_dependency(*[str(v) for v in values])
            if result is ClaimResult.REQUIRES_DISCLOSURE:
                requires.append(claim.key)
            self._log(
                "claim_answered",
                f"{claim.key} -> {result.value}"
                + (" [budget exhausted]" if over_budget else ""),
            )

        self.session.record_results(outcomes)
        self.session.outstanding_requires = set(requires)

        return CompatibilityResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            results=outcomes,
            session_status=self.session.status(),
            next=NextBlock(
                permitted=[
                    NextAction.COMPATIBILITY_REQUEST,
                    NextAction.DISCLOSURE_REQUEST,
                    NextAction.CONSENT_REQUEST,
                    NextAction.CLOSE,
                ],
                requires=requires,
            ),
            expires_at=_soon(),
        )

    def _answer(self, evaluation: LocalEvaluation, *, over_budget: bool) -> ClaimResult:
        """Decide what to say, within Section 15.5.

        The default policy: coarsen whenever the value consulted is
        evaluation-only and the truthful answer is affirmative, which is the
        canonical case of Section 15.4 -- a private threshold answered without
        being transmitted. Once the query budget is exhausted, decline.
        """
        if over_budget:
            return choose_result(evaluation, decline=True)
        coarsen = evaluation.evaluation_only and evaluation.truth is True
        return choose_result(evaluation, coarsen=coarsen)

    def receive_compatibility_response(
        self, response: CompatibilityResponse, request: CompatibilityRequest | None = None
    ) -> None:
        assert self.session is not None
        self.session.record_compatibility(response)
        if request is None:
            return
        # Mirror of the responder's bookkeeping: a confirmed dependency is
        # unresolved for both sides (Section 14.6).
        by_key = {claim.key: claim for claim in request.claims}
        for outcome in response.results:
            if outcome.key == "conditional_on" and outcome.result is ClaimResult.COMPATIBLE:
                claim = by_key.get("conditional_on")
                if claim is None:
                    continue
                values = claim.value if isinstance(claim.value, list) else [claim.value]
                self.session.note_dependency(*[str(v) for v in values])

    # -- disclosure --------------------------------------------------------

    def request_disclosure(
        self,
        attribute: str,
        purpose: str,
        *,
        requested_surface: Surface = Surface.SESSION,
        intended_use: IntendedUse = IntendedUse.COMPATIBILITY_EVALUATION,
        retention: Retention | None = Retention.SESSION_ONLY,
        reciprocal: bool = True,
    ) -> DisclosureRequest:
        assert self.session is not None
        request = DisclosureRequest(
            session_id=self.session.session_id,
            request_id=self._rid(),
            attribute=attribute,
            purpose=purpose,
            requested_surface=requested_surface,
            intended_use=intended_use,
            retention=retention,
            reciprocal=reciprocal,
            expires_at=_soon(),
        )
        self.session.register_request(request.request_id, request.type)
        self.session.begin_disclosure()
        self._log("disclosure_request", f"{attribute} ({purpose})")
        return request

    def handle_disclosure_request(
        self, request: DisclosureRequest
    ) -> DisclosureResponse:
        assert self.session is not None
        self.session.begin_disclosure()

        if self._authority(Authority.DISCLOSE) is AuthorityValue.FALSE:
            # Section 18: an authority refusal is reported as 'declined',
            # never as the operational outcome 'unauthorized'.
            return self._declined(request, "DISCLOSE authority is false")

        decision = evaluate_disclosure(
            self.standing_interest,
            request.attribute,
            self.session.max_depth,
            self.consents,
        )

        if decision.needs_principal_approval:
            if request.attribute in self.pre_approved:
                self.consents.approved_attributes.add(request.attribute)
                decision = evaluate_disclosure(
                    self.standing_interest,
                    request.attribute,
                    self.session.max_depth,
                    self.consents,
                )
            else:
                self._log("disclosure_pending", request.attribute)
                return DisclosureResponse(
                    session_id=self.session.session_id,
                    request_ref=request.request_id,
                    attribute=request.attribute,
                    status=DisclosureStatus.PENDING_PRINCIPAL_APPROVAL,
                    expires_at=_soon(),
                )

        if not decision.permitted:
            return self._declined(request, decision.reason)

        value = self.standing_interest.value_of(request.attribute)
        if value is None:
            # Section 14.4: a declined response MUST NOT indicate whether the
            # attribute exists. Absence is therefore reported as a refusal.
            return self._declined(request, "no value held")

        self._log("disclosure_granted", f"{request.attribute} ({decision.reason})")
        return self._advance(DisclosureResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            attribute=request.attribute,
            status=DisclosureStatus.GRANTED,
            value=value,
            expires_at=_soon(),
        ))

    def _declined(self, request: DisclosureRequest, why: str) -> DisclosureResponse:
        self._log("disclosure_declined", f"{request.attribute} ({why})")
        assert self.session is not None
        return self._advance(
            DisclosureResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                attribute=request.attribute,
                status=DisclosureStatus.DECLINED,
                expires_at=_soon(),
            )
        )

    def _advance(self, response: DisclosureResponse) -> DisclosureResponse:
        """Move our own view of the session when we answer a disclosure."""
        assert self.session is not None
        self.session.record_disclosure(response, discharge=False)
        return response

    # -- consent -----------------------------------------------------------

    def request_consent(
        self, action: ConsentAction, scope: list[str], reciprocal: bool = True
    ) -> ConsentRequest:
        assert self.session is not None
        request = ConsentRequest(
            session_id=self.session.session_id,
            request_id=self._rid(),
            action=action,
            scope=scope,
            reciprocal=reciprocal,
            binding_commitment=False,
            expires_at=_soon(),
        )
        self.session.register_request(request.request_id, request.type)
        self.session.begin_consent()
        self._log("consent_request", f"{action.value}: {', '.join(scope)}")
        return request

    def handle_consent_request(self, request: ConsentRequest) -> ConsentResponse:
        """Section 14.5.

        An Agent may grant consent without a per-instance human decision only
        if its Authority for the corresponding level is `true` *and* no
        attribute in scope carries the `principal_approval` gate.
        """
        assert self.session is not None
        self.session.begin_consent()
        level = CONSENT_ACTION_AUTHORITY[request.action]
        gated = [
            attribute
            for attribute in request.scope
            if self.standing_interest.class_of(attribute).gate is Gate.PRINCIPAL_APPROVAL
        ]

        if self._authority(level) is not AuthorityValue.TRUE or gated:
            if all(attribute in self.pre_approved for attribute in gated) and gated:
                self.consents.approved_attributes.update(gated)
                self.consents.granted_attributes.update(request.scope)
                self._log("consent_granted", f"{request.action.value} (approved)")
                return ConsentResponse(
                    session_id=self.session.session_id,
                    request_ref=request.request_id,
                    status=ConsentStatus.GRANTED,
                    granted_scope=list(request.scope),
                    expires_at=_soon(),
                )
            self._log("consent_pending", request.action.value)
            return ConsentResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                status=ConsentStatus.PENDING_PRINCIPAL_APPROVAL,
                expires_at=_soon(),
            )

        self.consents.granted_attributes.update(request.scope)
        self._log("consent_granted", request.action.value)
        return ConsentResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            status=ConsentStatus.GRANTED,
            granted_scope=list(request.scope),
            expires_at=_soon(),
        )

    # -- handoff -----------------------------------------------------------

    def handoff(self, protocol_ref: str) -> Handoff:
        assert self.session is not None
        scope: list[Authority] = []
        if self._authority(Authority.NEGOTIATE_NONBINDING) is AuthorityValue.TRUE:
            scope.append(Authority.NEGOTIATE_NONBINDING)
        message = Handoff(
            session_id=self.session.session_id,
            target=HandoffTarget(kind=HandoffKind.PROTOCOL, protocol_ref=protocol_ref),
            authorized_scope=scope,
            requires_principal_presence=True,
            expires_at=_soon(60 * 24),
        )
        self.session.record_handoff(message)
        self._log("handoff", protocol_ref)
        return message
