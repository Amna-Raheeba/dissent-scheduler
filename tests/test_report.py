from dissent_sched.audit import diagnose
from dissent_sched.generate import (
    build_scenario,
    calibrate_skills,
    generate_cases,
)
from dissent_sched.report import (
    audit_report_markdown,
    policy_report_markdown,
    schedule_report_markdown,
)
from dissent_sched.schedule import search_schedules


def _diagnosed_scenario():
    scenario = build_scenario(5, "medium", 7)
    calibrate_skills(scenario, 60)
    fixtures = generate_cases(scenario, 80, "calibration")
    return scenario, diagnose(scenario, fixtures, 4)


def test_audit_report_contents():
    scenario, diagnosis = _diagnosed_scenario()
    text = audit_report_markdown(scenario, diagnosis)
    assert "Failure-pathway audit: medium-5" in text
    assert "sycophantic_conformity" in text
    assert "consensus_collapse" in text
    assert "recommended dissent mode" in text


def test_schedule_report_contents():
    scenario, diagnosis = _diagnosed_scenario()
    search = search_schedules(
        [scenario], rounds=4, n_calibration=80, n_probe=60
    )
    text = schedule_report_markdown(scenario, search, diagnosis)
    assert "Dissent schedule search: medium-5" in text
    assert "Chosen schedule:" in text
    assert "closure per 1k tokens" in text
    assert search["best"]["key"] in text


def test_policy_report_contents():
    rows = [
        {"policy": "no_debate", "accuracy": 0.6, "mean_tokens": 240.0,
         "gap_closure": 0.0, "closure_per_1k_tokens": 0.0},
        {"policy": "scheduled (anchor:contested:top_skill)",
         "accuracy": 0.7, "mean_tokens": 900.0, "gap_closure": 0.25,
         "closure_per_1k_tokens": 0.27},
    ]
    scenario = build_scenario(5, "medium", 7)
    text = policy_report_markdown(scenario, rows)
    assert "Policy comparison: medium-5" in text
    assert "anchor:contested:top_skill" in text
    assert "0.700" in text
