"""Core data model for the dissent scheduler.

A *scenario* is one team debating one population of cases. Every agent
has three latent parameters, known to the simulator by construction:

- ``skill``: probability that the agent's private (pre-debate) answer
  is correct;
- ``conformity``: probability that, in a debate round, an agent who
  disagrees with the plurality answer abandons its own answer for the
  plurality answer (sycophantic conformity);
- ``fragility``: probability scale with which an agent holding the
  correct answer is destabilised by the leading wrong answer among its
  peers (it flips to that wrong answer with probability
  ``fragility * peer_share``).

Each case also plants a *distractor*: one wrong option that privately
attracts agents who miss the correct answer, with probability
``distractor_pull``. A strong distractor is what makes a wrong majority
possible at all -- without it, wrong answers scatter and the correct
answer usually wins the plurality.

Token pricing is declared, not measured: one agent statement (answer
plus short rationale) costs ``STATEMENT_TOKENS``; one dissent
intervention (a argued case for a minority answer) costs
``DISSENT_TOKENS`` on top of the dissenter's normal statement.
"""

import zlib

N_OPTIONS = 4
STATEMENT_TOKENS = 48
DISSENT_TOKENS = 140
SHIELD_STRENGTH = 0.75

DIVERSITY_PROFILES = {
    # distractor_pull: how strongly a missed answer collapses onto the
    # planted distractor; skill_lo/hi: private-accuracy range of the team.
    "low": {"distractor_pull": 0.65, "skill_lo": 0.50, "skill_hi": 0.60},
    "medium": {"distractor_pull": 0.40, "skill_lo": 0.45, "skill_hi": 0.75},
    "high": {"distractor_pull": 0.15, "skill_lo": 0.40, "skill_hi": 0.85},
}


def derive_seed(*parts):
    """Deterministic 32-bit seed from arbitrary parts (never hash())."""
    key = "|".join(str(part) for part in parts)
    return zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF


class Agent(object):
    """One debater: latent parameters plus a calibrated skill estimate."""

    def __init__(self, skill, conformity, fragility, estimated_skill=None):
        self.skill = float(skill)
        self.conformity = float(conformity)
        self.fragility = float(fragility)
        self.estimated_skill = (
            float(estimated_skill) if estimated_skill is not None else None
        )

    def to_dict(self):
        return {
            "skill": self.skill,
            "conformity": self.conformity,
            "fragility": self.fragility,
            "estimated_skill": self.estimated_skill,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            skill=data["skill"],
            conformity=data["conformity"],
            fragility=data["fragility"],
            estimated_skill=data.get("estimated_skill"),
        )


class Scenario(object):
    """A team plus the case-population parameters it debates."""

    def __init__(self, name, agents, distractor_pull, seed):
        self.name = name
        self.agents = list(agents)
        self.distractor_pull = float(distractor_pull)
        self.seed = int(seed)

    @property
    def n_agents(self):
        return len(self.agents)

    def to_dict(self):
        return {
            "name": self.name,
            "agents": [agent.to_dict() for agent in self.agents],
            "distractor_pull": self.distractor_pull,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            agents=[Agent.from_dict(item) for item in data["agents"]],
            distractor_pull=data["distractor_pull"],
            seed=data["seed"],
        )


class CaseFixture(object):
    """One case with ground truth and every agent's private answer.

    Fixtures are generated once per (scenario, case index) and shared by
    every policy, so policies face identical private answers -- the
    comparison is about debate dynamics, not sampling luck.
    """

    def __init__(self, case_id, correct, distractor, private_answers):
        self.case_id = int(case_id)
        self.correct = int(correct)
        self.distractor = int(distractor)
        self.private_answers = list(private_answers)

    @property
    def correct_present(self):
        return self.correct in self.private_answers

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "correct": self.correct,
            "distractor": self.distractor,
            "private_answers": list(self.private_answers),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            case_id=data["case_id"],
            correct=data["correct"],
            distractor=data["distractor"],
            private_answers=data["private_answers"],
        )


def plurality(answers, tiebreak_answers=None):
    """Plurality answer with a deterministic tie-break.

    Ties break toward the answer with more support in
    ``tiebreak_answers`` (the round-0 private answers), then toward the
    lowest option index.
    """
    counts = {}
    for answer in answers:
        counts[answer] = counts.get(answer, 0) + 1
    tie_counts = {}
    if tiebreak_answers is not None:
        for answer in tiebreak_answers:
            tie_counts[answer] = tie_counts.get(answer, 0) + 1
    best = None
    best_key = None
    for answer in sorted(counts):
        key = (counts[answer], tie_counts.get(answer, 0), -answer)
        if best_key is None or key > best_key:
            best = answer
            best_key = key
    return best


def vote_share(answers, answer):
    if not answers:
        return 0.0
    return sum(1 for item in answers if item == answer) / float(len(answers))
