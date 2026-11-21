import pytest

from dissent_sched.generate import build_scenario, generate_cases
from dissent_sched.models import (
    DISSENT_TOKENS,
    STATEMENT_TOKENS,
    Agent,
    CaseFixture,
    Scenario,
)
from dissent_sched.schedule import Schedule
from dissent_sched.simulate import (
    gap_closure,
    oracle_accuracy,
    run_debate,
    run_no_debate,
    run_policy,
)


def _rigid_scenario(conformity=0.0, fragility=0.0, n=3):
    agents = [
        Agent(skill=0.5, conformity=conformity, fragility=fragility,
              estimated_skill=0.5)
        for _ in range(n)
    ]
    return Scenario(name="rigid-%d" % n, agents=agents,
                    distractor_pull=0.0, seed=1)


def test_no_debate_plurality_and_tokens():
    scenario = _rigid_scenario()
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 2])
    result = run_no_debate(scenario, fixture)
    assert result.final_answer == 2
    assert result.correct
    assert result.tokens == 3 * STATEMENT_TOKENS
    assert result.dissent_events == 0


def test_no_debate_wrong_plurality():
    scenario = _rigid_scenario()
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[1, 1, 2])
    result = run_no_debate(scenario, fixture)
    assert result.final_answer == 1
    assert not result.correct


def test_free_debate_static_when_no_pressure():
    # Zero conformity and zero fragility: nobody ever flips.
    scenario = _rigid_scenario(conformity=0.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 2])
    result = run_debate(scenario, fixture, 4)
    assert result.final_answer == 2
    assert result.flips == []
    assert result.tokens == 3 * STATEMENT_TOKENS * 5
    assert len(result.snapshots) == 5


def test_free_debate_deterministic():
    scenario = build_scenario(5, "medium", 5)
    fixture = generate_cases(scenario, 1, "evaluation")[0]
    first = run_debate(scenario, fixture, 4)
    second = run_debate(scenario, fixture, 4)
    assert first.final_answer == second.final_answer
    assert first.flips == second.flips
    assert first.tokens == second.tokens


def test_conformity_certain_flips_to_plurality():
    # Conformity 1.0: every dissenter from the plurality flips round 1.
    scenario = _rigid_scenario(conformity=1.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[1, 1, 2])
    result = run_debate(scenario, fixture, 4)
    assert result.snapshots[1] == [1, 1, 1]
    assert result.final_answer == 1
    assert result.extinct_round == 1
    assert all(f["channel"] == "conformity" for f in result.flips)


def test_fragility_certain_flip_under_full_pressure():
    # The single correct holder faces two peers on the leading wrong
    # answer: pressure 1.0 and fragility 1.0 make the flip certain.
    scenario = _rigid_scenario(conformity=0.0, fragility=1.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 1])
    result = run_debate(scenario, fixture, 1)
    assert result.snapshots[1] == [1, 1, 1]
    assert len(result.flips) == 1
    assert result.flips[0]["channel"] == "fragility"


def test_anchor_dissenter_holds_and_is_charged():
    scenario = _rigid_scenario(conformity=1.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 1])
    schedule = Schedule("anchor", "every_round", "top_skill")
    result = run_debate(scenario, fixture, 2, schedule=schedule,
                        policy_key=schedule.key())
    # Agent 0 is the top-skill dissenter (all estimates tie at 0.5, so
    # the lowest index wins) and holds the correct answer throughout.
    assert all(snapshot[0] == 2 for snapshot in result.snapshots)
    assert result.dissent_events == 2
    assert result.tokens == (
        3 * STATEMENT_TOKENS * 3 + 2 * DISSENT_TOKENS
    )


def test_shield_reduces_fragility_flips():
    scenario = build_scenario(7, "low", 5)
    for agent in scenario.agents:
        agent.conformity = 0.0
        agent.fragility = 1.0
        agent.estimated_skill = 0.5
    fixtures = generate_cases(scenario, 40, "evaluation")

    def fragility_flips(schedule):
        total = 0
        for fixture in fixtures:
            result = run_debate(
                scenario, fixture, 4, schedule=schedule,
                policy_key=schedule.key() if schedule else "free",
            )
            total += sum(
                1 for f in result.flips if f["channel"] == "fragility"
            )
        return total

    unshielded = fragility_flips(None)
    shielded = fragility_flips(Schedule("shield", "every_round"))
    assert unshielded > 0
    assert shielded < unshielded


def test_revival_reseats_extinct_answer():
    scenario = _rigid_scenario(conformity=1.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 1])
    free = run_debate(scenario, fixture, 4)
    assert free.extinct_round == 1
    schedule = Schedule("revival", "every_round")
    revived = run_debate(scenario, fixture, 4, schedule=schedule,
                         policy_key=schedule.key())
    assert revived.dissent_events >= 1
    assert any(2 in snapshot for snapshot in revived.snapshots[1:])


def test_extinct_trigger_only_fires_when_needed():
    scenario = _rigid_scenario(conformity=0.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 1, 2])
    schedule = Schedule("shield", "extinct")
    result = run_debate(scenario, fixture, 4, schedule=schedule,
                        policy_key=schedule.key())
    assert result.dissent_events == 0


def test_contested_trigger_respects_share():
    scenario = _rigid_scenario(conformity=0.0, fragility=0.0)
    fixture = CaseFixture(0, correct=2, distractor=1,
                          private_answers=[2, 2, 2])
    schedule = Schedule("shield", "contested")
    result = run_debate(scenario, fixture, 4, schedule=schedule,
                        policy_key=schedule.key())
    assert result.dissent_events == 0


def test_run_policy_aggregates():
    scenario = build_scenario(5, "medium", 5)
    fixtures = generate_cases(scenario, 25, "evaluation")
    metrics = run_policy(scenario, fixtures, 4, policy_key="no_debate")
    assert metrics["n_cases"] == 25
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["mean_tokens"] == 5 * STATEMENT_TOKENS
    assert metrics["results"] == []
    with_results = run_policy(
        scenario, fixtures, 4, policy_key="no_debate", keep_results=True
    )
    assert len(with_results["results"]) == 25


def test_oracle_accuracy():
    fixtures = [
        CaseFixture(0, correct=1, distractor=0, private_answers=[1, 0]),
        CaseFixture(1, correct=2, distractor=0, private_answers=[0, 0]),
        CaseFixture(2, correct=3, distractor=0, private_answers=[3, 1]),
    ]
    assert oracle_accuracy(fixtures) == 2.0 / 3.0
    assert oracle_accuracy([]) == 0.0


def test_gap_closure_math():
    assert gap_closure(0.8, 0.6, 1.0) == pytest.approx(0.5)
    assert gap_closure(0.6, 0.6, 1.0) == pytest.approx(0.0)
    assert gap_closure(0.5, 0.6, 1.0) < 0.0
    # Degenerate denominator is guarded.
    assert gap_closure(0.9, 0.9, 0.9) == 0.0
