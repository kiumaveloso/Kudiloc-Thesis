"""
Effect sizes and multiple-comparison correction for the paired tests.

Reads the per-seed CSVs already produced by the three sweeps and, for
every pairwise algorithm comparison at every parameter point, reports:

  - the paired Wilcoxon signed-rank p-value
  - the matched-pairs rank-biserial correlation as an effect size
  - a Holm-Bonferroni adjusted p-value across the whole family of tests

Rank-biserial is the effect size appropriate to the Wilcoxon signed-rank
test. It is computed as (W+ - W-) / (W+ + W-), where W+ and W- are the
sums of ranks of positive and negative differences, and ranges from -1
to +1. Values near zero indicate that the two algorithms win against
each other about equally often across seeds, regardless of how small
the p-value is.

Run from the repo root:
    PYTHONPATH=. python3 experiments/run_effect_sizes.py
"""

import csv
from collections import defaultdict

from scipy.stats import rankdata, wilcoxon

SWEEPS = [
    ("density", "results/density_sweep.csv", "report_probability"),
    ("adversarial", "results/adversarial_sweep.csv", "adversarial_fraction"),
    ("staleness", "results/staleness_sweep.csv", "flip_probability"),
]

COMPARISONS = [
    ("reputation_weighted", "majority_vote"),
    ("time_decayed", "majority_vote"),
    ("time_decayed", "reputation_weighted"),
]

OUTPUT_PATH = "results/effect_sizes.csv"
ALPHA = 0.05


def load(path, param_column):
    """Return {param_value: {algorithm: {seed: accuracy}}}."""
    data = defaultdict(lambda: defaultdict(dict))
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            param = float(row[param_column])
            data[param][row["algorithm"]][int(row["seed"])] = float(
                row["accuracy"]
            )
    return data


def rank_biserial(diffs):
    """
    Matched-pairs rank-biserial correlation. Zero differences are
    dropped, matching the default handling in scipy's wilcoxon().
    """
    nonzero = [d for d in diffs if d != 0.0]
    if not nonzero:
        return 0.0

    ranks = rankdata([abs(d) for d in nonzero])
    w_pos = sum(r for r, d in zip(ranks, nonzero) if d > 0)
    w_neg = sum(r for r, d in zip(ranks, nonzero) if d < 0)
    total = w_pos + w_neg

    return (w_pos - w_neg) / total if total else 0.0


def magnitude(r):
    a = abs(r)
    if a < 0.1:
        return "negligible"
    if a < 0.3:
        return "small"
    if a < 0.5:
        return "medium"
    return "large"


def holm(pvalues):
    """
    Holm-Bonferroni step-down adjustment. Returns adjusted p-values in
    the original order, each capped at 1.0 and made monotonic.
    """
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0

    for rank, idx in enumerate(order):
        value = (m - rank) * pvalues[idx]
        running = max(running, value)
        adjusted[idx] = min(1.0, running)

    return adjusted


def main():
    records = []

    for sweep_name, path, param_column in SWEEPS:
        data = load(path, param_column)

        for param in sorted(data):
            for algo_a, algo_b in COMPARISONS:
                seeds = sorted(
                    set(data[param][algo_a]) & set(data[param][algo_b])
                )
                a = [data[param][algo_a][s] for s in seeds]
                b = [data[param][algo_b][s] for s in seeds]
                diffs = [x - y for x, y in zip(a, b)]

                mean_diff = sum(diffs) / len(diffs)

                if all(d == 0.0 for d in diffs):
                    p_raw = 1.0
                else:
                    p_raw = wilcoxon(a, b).pvalue

                records.append({
                    "sweep": sweep_name,
                    "parameter": param,
                    "comparison": f"{algo_a} vs {algo_b}",
                    "n_seeds": len(seeds),
                    "mean_diff_pts": mean_diff * 100,
                    "p_raw": p_raw,
                    "rank_biserial": rank_biserial(diffs),
                })

    adjusted = holm([r["p_raw"] for r in records])
    for record, p_adj in zip(records, adjusted):
        record["p_holm"] = p_adj
        record["significant_holm"] = "yes" if p_adj < ALPHA else "no"
        record["effect_magnitude"] = magnitude(record["rank_biserial"])

    changed = [
        r for r in records
        if (r["p_raw"] < ALPHA) != (r["p_holm"] < ALPHA)
    ]

    for sweep_name, _, _ in SWEEPS:
        print(f"\n{sweep_name}")
        for r in records:
            if r["sweep"] != sweep_name:
                continue
            print(
                f"  {r['parameter']:<5} {r['comparison']:<42} "
                f"diff={r['mean_diff_pts']:+7.2f}pts  "
                f"p={r['p_raw']:.2e}  "
                f"p_holm={r['p_holm']:.2e}  "
                f"{r['significant_holm']:<3} "
                f"rb={r['rank_biserial']:+.3f} ({r['effect_magnitude']})"
            )

    print(
        f"\n{len(records)} tests in the family. "
        f"{len(changed)} change significance status under Holm-Bonferroni."
    )
    if changed:
        for r in changed:
            print(
                f"  {r['sweep']} {r['parameter']} {r['comparison']}: "
                f"p={r['p_raw']:.2e} -> {r['p_holm']:.2e}"
            )

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sweep", "parameter", "comparison", "n_seeds",
                "mean_diff_pts", "p_raw", "p_holm", "significant_holm",
                "rank_biserial", "effect_magnitude",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print(f"\nWrote {len(records)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
