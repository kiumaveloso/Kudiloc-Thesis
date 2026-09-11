r"""
Generate thesis figures from the Phase 3 sweep summary CSVs.

Reads the summary CSVs and produces one line chart per research
question, each saved as both PDF (vector, for LaTeX \includegraphics)
and PNG (raster, for quick viewing/sharing).

Each chart plots mean accuracy vs. the swept parameter for all three
algorithms, with 95% confidence interval error bars (the ci95_halfwidth
column written by the sweep scripts). No pandas dependency: the CSVs are
small and read with the stdlib csv module, to keep the plotting step's
requirements minimal (matplotlib only).

Run from the repo root:
    PYTHONPATH=. python3 experiments/make_plots.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")  # non-interactive backend: write files, don't open a window
import matplotlib.pyplot as plt

FIGURES_DIR = "results/figures"

ALGO_STYLE = {
    "majority_vote": {"label": "Majority Vote", "color": "#c1121f", "marker": "o"},
    "reputation_weighted": {"label": "Reputation-Weighted", "color": "#0077b6", "marker": "s"},
    "time_decayed": {"label": "Time-Decayed", "color": "#2a9d8f", "marker": "^"},
}
ALGO_ORDER = ["majority_vote", "reputation_weighted", "time_decayed"]


def load_summary(path: str, x_column: str) -> dict:
    """
    Read a summary CSV into:
        { algorithm: { "x": [...], "mean": [...], "ci": [...] } }
    sorted by the x value, so lines plot left-to-right correctly.
    """
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
        triples.sort(key=lambda t: t[0])
        data[algo] = {
            "x": [t[0] for t in triples],
            "mean": [t[1] * 100 for t in triples],
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
            series["x"], series["mean"], yerr=series["ci"],
            label=style["label"], color=style["color"], marker=style["marker"],
            markersize=6, linewidth=2, capsize=3, elinewidth=1,
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
    fig.savefig(png_path, dpi=300)
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

    # RQ1: report density. Plotted against expected reports per ATM
    # rather than the raw report_probability, since reports-per-ATM is
    # the quantity the proposal names and the more interpretable axis.
    density = load_summary(
        "results/density_sweep_summary.csv", "reports_per_atm"
    )
    make_chart(
        density,
        x_label="Reports per ATM",
        title="Accuracy vs. report density (RQ1)",
        out_basename="density_sweep",
    )


if __name__ == "__main__":
    main()


# --- Half-life sensitivity chart --------------------------------------


def load_halflife_sensitivity(path: str = "results/halflife_sensitivity.csv") -> dict:
    """
    Read results/halflife_sensitivity.csv into:
        { series_label: { "x": [...], "mean": [...], "ci": [...] } }
    One series for Reputation-Weighted (no half_life, decay-free
    baseline) and one series per Time-Decayed half-life tested.
    """
    per_series = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row["algorithm"]
            half_life = row["half_life"]
            if algo == "reputation_weighted":
                label = "Reputation-Weighted"
            else:
                label = f"Time-Decayed ({int(float(half_life))}h half-life)"
            per_series.setdefault(label, []).append(
                (
                    float(row["flip_probability"]),
                    float(row["mean_accuracy"]) * 100,
                    float(row["ci95_halfwidth"]) * 100,
                )
            )

    data = {}
    for label, triples in per_series.items():
        triples.sort(key=lambda t: t[0])
        data[label] = {
            "x": [t[0] for t in triples],
            "mean": [t[1] for t in triples],
            "ci": [t[2] for t in triples],
        }
    return data


HALFLIFE_STYLE = {
    "Reputation-Weighted": {"color": "#0077b6", "marker": "s", "linestyle": "-"},
    "Time-Decayed (6h half-life)": {"color": "#e76f51", "marker": "v", "linestyle": "--"},
    "Time-Decayed (12h half-life)": {"color": "#2a9d8f", "marker": "^", "linestyle": "-"},
    "Time-Decayed (24h half-life)": {"color": "#8338ec", "marker": "D", "linestyle": ":"},
}
HALFLIFE_ORDER = [
    "Reputation-Weighted",
    "Time-Decayed (6h half-life)",
    "Time-Decayed (12h half-life)",
    "Time-Decayed (24h half-life)",
]


def make_halflife_chart(path: str = "results/halflife_sensitivity.csv") -> None:
    """
    Draw the half-life sensitivity chart: Reputation-Weighted (fixed,
    no decay parameter) against Time-Decayed at three half-lives, all
    against flip_probability. Saved as both PDF and PNG under
    FIGURES_DIR, matching the other charts' format.
    """
    data = load_halflife_sensitivity(path)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    for label in HALFLIFE_ORDER:
        if label not in data:
            continue
        style = HALFLIFE_STYLE[label]
        series = data[label]
        ax.errorbar(
            series["x"], series["mean"], yerr=series["ci"],
            label=label, color=style["color"], marker=style["marker"],
            linestyle=style["linestyle"], markersize=6, linewidth=2,
            capsize=3, elinewidth=1,
        )

    ax.set_xlabel("Flip probability (fraction of ATMs changing state)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Half-life sensitivity: Time-Decayed vs. Reputation-Weighted")
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower left", fontsize=9)

    fig.tight_layout()

    pdf_path = os.path.join(FIGURES_DIR, "halflife_sensitivity.pdf")
    png_path = os.path.join(FIGURES_DIR, "halflife_sensitivity.png")
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=300)
    plt.close(fig)

    print(f"Wrote {pdf_path}")
    print(f"Wrote {png_path}")


if __name__ == "__main__":
    make_halflife_chart()
