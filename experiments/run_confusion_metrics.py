"""
Confusion-matrix-based metrics at the extreme setting of each sweep.

Reproduces the endpoint scenario of each of the three sweeps using the
same seeds and parameters as the original runners, and scores all three
algorithms with precision, recall, F1 and balanced accuracy in addition
to plain accuracy. Results are averaged over the same 30 seeds.

The accuracy column doubles as a correctness check: it should reproduce
the figures already reported in the Results chapter.

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_confusion_metrics.py
"""

import csv

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.scoring.metrics import compute_metrics
from src.simulation.ground_truth import generate_atms, generate_flip_times
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
NUM_SEEDS = 30

OUTPUT_PATH = "results/confusion_metrics.csv"

METRIC_KEYS = ["accuracy", "precision", "recall", "f1", "balanced_accuracy"]

# (label, base_seed, report_probability, adversarial_fraction, flip_probability)
SCENARIOS = [
    ("RQ1 lowest density", 4000, 0.02, 0.3, None),
    ("RQ2 highest adversarial", 1000, 0.3, 0.8, None),
    ("RQ3 highest staleness", 2000, 0.3, 0.0, 0.8),
]

# Published Chapter 5 figures, for the correctness check.
EXPECTED = {
    ("RQ1 lowest density", "majority_vote"): 0.6573,
    ("RQ1 lowest density", "reputation_weighted"): 0.6707,
    ("RQ1 lowest density", "time_decayed"): 0.6547,
    ("RQ2 highest adversarial", "majority_vote"): 0.0120,
    ("RQ2 highest adversarial", "reputation_weighted"): 0.7327,
    ("RQ2 highest adversarial", "time_decayed"): 0.5967,
    ("RQ3 highest staleness", "majority_vote"): 0.5893,
    ("RQ3 highest staleness", "reputation_weighted"): 0.6420,
    ("RQ3 highest staleness", "time_decayed"): 0.8027,
}


def run_single_trial(seed, report_probability, adversarial_fraction, flip_probability):
    """
    Build one scenario and score all three algorithms. The call order
    matches the original sweep runners exactly: Majority Vote is scored
    before run_periodic_reveals, which mutates reporter reputations in
    place, and flip times are assigned before reports are generated.
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=adversarial_fraction
    )

    if flip_probability is not None:
        generate_flip_times(
            atms, seed=seed + 1,
            flip_probability=flip_probability, time_window=TIME_WINDOW,
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

    return {"majority_vote": mv, "reputation_weighted": rw, "time_decayed": td}


def main():
    rows = []

    for label, base_seed, report_prob, adv_frac, flip_prob in SCENARIOS:
        collected = {
            "majority_vote": {k: [] for k in METRIC_KEYS},
            "reputation_weighted": {k: [] for k in METRIC_KEYS},
            "time_decayed": {k: [] for k in METRIC_KEYS},
        }

        for i in range(NUM_SEEDS):
            result = run_single_trial(
                base_seed + i, report_prob, adv_frac, flip_prob
            )
            for algo_name, metrics in result.items():
                for key in METRIC_KEYS:
                    collected[algo_name][key].append(metrics[key])

        print(f"\n{label}")
        for algo_name, per_metric in collected.items():
            means = {
                k: sum(v) / len(v) for k, v in per_metric.items()
            }
            expected = EXPECTED.get((label, algo_name))
            delta = ""
            if expected is not None:
                diff = abs(means["accuracy"] - expected)
                flag = "OK" if diff < 0.005 else "MISMATCH"
                delta = f"  [published {expected:.2%} -> {flag}]"

            print(
                f"  {algo_name:22s} "
                f"acc={means['accuracy']:.2%}  "
                f"prec={means['precision']:.2%}  "
                f"rec={means['recall']:.2%}  "
                f"f1={means['f1']:.2%}  "
                f"bal={means['balanced_accuracy']:.2%}"
                f"{delta}"
            )

            row = {"scenario": label, "algorithm": algo_name, "n_seeds": NUM_SEEDS}
            row.update({k: means[k] for k in METRIC_KEYS})
            rows.append(row)

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["scenario", "algorithm", "n_seeds"] + METRIC_KEYS
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
