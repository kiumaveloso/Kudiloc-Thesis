"""
Majority Vote aggregation algorithm.

The unweighted baseline: counts how many reports claim "stocked" vs
"empty" for an ATM and returns whichever is more common. Every reporter
counts equally regardless of reliability or adversarial status — this
is exactly the naive approach that Reputation-Weighted and Time-Decayed
Trust Scoring are designed to improve upon.
"""

from src.simulation.models import AggregationAlgorithm, Report, Reporter


class MajorityVote(AggregationAlgorithm):
    """
    Aggregates reports by simple majority count, ignoring reporter
    identity, reliability, and report age entirely.
    """

    def aggregate(
        self,
        reports: list[Report],
        query_time: float,
        reporters: dict[str, Reporter] | None = None,
    ) -> bool:
        """
        Estimate ATM state via unweighted majority vote.

        Note: query_time and reporters are accepted for interface
        compatibility but unused — Majority Vote has no concept of
        report age or reporter trust.

        Tie-breaking: if there are zero reports, or the vote is exactly
        tied, defaults to True (stocked). This is a deliberate
        methodological choice, not an arbitrary one — worth noting
        explicitly in the thesis methodology chapter.
        """
        stocked_votes = sum(1 for r in reports if r.claimed_state)
        empty_votes = sum(1 for r in reports if not r.claimed_state)

        if stocked_votes >= empty_votes:
            return True
        return False