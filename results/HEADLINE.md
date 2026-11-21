# Headline results

Dissent on a schedule, priced in tokens, on 12 seeded debate scenarios (team sizes 3-10, three diversity profiles), with real measured accuracies from the seeded simulator.

- Scheduled dissent reaches mean accuracy **0.793** vs free debate **0.743** and the no-debate vote **0.811** (oracle 0.977): +0.050 over free debate, beating it in 10 of 12 scenarios and hurting in 2.
- Free debate *loses* 0.069 accuracy to the no-debate vote in these populations; scheduled dissent recovers **73%** of that self-inflicted loss, and matches or beats the vote in 1 of 12 scenarios. Closure per 1k tokens: scheduled -0.0751 vs free debate -0.3832.
- Dissenting constantly is worse than not dissenting at all: always-dissent reaches 0.703, below free debate's 0.743, and random-timing dissent reaches 0.763 -- the scheduled gain comes from mode and timing, not from dissent volume.
- At equal tokens, extra free-debate rounds reach 0.729 -- scheduled dissent beats that counterfactual by +0.064.
- Failure pathways in free debate: sycophantic conformity 18.9%, fragility 17.6%, consensus collapse 63.5% of attributable failures.
- Showcase (low-3): schedule shield:every_round:top_skill lifts accuracy from 0.381 (free debate) to 0.556 -- the largest rescue in the grid. The no-debate vote reaches 0.575 there and the oracle 0.894, so even the best rescue mostly repairs debate's own damage rather than beating silence.

Caveat: all teams and cases are synthetic and seeded, with agent parameters known by construction; the experiment validates the scheduler and the pathway audit under that model, not any live model team.
