"""
Comparison of the simulated and production reputation update rules.

Section 3.5 notes that the simulation uses a multiplicative reward and
penalty while the deployed system uses an additive one on a different
scale. This script runs both weighting rules over the RQ2 adversarial
sweep under identical scenarios and seeds, so that any difference is
attributable to the update rule alone.

Both reputation values are maintained in parallel on the same Reporter
objects: the multiplicative one by the existing update_reputations(),
the additive one by update_production_reputations() below, which
mirrors the production behaviour of +2 on agreement with the recent
majority and -3 on disagreement, clamped to [0, 100].

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_production_rule.py
"""

import csv

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.production_weighted import ProductionWeightedAggregation
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.scoring.accuracy import compute_accuracy
from src.simulation.ground_truth import generate_atms
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters

from experiments.common import run_periodic_reveals

NUM_ATMS = 50
NUM_REPORTERS = 30
TIME_WINDOW = 60.0
REPORT_PROBABILITY = 0.3
ADVERSARIAL_FRACTIONS = [0.0, 0.2, 0.4, 0.6, 0.8]
NUM_SEEDS = 30
BASE_SEED = 8000

START_SCORE = 50.0
REWARD = 2.0
PENALTY = 3.0
MIN_SCORE = 0.0
MAX_SCORE = 100.0
REVEAL_INTERVAL = 10.0

OUTPUT_PATH = "results/production_rule.csv"


def update_production_reputations(reports, atms, reporters):
    """
    Additive update mirroring the production rule, applied on the same
    periodic reveal schedule as the multiplicative one so the two are
    exposed to identical information.
    """
    atms_by_id = {a.atm_id: a for a in atms}
    reporters_by_id = {r.reporter_id: r for r in reporters}

    for reporter in reporters:
        reporter.production_reputation = START_SCORE

    interval_end = REVEAL_INTERVAL
    bucket = []

    def flush(batch):
        for report in batch:
            reporter = reporters_by_id[report.reporter_id]
            atm = atms_by_id[report.atm_id]
            correct = report.claimed_state == atm.true_state
            delta = REWARD if correct else -PENALTY
            reporter.production_reputation = max(
                MIN_SCORE,
                min(MAX_SCORE, reporter.production_reputation + delta),
            )

    for report in sorted(reports, key=lambda r: r.timestamp):
        if report.timestamp > interval_end:
            flush(bucket)
            bucket = []
            interval_end += REVEAL_INTERVAL
        bucket.append(report)

    flush(bucket)
    return reporters_by_id


def run_single_trial(adversarial_fraction, seed):
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=adversarial_fraction
    )
    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=REPORT_PROBABILITY, time_window=TIME_WINDOW,
    )

    query_time = TIME_WINDOW

    mv = compute_accuracy(atms, reports, MajorityVote(), query_time)

    update_production_reputations(reports, atms, reporters)
    pw = compute_accuracy(
        atms, reports, ProductionWeightedAggregation(), query_time,
        {r.reporter_id: r for r in reporters},
    )

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, TIME_WINDOW)
    rw = compute_accuracy(
        atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id
    )

    return {"majority_vote": mv, "production_weighted": pw, "reputation_weighted": rw}


def main():
    rows = []

    for adversarial_fraction in ADVERSARIAL_FRACTIONS:
        totals = {"majority_vote": [], "production_weighted": [], "reputation_weighted": []}

        for i in range(NUM_SEEDS):
            result = run_single_trial(adversarial_fraction, BASE_SEED + i)
            for name, value in result.items():
                totals[name].append(value)

        means = {k: sum(v) / len(v) for k, v in totals.items()}
        print(
            f"adv={adversarial_fraction:.1f}  "
            f"MV={means['majority_vote']:.2%}  "
            f"Production={means['production_weighted']:.2%}  "
            f"Multiplicative={means['reputation_weighted']:.2%}"
        )

        for name, mean in means.items():
            rows.append({
                "adversarial_fraction": adversarial_fraction,
                "algorithm": name,
                "mean_accuracy": mean,
                "n_seeds": NUM_SEEDS,
            })

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["adversarial_fraction", "algorithm", "mean_accuracy", "n_seeds"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
