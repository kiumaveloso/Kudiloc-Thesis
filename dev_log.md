# Dev Log

## Day 1 — [today's date]

- Ground truth, reporters, and report stream are seed-reproducible.
- Adversarial reporters deliberately flip state; unreliable reporters make
  random honest mistakes, kept these conceptually distinct.
- Majority Vote tie-break defaults to `True` (stocked), a documented
  methodological choice.
- Confirmed baseline behavior: 100% accuracy at low adversarial fraction
  (0.1), collapsing to 14% at high adversarial fraction (0.6), demonstrates
  the exact failure mode motivating Reputation-Weighted/Time-Decayed
  algorithms.

**Open question for tomorrow:** exact learning rule for reputation updates
(how often ground truth is "revealed," how much reporters gain/lose
reputation per correct/incorrect report).

## Day 2 — [today's date]
- Resolved open question from Day 1: reputation is **cross-ATM (global)**,
  not per-ATM. Reasoning:
  - `Reporter.reputation` is a single float per reporter in the data model,
    not indexed by atm_id — the model already assumes a global score.
  - Docstring specifies reputation updates when ground truth is
    "periodically revealed" — implies fixed-interval reveal events across
    the population, not per-ATM repeat queries.
  - No experiment runner exists yet with a notion of "rounds" on the same
    ATM, so same-ATM history isn't currently producible anyway.
- Design consequence: reputation needs time/volume to converge. Early in
  a simulation run, Reputation-Weighted may perform close to Majority Vote
  simply because reputations haven't stabilized yet. This should be
  measured explicitly (accuracy over simulated time / reporter volume),
  not just as a single end-state number — ties into RQ2 (adversarial
  resilience) and needs a "Threats to Validity" note on global vs
  per-location reputation trade-offs.
- Next: implement `src/simulation/reputation.py` (fixed-interval
  ground-truth reveal + multiplicative reward/penalty update, reward 1.1,
  penalty 0.9, clamp [0.01, 10.0]), then `ReputationWeightedAggregation`
  in `src/algorithms/`.
## Day 3 — Phase 2 close-out
- Implemented ReputationWeightedAggregation (src/algorithms/reputation_weighted.py)
  and the cross-ATM reputation update logic (src/simulation/reputation.py),
  per the Day 2 design decision: global reputation, multiplicative
  reward/penalty (1.1 / 0.9), clamped to [0.01, 10.0], updated via
  fixed-interval ground-truth reveals.
- Implemented TimeDecayedTrustScoring (src/algorithms/time_decayed.py):
  weight = reputation * e^(-lambda * age), lambda derived from a 12-hour
  half-life (lambda = ln(2)/12 ~= 0.0578). One simulated time unit is
  treated as one hour, a modeling assumption chosen to reflect realistic
  ATM cash-availability volatility in the Angola crowd-sourcing context
  (documented as an assumption, not an empirical constant).
- **Staleness bug found and fixed**: the original maybe_flip_states()
  applies an instantaneous, timestamp-blind flip to an ATM's true_state,
  so every report for a flipped ATM becomes equally right/wrong
  regardless of when it was submitted. This eliminated the
  recency-correctness gradient Time-Decayed is designed to exploit,
  confirmed when a naive staleness sanity check produced a weak,
  inconsistent result (+4%, sometimes even negative) that vanished under
  proper multi-seed averaging (~+1%, statistical noise).
  Root cause traced and fixed by adding flip_time / pre_flip_state
  fields to ATM, a generate_flip_times() function that assigns each
  flipping ATM an explicit moment of change within the report window,
  and a true_state_at(atm, timestamp) lookup. report_stream.py was
  updated to check each report's truth against its own timestamp instead
  of a single static true_state.
- Sanity check results (single seed, seed=42/7):
    Majority Vote (adversarial=0.6):        14.00%
    Reputation-Weighted (adversarial=0.6):  84.00%  (+70.00 pts vs MV)
    Reputation-Weighted (stale scenario):   62.00%
    Time-Decayed (stale scenario):          84.00%  (+22.00 pts vs RW)
  30-seed averaged staleness check (flip_prob=0.5, adversarial=0.0,
  isolating pure staleness from adversarial noise): RW 79.53% vs
  TD 88.93% (+9.40 pts) — confirms the effect is real and not seed luck.
- All three algorithms (MajorityVote, ReputationWeightedAggregation,
  TimeDecayedTrustScoring) run through compute_accuracy() unchanged,
  validating the shared AggregationAlgorithm interface design.
- Lesson for methodology chapter: always average comparative results
  over many seeds before treating a difference as real; a single seed
  can flip direction entirely (observed -2% to +4% swing pre-fix on
  what turned out to be pure noise).

## Day 3 — Phase 2 close-out
- Implemented ReputationWeightedAggregation (src/algorithms/reputation_weighted.py)
  and the cross-ATM reputation update logic (src/simulation/reputation.py),
  per the Day 2 design decision: global reputation, multiplicative
  reward/penalty (1.1 / 0.9), clamped to [0.01, 10.0], updated via
  fixed-interval ground-truth reveals.
- Implemented TimeDecayedTrustScoring (src/algorithms/time_decayed.py):
  weight = reputation * e^(-lambda * age), lambda derived from a 12-hour
  half-life (lambda = ln(2)/12 ~= 0.0578). One simulated time unit is
  treated as one hour, a modeling assumption chosen to reflect realistic
  ATM cash-availability volatility in the Angola crowd-sourcing context
  (documented as an assumption, not an empirical constant).
- **Staleness bug found and fixed**: the original maybe_flip_states()
  applies an instantaneous, timestamp-blind flip to an ATM's true_state,
  so every report for a flipped ATM becomes equally right/wrong
  regardless of when it was submitted. This eliminated the
  recency-correctness gradient Time-Decayed is designed to exploit,
  confirmed when a naive staleness sanity check produced a weak,
  inconsistent result (+4%, sometimes even negative) that vanished under
  proper multi-seed averaging (~+1%, statistical noise).
  Root cause traced and fixed by adding flip_time / pre_flip_state
  fields to ATM, a generate_flip_times() function that assigns each
  flipping ATM an explicit moment of change within the report window,
  and a true_state_at(atm, timestamp) lookup. report_stream.py was
  updated to check each report's truth against its own timestamp instead
  of a single static true_state.
- Sanity check results (single seed, seed=42/7):
    Majority Vote (adversarial=0.6):        14.00%
    Reputation-Weighted (adversarial=0.6):  84.00%  (+70.00 pts vs MV)
    Reputation-Weighted (stale scenario):   62.00%
    Time-Decayed (stale scenario):          84.00%  (+22.00 pts vs RW)
  30-seed averaged staleness check (flip_prob=0.5, adversarial=0.0,
  isolating pure staleness from adversarial noise): RW 79.53% vs
  TD 88.93% (+9.40 pts) — confirms the effect is real and not seed luck.
- All three algorithms (MajorityVote, ReputationWeightedAggregation,
  TimeDecayedTrustScoring) run through compute_accuracy() unchanged,
  validating the shared AggregationAlgorithm interface design.
- Lesson for methodology chapter: always average comparative results
  over many seeds before treating a difference as real; a single seed
  can flip direction entirely (observed -2% to +4% swing pre-fix on
  what turned out to be pure noise).

## Day 4 — Phase 3: RQ2/RQ3 sweeps
- Built experiments/common.py (shared run_periodic_reveals helper, used
  by both sweep scripts to avoid duplicating Phase 2 logic).
- RQ2 sweep (experiments/run_adversarial_sweep.py): adversarial_fraction
  from 0.0 to 0.8 (9 points), 30 seeds each, no staleness. Results in
  results/adversarial_sweep.csv.
    Key finding: Majority Vote collapses from 98.5% to 1.2% accuracy as
    adversarial_fraction rises; Reputation-Weighted stays robust down to
    73.3% even at 80% adversarial reporters. Time-Decayed consistently
    trails Reputation-Weighted slightly in this sweep (e.g. 89.5% vs
    94.9% at fraction=0.5) — expected, since decay adds noise by
    down-weighting valid recent reports when nothing is actually stale.
- RQ3 sweep (experiments/run_staleness_sweep.py): flip_probability from
  0.0 to 0.8 (9 points), 30 seeds each, adversarial_fraction fixed at 0
  to isolate staleness cleanly. Uses generate_flip_times() (not the
  timestamp-blind maybe_flip_states()) for genuine per-report staleness.
  Results in results/staleness_sweep.csv.
    Key finding: clean crossover pattern. At flip_probability=0.0,
    Reputation-Weighted slightly beats Time-Decayed (99.5% vs 97.1%,
    consistent with the RQ2 finding above). Time-Decayed overtakes
    around flip_probability~0.1-0.2 and the gap widens steadily,
    reaching +16.1 pts (80.3% vs 64.2%) at flip_probability=0.8.
- Still open for Phase 3: add standard deviation / confidence intervals
  to sweep output (currently means only); generate figures from the CSV
  data; consider a half-life sensitivity check (6h/12h/24h) as a
  robustness argument; write Results chapter text around this data.
dev_log.md updatedcat

## Day 4 (cont.) — Added confidence intervals to sweeps
- Added summarize() helper to experiments/common.py: mean, sample std,
  and 95% CI half-width (normal approximation, 1.96 * SE — reasonable at
  n=30, avoids a scipy dependency; noted as a simplification).
- Both sweep scripts now print mean±CI and write a *_summary.csv
  alongside the raw per-seed CSV (results/adversarial_sweep_summary.csv,
  results/staleness_sweep_summary.csv).
- CIs sharpen the RQ3 story: at flip_probability=0.1 the RW and TD
  intervals overlap (95.13%±0.95% vs 94.67%±1.19%, not distinguishable);
  by flip_probability=0.2 they separate cleanly (91.00%±0.99% vs
  93.20%±1.12%). So Time-Decayed's advantage becomes statistically
  significant once ~20% of ATMs change state during the report window.

## Day 5 — Phase 3: half-life sensitivity check
- Added experiments/run_halflife_sensitivity.py: reruns the RQ3 staleness
  scenario at three half-lives (6h, 12h, 24h), 30 seeds per point,
  reusing the same generated scenario across half-lives so any accuracy
  difference is attributable to the decay rate alone. Reputation-Weighted
  is computed once per scenario as a fixed reference (it has no decay
  parameter). Output: results/halflife_sensitivity.csv
- Result summary (mean accuracy, 30 seeds):
    flip=0.0  RW=99.67%  TD@6h=92.93%  TD@12h=97.47%  TD@24h=99.20%
    flip=0.2  RW=91.20%  TD@6h=89.93%  TD@12h=93.47%  TD@24h=93.80%
    flip=0.4  RW=80.87%  TD@6h=86.40%  TD@12h=87.40%  TD@24h=86.60%
    flip=0.6  RW=73.67%  TD@6h=85.00%  TD@12h=84.93%  TD@24h=81.47%
    flip=0.8  RW=63.13%  TD@6h=81.80%  TD@12h=79.47%  TD@24h=74.27%
- Robustness claim supported: Time-Decayed beats Reputation-Weighted at
  ALL three half-lives once flip_probability >= 0.4, so the core RQ3
  finding is not an artifact of the 12h choice.
- Honest caveat to state in the thesis: the exact crossover point does
  depend on the half-life. At flip=0.2, TD@6h (89.93%) slightly
  underperforms RW (91.20%) while TD@12h and TD@24h both beat it. The
  direction of the effect is stable; the threshold is not.
- Secondary finding worth a sentence in Discussion: the optimal half-life
  shifts with the rate of world change. Long half-life (24h) is best at
  low staleness, short half-life (6h) is best at high staleness. This is
  intuitive (forget faster when reality changes faster) and suggests
  adaptive decay as future work.
- Note: uses BASE_SEED=3000, distinct from the RQ3 sweep (2000), so RW
  values differ slightly from the main staleness sweep by design.
