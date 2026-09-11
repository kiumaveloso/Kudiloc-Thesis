"""
Sensitivity of the results to the stocked base rate.

All other experiments use initial_stocked_probability = 0.7. Because
every algorithm's tie-break rule returns stocked, that base rate sets
the accuracy floor when an ATM receives no reports, and could in
principle flatter the methods. This script repeats a low-density and a
mid-density configuration at three base rates, reporting accuracy and
balanced accuracy so the effect of the prior can be separated from the
effect of the aggregation logic.

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_base_rate_sensitivity.py
"""

import csv

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.scoring.metrics import compute_metrics
from src.simulation.ground_truth import generate_atms
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
ADVERSARIAL_FRACTION = 0.3
BASE_RATES = [0.5, 0.6, 0.7]
REPORT_PROBABILITIES = [0.02, 0.30]
NUM_SEEDS = 30
BASE_SEED = 7000

OUTPUT_PATH = "results/base_rate_sensitivity.csv"


def run_single_trial(base_rate, report_probability, seed):
    atms = generate_atms(
        NUM_ATMS, seed=seed, initial_stocked_probability=base_rate
    )
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=ADVERSARIAL_FRACTION
    )
    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=report_probability, time_window=TIME_WINDOW,
    )

    query_time = TIME_WINDOW

    mv = compute_metrics(atms, reports, MajorityVote(), query_time)

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, TIME_WINDOW)
    rw = compute_metrics(
        atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id
    )
    td = compute_metrics(
        atms, reports, TimeDecayedTrustScoring(), query_time, reporters_by_id
    )

    stocked = sum(1 for a in atms if a.true_state) / len(atms)

    return {"majority_vote": mv, "reputation_weighted": rw, "time_decayed": td}, stocked


def main():
    rows = []

    for report_probability in REPORT_PROBABILITIES:
        for base_rate in BASE_RATES:
            collected = {
                "majority_vote": {"accuracy": [], "balanced_accuracy": []},
                "reputation_weighted": {"accuracy": [], "balanced_accuracy": []},
                "time_decayed": {"accuracy": [], "balanced_accuracy": []},
            }
            realised = []

            for i in range(NUM_SEEDS):
                result, stocked = run_single_trial(
                    base_rate, report_probability, BASE_SEED + i
                )
                realised.append(stocked)
                for algo_name, metrics in result.items():
                    collected[algo_name]["accuracy"].append(metrics["accuracy"])
                    collected[algo_name]["balanced_accuracy"].append(
                        metrics["balanced_accuracy"]
                    )

            mean_stocked = sum(realised) / len(realised)
            print(
                f"\nreport_probability={report_probability:.2f}  "
                f"base_rate={base_rate:.1f}  "
                f"(realised {mean_stocked:.1%} stocked)"
            )

            for algo_name, per_metric in collected.items():
                acc = sum(per_metric["accuracy"]) / NUM_SEEDS
                bal = sum(per_metric["balanced_accuracy"]) / NUM_SEEDS
                print(f"  {algo_name:22s} acc={acc:.2%}  bal={bal:.2%}")
                rows.append({
                    "report_probability": report_probability,
                    "base_rate": base_rate,
                    "realised_stocked_fraction": mean_stocked,
                    "algorithm": algo_name,
                    "mean_accuracy": acc,
                    "mean_balanced_accuracy": bal,
                    "n_seeds": NUM_SEEDS,
                })

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "report_probability", "base_rate", "realised_stocked_fraction",
                "algorithm", "mean_accuracy", "mean_balanced_accuracy", "n_seeds",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
