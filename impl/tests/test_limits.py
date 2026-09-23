"""The four limit cases, kept honest.

Each of these asserts that a *known boundary still behaves as documented* in
LIMITS.md. If one of them starts to pass differently -- if a future change
makes an identity-first flow possible, say -- the test fails and LIMITS.md is
out of date, which is exactly when it is most dangerous.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from cid.agent import Agent  # noqa: E402
from cid.objects import (  # noqa: E402
    AuthoritySpec,
    ConditionalInterest,
    DisclosureClass,
    DisclosurePolicy,
    StandingInterest,
)
from cid.session import ProtocolError  # noqa: E402
from cid.vocab import (  # noqa: E402
    Authority,
    AuthorityValue,
    ConsentAction,
    Gate,
    InterestClass,
    Surface,
)

import limits  # noqa: E402


def test_l1_the_policy_cannot_express_an_obligation_to_publish():
    """L-1: every disclosure class is a ceiling, none is a floor."""
    for surface in Surface:
        cls = DisclosureClass(surface=surface)
        # There is no field, and no value of any field, that means "must".
        assert set(type(cls).model_fields) == {"surface", "gate"}
        assert cls.gate in set(Gate)
    # And nothing anywhere obliges an Agent to publish a projection.
    authority = AuthoritySpec(levels={Authority.PUBLISH_PROJECTION: AuthorityValue.FALSE})
    assert authority.permits(Authority.PUBLISH_PROJECTION) is False


def test_l2_a_one_dimensional_interest_is_recovered_as_fast_as_any_other():
    """L-2: the other conditions never hid the threshold."""
    assert limits.limit_fungible_and_perishable() is True


def test_l3_reciprocity_is_asymmetric_under_asymmetric_exposure():
    """L-3: the strong side spends one fact many times."""
    assert limits.limit_power_asymmetry() is True


def test_l4_identity_cannot_precede_probing():
    """L-4: the ordering of the ladder is enforced, not conventional."""
    interest = StandingInterest(
        id="local:si",
        principal_ref="local:principal",
        interest=ConditionalInterest(
            interest_class=InterestClass.PASSIVE_CONDITIONAL_DEMAND,
            action="consider",
            conditions={"instrument": ["private_placement"]},
        ),
        disclosure_policy=DisclosurePolicy(
            attributes={
                "principal_name": DisclosureClass(
                    surface=Surface.SESSION, gate=Gate.CONSENT
                )
            }
        ),
        authority=AuthoritySpec(
            levels={
                Authority.PROBE: AuthorityValue.TRUE,
                Authority.INTRODUCE: AuthorityValue.TRUE,
            }
        ),
    )
    a = Agent(ref="agent:a", standing_interest=interest)
    b = Agent(ref="agent:b", standing_interest=interest)
    opened = a.open_session("s-kyc", purpose="regulated")
    a.confirm_accept(b.handle_session_open(opened))

    with pytest.raises(ProtocolError):
        a.request_consent(ConsentAction.REVEAL_IDENTITY, ["principal_name"])


def test_all_four_limit_cases_still_reproduce():
    """The suite LIMITS.md rests on."""
    assert limits.limit_mandatory_disclosure() is True
    assert limits.limit_fungible_and_perishable() is True
    assert limits.limit_power_asymmetry() is True
    assert limits.limit_identity_first() is True
