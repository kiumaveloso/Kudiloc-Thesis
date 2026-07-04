"""
Scoring functions for evaluating aggregation algorithm accuracy against
known ground truth.
"""

from src.simulation.models import ATM, AggregationAlgorithm, Report


def compute_accuracy(
    atms: list[ATM],
    reports: list[Report],
    algorithm: AggregationAlgorithm,
    query_time: float,
    reporters: dict | None = None,
) -> float:
    """
    Run an aggregation algorithm on every ATM's reports and compare the
    estimate against the ATM's known true_state.

    Args:
        atms: The ATMs with known ground truth to score against.
        reports: All reports across all ATMs (will be filtered per-ATM).
        algorithm: The aggregation algorithm instance to evaluate.
        query_time: Simulated time at which estimates are requested.
        reporters: Optional reporter lookup, passed through to the
            algorithm for reputation-aware methods.

    Returns:
        Accuracy as a float in [0.0, 1.0]: the proportion of ATMs whose
        estimated state matched the true state.
    """
    correct = 0
    for atm in atms:
        atm_reports = [r for r in reports if r.atm_id == atm.atm_id]
        estimate = algorithm.aggregate(atm_reports, query_time, reporters)
        if estimate == atm.true_state:
            correct += 1

    return correct / len(atms) if atms else 0.0