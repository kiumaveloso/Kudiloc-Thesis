"""
Shared helpers for Phase 2/3 experiment scripts.

Kept separate from src/ because these are experiment-harness concerns
(how a script chooses to structure its reveal schedule), not part of
the core simulation/algorithm library itself.
"""

import math
import statistics

from src.simulation.reputation import update_reputations

DEFAULT_REVEAL_INTERVAL = 10.0  # simulated hours between periodic ground-truth reveals


def run_periodic_reveals(reports, atms, reporters, time_window, reveal_interval=DEFAULT_REVEAL_INTERVAL):
    """
    Process reports in time-bucketed order, calling update_reputations()
    after each interval, so reporter reputations mature progressively
    across the simulation rather than all at once at the end.

    Returns a reporter_id -> Reporter lookup with reputations updated
    in place, ready to pass into reputation-aware algorithms.
    """
    atms_by_id = {atm.atm_id: atm for atm in atms}
    reporters_by_id = {r.reporter_id: r for r in reporters}

    sorted_reports = sorted(reports, key=lambda r: r.timestamp)
    interval_end = reveal_interval
    bucket = []

    for report in sorted_reports:
        if report.timestamp > interval_end:
            if bucket:
                update_reputations(bucket, atms_by_id, reporters_by_id)
            bucket = []
            interval_end += reveal_interval
        bucket.append(report)

    if bucket:
        update_reputations(bucket, atms_by_id, reporters_by_id)

    return reporters_by_id


def summarize(values: list[float]) -> dict:
    """
    Compute mean, sample standard deviation, and a 95% confidence
    interval half-width for a list of accuracy values (one per seed).

    The CI uses the normal approximation (1.96 * standard_error) rather
    than a t-distribution correction. This is a reasonable simplification
    at n=30 (where the t-distribution is already close to normal), and
    avoids adding a scipy dependency for a single-purpose calculation —
    worth noting as a simplification if this exact CI value is quoted
    in the thesis (see dev_log.md).

    Args:
        values: A list of accuracy values (e.g. one per seed) for a
            single algorithm at a single parameter setting.

    Returns:
        dict with keys: mean, std, n, ci95_halfwidth. If len(values) < 2,
        std and ci95_halfwidth are 0.0 (standard deviation is undefined
        for a single sample).
    """
    n = len(values)
    mean = statistics.mean(values)

    if n < 2:
        return {"mean": mean, "std": 0.0, "n": n, "ci95_halfwidth": 0.0}

    std = statistics.stdev(values)
    standard_error = std / math.sqrt(n)
    ci95_halfwidth = 1.96 * standard_error

    return {"mean": mean, "std": std, "n": n, "ci95_halfwidth": ci95_halfwidth}
