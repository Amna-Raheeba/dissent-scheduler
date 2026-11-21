"""Demo: diagnose a team, search its dissent schedule, compare policies.

The demo team is five agents of medium diversity: a planted distractor
pulls missed answers together, so a wrong majority can form, and the
debate dynamics have something to lose -- and dissent something to
rescue.

Run: python notebooks/01_demo_run.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dissent_sched.audit import diagnose
from dissent_sched.cli import DEMO_ROUNDS
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
from dissent_sched.cli import _demo_policy_rows
from dissent_sched.schedule import search_schedules


def main():
    scenario = build_scenario(5, "medium", 7)
    calibrate_skills(scenario, 60)
    calibration = generate_cases(scenario, 80, "calibration")
    diagnosis = diagnose(scenario, calibration, DEMO_ROUNDS)
    print(audit_report_markdown(scenario, diagnosis))
    search = search_schedules(
        [scenario], rounds=DEMO_ROUNDS, n_calibration=80, n_probe=60
    )
    print(schedule_report_markdown(scenario, search, diagnosis))
    _, rows = _demo_policy_rows(scenario)
    print(policy_report_markdown(scenario, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
