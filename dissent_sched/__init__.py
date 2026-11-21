"""dissent_sched: dissent scheduling for multi-agent debates.

Diagnoses which failure pathway (sycophantic conformity, fragility,
consensus collapse) is losing correct answers in a seeded multi-agent
debate, searches dissent schedules (mode, trigger, dissenter) on
calibration cases, and prices every schedule in tokens as oracle-gap
closure per 1k tokens.

Author: Amna Raheeba
"""

from .audit import diagnose
from .generate import build_scenario, calibrate_skills, generate_cases
from .models import Agent, CaseFixture, Scenario
from .schedule import Schedule, schedule_space, search_schedules
from .simulate import (
    gap_closure,
    oracle_accuracy,
    run_debate,
    run_no_debate,
    run_policy,
)

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "CaseFixture",
    "Scenario",
    "Schedule",
    "calibrate_skills",
    "build_scenario",
    "diagnose",
    "gap_closure",
    "generate_cases",
    "oracle_accuracy",
    "run_debate",
    "run_no_debate",
    "run_policy",
    "schedule_space",
    "search_schedules",
]
