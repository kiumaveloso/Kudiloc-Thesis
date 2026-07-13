"""
Phase 2 sanity-check runner.

Two scenarios, per the Phase 2 checklist in dev_log.md:

1. Adversarial-fraction sanity check: recreates the Phase 1
   adversarial_fraction=0.6 scenario and confirms Reputation-Weighted
   Aggregation outperforms Majority Vote once reporter reputations have
   had a chance to converge via periodic ground-truth reveals.

2. Staleness sanity check: generates reports for ATMs, then flips a
   fraction of ATM true_states (simulating real-world change between
   report time and query time), and confirms Time-Decayed Trust Scoring
   outperforms Reputation-Weighted when many reports are now stale.

Periodic reveal implementation note: this simulation has no explicit
"rounds" concept yet, reports are a single timestamped stream. Periodic
ground-truth reveal is implemented here as time-bucketed reveals: reports
are grouped into fixed-width time intervals, and after each interval
"passes," update_reputations() is called on the reports seen in that
interval. This is a faithful implementation of "periodic reveal" without
requiring a multi-round harness, and preserves the cross-ATM reputation
design (see dev_log.md, Day 2).
"""

from src.algorithms.majority_vote import MajorityVote
from src.algorithms.reputation_weighted import ReputationWeightedAggregation
from src.algorithms.time_decayed import TimeDecayedTrustScoring
from src.scoring.accuracy import compute_accuracy
from src.simulation.ground_truth import generate_atms, generate_flip_times
from src.simulation.report_stream import generate_reports
from src.simulation.reporters import generate_reporters
from src.simulation.reputation import update_reputations

REVEAL_INTERVAL = 10.0  # simulated hours between periodic ground-truth reveals


def run_periodic_reveals(reports, atms, reporters, time_window, reveal_interval=REVEAL_INTERVAL):
    """
    Process reports in time-bucketed order, calling update_reputations()
    after each interval, so reporter reputations mature progressively
    across the simulation rather than all at once at the end.
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


def adversarial_fraction_sanity_check():
    print("=" * 70)
    print("SANITY CHECK 1: Adversarial fraction = 0.6")
    print("=" * 70)

    num_atms = 50
    num_reporters = 30
    adversarial_fraction = 0.6
    time_window = 60.0
    seed = 42

    atms = generate_atms(num_atms, seed=seed)
    reporters = generate_reporters(num_reporters, seed=seed, adversarial_fraction=adversarial_fraction)
    reports = generate_reports(atms, reporters, seed=seed, time_window=time_window)

    query_time = time_window

    mv_accuracy = compute_accuracy(atms, reports, MajorityVote(), query_time)

    reporters_by_id = run_periodic_reveals(reports, atms, reporters, time_window)
    rw_accuracy = compute_accuracy(atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id)

    print(f"Majority Vote accuracy:          {mv_accuracy:.2%}")
    print(f"Reputation-Weighted accuracy:     {rw_accuracy:.2%}")
    print(f"Improvement over Majority Vote:   {(rw_accuracy - mv_accuracy):+.2%}")
    print()

    return mv_accuracy, rw_accuracy


def staleness_sanity_check():
    print("=" * 70)
    print("SANITY CHECK 2: Staleness (ATM states change after reports)")
    print("=" * 70)

    num_atms = 50
    num_reporters = 30
    adversarial_fraction = 0.2
    time_window = 60.0
    seed = 7

    atms = generate_atms(num_atms, seed=seed)
    reporters = generate_reporters(num_reporters, seed=seed, adversarial_fraction=adversarial_fraction)

    # Assign flip_times BEFORE generating reports, so each report is
    # checked against the ATM's actual state at its own timestamp — this
    # is what makes staleness a genuine per-report property instead of
    # an instantaneous, timestamp-blind toggle (see dev_log.md
    # staleness-fix entry).
    generate_flip_times(atms, seed=seed + 1, flip_probability=0.5, time_window=time_window)

    reports = generate_reports(atms, reporters, seed=seed, time_window=time_window)

    # Mature reputations on these reports (reputation reflects
    # historical accuracy, which is legitimate — it's not cheating,
    # since it's based on past behavior, not future knowledge).
    reporters_by_id = run_periodic_reveals(reports, atms, reporters, time_window)

    # Query right at window close, scored against each ATM's final
    # true_state (post-flip, where applicable).
    query_time = time_window

    rw_accuracy = compute_accuracy(atms, reports, ReputationWeightedAggregation(), query_time, reporters_by_id)
    td_accuracy = compute_accuracy(atms, reports, TimeDecayedTrustScoring(), query_time, reporters_by_id)

    print(f"Reputation-Weighted accuracy (stale reports): {rw_accuracy:.2%}")
    print(f"Time-Decayed accuracy (stale reports):        {td_accuracy:.2%}")
    print(f"Improvement over Reputation-Weighted:         {(td_accuracy - rw_accuracy):+.2%}")
    print()

    return rw_accuracy, td_accuracy


if __name__ == "__main__":
    mv_acc, rw_acc = adversarial_fraction_sanity_check()
    rw_acc_stale, td_acc = staleness_sanity_check()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Majority Vote (adversarial=0.6):        {mv_acc:.2%}")
    print(f"Reputation-Weighted (adversarial=0.6):   {rw_acc:.2%}")
    print(f"Reputation-Weighted (stale scenario):    {rw_acc_stale:.2%}")
    print(f"Time-Decayed (stale scenario):           {td_acc:.2%}")
