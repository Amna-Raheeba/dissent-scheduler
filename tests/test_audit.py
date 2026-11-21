from dissent_sched.audit import (
    PATHWAY_TO_MODE,
    classify_failure,
    collapse_driver,
    diagnose,
)
from dissent_sched.generate import build_scenario, generate_cases
from dissent_sched.models import CaseFixture
from dissent_sched.simulate import DebateResult


def _result(private, correct_answer, final, flips, extinct_round,
            snapshots=None):
    fixture = CaseFixture(0, correct=correct_answer, distractor=1,
                          private_answers=private)
    return DebateResult(
        fixture=fixture,
        final_answer=final,
        tokens=0,
        dissent_events=0,
        snapshots=snapshots or [private],
        flips=flips,
        extinct_round=extinct_round,
    )


def test_classify_absent():
    result = _result([0, 1, 1], 2, 1, [], 0)
    assert classify_failure(result, 4) == "absent"


def test_classify_correct_returns_none():
    result = _result([2, 1, 1], 2, 2, [], None)
    assert classify_failure(result, 4) is None


def test_classify_collapse_when_extinct_before_final_round():
    flips = [{"round": 1, "agent": 0, "from": 2, "to": 1,
              "channel": "conformity"}]
    result = _result([2, 1, 1], 2, 1, flips, 1)
    assert classify_failure(result, 4) == "consensus_collapse"


def test_classify_extinct_only_at_final_round_is_not_collapse():
    flips = [{"round": 4, "agent": 0, "from": 2, "to": 1,
              "channel": "conformity"}]
    result = _result([2, 1, 1], 2, 1, flips, 4)
    assert classify_failure(result, 4) == "sycophantic_conformity"


def test_classify_conformity_dominant():
    flips = [
        {"round": 1, "agent": 0, "from": 2, "to": 1,
         "channel": "conformity"},
        {"round": 2, "agent": 2, "from": 2, "to": 1,
         "channel": "fragility"},
    ]
    result = _result([2, 1, 2], 2, 1, flips, None)
    assert classify_failure(result, 4) == "sycophantic_conformity"


def test_classify_fragility_dominant():
    flips = [
        {"round": 1, "agent": 0, "from": 2, "to": 1,
         "channel": "fragility"},
        {"round": 2, "agent": 2, "from": 2, "to": 1,
         "channel": "fragility"},
        {"round": 3, "agent": 1, "from": 2, "to": 1,
         "channel": "conformity"},
    ]
    result = _result([2, 2, 2], 2, 1, flips, None)
    assert classify_failure(result, 4) == "fragility"


def test_collapse_driver():
    flips = [
        {"round": 1, "agent": 0, "from": 2, "to": 1,
         "channel": "conformity"},
        {"round": 1, "agent": 2, "from": 2, "to": 1,
         "channel": "conformity"},
        {"round": 2, "agent": 1, "from": 2, "to": 1,
         "channel": "fragility"},
    ]
    result = _result([2, 2, 2], 2, 1, flips, 2)
    assert collapse_driver(result) == "conformity"
    assert collapse_driver(_result([2, 1, 1], 2, 1, [], 1)) is None


def test_pathway_to_mode_mapping():
    assert PATHWAY_TO_MODE["sycophantic_conformity"] == "anchor"
    assert PATHWAY_TO_MODE["fragility"] == "shield"
    assert PATHWAY_TO_MODE["consensus_collapse"] == "revival"


def test_diagnose_counts_add_up():
    scenario = build_scenario(5, "medium", 5)
    fixtures = generate_cases(scenario, 40, "calibration")
    diagnosis = diagnose(scenario, fixtures, 4)
    assert diagnosis["n_cases"] == 40
    assert diagnosis["n_failed"] + diagnosis["n_correct_final"] == 40
    attributable = sum(diagnosis["pathway_counts"].values())
    assert attributable + diagnosis["n_absent"] == diagnosis["n_failed"]
    if attributable:
        total_share = sum(diagnosis["pathway_shares"].values())
        assert abs(total_share - 1.0) < 1e-9
        assert diagnosis["dominant_pathway"] in \
            diagnosis["pathway_counts"]
        assert diagnosis["recommended_mode"] == \
            PATHWAY_TO_MODE[diagnosis["dominant_pathway"]]
