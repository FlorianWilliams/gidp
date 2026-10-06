"""An Agent acting under a Standing Interest (Sections 3, 13-18).

The Agent composes the other modules and adds nothing of its own to the
protocol semantics: evaluation lives in ``evaluation``, what may leave lives
in ``policy``, and what may happen next lives in ``session``. That separation
is what makes conformance criterion 3 testable: replay the same Standing
Interest, policy and session state, and the same objects come out.

Abuse controls (Section 24.3) are represented by a query budget. It is a
crude mitigation by design, and ``examples/probing.py`` measures how crude:
a budget is what an implementer must set, and this implementation exists partly
to give them a measured number to set it by.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any

from .auditing import DisclosureAudit
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
from .policy import (
    IDENTITY_ATTRIBUTES,
    SessionConsents,
    effective_depth,
    evaluate_disclosure,
)
from .session import ProtocolError, Session
from .vocab import (
    CONSENT_ACTION_AUTHORITY,
    PROFILE_CORE,
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
    IntendedUse,
    NextAction,
    Retention,
    SessionState,
    Surface,
)


def _now() -> datetime:
    return datetime.now(UTC)


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


def _points(value: Any) -> list[Any]:
    """The exact values a held or asked value pins down.

    A scalar pins itself, a list pins its elements, and a range pins a value
    only when it is degenerate (min == max). A non-degenerate range pins
    nothing: an interval whose edge happens to equal a private number is not
    refused, since a shared origin such as 0 would refuse half of all ranges.
    """
    if isinstance(value, dict):
        low, high = value.get("min"), value.get("max")
        return [low] if low is not None and low == high else []
    if isinstance(value, list | tuple | set):
        return [p for item in value for p in _points(item)]
    return [value]


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
    #: Section 14.7: target references covered by a granted `handoff`
    #: consent in this session.
    handoff_consents: set[str] = field(default_factory=set)
    _consent_actions: dict[str, tuple[ConsentAction, list[str]]] = field(
        default_factory=dict
    )
    #: Section 16.3: compatibility requests held while PROBE is
    #: `approval_required` and the Principal has not decided.
    _held_probes: dict[str, CompatibilityRequest] = field(default_factory=dict)
    audit: list[AuditEntry] = field(default_factory=list)
    queries_answered: int = 0
    #: Retention modes this Agent can enforce on what it receives.
    #: The default is the accurate one for an implementation that keeps a
    #: session in memory and nothing after it.
    dischargeable_retention: set[Retention] = field(
        default_factory=lambda: {Retention.SESSION_ONLY}
    )
    #: What this Agent declines to be asked (Section 24.3). None means it
    #: answers whatever Section 15.5 permits, which bounds nothing.
    #: Named at length because `audit` is already the audit *trail*, and the
    #: two are unrelated: one records what happened, this decides what may.
    disclosure_audit: DisclosureAudit | None = None
    _ids: Any = field(default_factory=lambda: count(1))

    # -- helpers -----------------------------------------------------------

    def _rid(self) -> str:
        return f"r-{next(self._ids)}"

    def _log(self, event: str, detail: str) -> None:
        self.audit.append(AuditEntry(event, detail))

    def _authority(self, level: Authority) -> AuthorityValue:
        return self.standing_interest.authority.value(level)

    # -- session establishment --------------------------------------------

    def _start_session_state(self) -> None:
        """Section 14.5: consent is scoped to a session. Whatever a previous
        session granted, recorded or held does not carry into a new one, even
        when the same Agent instance serves both."""
        self.consents = SessionConsents()
        self.handoff_consents = set()
        self._consent_actions = {}
        self._held_probes = {}

    def open_session(
        self,
        session_id: str,
        purpose: str,
        max_depth: Surface = Surface.SESSION,
        features: Iterable[Feature] = (),
    ) -> SessionOpen:
        if self._authority(Authority.PROBE) is AuthorityValue.FALSE:
            raise ProtocolError("PROBE authority is false; cannot open a session (16)")
        self._start_session_state()
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
        self._note_own_dependencies()
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
        # Section 14.1: SessionAccept carries the features supported on both
        # sides, which is the intersection of the two sets; it does not echo
        # the request.
        agreed = sorted(
            set(message.features) & self.supported_features, key=lambda f: f.value
        )
        self._start_session_state()
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
        self._note_own_dependencies()
        self._log(
            "session_accept",
            f"depth in force={depth.value}; features="
            f"{', '.join(f.value for f in agreed) or 'core only'}",
        )
        return accept

    def _note_own_dependencies(self) -> None:
        """Hand the session this side's dependencies and a way to ask, when
        the Opportunity is built, how far its Disclosure Policy lets them
        travel (Sections 10.3, 14.6; S-23)."""
        assert self.session is not None

        def visibility() -> str:
            assert self.session is not None
            cls = self.standing_interest.class_of("conditional_on")
            if not cls.evaluable:
                return "never"
            decision = evaluate_disclosure(
                self.standing_interest,
                "conditional_on",
                self.session.max_depth,
                self.consents,
            )
            return "transmit" if decision.permitted else "withhold"

        self.session.note_own_dependencies(
            self.standing_interest.interest.conditional_on, visibility
        )

    def confirm_accept(self, accept: SessionAccept) -> None:
        assert self.session is not None
        self.session.max_depth = effective_depth(
            self.session.max_depth, accept.max_depth
        )
        self.session.features = set(accept.features)
        self.session.accept(accept)
        self._log("session_confirmed", f"depth in force={self.session.max_depth.value}")

    # -- probing -----------------------------------------------------------

    def ask(self, claims: list[Claim]) -> CompatibilityRequest:
        assert self.session is not None
        request_id = self._rid()
        # Every claim is a proposition with its own name (S-24).
        claims = [
            c if c.claim_id is not None else c.model_copy(update={"claim_id": f"{request_id}.{i}"})
            for i, c in enumerate(claims)
        ]
        for claim in claims:
            leaked = self._own_private_value_in(claim)
            if leaked is not None:
                # Section 14.3: a request MUST NOT contain the requester's own
                # private values, the four reserved dependency lists of
                # Section 19.1 included. Refused before anything is emitted
                # or recorded. The guard compares known values; it cannot
                # prove the provenance of a value the caller transformed.
                raise ProtocolError(
                    f"claim {claim.claim_id!r} on {claim.key!r} carries this "
                    f"side's own private value of {leaked!r} (14.3)"
                )
        withdrawn = [cid for c in claims for cid in c.supersedes]
        self.session.check_supersedes("sent", withdrawn)
        request = CompatibilityRequest(
            session_id=self.session.session_id,
            request_id=request_id,
            claims=claims,
            allowed_results=list(ClaimResult),
            expires_at=_soon(),
        )
        self.session.register_request(request.request_id, request.type)
        self.session.note_claims("sent", claims)
        if withdrawn:
            self.session.pending_supersedes[request.request_id] = withdrawn
        self._log("compatibility_request", ", ".join(c.key for c in claims))
        return request

    def _own_private_value_in(self, claim: Claim) -> str | None:
        """The key whose private value this claim would carry, if any.

        Private means: not releasable at session depth without a decision --
        surface `local` (evaluation_only, never) or any gate. Compared by
        the exact values each side pins down, so `intersects [x]` over a
        private set containing x, or the degenerate range {x, x} over a
        private x, is caught as well as `equals x`. The check is conservative (a
        hypothesis that coincides with the secret is refused too)
        and does no provenance tracking: a value the caller transformed, such
        as a band built around the secret, passes unseen.
        """
        interest = self.standing_interest.interest
        own: dict[str, Any] = dict(interest.conditions)
        for reserved in ("conditional_on", "provides", "requires", "excludes"):
            values = getattr(interest, reserved)
            if values:
                own[reserved] = values
        if claim.key not in own:
            return None
        cls = self.standing_interest.class_of(claim.key)
        if cls.surface is not Surface.LOCAL and cls.gate is Gate.NONE:
            return None
        held = own[claim.key]
        held_points = _points(held)
        if claim.value == held or any(p in held_points for p in _points(claim.value)):
            return claim.key
        return None

    def handle_compatibility_request(
        self, request: CompatibilityRequest
    ) -> CompatibilityResponse | SessionClose | None:
        """Answer a compatibility request, or hold it.

        Returns None when the request is held: PROBE is `approval_required`
        and Section 16.3 gives that row no provisional response. The Agent
        sends nothing until `principal_answers_probe` is called; silence is
        the only wait signal the protocol has here.
        """
        assert self.session is not None

        if self._authority(Authority.PROBE) is AuthorityValue.FALSE:
            return self._decline_probe(request)

        if self._authority(Authority.PROBE) is AuthorityValue.APPROVAL_REQUIRED:
            self._held_probes[request.request_id] = request
            # 0.2 deadline semantics: a held proposition is unresolved on the
            # holder's side too, and blocks qualification until answered,
            # expired and superseded, or withdrawn.
            self.session.note_unanswered(
                "received", [c.claim_id for c in request.claims if c.claim_id]
            )
            self._log("probe_held", f"{len(request.claims)} claim(s), awaiting Principal")
            return None

        return self._answer_compatibility(request)

    def principal_answers_probe(
        self, request: CompatibilityRequest, approved: bool
    ) -> CompatibilityResponse | SessionClose | None:
        """The Principal's decision on a held compatibility request.

        Section 16.3: a late approval re-runs the earlier rows against the
        authority in force now. A refusal closes the session `declined`,
        which tells the peer nothing about why. Returns None if the request
        was not held or the session has since moved on.
        """
        held = self._held_probes.pop(request.request_id, None)
        if held is None or self.session is None:
            return None
        if self.session.state is SessionState.CLOSED:
            return None
        if not approved or self._authority(Authority.PROBE) is AuthorityValue.FALSE:
            return self._decline_probe(held)
        return self._answer_compatibility(held)

    def _decline_probe(self, request: CompatibilityRequest) -> SessionClose:
        assert self.session is not None
        return SessionClose(
            session_id=self.session.session_id,
            reason=CloseReason.DECLINED,
            request_ref=request.request_id,
            expires_at=_soon(),
        )

    def _answer_compatibility(
        self, request: CompatibilityRequest
    ) -> CompatibilityResponse:
        assert self.session is not None
        self.session.note_compatibility()
        outcomes: list[ClaimOutcome] = []
        requires: list[str] = []
        self.session.withdraw(
            "received", [cid for claim in request.claims for cid in claim.supersedes]
        )

        self.session.note_claims("received", request.claims)
        for claim in request.claims:
            self.queries_answered += 1
            over_budget = self.queries_answered > self.query_budget
            if self.disclosure_audit is not None and not self.disclosure_audit.admits(
                claim, self.standing_interest
            ):
                # Section 18: a refusal implies nothing, and this one implies
                # less than most, since an observer can reproduce the decision.
                result = ClaimResult.DECLINED
            elif claim.key in IDENTITY_ATTRIBUTES and (
                claim.key not in self.consents.identity_revealed
                or self._authority(Authority.INTRODUCE) is AuthorityValue.FALSE
            ):
                # Section 10.6: `compatible` to `principal_identity equals
                # "Acme GmbH"` confirms the identity without any
                # DisclosureResponse carrying it. This is the third such path,
                # after the two S-33 closed. Declined, which implies nothing. A
                # consent opens a possibility and waives no other row of
                # Section 16.3: INTRODUCE is re-read at every use (E-02).
                result = ClaimResult.DECLINED
            else:
                predicate = self.session.joint_predicate_for(
                    claim.key, claim.operator.value
                )
                if predicate is not None and predicate.value_form == "point":
                    # A profile's joint predicate (FORMAT.md): does this one
                    # candidate value satisfy our private value? Answered
                    # truthfully. Coarsening is a permitted deviation
                    # (15.5), and here it would erase the fact asked.
                    candidate = claim.model_copy(update={
                        "operator": ClaimOperator.OVERLAPS,
                        "value": {"min": claim.value, "max": claim.value},
                    })
                    evaluation = evaluate_claim(self.standing_interest, candidate)
                    result = self._answer(
                        evaluation, over_budget=over_budget, exact=True
                    )
                else:
                    evaluation = evaluate_claim(self.standing_interest, claim)
                    result = self._answer(evaluation, over_budget=over_budget)
                if self.disclosure_audit is not None:
                    self.disclosure_audit.record(claim, self.standing_interest, result)
            assert claim.claim_id is not None
            outcomes.append(
                ClaimOutcome(key=claim.key, claim_id=claim.claim_id, result=result)
            )
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

        # A held question, now answered, is no longer unresolved here.
        for outcome in outcomes:
            self.session.unanswered.discard(f"received:{outcome.claim_id}")
        self.session.record_results(outcomes, direction="received")
        self.session.outstanding_requires = set(requires)

        return CompatibilityResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            results=outcomes,
            session_status=self.session.status(),
            contingent_on=self.session.own_contingent_on(),
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

    def _answer(
        self, evaluation: LocalEvaluation, *, over_budget: bool, exact: bool = False
    ) -> ClaimResult:
        """Decide what to say, within Section 15.5.

        The default policy: coarsen whenever the value consulted is
        evaluation-only and the truthful answer is affirmative, which is the
        canonical case of Section 15.4: a private threshold answered without
        being transmitted. Once the query budget is exhausted, decline.
        """
        if over_budget:
            return choose_result(evaluation, decline=True)
        coarsen = evaluation.evaluation_only and evaluation.truth is True and not exact
        return choose_result(evaluation, coarsen=coarsen)

    def receive_compatibility_response(
        self,
        response: CompatibilityResponse,
        request: CompatibilityRequest | None = None,
    ) -> None:
        assert self.session is not None
        self.session.record_compatibility(response)
        if request is None:
            return
        # Mirror of the responder's bookkeeping: a confirmed dependency is
        # unresolved for both sides (Section 14.6).
        by_id = {claim.claim_id: claim for claim in request.claims}
        for outcome in response.results:
            if (
                outcome.key == "conditional_on"
                and outcome.result is ClaimResult.COMPATIBLE
            ):
                claim = by_id.get(outcome.claim_id)
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
        """Section 14.4.

        A stated retention is an obligation on this Agent towards the
        discloser (Section 10.7). An Agent may therefore only state one it
        can discharge; stating and disregarding it would make the field
        advice, and a limit nothing turns on is not a limit.
        """
        assert self.session is not None
        if retention is not None and retention not in self.dischargeable_retention:
            raise ProtocolError(
                f"this Agent cannot discharge retention {retention.value!r}, so "
                "it MUST NOT state it (Section 10.7); omit the field and let "
                "the responder decline"
            )
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
        self.session.begin_disclosure()  # SENT: our own request in flight
        self._log("disclosure_request", f"{attribute} ({purpose})")
        return request

    def handle_disclosure_request(
        self, request: DisclosureRequest
    ) -> DisclosureResponse:
        assert self.session is not None
        from .session import RECEIVED

        self.session.begin_disclosure(RECEIVED)

        if self._authority(Authority.DISCLOSE) is AuthorityValue.FALSE:
            # Section 18: an authority refusal is reported as 'declined',
            # never as the operational outcome 'unauthorized'.
            return self._declined(request, "DISCLOSE authority is false")

        if request.attribute in IDENTITY_ATTRIBUTES and (
            request.attribute not in self.consents.identity_revealed
            or self._authority(Authority.INTRODUCE) is AuthorityValue.FALSE
        ):
            # Section 10.6: the identity rules attach to the data, whatever
            # message carries it. An identity attribute travels only under a
            # `reveal_identity` consent, which requires INTRODUCE and
            # cannot precede qualification.
            return self._declined(
                request, "identity attribute without reveal_identity consent"
            )

        # Section 16.2: where a level is `approval_required`, the response
        # MUST be `pending_principal_approval`. Authority and the Disclosure
        # Policy are different axes (authority says whether this Agent may
        # perform a category of action at all, the gate says which attributes
        # need a decision), and an Agent that consulted only the gate would
        # silently ignore a Principal who said "ask me every time", for every
        # attribute that happens to carry no gate of its own.
        if (
            self._authority(Authority.DISCLOSE) is AuthorityValue.APPROVAL_REQUIRED
            and request.attribute not in self.pre_approved
        ):
            self._log("disclosure_pending", f"{request.attribute} (authority)")
            return DisclosureResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                attribute=request.attribute,
                status=DisclosureStatus.PENDING_PRINCIPAL_APPROVAL,
                expires_at=_soon(),
            )

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
        return self._advance(
            DisclosureResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                attribute=request.attribute,
                status=DisclosureStatus.GRANTED,
                value=value,
                expires_at=_soon(),
            )
        )

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

    def record_consent(
        self, response: ConsentResponse, *, discharge: bool = True
    ) -> None:
        """Record a peer's ConsentResponse, remembering what it authorised.

        Section 14.7: a Handoff must be preceded by a granted consent whose
        action is `handoff` and whose scope names the target. The session
        records the transition; the Agent records which action the grant
        was for, which the response alone does not say.
        """
        assert self.session is not None
        self.session.record_consent(response, discharge=discharge)
        if response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
            return  # provisional: the request is not discharged (Section 14)
        pending = self._consent_actions.pop(response.request_ref, None)
        if pending is None or response.status is not ConsentStatus.GRANTED:
            return
        action, _scope = pending
        if action is ConsentAction.HANDOFF:
            self.handoff_consents.update(response.granted_scope)

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
        self.session.begin_consent(action)
        self.session.register_request(request.request_id, request.type)
        self._consent_actions[request.request_id] = (action, list(scope))
        self._log("consent_request", f"{action.value}: {', '.join(scope)}")
        return request

    def handle_consent_request(self, request: ConsentRequest) -> ConsentResponse:
        """Section 14.5.

        An Agent may grant consent without a per-instance human decision only
        if its Authority for the corresponding level is `true` *and* no
        attribute in scope carries the `principal_approval` gate.
        """
        assert self.session is not None
        from .session import RECEIVED

        self.session.begin_consent(request.action, RECEIVED)

        if request.action is not ConsentAction.REVEAL_IDENTITY and any(
            attribute in IDENTITY_ATTRIBUTES for attribute in request.scope
        ):
            # Section 10.6: a scope that names an identity attribute under
            # any action but `reveal_identity` is declined; otherwise
            # `disclose_attributes` before qualification would do, under
            # DISCLOSE, what `reveal_identity` holds until after it.
            self._log("consent_declined", f"{request.action.value} (identity in scope)")
            return ConsentResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                status=ConsentStatus.DECLINED,
                granted_scope=[],
                expires_at=_soon(),
            )

        level = CONSENT_ACTION_AUTHORITY[request.action]
        gated = [
            attribute
            for attribute in request.scope
            if self.standing_interest.class_of(attribute).gate
            is Gate.PRINCIPAL_APPROVAL
        ]

        if self._authority(level) is AuthorityValue.FALSE:
            # Section 14.5: a refused authority is a refusal. Answering
            # `pending_principal_approval` would tell the peer to
            # wait for a decision nobody will be asked to make (Section 18
            # gives the same rule for disclosure). Section 16.3, second row.
            self._log("consent_declined", f"{request.action.value} (authority)")
            return ConsentResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                status=ConsentStatus.DECLINED,
                granted_scope=[],
                expires_at=_soon(),
            )

        if self._authority(level) is not AuthorityValue.TRUE or gated:
            if all(attribute in self.pre_approved for attribute in gated) and gated:
                self.consents.approved_attributes.update(gated)
                self.consents.granted_attributes.update(request.scope)
                if request.action is ConsentAction.REVEAL_IDENTITY:
                    self.consents.identity_revealed.update(request.scope)
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
        if request.action is ConsentAction.REVEAL_IDENTITY:
            self.consents.identity_revealed.update(request.scope)
        self._log("consent_granted", request.action.value)
        return ConsentResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            status=ConsentStatus.GRANTED,
            granted_scope=list(request.scope),
            expires_at=_soon(),
        )

    # -- the Principal answers ---------------------------------------------

    def principal_answers_consent(
        self, request: ConsentRequest, granted: bool
    ) -> ConsentResponse:
        """The terminal response to a consent the Principal was asked about.

        Without this the `principal_approval` gate is decorative. Section 14
        requires every request to be answered by exactly one terminal
        response, and a provisional `pending_principal_approval` does not
        discharge it; an Agent that can only ever say "pending" leaves a
        request outstanding for the life of the session and a human decision
        with nowhere to go. Section 17.2 has the transition on both branches
        (`CONSENT_PENDING` returns to `QUALIFIED` on a refusal); it was the
        Agent that had no way to fire it.
        """
        assert self.session is not None
        if granted:
            self.consents.approved_attributes.update(request.scope)
            self.consents.granted_attributes.update(request.scope)
            if request.action is ConsentAction.REVEAL_IDENTITY:
                self.consents.identity_revealed.update(request.scope)
        self._log(
            "consent_granted" if granted else "consent_declined",
            f"{request.action.value} (principal)",
        )
        return ConsentResponse(
            session_id=self.session.session_id,
            request_ref=request.request_id,
            status=ConsentStatus.GRANTED if granted else ConsentStatus.DECLINED,
            granted_scope=list(request.scope) if granted else [],
            expires_at=_soon(),
        )

    def principal_answers_disclosure(
        self, request: DisclosureRequest, granted: bool
    ) -> DisclosureResponse:
        """The terminal response to a disclosure the Principal was asked about.

        A refusal is `declined`, which Section 14.4 requires to be
        indistinguishable from any other refusal: it says nothing about
        whether the attribute exists or what it holds.
        """
        assert self.session is not None
        if not granted:
            self._log("disclosure_declined", request.attribute)
            return DisclosureResponse(
                session_id=self.session.session_id,
                request_ref=request.request_id,
                attribute=request.attribute,
                status=DisclosureStatus.DECLINED,
                expires_at=_soon(),
            )
        self.consents.approved_attributes.add(request.attribute)
        self._log("disclosure_granted", f"{request.attribute} (principal)")
        return self.handle_disclosure_request(request)

    # -- handoff -----------------------------------------------------------

    def handoff(self, protocol_ref: str) -> Handoff:
        assert self.session is not None
        if protocol_ref not in self.handoff_consents:
            raise ProtocolError(
                "a Handoff must be preceded by a granted consent whose "
                "action is `handoff` and whose scope names the target "
                "(Section 14.7)"
            )
        scope: list[Authority] = []
        if self._authority(Authority.NEGOTIATE_NONBINDING) is AuthorityValue.TRUE:
            scope.append(Authority.NEGOTIATE_NONBINDING)
        message = Handoff(
            session_id=self.session.session_id,
            target=HandoffTarget(kind=HandoffKind.PROTOCOL, protocol_ref=protocol_ref),
            authorized_scope=scope,
            requires_principal_presence=True,
            contingent_on=self.session.contingent_on(),
            expires_at=_soon(60 * 24),
        )
        self.session.emit_handoff()
        self._log("handoff", protocol_ref)
        return message
