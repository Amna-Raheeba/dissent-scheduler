# Evaluation summary

Seeded evaluation: 12 scenarios (team sizes [3, 5, 7, 10], diversity profiles ['low', 'medium', 'high']), 160 held-out cases per scenario, 4 debate rounds. Skills are estimated from a 60-case probe and schedules are searched on 80 calibration cases per scenario; no policy sees true parameters or the truth.

## Aggregates

- Mean accuracy: no-debate 0.811, free debate 0.743, always-dissent 0.703, random dissent 0.763, scheduled 0.793, free debate extended to equal tokens 0.729, oracle 0.977.
- Scheduled dissent vs free debate: +0.050 accuracy on average; it beats free debate in 10 of 12 scenarios and hurts in 2.
- Oracle-gap closure: free debate -0.414, always-dissent -0.843, random dissent -0.348, scheduled -0.146, extended free debate -0.516.
- Closure per 1k tokens: free debate -0.3832, scheduled -0.0751 (mean tokens per case: free 1500, scheduled 1990, always-dissent 1689).
- Failure pathways among attributable free-debate failures: sycophantic conformity 18.9%, fragility 17.6%, consensus collapse 63.5% (mean of per-scenario shares).

## Scenarios

| scenario | no debate | free | always | random | scheduled | extended | oracle | schedule |
|---|---|---|---|---|---|---|---|---|
| low-3 | 0.575 | 0.381 | 0.412 | 0.456 | 0.556 | 0.369 | 0.894 | shield:every_round:top_skill |
| medium-3 | 0.738 | 0.606 | 0.525 | 0.656 | 0.706 | 0.600 | 0.906 | shield:every_round:top_skill |
| high-3 | 0.756 | 0.656 | 0.581 | 0.700 | 0.725 | 0.637 | 0.963 | shield:every_round:top_skill |
| low-5 | 0.738 | 0.681 | 0.644 | 0.694 | 0.719 | 0.669 | 0.988 | shield:every_round:top_skill |
| medium-5 | 0.850 | 0.806 | 0.787 | 0.794 | 0.844 | 0.769 | 0.988 | shield:every_round:top_skill |
| high-5 | 0.812 | 0.719 | 0.644 | 0.769 | 0.800 | 0.694 | 0.988 | shield:every_round:top_skill |
| low-7 | 0.769 | 0.681 | 0.694 | 0.750 | 0.750 | 0.656 | 1.000 | shield:every_round:top_skill |
| medium-7 | 0.919 | 0.881 | 0.850 | 0.894 | 0.906 | 0.863 | 1.000 | shield:every_round:top_skill |
| high-7 | 0.950 | 0.919 | 0.887 | 0.931 | 0.938 | 0.906 | 1.000 | shield:every_round:top_skill |
| low-10 | 0.787 | 0.762 | 0.725 | 0.731 | 0.750 | 0.762 | 1.000 | anchor:last_round:top_skill |
| medium-10 | 0.950 | 0.931 | 0.812 | 0.894 | 0.925 | 0.931 | 1.000 | anchor:last_round:top_skill |
| high-10 | 0.894 | 0.887 | 0.869 | 0.887 | 0.894 | 0.887 | 1.000 | shield:every_round:top_skill |
