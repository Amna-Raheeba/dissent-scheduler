"""Run the pathway audit on the bundled demo scenario and print it.

Run: python examples/run_audit.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dissent_sched.audit import diagnose
from dissent_sched.generate import calibrate_skills, generate_cases
from dissent_sched.models import Scenario
from dissent_sched.report import audit_report_markdown


def main():
    path = os.path.join(os.path.dirname(__file__), "demo_scenario.json")
    with open(path) as handle:
        scenario = Scenario.from_dict(json.load(handle))
    calibrate_skills(scenario, 60)
    calibration = generate_cases(scenario, 80, "calibration")
    diagnosis = diagnose(scenario, calibration, 4)
    print(audit_report_markdown(scenario, diagnosis))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
