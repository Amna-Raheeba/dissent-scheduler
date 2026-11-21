from dissent_sched.models import (
    Agent,
    CaseFixture,
    Scenario,
    derive_seed,
    plurality,
    vote_share,
)


def test_derive_seed_deterministic_and_distinct():
    assert derive_seed("a", 1) == derive_seed("a", 1)
    assert derive_seed("a", 1) != derive_seed("a", 2)
    assert derive_seed("a", 1) != derive_seed("b", 1)
    assert 0 <= derive_seed("x") <= 0xFFFFFFFF


def test_plurality_simple_majority():
    assert plurality([0, 1, 1, 2, 1]) == 1
    assert plurality([3, 3, 3]) == 3


def test_plurality_tie_breaks_by_round_zero_support():
    # 0 and 1 tie at two votes each; round 0 favoured 1.
    assert plurality([0, 0, 1, 1], [1, 1, 1, 0]) == 1
    assert plurality([0, 0, 1, 1], [0, 0, 0, 1]) == 0


def test_plurality_tie_breaks_by_lowest_index_last():
    assert plurality([2, 2, 1, 1], [2, 1]) == 1
    assert plurality([2, 0]) == 0


def test_vote_share():
    assert vote_share([1, 1, 0, 2], 1) == 0.5
    assert vote_share([1, 1, 0, 2], 3) == 0.0
    assert vote_share([], 1) == 0.0


def test_agent_dict_round_trip():
    agent = Agent(skill=0.7, conformity=0.4, fragility=0.2,
                  estimated_skill=0.65)
    clone = Agent.from_dict(agent.to_dict())
    assert clone.skill == 0.7
    assert clone.conformity == 0.4
    assert clone.fragility == 0.2
    assert clone.estimated_skill == 0.65


def test_agent_estimated_skill_defaults_none():
    agent = Agent(skill=0.5, conformity=0.5, fragility=0.5)
    assert agent.estimated_skill is None
    assert Agent.from_dict(agent.to_dict()).estimated_skill is None


def test_scenario_dict_round_trip():
    scenario = Scenario(
        name="medium-3",
        agents=[Agent(0.6, 0.3, 0.2), Agent(0.5, 0.4, 0.3),
                Agent(0.7, 0.2, 0.1)],
        distractor_pull=0.4,
        seed=42,
    )
    clone = Scenario.from_dict(scenario.to_dict())
    assert clone.name == "medium-3"
    assert clone.n_agents == 3
    assert clone.distractor_pull == 0.4
    assert clone.seed == 42
    assert clone.agents[2].skill == 0.7


def test_case_fixture_correct_present():
    fixture = CaseFixture(case_id=0, correct=2, distractor=1,
                          private_answers=[0, 2, 1])
    assert fixture.correct_present
    absent = CaseFixture(case_id=1, correct=3, distractor=1,
                         private_answers=[0, 2, 1])
    assert not absent.correct_present


def test_case_fixture_dict_round_trip():
    fixture = CaseFixture(case_id=5, correct=1, distractor=0,
                          private_answers=[1, 0, 0, 2])
    clone = CaseFixture.from_dict(fixture.to_dict())
    assert clone.case_id == 5
    assert clone.correct == 1
    assert clone.distractor == 0
    assert clone.private_answers == [1, 0, 0, 2]
