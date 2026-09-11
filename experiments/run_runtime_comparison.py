"""
Runtime comparison of the three aggregation algorithms.

The motivation for this thesis emphasises lightweight algorithms
suitable for a resource-constrained, real-time mobile application, but
the sweeps measure only accuracy. This script measures the wall-clock
cost of a single aggregate() call at several report densities, so the
accuracy results can be read alongside their computational cost.

Each measurement times a fixed number of repeated aggregate() calls on
the same ATM's reports and divides by the repeat count, which keeps the
per-call figure above timer resolution. The scenario is built once per
seed and reused across all three algorithms, so any difference is
attributable to the aggregation logic alone.

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_runtime_comparison.py
"""

import csv
import statistics
import time

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.simulation.ground_truth import generate_atms
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
ADVERSARIAL_FRACTION = 0.3
REPORT_PROBABILITIES = [0.02, 0.1, 0.3, 0.5]
NUM_SEEDS = 10
REPEATS = 2000
BASE_SEED = 6000

OUTPUT_PATH = "results/runtime_comparison.csv"


def time_algorithm(algorithm, reports, query_time, reporters_by_id):
    """Mean microseconds per aggregate() call over REPEATS calls."""
    start = time.perf_counter()
    for _ in range(REPEATS):
        algorithm.aggregate(reports, query_time, reporters_by_id)
    elapsed = time.perf_counter() - start
    return (elapsed / REPEATS) * 1_000_000


def main():
    rows = []

    for report_probability in REPORT_PROBABILITIES:
        timings = {"majority_vote": [], "reputation_weighted": [], "time_decayed": []}
        report_counts = []

        for i in range(NUM_SEEDS):
            seed = BASE_SEED + i

            atms = generate_atms(NUM_ATMS, seed=seed)
            reporters = generate_reporters(
                NUM_REPORTERS, seed=seed,
                adversarial_fraction=ADVERSARIAL_FRACTION,
            )
            reports = generate_reports(
                atms, reporters, seed=seed,
                report_probability=report_probability,
                time_window=TIME_WINDOW,
            )
            reporters_by_id = run_periodic_reveals(
                reports, atms, reporters, TIME_WINDOW
            )

            # Time a single ATM's aggregation, which is the operation the
            # production system performs on each incoming report.
            target = max(
                atms,
                key=lambda a: sum(1 for r in reports if r.atm_id == a.atm_id),
            )
            atm_reports = [r for r in reports if r.atm_id == target.atm_id]
            report_counts.append(len(atm_reports))

            timings["majority_vote"].append(
                time_algorithm(MajorityVote(), atm_reports, TIME_WINDOW, reporters_by_id)
            )
            timings["reputation_weighted"].append(
                time_algorithm(
                    ReputationWeightedAggregation(), atm_reports,
                    TIME_WINDOW, reporters_by_id,
                )
            )
            timings["time_decayed"].append(
                time_algorithm(
                    TimeDecayedTrustScoring(), atm_reports,
                    TIME_WINDOW, reporters_by_id,
                )
            )

        mean_reports = statistics.mean(report_counts)
        print(f"\nreport_probability={report_probability:.2f} "
              f"({mean_reports:.1f} reports on the busiest ATM)")

        baseline = statistics.mean(timings["majority_vote"])
        for algo_name, values in timings.items():
            mean_us = statistics.mean(values)
            print(
                f"  {algo_name:22s} {mean_us:7.2f} us/call  "
                f"({mean_us / baseline:.2f}x Majority Vote)"
            )
            rows.append({
                "report_probability": report_probability,
                "reports_on_busiest_atm": mean_reports,
                "algorithm": algo_name,
                "mean_us_per_call": mean_us,
                "relative_to_majority_vote": mean_us / baseline,
                "n_seeds": NUM_SEEDS,
                "repeats_per_measurement": REPEATS,
            })

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "report_probability", "reports_on_busiest_atm", "algorithm",
                "mean_us_per_call", "relative_to_majority_vote",
                "n_seeds", "repeats_per_measurement",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
