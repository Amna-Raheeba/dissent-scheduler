"""Dissent schedules and the calibration search over them.

A schedule is (mode, trigger, dissenter):

- mode: ``anchor`` / ``shield`` / ``revival`` (see ``simulate.py``);
- trigger: ``every_round``, ``first_round``, ``last_round``,
  ``contested`` (fires only while the plurality share is below 0.6 --
  dissent is spent where the early votes actually disagree, not
  uniformly), or ``extinct`` (fires when some round-0 answer has lost
  its last holder);
- dissenter: ``top_skill`` (highest *estimated* skill from the
  calibration probe) or ``random`` (seeded per case). Two modes do not
  vary the dissenter: revival chooses its own -- the extinct answer's
  most credible original holder -- and shield is a room-level
  intervention (it damps fragility for everyone), so no individual
  dissenter acts. The search varies only the trigger for those modes.

The search prices every schedule in the space on calibration cases
(held out from the evaluation cases) and ranks by **oracle-gap closure
per 1k tokens**: how much of the gap between the no-debate vote and
the oracle (correct answer present in the private pool) the schedule
closes, per thousand tokens spent. Accuracy alone would reward
spending; tokens alone would reward silence.
"""

from .generate import calibrate_skills, generate_cases
from .simulate import gap_closure, oracle_accuracy, run_policy

MODES = ("anchor", "shield", "revival")
TRIGGERS = (
    "every_round",
    "first_round",
    "last_round",
    "contested",
    "extinct",
)
DISSENTERS = ("top_skill", "random")


class Schedule(object):
    def __init__(self, mode, trigger, dissenter="top_skill"):
        self.mode = mode
        self.trigger = trigger
        self.dissenter = dissenter

    def key(self):
        return "%s:%s:%s" % (self.mode, self.trigger, self.dissenter)

    def to_dict(self):
        return {
            "mode": self.mode,
            "trigger": self.trigger,
            "dissenter": self.dissenter,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            mode=data["mode"],
            trigger=data["trigger"],
            dissenter=data.get("dissenter", "top_skill"),
        )


def schedule_space():
    """The full search space (20 schedules)."""
    schedules = []
    for mode in MODES:
        for trigger in TRIGGERS:
            if mode in ("revival", "shield"):
                schedules.append(Schedule(mode, trigger, "top_skill"))
            else:
                for dissenter in DISSENTERS:
                    schedules.append(Schedule(mode, trigger, dissenter))
    return schedules


def evaluate_schedule(scenario, fixtures, schedule, rounds,
                      baseline_accuracy, oracle):
    metrics = run_policy(
        scenario, fixtures, rounds,
        schedule=schedule, policy_key=schedule.key(),
    )
    closure = gap_closure(metrics["accuracy"], baseline_accuracy, oracle)
    per_1k = (
        closure / metrics["mean_tokens"] * 1000.0
        if metrics["mean_tokens"] else 0.0
    )
    return {
        "schedule": schedule.to_dict(),
        "key": schedule.key(),
        "accuracy": metrics["accuracy"],
        "mean_tokens": metrics["mean_tokens"],
        "mean_dissent_events": metrics["mean_dissent_events"],
        "gap_closure": closure,
        "closure_per_1k_tokens": per_1k,
    }


def search_schedules(scenarios, rounds=4, n_calibration=80, n_probe=60):
    """Search the schedule space on calibration cases per scenario.

    Skills are calibrated first (probe set), so dissenter choice and
    anchor credibility run on estimates, never on true parameters.
    Returns the best schedule by closure per 1k tokens, the best by
    raw accuracy, and the full table averaged over scenarios.
    """
    totals = {}
    for scenario in scenarios:
        if any(agent.estimated_skill is None for agent in scenario.agents):
            calibrate_skills(scenario, n_probe)
        fixtures = generate_cases(scenario, n_calibration, "calibration")
        baseline = run_policy(
            scenario, fixtures, rounds, policy_key="no_debate"
        )["accuracy"]
        oracle = oracle_accuracy(fixtures)
        for schedule in schedule_space():
            row = evaluate_schedule(
                scenario, fixtures, schedule, rounds, baseline, oracle
            )
            bucket = totals.setdefault(
                schedule.key(),
                {
                    "schedule": schedule.to_dict(),
                    "key": schedule.key(),
                    "accuracy": 0.0,
                    "mean_tokens": 0.0,
                    "mean_dissent_events": 0.0,
                    "gap_closure": 0.0,
                    "closure_per_1k_tokens": 0.0,
                    "n_scenarios": 0,
                },
            )
            for field in (
                "accuracy",
                "mean_tokens",
                "mean_dissent_events",
                "gap_closure",
                "closure_per_1k_tokens",
            ):
                bucket[field] += row[field]
            bucket["n_scenarios"] += 1
    table = []
    for bucket in totals.values():
        n = float(bucket["n_scenarios"])
        row = dict(bucket)
        for field in (
            "accuracy",
            "mean_tokens",
            "mean_dissent_events",
            "gap_closure",
            "closure_per_1k_tokens",
        ):
            row[field] = bucket[field] / n
        table.append(row)
    table.sort(
        key=lambda row: (
            -row["closure_per_1k_tokens"],
            -row["accuracy"],
            row["key"],
        )
    )
    by_accuracy = sorted(
        table,
        key=lambda row: (-row["accuracy"], -row["closure_per_1k_tokens"],
                         row["key"]),
    )
    return {
        "best": table[0] if table else None,
        "best_by_accuracy": by_accuracy[0] if by_accuracy else None,
        "table": table,
        "rounds": rounds,
        "n_calibration": n_calibration,
    }
