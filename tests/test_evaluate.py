import copy

from dissent_sched.evaluate import (
    DEFAULT_CONFIG,
    SMOKE_CONFIG,
    check_drift,
    run_evaluation,
)


def test_default_config_shape():
    assert DEFAULT_CONFIG["sizes"] == [3, 5, 7, 10]
    assert DEFAULT_CONFIG["diversities"] == ["low", "medium", "high"]
    assert DEFAULT_CONFIG["rounds"] == 4


def test_smoke_evaluation_structure():
    evaluation = run_evaluation(SMOKE_CONFIG)
    assert evaluation["aggregates"]["n_scenarios"] == 4
    assert len(evaluation["scenarios"]) == 4
    for row in evaluation["scenarios"]:
        for key in (
            "no_debate", "free_debate", "always_dissent",
            "random_dissent", "scheduled", "free_debate_extended",
            "oracle",
        ):
            assert 0.0 <= row[key] <= 1.0
        assert row["oracle"] >= row["no_debate"] - 1e-9
        assert row["tokens_scheduled"] >= row["tokens_free"] - 1e-9
        assert row["schedule"].count(":") == 2
        assert row["diagnosed_mode"] in ("anchor", "shield", "revival")


def test_smoke_aggregates_consistent():
    evaluation = run_evaluation(SMOKE_CONFIG)
    agg = evaluation["aggregates"]
    rows = evaluation["scenarios"]
    mean_scheduled = sum(r["scheduled"] for r in rows) / len(rows)
    assert abs(agg["mean_scheduled"] - mean_scheduled) < 1e-12
    beats = sum(
        1 for r in rows if r["scheduled"] > r["free_debate"] + 1e-9
    )
    assert agg["n_scenarios_scheduled_beats_free"] == beats
    shares = (
        agg["pathway_share_sycophantic_conformity"]
        + agg["pathway_share_fragility"]
        + agg["pathway_share_consensus_collapse"]
    )
    assert abs(shares - 1.0) < 0.05 or shares == 0.0


def test_evaluation_deterministic():
    first = run_evaluation(SMOKE_CONFIG)
    second = run_evaluation(SMOKE_CONFIG)
    assert first["aggregates"]["mean_scheduled"] == \
        second["aggregates"]["mean_scheduled"]
    assert first["scenarios"][0]["schedule"] == \
        second["scenarios"][0]["schedule"]


def test_check_drift_identical_passes():
    evaluation = run_evaluation(SMOKE_CONFIG)
    ok, problems = check_drift(evaluation, copy.deepcopy(evaluation))
    assert ok
    assert problems == []


def test_check_drift_detects_tampering():
    evaluation = run_evaluation(SMOKE_CONFIG)
    tampered = copy.deepcopy(evaluation)
    tampered["aggregates"]["mean_scheduled"] += 0.25
    ok, problems = check_drift(evaluation, tampered)
    assert not ok
    assert any(key == "mean_scheduled" for key, _, _, _ in problems)
