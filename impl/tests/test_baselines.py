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


# -- Section 24.4, the Sybil demonstration ---------------------------------

def test_a_per_counterparty_budget_bounds_nothing_against_many_identities():
    """The bits track budget times identities, not the budget."""
    from baselines.sybil import probe_with_identities

    policy = POLICIES["default (spec 15.4)"]
    alone = probe_with_identities(policy, per_counterparty=2, identities=1)
    crowd = probe_with_identities(policy, per_counterparty=2, identities=8)
    assert alone.bits < crowd.bits
    assert crowd.bits == pytest.approx(
        probe_with_identities(policy, per_counterparty=8, identities=1).bits
    )


def test_a_global_cap_bounds_and_the_price_is_the_shop():
    """A cap not keyed to the asker cannot be diluted by identities, and
    cannot tell an adversary from a customer either."""
    from baselines.sybil import honest_sessions_served, probe_with_identities

    policy = POLICIES["default (spec 15.4)"]
    tight = probe_with_identities(policy, 6, identities=64, global_budget=4)
    loose = probe_with_identities(policy, 6, identities=64, global_budget=24)
    assert tight.bits < loose.bits
    # Tight enough to stop the extraction is tight enough to serve nobody.
    assert honest_sessions_served(policy, 6, 4) == 0
    assert honest_sessions_served(policy, 6, 24) > 0


# -- Section 11.4, the projection trade-off --------------------------------

def test_an_over_precise_projection_is_retrieved_less():
    """The result Section 11.4 does not lead a reader to expect."""
    from baselines.projection import LEVELS, population, queries, truly_relevant

    people, asks = population(800), queries(120)
    matchable = sum(
        1 for q in asks for c in people if truly_relevant(c, q)
    )

    def recall(level) -> float:
        found = sum(
            1 for q in asks for c in people
            if level.matches(c, q) and truly_relevant(c, q)
        )
        return found / matchable

    assert recall(LEVELS[0]) < recall(LEVELS[1]), (
        "the most precise projection should find fewer of its own matches"
    )


def test_the_coarsest_projection_drains_the_publisher():
    from baselines.projection import (
        LEVELS, PRIVATE_BITS, SESSION_BITS, population, queries,
    )

    people, asks = population(800), queries(120)
    retrievals = sum(
        1 for q in asks for c in people if LEVELS[-1].matches(c, q)
    )
    sessions = retrievals / len(people)
    assert sessions * SESSION_BITS > PRIVATE_BITS, (
        "publishing only a category should expose the publisher to more "
        "sessions than its private facts can survive"
    )


def test_resolving_one_hierarchy_removes_the_recall_penalty():
    """The recall cost of a precise projection is the provider's, not the
    protocol's: it disappears with one hierarchy and no ontology."""
    from baselines.projection import (
        LEVELS, population, queries, resolving, truly_relevant,
    )

    people, asks = population(800), queries(120)
    matchable = sum(1 for q in asks for c in people if truly_relevant(c, q))

    def recall(level) -> float:
        return sum(
            1 for q in asks for c in people
            if level.matches(c, q) and truly_relevant(c, q)
        ) / matchable

    plain = recall(LEVELS[0])
    resolved = recall(resolving(LEVELS[0]))
    assert plain < 0.5
    assert resolved > 0.95
    # And the publisher conceded exactly as much to the index either way.
    assert resolving(LEVELS[0]).projection_bits == LEVELS[0].projection_bits
