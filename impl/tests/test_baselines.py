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
    for mechanism in (
        public_posting,
        sealed_one_shot,
        private_set_intersection,
        cid_honest,
    ):
        assert mechanism().third_party is None


def test_the_intermediary_learns_everything():
    outcome = trusted_broker()
    total = sum(f.total_bits for f in FACTS)
    assert outcome.ledger.total(OPERATOR) == pytest.approx(total)
    assert len(outcome.ledger.exact(OPERATOR)) == len(FACTS)


def test_only_publication_leaks_to_an_unbounded_audience():
    assert public_posting().ledger.total(PUBLIC) > 0
    for mechanism in (
        trusted_broker,
        sealed_one_shot,
        private_set_intersection,
        cid_honest,
        cid_adversarial,
    ):
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
    assert late == pytest.approx(probe(POLICIES["truthful (no coarsening)"], 64)[0])


def test_randomisation_costs_discrimination():
    _, tnr_random = discrimination(POLICIES["randomised 50%"], 64)
    _, tnr_plain = discrimination(POLICIES["truthful (no coarsening)"], 64)
    assert tnr_random < tnr_plain


def test_a_budget_is_the_only_lever_that_bounds():
    for policy in POLICIES.values():
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
    matchable = sum(1 for q in asks for c in people if truly_relevant(c, q))

    def recall(level) -> float:
        found = sum(
            1
            for q in asks
            for c in people
            if level.matches(c, q) and truly_relevant(c, q)
        )
        return found / matchable

    assert recall(LEVELS[0]) < recall(LEVELS[1]), (
        "the most precise projection should find fewer of its own matches"
    )


def test_the_coarsest_projection_drains_the_publisher():
    from baselines.projection import (
        LEVELS,
        PRIVATE_BITS,
        SESSION_BITS,
        population,
        queries,
    )

    people, asks = population(800), queries(120)
    retrievals = sum(1 for q in asks for c in people if LEVELS[-1].matches(c, q))
    sessions = retrievals / len(people)
    assert sessions * SESSION_BITS > PRIVATE_BITS, (
        "publishing only a category should expose the publisher to more "
        "sessions than its private facts can survive"
    )


def test_resolving_one_hierarchy_removes_the_recall_penalty():
    """The recall cost of a precise projection is the provider's, not the
    protocol's: it disappears with one hierarchy and no ontology."""
    from baselines.projection import (
        LEVELS,
        population,
        queries,
        resolving,
        truly_relevant,
    )

    people, asks = population(800), queries(120)
    matchable = sum(1 for q in asks for c in people if truly_relevant(c, q))

    def recall(level) -> float:
        return (
            sum(
                1
                for q in asks
                for c in people
                if level.matches(c, q) and truly_relevant(c, q)
            )
            / matchable
        )

    plain = recall(LEVELS[0])
    resolved = recall(resolving(LEVELS[0]))
    assert plain < 0.5
    assert resolved > 0.95
    # And the publisher conceded exactly as much to the index either way.
    assert resolving(LEVELS[0]).projection_bits == LEVELS[0].projection_bits


# -- simulatability, in the sense of [KMN2005] -----------------------------


def test_the_policy_the_specification_illustrates_is_the_only_leaky_decision():
    """Section 15.4's coarsening consults the secret to decide; the others
    do not. This is the general reason behind S-12."""
    from baselines.mitigations import simulatability_report

    report = simulatability_report()
    assert report["default (spec 15.4)"] is False
    for name, simulatable in report.items():
        if name != "default (spec 15.4)":
            assert simulatable, f"{name} unexpectedly consults the private value"


def test_a_non_simulatable_decision_leaks_as_much_as_no_concealment():
    """The claim the classification makes, checked against the measurement."""
    from baselines.mitigations import probe

    leaky, _ = probe(POLICIES["default (spec 15.4)"], 64)
    plain, _ = probe(POLICIES["truthful (no coarsening)"], 64)
    assert leaky == pytest.approx(plain)


# -- when a budget separates an adversary from a customer ------------------


def test_a_separating_budget_exists_once_the_secret_is_large_enough():
    """The correction to a statement made too broadly.

    The Sybil demonstration reported that no cap both stopped the attacker
    and served the honest counterparty. That held for its own scenario — 41
    candidate values against a five-claim session — and was stated as though
    it held generally. It does not: the window opens as the secret grows.
    """
    from baselines.separability import extraction_cost

    honest = 5
    assert extraction_cost(41) <= honest, (
        "the worked case should be the narrow one that has no window"
    )
    assert extraction_cost(128) > honest
    assert extraction_cost(2048) > extraction_cost(128), (
        "extraction should grow with the entropy of what is protected"
    )


def test_extraction_cost_is_measured_not_assumed():
    """Not log2 by assertion: a bisection over a grid need not land on a
    power of two, and the demonstration's five-question extraction over 41
    values was one such case."""
    from math import log2

    from baselines.separability import extraction_cost

    for candidates in (8, 41, 512):
        cost = extraction_cost(candidates)
        assert cost <= log2(candidates) + 1


# -- a rate against a moving value -----------------------------------------


def test_a_throttle_alone_only_delays():
    """Twelve periods at one question each is twelve questions, and twelve
    questions are more than this secret is worth."""
    from math import log2

    from baselines.drift import GRID, run

    bits, _ = run(periods=12, per_period=1, drift_steps=0, aware=True)
    assert bits == pytest.approx(log2(len(GRID)))


def test_drift_preserves_uncertainty_only_against_a_slow_adversary():
    """Exponential in the rate, linear in the movement: halving the first
    is worth more than doubling the second."""
    from baselines.drift import run

    slow, _ = run(periods=12, per_period=1, drift_steps=4, aware=True)
    fast, _ = run(periods=12, per_period=4, drift_steps=4, aware=True)
    assert slow < fast, "a lower rate must leave the adversary knowing less"
    assert slow < 4.0, "a throttled adversary should not get everything"


def test_an_adversary_that_ignores_drift_ends_confident_and_wrong():
    """The finding worth keeping: it does not end uncertain."""
    from baselines.drift import run

    bits, correct = run(periods=12, per_period=1, drift_steps=4, aware=False)
    assert bits > 4.0, "the naive adversary believes it has narrowed"
    assert not correct, "and its belief is false"


# -- a budget in bits, audited simulatably ---------------------------------


def test_budgeting_bits_bounds_the_extractor():
    """What budgeting questions could not do."""
    from baselines.auditing import Auditor, extractor

    auditor = Auditor(budget_bits=2.0)
    extractor(auditor, 45_000_000)
    assert auditor.disclosed <= 2.0
    assert auditor.refusals >= 1


def test_the_same_budget_still_serves_most_honest_counterparties():
    """The separation the question-count budget could not produce."""
    from baselines.auditing import Auditor, honest

    auditor = Auditor(budget_bits=2.0)
    served = honest(auditor, 45_000_000, counterparties=40)
    assert served >= 30, f"only {served} of 40 honest counterparties served"


def test_the_refusal_does_not_depend_on_the_value():
    """Simulatability, checked: the same claim sequence must be admitted or
    refused identically whatever the responder happens to hold."""
    from baselines.auditing import GRID, Auditor
    from gidp.objects import Claim
    from gidp.vocab import ClaimOperator

    claim = Claim(
        key="valuation_floor",
        operator=ClaimOperator.WITHIN,
        value={"min": 60_000_000, "max": 60_000_000},
    )
    decisions = set()
    for floor in (0, 45_000_000, 200_000_000):
        auditor = Auditor(budget_bits=1.0)
        assert floor in GRID
        decisions.add(auditor.admits(claim))
    assert len(decisions) == 1, (
        "the decision to refuse must not be a function of the protected value"
    )


# -- the bound-utility frontier --------------------------------------------


def test_counting_questions_is_dominated():
    """Every question-count budget is beaten on both axes by something else.

    This is the whole argument of the last several findings, as an assertion:
    if a question budget ever reappears on the frontier, something changed
    and the reasoning needs revisiting.
    """
    from baselines.frontier import (
        BitBudget,
        Policy,
        QuestionBudget,
        measure,
    )

    question = measure(lambda: QuestionBudget("q", limit=4))
    bits = measure(lambda: BitBudget("b", budget=2.0))
    assert bits[0] <= question[0] and bits[1] > question[1], (
        f"bit budget {bits} should beat question budget {question}"
    )
    assert measure(lambda: Policy("none"))[1] == 40


def test_a_granularity_lattice_bounds_without_refusing_anyone():
    """The result the earlier dismissal missed: it holds no state, so honest
    traffic cannot deplete it."""
    from baselines.frontier import GranularityFloor, measure

    leak, served = measure(lambda: GranularityFloor("g", width=40_000_000))
    assert served == 40, "a lattice costs precision, not service"
    assert leak < 3.0, "and it still caps the resolution"


def test_the_lattice_caps_resolution_however_many_questions_are_asked():
    """Statelessness, checked: forty times the probing makes no difference."""
    from baselines.frontier import GranularityFloor, _probe

    short = _probe(GranularityFloor("g", width=40_000_000), attempts=4)
    long = _probe(GranularityFloor("g", width=40_000_000), attempts=400)
    assert short == pytest.approx(long)
