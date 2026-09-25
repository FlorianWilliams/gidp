"""An in-memory Discovery Provider (Section 12).

Deliberately the simplest architecture of Section 12.3 -- a single index that
receives projections and returns candidate references -- because the point is
to exercise the protocol, not to demonstrate a privacy-preserving retrieval
mechanism. Section 24.11 applies in full: a provider sees every projection and
query it serves, and this one is no exception.

The one thing it does take seriously is withdrawal. Section 12.2 requires a
provider to publish a withdrawal latency and to stop returning a withdrawn
projection within it, and an Agent to treat that published latency as the time
its projection remains retrievable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .objects import DiscoveryProjection


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class _Entry:
    projection: DiscoveryProjection
    withdrawn_at: datetime | None = None


@dataclass
class InMemoryProvider:
    """A Discovery Provider with the operations of Section 12.2."""

    #: Published withdrawal latency (Section 12.2). Zero here: this provider
    #: stops returning a projection immediately. A federated provider would
    #: publish something larger and honour it.
    withdrawal_latency: timedelta = timedelta(0)
    _entries: dict[str, _Entry] = field(default_factory=dict)
    #: Queries served, for the surveillance discussion of Section 25.5: an
    #: operator that cannot say how many queries it served cannot say what it
    #: knows.
    queries_served: int = 0

    # -- operations (Section 12.2) ----------------------------------------

    def publish_projection(self, projection: DiscoveryProjection) -> str:
        """Returns a provider-assigned ``projection_ref``.

        Section 12.2: the reference is assigned by the provider and need not
        equal the ``projection_id`` the Agent minted.
        """
        ref = f"pref-{len(self._entries) + 1}"
        self._entries[ref] = _Entry(projection)
        return ref

    def update_projection(self, ref: str, projection: DiscoveryProjection) -> str:
        if ref not in self._entries:
            return "unknown_reference"
        self._entries[ref] = _Entry(projection)
        return "updated"

    def withdraw_projection(self, ref: str) -> str:
        entry = self._entries.get(ref)
        if entry is None:
            return "unknown_reference"
        entry.withdrawn_at = _now()
        return "withdrawn"

    def query_candidates(self, query: DiscoveryProjection) -> list[str]:
        """Return candidate references matching a query projection.

        Retrieval is deliberately coarse (Section 12.4): overlap on any
        retrieval attribute. Section 11.6 applies -- retrieval based on a
        projection is not evidence of compatibility, consent or agreement, and
        the caller must open a session to learn anything.
        """
        self.queries_served += 1
        hits: list[str] = []
        for ref, entry in self._entries.items():
            if not self._retrievable(entry):
                continue
            if self._overlaps(entry.projection, query):
                hits.append(ref)
        return hits

    def resolve_candidate(self, ref: str) -> str | None:
        entry = self._entries.get(ref)
        if entry is None or not self._retrievable(entry):
            return None
        return entry.projection.endpoint

    # -- internals ---------------------------------------------------------

    def _retrievable(self, entry: _Entry) -> bool:
        now = _now()
        if entry.projection.expires_at <= now:
            return False
        if entry.withdrawn_at is not None:
            if now - entry.withdrawn_at >= self.withdrawal_latency:
                return False
        return True

    @staticmethod
    def _overlaps(a: DiscoveryProjection, b: DiscoveryProjection) -> bool:
        for field_name in ("categories", "domains", "geographies", "relation"):
            left = set(getattr(a, field_name))
            right = set(getattr(b, field_name))
            if left and right and not (left & right):
                return False
        return True
