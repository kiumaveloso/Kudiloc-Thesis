"""
Phase 3, robustness check: half-life sensitivity.

The 12-hour half-life used by TimeDecayedTrustScoring is a modeling
assumption, not an empirically derived constant (see dev_log.md and the
methodology chapter). A fair objection is that the algorithm's apparent
advantage might be an artifact of choosing a half-life that happens to
suit the simulated conditions.

This script addresses that objection directly by rerunning the RQ3
staleness sweep at three half-lives (6h, 12h, 24h) and reporting
Time-Decayed's accuracy at each, alongside Reputation-Weighted as a
fixed reference line. Reputation-Weighted has no decay parameter, so
its accuracy is identical across half-life settings by construction;
it is computed once per (flip_probability, seed) and reused, which also
serves as a built-in sanity check that the harness is not accidentally
varying something it should not.

The claim this supports, if the ranking holds across all three values,
is a robustness statement: Time-Decayed's advantage under staleness is
not contingent on one particular decay rate.

Output: results/halflife_sensitivity.csv (summary statistics only,
one row per half-life / flip_probability / algorithm combination).

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_halflife_sensitivity.py
"""

import csv
import math

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
ADVERSARIAL_FRACTION = 0.0  # isolate staleness, matching the RQ3 sweep
FLIP_PROBABILITIES = [0.0, 0.2, 0.4, 0.6, 0.8]
HALF_LIVES = [6.0, 12.0, 24.0]  # simulated hours
NUM_SEEDS = 30
BASE_SEED = 3000  # distinct from the other sweeps' seed ranges

OUTPUT_PATH = "results/halflife_sensitivity.csv"


def build_scenario(flip_probability: float, seed: int):
    """
    Construct one (flip_probability, seed) scenario and mature reporter
    reputations on it.

    Returns (atms, reports, reporters_by_id, query_time) so the same
    scenario can be scored by several algorithm configurations without
    regenerating it. Reusing the scenario across half-lives is what
    makes the comparison clean: any accuracy difference is attributable
    to the decay rate alone, not to a different random draw.
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=ADVERSARIAL_FRACTION
    )

    # flip_times must be assigned before reports are generated, so that
    # each report reflects the ATM state at its own timestamp.
    generate_flip_times(
        atms, seed=seed + 1,
        flip_probability=flip_probability, time_window=TIME_WINDOW,
    )

    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=REPORT_PROBABILITY, time_window=TIME_WINDOW,
    )

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, TIME_WINDOW)

    return atms, reports, reporters_by_id, TIME_WINDOW


def run_sensitivity():
    summary_rows = []

    for flip_probability in FLIP_PROBABILITIES:
        # Accuracy accumulators: one list per algorithm configuration.
        rw_scores = []
        td_scores = {half_life: [] for half_life in HALF_LIVES}

        for i in range(NUM_SEEDS):
            seed = BASE_SEED + i
            atms, reports, reporters_by_id, query_time = build_scenario(
                flip_probability, seed
            )

            rw_scores.append(
                compute_accuracy(
                    atms, reports, ReputationWeightedAggregation(),
                    query_time, reporters_by_id,
                )
            )

            for half_life in HALF_LIVES:
                lambda_ = math.log(2) / half_life
                td_scores[half_life].append(
                    compute_accuracy(
                        atms, reports, TimeDecayedTrustScoring(lambda_=lambda_),
                        query_time, reporters_by_id,
                    )
                )

        rw_stats = summarize(rw_scores)
        summary_rows.append({
            "flip_probability": flip_probability,
            "algorithm": "reputation_weighted",
            "half_life": "",  # not applicable: no decay parameter
            "mean_accuracy": rw_stats["mean"],
            "std_accuracy": rw_stats["std"],
            "ci95_halfwidth": rw_stats["ci95_halfwidth"],
            "n": rw_stats["n"],
        })

        line = f"flip_probability={flip_probability:.1f}  RW={rw_stats['mean']:.2%}"

        for half_life in HALF_LIVES:
            td_stats = summarize(td_scores[half_life])
            summary_rows.append({
                "flip_probability": flip_probability,
                "algorithm": "time_decayed",
                "half_life": half_life,
                "mean_accuracy": td_stats["mean"],
                "std_accuracy": td_stats["std"],
                "ci95_halfwidth": td_stats["ci95_halfwidth"],
                "n": td_stats["n"],
            })
            line += f"  TD@{half_life:.0f}h={td_stats['mean']:.2%}"

        print(line)

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "flip_probability", "algorithm", "half_life",
                "mean_accuracy", "std_accuracy", "ci95_halfwidth", "n",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(summary_rows)} summary rows to {OUTPUT_PATH}")
    return summary_rows


if __name__ == "__main__":
    run_sensitivity()
