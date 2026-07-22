r"""
Generate thesis figures from the Phase 3 sweep summary CSVs.

Reads results/adversarial_sweep_summary.csv (RQ2) and
results/staleness_sweep_summary.csv (RQ3) and produces one line chart
per research question, each saved as both PDF (vector, for LaTeX
\includegraphics) and PNG (raster, for quick viewing/sharing).

Each chart plots mean accuracy vs. the swept parameter for all three
algorithms, with 95% confidence interval error bars (the ci95_halfwidth
column written by the sweep scripts). No pandas dependency — the CSVs
are small and read with the stdlib csv module, to keep requirements.txt
minimal (matplotlib only).

Run from the repo root:
    PYTHONPATH=. python3 experiments/make_plots.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")  # non-interactive backend: write files, don't open a window
import matplotlib.pyplot as plt

FIGURES_DIR = "results/figures"

# Consistent display names, colors, and marker styles across both charts,
# so the same algorithm looks identical in every figure (helps the reader
# track a line across figures in the thesis).
ALGO_STYLE = {
    "majority_vote": {"label": "Majority Vote", "color": "#c1121f", "marker": "o"},
    "reputation_weighted": {"label": "Reputation-Weighted", "color": "#0077b6", "marker": "s"},
    "time_decayed": {"label": "Time-Decayed", "color": "#2a9d8f", "marker": "^"},
}
# Order lines are drawn / appear in the legend.
ALGO_ORDER = ["majority_vote", "reputation_weighted", "time_decayed"]


def load_summary(path: str, x_column: str) -> dict:
    """
    Read a summary CSV into a nested dict:
        { algorithm: { "x": [...], "mean": [...], "ci": [...] } }
    sorted by the x value, so lines plot left-to-right correctly.

    Args:
        path: Path to the summary CSV.
        x_column: Name of the swept-parameter column
            ("adversarial_fraction" or "flip_probability").
    """
    # Collect raw rows first, then sort per-algorithm by x.
    per_algo = {algo: [] for algo in ALGO_ORDER}

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row["algorithm"]
            if algo not in per_algo:
                continue
            per_algo[algo].append(
                (
                    float(row[x_column]),
                    float(row["mean_accuracy"]),
                    float(row["ci95_halfwidth"]),
                )
            )

    data = {}
    for algo, triples in per_algo.items():
        triples.sort(key=lambda t: t[0])  # sort by x
        data[algo] = {
            "x": [t[0] for t in triples],
            "mean": [t[1] * 100 for t in triples],  # to percentage points
            "ci": [t[2] * 100 for t in triples],
        }
    return data


def make_chart(data: dict, x_label: str, title: str, out_basename: str) -> None:
    """
    Draw one line chart (mean accuracy vs. swept parameter, with 95% CI
    error bars) and save it as both PDF and PNG under FIGURES_DIR.
    """
    fig, ax = plt.subplots(figsize=(7.0, 4.5))

    for algo in ALGO_ORDER:
        style = ALGO_STYLE[algo]
        series = data[algo]
        ax.errorbar(
            series["x"],
            series["mean"],
            yerr=series["ci"],
            label=style["label"],
            color=style["color"],
            marker=style["marker"],
            markersize=6,
            linewidth=2,
            capsize=3,          # little caps on the error bars
            elinewidth=1,
        )

    ax.set_xlabel(x_label)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title(title)
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower left")

    fig.tight_layout()

    pdf_path = os.path.join(FIGURES_DIR, out_basename + ".pdf")
    png_path = os.path.join(FIGURES_DIR, out_basename + ".png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=200)
    plt.close(fig)

    print(f"Wrote {pdf_path}")
    print(f"Wrote {png_path}")


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    adversarial = load_summary(
        "results/adversarial_sweep_summary.csv", "adversarial_fraction"
    )
    make_chart(
        adversarial,
        x_label="Adversarial fraction",
        title="Accuracy vs. adversarial fraction (RQ2)",
        out_basename="adversarial_sweep",
    )

    staleness = load_summary(
        "results/staleness_sweep_summary.csv", "flip_probability"
    )
    make_chart(
        staleness,
        x_label="Flip probability (fraction of ATMs changing state)",
        title="Accuracy vs. staleness (RQ3)",
        out_basename="staleness_sweep",
    )


if __name__ == "__main__":
    main()
