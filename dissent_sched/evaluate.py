"""Headline evaluation: scheduled dissent vs the standard debate policies.

Scenarios cross team sizes {3, 5, 7, 10} with diversity profiles
{low, medium, high}. For every scenario the tool first calibrates:
agent skills are estimated from a probe set, failure pathways are
diagnosed from free debate on calibration cases, and the schedule
search runs on those same calibration cases. Only then are the
policies compared on held-out evaluation cases:

- ``no_debate`` -- round-0 plurality vote;
- ``free_debate`` -- debate rounds, no intervention;
- ``always_dissent`` -- the diagnosed dissent mode, fired every round;
- ``random_dissent`` -- the scheduled mode, fired on seeded random
  rounds (same spend class, no timing);
- ``scheduled`` -- the schedule chosen by the calibration search;
- ``free_debate_extended`` -- free debate given extra rounds until its
  token spend matches the scheduled policy's: the "just buy more
  debate" counterfactual at equal budget;
- ``oracle`` -- the correct answer whenever it is present in the
  private pool (an upper bound, not a policy).

Everything is deterministic: same seeds, same numbers.
"""

import csv
import json
import os

from .audit import diagnose
from .generate import build_scenario, calibrate_skills, generate_cases
from .models import STATEMENT_TOKENS
from .schedule import Schedule, search_schedules
from .simulate import gap_closure, oracle_accuracy, run_policy

DEFAULT_CONFIG = {
    "sizes": [3, 5, 7, 10],
    "diversities": ["low", "medium", "high"],
    "base_seed": 20261121,
    "rounds": 4,
    "n_cases": 160,
    "n_calibration": 80,
    "n_probe": 60,
}

SMOKE_CONFIG = {
    "sizes": [3, 7],
    "diversities": ["low", "high"],
    "base_seed": 20261121,
    "rounds": 3,
    "n_cases": 40,
    "n_calibration": 30,
    "n_probe": 30,
}

_CSV_FIELDS = [
    "scenario",
    "n_agents",
    "diversity",
    "no_debate",
    "free_debate",
    "always_dissent",
    "random_dissent",
    "scheduled",
    "free_debate_extended",
    "oracle",
    "tokens_free",
    "tokens_scheduled",
    "closure_scheduled",
    "closure_per_1k_scheduled",
    "schedule",
    "diagnosed_mode",
]


def _policy_row(scenario, fixtures, rounds, schedule, policy_key):
    return run_policy(
        scenario, fixtures, rounds,
        schedule=schedule, policy_key=policy_key,
    )


def evaluate_scenario(scenario, cfg):
    rounds = cfg["rounds"]
    calibrate_skills(scenario, cfg["n_probe"])
    calibration = generate_cases(scenario, cfg["n_calibration"],
                                 "calibration")
    diagnosis = diagnose(scenario, calibration, rounds)
    search = search_schedules(
        [scenario], rounds=rounds,
        n_calibration=cfg["n_calibration"], n_probe=cfg["n_probe"],
    )
    scheduled = Schedule.from_dict(search["best"]["schedule"])
    diagnosed_mode = diagnosis["recommended_mode"] or "anchor"
    always = Schedule(diagnosed_mode, "every_round", "top_skill")
    random_schedule = Schedule(
        scheduled.mode, "random", scheduled.dissenter
    )
    fixtures = generate_cases(scenario, cfg["n_cases"], "evaluation")
    oracle = oracle_accuracy(fixtures)

    no_debate = _policy_row(scenario, fixtures, rounds, None, "no_debate")
    free = _policy_row(scenario, fixtures, rounds, None, "free")
    always_m = _policy_row(
        scenario, fixtures, rounds, always, always.key()
    )
    random_m = _policy_row(
        scenario, fixtures, rounds, random_schedule, random_schedule.key()
    )
    scheduled_m = _policy_row(
        scenario, fixtures, rounds, scheduled, scheduled.key()
    )
    round_cost = float(scenario.n_agents * STATEMENT_TOKENS)
    extra = int(round(
        (scheduled_m["mean_tokens"] - free["mean_tokens"]) / round_cost
    ))
    extra = max(0, extra)
    extended = run_policy(
        scenario, fixtures, rounds + extra, policy_key="free"
    )

    def closure(metrics):
        return gap_closure(metrics["accuracy"], no_debate["accuracy"],
                           oracle)

    def per_1k(metrics):
        if not metrics["mean_tokens"]:
            return 0.0
        return metrics["accuracy"] / metrics["mean_tokens"] * 1000.0

    def closure_per_1k(metrics):
        if not metrics["mean_tokens"]:
            return 0.0
        return closure(metrics) / metrics["mean_tokens"] * 1000.0

    return {
        "scenario": scenario.name,
        "n_agents": scenario.n_agents,
        "diversity": scenario.name.rsplit("-", 1)[0],
        "no_debate": no_debate["accuracy"],
        "free_debate": free["accuracy"],
        "always_dissent": always_m["accuracy"],
        "random_dissent": random_m["accuracy"],
        "scheduled": scheduled_m["accuracy"],
        "free_debate_extended": extended["accuracy"],
        "oracle": oracle,
        "tokens_no_debate": no_debate["mean_tokens"],
        "tokens_free": free["mean_tokens"],
        "tokens_always": always_m["mean_tokens"],
        "tokens_random": random_m["mean_tokens"],
        "tokens_scheduled": scheduled_m["mean_tokens"],
        "tokens_extended": extended["mean_tokens"],
        "closure_free": closure(free),
        "closure_always": closure(always_m),
        "closure_random": closure(random_m),
        "closure_scheduled": closure(scheduled_m),
        "closure_extended": closure(extended),
        "acc_per_1k_free": per_1k(free),
        "acc_per_1k_scheduled": per_1k(scheduled_m),
        "closure_per_1k_free": closure_per_1k(free),
        "closure_per_1k_scheduled": closure_per_1k(scheduled_m),
        "dissent_events_scheduled": scheduled_m["mean_dissent_events"],
        "schedule": scheduled.key(),
        "diagnosed_mode": diagnosed_mode,
        "dominant_pathway": diagnosis["dominant_pathway"],
        "pathway_shares": diagnosis["pathway_shares"],
        "extended_extra_rounds": extra,
    }


def run_evaluation(config=None):
    cfg = dict(DEFAULT_CONFIG)
    if config is not None:
        cfg.update(config)
    rows = []
    index = 0
    for n_agents in cfg["sizes"]:
        for diversity in cfg["diversities"]:
            seed = cfg["base_seed"] + 1000 * index
            scenario = build_scenario(n_agents, diversity, seed)
            rows.append(evaluate_scenario(scenario, cfg))
            index += 1
    return {
        "config": cfg,
        "scenarios": rows,
        "aggregates": _aggregates(rows),
    }


def _mean(rows, key):
    return sum(row[key] for row in rows) / float(len(rows))


def _aggregates(rows):
    agg = {"n_scenarios": len(rows)}
    for key in (
        "no_debate", "free_debate", "always_dissent", "random_dissent",
        "scheduled", "free_debate_extended", "oracle",
        "tokens_free", "tokens_scheduled", "tokens_always",
        "closure_free", "closure_always", "closure_random",
        "closure_scheduled", "closure_extended",
        "acc_per_1k_free", "acc_per_1k_scheduled",
        "closure_per_1k_free", "closure_per_1k_scheduled",
    ):
        agg["mean_" + key] = _mean(rows, key)
    agg["scheduled_minus_free_accuracy"] = _mean(
        rows, "scheduled"
    ) - _mean(rows, "free_debate")
    agg["scheduled_minus_extended_accuracy"] = _mean(
        rows, "scheduled"
    ) - _mean(rows, "free_debate_extended")
    agg["n_scenarios_scheduled_beats_free"] = sum(
        1 for row in rows if row["scheduled"] > row["free_debate"] + 1e-9
    )
    agg["n_scenarios_scheduled_hurts"] = sum(
        1 for row in rows if row["scheduled"] < row["free_debate"] - 1e-9
    )
    agg["n_scenarios_scheduled_ge_no_debate"] = sum(
        1 for row in rows if row["scheduled"] >= row["no_debate"] - 1e-9
    )
    for pathway in (
        "sycophantic_conformity", "fragility", "consensus_collapse"
    ):
        agg["pathway_share_" + pathway] = sum(
            row["pathway_shares"][pathway] for row in rows
        ) / float(len(rows))
    showcase = max(
        rows, key=lambda row: row["scheduled"] - row["free_debate"]
    )
    agg["showcase"] = {
        "scenario": showcase["scenario"],
        "schedule": showcase["schedule"],
        "no_debate": showcase["no_debate"],
        "free_debate": showcase["free_debate"],
        "scheduled": showcase["scheduled"],
        "oracle": showcase["oracle"],
        "closure_scheduled": showcase["closure_scheduled"],
    }
    return agg


def write_results(evaluation, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "evaluation.json"), "w") as handle:
        json.dump(evaluation, handle, indent=2)
    with open(os.path.join(outdir, "evaluation.csv"), "w",
              newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in evaluation["scenarios"]:
            writer.writerow(dict((key, row[key]) for key in _CSV_FIELDS))
    with open(os.path.join(outdir, "evaluation_summary.md"),
              "w") as handle:
        handle.write(summary_markdown(evaluation))
    with open(os.path.join(outdir, "HEADLINE.md"), "w") as handle:
        handle.write(headline_markdown(evaluation))


def summary_markdown(evaluation):
    agg = evaluation["aggregates"]
    cfg = evaluation["config"]
    lines = []
    lines.append("# Evaluation summary")
    lines.append("")
    lines.append(
        "Seeded evaluation: %d scenarios (team sizes %s, diversity "
        "profiles %s), %d held-out cases per scenario, %d debate rounds. "
        "Skills are estimated from a %d-case probe and schedules are "
        "searched on %d calibration cases per scenario; no policy sees "
        "true parameters or the truth."
        % (
            agg["n_scenarios"],
            cfg["sizes"],
            cfg["diversities"],
            cfg["n_cases"],
            cfg["rounds"],
            cfg["n_probe"],
            cfg["n_calibration"],
        )
    )
    lines.append("")
    lines.append("## Aggregates")
    lines.append("")
    lines.append(
        "- Mean accuracy: no-debate %.3f, free debate %.3f, "
        "always-dissent %.3f, random dissent %.3f, scheduled %.3f, "
        "free debate extended to equal tokens %.3f, oracle %.3f."
        % (
            agg["mean_no_debate"],
            agg["mean_free_debate"],
            agg["mean_always_dissent"],
            agg["mean_random_dissent"],
            agg["mean_scheduled"],
            agg["mean_free_debate_extended"],
            agg["mean_oracle"],
        )
    )
    lines.append(
        "- Scheduled dissent vs free debate: %+.3f accuracy on average; "
        "it beats free debate in %d of %d scenarios and hurts in %d."
        % (
            agg["scheduled_minus_free_accuracy"],
            agg["n_scenarios_scheduled_beats_free"],
            agg["n_scenarios"],
            agg["n_scenarios_scheduled_hurts"],
        )
    )
    lines.append(
        "- Oracle-gap closure: free debate %.3f, always-dissent %.3f, "
        "random dissent %.3f, scheduled %.3f, extended free debate %.3f."
        % (
            agg["mean_closure_free"],
            agg["mean_closure_always"],
            agg["mean_closure_random"],
            agg["mean_closure_scheduled"],
            agg["mean_closure_extended"],
        )
    )
    lines.append(
        "- Closure per 1k tokens: free debate %.4f, scheduled %.4f "
        "(mean tokens per case: free %.0f, scheduled %.0f, "
        "always-dissent %.0f)."
        % (
            agg["mean_closure_per_1k_free"],
            agg["mean_closure_per_1k_scheduled"],
            agg["mean_tokens_free"],
            agg["mean_tokens_scheduled"],
            agg["mean_tokens_always"],
        )
    )
    lines.append(
        "- Failure pathways among attributable free-debate failures: "
        "sycophantic conformity %.1f%%, fragility %.1f%%, consensus "
        "collapse %.1f%% (mean of per-scenario shares)."
        % (
            agg["pathway_share_sycophantic_conformity"] * 100.0,
            agg["pathway_share_fragility"] * 100.0,
            agg["pathway_share_consensus_collapse"] * 100.0,
        )
    )
    lines.append("")
    lines.append("## Scenarios")
    lines.append("")
    lines.append(
        "| scenario | no debate | free | always | random | scheduled "
        "| extended | oracle | schedule |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for row in evaluation["scenarios"]:
        lines.append(
            "| %s | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | %.3f | "
            "%s |"
            % (
                row["scenario"],
                row["no_debate"],
                row["free_debate"],
                row["always_dissent"],
                row["random_dissent"],
                row["scheduled"],
                row["free_debate_extended"],
                row["oracle"],
                row["schedule"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def headline_markdown(evaluation):
    agg = evaluation["aggregates"]
    show = agg["showcase"]
    lines = []
    lines.append("# Headline results")
    lines.append("")
    lines.append(
        "Dissent on a schedule, priced in tokens, on %d seeded debate "
        "scenarios (team sizes 3-10, three diversity profiles), with "
        "real measured accuracies from the seeded simulator."
        % agg["n_scenarios"]
    )
    lines.append("")
    lines.append(
        "- Scheduled dissent reaches mean accuracy **%.3f** vs free "
        "debate **%.3f** and the no-debate vote **%.3f** (oracle "
        "%.3f): %+.3f over free debate, beating it in %d of %d "
        "scenarios and hurting in %d."
        % (
            agg["mean_scheduled"],
            agg["mean_free_debate"],
            agg["mean_no_debate"],
            agg["mean_oracle"],
            agg["scheduled_minus_free_accuracy"],
            agg["n_scenarios_scheduled_beats_free"],
            agg["n_scenarios"],
            agg["n_scenarios_scheduled_hurts"],
        )
    )
    damage = agg["mean_no_debate"] - agg["mean_free_debate"]
    recovered = (
        (agg["mean_scheduled"] - agg["mean_free_debate"]) / damage
        if damage > 1e-9 else 0.0
    )
    lines.append(
        "- Free debate *loses* %.3f accuracy to the no-debate vote in "
        "these populations; scheduled dissent recovers **%.0f%%** of "
        "that self-inflicted loss, and matches or beats the vote in "
        "%d of %d scenarios. Closure per 1k tokens: scheduled %.4f "
        "vs free debate %.4f."
        % (
            damage,
            recovered * 100.0,
            agg["n_scenarios_scheduled_ge_no_debate"],
            agg["n_scenarios"],
            agg["mean_closure_per_1k_scheduled"],
            agg["mean_closure_per_1k_free"],
        )
    )
    lines.append(
        "- Dissenting constantly is worse than not dissenting at all: "
        "always-dissent reaches %.3f, below free debate's %.3f, and "
        "random-timing dissent reaches %.3f -- the scheduled gain "
        "comes from mode and timing, not from dissent volume."
        % (
            agg["mean_always_dissent"],
            agg["mean_free_debate"],
            agg["mean_random_dissent"],
        )
    )
    lines.append(
        "- At equal tokens, extra free-debate rounds reach %.3f -- "
        "scheduled dissent %s that counterfactual by %+.3f."
        % (
            agg["mean_free_debate_extended"],
            "beats" if agg["scheduled_minus_extended_accuracy"] >= 0
            else "trails",
            agg["scheduled_minus_extended_accuracy"],
        )
    )
    lines.append(
        "- Failure pathways in free debate: sycophantic conformity "
        "%.1f%%, fragility %.1f%%, consensus collapse %.1f%% of "
        "attributable failures."
        % (
            agg["pathway_share_sycophantic_conformity"] * 100.0,
            agg["pathway_share_fragility"] * 100.0,
            agg["pathway_share_consensus_collapse"] * 100.0,
        )
    )
    lines.append(
        "- Showcase (%s): schedule %s lifts accuracy from %.3f (free "
        "debate) to %.3f -- the largest rescue in the grid. The "
        "no-debate vote reaches %.3f there and the oracle %.3f, so "
        "even the best rescue mostly repairs debate's own damage "
        "rather than beating silence."
        % (
            show["scenario"],
            show["schedule"],
            show["free_debate"],
            show["scheduled"],
            show["no_debate"],
            show["oracle"],
        )
    )
    lines.append("")
    lines.append(
        "Caveat: all teams and cases are synthetic and seeded, with "
        "agent parameters known by construction; the experiment "
        "validates the scheduler and the pathway audit under that "
        "model, not any live model team."
    )
    lines.append("")
    return "\n".join(lines)


def check_drift(stored, fresh, tol=1e-6):
    """Compare aggregate numbers of two evaluations.

    Returns (ok, problems). Only numeric aggregate keys are compared.
    """
    problems = []
    stored_agg = stored["aggregates"]
    fresh_agg = fresh["aggregates"]
    for key in stored_agg:
        if key == "showcase":
            continue
        stored_value = stored_agg[key]
        if not isinstance(stored_value, (int, float)):
            continue
        fresh_value = fresh_agg.get(key)
        if fresh_value is None:
            problems.append((key, stored_value, None, None))
            continue
        diff = abs(stored_value - fresh_value)
        scale = max(1.0, abs(stored_value))
        if diff / scale > tol:
            problems.append((key, stored_value, fresh_value, diff))
    return (not problems), problems
