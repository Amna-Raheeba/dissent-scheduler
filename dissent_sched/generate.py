"""Seeded generation of teams, cases and calibration probes.

Team generation: for a team size and a diversity profile, each agent's
skill is drawn uniformly from the profile's skill range, conformity
from U(0.25, 0.60) and fragility from U(0.10, 0.50). Diversity is
operationalised through the distractor pull and the skill spread: a
low-diversity team is homogeneous *and* collapses onto the same wrong
answer, which is exactly the population in which a wrong majority can
form and dissent has something to rescue.

Case generation: the correct option is uniform over the four options;
the distractor is uniform over the three wrong ones. An agent's private
answer is correct with probability ``skill``; otherwise it is the
distractor with probability ``distractor_pull``, else uniform over the
remaining wrong options.

Calibration: the scheduler never sees true skills. It estimates each
agent's skill from a probe set -- private answers on labelled cases
with no debate -- exactly the pre-flight measurement a real deployment
could run.
"""

import random

from .models import (
    DIVERSITY_PROFILES,
    N_OPTIONS,
    Agent,
    CaseFixture,
    Scenario,
    derive_seed,
)


def build_team(n_agents, diversity, seed):
    """Build the agent list for one scenario, deterministically."""
    profile = DIVERSITY_PROFILES[diversity]
    rng = random.Random(derive_seed("team", seed))
    agents = []
    for _ in range(n_agents):
        agents.append(
            Agent(
                skill=rng.uniform(profile["skill_lo"], profile["skill_hi"]),
                conformity=rng.uniform(0.25, 0.60),
                fragility=rng.uniform(0.10, 0.50),
            )
        )
    return agents


def build_scenario(n_agents, diversity, seed):
    profile = DIVERSITY_PROFILES[diversity]
    return Scenario(
        name="%s-%d" % (diversity, n_agents),
        agents=build_team(n_agents, diversity, seed),
        distractor_pull=profile["distractor_pull"],
        seed=seed,
    )


def generate_case(scenario, case_id, stream):
    """Generate one case fixture. ``stream`` separates case populations
    (probe / calibration / evaluation) so they never share cases."""
    rng = random.Random(
        derive_seed("case", scenario.seed, stream, case_id)
    )
    correct = rng.randrange(N_OPTIONS)
    wrong = [option for option in range(N_OPTIONS) if option != correct]
    distractor = wrong[rng.randrange(len(wrong))]
    private_answers = []
    for agent in scenario.agents:
        if rng.random() < agent.skill:
            private_answers.append(correct)
            continue
        if rng.random() < scenario.distractor_pull:
            private_answers.append(distractor)
            continue
        rest = [option for option in wrong if option != distractor]
        private_answers.append(rest[rng.randrange(len(rest))])
    return CaseFixture(
        case_id=case_id,
        correct=correct,
        distractor=distractor,
        private_answers=private_answers,
    )


def generate_cases(scenario, n_cases, stream):
    return [
        generate_case(scenario, case_id, stream) for case_id in range(n_cases)
    ]


def calibrate_skills(scenario, n_probe=60):
    """Estimate each agent's skill from a labelled probe set.

    Mutates the scenario's agents (sets ``estimated_skill``) and returns
    the list of estimates. The probe cases are private answers only --
    no debate -- so the estimate measures the agent, not the dynamics.
    """
    fixtures = generate_cases(scenario, n_probe, "probe")
    estimates = []
    for index, agent in enumerate(scenario.agents):
        hits = sum(
            1
            for fixture in fixtures
            if fixture.private_answers[index] == fixture.correct
        )
        estimate = hits / float(n_probe)
        agent.estimated_skill = estimate
        estimates.append(estimate)
    return estimates


def top_skill_agent(scenario):
    """Index of the agent with the highest *estimated* skill."""
    best_index = 0
    best_value = -1.0
    for index, agent in enumerate(scenario.agents):
        value = agent.estimated_skill
        if value is None:
            value = agent.skill
        if value > best_value:
            best_value = value
            best_index = index
    return best_index
