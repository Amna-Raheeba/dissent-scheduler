# Changelog

## 0.1.0 — 2026-11-21

- Initial release.
- Seeded debate simulator: agents with known skill, conformity and
  fragility debate cases with a planted distractor option; every flip
  is recorded with its behavioural channel (conformity / fragility /
  revival).
- Failure-pathway audit: free-debate failures classified as
  sycophantic conformity, fragility, or consensus collapse (with the
  collapse driver reported), excluding cases no agent was privately
  right about; each pathway maps to a recommended dissent mode.
- Three dissent modes (anchor, shield, revival) and five triggers
  (every round, first, last, contested, extinct); 20-schedule search
  space ranked by oracle-gap closure per 1k tokens on calibration
  cases.
- Skill calibration from a labelled probe set of private answers --
  the scheduler runs on estimates, never on true parameters.
- Headline evaluation: 12 scenarios (team sizes 3-10 x three
  diversity profiles) comparing no-debate, free debate,
  always-dissent, random-timing dissent, scheduled dissent, and free
  debate extended to an equal token budget, against the
  private-pool oracle.
- Streamlit dashboard (3 tabs), CLI, notebooks, and a reproducibility
  script with a headline-drift guard.
