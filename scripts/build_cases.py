"""Generate the stored case data.

Writes:
- data/scenarios.json: the team of every evaluation scenario, using
  the same seed scheme as dissent_sched.evaluate, so the stored teams
  are exactly the ones the headline evaluation debates with.
- examples/demo_scenario.json: the demo team used by the CLI demo and
  the examples.

Run: python scripts/build_cases.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dissent_sched.cli import DEMO_SCENARIO
from dissent_sched.evaluate import DEFAULT_CONFIG
from dissent_sched.generate import build_scenario


def main():
    root = os.path.join(os.path.dirname(__file__), "..")
    cfg = DEFAULT_CONFIG
    scenarios = []
    index = 0
    for n_agents in cfg["sizes"]:
        for diversity in cfg["diversities"]:
            seed = cfg["base_seed"] + 1000 * index
            scenario = build_scenario(n_agents, diversity, seed)
            scenarios.append(scenario.to_dict())
            index += 1
    data_path = os.path.join(root, "data", "scenarios.json")
    with open(data_path, "w") as handle:
        json.dump({"scenarios": scenarios}, handle, indent=2)
    print("Wrote %s (%d scenarios)" % (data_path, len(scenarios)))

    demo_path = os.path.join(root, "examples", "demo_scenario.json")
    with open(demo_path, "w") as handle:
        json.dump(DEMO_SCENARIO.to_dict(), handle, indent=2)
    print("Wrote %s" % demo_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
