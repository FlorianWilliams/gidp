"""The comparative claim, guarded.

`spec/alternatives.md` rests on these numbers. A change to the protocol that
silently moves them should fail here rather than be discovered by a reader.
"""

from __future__ import annotations

import sys
from math import log2
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baselines.measure import COUNTERPARTY, OPERATOR, PUBLIC, Fact, Ledger
from baselines.mechanisms import (
    cid_adversarial,
    cid_honest,
    private_set_intersection,
    public_posting,
    sealed_one_shot,
    trusted_broker,
)
from baselines.mitigations import POLICIES, discrimination, probe
from baselines.scenario import FACTS


# -- the yardstick itself ---------------------------------------------------

def test_the_measure_is_zero_before_anything_is_observed():
    ledger = Ledger.over(FACTS)
    for audience in (COUNTERPARTY, OPERATOR, PUBLIC):
        assert ledger.total(audience) == 0.0


def test_revealing_a_fact_costs_its_whole_prior():
    fact = Fact("X", "f", 3, (1, 2, 3, 4))
    ledger = Ledger.over([fact])
    ledger.reveal(COUNTERPARTY, fact.key)
    assert ledger.bits(COUNTERPARTY, fact.key) == pytest.approx(log2(4))


def test_an_observation_that_rules_nothing_out_leaks_nothing():
    fact = Fact("X", "f", 3, (1, 2, 3, 4))
    ledger = Ledger.over([fact])
    ledger.observe(COUNTERPARTY, fact.key, lambda v: True)
    assert ledger.bits(COUNTERPARTY, fact.key) == 0.0


def test_the_harness_refuses_an_observation_the_truth_cannot_explain():
    """A predicate that excludes the true value means the harness is wrong."""
    fact = Fact("X", "f", 3, (1, 2, 3, 4))
    ledger = Ledger.over([fact])
    with pytest.raises(AssertionError):
        ledger.observe(COUNTERPARTY, fact.key, lambda v: v == 1)


# -- what separates the mechanisms -----------------------------------------

def test_only_the_intermediary_hands_both_secrets_to_a_third_party():
    assert trusted_broker().third_party is not None
    for mechanism in (public_posting, sealed_one_shot,
                      private_set_intersection, cid_honest):
        assert mechanism().third_party is None


def test_the_intermediary_learns_everything():
    outcome = trusted_broker()
    total = sum(f.total_bits for f in FACTS)
    assert outcome.ledger.total(OPERATOR) == pytest.approx(total)
    assert len(outcome.ledger.exact(OPERATOR)) == len(FACTS)


def test_only_publication_leaks_to_an_unbounded_audience():
    assert public_posting().ledger.total(PUBLIC) > 0
    for mechanism in (trusted_broker, sealed_one_shot,
                      private_set_intersection, cid_honest, cid_adversarial):
        assert mechanism().ledger.total(PUBLIC) == 0.0


def test_set_intersection_cannot_decide_the_case():
    assert private_set_intersection().verdict == "cannot decide"


def test_the_two_cryptographic_baselines_presuppose_the_rendezvous():
    assert sealed_one_shot().presupposes_rendezvous
    assert private_set_intersection().presupposes_rendezvous
    assert not cid_honest().presupposes_rendezvous


def test_probing_extracts_substantially_more_than_asking():
    honest, probing = cid_honest(), cid_adversarial()
    assert probing.ledger.total(COUNTERPARTY) > honest.ledger.total(COUNTERPARTY)
    # The gap is the open problem. If it ever closes, say why.
    assert probing.ledger.total(COUNTERPARTY) > 9.0


# -- the mitigation sweep ---------------------------------------------------

def test_the_coarsening_of_section_15_4_stops_no_inference():
    """The finding that produced SPEC-ISSUES S-12.

    Coarsening an affirmative local answer replaces one deterministic result
    with another. The adversary's partition of the hypothesis space is
    unchanged, so the leakage is identical to answering plainly.
    """
    for budget in (4, 8, 16, 64):
        plain, _ = probe(POLICIES["truthful (no coarsening)"], budget)
        coarsened, _ = probe(POLICIES["default (spec 15.4)"], budget)
        assert coarsened == pytest.approx(plain)


def test_the_degenerate_policies_are_degenerate():
    """Leaking nothing is easy; leaking nothing usefully is the problem."""
    for name in ("coarsen all local", "decline all local"):
        bits, _ = probe(POLICIES[name], 64)
        tpr, tnr = discrimination(POLICIES[name], 64)
        assert bits == 0.0
        assert min(tpr, tnr) == 0.0, f"{name} should be useless in one direction"


def test_randomisation_delays_and_does_not_bound():
    """It buys queries. Repetition buys them back."""
    early, _ = probe(POLICIES["randomised 50%"], 8)
    late, _ = probe(POLICIES["randomised 50%"], 64)
    plain, _ = probe(POLICIES["truthful (no coarsening)"], 8)
    assert early < plain
    assert late == pytest.approx(
        probe(POLICIES["truthful (no coarsening)"], 64)[0]
    )


def test_randomisation_costs_discrimination():
    _, tnr_random = discrimination(POLICIES["randomised 50%"], 64)
    _, tnr_plain = discrimination(POLICIES["truthful (no coarsening)"], 64)
    assert tnr_random < tnr_plain


def test_a_budget_is_the_only_lever_that_bounds():
    for name, policy in POLICIES.items():
        small, _ = probe(policy, 4)
        large, _ = probe(policy, 64)
        assert small <= large
    bounded, _ = probe(POLICIES["default (spec 15.4)"], 4)
    unbounded, _ = probe(POLICIES["default (spec 15.4)"], 64)
    assert bounded < unbounded
