import json
import os

from dissent_sched.evaluate import check_drift, run_evaluation

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def test_stored_results_exist():
    for name in ("evaluation.json", "evaluation.csv",
                 "evaluation_summary.md", "HEADLINE.md"):
        assert os.path.exists(os.path.join(RESULTS, name))


def test_stored_results_reproduce_without_drift():
    with open(os.path.join(RESULTS, "evaluation.json")) as handle:
        stored = json.load(handle)
    fresh = run_evaluation()
    ok, problems = check_drift(stored, fresh)
    assert ok, problems
