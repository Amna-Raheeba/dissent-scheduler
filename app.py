"""Streamlit dashboard for dissent-scheduler.

Three tabs:
1. Schedule -- build a team (size x diversity), calibrate it, search
   dissent schedules on calibration cases, and compare the chosen
   schedule against no-debate and free debate on held-out cases.
2. Pathways -- run the failure-pathway audit on a team: which of
   sycophantic conformity, fragility, or consensus collapse is losing
   its correct answers, and which dissent mode targets it.
3. Evaluation -- the stored headline results (results/evaluation.json).

Run: streamlit run app.py
"""

import json
import os

import streamlit as st

from dissent_sched.audit import PATHWAYS, diagnose
from dissent_sched.generate import (
    build_scenario,
    calibrate_skills,
    generate_cases,
)
from dissent_sched.schedule import Schedule, search_schedules
from dissent_sched.simulate import gap_closure, oracle_accuracy, run_policy

st.set_page_config(page_title="Dissent Scheduler", layout="wide")

ROUNDS = 4
DIVERSITIES = ["low", "medium", "high"]


def _team_controls(prefix):
    col1, col2 = st.columns(2)
    n_agents = col1.slider(
        "Team size", 3, 10, 5, 1, key=prefix + "_size"
    )
    diversity = col2.selectbox(
        "Diversity profile", DIVERSITIES, index=1, key=prefix + "_div"
    )
    return int(n_agents), diversity


def tab_schedule():
    st.header("Search a dissent schedule")
    st.write(
        "Dissent is an intervention with a price. The search prices "
        "every schedule on calibration cases and ranks by oracle-gap "
        "closure per 1k tokens -- how much of the gap between the "
        "no-debate vote and the best reachable answer the schedule "
        "closes, per thousand tokens spent."
    )
    n_agents, diversity = _team_controls("sched")
    scenario = build_scenario(n_agents, diversity, 7)
    calibrate_skills(scenario, 60)
    search = search_schedules(
        [scenario], rounds=ROUNDS, n_calibration=40, n_probe=60
    )
    best = search["best"]
    st.write(
        "**Chosen schedule: %s** -- calibration accuracy %.3f, gap "
        "closure %.3f, %.4f closure per 1k tokens."
        % (
            best["key"],
            best["accuracy"],
            best["gap_closure"],
            best["closure_per_1k_tokens"],
        )
    )
    rows = []
    for row in search["table"][:10]:
        rows.append(
            {
                "schedule": row["key"],
                "accuracy": round(row["accuracy"], 3),
                "gap closure": round(row["gap_closure"], 3),
                "closure / 1k tokens": round(
                    row["closure_per_1k_tokens"], 4
                ),
                "tokens / case": round(row["mean_tokens"]),
            }
        )
    st.dataframe(rows, use_container_width=True)
    scheduled = Schedule.from_dict(best["schedule"])
    fixtures = generate_cases(scenario, 60, "evaluation")
    oracle = oracle_accuracy(fixtures)
    comparison = []
    baseline = None
    for name, schedule in (
        ("no debate", None),
        ("free debate", None),
        ("scheduled", scheduled),
    ):
        metrics = run_policy(
            scenario, fixtures, ROUNDS,
            schedule=schedule, policy_key=name,
        )
        if name == "no debate":
            baseline = metrics["accuracy"]
        closure = gap_closure(metrics["accuracy"], baseline, oracle)
        comparison.append(
            {
                "policy": name,
                "accuracy": round(metrics["accuracy"], 3),
                "tokens / case": round(metrics["mean_tokens"]),
                "gap closure": round(closure, 3),
            }
        )
    st.dataframe(comparison, use_container_width=True)
    st.caption(
        "Held-out cases: 60. Oracle (correct answer present in the "
        "private pool): %.3f. All teams are synthetic and seeded."
        % oracle
    )


def tab_pathways():
    st.header("Which failure pathway is losing the correct answers?")
    st.write(
        "Free debate loses cases three ways: conformists pile onto a "
        "wrong plurality (sycophantic conformity), correct agents are "
        "destabilised by loud disagreement (fragility), or the correct "
        "answer's last holder flips before the final round (consensus "
        "collapse). Each pathway has a dissent mode that targets it."
    )
    n_agents, diversity = _team_controls("path")
    scenario = build_scenario(n_agents, diversity, 7)
    calibrate_skills(scenario, 60)
    fixtures = generate_cases(scenario, 80, "calibration")
    diagnosis = diagnose(scenario, fixtures, ROUNDS)
    shares = diagnosis["pathway_shares"]
    st.bar_chart(
        {"share of attributable failures": [shares[name] for name in PATHWAYS]}
    )
    st.caption(
        "Pathways in order: sycophantic conformity, fragility, "
        "consensus collapse. Absent cases (no privately correct "
        "agent): %d of %d."
        % (diagnosis["n_absent"], diagnosis["n_cases"])
    )
    if diagnosis["dominant_pathway"] is not None:
        st.write(
            "**Dominant pathway: %s -> recommended dissent mode: %s.**"
            % (
                diagnosis["dominant_pathway"],
                diagnosis["recommended_mode"],
            )
        )
    else:
        st.write("**No attributable failures on these cases.**")


def tab_evaluation():
    st.header("Headline evaluation (stored results)")
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results",
        "evaluation.json",
    )
    if not os.path.exists(path):
        st.info("No stored results yet. Run: python -m dissent_sched evaluate")
        return
    with open(path) as handle:
        evaluation = json.load(handle)
    agg = evaluation["aggregates"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Free debate accuracy", "%.3f" % agg["mean_free_debate"])
    m2.metric("Scheduled accuracy", "%.3f" % agg["mean_scheduled"])
    m3.metric(
        "Closure / 1k tokens (scheduled)",
        "%.4f" % agg["mean_closure_per_1k_scheduled"],
    )
    rows = []
    for scenario in evaluation["scenarios"]:
        rows.append(
            {
                "scenario": scenario["scenario"],
                "no debate": round(scenario["no_debate"], 3),
                "free": round(scenario["free_debate"], 3),
                "always": round(scenario["always_dissent"], 3),
                "random": round(scenario["random_dissent"], 3),
                "scheduled": round(scenario["scheduled"], 3),
                "extended": round(scenario["free_debate_extended"], 3),
                "oracle": round(scenario["oracle"], 3),
                "schedule": scenario["schedule"],
            }
        )
    st.dataframe(rows, use_container_width=True)
    show = agg["showcase"]
    st.write(
        "Showcase (%s): schedule %s lifts accuracy from %.3f (free "
        "debate) to %.3f, closing %.1f%% of the gap to the oracle "
        "(%.3f)."
        % (
            show["scenario"],
            show["schedule"],
            show["free_debate"],
            show["scheduled"],
            show["closure_scheduled"] * 100.0,
            show["oracle"],
        )
    )
    st.caption(
        "All teams and cases are synthetic and seeded, with agent "
        "parameters known by construction; see "
        "results/evaluation_summary.md."
    )


tab1, tab2, tab3 = st.tabs(["Schedule", "Pathways", "Evaluation"])
with tab1:
    tab_schedule()
with tab2:
    tab_pathways()
with tab3:
    tab_evaluation()
