"""
Phase 3, RQ3: Accuracy vs. Staleness sweep.

Sweeps flip_probability (the fraction of ATMs whose state changes
partway through the report window, via generate_flip_times) across a
range, running all three aggregation algorithms at each point, averaged
over many seeds, and writes raw per-run results to
results/staleness_sweep.csv.

Design notes (see dev_log.md for full justification):
- adversarial_fraction is fixed at 0.0 throughout this sweep. This
  isolates the staleness effect specifically — mixing in adversarial
  reporters would confound the two RQs. Adversarial resilience is
  already covered by the separate adversarial_sweep (RQ2).
- flip_probability is swept rather than half-life or query delay,
  because (see dev_log.md) query delay alone doesn't change algorithm
  ranking (a uniform time shift multiplies every report's decay by the
  same constant, which cancels out in a relative-weight comparison).
  The genuine lever is how MANY ATMs actually experience a state change
  during the window, and thus how much of the report set is
  potentially stale.
- Uses generate_flip_times() (not the older, timestamp-blind
  maybe_flip_states()) so each report is checked against the ATM's
  actual state at its own timestamp — this is what makes staleness a
  genuine per-report property. See dev_log.md, Day 3, for the bug this
  fixes.
- Majority Vote is included as a baseline for context, even though it
  has no notion of report age, to show the "floor" both trust-aware
  algorithms are being compared against.
"""

import csv

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.scoring.accuracy import compute_accuracy
from src.simulation.ground_truth import generate_atms, generate_flip_times
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals, summarize

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
REPORT_PROBABILITY = 0.3
ADVERSARIAL_FRACTION = 0.0  # fixed at 0 to isolate staleness from adversarial noise
FLIP_PROBABILITIES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
NUM_SEEDS = 30
BASE_SEED = 2000  # offset so these seeds don't collide with other sweeps

OUTPUT_PATH = "results/staleness_sweep.csv"
SUMMARY_OUTPUT_PATH = "results/staleness_sweep_summary.csv"


def run_single_trial(flip_probability: float, seed: int) -> dict:
    """
    Run one (flip_probability, seed) trial and return accuracy for all
    three algorithms.
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=ADVERSARIAL_FRACTION
    )

    # Assign flip_times BEFORE generating reports (order matters — see
    # dev_log.md Day 3 for the bug caused by getting this backwards).
    generate_flip_times(atms, seed=seed + 1, flip_probability=flip_probability, time_window=TIME_WINDOW)

    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=REPORT_PROBABILITY, time_window=TIME_WINDOW,
    )

    query_time = TIME_WINDOW

    mv_accuracy = compute_accuracy(atms, reports, MajorityVote(), query_time)

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, TIME_WINDOW)
    rw_accuracy = compute_accuracy(
        atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id
    )
    td_accuracy = compute_accuracy(
        atms, reports, TimeDecayedTrustScoring(), query_time, reporters_by_id
    )

    return {
        "majority_vote": mv_accuracy,
        "reputation_weighted": rw_accuracy,
        "time_decayed": td_accuracy,
    }


def run_sweep():
    rows = []
    summary = {}

    for flip_probability in FLIP_PROBABILITIES:
        accuracies = {"majority_vote": [], "reputation_weighted": [], "time_decayed": []}

        for i in range(NUM_SEEDS):
            seed = BASE_SEED + i
            result = run_single_trial(flip_probability, seed)
            for algo_name, accuracy in result.items():
                accuracies[algo_name].append(accuracy)
                rows.append({
                    "flip_probability": flip_probability,
                    "seed": seed,
                    "algorithm": algo_name,
                    "accuracy": accuracy,
                })

        summary[flip_probability] = {
            algo_name: summarize(values)
            for algo_name, values in accuracies.items()
        }

        mv_stats = summary[flip_probability]["majority_vote"]
        rw_stats = summary[flip_probability]["reputation_weighted"]
        td_stats = summary[flip_probability]["time_decayed"]

        print(
            f"flip_probability={flip_probability:.1f}  "
            f"MV={mv_stats['mean']:.2%}±{mv_stats['ci95_halfwidth']:.2%}  "
            f"RW={rw_stats['mean']:.2%}±{rw_stats['ci95_halfwidth']:.2%}  "
            f"TD={td_stats['mean']:.2%}±{td_stats['ci95_halfwidth']:.2%}"
        )

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["flip_probability", "seed", "algorithm", "accuracy"])
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []
    for flip_probability, algo_stats in summary.items():
        for algo_name, stats in algo_stats.items():
            summary_rows.append({
                "flip_probability": flip_probability,
                "algorithm": algo_name,
                "mean_accuracy": stats["mean"],
                "std_accuracy": stats["std"],
                "ci95_halfwidth": stats["ci95_halfwidth"],
                "n": stats["n"],
            })

    with open(SUMMARY_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["flip_probability", "algorithm", "mean_accuracy", "std_accuracy", "ci95_halfwidth", "n"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Wrote {len(summary_rows)} summary rows to {SUMMARY_OUTPUT_PATH}")
    return summary


if __name__ == "__main__":
    run_sweep()
