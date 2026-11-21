"""Failure-pathway audit: *why* did the debate lose this case?

The audit replays free debate (no dissent) and classifies every failed
case in which the correct answer was privately present into one of the
three failure pathways named by "The Cost of Consensus":

- **consensus collapse** -- the correct answer's holders hit zero
  before the final round: the answer was present, then voted away
  entirely, so no final-round recovery was possible;
- **sycophantic conformity** -- the correct answer survived to the end
  but lost, and at least half of its holder losses were conformity
  flips to a wrong plurality;
- **fragility** -- the correct answer survived but lost mainly through
  fragility flips: correct holders destabilised by the leading wrong
  answer rather than following the crowd.

Cases where no agent was privately correct are counted separately as
``absent`` -- no debate policy can rescue an answer nobody holds, and
mixing them in would flatter or damn every policy for the wrong reason.

Each pathway maps to the dissent mode that targets it: conformity ->
anchor, fragility -> shield, collapse -> revival. The audit reports
the dominant pathway and therefore the recommended mode. Attribution
is by recorded flip channel, i.e. exact under the simulator's own
dynamics -- the honest claim is about these seeded debates, and the
README says so.
"""

from .simulate import run_debate

PATHWAYS = ("sycophantic_conformity", "fragility", "consensus_collapse")

PATHWAY_TO_MODE = {
    "sycophantic_conformity": "anchor",
    "fragility": "shield",
    "consensus_collapse": "revival",
}


def classify_failure(result, rounds):
    """Classify one debate result. Returns a pathway name, ``absent``,
    or None when the debate ended correct."""
    fixture = result.fixture
    if not fixture.correct_present:
        return "absent"
    if result.correct:
        return None
    correct_losses = [
        flip for flip in result.flips if flip["from"] == fixture.correct
    ]
    if result.extinct_round is not None and result.extinct_round < rounds:
        return "consensus_collapse"
    conformity_losses = sum(
        1 for flip in correct_losses if flip["channel"] == "conformity"
    )
    fragility_losses = sum(
        1 for flip in correct_losses if flip["channel"] == "fragility"
    )
    if conformity_losses >= fragility_losses:
        return "sycophantic_conformity"
    return "fragility"


def collapse_driver(result):
    """Dominant flip channel among correct-holder losses, or None."""
    fixture = result.fixture
    correct_losses = [
        flip for flip in result.flips if flip["from"] == fixture.correct
    ]
    if not correct_losses:
        return None
    conformity_losses = sum(
        1 for flip in correct_losses if flip["channel"] == "conformity"
    )
    if conformity_losses * 2 >= len(correct_losses):
        return "conformity"
    return "fragility"


def diagnose(scenario, fixtures, rounds=4):
    """Run free debate and classify every failure by pathway."""
    counts = dict((pathway, 0) for pathway in PATHWAYS)
    absent = 0
    failed = 0
    correct_final = 0
    collapse_drivers = {"conformity": 0, "fragility": 0}
    for fixture in fixtures:
        result = run_debate(scenario, fixture, rounds, policy_key="free")
        label = classify_failure(result, rounds)
        if label == "absent":
            absent += 1
            failed += 1
        elif label is None:
            correct_final += 1
        else:
            counts[label] += 1
            failed += 1
            if label == "consensus_collapse":
                driver = collapse_driver(result)
                if driver is not None:
                    collapse_drivers[driver] += 1
    attributable = sum(counts.values())
    shares = dict(
        (pathway, (counts[pathway] / float(attributable))
         if attributable else 0.0)
        for pathway in PATHWAYS
    )
    dominant = None
    if attributable:
        dominant = max(PATHWAYS, key=lambda name: (counts[name], name))
    return {
        "n_cases": len(fixtures),
        "n_failed": failed,
        "n_correct_final": correct_final,
        "n_absent": absent,
        "pathway_counts": counts,
        "pathway_shares": shares,
        "collapse_drivers": collapse_drivers,
        "dominant_pathway": dominant,
        "recommended_mode": (
            PATHWAY_TO_MODE[dominant] if dominant is not None else None
        ),
    }
