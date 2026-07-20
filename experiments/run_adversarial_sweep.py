"""
Phase 3, RQ2: Accuracy vs. Adversarial Fraction sweep.

Sweeps adversarial_fraction across a range, running all three
aggregation algorithms (Majority Vote, Reputation-Weighted,
Time-Decayed) at each point, averaged over many seeds, and writes the
raw per-run results to results/adversarial_sweep.csv for later
plotting/analysis in the thesis Results chapter.

Design notes (see dev_log.md for full justification):
- Reputations are matured via periodic ground-truth reveals
  (experiments/common.py: run_periodic_reveals) before being used by
  the reputation-aware algorithms, consistent with the Phase 2 sanity
  checks.
- No ATM state changes during this sweep (flip_probability=0 throughout)
  — this experiment isolates the effect of adversarial reporters, not
  staleness. The staleness dimension is a separate sweep (RQ3).
- Multiple seeds per adversarial_fraction value are essential: a single
  seed can produce a misleading result (see dev_log.md Day 3 entry on
  the staleness bug, where single-seed noise initially masked/inflated
  an effect). This script defaults to 30 seeds per point.
"""

import csv

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.scoring.accuracy import compute_accuracy
from src.simulation.ground_truth import generate_atms
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals, summarize

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
REPORT_PROBABILITY = 0.3
ADVERSARIAL_FRACTIONS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
NUM_SEEDS = 30
BASE_SEED = 1000  # offset so these seeds don't collide with earlier sanity-check seeds

OUTPUT_PATH = "results/adversarial_sweep.csv"
SUMMARY_OUTPUT_PATH = "results/adversarial_sweep_summary.csv"


def run_single_trial(adversarial_fraction: float, seed: int) -> dict:
    """
    Run one (adversarial_fraction, seed) trial and return accuracy for
    all three algorithms.
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=adversarial_fraction
    )
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

    for adversarial_fraction in ADVERSARIAL_FRACTIONS:
        accuracies = {"majority_vote": [], "reputation_weighted": [], "time_decayed": []}

        for i in range(NUM_SEEDS):
            seed = BASE_SEED + i
            result = run_single_trial(adversarial_fraction, seed)
            for algo_name, accuracy in result.items():
                accuracies[algo_name].append(accuracy)
                rows.append({
                    "adversarial_fraction": adversarial_fraction,
                    "seed": seed,
                    "algorithm": algo_name,
                    "accuracy": accuracy,
                })

        summary[adversarial_fraction] = {
            algo_name: summarize(values)
            for algo_name, values in accuracies.items()
        }

        mv_stats = summary[adversarial_fraction]["majority_vote"]
        rw_stats = summary[adversarial_fraction]["reputation_weighted"]
        td_stats = summary[adversarial_fraction]["time_decayed"]

        print(
            f"adversarial_fraction={adversarial_fraction:.1f}  "
            f"MV={mv_stats['mean']:.2%}±{mv_stats['ci95_halfwidth']:.2%}  "
            f"RW={rw_stats['mean']:.2%}±{rw_stats['ci95_halfwidth']:.2%}  "
            f"TD={td_stats['mean']:.2%}±{td_stats['ci95_halfwidth']:.2%}"
        )

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["adversarial_fraction", "seed", "algorithm", "accuracy"])
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []
    for adversarial_fraction, algo_stats in summary.items():
        for algo_name, stats in algo_stats.items():
            summary_rows.append({
                "adversarial_fraction": adversarial_fraction,
                "algorithm": algo_name,
                "mean_accuracy": stats["mean"],
                "std_accuracy": stats["std"],
                "ci95_halfwidth": stats["ci95_halfwidth"],
                "n": stats["n"],
            })

    with open(SUMMARY_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["adversarial_fraction", "algorithm", "mean_accuracy", "std_accuracy", "ci95_halfwidth", "n"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Wrote {len(summary_rows)} summary rows to {SUMMARY_OUTPUT_PATH}")
    return summary


if __name__ == "__main__":
    run_sweep()
