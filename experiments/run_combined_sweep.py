"""
Combined adversarial and staleness sweep.

Every other sweep varies one condition while holding the others fixed,
which isolates each effect but leaves the interaction unmeasured. A
deployed system experiences unreliable reporters and ageing reports at
the same time. This script crosses adversarial_fraction with
flip_probability and scores all three algorithms at each combination.

The corners reproduce conditions already covered elsewhere: (0.0, 0.0)
is the shared baseline, (0.4, 0.0) and (0.8, 0.0) sit on the RQ2 sweep,
and (0.0, 0.4) and (0.0, 0.8) sit on the RQ3 sweep. These will not match
those sweeps' figures exactly, because this experiment uses its own seed
range (see Section 4.4.1).

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_combined_sweep.py
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
ADVERSARIAL_FRACTIONS = [0.0, 0.4, 0.8]
FLIP_PROBABILITIES = [0.0, 0.4, 0.8]
NUM_SEEDS = 30
BASE_SEED = 5000  # distinct from all other sweeps

OUTPUT_PATH = "results/combined_sweep.csv"
SUMMARY_OUTPUT_PATH = "results/combined_sweep_summary.csv"


def run_single_trial(adversarial_fraction, flip_probability, seed):
    """
    One trial at a given (adversarial_fraction, flip_probability, seed).
    Call order matches the existing sweep runners: flip times are
    assigned before reports are generated, and Majority Vote is scored
    before run_periodic_reveals mutates reporter reputations.
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=adversarial_fraction
    )

    generate_flip_times(
        atms, seed=seed + 1,
        flip_probability=flip_probability, time_window=TIME_WINDOW,
    )

    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=REPORT_PROBABILITY, time_window=TIME_WINDOW,
    )

    query_time = TIME_WINDOW

    mv = compute_accuracy(atms, reports, MajorityVote(), query_time)

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, TIME_WINDOW)
    rw = compute_accuracy(
        atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id
    )
    td = compute_accuracy(
        atms, reports, TimeDecayedTrustScoring(), query_time, reporters_by_id
    )

    return {"majority_vote": mv, "reputation_weighted": rw, "time_decayed": td}


def run_sweep():
    rows = []
    summary_rows = []

    for adversarial_fraction in ADVERSARIAL_FRACTIONS:
        for flip_probability in FLIP_PROBABILITIES:
            accuracies = {
                "majority_vote": [],
                "reputation_weighted": [],
                "time_decayed": [],
            }

            for i in range(NUM_SEEDS):
                seed = BASE_SEED + i
                result = run_single_trial(
                    adversarial_fraction, flip_probability, seed
                )
                for algo_name, accuracy in result.items():
                    accuracies[algo_name].append(accuracy)
                    rows.append({
                        "adversarial_fraction": adversarial_fraction,
                        "flip_probability": flip_probability,
                        "seed": seed,
                        "algorithm": algo_name,
                        "accuracy": accuracy,
                    })

            stats = {
                algo_name: summarize(values)
                for algo_name, values in accuracies.items()
            }

            for algo_name, s in stats.items():
                summary_rows.append({
                    "adversarial_fraction": adversarial_fraction,
                    "flip_probability": flip_probability,
                    "algorithm": algo_name,
                    "mean_accuracy": s["mean"],
                    "std_accuracy": s["std"],
                    "ci95_halfwidth": s["ci95_halfwidth"],
                    "n": s["n"],
                })

            print(
                f"adv={adversarial_fraction:.1f} flip={flip_probability:.1f}  "
                f"MV={stats['majority_vote']['mean']:.2%}"
                f"±{stats['majority_vote']['ci95_halfwidth']:.2%}  "
                f"RW={stats['reputation_weighted']['mean']:.2%}"
                f"±{stats['reputation_weighted']['ci95_halfwidth']:.2%}  "
                f"TD={stats['time_decayed']['mean']:.2%}"
                f"±{stats['time_decayed']['ci95_halfwidth']:.2%}"
            )

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "adversarial_fraction", "flip_probability",
                "seed", "algorithm", "accuracy",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(SUMMARY_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "adversarial_fraction", "flip_probability", "algorithm",
                "mean_accuracy", "std_accuracy", "ci95_halfwidth", "n",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Wrote {len(summary_rows)} summary rows to {SUMMARY_OUTPUT_PATH}")


if __name__ == "__main__":
    run_sweep()
