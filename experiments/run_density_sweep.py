"""
Phase 3, RQ1: Accuracy vs. Report Density sweep.

Report density is the third independent variable named in the thesis
proposal, Section 6: "number of reports available per ATM at query
time." It is swept here via report_probability (the chance that any
given reporter files a report about any given ATM), with the expected
reports per ATM reported alongside it, since that is the quantity the
proposal actually names and the more interpretable of the two.

    expected reports per ATM = NUM_REPORTERS * report_probability

Design notes (see dev_log.md for full justification):
- adversarial_fraction is held at 0.3 rather than 0.0. The proposal
  (Section 6) states that a comparison in which every method performs
  equally well indicates the scenarios were not discriminating enough.
  At zero adversaries all three algorithms converge to near-identical
  accuracy at any density, which would make the sweep uninformative.
  A moderate adversarial fraction keeps the comparison meaningful
  while leaving density as the variable actually being swept.
- No staleness (flip_probability is left at 0, i.e. generate_flip_times
  is not called). Density and staleness are separate independent
  variables in the proposal's design table and are swept separately.
- The density values are spaced more finely at the sparse end, because
  that is where the algorithms are expected to separate: with very few
  reports per ATM there is little evidence to weight, so reputation and
  decay have less to work with. At high density all methods should
  converge, which is itself worth showing.
- IMPORTANT floor effect: at very low density most ATMs receive zero
  reports, and the shared tie-break rule returns True (stocked) in that
  case. Since initial_stocked_probability is 0.7, always answering
  "stocked" scores about 70% by construction. The zero_report_fraction
  column is recorded so this floor is visible in the data rather than
  being mistaken for algorithm performance.

Output: results/density_sweep.csv (raw, per seed) and
results/density_sweep_summary.csv (mean, std, 95% CI).

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_density_sweep.py
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
ADVERSARIAL_FRACTION = 0.3  # moderate: keeps the comparison discriminating
REPORT_PROBABILITIES = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
NUM_SEEDS = 30
BASE_SEED = 4000  # distinct from the other sweeps' seed ranges

OUTPUT_PATH = "results/density_sweep.csv"
SUMMARY_OUTPUT_PATH = "results/density_sweep_summary.csv"


def run_single_trial(report_probability: float, seed: int) -> dict:
    """
    Run one (report_probability, seed) trial and return accuracy for all
    three algorithms, the actual reports generated per ATM, and the
    fraction of ATMs that received no reports at all (the floor-effect
    diagnostic described in the module docstring).
    """
    atms = generate_atms(NUM_ATMS, seed=seed)
    reporters = generate_reporters(
        NUM_REPORTERS, seed=seed, adversarial_fraction=ADVERSARIAL_FRACTION
    )
    reports = generate_reports(
        atms, reporters, seed=seed,
        report_probability=report_probability, time_window=TIME_WINDOW,
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

    atms_with_reports = {r.atm_id for r in reports}
    zero_report_fraction = sum(
        1 for atm in atms if atm.atm_id not in atms_with_reports
    ) / len(atms)

    return {
        "accuracies": {
            "majority_vote": mv_accuracy,
            "reputation_weighted": rw_accuracy,
            "time_decayed": td_accuracy,
        },
        "reports_per_atm": len(reports) / NUM_ATMS,
        "zero_report_fraction": zero_report_fraction,
    }


def run_sweep():
    rows = []
    summary = {}

    for report_probability in REPORT_PROBABILITIES:
        accuracies = {"majority_vote": [], "reputation_weighted": [], "time_decayed": []}
        reports_per_atm_samples = []
        zero_report_samples = []

        for i in range(NUM_SEEDS):
            seed = BASE_SEED + i
            result = run_single_trial(report_probability, seed)
            reports_per_atm_samples.append(result["reports_per_atm"])
            zero_report_samples.append(result["zero_report_fraction"])

            for algo_name, accuracy in result["accuracies"].items():
                accuracies[algo_name].append(accuracy)
                rows.append({
                    "report_probability": report_probability,
                    "seed": seed,
                    "algorithm": algo_name,
                    "accuracy": accuracy,
                    "reports_per_atm": result["reports_per_atm"],
                    "zero_report_fraction": result["zero_report_fraction"],
                })

        mean_reports_per_atm = sum(reports_per_atm_samples) / len(reports_per_atm_samples)
        mean_zero_report_fraction = sum(zero_report_samples) / len(zero_report_samples)

        summary[report_probability] = {
            "reports_per_atm": mean_reports_per_atm,
            "zero_report_fraction": mean_zero_report_fraction,
            "stats": {
                algo_name: summarize(values)
                for algo_name, values in accuracies.items()
            },
        }

        stats = summary[report_probability]["stats"]
        print(
            f"report_probability={report_probability:.2f} "
            f"(~{mean_reports_per_atm:.1f} reports/ATM, "
            f"{mean_zero_report_fraction:.0%} ATMs with no reports)  "
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
                "report_probability", "seed", "algorithm", "accuracy",
                "reports_per_atm", "zero_report_fraction",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []
    for report_probability, entry in summary.items():
        for algo_name, stats in entry["stats"].items():
            summary_rows.append({
                "report_probability": report_probability,
                "reports_per_atm": entry["reports_per_atm"],
                "zero_report_fraction": entry["zero_report_fraction"],
                "algorithm": algo_name,
                "mean_accuracy": stats["mean"],
                "std_accuracy": stats["std"],
                "ci95_halfwidth": stats["ci95_halfwidth"],
                "n": stats["n"],
            })

    with open(SUMMARY_OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "report_probability", "reports_per_atm", "zero_report_fraction",
                "algorithm", "mean_accuracy", "std_accuracy", "ci95_halfwidth", "n",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Wrote {len(summary_rows)} summary rows to {SUMMARY_OUTPUT_PATH}")
    return summary


if __name__ == "__main__":
    run_sweep()
