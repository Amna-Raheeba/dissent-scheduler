"""Command line interface.

Usage:
    python -m dissent_sched demo
    python -m dissent_sched schedule --scenario examples/demo_scenario.json
    python -m dissent_sched audit --scenario examples/demo_scenario.json
    python -m dissent_sched evaluate --outdir results
"""

import argparse
import json

from .audit import diagnose
from .evaluate import run_evaluation, write_results
from .generate import build_scenario, calibrate_skills, generate_cases
from .models import Scenario
from .report import (
    audit_report_markdown,
    policy_report_markdown,
    schedule_report_markdown,
)
from .schedule import Schedule, search_schedules
from .simulate import gap_closure, oracle_accuracy, run_policy

DEMO_SCENARIO = build_scenario(5, "medium", 7)
DEMO_ROUNDS = 4


def _demo_policy_rows(scenario):
    calibrate_skills(scenario, 60)
    search = search_schedules(
        [scenario], rounds=DEMO_ROUNDS, n_calibration=80, n_probe=60
    )
    scheduled = Schedule.from_dict(search["best"]["schedule"])
    fixtures = generate_cases(scenario, 60, "evaluation")
    oracle = oracle_accuracy(fixtures)
    policies = [
        ("no_debate", None),
        ("free_debate", None),
        ("scheduled", scheduled),
    ]
    rows = []
    baseline = None
    for name, schedule in policies:
        metrics = run_policy(
            scenario, fixtures, DEMO_ROUNDS,
            schedule=schedule, policy_key=name,
        )
        if name == "no_debate":
            baseline = metrics["accuracy"]
        closure = gap_closure(metrics["accuracy"], baseline, oracle)
        rows.append({
            "policy": name if schedule is None else
            "scheduled (%s)" % schedule.key(),
            "accuracy": metrics["accuracy"],
            "mean_tokens": metrics["mean_tokens"],
            "gap_closure": closure,
            "closure_per_1k_tokens": (
                closure / metrics["mean_tokens"] * 1000.0
                if metrics["mean_tokens"] else 0.0
            ),
        })
    return search, rows


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dissent_sched",
        description=(
            "Schedule dissent in multi-agent debates: diagnose which "
            "failure pathway is losing correct answers, search dissent "
            "schedules on calibration cases, and price every policy "
            "in tokens."
        ),
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("demo", help="Diagnose and schedule a built-in demo team")

    sched_parser = sub.add_parser(
        "schedule", help="Search dissent schedules for a scenario JSON"
    )
    sched_parser.add_argument("--scenario", required=True,
                              help="Scenario JSON path")

    audit_parser = sub.add_parser(
        "audit", help="Diagnose failure pathways for a scenario JSON"
    )
    audit_parser.add_argument("--scenario", required=True,
                              help="Scenario JSON path")

    eval_parser = sub.add_parser(
        "evaluate", help="Run the headline evaluation and write results"
    )
    eval_parser.add_argument("--outdir", default="results")
    return parser


def _load_scenario(path):
    with open(path) as handle:
        return Scenario.from_dict(json.load(handle))


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "demo":
        scenario = build_scenario(5, "medium", 7)
        calibrate_skills(scenario, 60)
        calibration = generate_cases(scenario, 80, "calibration")
        diagnosis = diagnose(scenario, calibration, DEMO_ROUNDS)
        search, rows = _demo_policy_rows(scenario)
        print(audit_report_markdown(scenario, diagnosis))
        print(schedule_report_markdown(scenario, search, diagnosis))
        print(policy_report_markdown(scenario, rows))
        return 0
    if args.command == "schedule":
        scenario = _load_scenario(args.scenario)
        calibrate_skills(scenario, 60)
        calibration = generate_cases(scenario, 80, "calibration")
        diagnosis = diagnose(scenario, calibration, DEMO_ROUNDS)
        search = search_schedules(
            [scenario], rounds=DEMO_ROUNDS, n_calibration=80, n_probe=60
        )
        print(schedule_report_markdown(scenario, search, diagnosis))
        return 0
    if args.command == "audit":
        scenario = _load_scenario(args.scenario)
        calibrate_skills(scenario, 60)
        calibration = generate_cases(scenario, 80, "calibration")
        diagnosis = diagnose(scenario, calibration, DEMO_ROUNDS)
        print(audit_report_markdown(scenario, diagnosis))
        return 0
    if args.command == "evaluate":
        evaluation = run_evaluation()
        write_results(evaluation, args.outdir)
        agg = evaluation["aggregates"]
        print(
            "Wrote results to %s (scheduled %.3f vs free debate %.3f; "
            "closure per 1k tokens %.4f vs %.4f)"
            % (
                args.outdir,
                agg["mean_scheduled"],
                agg["mean_free_debate"],
                agg["mean_closure_per_1k_scheduled"],
                agg["mean_closure_per_1k_free"],
            )
        )
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
