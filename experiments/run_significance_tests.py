"""
Phase 3/4: Paired significance tests on the sweep results.

The thesis proposal (Section 6) commits to reporting results "as means
with variability, with significance assessed using an appropriate paired
test." This script provides that paired test.

Why a PAIRED test is the right choice: for each seed, all three
algorithms are evaluated on the *identical* generated scenario (same
ATMs, same reporters, same reports) — only the aggregation logic
differs. The per-seed accuracies are therefore naturally paired, and a
paired test compares the three algorithms on a like-for-like basis
rather than as independent samples. This removes seed-to-seed scenario
variability from the comparison and is more powerful than an unpaired
test on the same data.

Which test: the Wilcoxon signed-rank test (a paired, non-parametric
test). It does not assume the per-seed differences are normally
distributed, which is safer for bounded accuracy values (proportions in
[0, 1] whose differences can be skewed, especially near the ceiling or
floor) than a paired t-test. Where the two algorithms produce identical
accuracy on every seed (zero differences everywhere — common at the
easy end of a sweep), the Wilcoxon test is undefined; this is detected
and reported as "n/a (no differences)" rather than crashing.

For each swept parameter value, this script runs three pairwise
comparisons:
    reputation_weighted vs majority_vote
    time_decayed        vs majority_vote
    time_decayed        vs reputation_weighted
reporting the mean per-seed difference and the Wilcoxon p-value for
each. Reads the RAW per-seed CSVs (not the summary CSVs, which have
already averaged the per-seed detail away).

Output: results/significance_tests.csv

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_significance_tests.py
"""

import csv
from collections import defaultdict

from scipy.stats import wilcoxon

# Each sweep: (raw CSV path, name of the swept-parameter column).
SWEEPS = [
    ("results/adversarial_sweep.csv", "adversarial_fraction"),
    ("results/staleness_sweep.csv", "flip_probability"),
    ("results/density_sweep.csv", "report_probability"),
]

# The pairwise comparisons to run, as (algorithm_a, algorithm_b). The
# reported difference is (a - b), so a positive mean difference means
# algorithm_a scored higher on average.
COMPARISONS = [
    ("reputation_weighted", "majority_vote"),
    ("time_decayed", "majority_vote"),
    ("time_decayed", "reputation_weighted"),
]

OUTPUT_PATH = "results/significance_tests.csv"


def load_raw(path: str, x_column: str) -> dict:
    """
    Load a raw per-seed CSV into:
        { x_value: { algorithm: { seed: accuracy } } }

    Keeping accuracies keyed by seed (rather than in a flat list) is what
    lets us pair correctly: for a given x value and pair of algorithms,
    we line up the two accuracies that share the same seed.
    """
    data = defaultdict(lambda: defaultdict(dict))
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            x_value = float(row[x_column])
            algorithm = row["algorithm"]
            seed = int(row["seed"])
            accuracy = float(row["accuracy"])
            data[x_value][algorithm][seed] = accuracy
    return data


def paired_differences(acc_a: dict, acc_b: dict) -> list:
    """
    Given two {seed: accuracy} dicts, return the list of (a - b)
    differences over the seeds they share, ordered by seed for
    determinism. Only seeds present in BOTH are used (they should be
    identical sets in practice; the intersection is defensive).
    """
    shared_seeds = sorted(set(acc_a) & set(acc_b))
    return [acc_a[s] - acc_b[s] for s in shared_seeds]


def run_tests():
    output_rows = []

    for path, x_column in SWEEPS:
        try:
            data = load_raw(path, x_column)
        except FileNotFoundError:
            print(f"SKIP: {path} not found (run the corresponding sweep first)")
            continue

        print(f"\n=== {path} (paired Wilcoxon signed-rank) ===")

        for x_value in sorted(data):
            for algo_a, algo_b in COMPARISONS:
                acc_a = data[x_value].get(algo_a, {})
                acc_b = data[x_value].get(algo_b, {})
                diffs = paired_differences(acc_a, acc_b)

                n = len(diffs)
                mean_diff = sum(diffs) / n if n else 0.0

                # Wilcoxon is undefined when every difference is zero
                # (the two algorithms tied on every seed). Report that
                # explicitly instead of letting scipy raise.
                if n == 0 or all(d == 0 for d in diffs):
                    p_value = None
                    significant = ""
                else:
                    # zero_method='wilcox' (the default) drops zero
                    # differences; this is the standard handling.
                    _, p_value = wilcoxon(diffs)
                    significant = "yes" if p_value < 0.05 else "no"

                output_rows.append({
                    "sweep": path,
                    "x_column": x_column,
                    "x_value": x_value,
                    "comparison": f"{algo_a} vs {algo_b}",
                    "mean_diff": mean_diff,
                    "n": n,
                    "p_value": p_value if p_value is not None else "",
                    "significant_p<0.05": significant,
                })

                p_display = f"p={p_value:.2e}" if p_value is not None else "p=n/a (no differences)"
                sig_mark = " *" if significant == "yes" else ""
                print(
                    f"{x_column}={x_value:<5} {algo_a} vs {algo_b}: "
                    f"mean_diff={mean_diff:+.2%}  {p_display}{sig_mark}"
                )

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sweep", "x_column", "x_value", "comparison",
                "mean_diff", "n", "p_value", "significant_p<0.05",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nWrote {len(output_rows)} test results to {OUTPUT_PATH}")
    return output_rows


if __name__ == "__main__":
    run_tests()
