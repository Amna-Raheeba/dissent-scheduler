# Dissent Scheduler

Dissent in a multi-agent debate, **on a schedule and priced in
tokens**: a failure-pathway audit that diagnoses *why* a debate is
losing correct answers, plus a scheduler that searches when, how, and
through whom dissent should be injected to rescue them — reporting
oracle-gap closure per 1k tokens, not just accuracy.

## 1. What it is

Multi-agent debate is usually run unguided: agents state answers, see
each other's, and update. "The Cost of Consensus" (2026) showed on
live model teams that this often *loses* to not debating at all, and
named three failure pathways — sycophantic conformity, fragility, and
consensus collapse — but tested no intervention.

This tool is the prescriptive follow-up, built offline where every
agent's private correctness, conformity, and fragility are ground
truth. Given a team, it returns:

1. a **pathway audit** of free debate: how many failures were
   sycophantic conformity (correct holders flipped to a wrong
   plurality), fragility (correct holders destabilised by the leading
   wrong answer), or consensus collapse (the correct answer's last
   holder flipped before the final round) — excluding cases no agent
   was privately right about, which no debate policy can rescue;
2. a **searched dissent schedule** — mode (anchor / shield / revival),
   trigger (every round, first, last, contested-only, extinction-only),
   and dissenter (highest estimated skill, or seeded random) — chosen
   on calibration cases by oracle-gap closure per 1k tokens;
3. a **priced policy table**: no-debate vote, free debate,
   always-dissent, random-timing dissent, the scheduled policy, and
   free debate extended with extra rounds to the same token budget —
   each with accuracy, tokens per case, and gap closure.

Skills are never assumed: the tool estimates them from a labelled
probe set (private answers only, no debate), exactly the pre-flight
measurement a real deployment could run. Everything is offline,
deterministic and seeded. Pure Python standard library; no API keys,
no model downloads, no network.

## 2. The novel mechanism

**Debate dynamics with recorded causes.** Each agent carries three
latent parameters — skill (private accuracy), conformity (probability
of flipping to the plurality when it disagrees), fragility
(probability scale for a correct holder to be destabilised by the
leading wrong answer, weighted by peer share). A planted *distractor*
option attracts missed answers with probability `distractor_pull`,
which is what lets a wrong majority form at all. Every flip is
recorded with its channel, so failure attribution is read off the
trace, not guessed.

**Three dissent modes, one per pathway.**

- **anchor** (targets conformity): the dissenter holds its answer and
  conformity flips are redirected to the dissenter's answer with
  probability equal to the dissenter's estimated skill — conformists
  follow the loudest credible voice instead of the crowd;
- **shield** (targets fragility): fragility flips are damped by 75%
  on dissent rounds — public dissent legitimises holding a minority
  view, so correct agents are harder to destabilise;
- **revival** (targets collapse): an answer present in round 0 but
  currently holderless is re-seated with its most credible original
  holder, who holds for the round, and each other original holder
  returns to it with probability 0.5.

**Scheduling, not volume.** Triggers spend dissent only where it can
matter — e.g. `contested` fires only while the plurality share is
below 0.6, i.e. where the early reviewers actually disagree. The
search ranks schedules by **oracle-gap closure per 1k tokens**: the
fraction of the gap between the no-debate vote and the oracle
(correct answer present in the private pool) that the schedule
closes, per thousand tokens spent. Accuracy alone would reward
spending; tokens alone would reward silence.

## 3. Prior art and the differentiator

- **"The Cost of Consensus" (2026)** diagnoses the three pathways on
  live 7–8B model teams and concludes unguided debate loses to
  isolated self-correction — but tests no intervention.
- The debate / self-consistency literature tunes *whether* to debate
  or how many samples to draw; interventions, when tried, are
  unguided (a fixed devil's advocate, a fixed number of rounds).

None of it schedules the intervention: which mode, at which round,
through which agent, at what token price, chosen against measured
failure pathways. The differentiator is a costed, calibrated
intervention policy — the prescriptive follow-up to a published
diagnosis, evaluated offline where the correct answer and every
agent's private state are ground truth.

## 4. Measured headline results

Seeded evaluation, 12 scenarios (team sizes 3–10 × diversity profiles
low / medium / high), 160 held-out cases per scenario, 4 debate
rounds. Skills estimated from a 60-case probe; schedules searched on
80 calibration cases per scenario. Full detail in `results/`.

- Mean accuracy: no-debate vote **0.811**, free debate **0.743**,
  always-dissent **0.703**, random-timing dissent **0.763**,
  **scheduled 0.793**, free debate extended to equal tokens **0.729**,
  oracle **0.977**.
- Scheduled dissent beats free debate by **+0.050** on average, in
  **10 of 12** scenarios (it hurts in 2, both 10-agent teams where
  calibration picked a last-round anchor) — and beats the equal-token
  counterfactual (just buy more debate rounds) by **+0.064**.
- **Dissenting constantly is worse than not dissenting at all:**
  always-dissent (0.703) finishes *below* free debate (0.743). The
  scheduled gain comes from mode and timing, not dissent volume.
- Free debate loses 0.069 accuracy to the plain no-debate vote in
  these populations; scheduled dissent recovers **73%** of that
  self-inflicted loss, but matches or beats the vote in only 1 of 12
  scenarios. Dissent mostly repairs debate's damage — it does not
  make debate better than silence here, and the tool says so.
- Failure pathways among attributable free-debate failures:
  **consensus collapse 63.5%**, sycophantic conformity 18.9%,
  fragility 17.6%.
- The audit's mode recommendation and the priced search disagree,
  measurably: collapse dominates, so the audit recommends revival in
  11 of 12 scenarios — but the search picks **shield in 10 of 12**.
  Preventing destabilisation prices better than reviving extinct
  answers.
- **Showcase** (low-3, a 3-agent low-diversity team): free debate
  collapses to 0.381; the searched schedule
  (`shield:every_round:top_skill`) rescues it to **0.556** — still
  short of the no-debate vote (0.575) and the oracle (0.894).

## 5. Quick start

```bash
pip install -r requirements.txt

python -m dissent_sched demo                               # built-in demo team
python -m dissent_sched audit --scenario examples/demo_scenario.json
python -m dissent_sched schedule --scenario examples/demo_scenario.json
python -m dissent_sched evaluate                           # regenerate results/
python examples/run_audit.py                               # audit via the example script
streamlit run app.py                                       # dashboard (3 tabs)
```

Scenario format: JSON with `name`, `agents` (each with `skill`,
`conformity`, `fragility`), `distractor_pull`, and `seed` (see
`examples/demo_scenario.json`). True parameters are the simulator's
ground truth; the scheduler itself only ever uses probe-estimated
skills.

## 6. How it works

1. **Calibrate** — estimate each agent's skill from a labelled probe
   set of private answers; no debate involved.
2. **Diagnose** — run free debate on calibration cases and classify
   every attributable failure by pathway from its recorded flips.
3. **Search** — price all 20 schedules (3 modes × 5 triggers, with
   the dissenter varied only where an individual dissenter acts) on
   the calibration cases; rank by gap closure per 1k tokens.
4. **Evaluate** — run the chosen schedule and the five baselines on
   held-out cases with identical private answers, and report
   accuracy, tokens, closure, and the pathway mix side by side.

## 7. Repository layout

```
dissent_sched/       the package (models, generate, simulate, audit,
                     schedule, evaluate, report, cli)
data/                the 12 evaluation scenario teams
tests/               pytest suite (68 tests)
notebooks/           01_demo_run.py, 02_evaluation_experiment.py
examples/            demo scenario, runner, sample report
scripts/             build_cases.py, reproduce_results.py (drift guard)
results/             evaluation.json/.csv, evaluation_summary.md, HEADLINE.md
app.py               Streamlit dashboard (Schedule / Pathways / Evaluation)
```

## 8. Honest limits

- **Synthetic teams only.** Every number above is measured on seeded
  synthetic teams whose skill, conformity, fragility, and distractor
  pull are known by construction. The experiment validates the
  scheduler, the audit, and the pricing under that model; it does not
  measure any live model team, whose parameters must be estimated
  from real debate logs and will be noisier.
- **The no-debate vote is a strong baseline here.** In these
  conformity-prone populations debate itself is the main problem, and
  scheduled dissent's measured job is damage recovery (73% of the
  loss), not dominance over aggregation. Populations where debate
  genuinely adds signal (e.g. agents with complementary knowledge)
  are not modelled — private answers here are independent draws given
  skill and the distractor.
- **Attribution is exact by construction.** Pathway labels come from
  the simulator's own flip channels. On real logs the channels are
  latent and would have to be inferred; the audit's taxonomy and
  counting conventions are the transferable part.
- **Declared token prices.** A statement costs 48 tokens and a
  dissent intervention 140 by declaration, not by measurement. The
  rankings are robust to the ratio only within reason; re-declare
  them for a real system before trusting the chosen schedule.
- **Calibration noise.** Schedules are searched on 80 cases, so
  near-tied schedules are interchangeable; the search's preference
  for shield over revival is consistent across scenarios, but
  individual trigger choices should not be over-read.
- **Simple dynamics.** Simultaneous updates, plurality aggregation
  with a fixed tie-break, no agent memory across cases, no argument
  content — dissent is a behavioural intervention, not a textual one.

## 9. Reproducing the results

```bash
python scripts/build_cases.py        # regenerate data/ and the demo files
python -m dissent_sched evaluate    # regenerate results/
python scripts/reproduce_results.py  # re-run and check for headline drift
pytest                               # full test suite
```

## 10. License

MIT. Author: Amna Raheeba.
