"""An in-process wire between two Agents, and the checks it enforces.

GIDP 0.1 defines no transport binding (Section 22), so this is not a binding:
it is a test harness that carries objects from one Agent to the other and
enforces, on every message, the rules Section 14 states about correlation and
answering. Those rules are easy to state and easy to violate, and an
implementation that only ever talks to itself will not notice.

The transcript it records is also the artefact a reviewer reads: a session is
much easier to judge from its message log than from its source code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .objects import (
    ONE_WAY_TYPES,
    REQUEST_TYPES,
    RESPONSE_TYPES,
    SessionClose,
    TransmittedObject,
)


class WireError(Exception):
    """A message that breaks a rule of Section 14."""


@dataclass
class Wire:
    """Carries objects between two peers, checking Section 14 as it goes."""

    transcript: list[tuple[str, TransmittedObject]] = field(default_factory=list)
    #: request_id -> True while the request is undischarged.
    outstanding: dict[str, str] = field(default_factory=dict)
    #: request_ids that have received a provisional response and are still
    #: waiting for their terminal one (Section 14).
    provisional: set[str] = field(default_factory=set)

    def send(self, sender: str, message: TransmittedObject) -> TransmittedObject:
        self._check(sender, message)
        self.transcript.append((sender, message))
        return message

    # -- checks ------------------------------------------------------------

    def _check(self, sender: str, message: TransmittedObject) -> None:
        if isinstance(message, REQUEST_TYPES):
            request_id = message.request_id
            if request_id in self.outstanding:
                raise WireError(
                    f"{sender} reused request_id {request_id!r} while it was "
                    "still outstanding (Section 14)"
                )
            self.outstanding[request_id] = sender
            return

        if isinstance(message, RESPONSE_TYPES):
            ref = message.request_ref
            if ref not in self.outstanding:
                raise WireError(
                    f"{sender} answered {ref!r}, which is not outstanding; every "
                    "response carries the request_ref it answers (Section 14)"
                )
            if self.outstanding[ref] == sender:
                raise WireError(
                    f"{sender} answered its own request {ref!r} (Section 14)"
                )
            if self._is_provisional(message):
                self.provisional.add(ref)
                return
            self.provisional.discard(ref)
            del self.outstanding[ref]
            return

        if isinstance(message, SessionClose):
            if message.request_ref is not None:
                self.outstanding.pop(message.request_ref, None)
                self.provisional.discard(message.request_ref)
            return

        if isinstance(message, ONE_WAY_TYPES):
            # Opportunity and Handoff are notifications: they are neither
            # requests nor responses and are not answered (Section 14).
            return

        raise WireError(f"{type(message).__name__} is not a GIDP 0.1 object")

    @staticmethod
    def _is_provisional(message: TransmittedObject) -> bool:
        status = getattr(message, "status", None)
        if status is None:
            return False
        from .vocab import (
            PROVISIONAL_DISCLOSURE_STATUSES,
            ConsentStatus,
            DisclosureStatus,
        )

        if isinstance(status, DisclosureStatus):
            return status in PROVISIONAL_DISCLOSURE_STATUSES
        if isinstance(status, ConsentStatus):
            return status is ConsentStatus.PENDING_PRINCIPAL_APPROVAL
        return False

    # -- reporting ---------------------------------------------------------

    def unanswered(self) -> dict[str, str]:
        """Requests still outstanding when the session ended.

        A conforming session leaves none: every request is answered by exactly
        one response or by a SessionClose (Section 14).
        """
        return dict(self.outstanding)

    def render(self) -> str:
        lines = []
        for sender, message in self.transcript:
            fields = message.model_dump(exclude_none=True, mode="json")
            kind = fields.pop("type")
            fields.pop("version", None)
            fields.pop("expires_at", None)
            fields.pop("session_id", None)
            lines.append(f"{sender:>8} | {kind}: {fields}")
        return "\n".join(lines)
