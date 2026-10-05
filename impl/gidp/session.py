"""The Compatibility Session as three axes (0.2 model; Sections 15.2, 17.2).

0.1 encoded three different things in one state: the session's *phase*, the
*request in flight*, and the *consents and evaluation*. Every reviewer found
the seams: the ``_RETURN`` bookkeeping that remembered where a request was
asked from, the special case for a qualification reached mid-wait, and the
grant-before-qualification exception. This module is the 0.2 refactoring the
reviews converged on. ``Session`` now holds:

- phase: the monotonic life of the session,
  ``REQUESTED → EXPLORING → QUALIFIED → HANDED_OFF``, with ``CLOSED``
  reachable from anywhere. A disclosure or a consent never changes it.
- pending: the request in flight (at most one at a time per view,
  which is 0.1's concurrency rule made explicit). Answering a request
  clears it; the phase was never moved, so nothing needs restoring.
- evaluation and consents: standing propositions, the peer's reported
  status, granted consents (held by the Agent), dependencies.

The 0.1 wire states remain as a **derived view** (the ``state`` property):
``PROBING`` is ``EXPLORING`` with nothing pending, ``DISCLOSURE_PENDING``
and ``CONSENT_PENDING`` are the pending axis, ``CONSENTED`` is ``QUALIFIED``
plus a post-qualification grant. The rules that needed stating as patches
in 0.1 fall out of the shape: a disclosure returns the session to the stage
it was asked from *because the phase never left it*; a qualification reached
mid-wait defers to the return *because qualification requires the pending
axis empty and recomputes then*; an ``incompatible`` closes mid-wait
*because closing reads the evaluation axis and ignores the pending one*.

The state is held per session and per direction of request: each Agent
tracks the requests it has sent, so both Agents may hold an outstanding
request at the same time without the session having two conflicting states.
``Session`` models one side's view.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

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


class Phase(str, enum.Enum):
    """The session's monotonic life, one of the three axes."""

    REQUESTED = "requested"
    EXPLORING = "exploring"
    QUALIFIED = "qualified"
    HANDED_OFF = "handed_off"
    CLOSED = "closed"


#: The pending axis is keyed per direction. Section 17.2 holds state per
#: side *and per direction of request*, so an Agent whose own consent is
#: awaiting the peer Principal's decision can still receive and answer a
#: disclosure the peer asks meanwhile. Within one direction, at most one
#: request is in flight at a time: 0.1's concurrency rule, explicit.
SENT = "sent"
RECEIVED = "received"
PENDING_DISCLOSURE = "DisclosureRequest"
PENDING_CONSENT = "ConsentRequest"

#: The token an Opportunity carries in `contingent_on` for dependencies its
#: sender holds but may not name (Section 14.6, S-23).
UNDISCLOSED_DEPENDENCY = "undisclosed"



@dataclass(frozen=True)
class JointPredicate:
    """A profile's joint predicate in its wire form (profiles/FORMAT.md).

    The predicate travels as ordinary claims on `key` with `operator`; a
    `point` value form asks whether one candidate value satisfies the
    responder's private value. It holds, in a side's local view, when a
    standing proposition on it resolved `compatible` -- in one direction,
    or, for `both_directions`, in each direction on the same value: one
    side's acceptance of a candidate proves nothing about the other's
    (the buyer-at-80 / seller-at-90 trap). `conditionally_compatible` does
    not satisfy it: a coarsened answer withholds the information the
    predicate exists to establish (E-11).
    """

    name: str
    key: str
    operator: str
    value_form: str = "point"
    satisfied_when: str = "both_directions"

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
    close_reason: CloseReason | None = None

    #: Axis 1: the phase. None until a SessionOpen is seen.
    phase: Phase | None = None
    #: Axis 2: the requests in flight, keyed by direction (SENT for
    #: requests this side asked, RECEIVED for requests it was asked), each
    #: holding PENDING_DISCLOSURE or PENDING_CONSENT.
    pending_requests: dict[str, str] = field(default_factory=dict)
    #: Axis 3 (consents): the directions (SENT/RECEIVED) in which a
    #: consent was granted after qualification (what the 0.1 wire view
    #: calls CONSENTED, per directional view). The phase is read before the
    #: grant is processed, so a pre-qualification grant that unblocks a
    #: deferred qualification never becomes retrospectively
    #: post-qualification.
    post_qualification_consents: set[str] = field(default_factory=set)
    #: Unanswered propositions, in either direction: a claim of ours whose
    #: request expired with no terminal, or a claim we received and hold
    #: for a PROBE approval (Section 16.3). They are unresolved, block
    #: qualification on the side that records them (a question that went
    #: unanswered must not make a session qualifiable), and clear when
    #: superseded (the one extension 0.2 makes to supersedes).
    unanswered: set[str] = field(default_factory=set)

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
    #: The profile's joint predicates (FORMAT.md); each enters the entry
    #: conditions like a required dimension, but asks more of it.
    joint_predicates: list[JointPredicate] = field(default_factory=list)
    #: Proposition -> (key, operator, canonical value), for the claims this
    #: side sent or received; what a joint predicate is checked against.
    claim_of: dict[str, tuple[str, str, str]] = field(default_factory=dict)
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
    #: request_id -> True while a request is undischarged (Section 14).
    open_requests: dict[str, str] = field(default_factory=dict)
    opportunity_emitted: bool = False
    #: Section 14.6: the session_status the peer last reported in a
    #: CompatibilityResponse. Qualification is the conjunction of both
    #: sides' entry conditions, and this is the initiator's view of the
    #: responder's.
    peer_status: SessionStatus | None = None

    # -- the derived 0.1 view ----------------------------------------------

    def state_of(self, direction: str) -> SessionState | None:
        """The faithful 0.1 projection of ONE directional view (17.2).

        This projection, and not the aggregate below, reproduces the 0.1
        table: each direction's view moves on its own requests and its own
        grants. Admission never reads a projection (the guards read the
        axes), so neither projection can mask an admissible event.
        """
        if self.phase is None:
            return None
        if self.phase is Phase.CLOSED:
            return SessionState.CLOSED
        if self.phase is Phase.HANDED_OFF:
            return SessionState.HANDED_OFF
        if self.phase is Phase.REQUESTED:
            return SessionState.REQUESTED
        in_flight = self.pending_requests.get(direction)
        if in_flight == PENDING_DISCLOSURE:
            return SessionState.DISCLOSURE_PENDING
        if in_flight == PENDING_CONSENT:
            return SessionState.CONSENT_PENDING
        if self.phase is Phase.QUALIFIED:
            return (
                SessionState.CONSENTED
                if direction in self.post_qualification_consents
                else SessionState.QUALIFIED
            )
        return SessionState.PROBING

    @property
    def state(self) -> SessionState | None:
        """An aggregate display view: this side's own sent request first,
        a received one otherwise. It is a convenience and never a basis for
        admission; the 0.1 projection is ``state_of(direction)``.
        """
        own = self.state_of(SENT)
        if own in (SessionState.DISCLOSURE_PENDING, SessionState.CONSENT_PENDING):
            return own
        received = self.state_of(RECEIVED)
        if received in (
            SessionState.DISCLOSURE_PENDING,
            SessionState.CONSENT_PENDING,
        ):
            return received
        if (
            self.phase is Phase.QUALIFIED
            and self.post_qualification_consents
        ):
            return SessionState.CONSENTED
        return own

    def _refuse(self, event: str) -> ProtocolError:
        state = self.state
        return ProtocolError(
            f"no transition for event {event!r} in state "
            f"{state.value if state else 'None'} (Section 17.2)"
        )

    def _require_open(self, event: str) -> None:
        """The exploring and qualified phases are where exchange happens."""
        if self.phase not in (Phase.EXPLORING, Phase.QUALIFIED):
            raise self._refuse(event)

    # -- phase transitions --------------------------------------------------

    def open(self, message: SessionOpen) -> None:
        if self.phase is not None:
            raise self._refuse("SessionOpen")
        self.phase = Phase.REQUESTED
        self.open_requests[message.request_id] = message.type

    def accept(self, message: SessionAccept) -> None:
        if self.phase is not Phase.REQUESTED:
            raise self._refuse("SessionAccept")
        self.phase = Phase.EXPLORING
        self._discharge(message.request_ref)

    def close(self, reason: CloseReason) -> None:
        if self.phase is Phase.CLOSED:
            raise ProtocolError(
                "CLOSED is terminal; a new interaction needs a new "
                "session_id (Section 17.2)"
            )
        self.phase = Phase.CLOSED
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

    def _begin_pending(self, kind: str, direction: str) -> None:
        """Open the pending axis: one request in flight per direction.

        The phase does not move. A disclosure or a consent is a request
        made *within* a stage and is not a stage of its own (Section 17.2),
        so there is nothing to remember and nothing to restore on the answer.
        The directions are independent (Section 17.2): a request received
        while one's own is awaiting the peer is admitted.
        """
        self._require_open(kind)
        if direction in self.pending_requests:
            raise self._refuse(kind)
        self.pending_requests[direction] = kind

    def begin_consent(
        self, action: ConsentAction | None = None, direction: str = SENT
    ) -> None:
        """Open a consent request.

        Before qualification only `disclose_attributes` is permitted:
        identity, direct contact and handoff remain behind qualification
        (Sections 5, 14.5).
        """
        if (
            self.phase is Phase.EXPLORING
            and action is not None
            and action is not ConsentAction.DISCLOSE_ATTRIBUTES
        ):
            raise ProtocolError(
                f"consent to {action.value!r} cannot be sought before "
                "qualification; only disclose_attributes may be (Sections 5, "
                "14.5, 17.2)"
            )
        self._begin_pending(PENDING_CONSENT, direction)

    def begin_disclosure(self, direction: str = SENT) -> None:
        """Open a disclosure request, in any open phase."""
        self._begin_pending(PENDING_DISCLOSURE, direction)

    def note_compatibility(self) -> None:
        """Probing continues in any open phase, pending or not (Section 17.2)."""
        self._require_open("Compatibility")

    def record_compatibility(self, response: CompatibilityResponse) -> None:
        self._require_open("Compatibility")
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

    def note_claims(self, direction: str, claims: Iterable[Any]) -> None:
        """Remember what each proposition asked, for the joint predicates."""
        for claim in claims:
            self.claim_of[f"{direction}:{claim.claim_id}"] = (
                claim.key,
                getattr(claim.operator, "value", str(claim.operator)),
                json.dumps(claim.value, sort_keys=True),
            )

    def joint_predicate_for(self, key: str, operator: str) -> JointPredicate | None:
        for predicate in self.joint_predicates:
            if predicate.key == key and predicate.operator == operator:
                return predicate
        return None

    def _joint_holds(self, predicate: JointPredicate) -> bool:
        def accepted(direction: str) -> set[str]:
            return {
                value
                for proposition, (key, operator, value) in self.claim_of.items()
                if proposition.startswith(f"{direction}:")
                and key == predicate.key
                and operator == predicate.operator
                and self.results.get(proposition) is ClaimResult.COMPATIBLE
            }

        if predicate.satisfied_when == "one_direction":
            return bool(accepted("sent") | accepted("received"))
        return bool(accepted("sent") & accepted("received"))

    def check_supersedes(self, direction: str, claim_ids: Iterable[str]) -> None:
        """A claim may withdraw only an answered claim of its own sender, and
        never one answered `incompatible` (S-24).

        The second rule matters more. A known contradiction closes
        the session (Section 17.2); letting its asker withdraw it and ask a
        neighbouring value instead would make bisection (the attack of
        Section 24.3) a supported feature of the protocol.
        """
        for claim_id in claim_ids:
            proposition = f"{direction}:{claim_id}"
            if proposition in self.unanswered:
                # The 0.2 extension: our own claim that expired unanswered
                # may be superseded. The rule rests on its invariants --
                # no recorded incompatible is removed, no budget refunded
                # -- not on silence being information-free (it is not;
                # Section 24.7).
                continue
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
            self.unanswered.discard(proposition)

    def _dimension(self, proposition: str) -> str:
        # A result set directly, as the conformance suite does, is its own
        # dimension.
        return self.dimension_of.get(proposition, proposition)

    def record_disclosure(
        self, response: DisclosureResponse, *, discharge: bool = True
    ) -> None:
        """Apply a DisclosureResponse.

        ``discharge`` is False on the responder's own view: the request_id
        belongs to the peer, so there is nothing of ours to discharge, but
        the pending axis still clears (Section 17.2).
        """
        direction = SENT if discharge else RECEIVED
        if self.pending_requests.get(direction) != PENDING_DISCLOSURE:
            raise self._refuse("DisclosureResponse")
        provisional = response.status in PROVISIONAL_DISCLOSURE_STATUSES
        if not provisional:
            if discharge:
                # Correlate before clearing: a delayed duplicate of an
                # earlier response names a request already discharged and
                # must not clear the wait a newer request opened.
                self._discharge(response.request_ref)
            del self.pending_requests[direction]
        self.outstanding_requires.discard(response.attribute)

    def record_consent(
        self, response: ConsentResponse, *, discharge: bool = True
    ) -> None:
        direction = SENT if discharge else RECEIVED
        if self.pending_requests.get(direction) != PENDING_CONSENT:
            raise self._refuse("ConsentResponse")
        if response.status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL:
            return  # provisional: the request stays in flight (Section 14)
        if discharge:
            # Correlate before clearing (see record_disclosure).
            self._discharge(response.request_ref)
        del self.pending_requests[direction]
        if response.status is ConsentStatus.GRANTED and self.phase is Phase.QUALIFIED:
            # A grant before qualification opens a gate (Section 10.2); it
            # does not make the session CONSENTED, which is the stage from
            # which a Handoff may leave. The fact is per direction: a grant
            # in one directional view does not make the other CONSENTED.
            self.post_qualification_consents.add(direction)

    def expire_request(
        self, request_id: str, claim_ids: Iterable[str] = ()
    ) -> None:
        """A request of ours whose ``expires_at`` passed with no terminal.

        0.2 semantics, stated as such (not as 0.1 equivalence): the wait
        ends without closing the session, and a terminal that arrives
        later names a discharged request and is refused by correlation.
        For a CompatibilityRequest, each of its claims becomes an
        unresolved proposition that blocks qualification until superseded
        (Section 14.2, the 0.2 extension), because expiring an awkward question
        must not make the session qualifiable.
        """
        kind = self.open_requests.get(request_id)
        if kind is None:
            raise ProtocolError(
                f"cannot expire unknown request {request_id!r} (Section 14)"
            )
        del self.open_requests[request_id]
        if kind in (PENDING_DISCLOSURE, PENDING_CONSENT):
            if self.pending_requests.get(SENT) == kind:
                del self.pending_requests[SENT]
        self.note_unanswered(SENT, claim_ids)
        self.pending_supersedes.pop(request_id, None)

    def note_unanswered(self, direction: str, claim_ids: Iterable[str]) -> None:
        """Record claims that stand without a result: our own expired
        questions, or questions we received and hold for a Principal's
        PROBE decision (Section 16.3). Both block qualification."""
        for claim_id in claim_ids:
            self.unanswered.add(f"{direction}:{claim_id}")

    def emit_handoff(self) -> None:
        """The emitter's side of the quiescence barrier (0.2 semantics).

        A local guard, scoped as such: both pending slots empty and no
        locally known active CompatibilityRequest in either direction
        (an own question still undischarged, or a received question held
        unanswered). An expired-but-unsuperseded proposition is an
        evaluation fact, not an active request, and does not block. The
        guard cannot see a request in transit; emission is therefore NOT
        a bilateral acceptance of the transfer, and the collision is
        decided on the recipient's side (record_handoff).
        """
        if self.phase is not Phase.QUALIFIED or self.pending_requests:
            raise ProtocolError(
                "a Handoff requires the qualified phase and both pending "
                "slots empty (Sections 14.7, 17.2)"
            )
        if "CompatibilityRequest" in self.open_requests.values() or any(
            proposition.startswith(f"{RECEIVED}:")
            for proposition in self.unanswered
        ):
            raise ProtocolError(
                "a Handoff requires no locally known active compatibility "
                "request in either direction (0.2 quiescence barrier)"
            )
        self.phase = Phase.HANDED_OFF

    def record_handoff(self, message: Handoff) -> None:
        """The recipient's side: 0.1's own rule decides the collision.

        A recipient whose directional view is not QUALIFIED or CONSENTED
        -- a pending slot occupied, a request of its own in transit --
        refuses: it closes the session with reason 'unsupported', which
        also ends its wait, and the emitter moves HANDED_OFF -> CLOSED on
        receiving that close. Recovery is a new session against the same
        budget.
        """
        if self.phase is not Phase.QUALIFIED or self.pending_requests:
            raise ProtocolError(
                "a recipient that receives a Handoff in an earlier state MUST "
                "close the session with reason 'unsupported' (Section 17.2)"
            )
        self.phase = Phase.HANDED_OFF

    def record_close(self, message: SessionClose) -> None:
        self.close(message.reason)

    # -- status ------------------------------------------------------------

    def status(self) -> SessionStatus:
        """Compute ``session_status`` per the table of Section 15.2."""
        if self.phase is Phase.CLOSED:
            return SessionStatus.CLOSED

        values = list(self.results.values())

        if ClaimResult.INCOMPATIBLE in values:
            return SessionStatus.INCOMPATIBLE

        # Section 15.2: the entry conditions decide the transition; once it
        # is taken the status is kept, whatever is recorded afterwards.
        if self.opportunity_emitted:
            return SessionStatus.POTENTIALLY_COMPATIBLE

        # Section 17.2: while a disclosure or consent is pending, the status
        # is not yet reported qualifying; it is recomputed when the
        # pending axis empties, over the propositions then standing, so
        # that status, phase and Opportunity advance together.
        if self.phase is not Phase.EXPLORING or self.pending_requests:
            return SessionStatus.OPEN

        # Section 15.2: every claim must have resolved `compatible` or
        # `conditionally_compatible`, and at least one `compatible`. A
        # non-qualifying result prevents qualification, so that an
        # Opportunity never rests on silence (Section 18).
        qualifying = (ClaimResult.COMPATIBLE, ClaimResult.CONDITIONALLY_COMPATIBLE)
        covered = {self._dimension(p) for p in self.results}
        qualifies = (
            bool(values)
            and not self.outstanding_requires
            # A question of ours that has no answer yet (held for a PROBE
            # approval, say; Section 16.3) is an unresolved proposition,
            # and an Opportunity must not be emitted over it. Expiry
            # discharges the request without making it a result (S-59).
            and "CompatibilityRequest" not in self.open_requests.values()
            and not self.unanswered
            and ClaimResult.COMPATIBLE in values
            and all(v in qualifying for v in values)
            # Section 15.2: the profile's qualification requirements enter
            # the entry conditions directly: a required dimension nobody
            # has examined blocks the transition however positively the
            # examined ones answered.
            and self.required_dimensions <= covered
            and all(self._joint_holds(p) for p in self.joint_predicates)
        )
        return SessionStatus.POTENTIALLY_COMPATIBLE if qualifies else SessionStatus.OPEN

    def qualify(self) -> bool:
        """Apply the EXPLORING -> QUALIFIED transition if the status warrants.

        Returns True exactly once per session, on the transition that
        produces the Opportunity (Sections 14.6, 17.2). ``status()`` already
        requires the pending axis empty and the phase EXPLORING, so a
        qualification reached mid-wait defers and is recomputed at the
        return.
        """
        if self.status() is not SessionStatus.POTENTIALLY_COMPATIBLE:
            return False
        if self.opportunity_emitted:
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
            # entry conditions. The responder confirms its own (profile
            # requirements included) through the status it reports, and
            # the initiator does not emit until that report qualifies.
            return False
        self.phase = Phase.QUALIFIED
        self.opportunity_emitted = True
        return True

    def fail_incompatible(self) -> None:
        if self.phase not in (Phase.EXPLORING, Phase.QUALIFIED):
            raise self._refuse("session_status=incompatible")
        self.phase = Phase.CLOSED
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
        saying on what. The fact of contingency is a result derived from an
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
