from dissent_sched.generate import (
    build_scenario,
    build_team,
    calibrate_skills,
    generate_case,
    generate_cases,
    top_skill_agent,
)
from dissent_sched.models import DIVERSITY_PROFILES


def test_build_team_sizes():
    for n in (3, 5, 7, 10):
        assert len(build_team(n, "medium", 11)) == n


def test_build_team_parameter_ranges():
    for diversity, profile in DIVERSITY_PROFILES.items():
        for agent in build_team(10, diversity, 3):
            assert profile["skill_lo"] <= agent.skill <= profile["skill_hi"]
            assert 0.25 <= agent.conformity <= 0.60
            assert 0.10 <= agent.fragility <= 0.50


def test_build_team_deterministic():
    first = build_team(5, "high", 99)
    second = build_team(5, "high", 99)
    assert [a.skill for a in first] == [a.skill for a in second]
    other = build_team(5, "high", 100)
    assert [a.skill for a in first] != [a.skill for a in other]


def test_build_scenario_fields():
    scenario = build_scenario(7, "low", 5)
    assert scenario.name == "low-7"
    assert scenario.n_agents == 7
    assert scenario.distractor_pull == \
        DIVERSITY_PROFILES["low"]["distractor_pull"]


def test_generate_case_validity():
    scenario = build_scenario(5, "medium", 5)
    for case_id in range(30):
        fixture = generate_case(scenario, case_id, "evaluation")
        assert 0 <= fixture.correct < 4
        assert 0 <= fixture.distractor < 4
        assert fixture.distractor != fixture.correct
        assert len(fixture.private_answers) == 5
        assert all(0 <= a < 4 for a in fixture.private_answers)


def test_generate_case_deterministic():
    scenario = build_scenario(5, "medium", 5)
    first = generate_case(scenario, 3, "evaluation")
    second = generate_case(scenario, 3, "evaluation")
    assert first.private_answers == second.private_answers
    assert first.correct == second.correct


def test_generate_case_streams_differ():
    scenario = build_scenario(5, "medium", 5)
    eval_fixture = generate_case(scenario, 3, "evaluation")
    calib_fixture = generate_case(scenario, 3, "calibration")
    assert (eval_fixture.correct, eval_fixture.private_answers) != \
        (calib_fixture.correct, calib_fixture.private_answers)


def test_generate_cases_count():
    scenario = build_scenario(3, "high", 5)
    fixtures = generate_cases(scenario, 17, "evaluation")
    assert len(fixtures) == 17
    assert [f.case_id for f in fixtures] == list(range(17))


def test_distractor_pull_shapes_private_answers():
    # A perfect-skill team is always privately correct regardless of pull.
    scenario = build_scenario(5, "low", 5)
    for agent in scenario.agents:
        agent.skill = 1.0
    for fixture in generate_cases(scenario, 20, "evaluation"):
        assert all(a == fixture.correct
                   for a in fixture.private_answers)


def test_calibrate_skills_sets_estimates():
    scenario = build_scenario(5, "medium", 5)
    estimates = calibrate_skills(scenario, 60)
    assert len(estimates) == 5
    for agent, estimate in zip(scenario.agents, estimates):
        assert agent.estimated_skill == estimate
        assert 0.0 <= estimate <= 1.0


def test_calibrate_skills_tracks_skill_loosely():
    scenario = build_scenario(3, "high", 5)
    scenario.agents[0].skill = 1.0
    scenario.agents[1].skill = 0.0
    estimates = calibrate_skills(scenario, 60)
    assert estimates[0] == 1.0
    assert estimates[1] == 0.0


def test_top_skill_agent_uses_estimates():
    scenario = build_scenario(4, "medium", 5)
    for index, agent in enumerate(scenario.agents):
        agent.estimated_skill = 0.1 * index
    assert top_skill_agent(scenario) == 3
    scenario.agents[0].estimated_skill = 0.99
    assert top_skill_agent(scenario) == 0
