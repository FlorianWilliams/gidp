"""The Compatibility Session: state machine and status (Sections 15.2, 17.2).

The transition table of Section 17.2 is normative and says an implementation
MUST implement exactly those transitions and no others, so it is reproduced
here as data rather than scattered through control flow: ``TRANSITIONS`` below
is the table, and every state change goes through it.

Section 17.2 also states that the state is held per session *and per direction
of request*: each Agent tracks the state of the requests it has sent, so both
Agents may hold an outstanding request at the same time without the session
having two conflicting states. ``Session`` here models one side's view.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .objects import (
    ClaimOutcome,
    CompatibilityResponse,
    ConsentResponse,
    DisclosureResponse,
    Handoff,
    Opportunity,
    SessionAccept,
    SessionClose,
    SessionOpen,
)
from .vocab import (
    PROVISIONAL_DISCLOSURE_STATUSES,
    ClaimResult,
    CloseReason,
    ConsentAction,
    ConsentStatus,
    SessionState,
    SessionStatus,
    Surface,
)


class ProtocolError(Exception):
    """A message that the specification does not allow in the current state."""


class Event(str):
    """Event names used as keys in the transition table."""


SESSION_OPEN = Event("SessionOpen")
SESSION_ACCEPT = Event("SessionAccept")
COMPATIBILITY = Event("Compatibility")  # request or response
DISCLOSURE_REQUEST = Event("DisclosureRequest")
DISCLOSURE_TERMINAL = Event("DisclosureResponse.terminal")
DISCLOSURE_PROVISIONAL = Event("DisclosureResponse.provisional")
QUALIFY = Event("session_status=potentially_compatible")
INCOMPATIBLE = Event("session_status=incompatible")
CONSENT_REQUEST = Event("ConsentRequest")
CONSENT_GRANTED = Event("ConsentResponse.granted")
CONSENT_DECLINED = Event("ConsentResponse.declined")
CONSENT_PROVISIONAL = Event("ConsentResponse.provisional")
HANDOFF = Event("Handoff")
CLOSE = Event("SessionClose")


#: Target meaning "return to the state the pending request was sent from".
#: A disclosure or a consent is a request inside a stage of the session, not a
#: stage of its own; answering it must not move the session to a different
#: stage than the one it was asked in (S-22).
_RETURN = object()

#: The normative transition table of Section 17.2. ``None`` as the target
#: means "state unchanged"; ``_RETURN`` means "the state the pending request
#: was sent from".
TRANSITIONS: dict[tuple[SessionState | None, Event], object] = {
    (None, SESSION_OPEN): SessionState.REQUESTED,
    (SessionState.REQUESTED, SESSION_ACCEPT): SessionState.PROBING,
    (SessionState.REQUESTED, CLOSE): SessionState.CLOSED,
    (SessionState.PROBING, COMPATIBILITY): None,
    # A disclosure may be asked in any open stage and returns to it.
    (SessionState.PROBING, DISCLOSURE_REQUEST): SessionState.DISCLOSURE_PENDING,
    (SessionState.QUALIFIED, DISCLOSURE_REQUEST): SessionState.DISCLOSURE_PENDING,
    (SessionState.CONSENTED, DISCLOSURE_REQUEST): SessionState.DISCLOSURE_PENDING,
    (SessionState.DISCLOSURE_PENDING, DISCLOSURE_TERMINAL): _RETURN,
    (SessionState.DISCLOSURE_PENDING, DISCLOSURE_PROVISIONAL): None,
    (SessionState.DISCLOSURE_PENDING, COMPATIBILITY): None,
    (SessionState.PROBING, QUALIFY): SessionState.QUALIFIED,
    (SessionState.PROBING, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.DISCLOSURE_PENDING, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.CONSENT_PENDING, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.QUALIFIED, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.CONSENTED, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.QUALIFIED, COMPATIBILITY): None,
    # Consent to disclose attributes may be sought while probing, because a
    # `session/consent` attribute can be what qualification needs. Every
    # other consent action waits for qualification (Section 5, 14.5).
    (SessionState.PROBING, CONSENT_REQUEST): SessionState.CONSENT_PENDING,
    (SessionState.QUALIFIED, CONSENT_REQUEST): SessionState.CONSENT_PENDING,
    (SessionState.CONSENTED, CONSENT_REQUEST): SessionState.CONSENT_PENDING,
    (SessionState.CONSENT_PENDING, CONSENT_GRANTED): SessionState.CONSENTED,
    (SessionState.CONSENT_PENDING, CONSENT_DECLINED): _RETURN,
    (SessionState.CONSENT_PENDING, CONSENT_PROVISIONAL): None,
    (SessionState.CONSENT_PENDING, COMPATIBILITY): None,
    (SessionState.CONSENTED, COMPATIBILITY): None,
    (SessionState.QUALIFIED, HANDOFF): SessionState.HANDED_OFF,
    (SessionState.CONSENTED, HANDOFF): SessionState.HANDED_OFF,
    (SessionState.HANDED_OFF, CLOSE): SessionState.CLOSED,
}

#: Every state except CLOSED may transition to CLOSED on SessionClose or on
#: expiry (Section 17.2, final row).
#: The token an Opportunity carries in `contingent_on` for dependencies its
#: sender holds but may not name (Section 14.6, S-23).
UNDISCLOSED_DEPENDENCY = "undisclosed"

_CLOSEABLE = tuple(s for s in SessionState if s is not SessionState.CLOSED)


@dataclass
class Session:
    """One side's view of a Compatibility Session."""

    session_id: str
    is_initiator: bool
    profile: str
    max_depth: Surface
    #: Optional features in force, i.e. the intersection both sides support
    #: (Section 14.1). The bilateral core is implied and never listed.
    features: set = field(default_factory=set)
    state: SessionState | None = None
    close_reason: CloseReason | None = None

    #: Proposition -> its result, for every claim still standing in either
    #: direction (S-24). A proposition is "sent:<claim_id>" or
    #: "received:<claim_id>": the two sides number their own claims, so the
    #: direction is part of the identity.
    results: dict[str, ClaimResult] = field(default_factory=dict)
    #: Proposition -> the dimension (claim key) it asks about. Dimensions are
    #: what an Opportunity counts (Section 14.6); propositions are what the
    #: status is computed over (Section 15.2).
    dimension_of: dict[str, str] = field(default_factory=dict)
    #: Section 15.2: dimensions the session's profile requires to have been
    #: examined before qualification. The core profile requires none.
    required_dimensions: set[str] = field(default_factory=set)
    #: request_id -> claim_ids that request withdraws, applied on its answer.
    pending_supersedes: dict[str, list[str]] = field(default_factory=dict)
    #: Attribute keys whose disclosure would resolve a requires_disclosure.
    outstanding_requires: set[str] = field(default_factory=set)
    #: Dependencies named by either side that this session cannot resolve
    #: (Section 14.6). A bilateral session can record a `conditional_on`
    #: entry; it cannot satisfy one, because the party it names is not in
    #: the session.
    unresolved_dependencies: set[str] = field(default_factory=set)
    #: This side's own `conditional_on`, kept apart from what it learned,
    #: because only its own is subject to its Disclosure Policy (S-23).
    own_dependencies: set[str] = field(default_factory=set)
    #: Asked at the moment the Opportunity is built, so that a consent
    #: granted later in the session is taken into account: "transmit",
    #: "withhold" (evaluation-only, or gated and not yet opened) or "never".
    dependency_visibility: Callable[[], str] | None = None
    #: The stage a pending disclosure or consent was asked from (S-22).
    return_to: SessionState | None = None
    #: request_id -> True while a request is undischarged (Section 14).
    open_requests: dict[str, str] = field(default_factory=dict)
    opportunity_emitted: bool = False
    #: Section 14.6: the session_status the peer last reported in a
    #: CompatibilityResponse. Qualification is the conjunction of both
    #: sides' entry conditions, and this is the initiator's view of the
    #: responder's.
    peer_status: SessionStatus | None = None

    # -- transitions -------------------------------------------------------

    def _fire(self, event: Event) -> None:
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ProtocolError(
                f"no transition for event {event!r} in state "
                f"{self.state.value if self.state else 'None'} (Section 17.2)"
            )
        target = TRANSITIONS[key]
        if event in (DISCLOSURE_REQUEST, CONSENT_REQUEST):
            self.return_to = self.state
        if target is _RETURN:
            target = self.return_to
        elif event is CONSENT_GRANTED and self.return_to is SessionState.PROBING:
            # A grant before qualification opens a gate (Section 10.2); it
            # does not make the session CONSENTED, which is the stage from
            # which a Handoff may leave.
            target = SessionState.PROBING
        if target is not None:
            self.state = target  # type: ignore[assignment]

    def open(self, message: SessionOpen) -> None:
        self._fire(SESSION_OPEN)
        self.open_requests[message.request_id] = message.type

    def accept(self, message: SessionAccept) -> None:
        self._fire(SESSION_ACCEPT)
        self._discharge(message.request_ref)

    def close(self, reason: CloseReason) -> None:
        if self.state is SessionState.CLOSED:
            raise ProtocolError(
                "CLOSED is terminal; a new interaction needs a new "
                "session_id (Section 17.2)"
            )
        if self.state not in _CLOSEABLE:
            raise ProtocolError(f"cannot close from {self.state}")
        self.state = SessionState.CLOSED
        self.close_reason = reason

    # -- requests and responses -------------------------------------------

    def register_request(self, request_id: str, kind: str) -> None:
        if request_id in self.open_requests:
            raise ProtocolError(
                f"request_id {request_id!r} is already outstanding; a requester "
                "MUST NOT send a duplicate request while a provisional response "
                "is outstanding (Section 14)"
            )
        self.open_requests[request_id] = kind

    def _discharge(self, request_ref: str) -> None:
        if request_ref not in self.open_requests:
            raise ProtocolError(
                f"response references unknown request {request_ref!r} (Section 14)"
            )
        del self.open_requests[request_ref]

    def begin_consent(self, action: ConsentAction | None = None) -> None:
        """Enter CONSENT_PENDING.

        From PROBING only `disclose_attributes` is permitted: identity,
        direct contact and handoff remain behind qualification (Section 5).
        """
        if (
            self.state is SessionState.PROBING
            and action is not None
            and action is not ConsentAction.DISCLOSE_ATTRIBUTES
        ):
            raise ProtocolError(
                f"consent to {action.value!r} cannot be sought before "
                "qualification; only disclose_attributes may be (Sections 5, "
                "14.5, 17.2)"
            )
        self._fire(CONSENT_REQUEST)

    def begin_disclosure(self) -> None:
        """PROBING, QUALIFIED or CONSENTED + DisclosureRequest -> pending."""
        self._fire(DISCLOSURE_REQUEST)

    def note_compatibility(self) -> None:
        """Probing continues; the state is unchanged (Section 17.2)."""
        self._fire(COMPATIBILITY)

    def record_compatibility(self, response: CompatibilityResponse) -> None:
        self._fire(COMPATIBILITY)
        self.peer_status = response.session_status
        self._discharge(response.request_ref)
        self.withdraw("sent", self.pending_supersedes.pop(response.request_ref, []))
        self.record_results(response.results, direction="sent")
        # Section 14.3: contingencies the responder states are merged into
        # what the Opportunity will carry (Section 14.6).
        self.note_dependency(*response.contingent_on)
        self.outstanding_requires = set(response.next.requires)

    def record_results(
        self, outcomes: Iterable[ClaimOutcome], *, direction: str
    ) -> None:
        for outcome in outcomes:
            proposition = f"{direction}:{outcome.claim_id}"
            self.results[proposition] = outcome.result
            self.dimension_of[proposition] = outcome.key

    def check_supersedes(self, direction: str, claim_ids: Iterable[str]) -> None:
        """A claim may withdraw only an answered claim of its own sender, and
        never one answered `incompatible` (S-24).

        The second rule is the one that matters. A known contradiction closes
        the session (Section 17.2); letting its asker withdraw it and ask a
        neighbouring value instead would make bisection -- the attack of
        Section 24.3 -- a supported feature of the protocol.
        """
        for claim_id in claim_ids:
            proposition = f"{direction}:{claim_id}"
            if proposition not in self.results:
                raise ProtocolError(
                    f"cannot supersede {claim_id!r}: a claim may supersede only "
                    "an answered claim sent by the same side (Section 14.2)"
                )
            if self.results[proposition] is ClaimResult.INCOMPATIBLE:
                raise ProtocolError(
                    f"cannot supersede {claim_id!r}: an incompatible result is a "
                    "known contradiction and closes the session (Sections "
                    "14.2, 17.2)"
                )

    def withdraw(self, direction: str, claim_ids: Iterable[str]) -> None:
        claim_ids = list(claim_ids)
        self.check_supersedes(direction, claim_ids)
        for claim_id in claim_ids:
            proposition = f"{direction}:{claim_id}"
            self.results.pop(proposition, None)
            self.dimension_of.pop(proposition, None)

    def _dimension(self, proposition: str) -> str:
        # A result set directly, as the conformance suite does, is its own
        # dimension.
        return self.dimension_of.get(proposition, proposition)

    def record_disclosure(
        self, response: DisclosureResponse, *, discharge: bool = True
    ) -> None:
        """Apply a DisclosureResponse.

        ``discharge`` is False on the responder's own view: the request_id
        belongs to the peer, so there is nothing of ours to discharge, but the
        state still moves (Section 17.2).
        """
        provisional = response.status in PROVISIONAL_DISCLOSURE_STATUSES
        self._fire(DISCLOSURE_PROVISIONAL if provisional else DISCLOSURE_TERMINAL)
        if not provisional and discharge:
            self._discharge(response.request_ref)
        self.outstanding_requires.discard(response.attribute)

    def record_consent(
        self, response: ConsentResponse, *, discharge: bool = True
    ) -> None:
        if response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
            self._fire(CONSENT_PROVISIONAL)
            return
        self._fire(
            CONSENT_GRANTED
            if response.status is ConsentStatus.GRANTED
            else CONSENT_DECLINED
        )
        if discharge:
            self._discharge(response.request_ref)

    def record_handoff(self, message: Handoff) -> None:
        if self.state not in (SessionState.QUALIFIED, SessionState.CONSENTED):
            raise ProtocolError(
                "a recipient that receives a Handoff in an earlier state MUST "
                "close the session with reason 'unsupported' (Section 17.2)"
            )
        self._fire(HANDOFF)

    def record_close(self, message: SessionClose) -> None:
        self.close(message.reason)

    # -- status ------------------------------------------------------------

    def status(self) -> SessionStatus:
        """Compute ``session_status`` per the table of Section 15.2."""
        if self.state is SessionState.CLOSED:
            return SessionStatus.CLOSED

        values = list(self.results.values())

        if ClaimResult.INCOMPATIBLE in values:
            return SessionStatus.INCOMPATIBLE

        # Section 15.2: the entry conditions decide the transition; once it
        # is taken the status is kept, whatever is recorded afterwards.
        if self.opportunity_emitted:
            return SessionStatus.POTENTIALLY_COMPATIBLE

        # Section 17.2: while a disclosure or consent is pending, the status
        # is not yet reported qualifying -- it is recomputed on the return
        # to PROBING, over the propositions then standing, so that status,
        # state and Opportunity advance together.
        if self.state is not SessionState.PROBING:
            return SessionStatus.OPEN

        # Section 15.2: every claim must have resolved `compatible` or
        # `conditionally_compatible`, and at least one `compatible`. A
        # `declined`, `unknown`, `requires_disclosure` or
        # A non-qualifying result prevents qualification, so that
        # an Opportunity never rests on silence (Section 18).
        qualifying = (ClaimResult.COMPATIBLE, ClaimResult.CONDITIONALLY_COMPATIBLE)
        covered = {self._dimension(p) for p in self.results}
        qualifies = (
            bool(values)
            and not self.outstanding_requires
            and ClaimResult.COMPATIBLE in values
            and all(v in qualifying for v in values)
            # Section 15.2: the profile's qualification requirements enter
            # the entry conditions directly -- a required dimension nobody
            # has examined blocks the transition however positively the
            # examined ones answered.
            and self.required_dimensions <= covered
        )
        return SessionStatus.POTENTIALLY_COMPATIBLE if qualifies else SessionStatus.OPEN

    def qualify(self) -> bool:
        """Apply the PROBING -> QUALIFIED transition if the status warrants it.

        Returns True exactly once per session, on the transition that produces
        the Opportunity (Sections 14.6, 17.2).
        """
        if self.status() is not SessionStatus.POTENTIALLY_COMPATIBLE:
            return False
        if self.opportunity_emitted:
            return False
        if self.state is not SessionState.PROBING:
            # Section 17.2: a qualifying status reached while a disclosure or
            # consent is pending neither fires nor lapses; the caller applies
            # it on the return to PROBING.
            return False
        if (
            self.is_initiator
            and self.peer_status is not None
            and self.peer_status is not SessionStatus.POTENTIALLY_COMPATIBLE
        ):
            # A result set directly, as the conformance suite does, leaves
            # peer_status None; on the wire every result arrives with a
            # report, so None never occurs in a real exchange.
            # Section 14.6: qualification is the conjunction of both sides'
            # entry conditions. The responder confirms its own -- profile
            # requirements included -- through the status it reports, and
            # the initiator does not emit until that report qualifies.
            return False
        self._fire(QUALIFY)
        self.opportunity_emitted = True
        return True

    def fail_incompatible(self) -> None:
        self._fire(INCOMPATIBLE)
        self.close_reason = CloseReason.INCOMPATIBLE

    # -- opportunity -------------------------------------------------------

    def open_conditions(self) -> list[str]:
        """Claim keys whose most recent result is conditionally_compatible.

        Section 14.6: `compatible_dimensions` plus the length of this list
        equals `evaluated_dimensions` in any session that qualifies.
        """
        return sorted(
            {
                self._dimension(proposition)
                for proposition, result in self.results.items()
                if result is ClaimResult.CONDITIONALLY_COMPATIBLE
            }
        )

    def note_dependency(self, *dependencies: str) -> None:
        """Record a dependency the session cannot resolve (Section 14.6)."""
        self.unresolved_dependencies.update(dependencies)

    def note_own_dependencies(
        self, dependencies: Iterable[str], visibility: Callable[[], str]
    ) -> None:
        """Record this side's own `conditional_on` and how far it may travel."""
        self.own_dependencies.update(dependencies)
        self.dependency_visibility = visibility

    def own_contingent_on(self) -> list[str]:
        """This side's own communicable contingencies (Section 14.3).

        What a responder states in a ``CompatibilityResponse`` so that the
        initiator, who cannot know these dependencies, can still build an
        Opportunity that matches the responder's evaluation (Section 14.6).
        Names travel if the policy transmits them; a withheld dependency
        travels as the single token ``undisclosed``; ``never`` leaves no
        trace.
        """
        visibility = self.dependency_visibility() if self.dependency_visibility else "transmit"
        own = self.own_dependencies - self.unresolved_dependencies
        if not own:
            return []
        if visibility == "transmit":
            return sorted(own)
        if visibility == "withhold":
            return [UNDISCLOSED_DEPENDENCY]
        return []

    def contingent_on(self) -> list[str]:
        """What the Opportunity may say it depends on (Sections 10.3, 14.6).

        A mandatory field does not outrank the Disclosure Policy. Learned
        dependencies were stated by the peer and travel as they are. This
        side's own travel by name only if its policy permits it; otherwise a
        single ``undisclosed`` marks the Opportunity as contingent without
        saying on what -- the fact of contingency is a result derived from an
        evaluation-only attribute, which `evaluation_only` permits. A `never`
        dependency leaves no trace, because a flag that exists only because
        of it would be a transmitted result produced from it.
        """
        return sorted(set(self.unresolved_dependencies) | set(self.own_contingent_on()))

    def build_opportunity(
        self, structure: str, expires_at, identity_status: dict
    ) -> Opportunity:
        if not self.is_initiator:
            raise ProtocolError(
                "the session initiator emits the Opportunity (Section 14.6)"
            )
        # Section 14.6: each dimension counts once, however many propositions
        # asked about it; a dimension is compatible only if every proposition
        # on it is, and conditionally_compatible is not compatible.
        by_dimension: dict[str, list[ClaimResult]] = {}
        for proposition, result in self.results.items():
            by_dimension.setdefault(self._dimension(proposition), []).append(result)
        compatible = sum(
            1
            for results in by_dimension.values()
            if all(r is ClaimResult.COMPATIBLE for r in results)
        )
        return Opportunity(
            session_id=self.session_id,
            structure=structure,
            evaluated_dimensions=len(by_dimension),
            compatible_dimensions=compatible,
            open_conditions=self.open_conditions(),
            contingent_on=self.contingent_on(),
            identity_status=identity_status,
            expires_at=expires_at,
        )
