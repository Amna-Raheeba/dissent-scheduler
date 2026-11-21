"""The debate simulator.

A debate starts from the private answers (round 0) and runs a fixed
number of rounds. In every round all agents update simultaneously from
the round-start state through two behavioural channels:

- **conformity**: an agent who disagrees with the plurality answer
  flips to it with probability ``conformity``;
- **fragility**: an agent holding the correct answer flips to the
  leading wrong answer with probability ``fragility`` times the share
  of its peers holding that wrong answer -- a correct agent
  destabilised by loud disagreement, even when the correct answer is
  itself the plurality.

Every flip is recorded with its channel, which is what makes the
failure-pathway audit (see ``audit.py``) possible.

A *dissent intervention* (see ``schedule.py``) can fire at the start of
a round, in one of three modes:

- **anchor**: the dissenter (the agent with the highest estimated
  skill, or a seeded random agent) holds its answer for the round, and
  conformity flips are redirected to the dissenter's answer with
  probability equal to the dissenter's estimated skill -- conformists
  follow the loudest credible voice instead of the crowd;
- **shield**: fragility flips are damped by ``SHIELD_STRENGTH`` for
  the round -- public dissent legitimises holding a minority view, so
  correct agents are harder to destabilise;
- **revival**: an answer that was present in round 0 but currently has
  no holder is re-seated with its highest-estimated-skill original
  holder, putting a voted-away answer back in the pool; the dissenter
  holds for the round, and each other original holder returns to the
  answer with probability 0.5 -- the dissenter re-presents the case,
  and the agents who privately held it are reminded of their own
  signal.

Tokens: round 0 costs one statement per agent; each debate round costs
one statement per agent, plus ``DISSENT_TOKENS`` for each round in
which a dissent intervention actually fires.
"""

import random

from .models import (
    DISSENT_TOKENS,
    SHIELD_STRENGTH,
    STATEMENT_TOKENS,
    derive_seed,
    plurality,
)
from .generate import top_skill_agent


class DebateResult(object):
    def __init__(self, fixture, final_answer, tokens, dissent_events,
                 snapshots, flips, extinct_round):
        self.fixture = fixture
        self.final_answer = final_answer
        self.tokens = tokens
        self.dissent_events = dissent_events
        self.snapshots = snapshots
        self.flips = flips
        self.extinct_round = extinct_round

    @property
    def correct(self):
        return self.final_answer == self.fixture.correct


def _leading_wrong(state, correct, private):
    wrong = [answer for answer in state if answer != correct]
    if not wrong:
        return None
    wrong_private = [answer for answer in private if answer != correct]
    return plurality(wrong, wrong_private)


def _trigger_fires(trigger, round_index, rounds, state, private, rng):
    if trigger == "every_round":
        return True
    if trigger == "first_round":
        return round_index == 1
    if trigger == "last_round":
        return round_index == rounds
    if trigger == "contested":
        leader = plurality(state, private)
        share = sum(1 for a in state if a == leader) / float(len(state))
        return share < 0.6
    if trigger == "extinct":
        return any(answer not in state for answer in set(private))
    if trigger == "random":
        return rng.random() < 0.5
    raise ValueError("unknown trigger: %s" % trigger)


def _pick_dissenter(scenario, fixture, schedule, rng):
    if schedule.dissenter == "top_skill":
        return top_skill_agent(scenario)
    if schedule.dissenter == "random":
        return rng.randrange(scenario.n_agents)
    raise ValueError("unknown dissenter: %s" % schedule.dissenter)


def _revival_target(scenario, fixture, state):
    """Extinct round-0 answer whose best original holder is strongest.

    Returns (answer, holder_index) or None. The scheduler cannot see
    the truth: it revives the extinct answer backed by the most
    credible original holder, right or wrong.
    """
    best = None
    best_key = None
    for answer in sorted(set(fixture.private_answers)):
        if answer in state:
            continue
        holders = [
            index
            for index, held in enumerate(fixture.private_answers)
            if held == answer
        ]
        for holder in holders:
            agent = scenario.agents[holder]
            credibility = agent.estimated_skill
            if credibility is None:
                credibility = agent.skill
            key = (credibility, -holder)
            if best_key is None or key > best_key:
                best_key = key
                best = (answer, holder)
    return best


def run_debate(scenario, fixture, rounds, schedule=None,
               policy_key="free"):
    """Simulate one debate. ``schedule=None`` is free debate."""
    private = list(fixture.private_answers)
    state = list(private)
    n_agents = scenario.n_agents
    tokens = n_agents * STATEMENT_TOKENS
    dissent_events = 0
    snapshots = [list(state)]
    flips = []
    extinct_round = None
    if fixture.correct not in state:
        extinct_round = 0
    rng = random.Random(
        derive_seed("debate", scenario.seed, fixture.case_id, policy_key)
    )
    for round_index in range(1, rounds + 1):
        dissenter = None
        anchor_answer = None
        shielded = False
        if schedule is not None and _trigger_fires(
            schedule.trigger, round_index, rounds, state, private, rng
        ):
            if schedule.mode == "revival":
                target = _revival_target(scenario, fixture, state)
                if target is not None:
                    answer, dissenter = target
                    state[dissenter] = answer
                    dissent_events += 1
                    tokens += DISSENT_TOKENS
                    for holder, held in enumerate(
                        fixture.private_answers
                    ):
                        if holder != dissenter and held == answer \
                                and rng.random() < 0.5:
                            flips.append({
                                "round": round_index,
                                "agent": holder,
                                "from": state[holder],
                                "to": answer,
                                "channel": "revival",
                            })
                            state[holder] = answer
            elif schedule.mode in ("anchor", "shield"):
                dissenter = _pick_dissenter(
                    scenario, fixture, schedule, rng
                )
                dissent_events += 1
                tokens += DISSENT_TOKENS
                if schedule.mode == "anchor":
                    anchor_answer = state[dissenter]
                else:
                    shielded = True
            else:
                raise ValueError("unknown mode: %s" % schedule.mode)
        leader = plurality(state, private)
        leading_wrong = _leading_wrong(state, fixture.correct, private)
        new_state = list(state)
        for index, agent in enumerate(scenario.agents):
            if dissenter is not None and index == dissenter \
                    and schedule is not None \
                    and schedule.mode in ("anchor", "revival"):
                continue
            if state[index] == fixture.correct and leading_wrong is not None:
                peers = n_agents - 1
                holders = sum(
                    1
                    for other, held in enumerate(state)
                    if other != index and held == leading_wrong
                )
                pressure = holders / float(peers) if peers else 0.0
                prob = agent.fragility * pressure
                if shielded:
                    prob *= 1.0 - SHIELD_STRENGTH
                if rng.random() < prob:
                    new_state[index] = leading_wrong
                    flips.append({
                        "round": round_index,
                        "agent": index,
                        "from": state[index],
                        "to": leading_wrong,
                        "channel": "fragility",
                    })
                    continue
            if state[index] != leader:
                if rng.random() < agent.conformity:
                    target = leader
                    channel_note = "plurality"
                    if anchor_answer is not None \
                            and anchor_answer != leader:
                        dissenter_agent = scenario.agents[dissenter]
                        credibility = dissenter_agent.estimated_skill
                        if credibility is None:
                            credibility = dissenter_agent.skill
                        if rng.random() < credibility:
                            target = anchor_answer
                            channel_note = "anchor"
                    new_state[index] = target
                    flips.append({
                        "round": round_index,
                        "agent": index,
                        "from": state[index],
                        "to": target,
                        "channel": "conformity",
                        "target": channel_note,
                    })
        state = new_state
        tokens += n_agents * STATEMENT_TOKENS
        snapshots.append(list(state))
        if fixture.correct not in state and extinct_round is None:
            extinct_round = round_index
    final = plurality(state, private)
    return DebateResult(
        fixture=fixture,
        final_answer=final,
        tokens=tokens,
        dissent_events=dissent_events,
        snapshots=snapshots,
        flips=flips,
        extinct_round=extinct_round,
    )


def run_no_debate(scenario, fixture):
    """Round-0 plurality vote: no rounds, no dissent."""
    return DebateResult(
        fixture=fixture,
        final_answer=plurality(
            fixture.private_answers, fixture.private_answers
        ),
        tokens=scenario.n_agents * STATEMENT_TOKENS,
        dissent_events=0,
        snapshots=[list(fixture.private_answers)],
        flips=[],
        extinct_round=0 if not fixture.correct_present else None,
    )


def run_policy(scenario, fixtures, rounds, schedule=None,
               policy_key="free", keep_results=False):
    """Run one policy over fixtures; return aggregate metrics."""
    n_correct = 0
    total_tokens = 0
    total_dissent = 0
    results = []
    for fixture in fixtures:
        if policy_key == "no_debate":
            result = run_no_debate(scenario, fixture)
        else:
            result = run_debate(
                scenario, fixture, rounds,
                schedule=schedule, policy_key=policy_key,
            )
        if result.correct:
            n_correct += 1
        total_tokens += result.tokens
        total_dissent += result.dissent_events
        if keep_results:
            results.append(result)
    n_cases = len(fixtures)
    return {
        "accuracy": n_correct / float(n_cases) if n_cases else 0.0,
        "mean_tokens": total_tokens / float(n_cases) if n_cases else 0.0,
        "mean_dissent_events": (
            total_dissent / float(n_cases) if n_cases else 0.0
        ),
        "n_cases": n_cases,
        "results": results,
    }


def oracle_accuracy(fixtures):
    """Share of cases where the correct answer is in the private pool."""
    if not fixtures:
        return 0.0
    hits = sum(1 for fixture in fixtures if fixture.correct_present)
    return hits / float(len(fixtures))


def gap_closure(accuracy, baseline_accuracy, oracle):
    """Fraction of the no-debate -> oracle gap a policy closes."""
    denominator = oracle - baseline_accuracy
    if denominator <= 1e-9:
        return 0.0
    return (accuracy - baseline_accuracy) / denominator
