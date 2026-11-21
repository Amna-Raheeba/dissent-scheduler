from dissent_sched.generate import build_scenario, calibrate_skills
from dissent_sched.schedule import (
    DISSENTERS,
    MODES,
    TRIGGERS,
    Schedule,
    evaluate_schedule,
    schedule_space,
    search_schedules,
)
from dissent_sched.generate import generate_cases
from dissent_sched.simulate import oracle_accuracy, run_policy


def test_schedule_key_and_dict_round_trip():
    schedule = Schedule("anchor", "contested", "random")
    assert schedule.key() == "anchor:contested:random"
    clone = Schedule.from_dict(schedule.to_dict())
    assert clone.mode == "anchor"
    assert clone.trigger == "contested"
    assert clone.dissenter == "random"


def test_schedule_space_size_and_coverage():
    space = schedule_space()
    assert len(space) == 20
    keys = set(s.key() for s in space)
    assert len(keys) == 20
    for mode in MODES:
        for trigger in TRIGGERS:
            if mode in ("revival", "shield"):
                assert "%s:%s:top_skill" % (mode, trigger) in keys
            else:
                for dissenter in DISSENTERS:
                    assert "%s:%s:%s" % (mode, trigger, dissenter) in keys


def test_evaluate_schedule_fields():
    scenario = build_scenario(5, "medium", 5)
    calibrate_skills(scenario, 30)
    fixtures = generate_cases(scenario, 20, "calibration")
    baseline = run_policy(
        scenario, fixtures, 4, policy_key="no_debate"
    )["accuracy"]
    oracle = oracle_accuracy(fixtures)
    row = evaluate_schedule(
        scenario, fixtures, Schedule("shield", "every_round"), 4,
        baseline, oracle,
    )
    assert row["key"] == "shield:every_round:top_skill"
    assert 0.0 <= row["accuracy"] <= 1.0
    assert row["mean_tokens"] > 0
    assert row["mean_dissent_events"] == 4.0


def test_search_schedules_structure():
    scenario = build_scenario(3, "low", 5)
    search = search_schedules(
        [scenario], rounds=3, n_calibration=20, n_probe=20
    )
    assert len(search["table"]) == 20
    best = search["best"]
    assert best is search["table"][0]
    assert best["closure_per_1k_tokens"] >= \
        search["table"][-1]["closure_per_1k_tokens"]
    assert search["best_by_accuracy"]["accuracy"] >= best["accuracy"]


def test_search_schedules_deterministic():
    scenario = build_scenario(3, "low", 5)
    first = search_schedules(
        [scenario], rounds=3, n_calibration=20, n_probe=20
    )
    second = search_schedules(
        [scenario], rounds=3, n_calibration=20, n_probe=20
    )
    assert first["best"]["key"] == second["best"]["key"]
    assert first["best"]["accuracy"] == second["best"]["accuracy"]


def test_search_calibrates_skills_when_missing():
    scenario = build_scenario(3, "medium", 5)
    assert all(a.estimated_skill is None for a in scenario.agents)
    search_schedules([scenario], rounds=2, n_calibration=10, n_probe=20)
    assert all(a.estimated_skill is not None for a in scenario.agents)
