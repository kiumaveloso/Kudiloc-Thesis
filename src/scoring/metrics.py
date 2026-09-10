"""
Confusion-matrix-based scoring for aggregation algorithms.

Extends compute_accuracy() with precision, recall, F1-score and
balanced accuracy. "Stocked" (True) is treated as the positive class
throughout. Balanced accuracy is reported because the generated ground
truth is unbalanced (roughly 70% of ATMs are stocked), which makes
plain accuracy difficult to interpret on its own.
"""

from src.simulation.models import ATM, AggregationAlgorithm, Report


def compute_metrics(
    atms: list[ATM],
    reports: list[Report],
    algorithm: AggregationAlgorithm,
    query_time: float,
    reporters: dict | None = None,
) -> dict:
    """
    Run an aggregation algorithm on every ATM and score its estimates
    against known ground truth using a confusion matrix.

    Same arguments as compute_accuracy(). Returns a dict with keys:
    accuracy, precision, recall, f1, balanced_accuracy, and the four
    raw counts tp, fp, tn, fn.
    """
    reports_by_atm: dict[str, list[Report]] = {}
    for report in reports:
        reports_by_atm.setdefault(report.atm_id, []).append(report)

    tp = fp = tn = fn = 0

    for atm in atms:
        atm_reports = reports_by_atm.get(atm.atm_id, [])
        estimate = algorithm.aggregate(atm_reports, query_time, reporters)

        if atm.true_state and estimate:
            tp += 1
        elif not atm.true_state and estimate:
            fp += 1
        elif not atm.true_state and not estimate:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    balanced_accuracy = (recall + specificity) / 2

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": balanced_accuracy,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }
