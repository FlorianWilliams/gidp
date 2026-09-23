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

from dataclasses import dataclass, field
from typing import Iterable

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
    ClaimResult,
    CloseReason,
    ConsentStatus,
    DisclosureStatus,
    PROVISIONAL_DISCLOSURE_STATUSES,
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
COMPATIBILITY = Event("Compatibility")           # request or response
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


#: The normative transition table of Section 17.2. ``None`` as the target
#: means "state unchanged".
TRANSITIONS: dict[tuple[SessionState | None, Event], SessionState | None] = {
    (None, SESSION_OPEN): SessionState.REQUESTED,
    (SessionState.REQUESTED, SESSION_ACCEPT): SessionState.PROBING,
    (SessionState.REQUESTED, CLOSE): SessionState.CLOSED,

    (SessionState.PROBING, COMPATIBILITY): None,
    (SessionState.PROBING, DISCLOSURE_REQUEST): SessionState.DISCLOSURE_PENDING,
    (SessionState.DISCLOSURE_PENDING, DISCLOSURE_TERMINAL): SessionState.PROBING,
    (SessionState.DISCLOSURE_PENDING, DISCLOSURE_PROVISIONAL): None,
    (SessionState.DISCLOSURE_PENDING, COMPATIBILITY): None,

    (SessionState.PROBING, QUALIFY): SessionState.QUALIFIED,
    (SessionState.PROBING, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.DISCLOSURE_PENDING, INCOMPATIBLE): SessionState.CLOSED,
    (SessionState.QUALIFIED, INCOMPATIBLE): SessionState.CLOSED,

    (SessionState.QUALIFIED, COMPATIBILITY): None,
    (SessionState.QUALIFIED, DISCLOSURE_REQUEST): SessionState.DISCLOSURE_PENDING,
    (SessionState.QUALIFIED, CONSENT_REQUEST): SessionState.CONSENT_PENDING,

    (SessionState.CONSENT_PENDING, CONSENT_GRANTED): SessionState.CONSENTED,
    (SessionState.CONSENT_PENDING, CONSENT_DECLINED): SessionState.QUALIFIED,
    (SessionState.CONSENT_PENDING, CONSENT_PROVISIONAL): None,
    (SessionState.CONSENT_PENDING, COMPATIBILITY): None,
    (SessionState.CONSENTED, CONSENT_REQUEST): SessionState.CONSENT_PENDING,
    (SessionState.CONSENTED, COMPATIBILITY): None,

    (SessionState.QUALIFIED, HANDOFF): SessionState.HANDED_OFF,
    (SessionState.CONSENTED, HANDOFF): SessionState.HANDED_OFF,
    (SessionState.HANDED_OFF, CLOSE): SessionState.CLOSED,
}

#: Every state except CLOSED may transition to CLOSED on SessionClose or on
#: expiry (Section 17.2, final row).
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

    #: Claim key -> most recent result received or sent for it.
    results: dict[str, ClaimResult] = field(default_factory=dict)
    #: Attribute keys whose disclosure would resolve a requires_disclosure.
    outstanding_requires: set[str] = field(default_factory=set)
    #: Dependencies named by either side that this session cannot resolve
    #: (Section 14.6). A bilateral session can record a `conditional_on`
    #: entry; it cannot satisfy one, because the party it names is not in
    #: the session.
    unresolved_dependencies: set[str] = field(default_factory=set)
    #: request_id -> True while a request is undischarged (Section 14).
    open_requests: dict[str, str] = field(default_factory=dict)
    opportunity_emitted: bool = False

    # -- transitions -------------------------------------------------------

    def _fire(self, event: Event) -> None:
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ProtocolError(
                f"no transition for event {event!r} in state "
                f"{self.state.value if self.state else 'None'} (Section 17.2)"
            )
        target = TRANSITIONS[key]
        if target is not None:
            self.state = target

    def open(self, message: SessionOpen) -> None:
        self._fire(SESSION_OPEN)
        self.open_requests[message.request_id] = message.type

    def accept(self, message: SessionAccept) -> None:
        self._fire(SESSION_ACCEPT)
        self._discharge(message.request_ref)

    def close(self, reason: CloseReason) -> None:
        if self.state is SessionState.CLOSED:
            raise ProtocolError("CLOSED is terminal; a new interaction needs a new "
                                "session_id (Section 17.2)")
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

    def begin_consent(self) -> None:
        """QUALIFIED or CONSENTED + ConsentRequest -> CONSENT_PENDING."""
        self._fire(CONSENT_REQUEST)

    def begin_disclosure(self) -> None:
        """PROBING or QUALIFIED + DisclosureRequest -> DISCLOSURE_PENDING."""
        self._fire(DISCLOSURE_REQUEST)

    def note_compatibility(self) -> None:
        """Probing continues; the state is unchanged (Section 17.2)."""
        self._fire(COMPATIBILITY)

    def record_compatibility(self, response: CompatibilityResponse) -> None:
        self._fire(COMPATIBILITY)
        self._discharge(response.request_ref)
        self.record_results(response.results)
        self.outstanding_requires = set(response.next.requires)

    def record_results(self, outcomes: Iterable[ClaimOutcome]) -> None:
        for outcome in outcomes:
            self.results[outcome.key] = outcome.result

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

        # Section 15.2: every claim must have resolved `compatible` or
        # `conditionally_compatible`, and at least one `compatible`. A
        # `declined`, `unknown`, `requires_disclosure` or
        # `requires_principal_approval` result prevents qualification, so that
        # an Opportunity never rests on silence (Section 18).
        qualifying = (ClaimResult.COMPATIBLE, ClaimResult.CONDITIONALLY_COMPATIBLE)
        qualifies = (
            bool(values)
            and not self.outstanding_requires
            and ClaimResult.COMPATIBLE in values
            and all(v in qualifying for v in values)
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
        return [
            key
            for key, result in self.results.items()
            if result is ClaimResult.CONDITIONALLY_COMPATIBLE
        ]

    def note_dependency(self, *dependencies: str) -> None:
        """Record a dependency the session cannot resolve (Section 14.6)."""
        self.unresolved_dependencies.update(dependencies)

    def build_opportunity(
        self, structure: str, expires_at, identity_status: dict
    ) -> Opportunity:
        if not self.is_initiator:
            raise ProtocolError(
                "the session initiator emits the Opportunity (Section 14.6)"
            )
        # Section 14.6: each claim key counts once, whatever the number of
        # times it was asked; conditionally_compatible is not compatible.
        compatible = sum(
            1 for r in self.results.values() if r is ClaimResult.COMPATIBLE
        )
        return Opportunity(
            session_id=self.session_id,
            structure=structure,
            evaluated_dimensions=len(self.results),
            compatible_dimensions=compatible,
            open_conditions=self.open_conditions(),
            contingent_on=sorted(self.unresolved_dependencies),
            identity_status=identity_status,
            expires_at=expires_at,
        )
