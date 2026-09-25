"""The invariants, against Standing Interests nobody designed.

Every other test in this suite runs a case an author chose. That is how the
four worked domains were chosen, and the limit cases exist because choosing
your own examples is a way of being wrong. These tests choose nothing: they
generate Standing Interests, policies, authorities and claim sequences and
assert the properties that must hold for all of them.

This is the closest a single implementation can come to the real check, which
is a second implementation written by someone else. It is not a substitute
for it, and the README asks for one.

Run a longer search than the default when it matters:

    python -m pytest tests/test_properties.py --hypothesis-seed=random -q
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gidp.agent import Agent
from gidp.evaluation import assert_truthful, choose_result, evaluate_claim
from gidp.objects import (
    AuthoritySpec,
    Claim,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from gidp.policy import RetrievalAttribute, derive_projection
from gidp.session import ProtocolError
from gidp.vocab import (
    Authority,
    AuthorityValue,
    ClaimOperator,
    ClaimResult,
    Gate,
    Surface,
)

SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

KEYS = ("alpha", "beta", "gamma", "delta")
TOKENS = ("one", "two", "three", "four", "five")


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


@st.composite
def ranges(draw):
    low = draw(st.integers(min_value=0, max_value=1_000))
    width = draw(st.integers(min_value=0, max_value=1_000))
    return {"min": low, "max": low + width}


@st.composite
def condition_values(draw):
    return draw(
        st.one_of(
            st.lists(st.sampled_from(TOKENS), min_size=1, max_size=3, unique=True),
            ranges(),
            st.sampled_from(TOKENS),
            st.integers(min_value=0, max_value=2_000),
        )
    )


@st.composite
def disclosure_classes(draw):
    surface = draw(st.sampled_from(list(Surface)))
    gate = draw(st.sampled_from(list(Gate)))
    # Section 10: a local attribute is evaluation-only, and a gate on it
    # would describe a disclosure that cannot happen.
    if surface is Surface.LOCAL:
        gate = Gate.NONE
    return DisclosureClass(surface=surface, gate=gate)


@st.composite
def standing_interests(draw, identifier: str = "local:si"):
    keys = draw(st.lists(st.sampled_from(KEYS), min_size=1, max_size=4, unique=True))
    conditions = {key: draw(condition_values()) for key in keys}
    policy = {key: draw(disclosure_classes()) for key in keys}
    levels = {
        level: draw(st.sampled_from(list(AuthorityValue)))
        for level in Authority
        if level is not Authority.COMMIT
    }
    return StandingInterest(
        id=identifier,
        principal_ref=f"{identifier}-principal",
        interest=ConditionalInterest(
            action="explore",
            conditions=conditions,
        ),
        disclosure_policy=DisclosurePolicy(attributes=policy),
        authority=AuthoritySpec(levels=levels, evidence_ref="urn:example:delegation"),
    )


@st.composite
def claims(draw):
    return Claim(
        key=draw(st.sampled_from(KEYS)),
        operator=draw(st.sampled_from(list(ClaimOperator))),
        value=draw(condition_values()),
    )


# ---------------------------------------------------------------------------
# Section 15.5 — truthfulness
# ---------------------------------------------------------------------------


@SETTINGS
@given(standing_interests(), claims(), st.booleans(), st.booleans())
def test_no_reachable_answer_ever_contradicts_the_private_values(
    interest, claim, coarsen, decline
):
    """The central obligation, over every policy the vocabulary permits."""
    evaluation = evaluate_claim(interest, claim)
    answer = choose_result(evaluation, coarsen=coarsen, decline=decline)
    assert_truthful(evaluation, answer)


@SETTINGS
@given(standing_interests(), claims())
def test_a_definite_answer_requires_a_definite_truth(interest, claim):
    """`compatible` and `incompatible` may never rest on an undetermined truth."""
    evaluation = evaluate_claim(interest, claim)
    answer = choose_result(evaluation)
    if answer in (ClaimResult.COMPATIBLE, ClaimResult.INCOMPATIBLE):
        assert evaluation.truth is not None
    if evaluation.truth is None:
        assert answer in (
            ClaimResult.UNKNOWN,
            ClaimResult.REQUIRES_DISCLOSURE,
            ClaimResult.DECLINED,
        )


# ---------------------------------------------------------------------------
# Sections 9.1 and 10 — a local value never leaves its holder
# ---------------------------------------------------------------------------


def _local_values(interest: StandingInterest) -> list:
    return [
        value
        for key, value in interest.interest.conditions.items()
        if interest.class_of(key).surface is Surface.LOCAL
    ]


def _appears_in(value, payload) -> bool:
    if isinstance(payload, dict):
        return any(_appears_in(value, v) for v in payload.values())
    if isinstance(payload, list):
        return any(_appears_in(value, v) for v in payload)
    return payload == value


@SETTINGS
@given(standing_interests(), st.lists(claims(), min_size=1, max_size=6))
def test_a_responder_never_transmits_its_own_local_values(interest, claim_list):
    """Section 9.1, as a property rather than as one scenario.

    Per sender, which is the nuance S-09 forced into the open: a querent may
    name a value the responder happens to hold, and that is the querent's
    disclosure, not the responder's.
    """
    assume(interest.authority.permits(Authority.PROBE))
    responder = Agent(ref="agent:opaque:r", standing_interest=interest)
    initiator = Agent(ref="agent:opaque:i", standing_interest=interest)
    opened = initiator.open_session("s", purpose="test")
    accept = responder.handle_session_open(opened)
    initiator.confirm_accept(accept)

    request = initiator.ask(claim_list)
    response = responder.handle_compatibility_request(request)
    payload = response.model_dump(mode="json", exclude_none=True)

    for value in _local_values(interest):
        assert not _appears_in(value, payload), (
            f"a local value reached the wire in {payload}"
        )


@SETTINGS
@given(standing_interests())
def test_a_projection_never_carries_a_local_value(interest):
    """Section 11: what is published is bounded by the policy."""
    assume(interest.authority.permits(Authority.PUBLISH_PROJECTION))
    keys = list(interest.interest.conditions)
    projection = derive_projection(
        interest,
        projection_id="p",
        endpoint="agent:opaque:r",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        interest_ref=None,
        attributes=[RetrievalAttribute("categories", None, lambda _: ["generic"])],
    )
    payload = projection.model_dump(mode="json", exclude_none=True)
    for value in _local_values(interest):
        assert not _appears_in(value, payload)
    assert keys  # the interest was non-empty, so the check meant something


# ---------------------------------------------------------------------------
# Section 17.2 — the state machine admits nothing it has not defined
# ---------------------------------------------------------------------------

EVENTS = ("ask", "disclose", "consent", "handoff", "close")


@SETTINGS
@given(standing_interests(), st.lists(st.sampled_from(EVENTS), min_size=1, max_size=8))
def test_every_event_sequence_either_advances_or_is_refused(interest, events):
    """No sequence reaches an undefined state, and none passes silently."""
    assume(interest.authority.permits(Authority.PROBE))
    a = Agent(ref="agent:opaque:a", standing_interest=interest)
    b = Agent(ref="agent:opaque:b", standing_interest=interest)
    opened = a.open_session("s", purpose="test")
    a.confirm_accept(b.handle_session_open(opened))

    for event in events:
        try:
            if event == "ask":
                request = a.ask(
                    [
                        Claim(
                            key="alpha",
                            operator=ClaimOperator.INTERSECTS,
                            value=["one"],
                        )
                    ]
                )
                a.receive_compatibility_response(
                    b.handle_compatibility_request(request), request
                )
            elif event == "disclose":
                a.request_disclosure("alpha", purpose="test")
            elif event == "consent":
                from gidp.vocab import ConsentAction

                a.request_consent(ConsentAction.REVEAL_IDENTITY, ["alpha"])
            elif event == "handoff":
                a.handoff("https://example.org/human/v1")
            elif event == "close":
                from gidp.vocab import CloseReason

                a.session.close(CloseReason.COMPLETED)
        except ProtocolError:
            # A refusal is a defined outcome; the point is that it is raised
            # rather than silently accepted.
            continue
        assert a.session.state is not None
