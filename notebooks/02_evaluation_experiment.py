"""Evaluation experiment (smoke configuration for CI).

Runs the headline evaluation on a reduced scenario set (team sizes 3
and 7, low and high diversity, fewer cases) and prints the aggregates.
The full evaluation that produced results/ is:

    python -m dissent_sched evaluate

Run: python notebooks/02_evaluation_experiment.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dissent_sched.evaluate import SMOKE_CONFIG, run_evaluation


def main():
    evaluation = run_evaluation(SMOKE_CONFIG)
    agg = evaluation["aggregates"]
    print("Scenarios: %d" % agg["n_scenarios"])
    print("Mean no-debate accuracy: %.3f" % agg["mean_no_debate"])
    print("Mean free-debate accuracy: %.3f" % agg["mean_free_debate"])
    print("Mean always-dissent accuracy: %.3f" % agg["mean_always_dissent"])
    print("Mean random-dissent accuracy: %.3f" % agg["mean_random_dissent"])
    print("Mean scheduled accuracy: %.3f" % agg["mean_scheduled"])
    print(
        "Mean extended free-debate accuracy: %.3f"
        % agg["mean_free_debate_extended"]
    )
    print("Mean oracle accuracy: %.3f" % agg["mean_oracle"])
    print(
        "Scheduled minus free debate: %+.3f"
        % agg["scheduled_minus_free_accuracy"]
    )
    print(
        "Closure per 1k tokens (scheduled): %.4f"
        % agg["mean_closure_per_1k_scheduled"]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
