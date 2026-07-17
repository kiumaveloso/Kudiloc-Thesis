"""
Shared helpers for Phase 2/3 experiment scripts.

Kept separate from src/ because these are experiment-harness concerns
(how a script chooses to structure its reveal schedule), not part of
the core simulation/algorithm library itself.
"""

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
