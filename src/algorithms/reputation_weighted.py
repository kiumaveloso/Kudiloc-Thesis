"""
Reputation-Weighted Aggregation algorithm.

Improves on Majority Vote by weighting each report by its reporter's
current `reputation` (a cross-ATM, periodically-updated trust score —
see src/simulation/reputation.py) instead of counting every report
equally. A reporter with a strong track record across the population
of ATMs they've reported on has proportionally more influence on the
aggregate estimate for any given ATM, including ATMs they've never
reported on before.

This directly targets the failure mode Majority Vote demonstrated in
Phase 1 (accuracy collapsing to 14% at high adversarial fraction):
adversarial reporters who are consistently wrong should, over time,
accumulate low reputation and be down-weighted, limiting their ability
to corrupt the aggregate even when they are numerous.
"""

from src.simulation.models import AggregationAlgorithm, Report, Reporter


class ReputationWeightedAggregation(AggregationAlgorithm):
    """
    Aggregates reports by summing each report's reporter.reputation as a
    weight toward "stocked" or "empty", and returning whichever side has
    the greater total weight.

    Unlike Majority Vote, this algorithm requires the `reporters` lookup
    to be supplied — reputation lives on the Reporter object, not on the
    Report itself (reports are immutable snapshots; reputation is a
    living, updated value — see models.py docstrings for both).
    """

    def aggregate(
        self,
        reports: list[Report],
        query_time: float,
        reporters: dict[str, Reporter] | None = None,
    ) -> bool:
        """
        Estimate ATM state via reputation-weighted vote.

        Args:
            reports: Reports for a single ATM at query time.
            query_time: Unused here — Reputation-Weighted has no notion
                of report age (that's Time-Decayed Trust Scoring's job).
                Accepted for interface compatibility only.
            reporters: Required. Lookup of reporter_id -> Reporter, used
                to read each report's reporter's current reputation.

        Returns:
            True (stocked) if total reputation-weight for "stocked"
            reports is >= total weight for "empty" reports, else False.

        Raises:
            ValueError: if `reporters` is None. Reputation-Weighted
                cannot function without reputation data, unlike
                Majority Vote, so this is enforced rather than silently
                falling back to unweighted counting.
        """
        if reporters is None:
            raise ValueError(
                "ReputationWeightedAggregation requires a reporters "
                "lookup (reporter_id -> Reporter) to read reputation "
                "weights; received None."
            )

        stocked_weight = 0.0
        empty_weight = 0.0

        for report in reports:
            weight = reporters[report.reporter_id].reputation
            if report.claimed_state:
                stocked_weight += weight
            else:
                empty_weight += weight

        # Tie-breaking mirrors MajorityVote for consistency: defaults to
        # True (stocked) when there are zero reports or weights are
        # exactly tied. Same methodological choice, documented once in
        # MajorityVote and reapplied here rather than re-justified.
        if stocked_weight >= empty_weight:
            return True
        return False
